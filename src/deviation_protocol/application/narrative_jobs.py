from __future__ import annotations

from datetime import datetime
from enum import StrEnum
import json
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from deviation_protocol.domain.json_values import FrozenJsonDict, freeze_bounded_json_value


MAX_NARRATIVE_JOB_JSON_BYTES = 128_000
LOCAL_TEMPLATE_PROMPT_SCHEMA_VERSION = "local-server-template-v1"
LOCAL_TEMPLATE_PROVIDER_NAME = "local-server"
LOCAL_TEMPLATE_MODEL_NAME = "fixed-decision-template"


class NarrativeJobStatus(StrEnum):
    PREPARED = "PREPARED"
    IN_PROGRESS = "IN_PROGRESS"
    PROPOSAL_VALIDATED = "PROPOSAL_VALIDATED"
    COMMITTED = "COMMITTED"
    # Retained only to deserialize legacy rows. Production orchestration has no
    # transition to this state and exposes it conservatively as terminal failure.
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    FAILED_TERMINAL = "FAILED_TERMINAL"
    STALE = "STALE"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"


ACTIVE_NARRATIVE_JOB_STATUSES = frozenset(
    {
        NarrativeJobStatus.PREPARED,
        NarrativeJobStatus.IN_PROGRESS,
        NarrativeJobStatus.PROPOSAL_VALIDATED,
    }
)


class NarrativeJob(BaseModel):
    """Persistence-safe durable coordination record; never exposed directly by the API."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    job_id: Annotated[str, Field(strict=True, min_length=1, max_length=64)]
    session_id: Annotated[str, Field(strict=True, min_length=1, max_length=64)]
    turn_id: Annotated[str, Field(strict=True, min_length=1, max_length=64)]
    client_request_id: Annotated[str, Field(strict=True, min_length=1, max_length=64)]
    action_signature: Annotated[str, Field(strict=True, pattern=r"^[0-9a-f]{64}$")]
    prepared_state_version: Annotated[int, Field(strict=True, ge=0)]
    state_fingerprint: Annotated[str, Field(strict=True, pattern=r"^[0-9a-f]{64}$")]
    scenario_id: Annotated[str, Field(strict=True, min_length=1, max_length=128)]
    scenario_content_version: Annotated[str, Field(strict=True, min_length=1, max_length=128)]
    request_fingerprint: Annotated[str, Field(strict=True, pattern=r"^[0-9a-f]{64}$")]
    narrative_request: dict[str, Any]
    prompt_schema_version: Annotated[str, Field(strict=True, min_length=1, max_length=64)]
    style_profile_version: Annotated[str, Field(strict=True, min_length=1, max_length=64)]
    provider_name: Annotated[str, Field(strict=True, min_length=1, max_length=64)]
    model_name: Annotated[str, Field(strict=True, min_length=1, max_length=128)]
    status: NarrativeJobStatus = NarrativeJobStatus.PREPARED
    attempt_count: Annotated[int, Field(strict=True, ge=0, le=1)] = 0
    lease_token: Annotated[str, Field(strict=True, min_length=32, max_length=128)] | None = None
    lease_owner: Annotated[str, Field(strict=True, min_length=1, max_length=128)] | None = None
    lease_expires_at: datetime | None = None
    validated_proposal: dict[str, Any] | None = None
    validated_proposal_digest: Annotated[str, Field(strict=True, pattern=r"^[0-9a-f]{64}$")] | None = None
    outcome_rule_id: Annotated[str, Field(strict=True, min_length=1, max_length=128)] | None = None
    accepted_narrative_text: Annotated[str, Field(strict=True, min_length=1, max_length=10_000)] | None = None
    error_code: Annotated[str, Field(strict=True, pattern=r"^[A-Z][A-Z0-9_]{0,127}$")] | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("narrative_request", "validated_proposal")
    @classmethod
    def freeze_json(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return None
        try:
            frozen = freeze_bounded_json_value(
                value,
                path="narrative job JSON",
                allow_floats=False,
                max_depth=24,
                max_collection_items=512,
                max_string_length=10_000,
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(str(exc)) from None
        if not isinstance(frozen, FrozenJsonDict):
            raise TypeError("narrative job JSON must be an object")
        encoded = json.dumps(
            frozen,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        if len(encoded) > MAX_NARRATIVE_JOB_JSON_BYTES:
            raise ValueError("narrative job JSON exceeds the storage boundary")
        return frozen

    @model_validator(mode="after")
    def validate_lifecycle_shape(self) -> NarrativeJob:
        local_template = (
            self.prompt_schema_version == LOCAL_TEMPLATE_PROMPT_SCHEMA_VERSION
        )
        if local_template:
            if (
                self.provider_name != LOCAL_TEMPLATE_PROVIDER_NAME
                or self.model_name != LOCAL_TEMPLATE_MODEL_NAME
                or self.status is not NarrativeJobStatus.COMMITTED
                or self.attempt_count != 0
                or any(
                    value is not None
                    for value in (
                        self.lease_token,
                        self.lease_owner,
                        self.lease_expires_at,
                        self.error_code,
                    )
                )
                or self.validated_proposal is None
                or self.validated_proposal_digest is None
                or self.outcome_rule_id != "local.server_decision_template"
                or self.accepted_narrative_text is None
            ):
                raise ValueError("local template narrative job is incomplete")
            return self
        leased = self.status in {
            NarrativeJobStatus.IN_PROGRESS,
            NarrativeJobStatus.PROPOSAL_VALIDATED,
        }
        if leased != all(
            value is not None
            for value in (self.lease_token, self.lease_owner, self.lease_expires_at)
        ):
            raise ValueError("narrative job lease fields do not match status")
        if self.status is NarrativeJobStatus.PROPOSAL_VALIDATED and (
            self.validated_proposal is None or self.validated_proposal_digest is None
        ):
            raise ValueError("validated narrative job requires a proposal and digest")
        if (self.validated_proposal is None) != (
            self.validated_proposal_digest is None
        ):
            raise ValueError("narrative proposal and digest must be stored together")
        if self.status in {
            NarrativeJobStatus.PREPARED,
            NarrativeJobStatus.IN_PROGRESS,
        } and self.validated_proposal is not None:
            raise ValueError("unvalidated narrative job cannot contain a proposal")
        if self.status is NarrativeJobStatus.COMMITTED and (
            self.validated_proposal is None
            or self.validated_proposal_digest is None
            or self.outcome_rule_id is None
            or self.accepted_narrative_text is None
        ):
            raise ValueError("committed narrative job is incomplete")
        if self.status is not NarrativeJobStatus.COMMITTED and (
            self.outcome_rule_id is not None
            or self.accepted_narrative_text is not None
        ):
            raise ValueError("only a committed job may contain accepted narrative")
        terminal = self.status in {
            NarrativeJobStatus.FAILED_RETRYABLE,
            NarrativeJobStatus.FAILED_TERMINAL,
            NarrativeJobStatus.STALE,
            NarrativeJobStatus.OUTCOME_UNKNOWN,
        }
        if terminal != (self.error_code is not None):
            raise ValueError("narrative job error code does not match terminal status")
        if self.attempt_count > 0 and self.status is NarrativeJobStatus.PREPARED:
            raise ValueError("prepared narrative job cannot have an attempt")
        if (
            self.status is NarrativeJobStatus.STALE
            and self.attempt_count == 0
        ):
            return self
        if self.status is not NarrativeJobStatus.PREPARED and self.attempt_count != 1:
            raise ValueError("claimed narrative jobs require exactly one attempt")
        return self
