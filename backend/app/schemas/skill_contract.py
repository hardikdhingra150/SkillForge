"""The contract every stored skill declares: what it needs, returns and may use."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.sandbox.tools import TOOL_NAMES
from app.services.checks import CHECKS

Identifier = Field(pattern=r"^[a-z][a-z0-9_]{0,59}$")


class ContractField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Identifier
    # csv: a confirmed CSV input; column: a header name bound from the confirmed mapping.
    type: Literal["csv", "column", "text", "integer", "decimal_string", "list", "object"]
    required: bool = True
    description: str = Field(default="", max_length=300)


class SkillContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    capability: str = Identifier
    summary: str = Field(min_length=1, max_length=300)
    entrypoint: Literal["run"] = "run"
    inputs: list[ContractField] = Field(min_length=1, max_length=20)
    outputs: list[ContractField] = Field(min_length=1, max_length=20)
    tools: list[str] = Field(max_length=len(TOOL_NAMES))
    checks: list[str] = Field(min_length=1, max_length=10)

    @field_validator("inputs", "outputs")
    @classmethod
    def unique_names(cls, fields):
        names = [field.name for field in fields]
        if len(set(names)) != len(names):
            raise ValueError("Field names must be unique.")
        return fields

    @field_validator("tools")
    @classmethod
    def known_tools(cls, tools):
        unknown = sorted(set(tools) - set(TOOL_NAMES))
        if unknown or len(set(tools)) != len(tools):
            raise ValueError(f"Tools must be unique and approved; unknown: {unknown}.")
        return tools

    @field_validator("checks")
    @classmethod
    def known_checks(cls, checks):
        unknown = sorted(set(checks) - set(CHECKS))
        if unknown:
            raise ValueError(f"Unknown checks: {unknown}.")
        return checks
