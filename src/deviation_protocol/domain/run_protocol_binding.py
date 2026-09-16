"""Detached stored-family results; neither result authorizes a caller."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from deviation_protocol.domain.run import (
    CanonicalRun,
    ContinuousStoryLineId,
    RunId,
    RunLifecycleStatus,
    RunStateVersion,
    revalidate_run_model,
    validate_canonical_run,
)
from deviation_protocol.domain.run_protocol_resolution import (
    ResolvedRunProtocolObjectivesV1,
)


RUN_PROTOCOL_BINDING_EPOCH = "run-protocol-binding"
RUN_PROTOCOL_BINDING_V1_VERSION = 1
RUN_FAMILY_NATIVE_V1 = "phase_3_3_native"


class LegacyRunCompatibilityV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True,
                              revalidate_instances="always")

    canonical_run: CanonicalRun
    session_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")

    @field_validator("canonical_run", mode="before")
    @classmethod
    def _validate_original_run(cls, value: CanonicalRun) -> CanonicalRun:
        return validate_canonical_run(value)

    @model_validator(mode="after")
    def _validate_association(self) -> LegacyRunCompatibilityV1:
        run = self.canonical_run
        if (
            run.state_version.value != 3
            or run.lifecycle_status is not RunLifecycleStatus.ACTIVE
            or run.player_character_binding is None
            or len(run.trusted_participation_references) != 1
            or run.trusted_participation_references[0].session_id != self.session_id
        ):
            raise ValueError("legacy result requires the exact active entry family")
        return self


class NativeRunProtocolBindingV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True,
                              revalidate_instances="always")

    run_id: RunId
    continuous_story_line_id: ContinuousStoryLineId
    bound_state_version: RunStateVersion
    resolved_protocol: ResolvedRunProtocolObjectivesV1

    @field_validator("run_id", "continuous_story_line_id", "bound_state_version", "resolved_protocol", mode="before")
    @classmethod
    def _validate_original_state(cls, value, info):
        expected = {
            "run_id": RunId,
            "continuous_story_line_id": ContinuousStoryLineId,
            "bound_state_version": RunStateVersion,
            "resolved_protocol": ResolvedRunProtocolObjectivesV1,
        }[info.field_name]
        return revalidate_run_model(value, expected)


_ClassifiedRun = LegacyRunCompatibilityV1 | NativeRunProtocolBindingV1
