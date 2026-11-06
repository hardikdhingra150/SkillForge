"""The chat agent: plan a turn, reuse or create a skill, prove it, and reply.

    user message (+ attached CSV files)
      -> plan (LLM): plain answer, or 1-4 skill steps; a step's input may be "$stepN.field" from an
         earlier step, and a step may read an attached CSV
      -> answer: the model replies directly
      -> skill: latest validated version for the capability?
           yes -> run in the sandbox + contract checks
                  failed -> SkillSmith patch (LLM), proven, promoted as a repaired version
           no  -> SkillSmith create (LLM): contract + source + worked examples,
                  proven in the sandbox (examples + this input), registered as v1.0.0
      -> reply with the skill's output

Whatever the model writes is untrusted: it only becomes a skill after the
sandbox policy, the contract schema and every worked example pass.
"""

import json
from contextvars import ContextVar
from datetime import UTC, datetime

from sqlalchemy import func, select

from app.config import settings
from app.database.chat_models import ChatAttachment, ChatMessage, Conversation
from app.database.session import SessionLocal
from app.database.skill_models import SkillVersion
from app.llm import PROVIDERS, LLMError, complete_json, get_provider, only
from app.sandbox import PolicyViolation, check_source, run_skill
from app.sandbox.tools import TOOL_DOCS, TOOL_NAMES
from app.schemas.skill_contract import SkillContract
from app.security import LOCAL_WORKSPACE_ID
from app.services import audit, live, scoreboard
from app.services.checks import CheckFailed, run_checks
from app.services.csv_inputs import parse_csv
from app.services.discovery import discover
from app.services.repair import (
    Repaired,
    attempt_repair,
    classify_check,
    classify_run_error,
    encode_fixture,
    lineage_fixtures,
    promote,
    retired_duplicate,
)
from app.services.skill_registry import (
    ExampleMismatch,
    can_see,
    implementation_hash,
    latest_validated,
    owner_for,
    run_fixture_tests,
    shareable_change,
    verify,
    version_key,
    visible_to,
)
from app.services.workflows import WORKFLOWS, describe_mapping, match_workflows, suggest_mapping, validate_columns

MAX_HISTORY = 10
# The workspace the current chat turn belongs to: it sees the shared skills plus its own.
TURN_WORKSPACE: ContextVar = ContextVar("turn_workspace", default=LOCAL_WORKSPACE_ID)
# Strongest first: used to pick an independent verifier and an escalation target.
STRENGTH_ORDER = ["claude", "codex", "ollama"]
LOCAL = "ollama"
SMITH_ATTEMPTS = 3
CHAT_TOOLS = [name for name in TOOL_NAMES if name not in ("read_csv", "column")]  # value-only skills
MAX_STEPS = 4
VERIFY_FILE_BYTES = 12_000  # larger files are too big for a model to recompute reliably

PLANNER_SYSTEM = """You are the planner inside SkillForge, a workspace where AI agents build reusable skills.
Decide how to handle the user's latest message.

Use "skill" ONLY when the message gives concrete input values (in the text or in attached files) AND asks to
compute or transform them (counting, converting units, extracting patterns, reformatting, sorting, statistics,
parsing, validating, aggregating a CSV), so the same small pure-Python function could be reused later.
Everything else is "answer": greetings, explanations, opinions, creative writing, advice, questions about
SkillForge, and ANY request to write, show, fix or explain code ("give me code to...", "write a function...").

For "skill", give one or more steps. Use several steps only when the task is a sequence of DIFFERENT operations
("extract the emails, then dedupe them, then count by domain"); at most 4 steps. For each step:
- capability: snake_case name of the GENERAL operation, never the specific values (e.g. "extract_emails").
- If an existing skill below does the same operation, reuse its capability and its input names exactly.
- inputs: values keyed by short snake_case names. A later step may use an earlier step's output as an input
  value written exactly as "$step1.<output_name>" (for example "$step1.emails").
- input_types: for each input one of text, integer, number, boolean, list, object.
- files: only when the step reads an attached CSV: {"<input_name>": "<attached file name>"}; column names the
  skill needs go in inputs (for example {"product_column": "Product", "revenue_column": "Sales"}).

Use "clarify" when the user clearly wants a task done but a value it needs is missing or ambiguous
("convert this temperature" with no number, "count by domain" with no emails, a CSV task without saying which
column). Ask ONE short, specific question. Do not clarify greetings or questions you can simply answer.

Reply with ONLY a JSON object:
{"mode": "skill" | "answer" | "clarify", "question": str, "steps": [{"capability": str, "summary": str,
  "inputs": {...}, "input_types": {...}, "files": {...}}]}
For "answer" only "mode" is required; for "clarify" give "mode" and "question"."""

SMITH_SYSTEM = """You are SkillSmith, the engineer inside SkillForge. You write small, safe, reusable skills.

A skill is Python source defining exactly one entry point:
    def run(inputs, tools):
        ...
        return {...}   # a JSON-serializable dict

Hard rules (violations are rejected automatically):
- No imports, no classes, no file or network access, no print, no eval/exec/open/getattr/type.
- No names starting with "_" and no attribute names starting with "_".
- Module level may contain only function definitions and constants.
- Allowed builtins: abs all any bool dict enumerate filter float int isinstance len list map max min
  range reversed round set sorted str sum tuple zip, plus Exception, KeyError, TypeError, ValueError.
- String/list/dict methods are fine (e.g. text.split(), text.lower()).
- Extra helpers are available only through `tools` and must be listed in the contract:
{tool_docs}
- Make the skill GENERAL for the capability, not hard-coded to the example values.

Reply with ONLY a JSON object:
{
  "summary": "one line: what the skill does",
  "inputs":  [{"name": "...", "type": "text|integer|number|boolean|list|object|csv", "description": "..."}],
  "outputs": [{"name": "...", "type": "text|integer|number|boolean|list|object|decimal_string", "description": "..."}],
  "tools":   ["tool names you use, or empty"],
  "source":  "def run(inputs, tools):\\n    ...",
  "examples": [{"name": "snake_case", "inputs": {...}, "files": {...}, "output": {...exact expected output...}}]
}
Give at least 3 examples with exact expected outputs, including one edge case.
For a "csv" input, read it with tools.read_csv("<input name>") and give each example's CSV text in
"files": {"<input name>": "header1,header2\\nvalue,value\\n"}; column names go in normal text inputs."""


