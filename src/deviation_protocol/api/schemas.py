from __future__ import annotations

import unicodedata
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from deviation_protocol.application.turn_response import TurnResponse
from deviation_protocol.application.session_service import (
    NarrativeRequestStatusResult,
    PublicNarrativeRequestStatus,
    NarrativeRequestClientAction,
)
from deviation_protocol.domain.actions import (
    MAX_ACTION_DESCRIPTION_LENGTH,
    MAX_ACTION_DIALOGUE_LENGTH,
    ActionSubmission,
    ActionType,
)
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
    description: Annotated[
        str,
        Field(strict=True, min_length=1, max_length=MAX_ACTION_DESCRIPTION_LENGTH),
    ] | None = None
    dialogue: Annotated[
        str,
        Field(strict=True, min_length=1, max_length=MAX_ACTION_DIALOGUE_LENGTH),
    ] | None = None
    decision_id: SafeId128 | None = None
    choice_id: SafeId128 | None = None
    item_instance_id: SafeId128 | None = None
    equipment_slot_id: SafeId128 | None = None
    skill_definition_id: SafeId128 | None = None

    @model_validator(mode="after")
    def validate_continue_payload(self) -> ActionRequest:
        if self.action_type is not ActionType.CONTINUE:
            return self
        payload_fields = {
            "target_ids",
            "tool_ids",
            "description",
            "dialogue",
            "decision_id",
            "choice_id",
            "item_instance_id",
            "equipment_slot_id",
            "skill_definition_id",
        }
        if self.model_fields_set.intersection(payload_fields):
            raise ValueError("CONTINUE does not accept an action payload")
        return self

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
        return cls(
            session_id=response.session_id,
            client_request_id=response.client_request_id,
            resolution_kind=response.resolution_kind.value,
            result_code=response.result_code,
            feedback_code=response.feedback_code,
            feedback_parameters=dict(response.feedback_parameters),
            resulting_state_version=response.resulting_state_version,
            state_changed=response.state_changed,
            narrative_required=response.narrative_required,
            narrative_pending=response.narrative_pending,
            narrative_frame=response.narrative_frame,
            narrative_text=response.narrative_text,
            narrative_status=response.narrative_status,
            local_query_result=(
                dict(response.local_query_result)
                if response.local_query_result is not None
                else None
            ),
        )


class NarrativeRequestStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: SafeId64
    client_request_id: SafeId64
    status: PublicNarrativeRequestStatus
    client_action: NarrativeRequestClientAction
    error_code: Annotated[
        str, Field(strict=True, pattern=r"^[A-Z][A-Z0-9_]{0,127}$")
    ] | None = None
    retry_after_seconds: int | None = Field(default=None, ge=1, le=60)
    response: ActionResponse | None = None

    @model_validator(mode="after")
    def validate_status_shape(self) -> NarrativeRequestStatusResponse:
        if self.status is PublicNarrativeRequestStatus.PENDING:
            valid = (
                self.client_action is NarrativeRequestClientAction.POLL_SAME_REQUEST
                and self.retry_after_seconds is not None
                and self.error_code is None
                and self.response is None
            )
        elif self.status is PublicNarrativeRequestStatus.COMMITTED:
            valid = (
                self.client_action
                is NarrativeRequestClientAction.RESPONSE_AVAILABLE
                and self.response is not None
                and self.retry_after_seconds is None
                and self.error_code is None
            )
        else:
            expected = {
                PublicNarrativeRequestStatus.STALE: (
                    NarrativeRequestClientAction.REFRESH_VIEW,
                    "NARRATIVE_REQUEST_STALE",
                ),
                PublicNarrativeRequestStatus.OUTCOME_UNKNOWN: (
                    NarrativeRequestClientAction.DO_NOT_RETRY,
                    "NARRATIVE_OUTCOME_UNKNOWN",
                ),
                PublicNarrativeRequestStatus.FAILED: (
                    NarrativeRequestClientAction.DO_NOT_RETRY,
                    "NARRATIVE_REQUEST_FAILED",
                ),
            }[self.status]
            valid = (
                (self.client_action, self.error_code) == expected
                and self.retry_after_seconds is None
                and self.response is None
            )
        if not valid:
            raise ValueError("narrative request status response has an invalid shape")
        return self

    @classmethod
    def from_application_result(
        cls, result: NarrativeRequestStatusResult
    ) -> NarrativeRequestStatusResponse:
        return cls(
            session_id=result.session_id,
            client_request_id=result.client_request_id,
            status=result.status,
            client_action=result.client_action,
            error_code=result.error_code,
            retry_after_seconds=result.retry_after_seconds,
            response=(
                ActionResponse.from_turn_response(result.response)
                if result.response is not None
                else None
            ),
        )


class ErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")
    error_code: str
    message: str


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    error: ErrorDetail
