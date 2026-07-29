from __future__ import annotations

from datetime import datetime
from enum import StrEnum
import hashlib

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_serializer,
    model_validator,
)

from deviation_protocol.domain.player_character import (
    ApplicableCharacterReference,
    PlayerCharacterId,
    validate_applicable_character_reference,
)
from deviation_protocol.domain.run import (
    CanonicalRun,
    ContinuousStoryLineId,
    ReservedPlayerCharacterBinding,
    RunAuthoritySourceRef,
    RunId,
    RunLifecycleStatus,
    RunMutationKind,
    RunMutationProvenance,
    RunOperationId,
    RunSessionParticipationReference,
    RunStateVersion,
    canonical_run_operation_bytes,
    revalidate_run_model,
    validate_canonical_run,
)


CREATE_RUN_RESULT_SCHEMA_VERSION = "run.create-result/v1"
ATTACH_SESSION_RESULT_SCHEMA_VERSION = "run.attach-session-result/v1"
BIND_PLAYER_CHARACTER_RESULT_SCHEMA_VERSION = (
    "run.bind-player-character-result/v1"
)


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, strict=True, revalidate_instances="always"
    )


class RunOperationNamespace(StrEnum):
    CREATE_V1 = "run.create/v1"
    ATTACH_SESSION_V1 = "run.attach-session/v1"
    BIND_PLAYER_CHARACTER_V1 = "run.bind-player-character/v1"


class RunOperationFingerprint(_StrictFrozenModel):
    value: str = Field(strict=True, pattern=r"^[0-9a-f]{64}$")


class CreateRunCommand(_StrictFrozenModel):
    source_reference: RunAuthoritySourceRef


class AttachSessionCommand(_StrictFrozenModel):
    run_id: RunId
    continuous_story_line_id: ContinuousStoryLineId
    session_id: str = Field(strict=True, min_length=1, max_length=128)
    expected_state_version: RunStateVersion
    source_reference: RunAuthoritySourceRef

    @model_validator(mode="after")
    def validate_session_identity(self) -> AttachSessionCommand:
        if not self.session_id or any(character.isspace() for character in self.session_id):
            raise ValueError("session identity must be an opaque non-whitespace value")
        return self


class ReservedBindPlayerCharacterCommand(_StrictFrozenModel):
    run_id: RunId
    continuous_story_line_id: ContinuousStoryLineId
    expected_state_version: RunStateVersion
    source_reference: RunAuthoritySourceRef


class BindPlayerCharacterCommand(_StrictFrozenModel):
    run_id: RunId
    continuous_story_line_id: ContinuousStoryLineId
    target_player_character_id: PlayerCharacterId
    expected_state_version: RunStateVersion
    source_reference: RunAuthoritySourceRef


class RunSafeResult(_StrictFrozenModel):
    result_schema_version: str = Field(strict=True, min_length=1, max_length=64)
    run_id: RunId
    continuous_story_line_id: ContinuousStoryLineId
    lifecycle_status: RunLifecycleStatus
    resulting_state_version: RunStateVersion
    participation_reference: RunSessionParticipationReference | None = None
    applicable_character_reference: ApplicableCharacterReference | None = None

    @model_serializer(mode="plain")
    def serialize_result(self) -> dict[str, object]:
        serialized: dict[str, object] = {
            "result_schema_version": self.result_schema_version,
            "run_id": self.run_id,
            "continuous_story_line_id": self.continuous_story_line_id,
            "lifecycle_status": self.lifecycle_status,
            "resulting_state_version": self.resulting_state_version,
            "participation_reference": self.participation_reference,
        }
        if (
            self.result_schema_version
            == BIND_PLAYER_CHARACTER_RESULT_SCHEMA_VERSION
        ):
            serialized["applicable_character_reference"] = (
                self.applicable_character_reference
            )
        return serialized

    @model_validator(mode="after")
    def validate_result_shape(self) -> RunSafeResult:
        if self.result_schema_version == CREATE_RUN_RESULT_SCHEMA_VERSION:
            if (
                self.lifecycle_status is not RunLifecycleStatus.PRE_FIRST_TURN
                or self.resulting_state_version.value != 1
                or self.participation_reference is not None
                or self.applicable_character_reference is not None
            ):
                raise ValueError("creation result must describe initial unjoined state")
        elif self.result_schema_version == ATTACH_SESSION_RESULT_SCHEMA_VERSION:
            participation = self.participation_reference
            if (
                not self.lifecycle_status.is_active_line
                or participation is None
                or self.applicable_character_reference is not None
                or (
                    participation.run_id != self.run_id
                    or participation.continuous_story_line_id
                    != self.continuous_story_line_id
                    or participation.joined_state_version
                    != self.resulting_state_version
                )
            ):
                raise ValueError("participation result is inconsistent")
        elif (
            self.result_schema_version
            == BIND_PLAYER_CHARACTER_RESULT_SCHEMA_VERSION
        ):
            if (
                not self.lifecycle_status.is_active_line
                or self.participation_reference is not None
                or self.applicable_character_reference is None
            ):
                raise ValueError("player-character binding result is inconsistent")
        else:
            raise ValueError("Run result schema is not admitted")
        return self


