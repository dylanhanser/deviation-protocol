from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta
from enum import StrEnum
import json
import re
from typing import Any, TypeVar
import unicodedata

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from deviation_protocol.domain.player_character import ApplicableCharacterReference


MAX_RUN_STATE_VERSION = 2**63 - 1
_OPAQUE_REFERENCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_ModelT = TypeVar("_ModelT", bound=BaseModel)


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, strict=True, revalidate_instances="always"
    )


def revalidate_run_model(value: _ModelT, model_type: type[_ModelT]) -> _ModelT:
    """Revalidate a complete actual Pydantic instance at a Run trust boundary."""

    if type(value) is not model_type:
        raise TypeError(f"expected {model_type.__name__}")
    _validate_actual_pydantic_state(value, path=model_type.__name__, visited=set())
    validated = model_type.model_validate(value)
    if validated != value:
        raise ValueError(f"{model_type.__name__} is not already canonical")
    return value


def _validate_actual_pydantic_state(
    value: BaseModel, *, path: str, visited: set[int]
) -> None:
    identity = id(value)
    if identity in visited:
        return
    visited.add(identity)
    model_type = type(value)
    fields = set(model_type.model_fields)
    state = value.__dict__
    if set(state) != fields:
        raise ValueError(f"{path} has non-canonical instance state")
    extra = getattr(value, "__pydantic_extra__", None)
    if extra:
        raise ValueError(f"{path} has unauthorized Pydantic extra state")
    private = getattr(value, "__pydantic_private__", None)
    if private:
        raise ValueError(f"{path} has unauthorized Pydantic private state")
    fields_set = getattr(value, "__pydantic_fields_set__", None)
    if type(fields_set) is not set or not fields_set <= fields:
        raise ValueError(f"{path} has invalid Pydantic fields-set state")
    for field_name in fields:
        _validate_nested_state(state[field_name], path=f"{path}.{field_name}", visited=visited)


def _validate_nested_state(value: Any, *, path: str, visited: set[int]) -> None:
    if isinstance(value, BaseModel):
        _validate_actual_pydantic_state(value, path=path, visited=visited)
    elif isinstance(value, Mapping):
        for key, nested in value.items():
            _validate_nested_state(key, path=f"{path}.<key>", visited=visited)
            _validate_nested_state(nested, path=f"{path}[{key!r}]", visited=visited)
    elif isinstance(value, (tuple, list, set, frozenset)):
        for index, nested in enumerate(value):
            _validate_nested_state(nested, path=f"{path}[{index}]", visited=visited)


def _require_exact_utc_datetime(value: datetime) -> datetime:
    if (
        type(value) is not datetime
        or value.tzinfo is None
        or value.utcoffset() != timedelta(0)
    ):
        raise ValueError("Run timestamp must be an exact UTC datetime")
    return value


def canonical_run_operation_bytes(value: Any) -> bytes:
    """Return the frozen canonical UTF-8 JSON form for a Run operation."""

    return json.dumps(
        _canonical_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _canonical_value(value: Any) -> Any:
    if value is None or type(value) is bool:
        return value
    if type(value) is int:
        if not -(2**63) <= value <= MAX_RUN_STATE_VERSION:
            raise ValueError("canonical integer is outside the signed 64-bit range")
        return value
    if isinstance(value, str):
        normalized = unicodedata.normalize("NFC", value)
        normalized.encode("utf-8")
        return normalized
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, BaseModel):
        return _canonical_value(value.model_dump(mode="python", warnings="none"))
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, nested in value.items():
            if not isinstance(key, str):
                raise TypeError("canonical object keys must be strings")
            normalized_key = unicodedata.normalize("NFC", key)
            normalized_key.encode("utf-8")
            if normalized_key in normalized:
                raise ValueError("canonical object keys collide after NFC normalization")
            normalized[normalized_key] = _canonical_value(nested)
        return {key: normalized[key] for key in sorted(normalized)}
    if isinstance(value, (tuple, list)):
        return [_canonical_value(item) for item in value]
    raise TypeError(f"unsupported canonical value {type(value).__name__}")


