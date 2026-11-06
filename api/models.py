import re
from typing import Literal
from pydantic import BaseModel, field_validator

VALID_STATES = {"created", "ready", "running", "succeeded", "failed", "deleted"}
SANDBOX_REGEX = re.compile(r"^sbx-[a-z0-9]{8,}$")

class RunCreate(BaseModel):
    run_id: str
    sandbox_name: str
    problem_id: str
    state: str
    execution_target: str

    @field_validator("sandbox_name")
    @classmethod
    def validate_sandbox_name(cls, v: str) -> str:
        if not SANDBOX_REGEX.match(v):
            raise ValueError(f"sandbox_name '{v}' must match pattern '^sbx-[a-z0-9]{{8,}}$'")
        return v

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        if v not in VALID_STATES:
            raise ValueError(f"state '{v}' must be one of {VALID_STATES}")
        return v

    @field_validator("execution_target")
    @classmethod
    def validate_execution_target(cls, v: str) -> str:
        if v != "celesto_sandbox":
            raise ValueError(f"execution_target must be exactly 'celesto_sandbox', got '{v}'")
        return v

class RunResponse(BaseModel):
    run_id: str
    sandbox_name: str
    problem_id: str
    state: str
    execution_target: str
    created_at: str | None = None