class RunReceiptKey(_StrictFrozenModel):
    operation_namespace: RunOperationNamespace
    operation_id: RunOperationId
    run_id: RunId | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> RunReceiptKey:
        if (self.operation_namespace is RunOperationNamespace.CREATE_V1) != (self.run_id is None):
            raise ValueError("creation receipts are global and mutation receipts are Run scoped")
        return self


class StoredRunSuccessReceipt(_StrictFrozenModel):
    key: RunReceiptKey
    fingerprint: RunOperationFingerprint
    command_kind: RunMutationKind
    result: RunSafeResult

    @model_validator(mode="after")
    def validate_receipt_bindings(self) -> StoredRunSuccessReceipt:
        expected = {
            RunMutationKind.CREATE: (
                RunOperationNamespace.CREATE_V1,
                CREATE_RUN_RESULT_SCHEMA_VERSION,
            ),
            RunMutationKind.ATTACH_SESSION: (
                RunOperationNamespace.ATTACH_SESSION_V1,
                ATTACH_SESSION_RESULT_SCHEMA_VERSION,
            ),
            RunMutationKind.BIND_PLAYER_CHARACTER: (
                RunOperationNamespace.BIND_PLAYER_CHARACTER_V1,
                BIND_PLAYER_CHARACTER_RESULT_SCHEMA_VERSION,
            ),
        }.get(self.command_kind)
        if expected is None or (
            self.key.operation_namespace,
            self.result.result_schema_version,
        ) != expected:
            raise ValueError("stored Run receipt command bindings are inconsistent")
        if self.key.run_id is not None and self.key.run_id != self.result.run_id:
            raise ValueError("stored Run receipt scope does not bind its result")
        return self


class RunReplayDecisionCode(StrEnum):
    ABSENT = "ABSENT"
    REPLAY = "REPLAY"
    CONFLICT = "CONFLICT"
    RESERVED_OPERATION_REJECTED = "RESERVED_OPERATION_REJECTED"


class RunReplayDecision(_StrictFrozenModel):
    code: RunReplayDecisionCode
    stored_success_result: RunSafeResult | None = None

    @model_validator(mode="after")
    def validate_shape(self) -> RunReplayDecision:
        if (self.code is RunReplayDecisionCode.REPLAY) != (self.stored_success_result is not None):
            raise ValueError("only a replay decision may contain a stored result")
        return self


def create_run_fingerprint(command: CreateRunCommand) -> tuple[bytes, RunOperationFingerprint]:
    command = revalidate_run_model(command, CreateRunCommand)
    return _fingerprint({"command_kind": RunMutationKind.CREATE, "operation_namespace": RunOperationNamespace.CREATE_V1, "source_reference": command.source_reference})


def construct_created_run(
    command: CreateRunCommand,
    *,
    run_id: RunId,
    continuous_story_line_id: ContinuousStoryLineId,
    operation_id: RunOperationId,
    occurred_at: datetime,
) -> CanonicalRun:
    """Build the initial Run state from already-issued identities without I/O."""

    command = revalidate_run_model(command, CreateRunCommand)
    run_id = revalidate_run_model(run_id, RunId)
    continuous_story_line_id = revalidate_run_model(
        continuous_story_line_id, ContinuousStoryLineId
    )
    operation_id = revalidate_run_model(operation_id, RunOperationId)
    provenance = RunMutationProvenance(
        target_run_id=run_id,
        target_continuous_story_line_id=continuous_story_line_id,
        prior_state_version=None,
        resulting_state_version=RunStateVersion(value=1),
        mutation_kind=RunMutationKind.CREATE,
        operation_id=operation_id,
        source_reference=command.source_reference,
        occurred_at=occurred_at,
    )
    return CanonicalRun(
        run_id=run_id,
        continuous_story_line_id=continuous_story_line_id,
        lifecycle_status=RunLifecycleStatus.PRE_FIRST_TURN,
        state_version=RunStateVersion(value=1),
        creation_provenance=provenance,
        current_mutation_provenance=provenance,
    )