class _OpaqueReference(_StrictFrozenModel):
    value: str = Field(strict=True, min_length=1, max_length=128)

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: str) -> str:
        if not _OPAQUE_REFERENCE.fullmatch(value):
            raise ValueError("reference must be a bounded opaque identifier")
        return value

    def __str__(self) -> str:
        return self.value


class RunId(_OpaqueReference):
    """Permanent identity of one canonical Run."""


class ContinuousStoryLineId(_OpaqueReference):
    """Permanent identity of the one line owned by a Run."""


class RunOperationId(_OpaqueReference):
    """Opaque idempotency identity; never authority or a Run identity."""


class RunAuthoritySourceRef(_OpaqueReference):
    """Trusted server provenance reference; never caller authority."""


class RunLifecycleStatus(StrEnum):
    PRE_FIRST_TURN = "pre_first_turn"
    ACTIVE = "active"
    COMPLETED = "completed"
    TERMINATED = "terminated"

    @property
    def is_active_line(self) -> bool:
        return self in {self.PRE_FIRST_TURN, self.ACTIVE}


class RunStateVersion(_StrictFrozenModel):
    value: int = Field(strict=True, ge=1, le=MAX_RUN_STATE_VERSION)

    @property
    def has_successor(self) -> bool:
        return self.value < MAX_RUN_STATE_VERSION

    def successor(self) -> RunStateVersion:
        if not self.has_successor:
            raise ValueError("Run state version has no signed 64-bit successor")
        return RunStateVersion(value=self.value + 1)


class RunMutationKind(StrEnum):
    CREATE = "CREATE"
    ATTACH_SESSION = "ATTACH_SESSION"
    BIND_PLAYER_CHARACTER = "BIND_PLAYER_CHARACTER"


class RunMutationProvenance(_StrictFrozenModel):
    target_run_id: RunId
    target_continuous_story_line_id: ContinuousStoryLineId
    prior_state_version: RunStateVersion | None
    resulting_state_version: RunStateVersion
    mutation_kind: RunMutationKind
    operation_id: RunOperationId
    source_reference: RunAuthoritySourceRef
    occurred_at: datetime

    @field_validator("occurred_at")
    @classmethod
    def validate_occurred_at(cls, value: datetime) -> datetime:
        return _require_exact_utc_datetime(value)

    @model_validator(mode="after")
    def validate_transition(self) -> RunMutationProvenance:
        if self.mutation_kind is RunMutationKind.CREATE:
            if self.prior_state_version is not None or self.resulting_state_version.value != 1:
                raise ValueError("creation provenance must establish state version one")
        elif (
            self.prior_state_version is None
            or self.resulting_state_version.value != self.prior_state_version.value + 1
        ):
            raise ValueError("Run mutation provenance must advance exactly one version")
        return self


class ReservedPlayerCharacterBinding(_StrictFrozenModel):
    """The exact immutable Run-owned player-character binding envelope."""

    run_id: RunId
    continuous_story_line_id: ContinuousStoryLineId
    applicable_character_reference: ApplicableCharacterReference
    binding_state: str = Field(strict=True, pattern=r"^(active|historical)$")
    binding_operation_id: RunOperationId
    binding_authority_source_ref: RunAuthoritySourceRef
    bound_at: datetime
    inactivated_at: datetime | None = None

    @field_validator("bound_at", "inactivated_at")
    @classmethod
    def validate_audit_time(cls, value: datetime | None) -> datetime | None:
        return (
            _require_exact_utc_datetime(value)
            if value is not None
            else None
        )

    @model_validator(mode="after")
    def validate_state_times(self) -> ReservedPlayerCharacterBinding:
        if (self.binding_state == "active") != (self.inactivated_at is None):
            raise ValueError("binding state and inactivation time are inconsistent")
        return self


class RunSessionParticipationReference(_StrictFrozenModel):
    session_id: str = Field(strict=True, min_length=1, max_length=128)
    run_id: RunId
    continuous_story_line_id: ContinuousStoryLineId
    joined_state_version: RunStateVersion
    operation_id: RunOperationId
    source_reference: RunAuthoritySourceRef

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, value: str) -> str:
        if not _OPAQUE_REFERENCE.fullmatch(value):
            raise ValueError("session identity must be a bounded opaque identifier")
        return value