VERIFIER_SYSTEM = """You are the independent verifier inside SkillForge. A skill (a small program) produced an
output for a user's request. Check whether the output is CORRECT: recompute the answer yourself from the inputs.
Judge it against the skill's DOCUMENTED BEHAVIOUR (its summary and input descriptions, including stated defaults)
applied to the request. Mark it wrong only if it is incorrect for that documented behaviour, or if the request
EXPLICITLY asks for something the documented behaviour contradicts. Where the request is silent or ambiguous, the
documented behaviour decides. Ignore formatting differences (6.5 vs 6.50, key order, int vs float when equal).
Reply with ONLY a JSON object: {"correct": true | false, "expected": <your answer>, "reason": "short"}"""


class SmithExhausted(ValueError):
    """SkillSmith could not produce a skill that passes its proof."""


class NeedsInput(ValueError):
    """A skill was found but a value it needs is missing: ask the user instead of failing."""


class MatchMismatch(ValueError):
    """A model-confirmed match did not hold up on the user's input; build a new skill instead of repairing."""


# ---------- step log (each step is its own short transaction so the UI can poll progress) ----------

def workspace_of(db, message_id):
    """The workspace a chat reply belongs to, so its audit events land there."""
    message = db.get(ChatMessage, message_id)
    conversation = db.get(Conversation, message.conversation_id) if message else None
    return conversation.workspace_id if conversation else None


def add_step(message_id, kind, text, payload=None):
    with SessionLocal.begin() as db:
        message = db.get(ChatMessage, message_id)
        message.steps_json = [*message.steps_json, {
            "kind": kind, "text": text, "payload": payload or {}, "at": datetime.now(UTC).isoformat(),
        }]
        message.updated_at = func.now()
        conversation_id = message.conversation_id
    live.bump(conversation_id)


def finish(message_id, *, content, status="done", skill=None):
    with SessionLocal.begin() as db:
        message = db.get(ChatMessage, message_id)
        message.content, message.status, message.skill_json = content, status, skill
        message.updated_at = func.now()
        db.get(Conversation, message.conversation_id).updated_at = func.now()
        conversation_id = message.conversation_id
    live.bump(conversation_id)


# ---------- planning ----------

def history_text(db, conversation_id, before_sequence):
    rows = db.scalars(
        select(ChatMessage).where(ChatMessage.conversation_id == conversation_id, ChatMessage.sequence < before_sequence,
                                  ChatMessage.status == "done")
        .order_by(ChatMessage.sequence.desc()).limit(MAX_HISTORY)
    ).all()
    return "\n".join(f"{m.role.upper()}: {m.content[:1500]}" for m in reversed(rows))


def needs_files(contract: dict) -> bool:
    """Skills that read an uploaded file (CSV inputs or column mappings)."""
    return any(field.get("type") in ("csv", "column") for field in contract.get("inputs", []))


def registry_text(db, with_files=False):
    rows = db.scalars(select(SkillVersion).where(visible_to(TURN_WORKSPACE.get()), SkillVersion.status == "validated",
                                                 SkillVersion.contract_json.is_not(None))).all()
    seen, lines = set(), []
    for row in rows:
        if row.capability in seen or (needs_files(row.contract_json) and not with_files):
            continue
        seen.add(row.capability)
        names = ", ".join(f"{field['name']}:{field.get('type', 'text')}" for field in row.contract_json.get("inputs", []))
        lines.append(f"- {row.capability}: {row.contract_json.get('summary', '')} (inputs: {names})")
    return "\n".join(lines) or "(none yet)"


def attachments_text(attachments):
    if not attachments:
        return "(no files attached)"
    return "\n".join(f"- {a['filename']}: {a['row_count']} rows; columns: {', '.join(a['headers'])}; "
                     f"first rows: {json.dumps(a['preview'][:3])}" for a in attachments.values())


def normalize_step(raw):
    capability = str(raw.get("capability", "")).strip().lower()
    capability = "".join(ch if ch.isalnum() else "_" for ch in capability).strip("_")[:60]
    inputs = raw.get("inputs") if isinstance(raw.get("inputs"), dict) else None
    files = raw.get("files") if isinstance(raw.get("files"), dict) else {}
    if not capability or inputs is None:
        return None
    return {"capability": capability, "summary": str(raw.get("summary") or capability), "inputs": inputs,
            "input_types": raw.get("input_types") if isinstance(raw.get("input_types"), dict) else {}, "files": files}


def plan(provider, model, history, registry, text, attachments=None):
    prompt = (f"Existing skills:\n{registry}\n\nAttached files:\n{attachments_text(attachments)}\n\n"
              f"Conversation so far:\n{history or '(new conversation)'}\n\nLatest user message:\n{text}")
    decision = complete_json(provider, prompt, system=PLANNER_SYSTEM, model=model)
    if decision.get("mode") == "clarify" and str(decision.get("question") or "").strip():
        return {"mode": "clarify", "question": str(decision["question"]).strip()[:500]}
    if decision.get("mode") != "skill":
        return {"mode": "answer"}
    raw_steps = decision.get("steps") if isinstance(decision.get("steps"), list) else [decision]
    steps = [step for step in (normalize_step(r) for r in raw_steps[:MAX_STEPS] if isinstance(r, dict)) if step]
    # A skill computes from values; a first step with nothing to compute from is just an answer.
    if not steps or not (steps[0]["inputs"] or steps[0]["files"]):
        return {"mode": "answer"}
    return {"mode": "skill", "steps": steps, "capability": steps[0]["capability"], "inputs": steps[0]["inputs"]}


