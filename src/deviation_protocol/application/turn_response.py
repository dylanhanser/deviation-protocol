from __future__ import annotations

from typing import Any, Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from deviation_protocol.application.dynamic_narrative_models import (
    DYNAMIC_LEGACY_PROMPT_SCHEMA_VERSION,
    DYNAMIC_PROMPT_SCHEMA_VERSION,
)
from deviation_protocol.application.narrative_jobs import (
    LOCAL_TEMPLATE_PROMPT_SCHEMA_VERSION,
    NarrativeJob,
    NarrativeJobStatus,
)
from deviation_protocol.application.resolution import ResolutionStatus
from deviation_protocol.domain.json_values import freeze_json_object
from deviation_protocol.domain.narrative import NarrativeFrame
from deviation_protocol.domain.narrative_outcome import NarrativeOutcomeResult


StableId = Annotated[str, Field(strict=True, min_length=1, max_length=64)]
StableCode = Annotated[
    str,
    Field(strict=True, pattern=r"^[A-Z][A-Z0-9_]{0,127}$"),
]
StrictBool = Annotated[bool, Field(strict=True)]
_DYNAMIC_COMMITTED_CODE = "DYNAMIC_NARRATIVE_COMMITTED"
_DYNAMIC_PROMPT_SCHEMA_PREFIX = "dynamic-narrative-prompt-"
_DYNAMIC_OUTCOME_RESULTS = frozenset(item.value for item in NarrativeOutcomeResult)


class CommittedTurnResponseValidationError(ValueError):
    """Sanitized internal failure for contradictory persisted recovery data."""

    def __init__(self) -> None:
        super().__init__("stored committed response violates its trusted schema")