class CanonicalRun(_StrictFrozenModel):
    run_id: RunId
    continuous_story_line_id: ContinuousStoryLineId
    lifecycle_status: RunLifecycleStatus
    state_version: RunStateVersion
    creation_provenance: RunMutationProvenance
    current_mutation_provenance: RunMutationProvenance
    trusted_participation_references: tuple[RunSessionParticipationReference, ...] = ()
    player_character_binding: ReservedPlayerCharacterBinding | None = None

    @model_validator(mode="after")
    def validate_complete_minimum_state(self) -> CanonicalRun:
        creation = self.creation_provenance
        current = self.current_mutation_provenance
        if (
            creation.mutation_kind is not RunMutationKind.CREATE
            or creation.target_run_id != self.run_id
            or creation.target_continuous_story_line_id != self.continuous_story_line_id
            or current.target_run_id != self.run_id
            or current.target_continuous_story_line_id != self.continuous_story_line_id
            or current.resulting_state_version != self.state_version
        ):
            raise ValueError("Run provenance does not bind the canonical state")
        if self.lifecycle_status is not RunLifecycleStatus.PRE_FIRST_TURN:
            raise ValueError("current Run implementation permits only pre_first_turn state")
        binding = self.player_character_binding
        if binding is not None:
            if (
                binding.run_id != self.run_id
                or binding.continuous_story_line_id
                != self.continuous_story_line_id
            ):
                raise ValueError("player-character binding does not bind this Run")
            if (
                binding.binding_state != "active"
                or binding.inactivated_at is not None
                or not self.lifecycle_status.is_active_line
            ):
                raise ValueError(
                    "P4-S1 permits only a complete active binding on an active line"
                )
        if current.mutation_kind is RunMutationKind.BIND_PLAYER_CHARACTER:
            if binding is None:
                raise ValueError(
                    "binding mutation provenance requires a complete binding"
                )
            if (
                binding.binding_operation_id != current.operation_id
                or binding.binding_authority_source_ref
                != current.source_reference
                or binding.bound_at != current.occurred_at
            ):
                raise ValueError(
                    "binding mutation provenance is inconsistent with the binding"
                )
        versions = tuple(
            item.joined_state_version.value
            for item in self.trusted_participation_references
        )
        sessions = tuple(item.session_id for item in self.trusted_participation_references)
        expected_successor_versions = set(range(2, self.state_version.value + 1))
        participation_versions = set(versions)
        missing_versions = expected_successor_versions - participation_versions
        if (
            len(versions) != len(participation_versions)
            or tuple(sorted(versions)) != versions
            or not participation_versions <= expected_successor_versions
            or (
                binding is None
                and missing_versions
            )
            or (
                binding is not None
                and len(missing_versions) != 1
            )
            or (
                current.mutation_kind is RunMutationKind.BIND_PLAYER_CHARACTER
                and missing_versions != {self.state_version.value}
            )
        ):
            raise ValueError(
                "participation references must cover every non-binding "
                "successor version in order"
            )
        if len(sessions) != len(set(sessions)):
            raise ValueError("participation references must have unique Session identities")
        for participation in self.trusted_participation_references:
            if (
                participation.run_id != self.run_id
                or participation.continuous_story_line_id != self.continuous_story_line_id
                or participation.joined_state_version.value > self.state_version.value
            ):
                raise ValueError("participation reference does not bind this Run state")
        if self.current_mutation_provenance.mutation_kind is RunMutationKind.CREATE:
            if (
                self.state_version.value != 1
                or self.trusted_participation_references
                or current != creation
                or binding is not None
            ):
                raise ValueError(
                    "creation state must be version one with exact creation provenance "
                    "and no participation or binding"
                )
        elif self.current_mutation_provenance.mutation_kind is RunMutationKind.ATTACH_SESSION:
            if not self.trusted_participation_references:
                raise ValueError("attach-session state requires participation")
            latest = self.trusted_participation_references[-1]
            if (
                latest.joined_state_version != self.state_version
                or latest.operation_id != self.current_mutation_provenance.operation_id
                or latest.source_reference != self.current_mutation_provenance.source_reference
            ):
                raise ValueError("current attach-session provenance is inconsistent")
        return self


def validate_canonical_run(value: CanonicalRun) -> CanonicalRun:
    return revalidate_run_model(value, CanonicalRun)