def resolve_refs(inputs, outputs):
    """Replace "$stepN.field" values with the output of an earlier step."""
    resolved = {}
    for name, value in inputs.items():
        if isinstance(value, str) and value.startswith("$step"):
            ref, _, field = value[5:].partition(".")
            if not ref.isdigit() or int(ref) > len(outputs) or int(ref) < 1:
                raise ValueError(f"Step input {name} refers to {value}, which is not an earlier step.")
            earlier = outputs[int(ref) - 1]
            if field not in earlier:
                raise ValueError(f"Step {ref} has no output named {field!r} (it returned {', '.join(earlier)}).")
            value = earlier[field]
        resolved[name] = value
    return resolved


def bind_files(step_files, attachments):
    files = {}
    for input_name, filename in step_files.items():
        match = attachments.get(filename) or (next(iter(attachments.values())) if len(attachments) == 1 else None)
        if match is None:
            raise ValueError(f"I can't find the attached file {filename!r}.")
        files[input_name] = match["content"]
    return files


# ---------- SkillSmith ----------

def smith_prompt(capability, summary, inputs, input_types, feedback=None, existing=None, files=None):
    parts = [f"Capability: {capability}", f"Goal: {summary}",
             f"The user's current inputs (your skill must handle these, with exactly these input names): {json.dumps(inputs)}",
             f"Input types: {json.dumps(input_types)}"]
    if files:
        parts.append("CSV inputs (type csv, read with tools.read_csv(name)):\n" + "\n".join(
            f"- {name}: first lines:\n{content.decode('utf-8-sig', errors='replace')[:600]}" for name, content in files.items()))
    if existing:
        parts.append(f"The current version fails on these inputs. Fix it while keeping the same inputs and outputs.\n"
                     f"Current source:\n{existing}")
    if feedback:
        parts.append(f"Your previous attempt was rejected:\n{feedback}\nFix exactly that and reply with the full JSON again.")
    return "\n\n".join(parts)


def build_candidate(capability, spec, allow_files=False):
    allowed = TOOL_NAMES if allow_files else CHAT_TOOLS
    contract = {
        "capability": capability, "summary": str(spec.get("summary") or capability)[:300], "entrypoint": "run",
        "inputs": [{"name": f["name"], "type": f.get("type", "text"), "description": str(f.get("description", ""))[:300]}
                   for f in spec.get("inputs", [])],
        "outputs": [{"name": f["name"], "type": f.get("type", "text"), "description": str(f.get("description", ""))[:300]}
                    for f in spec.get("outputs", [])],
        "tools": [t for t in spec.get("tools", []) if t in allowed],
        "checks": ["contract_outputs"],
    }
    if not allow_files and any(f["type"] == "csv" for f in contract["inputs"]):
        raise ValueError("This task has no attached file, so the skill cannot take a csv input.")
    SkillContract.model_validate(contract)
    source = spec.get("source") or ""
    check_source(source)
    examples = []
    for i, e in enumerate(spec.get("examples") or [], start=1):
        example_files = {k: str(v).encode() for k, v in (e.get("files") or {}).items()} if allow_files else {}
        examples.append((str(e.get("name") or f"example_{i}"), e.get("inputs") or {}, example_files,
                         {"output": e.get("output") or {}}))
    if len(examples) < 3:
        raise ValueError("Give at least 3 examples with exact expected outputs.")
    return source, contract, examples


def verifier_view(inputs, files):
    """What the verifier sees: the inputs, plus small files in full. None when a file is too big to check by hand."""
    view = dict(inputs)
    for name, content in (files or {}).items():
        if len(content) > VERIFY_FILE_BYTES:
            return None
        view[name] = content.decode("utf-8-sig", errors="replace")
    return view


REBIND_SYSTEM = """A reusable skill ran with inputs that did not match what the user asked for. Re-read the user's
request and set the skill's inputs correctly, using ONLY the input names listed, including optional ones when the
request implies them (for example a flag the user asked for). Keep values that were already right.
Reply with ONLY a JSON object: {"inputs": {...}, "changed": ["names you changed"], "reason": "short"}"""


def rebind_inputs(provider, model, request, contract: dict, inputs: dict, problem: str):
    """Let a model re-bind the inputs from the full contract. Returns new inputs, or None if nothing changed."""
    names = [f["name"] for f in contract.get("inputs", [])]
    prompt = (f"User request: {request}{documented(contract)}\nInputs used: {json.dumps(inputs)}\n"
              f"What went wrong: {problem}")
    try:
        reply = complete_json(provider, prompt, system=REBIND_SYSTEM, model=model, timeout=90)
    except (LLMError, ValueError):
        return None
    proposed = reply.get("inputs") if isinstance(reply.get("inputs"), dict) else {}
    rebound = {**inputs, **{k: v for k, v in proposed.items() if k in names}}
    return rebound if rebound != inputs else None


def documented(contract: dict | None) -> str:
    if not contract:
        return ""
    fields = "; ".join(f"{f['name']} ({f.get('type', 'text')}{', optional' if f.get('required') is False else ''})"
                       f"{': ' + f['description'] if f.get('description') else ''}" for f in contract.get("inputs", []))
    return f"\nSkill's documented behaviour: {contract.get('summary', '')}\nInputs: {fields}"


