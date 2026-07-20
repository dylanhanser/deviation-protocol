from __future__ import annotations

from typing import Any, Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from deviation_protocol.application.resolution import ResolutionStatus
from deviation_protocol.domain.json_values import freeze_json_object
from deviation_protocol.domain.narrative import NarrativeFrame


StableId = Annotated[str, Field(strict=True, min_length=1, max_length=64)]
StableCode = Annotated[
    str,
    Field(strict=True, pattern=r"^[A-Z][A-Z0-9_]{0,127}$"),
]
StrictBool = Annotated[bool, Field(strict=True)]


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
