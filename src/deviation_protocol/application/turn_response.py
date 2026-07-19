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
        is_narrative = self.resolution_kind is ResolutionStatus.NARRATIVE_REQUIRED
        if self.resolution_kind is ResolutionStatus.ANOMALY_EVALUATION_REQUIRED:
            raise ValueError("anomaly evaluation is not supported by the turn response")
        if self.narrative_required != is_narrative or self.narrative_pending != is_narrative:
            raise ValueError("narrative flags must match resolution_kind")
        if self.state_changed and self.resolution_kind is not ResolutionStatus.RESOLVED_LOCAL:
            raise ValueError("only RESOLVED_LOCAL may report a state change")
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