def attach_session_fingerprint(
    command: AttachSessionCommand, *, operation_id: RunOperationId
) -> tuple[bytes, RunOperationFingerprint]:
    command = revalidate_run_model(command, AttachSessionCommand)
    operation_id = revalidate_run_model(operation_id, RunOperationId)
    return _fingerprint({"command_kind": RunMutationKind.ATTACH_SESSION, "continuous_story_line_id": command.continuous_story_line_id, "expected_state_version": command.expected_state_version.value, "operation_id": operation_id, "operation_namespace": RunOperationNamespace.ATTACH_SESSION_V1, "run_id": command.run_id, "session_id": command.session_id, "source_reference": command.source_reference})


def bind_player_character_fingerprint(
    command: BindPlayerCharacterCommand,
    *,
    operation_id: RunOperationId,
) -> tuple[bytes, RunOperationFingerprint]:
    command = revalidate_run_model(command, BindPlayerCharacterCommand)
    operation_id = revalidate_run_model(operation_id, RunOperationId)
    return _fingerprint(
        {
            "command_kind": RunMutationKind.BIND_PLAYER_CHARACTER,
            "continuous_story_line_id": command.continuous_story_line_id,
            "expected_state_version": command.expected_state_version.value,
            "operation_id": operation_id,
            "operation_namespace": (
                RunOperationNamespace.BIND_PLAYER_CHARACTER_V1
            ),
            "run_id": command.run_id,
            "source_reference": command.source_reference,
            "target_player_character_id": (
                command.target_player_character_id
            ),
        }
    )


def attach_session_to_run(
    run: CanonicalRun,
    command: AttachSessionCommand,
    *,
    operation_id: RunOperationId,
    occurred_at: datetime,
) -> CanonicalRun:
    """Return the one-version successor for an admitted trusted participation."""

    run = validate_canonical_run(run)
    command = revalidate_run_model(command, AttachSessionCommand)
    operation_id = revalidate_run_model(operation_id, RunOperationId)
    if (
        command.run_id != run.run_id
        or command.continuous_story_line_id != run.continuous_story_line_id
        or command.expected_state_version != run.state_version
    ):
        raise ValueError("attach-session command does not bind the current Run state")
    if not run.lifecycle_status.is_active_line:
        raise ValueError("cannot attach a Session to a non-active Run line")
    if any(item.session_id == command.session_id for item in run.trusted_participation_references):
        raise ValueError("Session already participates in this Run")
    successor = run.state_version.successor()
    participation = RunSessionParticipationReference(
        session_id=command.session_id,
        run_id=run.run_id,
        continuous_story_line_id=run.continuous_story_line_id,
        joined_state_version=successor,
        operation_id=operation_id,
        source_reference=command.source_reference,
    )
    provenance = RunMutationProvenance(
        target_run_id=run.run_id,
        target_continuous_story_line_id=run.continuous_story_line_id,
        prior_state_version=run.state_version,
        resulting_state_version=successor,
        mutation_kind=RunMutationKind.ATTACH_SESSION,
        operation_id=operation_id,
        source_reference=command.source_reference,
        occurred_at=occurred_at,
    )
    return CanonicalRun(
        run_id=run.run_id,
        continuous_story_line_id=run.continuous_story_line_id,
        lifecycle_status=run.lifecycle_status,
        state_version=successor,
        creation_provenance=run.creation_provenance,
        current_mutation_provenance=provenance,
        trusted_participation_references=(*run.trusted_participation_references, participation),
        player_character_binding=run.player_character_binding,
    )


def bind_player_character_to_run(
    run: CanonicalRun,
    command: BindPlayerCharacterCommand,
    *,
    applicable_character_reference: ApplicableCharacterReference,
    operation_id: RunOperationId,
    occurred_at: datetime,
) -> CanonicalRun:
    """Return the one-version successor containing one complete active binding."""

    run = validate_canonical_run(run)
    command = revalidate_run_model(command, BindPlayerCharacterCommand)
    applicable_character_reference = validate_applicable_character_reference(
        applicable_character_reference
    )
    operation_id = revalidate_run_model(operation_id, RunOperationId)
    if (
        command.run_id != run.run_id
        or command.continuous_story_line_id
        != run.continuous_story_line_id
        or command.expected_state_version != run.state_version
    ):
        raise ValueError(
            "bind-player-character command does not bind the current Run state"
        )
    if not run.lifecycle_status.is_active_line:
        raise ValueError("cannot bind a player character to a non-active Run line")
    if run.player_character_binding is not None:
        raise ValueError("Run line already has a player-character binding")
    if (
        applicable_character_reference.player_character_id
        != command.target_player_character_id
    ):
        raise ValueError(
            "applicable character reference does not bind the command target"
        )
    successor = run.state_version.successor()
    provenance = RunMutationProvenance(
        target_run_id=run.run_id,
        target_continuous_story_line_id=run.continuous_story_line_id,
        prior_state_version=run.state_version,
        resulting_state_version=successor,
        mutation_kind=RunMutationKind.BIND_PLAYER_CHARACTER,
        operation_id=operation_id,
        source_reference=command.source_reference,
        occurred_at=occurred_at,
    )
    binding = ReservedPlayerCharacterBinding(
        run_id=run.run_id,
        continuous_story_line_id=run.continuous_story_line_id,
        applicable_character_reference=applicable_character_reference,
        binding_state="active",
        binding_operation_id=operation_id,
        binding_authority_source_ref=command.source_reference,
        bound_at=occurred_at,
    )
    return CanonicalRun(
        run_id=run.run_id,
        continuous_story_line_id=run.continuous_story_line_id,
        lifecycle_status=run.lifecycle_status,
        state_version=successor,
        creation_provenance=run.creation_provenance,
        current_mutation_provenance=provenance,
        trusted_participation_references=(
            run.trusted_participation_references
        ),
        player_character_binding=binding,
    )