def verify_output(provider, model, request, capability, inputs, output, contract=None):
    """Ask the model to recompute the answer independently. Returns (correct, reason)."""
    prompt = (f"User request: {request}\nSkill: {capability}{documented(contract)}\nInputs it received: {json.dumps(inputs)}\n"
              f"Output it produced: {json.dumps(output)}")
    try:
        verdict = complete_json(provider, prompt, system=VERIFIER_SYSTEM, model=model, timeout=120)
    except ValueError:
        return True, "The verifier gave no usable verdict."
    if verdict.get("correct") is False:
        return False, f"{verdict.get('reason', 'judged incorrect')} (expected {json.dumps(verdict.get('expected'))})"
    return True, str(verdict.get("reason", ""))


def prove(source, contract, examples, inputs, verifier=None, files=None):
    """Every worked example must reproduce exactly, the user's input must pass the contract, and the
    independent verifier must agree with the answer."""
    evidence = run_fixture_tests(source, contract, examples)
    parsed = SkillContract.model_validate(contract)
    run = run_skill(source, inputs=inputs, files=files or {}, tools=parsed.tools)
    if not run.ok:
        raise ValueError(f"On the user's inputs the skill raised {run.error.get('type')}: {run.error.get('message')}")
    run_checks(parsed, files or {}, inputs, run.output)
    if verifier:
        correct, reason = verifier(inputs, run.output, files, contract)
        if not correct:
            raise ValueError(f"The verifier says the output {json.dumps(run.output)} is wrong: {reason}")
    return evidence, run.output


def prove_with_arbitration(message_id, judge, summary, capability, source, contract, examples, inputs, verifier, files=None):
    """Prove the candidate. When an example disagrees with the code, the independent verifier decides who is
    right: if it sides with the code, the example is corrected; otherwise the mismatch is a real failure."""
    corrected = set()
    while True:
        try:
            evidence, output = prove(source, contract, examples, inputs, verifier, files)
            return evidence, output, examples
        except ExampleMismatch as mismatch:
            if judge is None or mismatch.name in corrected:
                raise
            example_files = next((f for n, _, f, _ in examples if n == mismatch.name), {})
            view = verifier_view(mismatch.inputs, example_files)
            if view is None:
                raise
            add_step(message_id, "arbitrating", f"Example {mismatch.name}: the code says {json.dumps(mismatch.output)}, "
                     f"the example says {json.dumps(mismatch.expected)}. Asking the verifier who is right…")
            correct, reason = judge(f"Task: {summary}", capability, view, mismatch.output)
            if not correct:
                add_step(message_id, "arbitrated", f"The verifier sided with the example: {reason}")
                raise
            corrected.add(mismatch.name)
            if getattr(judge, "author_id", None):
                scoreboard.record(judge.author_id, "author", "example_corrected", capability=capability)
            examples = [(name, ex_inputs, ex_files, {"output": mismatch.output, "corrected_by_verifier": True})
                        if name == mismatch.name else (name, ex_inputs, ex_files, expected)
                        for name, ex_inputs, ex_files, expected in examples]
            add_step(message_id, "arbitrated", f"The verifier sided with the code. Corrected example {mismatch.name}.")


def smith(message_id, provider, model, capability, summary, inputs, input_types, existing=None, verifier=None, feedback=None,
          judge=None, files=None):
    """Ask the model for a skill until it passes the proof, or attempts run out. Returns (source, contract, examples, evidence, output)."""
    tools = TOOL_NAMES if files else CHAT_TOOLS
    system = SMITH_SYSTEM.replace("{tool_docs}", "\n".join(f"  - {TOOL_DOCS[t]}" for t in tools))
    for attempt in range(1, SMITH_ATTEMPTS + 1):
        verb = "fixing" if existing else "writing"
        add_step(message_id, "smith_attempt", f"SkillSmith attempt {attempt}: {verb} {capability}.")
        try:
            spec = complete_json(provider, smith_prompt(capability, summary, inputs, input_types, feedback, existing, files),
                                 system=system, model=model, timeout=300)
            source, contract, examples = build_candidate(capability, spec, allow_files=bool(files))
            evidence, output, examples = prove_with_arbitration(message_id, judge, summary, capability,
                                                                source, contract, examples, inputs, verifier, files)
            scoreboard.record(provider.id, "author", "proven", model=model, capability=capability, attempts=attempt)
            return source, contract, examples, evidence, output
        except LLMError:
            raise
        except (ValueError, PolicyViolation, CheckFailed, KeyError, TypeError) as error:
            feedback = str(error)[:800]
            add_step(message_id, "smith_rejected", f"Rejected attempt {attempt}: {feedback}")
            scoreboard.record(provider.id, "author", "rejected", model=model, capability=capability)
    scoreboard.record(provider.id, "author", "exhausted", model=model, capability=capability, attempts=SMITH_ATTEMPTS)
    raise SmithExhausted(f"SkillSmith could not produce a skill that passes its proof after {SMITH_ATTEMPTS} attempts.")


# ---------- the turn ----------

def bind_chat_inputs(contract, extracted, files=None):
    """Value inputs come from the plan; csv inputs come from attached files."""
    files = files or {}
    missing = [f.name for f in contract.inputs
               if f.required and (f.name not in files if f.type == "csv" else f.name not in extracted)]
    if missing:
        described = [next((f.description for f in contract.inputs if f.name == name), "") or name.replace("_", " ")
                     for name in missing]
        raise NeedsInput(f"To run {contract.capability} I need: {'; '.join(described)}. What should I use?")
    return {f.name: extracted[f.name] for f in contract.inputs if f.type != "csv" and f.name in extracted}


