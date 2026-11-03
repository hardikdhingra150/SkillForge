"""SkillForge as an MCP server: every validated skill becomes a tool other agents can call.

    claude mcp add skillforge -- <repo>/backend/bin/skillforge-mcp
    codex mcp add skillforge -- <repo>/backend/bin/skillforge-mcp

Tools run exactly like inside SkillForge: the latest validated version for the
capability, integrity-checked, executed in the sandbox, then the contract checks.
The tool list is read from the registry on every request, so new and repaired
skills appear without restarting the server. stdout carries the protocol; logs go to stderr.
"""

import asyncio
import json
import logging
import re

import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from sqlalchemy import select

from app.database.session import SessionLocal
from app.database.skill_models import SkillVersion
from app.sandbox import run_skill
from app.services import scoreboard
from app.services.checks import CheckFailed, run_checks
from app.services.skill_registry import SkillIntegrityError, latest_validated, verify, version_key

logger = logging.getLogger("skillforge.mcp")
server = Server("skillforge", instructions=(
    "SkillForge tools are tested, versioned skills. Each one runs in a sandbox and its output is checked "
    "against its contract before it is returned. Prefer them over writing equivalent code by hand."))

JSON_TYPES = {"text": "string", "integer": "integer", "number": "number", "boolean": "boolean", "list": "array",
              "object": "object", "decimal_string": "string", "column": "string", "csv": "string"}
LIST_TOOL = "skillforge_list_skills"


def tool_name(capability: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", capability)[:64]


def latest_skills(db) -> dict[str, SkillVersion]:
    """The newest validated, runnable version of every capability, keyed by tool name."""
    rows = db.scalars(select(SkillVersion).where(SkillVersion.status == "validated", SkillVersion.source_code.is_not(None))).all()
    best: dict[str, SkillVersion] = {}
    for row in rows:
        current = best.get(row.capability)
        if current is None or version_key(row.version) > version_key(current.version):
            best[row.capability] = row
    return {tool_name(capability): row for capability, row in best.items()}


def input_schema(contract: dict) -> dict:
    properties, required = {}, []
    for field in contract.get("inputs", []):
        kind = field.get("type", "text")
        description = field.get("description", "")
        if kind == "csv":
            description = f"{description} CSV text, header row first.".strip()
        elif kind == "column":
            description = f"{description} A column name from the CSV header.".strip()
        properties[field["name"]] = {"type": JSON_TYPES.get(kind, "string"), "description": description}
        if field.get("required", True):
            required.append(field["name"])
    return {"type": "object", "properties": properties, "required": required, "additionalProperties": False}


def describe(row: SkillVersion) -> str:
    summary = row.contract_json.get("summary") or row.capability
    tests = (row.validation_json or {}).get("test_count", 0)
    origin = f"{row.origin} from v{row.parent_version}" if row.parent_version else row.origin
    return f"{summary} (SkillForge {row.skill_id} v{row.version}, {origin}, proven by {tests} tests in a sandbox.)"


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    def load():
        with SessionLocal() as db:
            return [types.Tool(name=name, description=describe(row), inputSchema=input_schema(row.contract_json),
                               annotations=types.ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False))
                    for name, row in sorted(latest_skills(db).items())]
    tools = await asyncio.to_thread(load)
    tools.append(types.Tool(
        name=LIST_TOOL, description="List SkillForge's validated skills with their versions, origins and evidence.",
        inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
        annotations=types.ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False)))
    return tools


def execute(name: str, arguments: dict) -> dict:
    with SessionLocal.begin() as db:
        if name == LIST_TOOL:
            return {"skills": [{"tool": tool, "skill_id": row.skill_id, "version": row.version, "origin": row.origin,
                                "parent_version": row.parent_version, "summary": row.contract_json.get("summary"),
                                "tests": (row.validation_json or {}).get("test_count")}
                               for tool, row in sorted(latest_skills(db).items())]}
        row = latest_skills(db).get(name)
        if row is None:
            raise ValueError(f"No validated SkillForge skill is exposed as {name!r}.")
        skill = latest_validated(db, row.capability)
        contract = verify(skill)
        source, key = skill.source_code, (skill.skill_id, skill.version)
        creator = (skill.change_json or {}).get("created_by")
    files = {f.name: str(arguments[f.name]).encode() for f in contract.inputs if f.type == "csv" and f.name in arguments}
    inputs = {f.name: arguments[f.name] for f in contract.inputs if f.type != "csv" and f.name in arguments}
    missing = [f.name for f in contract.inputs if f.required and f.name not in arguments]
    if missing:
        raise ValueError(f"Missing required input(s): {', '.join(missing)}.")
    run = run_skill(source, inputs=inputs, files=files, tools=contract.tools)
    if not run.ok:
        raise ValueError(f"{key[0]} v{key[1]} failed in the sandbox: {run.error.get('message')} "
                         "(open SkillForge to repair it; the next version will be exposed automatically).")
    validation = run_checks(contract, files, inputs, run.output)
    if creator:
        scoreboard.record(creator, "author", "reused", capability=contract.capability)
    return {"output": run.output, "skill": {"id": key[0], "version": key[1]}, "checks": validation["checks"],
            "duration_ms": run.duration_ms}


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> types.CallToolResult:
    try:
        result = await asyncio.to_thread(execute, name, arguments or {})
    except (ValueError, CheckFailed, SkillIntegrityError) as error:
        return types.CallToolResult(content=[types.TextContent(type="text", text=str(error))], isError=True)
    # Structured content carries provenance too: which version answered and which checks it passed.
    return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps(result, indent=2))],
                                structuredContent=result)


async def main():
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")  # stderr only
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