def reject_reserved_bind_player_character(
    command: ReservedBindPlayerCharacterCommand, *, operation_id: RunOperationId
) -> RunReplayDecision:
    revalidate_run_model(command, ReservedBindPlayerCharacterCommand)
    revalidate_run_model(operation_id, RunOperationId)
    return RunReplayDecision(code=RunReplayDecisionCode.RESERVED_OPERATION_REJECTED)


def evaluate_receipt(
    receipt: StoredRunSuccessReceipt | None,
    *,
    key: RunReceiptKey,
    fingerprint: RunOperationFingerprint,
    command_kind: RunMutationKind,
) -> RunReplayDecision:
    key = revalidate_run_model(key, RunReceiptKey)
    fingerprint = revalidate_run_model(fingerprint, RunOperationFingerprint)
    if receipt is None:
        return RunReplayDecision(code=RunReplayDecisionCode.ABSENT)
    receipt = revalidate_run_model(receipt, StoredRunSuccessReceipt)
    if receipt.key == key and receipt.fingerprint == fingerprint and receipt.command_kind is command_kind:
        return RunReplayDecision(code=RunReplayDecisionCode.REPLAY, stored_success_result=receipt.result)
    return RunReplayDecision(code=RunReplayDecisionCode.CONFLICT)


def creation_result(run: CanonicalRun) -> RunSafeResult:
    run = validate_canonical_run(run)
    if run.current_mutation_provenance.mutation_kind is not RunMutationKind.CREATE:
        raise ValueError("creation result requires a creation Run state")
    return RunSafeResult(result_schema_version=CREATE_RUN_RESULT_SCHEMA_VERSION, run_id=run.run_id, continuous_story_line_id=run.continuous_story_line_id, lifecycle_status=run.lifecycle_status, resulting_state_version=run.state_version)


def attach_session_result(run: CanonicalRun) -> RunSafeResult:
    run = validate_canonical_run(run)
    if run.current_mutation_provenance.mutation_kind is not RunMutationKind.ATTACH_SESSION or not run.trusted_participation_references:
        raise ValueError("participation result requires an attached Session state")
    return RunSafeResult(result_schema_version=ATTACH_SESSION_RESULT_SCHEMA_VERSION, run_id=run.run_id, continuous_story_line_id=run.continuous_story_line_id, lifecycle_status=run.lifecycle_status, resulting_state_version=run.state_version, participation_reference=run.trusted_participation_references[-1])


def bind_player_character_result(run: CanonicalRun) -> RunSafeResult:
    run = validate_canonical_run(run)
    binding = run.player_character_binding
    if (
        run.current_mutation_provenance.mutation_kind
        is not RunMutationKind.BIND_PLAYER_CHARACTER
        or binding is None
        or binding.binding_state != "active"
    ):
        raise ValueError(
            "player-character binding result requires a binding Run state"
        )
    return RunSafeResult(
        result_schema_version=BIND_PLAYER_CHARACTER_RESULT_SCHEMA_VERSION,
        run_id=run.run_id,
        continuous_story_line_id=run.continuous_story_line_id,
        lifecycle_status=run.lifecycle_status,
        resulting_state_version=run.state_version,
        applicable_character_reference=(
            binding.applicable_character_reference
        ),
    )


def _fingerprint(payload: object) -> tuple[bytes, RunOperationFingerprint]:
    encoded = canonical_run_operation_bytes(payload)
    return encoded, RunOperationFingerprint(value=hashlib.sha256(encoded).hexdigest())