class TurnResponse(BaseModel):
    """Strict, persistence-safe result returned by the turn application boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: StableId
    client_request_id: StableId
    action_signature: Annotated[
        str,
        Field(strict=True, pattern=r"^[0-9a-f]{64}$"),
    ]
    resolution_kind: ResolutionStatus
    result_code: StableCode
    feedback_code: StableCode
    feedback_parameters: dict[str, Any] = Field(default_factory=dict)
    resulting_state_version: Annotated[int, Field(strict=True, ge=0)]
    state_changed: StrictBool
    narrative_required: StrictBool
    narrative_pending: StrictBool
    narrative_frame: NarrativeFrame | None = None
    narrative_text: Annotated[str, Field(strict=True, min_length=1, max_length=10_000)] | None = None
    narrative_status: Annotated[
        str, Field(strict=True, pattern=r"^(PENDING|COMMITTED)$")
    ] | None = None
    local_query_result: dict[str, Any] | None = None

    @field_validator("feedback_parameters", "local_query_result")
    @classmethod
    def freeze_json_objects(
        cls, value: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        if value is None:
            return None
        return freeze_json_object(value, path="turn response JSON")

    @model_validator(mode="after")
    def validate_resolution_shape(self) -> TurnResponse:
        is_narrative = self.resolution_kind in {
            ResolutionStatus.NARRATIVE_REQUIRED,
            ResolutionStatus.NARRATIVE_COMMITTED,
        }
        if self.resolution_kind is ResolutionStatus.ANOMALY_EVALUATION_REQUIRED:
            raise ValueError("anomaly evaluation is not supported by the turn response")
        expected_pending = self.resolution_kind is ResolutionStatus.NARRATIVE_REQUIRED
        if expected_pending and self.narrative_status is None:
            # Backward-compatible construction for in-process deterministic
            # adapters; persisted/API output always includes the explicit state.
            object.__setattr__(self, "narrative_status", "PENDING")
        if self.narrative_required != is_narrative or self.narrative_pending != expected_pending:
            raise ValueError("narrative flags must match resolution_kind")
        if self.state_changed and self.resolution_kind not in {
            ResolutionStatus.RESOLVED_LOCAL,
            ResolutionStatus.NARRATIVE_COMMITTED,
        }:
            raise ValueError("only a committed resolution may report a state change")
        if is_narrative:
            expected_status = "PENDING" if expected_pending else "COMMITTED"
            if self.narrative_status != expected_status:
                raise ValueError("narrative status does not match resolution kind")
            if (self.narrative_text is not None) != (
                self.resolution_kind is ResolutionStatus.NARRATIVE_COMMITTED
            ):
                raise ValueError("narrative text is visible only after commit")
        elif self.narrative_status is not None:
            raise ValueError("non-narrative response cannot carry narrative status")
        elif self.narrative_text is not None and not (
            self.resolution_kind is ResolutionStatus.RESOLVED_LOCAL
            and self.state_changed
        ):
            raise ValueError(
                "only a state-changing local response may carry fixed server narrative"
            )
        if self.local_query_result is not None and (
            self.resolution_kind is not ResolutionStatus.RESOLVED_LOCAL
            or self.state_changed
        ):
            raise ValueError("local_query_result is only valid for a local query")
        is_local_query = (
            self.resolution_kind is ResolutionStatus.RESOLVED_LOCAL
            and not self.state_changed
        )
        if is_local_query and self.local_query_result is None:
            raise ValueError("a local query must preserve its result")
        if is_local_query and self.local_query_result != self.feedback_parameters:
            raise ValueError("local query result must match feedback parameters")
        return self

    def to_persistence(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


def validate_committed_turn_response_for_recovery(
    response: TurnResponse,
    job: NarrativeJob | None,
    *,
    stored_turn_id: str,
) -> TurnResponse:
    """Validate one parsed commitment against its trusted durable schema epoch."""

    if not isinstance(response, TurnResponse):
        raise CommittedTurnResponseValidationError()

    if job is None:
        if (
            response.result_code == _DYNAMIC_COMMITTED_CODE
            or response.feedback_code == _DYNAMIC_COMMITTED_CODE
        ):
            raise CommittedTurnResponseValidationError()
        return response
    if not isinstance(job, NarrativeJob):
        raise CommittedTurnResponseValidationError()
    if (
        type(stored_turn_id) is not str
        or job.session_id != response.session_id
        or job.turn_id != stored_turn_id
        or job.client_request_id != response.client_request_id
        or job.action_signature != response.action_signature
    ):
        raise CommittedTurnResponseValidationError()

    prompt_schema_version = job.prompt_schema_version
    if prompt_schema_version == LOCAL_TEMPLATE_PROMPT_SCHEMA_VERSION:
        if (
            response.result_code == _DYNAMIC_COMMITTED_CODE
            or response.feedback_code == _DYNAMIC_COMMITTED_CODE
        ):
            raise CommittedTurnResponseValidationError()
        return response
    if prompt_schema_version not in {
        DYNAMIC_LEGACY_PROMPT_SCHEMA_VERSION,
        DYNAMIC_PROMPT_SCHEMA_VERSION,
    }:
        if (
            prompt_schema_version.startswith(_DYNAMIC_PROMPT_SCHEMA_PREFIX)
            or response.result_code == _DYNAMIC_COMMITTED_CODE
            or response.feedback_code == _DYNAMIC_COMMITTED_CODE
        ):
            raise CommittedTurnResponseValidationError()
        return response

    if (
        job.status is not NarrativeJobStatus.COMMITTED
        or response.resolution_kind is not ResolutionStatus.NARRATIVE_COMMITTED
        or response.state_changed is not True
        or response.narrative_required is not True
        or response.narrative_pending is not False
        or response.narrative_status != "COMMITTED"
        or response.narrative_text is None
        or response.result_code != _DYNAMIC_COMMITTED_CODE
        or response.feedback_code != _DYNAMIC_COMMITTED_CODE
    ):
        raise CommittedTurnResponseValidationError()

    expected_feedback_keys = {"outcome_result"}
    if prompt_schema_version == DYNAMIC_PROMPT_SCHEMA_VERSION:
        expected_feedback_keys.add("public_fact_count")
    if set(response.feedback_parameters) != expected_feedback_keys:
        raise CommittedTurnResponseValidationError()

    outcome_result = response.feedback_parameters["outcome_result"]
    if type(outcome_result) is not str or outcome_result not in _DYNAMIC_OUTCOME_RESULTS:
        raise CommittedTurnResponseValidationError()

    if prompt_schema_version == DYNAMIC_PROMPT_SCHEMA_VERSION:
        public_fact_count = response.feedback_parameters["public_fact_count"]
        if (
            type(public_fact_count) is not int
            or not 0 <= public_fact_count <= 3
        ):
            raise CommittedTurnResponseValidationError()
    return response