def load_attachments(db, message_id):
    rows = db.scalars(select(ChatAttachment).where(ChatAttachment.message_id == message_id)).all()
    return {row.filename: {"filename": row.filename, "headers": row.headers_json, "row_count": row.row_count,
                           "preview": row.preview_json, "content": row.content_bytes} for row in rows}


# ---------- spreadsheet tasks: the former Workbench, inside Chat ----------

def spreadsheet_workflow(text: str) -> str | None:
    """The one file workflow this request names ("total sales by region"), if exactly one fits."""
    matches = match_workflows(text)
    return matches[0] if len(matches) == 1 else None


def latest_attachments(db, conversation_id, before_sequence):
    """Files attached to the most recent earlier message in this conversation that had any."""
    message_ids = select(ChatMessage.id).where(ChatMessage.conversation_id == conversation_id,
                                               ChatMessage.sequence < before_sequence)
    latest = db.scalars(select(ChatAttachment.message_id).where(ChatAttachment.message_id.in_(message_ids))
                        .order_by(ChatAttachment.created_at.desc()).limit(1)).first()
    return load_attachments(db, latest) if latest else {}


def spreadsheet_author(provider_id, model, capability):
    """The model that would rewrite the skill if the automatic fixes fail (None: no model is connected)."""
    if provider_id == "auto":
        provider_id = scoreboard.route_author(capability)[0] or scoreboard.pick_planner()
        model = PROVIDERS[provider_id].status().default_model if provider_id else None
    if provider_id is None or not PROVIDERS[provider_id].status().available:
        return None, provider_id, model
    return get_provider(provider_id), provider_id, model


def run_spreadsheet_task(message_id, workflow_id, attachments, request, provider_id, model):
    """Run a file workflow without a model: suggest the columns, run the skill, check every number against an
    independent recomputation. If it fails, repair it: the automatic fixes first, then a model rewrite."""
    workflow = WORKFLOWS[workflow_id]
    filename, attachment = next(iter(attachments.items()))
    headers, rows = parse_csv(attachment["content"])
    add_step(message_id, "spreadsheet", f"A spreadsheet task: {workflow.title.lower()} on {filename} "
             f"({len(rows)} rows). No model is needed to plan it.", {"workflow": workflow_id})
    mapping = suggest_mapping(workflow_id, headers, rows, request)
    missing = [role.label.lower() for role in workflow.roles if role.required and not mapping.get(role.name)]
    if missing:
        raise NeedsInput(f"Which column holds the {' and the '.join(missing)}? {filename} has: {', '.join(headers)}. "
                         f"Reply with the request and the column, for example: \"{workflow.example[:-1]} using "
                         f"{headers[-1]}.\"")
    mapping = validate_columns(workflow_id, headers, rows, mapping)
    if mapping:
        add_step(message_id, "columns", f"Using {describe_mapping(workflow_id, mapping)}.", {"columns": mapping})
    with SessionLocal() as db:
        skill = latest_validated(db, workflow_id, TURN_WORKSPACE.get())
        if skill is None:
            raise ValueError(f"No skill is registered for {workflow.title.lower()}. Run the starter-skill setup.")
        key = (skill.skill_id, skill.version)
    provider, author_id, author_model = spreadsheet_author(provider_id, model, workflow_id)
    extracted = {f"{role}_column": header for role, header in mapping.items()}
    return reuse_or_repair(message_id, provider, author_id, author_model, key, extracted, {}, workflow.about, request,
                           {workflow.file_input: attachment["content"]}, model_check=False)


def run_turn(conversation_id, assistant_id, provider_id, model, allowed=None):
    """Answer one chat message using only the `allowed` model providers (None: all of them), seeing only the
    shared skills and this conversation's workspace's own."""
    with SessionLocal() as db:
        conversation = db.get(Conversation, conversation_id)
        workspace_id = conversation.workspace_id if conversation else LOCAL_WORKSPACE_ID
    token = TURN_WORKSPACE.set(workspace_id)
    try:
        with only(allowed):
            _run_turn(conversation_id, assistant_id, provider_id, model)
    finally:
        TURN_WORKSPACE.reset(token)


