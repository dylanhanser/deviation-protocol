from __future__ import annotations

import unicodedata
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from deviation_protocol.application.turn_response import TurnResponse
from deviation_protocol.domain.actions import ActionSubmission, ActionType
from deviation_protocol.domain.narrative import NarrativeFrame


SafeId64 = Annotated[
    str,
    Field(
        strict=True,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$",
    ),
]
SafeId128 = Annotated[
    str,
    Field(
        strict=True,
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$",
    ),
]


class StrictApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("*", mode="before")
    @classmethod
    def reject_unicode_controls(cls, value: object) -> object:
        values: tuple[object, ...]
        if isinstance(value, (list, tuple, set, frozenset)):
            values = tuple(value)
        else:
            values = (value,)
        for item in values:
            if isinstance(item, str) and any(
                unicodedata.category(character) in {"Cc", "Cf"} for character in item
            ):
                raise ValueError("Unicode control characters are not allowed")
        return value


class CreateSessionRequest(StrictApiModel):
    client_request_id: SafeId64
    character_definition_id: SafeId128
    scenario_id: SafeId128


class ActionRequest(StrictApiModel):
    turn_id: SafeId64
    client_request_id: SafeId64
    action_type: ActionType
    target_ids: tuple[SafeId128, ...] = Field(default=(), max_length=16)
    tool_ids: tuple[SafeId128, ...] = Field(default=(), max_length=16)
    description: Annotated[str, Field(strict=True, min_length=1, max_length=150)] | None = None
    dialogue: Annotated[str, Field(strict=True, min_length=1, max_length=200)] | None = None
    decision_id: SafeId128 | None = None
    choice_id: SafeId128 | None = None
    item_instance_id: SafeId128 | None = None
    equipment_slot_id: SafeId128 | None = None
    skill_definition_id: SafeId128 | None = None

    def to_submission(self, session_id: str) -> ActionSubmission:
        return ActionSubmission(
            session_id=session_id,
            **self.model_dump(),
        )


class ActionResponse(BaseModel):
    """Player-safe action result without persistence-only integrity fields."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: SafeId64
    client_request_id: SafeId64
    resolution_kind: Literal[
        "RESOLVED_LOCAL",
        "REJECTED_LOCAL",
        "NARRATIVE_REQUIRED",
        "NARRATIVE_COMMITTED",
    ]
    result_code: str
    feedback_code: str
    feedback_parameters: dict[str, Any] = Field(default_factory=dict)
    resulting_state_version: int = Field(ge=0)
    state_changed: bool
    narrative_required: bool
    narrative_pending: bool
    narrative_frame: NarrativeFrame | None = None
    narrative_text: str | None = Field(default=None, min_length=1, max_length=10_000)
    narrative_status: Literal["PENDING", "COMMITTED"] | None = None
    local_query_result: dict[str, Any] | None = None

    @classmethod
    def from_turn_response(cls, response: TurnResponse) -> ActionResponse:
        return cls.model_validate(
            response.model_dump(mode="json", exclude={"action_signature"})
        )


class ErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")
    error_code: str
    message: str


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    error: ErrorDetail
