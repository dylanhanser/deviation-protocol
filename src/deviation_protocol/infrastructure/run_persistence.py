"""Strict offline persistence carriers and codecs for the minimum Run core."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from typing import Any

from deviation_protocol.application.run_operations import (
    ATTACH_SESSION_RESULT_SCHEMA_VERSION,
    BIND_PLAYER_CHARACTER_RESULT_SCHEMA_VERSION,
    CREATE_RUN_RESULT_SCHEMA_VERSION,
    AttachSessionCommand,
    BindPlayerCharacterCommand,
    CreateRunCommand,
    P8_S2_EVIDENCE_MAGIC,
    P8_S2_EVIDENCE_VERSION,
    RunEntryCreationEvidence,
    RunOperationFingerprint,
    RunOperationNamespace,
    StoredRunSuccessReceipt,
    attach_session_fingerprint,
    attach_session_result,
    bind_player_character_fingerprint,
    bind_player_character_result,
    create_run_fingerprint,
    run_entry_creation_fingerprint,
    run_entry_evidence_bytes,
    creation_result,
)
from deviation_protocol.application.ports import RunWriteConflictError
from deviation_protocol.domain.player_character import (
    ApplicableCharacterReference,
    CanonicalPlayerCharacter,
    PlayerCharacterContractVersion,
    PlayerCharacterId,
    PlayerCharacterLifecycle,
    PlayerCharacterRevision,
    validate_canonical_player_character,
)
from deviation_protocol.domain.run import (
    CanonicalRun,
    ContinuousStoryLineId,
    MAX_RUN_STATE_VERSION,
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


class RunStoredRecordIntegrityError(ValueError):
    """Persisted Run evidence is malformed, incomplete, or cross-bound."""


class RunRepositoryError(RuntimeError):
    """A minimum Run-core database operation failed."""


class RunRepositoryConflictError(RunRepositoryError, RunWriteConflictError):
    """A known immutable or unique Run constraint rejected a write."""


@dataclass(frozen=True, slots=True)
class StoredCurrentRunRecord:
    run_id: RunId
    continuous_story_line_id: ContinuousStoryLineId
    lifecycle_status: str
    state_version: int
    creation_operation_id: RunOperationId
    creation_source_reference: RunAuthoritySourceRef
    creation_occurred_at: datetime
    prior_state_version: int | None
    mutation_kind: str
    operation_id: RunOperationId
    source_reference: RunAuthoritySourceRef
    occurred_at: datetime
    binding_player_character_id: str | None
    binding_contract_version: str | None
    binding_record_revision: int | None
    binding_state: str | None
    binding_operation_id: str | None
    binding_authority_source_ref: str | None
    bound_at: datetime | None
    inactivated_at: datetime | None
    active_player_character_id: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class StoredRunRevisionRecord:
    run_id: RunId
    continuous_story_line_id: ContinuousStoryLineId
    lifecycle_status: str
    state_version: int
    creation_operation_id: RunOperationId
    creation_source_reference: RunAuthoritySourceRef
    creation_occurred_at: datetime
    prior_state_version: int | None
    mutation_kind: str
    operation_id: RunOperationId
    source_reference: RunAuthoritySourceRef
    occurred_at: datetime
    binding_player_character_id: str | None
    binding_contract_version: str | None
    binding_record_revision: int | None
    binding_state: str | None
    binding_operation_id: str | None
    binding_authority_source_ref: str | None
    bound_at: datetime | None
    inactivated_at: datetime | None
    active_player_character_id: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class StoredRunSessionParticipationRecord:
    session_id: str
    run_id: RunId
    continuous_story_line_id: ContinuousStoryLineId
    joined_state_version: int
    operation_id: RunOperationId
    source_reference: RunAuthoritySourceRef
    joined_at: datetime


@dataclass(frozen=True, slots=True)
class StoredRunCreationReceiptRecord:
    operation_namespace: str
    operation_id: RunOperationId
    fingerprint: bytes
    command_kind: str
    result_schema_version: str
    result_run_id: RunId
    result_continuous_story_line_id: ContinuousStoryLineId
    resulting_lifecycle_status: str
    resulting_state_version: int
    receipt_canonical: bytes
    operation_evidence_canonical: bytes
    created_at: datetime


@dataclass(frozen=True, slots=True)
class StoredRunMutationReceiptRecord:
    run_id: RunId
    operation_namespace: str
    operation_id: RunOperationId
    fingerprint: bytes
    command_kind: str
    result_schema_version: str
    expected_state_version: int
    result_run_id: RunId
    result_continuous_story_line_id: ContinuousStoryLineId
    resulting_lifecycle_status: str
    resulting_state_version: int
    participation_session_id: str | None
    participation_operation_id: str | None
    participation_source_reference: str | None
    result_player_character_id: str | None
    result_character_contract_version: str | None
    result_character_record_revision: int | None
    receipt_canonical: bytes
    operation_evidence_canonical: bytes
    created_at: datetime


def _fail(message: str) -> RunStoredRecordIntegrityError:
    return RunStoredRecordIntegrityError(message)


def _require_version(value: Any, field_name: str) -> None:
    if type(value) is not int or not 1 <= value <= MAX_RUN_STATE_VERSION:
        raise _fail(f"{field_name} is outside the stored Run version domain")


def _require_optional_version(value: Any, field_name: str) -> None:
    if value is not None:
        _require_version(value, field_name)


def _require_bytes(value: Any, field_name: str) -> None:
    if type(value) is not bytes or not value:
        raise _fail(f"{field_name} must be non-empty immutable bytes")


def _require_fingerprint(value: Any, field_name: str) -> None:
    if type(value) is not bytes or len(value) != 32:
        raise _fail(f"{field_name} must contain exactly 32 immutable bytes")


def _require_utc(value: Any, field_name: str) -> None:
    if (
        type(value) is not datetime
        or value.tzinfo is None
        or value.utcoffset() != timedelta(0)
    ):
        raise _fail(f"{field_name} must be an exact UTC datetime")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _fail("stored canonical JSON has duplicate keys")
        result[key] = value
    return result


def _strict_object(value: bytes) -> dict[str, Any]:
    _require_bytes(value, "stored canonical value")
    try:
        decoded = value.decode("utf-8")
        result = json.loads(
            decoded,
            parse_float=lambda _value: (_ for _ in ()).throw(
                _fail("JSON floats are not permitted")
            ),
            parse_constant=lambda _value: (_ for _ in ()).throw(
                _fail("non-standard JSON constant")
            ),
            object_pairs_hook=_unique_object,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        if isinstance(exc, RunStoredRecordIntegrityError):
            raise
        raise _fail("stored canonical value is not strict UTF-8 JSON") from exc
    if type(result) is not dict:
        raise _fail("stored canonical value must contain exactly one object")
    return result


def fingerprint_to_storage_bytes(value: RunOperationFingerprint) -> bytes:
    try:
        value = revalidate_run_model(value, RunOperationFingerprint)
        raw = bytes.fromhex(value.value)
    except (AttributeError, TypeError, ValueError) as exc:
        raise _fail("Run operation fingerprint is invalid") from exc
    if len(raw) != 32 or raw.hex() != value.value:
        raise _fail("Run operation fingerprint must be canonical lowercase SHA-256")
    return raw


def fingerprint_from_storage_bytes(value: bytes) -> RunOperationFingerprint:
    _require_fingerprint(value, "stored fingerprint")
    try:
        return RunOperationFingerprint(value=value.hex())
    except (TypeError, ValueError) as exc:
        raise _fail("stored Run operation fingerprint is invalid") from exc


def run_receipt_to_storage_bytes(value: StoredRunSuccessReceipt) -> bytes:
    try:
        value = revalidate_run_model(value, StoredRunSuccessReceipt)
        encoded = canonical_run_operation_bytes(value)
    except (AttributeError, TypeError, ValueError) as exc:
        raise _fail("stored Run receipt is invalid") from exc
    if not 1 <= len(encoded) <= 65_536:
        raise _fail("stored Run receipt canonical bytes are outside their bounds")
    return encoded


def _receipt_from_storage(value: bytes) -> StoredRunSuccessReceipt:
    _strict_object(value)
    try:
        receipt = StoredRunSuccessReceipt.model_validate_json(value)
        receipt = revalidate_run_model(receipt, StoredRunSuccessReceipt)
    except (TypeError, ValueError) as exc:
        raise _fail("stored Run receipt is invalid") from exc
    if run_receipt_to_storage_bytes(receipt) != value:
        raise _fail("stored Run receipt is non-canonical")
    return receipt


def creation_operation_evidence_to_storage_bytes(command: CreateRunCommand) -> bytes:
    try:
        command = revalidate_run_model(command, CreateRunCommand)
        create_run_fingerprint(command)
        return canonical_run_operation_bytes(command)
    except (AttributeError, TypeError, ValueError) as exc:
        raise _fail("Run creation operation evidence is invalid") from exc


def creation_operation_evidence_from_storage(value: bytes) -> CreateRunCommand:
    _strict_object(value)
    try:
        command = CreateRunCommand.model_validate_json(value)
        command = revalidate_run_model(command, CreateRunCommand)
    except (TypeError, ValueError) as exc:
        raise _fail("Run creation operation evidence is invalid") from exc
    if creation_operation_evidence_to_storage_bytes(command) != value:
        raise _fail("Run creation operation evidence is non-canonical")
    return command


def run_entry_creation_evidence_from_storage(value: bytes) -> RunEntryCreationEvidence:
    """Decode only the reserved P8 composite family; never fall back."""
    if type(value) is not bytes or not 14 <= len(value) <= 4096:
        raise _fail("Run entry creation evidence is outside its byte bounds")
    if not value.startswith(P8_S2_EVIDENCE_MAGIC):
        raise _fail("Run entry creation evidence has invalid family magic")
    if value[12] != P8_S2_EVIDENCE_VERSION:
        raise _fail("Run entry creation evidence has an unsupported version")
    payload = value[13:]
    _strict_object(payload)
    try:
        evidence = RunEntryCreationEvidence.model_validate_json(
            payload, strict=True
        )
        evidence = revalidate_run_model(evidence, RunEntryCreationEvidence)
    except (TypeError, ValueError) as exc:
        raise _fail("Run entry creation evidence is invalid") from exc
    if run_entry_evidence_bytes(evidence) != value:
        raise _fail("Run entry creation evidence is non-canonical")
    return evidence


def creation_evidence_from_storage(
    value: bytes,
) -> CreateRunCommand | RunEntryCreationEvidence:
    """Select the historical or composite family from its non-overlapping byte."""
    if type(value) is not bytes or not value:
        raise _fail("Run creation evidence is empty or invalid")
    if value[0] == 0x89:
        return run_entry_creation_evidence_from_storage(value)
    if value[0] == 0x7B:
        return creation_operation_evidence_from_storage(value)
    raise _fail("Run creation evidence has no admitted family")


def attach_operation_evidence_to_storage_bytes(command: AttachSessionCommand) -> bytes:
    try:
        command = revalidate_run_model(command, AttachSessionCommand)
        return canonical_run_operation_bytes(command)
    except (AttributeError, TypeError, ValueError) as exc:
        raise _fail("Run attachment operation evidence is invalid") from exc


def attach_operation_evidence_from_storage(value: bytes) -> AttachSessionCommand:
    _strict_object(value)
    try:
        command = AttachSessionCommand.model_validate_json(value)
        command = revalidate_run_model(command, AttachSessionCommand)
    except (TypeError, ValueError) as exc:
        raise _fail("Run attachment operation evidence is invalid") from exc
    if attach_operation_evidence_to_storage_bytes(command) != value:
        raise _fail("Run attachment operation evidence is non-canonical")
    return command


def binding_operation_evidence_to_storage_bytes(
    command: BindPlayerCharacterCommand,
) -> bytes:
    try:
        command = revalidate_run_model(command, BindPlayerCharacterCommand)
        return canonical_run_operation_bytes(command)
    except (AttributeError, TypeError, ValueError) as exc:
        raise _fail("Run binding operation evidence is invalid") from exc


def binding_operation_evidence_from_storage(
    value: bytes,
) -> BindPlayerCharacterCommand:
    _strict_object(value)
    try:
        command = BindPlayerCharacterCommand.model_validate_json(value)
        command = revalidate_run_model(
            command,
            BindPlayerCharacterCommand,
        )
    except (TypeError, ValueError) as exc:
        raise _fail("Run binding operation evidence is invalid") from exc
    if binding_operation_evidence_to_storage_bytes(command) != value:
        raise _fail("Run binding operation evidence is non-canonical")
    return command


def participation_from_storage(
    stored: StoredRunSessionParticipationRecord,
) -> RunSessionParticipationReference:
    _require_version(stored.joined_state_version, "joined_state_version")
    _require_utc(stored.joined_at, "joined_at")
    try:
        participation = RunSessionParticipationReference(
            session_id=stored.session_id,
            run_id=revalidate_run_model(stored.run_id, RunId),
            continuous_story_line_id=revalidate_run_model(
                stored.continuous_story_line_id,
                ContinuousStoryLineId,
            ),
            joined_state_version=RunStateVersion(
                value=stored.joined_state_version
            ),
            operation_id=revalidate_run_model(
                stored.operation_id,
                RunOperationId,
            ),
            source_reference=revalidate_run_model(
                stored.source_reference,
                RunAuthoritySourceRef,
            ),
        )
        return revalidate_run_model(
            participation,
            RunSessionParticipationReference,
        )
    except (AttributeError, TypeError, ValueError) as exc:
        raise _fail("stored Run participation is invalid") from exc


_BINDING_ENVELOPE_FIELDS = (
    "binding_player_character_id",
    "binding_contract_version",
    "binding_record_revision",
    "binding_state",
    "binding_operation_id",
    "binding_authority_source_ref",
    "bound_at",
    "inactivated_at",
)


def _binding_from_storage(
    stored: StoredCurrentRunRecord | StoredRunRevisionRecord,
) -> ReservedPlayerCharacterBinding | None:
    values = tuple(
        getattr(stored, field_name)
        for field_name in _BINDING_ENVELOPE_FIELDS
    )
    present = tuple(value is not None for value in values)
    required_present = present[:-1]
    is_current = isinstance(stored, StoredCurrentRunRecord)
    if not any(present):
        if stored.active_player_character_id is not None:
            raise _fail(
                "unbound current Run has an active-character backstop"
            )
        return None
    if not all(required_present):
        raise _fail("stored Run binding evidence is partial")
    if not is_current and stored.active_player_character_id is not None:
        raise _fail(
            "immutable Run revision has a current-only active backstop"
        )
    _require_version(
        stored.binding_record_revision,
        "binding_record_revision",
    )
    _require_utc(stored.bound_at, "bound_at")
    if stored.inactivated_at is not None:
        _require_utc(stored.inactivated_at, "inactivated_at")
    if (
        stored.binding_state != "active"
        or stored.inactivated_at is not None
    ):
        raise _fail("P4-S1 stored binding must be complete and active")
    if (
        is_current
        and stored.active_player_character_id
        != stored.binding_player_character_id
    ):
        raise _fail(
            "active binding does not match the current-row backstop"
        )
    try:
        binding = ReservedPlayerCharacterBinding(
            run_id=revalidate_run_model(stored.run_id, RunId),
            continuous_story_line_id=revalidate_run_model(
                stored.continuous_story_line_id,
                ContinuousStoryLineId,
            ),
            applicable_character_reference=ApplicableCharacterReference(
                player_character_id=PlayerCharacterId(
                    value=stored.binding_player_character_id
                ),
                contract_version=PlayerCharacterContractVersion(
                    stored.binding_contract_version
                ),
                record_revision=PlayerCharacterRevision(
                    value=stored.binding_record_revision
                ),
            ),
            binding_state=stored.binding_state,
            binding_operation_id=RunOperationId(
                value=stored.binding_operation_id
            ),
            binding_authority_source_ref=RunAuthoritySourceRef(
                value=stored.binding_authority_source_ref
            ),
            bound_at=stored.bound_at,
            inactivated_at=stored.inactivated_at,
        )
        return revalidate_run_model(
            binding,
            ReservedPlayerCharacterBinding,
        )
    except (AttributeError, TypeError, ValueError) as exc:
        raise _fail("stored Run binding evidence is invalid") from exc


def _run_from_core(
    stored: StoredCurrentRunRecord | StoredRunRevisionRecord,
    *,
    participations: tuple[RunSessionParticipationReference, ...],
) -> CanonicalRun:
    _require_version(stored.state_version, "state_version")
    _require_optional_version(stored.prior_state_version, "prior_state_version")
    _require_utc(stored.creation_occurred_at, "creation_occurred_at")
    _require_utc(stored.occurred_at, "occurred_at")
    _require_utc(stored.created_at, "created_at")
    if isinstance(stored, StoredCurrentRunRecord):
        _require_utc(stored.updated_at, "updated_at")
        if (
            stored.created_at != stored.creation_occurred_at
            or stored.updated_at != stored.occurred_at
        ):
            raise _fail("stored current Run audit times are inconsistent")
    elif stored.created_at != stored.occurred_at:
        raise _fail("stored Run revision audit time is inconsistent")
    binding = _binding_from_storage(stored)
    try:
        run_id = revalidate_run_model(stored.run_id, RunId)
        line_id = revalidate_run_model(
            stored.continuous_story_line_id,
            ContinuousStoryLineId,
        )
        creation_operation_id = revalidate_run_model(
            stored.creation_operation_id,
            RunOperationId,
        )
        creation_source = revalidate_run_model(
            stored.creation_source_reference,
            RunAuthoritySourceRef,
        )
        operation_id = revalidate_run_model(
            stored.operation_id,
            RunOperationId,
        )
        source = revalidate_run_model(
            stored.source_reference,
            RunAuthoritySourceRef,
        )
        lifecycle = RunLifecycleStatus(stored.lifecycle_status)
        mutation_kind = RunMutationKind(stored.mutation_kind)
        creation = RunMutationProvenance(
            target_run_id=run_id,
            target_continuous_story_line_id=line_id,
            prior_state_version=None,
            resulting_state_version=RunStateVersion(value=1),
            mutation_kind=RunMutationKind.CREATE,
            operation_id=creation_operation_id,
            source_reference=creation_source,
            occurred_at=stored.creation_occurred_at,
        )
        current = RunMutationProvenance(
            target_run_id=run_id,
            target_continuous_story_line_id=line_id,
            prior_state_version=(
                RunStateVersion(value=stored.prior_state_version)
                if stored.prior_state_version is not None
                else None
            ),
            resulting_state_version=RunStateVersion(
                value=stored.state_version
            ),
            mutation_kind=mutation_kind,
            operation_id=operation_id,
            source_reference=source,
            occurred_at=stored.occurred_at,
        )
        return validate_canonical_run(
            CanonicalRun(
                run_id=run_id,
                continuous_story_line_id=line_id,
                lifecycle_status=lifecycle,
                state_version=RunStateVersion(value=stored.state_version),
                creation_provenance=creation,
                current_mutation_provenance=current,
                trusted_participation_references=participations,
                player_character_binding=binding,
            )
        )
    except (AttributeError, TypeError, ValueError) as exc:
        raise _fail("stored canonical Run state is invalid") from exc


def canonical_run_from_revision_storage(
    stored: StoredRunRevisionRecord,
    *,
    participations: tuple[RunSessionParticipationReference, ...],
) -> CanonicalRun:
    return _run_from_core(stored, participations=participations)


def canonical_run_from_current_storage(
    stored: StoredCurrentRunRecord,
    *,
    participations: tuple[RunSessionParticipationReference, ...],
) -> CanonicalRun:
    return _run_from_core(stored, participations=participations)


def creation_receipt_from_storage(
    stored: StoredRunCreationReceiptRecord,
) -> StoredRunSuccessReceipt:
    _require_fingerprint(stored.fingerprint, "fingerprint")
    _require_version(stored.resulting_state_version, "resulting_state_version")
    _require_utc(stored.created_at, "created_at")
    _require_bytes(stored.receipt_canonical, "receipt_canonical")
    _require_bytes(
        stored.operation_evidence_canonical,
        "operation_evidence_canonical",
    )
    receipt = _receipt_from_storage(stored.receipt_canonical)
    command = creation_evidence_from_storage(
        stored.operation_evidence_canonical
    )
    if isinstance(command, RunEntryCreationEvidence):
        _, fingerprint = run_entry_creation_fingerprint(command)
    else:
        _, fingerprint = create_run_fingerprint(command)
    result = receipt.result
    if (
        receipt.key.operation_namespace is not RunOperationNamespace.CREATE_V1
        or receipt.key.run_id is not None
        or receipt.key.operation_namespace.value != stored.operation_namespace
        or receipt.key.operation_id != stored.operation_id
        or fingerprint_to_storage_bytes(receipt.fingerprint) != stored.fingerprint
        or receipt.fingerprint != fingerprint
        or receipt.command_kind is not RunMutationKind.CREATE
        or receipt.command_kind.value != stored.command_kind
        or result.result_schema_version != CREATE_RUN_RESULT_SCHEMA_VERSION
        or result.result_schema_version != stored.result_schema_version
        or result.run_id != stored.result_run_id
        or result.continuous_story_line_id
        != stored.result_continuous_story_line_id
        or result.lifecycle_status.value != stored.resulting_lifecycle_status
        or result.resulting_state_version.value
        != stored.resulting_state_version
        or result.participation_reference is not None
    ):
        raise _fail("stored Run creation receipt columns are inconsistent")
    return receipt


def mutation_receipt_from_storage(
    stored: StoredRunMutationReceiptRecord,
) -> StoredRunSuccessReceipt:
    _require_fingerprint(stored.fingerprint, "fingerprint")
    _require_version(stored.expected_state_version, "expected_state_version")
    _require_version(stored.resulting_state_version, "resulting_state_version")
    _require_utc(stored.created_at, "created_at")
    _require_bytes(stored.receipt_canonical, "receipt_canonical")
    _require_bytes(
        stored.operation_evidence_canonical,
        "operation_evidence_canonical",
    )
    receipt = _receipt_from_storage(stored.receipt_canonical)
    result = receipt.result
    if (
        receipt.key.run_id != stored.run_id
        or receipt.key.operation_namespace.value != stored.operation_namespace
        or receipt.key.operation_id != stored.operation_id
        or fingerprint_to_storage_bytes(receipt.fingerprint) != stored.fingerprint
        or result.result_schema_version != stored.result_schema_version
        or result.resulting_state_version.value
        != stored.resulting_state_version
        or stored.resulting_state_version
        != stored.expected_state_version + 1
        or result.run_id != stored.result_run_id
        or result.run_id != stored.run_id
        or result.continuous_story_line_id
        != stored.result_continuous_story_line_id
        or result.lifecycle_status.value != stored.resulting_lifecycle_status
    ):
        raise _fail("stored Run mutation receipt columns are inconsistent")
    if stored.command_kind == RunMutationKind.ATTACH_SESSION.value:
        reserved = (
            stored.result_player_character_id,
            stored.result_character_contract_version,
            stored.result_character_record_revision,
        )
        if any(value is not None for value in reserved):
            raise _fail(
                "Run attachment receipt populated binding result fields"
            )
        if (
            stored.participation_session_id is None
            or stored.participation_operation_id is None
            or stored.participation_source_reference is None
        ):
            raise _fail(
                "Run attachment receipt participation fields are incomplete"
            )
        command = attach_operation_evidence_from_storage(
            stored.operation_evidence_canonical
        )
        _, fingerprint = attach_session_fingerprint(
            command,
            operation_id=stored.operation_id,
        )
        participation = result.participation_reference
        if (
            receipt.key.operation_namespace
            is not RunOperationNamespace.ATTACH_SESSION_V1
            or receipt.fingerprint != fingerprint
            or receipt.command_kind is not RunMutationKind.ATTACH_SESSION
            or result.result_schema_version
            != ATTACH_SESSION_RESULT_SCHEMA_VERSION
            or command.expected_state_version.value
            != stored.expected_state_version
            or participation is None
            or result.applicable_character_reference is not None
            or participation.session_id
            != stored.participation_session_id
            or participation.operation_id.value
            != stored.participation_operation_id
            or participation.source_reference.value
            != stored.participation_source_reference
        ):
            raise _fail(
                "stored Run attachment receipt columns are inconsistent"
            )
    elif stored.command_kind == RunMutationKind.BIND_PLAYER_CHARACTER.value:
        participation_fields = (
            stored.participation_session_id,
            stored.participation_operation_id,
            stored.participation_source_reference,
        )
        binding_result_fields = (
            stored.result_player_character_id,
            stored.result_character_contract_version,
            stored.result_character_record_revision,
        )
        if any(value is not None for value in participation_fields):
            raise _fail(
                "Run binding receipt populated participation fields"
            )
        if not all(value is not None for value in binding_result_fields):
            raise _fail("Run binding receipt result fields are incomplete")
        _require_version(
            stored.result_character_record_revision,
            "result_character_record_revision",
        )
        command = binding_operation_evidence_from_storage(
            stored.operation_evidence_canonical
        )
        _, fingerprint = bind_player_character_fingerprint(
            command,
            operation_id=stored.operation_id,
        )
        reference = result.applicable_character_reference
        if (
            receipt.key.operation_namespace
            is not RunOperationNamespace.BIND_PLAYER_CHARACTER_V1
            or receipt.fingerprint != fingerprint
            or receipt.command_kind
            is not RunMutationKind.BIND_PLAYER_CHARACTER
            or result.result_schema_version
            != BIND_PLAYER_CHARACTER_RESULT_SCHEMA_VERSION
            or command.expected_state_version.value
            != stored.expected_state_version
            or result.participation_reference is not None
            or reference is None
            or reference.player_character_id.value
            != stored.result_player_character_id
            or reference.contract_version.value
            != stored.result_character_contract_version
            or reference.record_revision.value
            != stored.result_character_record_revision
            or command.target_player_character_id
            != reference.player_character_id
        ):
            raise _fail(
                "stored Run binding receipt columns are inconsistent"
            )
    else:
        raise _fail("stored Run mutation receipt command is not admitted")
    return receipt


def _same_core(
    current: StoredCurrentRunRecord,
    revision: StoredRunRevisionRecord,
) -> bool:
    names = (
        "run_id",
        "continuous_story_line_id",
        "lifecycle_status",
        "state_version",
        "creation_operation_id",
        "creation_source_reference",
        "creation_occurred_at",
        "prior_state_version",
        "mutation_kind",
        "operation_id",
        "source_reference",
        "occurred_at",
        *_BINDING_ENVELOPE_FIELDS,
    )
    return all(getattr(current, name) == getattr(revision, name) for name in names)


def validate_stored_run_record_set(
    *,
    creation_receipt: StoredRunCreationReceiptRecord | None,
    mutation_receipts: tuple[StoredRunMutationReceiptRecord, ...],
    revisions: tuple[StoredRunRevisionRecord, ...] | None,
    current: StoredCurrentRunRecord | None,
    participations: tuple[StoredRunSessionParticipationRecord, ...],
    referenced_player_character_revision: (
        CanonicalPlayerCharacter | None
    ) = None,
) -> CanonicalRun:
    """Reconstruct one complete Run history or fail closed."""

    if creation_receipt is None:
        raise _fail("Run creation receipt record is required")
    if not revisions:
        raise _fail("Run revision history is required")
    if current is None:
        raise _fail("current Run record is required")

    ordered_revisions = tuple(sorted(revisions, key=lambda item: item.state_version))
    versions = tuple(item.state_version for item in ordered_revisions)
    if versions != tuple(range(1, len(ordered_revisions) + 1)):
        raise _fail("Run revision history is missing or discontinuous")
    if current.state_version != versions[-1] or not _same_core(
        current,
        ordered_revisions[-1],
    ):
        raise _fail("current Run row does not equal latest immutable revision")

    ordered_participations = tuple(
        sorted(participations, key=lambda item: item.joined_state_version)
    )
    decoded_participations = tuple(
        participation_from_storage(item) for item in ordered_participations
    )
    joined_versions = tuple(
        item.joined_state_version.value for item in decoded_participations
    )
    if len({item.session_id for item in decoded_participations}) != len(
        decoded_participations
    ):
        raise _fail("Run participation Session identity is duplicated")

    history: list[CanonicalRun] = []
    for stored_revision in ordered_revisions:
        revision_participations = tuple(
            item
            for item in decoded_participations
            if item.joined_state_version.value <= stored_revision.state_version
        )
        history.append(
            canonical_run_from_revision_storage(
                stored_revision,
                participations=revision_participations,
            )
        )
    current_run = canonical_run_from_current_storage(
        current,
        participations=decoded_participations,
    )
    if current_run != history[-1]:
        raise _fail("current Run reconstruction does not equal latest history")
    if any(
        item.run_id != current_run.run_id
        or item.continuous_story_line_id
        != current_run.continuous_story_line_id
        for item in history
    ):
        raise _fail("Run history substituted an identity or story line")
    canonical_creation_provenance = history[0].creation_provenance
    if any(
        item.creation_provenance != canonical_creation_provenance
        for item in (*history[1:], current_run)
    ):
        raise _fail("Run history rewrote immutable creation provenance")
    expected_joined_versions = tuple(
        item.state_version.value
        for item in history[1:]
        if (
            item.current_mutation_provenance.mutation_kind
            is RunMutationKind.ATTACH_SESSION
        )
    )
    if joined_versions != expected_joined_versions:
        raise _fail("Run participation history is missing or discontinuous")

    binding_versions = tuple(
        item.state_version.value
        for item in history
        if (
            item.current_mutation_provenance.mutation_kind
            is RunMutationKind.BIND_PLAYER_CHARACTER
        )
    )
    current_binding = current_run.player_character_binding
    if current_binding is None:
        if binding_versions or any(
            item.player_character_binding is not None for item in history
        ):
            raise _fail("Run history lost surviving binding evidence")
        if referenced_player_character_revision is not None:
            raise _fail(
                "unbound Run has unexpected referenced character evidence"
            )
    else:
        if len(binding_versions) != 1:
            raise _fail(
                "Run history must contain exactly one binding transition"
            )
        binding_version = binding_versions[0]
        for item in history:
            expected_binding = (
                None
                if item.state_version.value < binding_version
                else current_binding
            )
            if item.player_character_binding != expected_binding:
                raise _fail(
                    "Run history replaced or contradicted its binding"
                )
        if referenced_player_character_revision is None:
            raise _fail(
                "referenced immutable player-character revision is missing"
            )
        try:
            referenced_record = validate_canonical_player_character(
                referenced_player_character_revision
            )
        except (AttributeError, TypeError, ValueError) as exc:
            raise _fail(
                "referenced immutable player-character revision is invalid"
            ) from exc
        reference = current_binding.applicable_character_reference
        if (
            referenced_record.player_character_id
            != reference.player_character_id
            or referenced_record.contract_version
            != reference.contract_version
            or referenced_record.record_revision
            != reference.record_revision
            or referenced_record.lifecycle
            is not PlayerCharacterLifecycle.ACTIVE
        ):
            raise _fail(
                "binding reference does not match its immutable "
                "player-character revision"
            )

    creation = creation_receipt_from_storage(creation_receipt)
    creation_command = creation_evidence_from_storage(
        creation_receipt.operation_evidence_canonical
    )
    initial = history[0]
    if (
        creation.result != creation_result(initial)
        or creation.key.operation_id
        != initial.creation_provenance.operation_id
        or (
            creation_command.trusted_run_source.source_reference
            if isinstance(creation_command, RunEntryCreationEvidence)
            else creation_command.source_reference
        )
        != initial.creation_provenance.source_reference
        or creation_receipt.created_at
        != initial.creation_provenance.occurred_at
    ):
        raise _fail("Run creation receipt does not bind revision one")

    decoded_mutations = tuple(
        (stored, mutation_receipt_from_storage(stored))
        for stored in mutation_receipts
    )
    if len(decoded_mutations) != len(history) - 1:
        raise _fail("Run mutation receipts do not cover successor history")
    mutation_by_version: dict[
        int,
        tuple[StoredRunMutationReceiptRecord, StoredRunSuccessReceipt],
    ] = {}
    for stored, receipt in decoded_mutations:
        if stored.resulting_state_version in mutation_by_version:
            raise _fail("multiple Run receipts claim one successor revision")
        mutation_by_version[stored.resulting_state_version] = (stored, receipt)
    if set(mutation_by_version) != set(range(2, len(history) + 1)):
        raise _fail("Run mutation receipts do not bind every successor revision")

    for version in range(2, len(history) + 1):
        before = history[version - 2]
        after = history[version - 1]
        stored, receipt = mutation_by_version[version]
        provenance = after.current_mutation_provenance
        if (
            receipt.key.run_id != after.run_id
            or receipt.key.operation_id != provenance.operation_id
            or stored.run_id != after.run_id
            or stored.expected_state_version != before.state_version.value
            or stored.created_at != provenance.occurred_at
        ):
            raise _fail("Run mutation evidence does not bind adjacent history")
        if provenance.mutation_kind is RunMutationKind.ATTACH_SESSION:
            command = attach_operation_evidence_from_storage(
                stored.operation_evidence_canonical
            )
            if not after.trusted_participation_references:
                raise _fail(
                    "Run attachment history has no participation evidence"
                )
            participation = after.trusted_participation_references[-1]
            stored_participation = next(
                (
                    item
                    for item in ordered_participations
                    if item.joined_state_version == version
                ),
                None,
            )
            if (
                receipt.result != attach_session_result(after)
                or command.run_id != after.run_id
                or command.continuous_story_line_id
                != after.continuous_story_line_id
                or command.session_id != participation.session_id
                or command.expected_state_version != before.state_version
                or command.source_reference != provenance.source_reference
                or participation.operation_id != provenance.operation_id
                or participation.source_reference
                != provenance.source_reference
                or stored_participation is None
                or stored_participation.joined_at
                != provenance.occurred_at
                or after.player_character_binding
                != before.player_character_binding
            ):
                raise _fail(
                    "Run attachment evidence does not bind adjacent history"
                )
        elif (
            provenance.mutation_kind
            is RunMutationKind.BIND_PLAYER_CHARACTER
        ):
            command = binding_operation_evidence_from_storage(
                stored.operation_evidence_canonical
            )
            binding = after.player_character_binding
            if (
                binding is None
                or before.player_character_binding is not None
                or receipt.result != bind_player_character_result(after)
                or command.run_id != after.run_id
                or command.continuous_story_line_id
                != after.continuous_story_line_id
                or command.expected_state_version != before.state_version
                or command.source_reference != provenance.source_reference
                or command.target_player_character_id
                != binding.applicable_character_reference.player_character_id
                or binding.binding_operation_id
                != provenance.operation_id
                or binding.binding_authority_source_ref
                != provenance.source_reference
                or binding.bound_at != provenance.occurred_at
                or any(
                    item.joined_state_version.value == version
                    for item in decoded_participations
                )
            ):
                raise _fail(
                    "Run binding evidence does not bind adjacent history"
                )
        else:
            raise _fail("Run history contains an unsupported mutation")

    return current_run