def _run_turn(conversation_id, assistant_id, provider_id, model):
    try:
        with SessionLocal() as db:
            message = db.get(ChatMessage, assistant_id)
            user = db.scalars(select(ChatMessage).where(ChatMessage.conversation_id == conversation_id,
                                                        ChatMessage.sequence == message.sequence - 1)).one()
            attachments = load_attachments(db, user.id)
            workflow_id = spreadsheet_workflow(user.content)
            if workflow_id and not attachments:  # "now total it by month": use the file attached earlier
                attachments = latest_attachments(db, conversation_id, user.sequence)
            history = history_text(db, conversation_id, user.sequence)
            registry = registry_text(db, with_files=bool(attachments))
        if workflow_id and attachments:
            payload = run_spreadsheet_task(assistant_id, workflow_id, attachments, user.content, provider_id, model)
            finish(assistant_id, content=payload["text"], skill=payload["skill"])
            return
        auto = provider_id == "auto"
        if auto:
            provider_id = scoreboard.pick_planner()
            if provider_id is None:
                raise LLMError("No model is available. Connect Claude, Codex, an API key, or a local model.")
            model = PROVIDERS[provider_id].status().default_model
        planner = get_provider(provider_id)

        add_step(assistant_id, "planning", f"Planning with {planner.label}{' (auto)' if auto else ''}…")
        decision = plan(planner, model, history, registry, user.content, attachments)
        if decision.get("mode") == "clarify":
            add_step(assistant_id, "clarifying", "A value is missing or ambiguous, so asking before doing anything.")
            finish(assistant_id, content=decision["question"], skill={"event": "clarify", "question": decision["question"]})
            return
        if decision.get("mode") != "skill":
            add_step(assistant_id, "answering", "This needs a direct answer, not a skill.")
            files_note = f"\n\nAttached files:\n{attachments_text(attachments)}" if attachments else ""
            reply = planner.complete(f"Conversation so far:\n{history or '(new)'}\n\nUSER: {user.content}{files_note}",
                                     system="You are SkillForge's assistant. Answer clearly and concisely in Markdown.",
                                     model=model)
            finish(assistant_id, content=reply)
            return

        steps = decision["steps"]
        if len(steps) > 1:
            add_step(assistant_id, "pipeline", "A multi-step task: " + " → ".join(s["capability"] for s in steps) + ".",
                     {"steps": [s["capability"] for s in steps]})
        outputs, payloads = [], []
        for index, step in enumerate(steps, start=1):
            label = f"Step {index}/{len(steps)}: " if len(steps) > 1 else ""
            payloads.append(run_step(assistant_id, label, step, outputs, attachments, auto, provider_id, model, user.content))
            outputs.append(payloads[-1]["output"])

        if len(payloads) == 1:
            finish(assistant_id, content=payloads[0]["text"], skill=payloads[0]["skill"])
        else:
            text = "Ran " + " → ".join(f"**{p['skill']['skill_id']} v{p['skill']['version']}**" for p in payloads) + "."
            final = payloads[-1]["skill"]
            finish(assistant_id, content=text, skill={**final, "event": "pipeline",
                                                      "steps": [p["skill"] for p in payloads]})
    except NeedsInput as question:
        add_step(assistant_id, "clarifying", "A value the skill needs is missing, so asking for it.")
        finish(assistant_id, content=str(question), skill={"event": "clarify", "question": str(question)})
    except (LLMError, ValueError) as error:
        add_step(assistant_id, "failed", str(error))
        finish(assistant_id, content=f"I couldn't complete this: {error}", status="failed")
    except Exception as error:  # never leave a message pending
        add_step(assistant_id, "failed", "Unexpected error.", {"type": type(error).__name__})
        finish(assistant_id, content="Something went wrong while handling this message.", status="failed")
        raise


def run_step(message_id, label, step, outputs, attachments, auto, provider_id, model, request):
    capability, summary, input_types = step["capability"], step["summary"], step["input_types"]
    inputs = resolve_refs(step["inputs"], outputs)
    files = bind_files(step["files"], attachments) if step["files"] else {}
    add_step(message_id, "planned", f"{label}a reusable skill: {capability}.", {"capability": capability, "inputs": inputs})

    match = discover_capability(message_id, capability, inputs, files, request)
    capability, inputs = match.capability, match.inputs
    confirmed_by_model = match.how == "model"

    with SessionLocal.begin() as db:
        workspace = TURN_WORKSPACE.get()
        skill = latest_validated(db, capability, workspace)
        if skill is not None and needs_files(skill.contract_json) and not files:
            capability, skill = f"{capability}_text", latest_validated(db, f"{capability}_text", workspace)
        existing = (skill.skill_id, skill.version) if skill else None

    provider = get_provider(provider_id)
    if auto:
        routed, reason = scoreboard.route_author(capability)
        if routed:
            provider_id, provider = routed, get_provider(routed)
            model = provider.status().default_model
            add_step(message_id, "routed", f"Auto-routing: {provider.label}. {reason}", {"provider": routed})

    def attempt(author, author_id, author_model):
        if existing:
            try:
                return reuse_or_repair(message_id, author, author_id, author_model, existing, inputs, input_types,
                                       summary, request, files, allow_repair=not confirmed_by_model)
            except MatchMismatch as mismatch:
                add_step(message_id, "match_rejected", f"{mismatch} Building a new skill instead.")
                original = step["capability"]
                return create(message_id, author, author_id, author_model, original, summary, resolve_refs(step["inputs"], outputs),
                              input_types, request, files)
        return create(message_id, author, author_id, author_model, capability, summary, inputs, input_types, request, files)

    try:
        outcome = attempt(provider, provider_id, model)
    except SmithExhausted:
        stronger = next((p for p in STRENGTH_ORDER[:STRENGTH_ORDER.index(provider_id)]
                         if p != LOCAL and PROVIDERS[p].status().available), None)
        if stronger is None:
            raise
        add_step(message_id, "escalating", f"{provider.label} could not produce a proven skill. "
                 f"Escalating to {PROVIDERS[stronger].label}.")
        scoreboard.record(provider_id, "author", "escalated", model=model, capability=capability)
        outcome = attempt(PROVIDERS[stronger], stronger, PROVIDERS[stronger].status().default_model)
    outcome["output"] = outcome["skill"]["output"]
    return outcome


def discover_capability(message_id, capability, inputs, files, request):
    """Find an existing skill for this operation before creating one (see services/discovery.py)."""
    with SessionLocal() as db:
        rows = db.scalars(select(SkillVersion).where(visible_to(TURN_WORKSPACE.get()), SkillVersion.status == "validated",
                                                     SkillVersion.contract_json.is_not(None))).all()
    skills = {}
    for row in rows:
        if needs_files(row.contract_json) and not files:
            continue
        skills.setdefault(row.capability, {"summary": row.contract_json.get("summary", ""),
                                           "inputs": [f["name"] for f in row.contract_json.get("inputs", [])]})
    # Only a strong model may confirm a close match; with none available, a close call creates a new skill.
    confirmer = next((PROVIDERS[p] for p in STRENGTH_ORDER if p != LOCAL and PROVIDERS[p].status().available), None)
    match = discover(capability, inputs, skills, provider=confirmer,
                     model=confirmer.status().default_model if confirmer else None, request=request)
    if match.how in ("names", "model"):
        add_step(message_id, "discovered", f"Reusing {match.capability} for {capability}: {match.reason}",
                 {"planned": capability, "matched": match.capability, "how": match.how})
    return match


