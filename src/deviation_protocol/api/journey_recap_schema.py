"""Closed companion read contract; existing Journey DTOs remain unchanged."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from deviation_protocol.api.schemas import SafeId64, SafeId128


class RecapContext(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    run_id: SafeId128
    run_state_version: int = Field(ge=1, le=2**53 - 1)
    session_state_version: int = Field(ge=0, le=2**53 - 1)
    scenario_id: SafeId128
    content_version: SafeId128
    cutoff_visit: int = Field(ge=1, le=3)
    scope: Literal["current", "historical"]
    lifecycle_at_cutoff: Literal["active", "completed", "terminated"]


class JourneyRecapResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["native-run-recap/v1"]
    session_id: SafeId64
    context: RecapContext | None
    status: Literal["complete", "incomplete", "unavailable_evidence", "unavailable_overflow"]
    text: str = Field(max_length=2000)

    @model_validator(mode="after")
    def validate_result(self):
        if self.status in ("complete", "incomplete"):
            if self.context is None or not self.text:
                raise ValueError("available recap requires context and text")
        elif self.text:
            raise ValueError("unavailable recap cannot carry partial text")
        if self.status == "unavailable_overflow" and self.context is None:
            raise ValueError("overflow requires validated context")
        if self.context and self.context.scope == "historical" and self.context.lifecycle_at_cutoff != "active":
            raise ValueError("later terminal status cannot enter historical cutoff")
        return self