def reply_payload(skill, output, event):
    return {"skill_id": skill.skill_id, "version": skill.version, "capability": skill.capability,
            "origin": skill.origin, "parent_version": skill.parent_version, "event": event, "output": output,
            "contract": skill.contract_json}


def pick_judge(author_id, author_model):
    """Prefer a different, strong model as the verifier, so the author never grades its own work. The local
    model never judges a cloud model; without another strong model available the author checks itself."""
    for candidate in STRENGTH_ORDER:
        if candidate in (author_id, LOCAL) or not PROVIDERS[candidate].status().available:
            continue
        return PROVIDERS[candidate], PROVIDERS[candidate].status().default_model
    return get_provider(author_id), author_model


def make_judge(author_id, author_model):
    provider, model = pick_judge(author_id, author_model)

    def judge(request, capability, inputs, output, contract=None):
        return verify_output(provider, model, request, capability, inputs, output, contract)
    judge.label, judge.provider_id, judge.author_id = provider.label, provider.id, author_id
    return judge


def make_verifier(message_id, judge, request, capability):
    def check(inputs, output, files=None, contract=None):
        view = verifier_view(inputs, files)
        if view is None:
            add_step(message_id, "verify_skipped", "The file is too large for a model to recompute by hand; "
                     "relying on the contract checks and the worked examples.")
            return True, "skipped (large file)"
        add_step(message_id, "verifying", f"Independent verifier ({judge.label}) is recomputing the answer…")
        correct, reason = judge(request, capability, view, output, contract)
        add_step(message_id, "verified" if correct else "verify_failed",
                 "Verifier agrees with the output." if correct else f"Verifier disagrees: {reason}")
        scoreboard.record(judge.provider_id, "verifier", "agreed" if correct else "disagreed", capability=capability)
        if not correct:
            scoreboard.record(judge.author_id, "author", "overruled", capability=capability)
        return correct, reason
    return check


def reuse_or_repair(message_id, provider, provider_id, model, key, extracted, input_types, summary, request, files=None,
                    allow_repair=True, model_check=True):
    """Run a stored skill; if it fails, repair it (automatic fixes first, then a model rewrite) and save the new
    version. model_check=False trusts the contract checks alone (spreadsheet tasks, whose checks recompute the
    whole answer), so no model is needed unless the skill has to be rewritten."""
    files = files or {}
    with SessionLocal.begin() as db:
        skill = db.get(SkillVersion, key)
        if not can_see(skill, TURN_WORKSPACE.get()):
            raise ValueError(f"{key[0]} v{key[1]} is not available in this workspace.")
        contract = verify(skill)
        source = skill.source_code
    add_step(message_id, "skill_selected", f"Found {skill.skill_id} v{skill.version} in the registry. Running it in the sandbox.")
    inputs = bind_chat_inputs(contract, extracted, files)
    run = run_skill(source, inputs=inputs, files=files, tools=contract.tools)
    failure = None if run.ok else f"{run.error.get('type')}: {run.error.get('message')}"
    typed_failure = None if run.ok else classify_run_error(run.error)
    judge = make_judge(provider_id, model) if provider is not None else None
    if model_check and judge is not None:
        verifier = make_verifier(message_id, judge, request, skill.capability)
    else:
        def verifier(*_args, **_kwargs):
            return True, "the contract checks"
    if run.ok:
        try:
            run_checks(contract, files, inputs, run.output)
            correct, reason = verifier(inputs, run.output, files, skill.contract_json)
            if not correct:
                failure = f"wrong answer {json.dumps(run.output)}: {reason}"
        except CheckFailed as error:
            failure, typed_failure = str(error), classify_check(error)
    if failure is not None and run.ok and typed_failure is None and model_check and provider is not None:
        # The verifier says the answer is wrong. Often the skill is fine and an input was bound wrong
        # (an optional flag the planner missed): re-bind from the full contract before touching code.
        strong = next((PROVIDERS[p] for p in STRENGTH_ORDER if p != LOCAL and PROVIDERS[p].status().available), provider)
        rebound = rebind_inputs(strong, strong.status().default_model if strong is not provider else model,
                                request, skill.contract_json, inputs, failure)
        if rebound is not None:
            add_step(message_id, "rebinding", f"Re-read the request against the skill's inputs: {json.dumps(rebound)}.",
                     {"inputs": rebound})
            rerun = run_skill(source, inputs=rebound, files=files, tools=contract.tools)
            if rerun.ok:
                try:
                    run_checks(contract, files, rebound, rerun.output)
                    correct, reason = verifier(rebound, rerun.output, files, skill.contract_json)
                except CheckFailed as error:
                    correct, reason = False, str(error)
                if correct:
                    run, inputs, failure = rerun, rebound, None
                else:
                    failure = f"wrong answer {json.dumps(rerun.output)} even after re-binding inputs: {reason}"

    if failure is None:
        add_step(message_id, "skill_ran", f"Done in {run.duration_ms:g} ms. Reused v{skill.version}, no new code needed.")
        creator = (skill.change_json or {}).get("created_by") or (skill.change_json or {}).get("provider")
        if creator:
            scoreboard.record(creator, "author", "reused", capability=skill.capability)
        return {"text": f"Reused **{skill.skill_id} v{skill.version}**.", "skill": reply_payload(skill, run.output, "reused")}

    add_step(message_id, "skill_failed", f"v{skill.version} failed on this input: {failure}")
    if not allow_repair:
        raise MatchMismatch(f"{skill.skill_id} looked like the same operation but failed on this input ({failure}).")

    # Deterministic strategies first (cheap, no model): e.g. export-formatted amounts in a CSV.
    if typed_failure is not None:
        with SessionLocal.begin() as db:
            parent = db.get(SkillVersion, key)
            emit = lambda kind, _stage, text, payload=None: add_step(message_id, kind, text, payload)  # noqa: E731
            repaired = attempt_repair(db, emit, parent, inputs, files, typed_failure, settings.repair_budget,
                                      actor=f"agent:{provider_id}", workspace_id=workspace_of(db, message_id))
            if isinstance(repaired, Repaired):
                new_key = (repaired.skill.skill_id, repaired.skill.version)
                output = repaired.output
        if isinstance(repaired, Repaired):
            with SessionLocal() as db:
                new = db.get(SkillVersion, new_key)
                return {"text": f"Repaired **{new.skill_id}** and saved **v{new.version}**.",
                        "skill": reply_payload(new, output, "repaired")}

    if provider is None:
        raise ValueError(f"{skill.skill_id} v{skill.version} failed ({failure}). The automatic fixes didn't work, and "
                         "no AI model is connected to rewrite it.")
    add_step(message_id, "rewriting", f"The automatic fixes didn't work. {provider.label} will rewrite the skill "
             "and test it again.")
    if not model_check:
        verifier = make_verifier(message_id, judge, request, skill.capability)
    new_source, new_contract, examples, evidence, output = smith(
        message_id, provider, model, skill.capability, summary, inputs, input_types, existing=source,
        verifier=verifier, feedback=f"The current version failed: {failure}", judge=judge, files=files)
    if [f["name"] for f in new_contract["inputs"]] != [f.name for f in contract.inputs]:
        raise ValueError("The repair changed the skill's inputs, so it cannot replace this version.")
    with SessionLocal.begin() as db:
        parent = db.get(SkillVersion, key)
        retired = retired_duplicate(db, parent.skill_id, new_source, new_contract)
        if retired is not None:
            raise ValueError(f"The repair is identical to v{retired.version}, which a reviewer retired. Review it instead.")
        regression = lineage_fixtures(db, parent)
        evidence = run_fixture_tests(new_source, new_contract, regression + examples)
        stored_files = files if sum(len(v) for v in files.values()) <= 256 * 1024 else {}
        fixtures = examples + ([(f"regression_input_{parent.version}", inputs, stored_files, "checks")]
                               if stored_files or not files else [])
        new = promote(db, parent, new_source, new_contract, {**evidence, "repaired_from": parent.version}, {
            "strategy": "skillsmith_llm", "summary": f"Rewritten by {provider.label} after: {failure}",
            "failure": {"code": "SKILL_ERROR", "message": failure}, "provider": provider_id, "model": model,
            "fixtures": [encode_fixture(*f) for f in fixtures],
        }, actor=f"agent:{provider_id}", workspace_id=workspace_of(db, message_id))
        new_key = (new.skill_id, new.version)
    add_step(message_id, "skill_promoted", f"Saved {new_key[0]} v{new_key[1]} (repaired from v{key[1]}), "
             f"proven by {evidence['test_count']} tests.")
    with SessionLocal() as db:
        new = db.get(SkillVersion, new_key)
        return {"text": f"Repaired **{new.skill_id}** and saved **v{new.version}**.", "skill": reply_payload(new, output, "repaired")}


def create(message_id, provider, provider_id, model, capability, summary, inputs, input_types, request, files=None):
    add_step(message_id, "no_skill", f"No skill can do {capability} yet. SkillSmith will create one.")
    judge = make_judge(provider_id, model)
    verifier = make_verifier(message_id, judge, request, capability)
    source, contract, examples, evidence, output = smith(message_id, provider, model, capability, summary, inputs,
                                                         input_types, verifier=verifier, judge=judge, files=files)
    skill_id = capability
    with SessionLocal.begin() as db:
        fingerprint = implementation_hash(source, contract)
        taken = db.scalars(select(SkillVersion.version).where(SkillVersion.skill_id == skill_id)).all()
        version = "1.0.0" if not taken else f"{max(version_key(v) for v in taken)[0] + 1}.0.0"
        row = db.get(SkillVersion, (skill_id, version))
        if row is None:
            row = SkillVersion(skill_id=skill_id, version=version, capability=capability, status="validated",
                               implementation_hash=fingerprint, validation_json=evidence, source_code=source,
                               contract_json=contract, origin="generated",
                               workspace_id=owner_for(TURN_WORKSPACE.get()), change_json=shareable_change({
                                   "created_by": provider_id, "model": model, "request": request[:500],
                                   "fixtures": [encode_fixture(*e) for e in examples],
                               }, TURN_WORKSPACE.get()))
            db.add(row)
            db.flush()
            audit.record(db, actor=f"agent:{provider_id}", action="skill.promoted",
                         target=audit.skill_target(skill_id, version),
                         reason=f"Created by SkillSmith for: {request[:300]}",
                         details={"origin": "generated", "model": model, "tests": evidence.get("test_count"),
                                  "implementation_hash": fingerprint},
                         **({"workspace_id": ws} if (ws := workspace_of(db, message_id)) else {}))
        key = (row.skill_id, row.version)
    add_step(message_id, "skill_created", f"Created {key[0]} v{key[1]}: passed {evidence['test_count']} examples in the sandbox. "
             "Saved to the registry for reuse.")
    with SessionLocal() as db:
        row = db.get(SkillVersion, key)
        return {"text": f"Created a new skill, **{row.skill_id} v{row.version}**, and ran it.",
                "skill": reply_payload(row, output, "created")}
