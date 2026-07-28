"""Offline, fail-closed persistence carriers for structured player characters.

This module deliberately contains no ORM, repository, clock, or I/O code.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from typing import Any, Callable

from deviation_protocol.application.player_character_operations import (
    CharacterOperationFingerprint,
    CharacterCreationCommand,
    CharacterMutationCommand,
    CreationReceiptKey,
    MutationReceiptKey,
    StoredCreationSuccessReceipt,
    StoredMutationSuccessReceipt,
    validate_stored_creation_success_receipt,
    validate_stored_mutation_success_receipt,
    creation_fingerprint,
    evaluate_mutation_policy,
    mutation_fingerprint,
)
from deviation_protocol.domain.player_character import (
    AuthoritySourceRef,
    CanonicalPlayerCharacter,
    ControllerBindingRef,
    MAX_CANONICAL_INTEGER,
    PlayerCharacterAuthorityClass,
    PlayerCharacterId,
    PlayerCharacterLifecycle,
    PlayerCharacterMutationKind,
    PlayerCharacterRevision,
    canonical_character_operation_bytes,
    revalidate_player_character_model,
    validate_canonical_player_character,
)
from deviation_protocol.domain.player_character_policies import (
    CreatePlayerCharacterPolicy,
)


class PlayerCharacterStoredRecordIntegrityError(ValueError):
    """Persisted player-character evidence is malformed or cross-bound."""


@dataclass(frozen=True, slots=True)
class StoredControllerBindingRecord:
    controller_binding: ControllerBindingRef
    created_at: datetime


@dataclass(frozen=True, slots=True)
class StoredPlayerCharacterIdAllocationRecord:
    player_character_id: PlayerCharacterId
    created_at: datetime


@dataclass(frozen=True, slots=True)
class StoredCurrentPlayerCharacterRecord:
    player_character_id: PlayerCharacterId
    contract_version: str
    record_revision: int
    controller_binding: ControllerBindingRef
    lifecycle: str
    record_canonical: bytes
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class StoredPlayerCharacterRevisionRecord:
    player_character_id: PlayerCharacterId
    record_revision: int
    contract_version: str
    controller_binding: ControllerBindingRef
    lifecycle: str
    prior_revision: int | None
    mutation_kind: str
    authority_class: str
    source_reference: AuthoritySourceRef
    record_canonical: bytes
    created_at: datetime


@dataclass(frozen=True, slots=True)
class StoredCreationReceiptRecord:
    controller_binding: ControllerBindingRef
    operation_namespace: str
    operation_id: str
    fingerprint: bytes
    command_kind: str
    result_schema_version: str
    result_player_character_id: PlayerCharacterId
    result_contract_version: str
    resulting_revision: int
    resulting_lifecycle: str
    result_record_fingerprint: bytes
    receipt_canonical: bytes
    operation_evidence_canonical: bytes
    created_at: datetime


@dataclass(frozen=True, slots=True)
class StoredMutationReceiptRecord:
    player_character_id: PlayerCharacterId
    operation_namespace: str
    operation_id: str
    fingerprint: bytes
    command_kind: str
    result_schema_version: str
    expected_revision: int
    result_player_character_id: PlayerCharacterId
    result_contract_version: str
    result_command_kind: str
    command_result: str
    resulting_revision: int
    resulting_lifecycle: str
    before_record_fingerprint: bytes
    after_record_fingerprint: bytes
    receipt_canonical: bytes
    operation_evidence_canonical: bytes
    created_at: datetime


def _fail(message: str) -> PlayerCharacterStoredRecordIntegrityError:
    return PlayerCharacterStoredRecordIntegrityError(message)


def _require_exact_revision(value: Any, field_name: str) -> None:
    if type(value) is not int:
        raise _fail(f"{field_name} must be an exact integer")
    if not 1 <= value <= MAX_CANONICAL_INTEGER:
        raise _fail(f"{field_name} is outside the stored revision domain")


def _require_optional_exact_revision(value: Any, field_name: str) -> None:
    if value is not None:
        _require_exact_revision(value, field_name)


def _require_non_empty_bytes(value: Any, field_name: str) -> None:
    if type(value) is not bytes or not value:
        raise _fail(f"{field_name} must be non-empty immutable bytes")


def _require_fingerprint_bytes(value: Any, field_name: str) -> None:
    if type(value) is not bytes or len(value) != 32:
        raise _fail(
            f"{field_name} must contain exactly 32 immutable bytes"
        )


def _strict_object(value: bytes) -> dict[str, Any]:
    _require_non_empty_bytes(value, "stored canonical value")
    try:
        decoded = value.decode("utf-8")
        result = json.loads(
            decoded,
            parse_float=lambda _value: (_ for _ in ()).throw(_fail("JSON floats are not permitted")),
            parse_constant=lambda _value: (_ for _ in ()).throw(_fail("non-standard JSON constant")),
            object_pairs_hook=lambda pairs: _unique_object(pairs),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        if isinstance(exc, PlayerCharacterStoredRecordIntegrityError):
            raise
        raise _fail("stored canonical value is not strict UTF-8 JSON") from exc
    if type(result) is not dict:
        raise _fail("stored canonical value must contain exactly one object")
    return result


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _fail("stored canonical JSON has duplicate keys")
        result[key] = value
    return result


def fingerprint_to_storage_bytes(value: CharacterOperationFingerprint) -> bytes:
    try:
        raw = bytes.fromhex(value.value)
    except (AttributeError, TypeError, ValueError) as exc:
        raise _fail("operation fingerprint is invalid") from exc
    if len(raw) != 32 or raw.hex() != value.value:
        raise _fail("operation fingerprint must be canonical lowercase SHA-256")
    return raw


def fingerprint_from_storage_bytes(value: bytes) -> CharacterOperationFingerprint:
    if type(value) is not bytes or len(value) != 32:
        raise _fail("stored fingerprint must contain exactly 32 bytes")
    try:
        return CharacterOperationFingerprint(value=value.hex())
    except ValueError as exc:
        raise _fail("stored fingerprint is invalid") from exc


def canonical_record_to_storage_bytes(value: CanonicalPlayerCharacter) -> bytes:
    try:
        return canonical_character_operation_bytes(validate_canonical_player_character(value))
    except (AttributeError, TypeError, ValueError) as exc:
        raise _fail("canonical player-character record is invalid") from exc


def _canonical_record_from_storage(value: bytes) -> CanonicalPlayerCharacter:
    payload = _strict_object(value)
    try:
        record = CanonicalPlayerCharacter.model_validate_json(value)
        record = validate_canonical_player_character(record)
    except (TypeError, ValueError) as exc:
        raise _fail("stored canonical player-character record is invalid") from exc
    if canonical_record_to_storage_bytes(record) != value:
        raise _fail("stored canonical player-character record is non-canonical")
    return record


def _check_record_columns(record: CanonicalPlayerCharacter, stored: Any) -> None:
    provenance = record.authority_provenance
    if (
        record.player_character_id != stored.player_character_id
        or record.contract_version.value != stored.contract_version
        or record.record_revision.value != stored.record_revision
        or record.controller_binding != stored.controller_binding
        or record.lifecycle.value != stored.lifecycle
    ):
        raise _fail("stored record columns do not match canonical record")
    if hasattr(stored, "prior_revision") and (
        (provenance.prior_revision.value if provenance.prior_revision else None) != stored.prior_revision
        or provenance.mutation_kind.value != stored.mutation_kind
        or provenance.authority_class.value != stored.authority_class
        or provenance.source_reference != stored.source_reference
    ):
        raise _fail("stored revision provenance does not match canonical record")


def canonical_record_from_current_storage(stored: StoredCurrentPlayerCharacterRecord) -> CanonicalPlayerCharacter:
    _require_exact_revision(
        stored.record_revision,
        "stored current record_revision",
    )
    _require_non_empty_bytes(
        stored.record_canonical,
        "stored current record_canonical",
    )
    record = _canonical_record_from_storage(stored.record_canonical)
    _check_record_columns(record, stored)
    return record


def canonical_record_from_revision_storage(stored: StoredPlayerCharacterRevisionRecord) -> CanonicalPlayerCharacter:
    _require_exact_revision(
        stored.record_revision,
        "stored revision record_revision",
    )
    _require_optional_exact_revision(
        stored.prior_revision,
        "stored revision prior_revision",
    )
    _require_non_empty_bytes(
        stored.record_canonical,
        "stored revision record_canonical",
    )
    record = _canonical_record_from_storage(stored.record_canonical)
    _check_record_columns(record, stored)
    return record


def _receipt_to_bytes(value: StoredCreationSuccessReceipt | StoredMutationSuccessReceipt) -> bytes:
    try:
        encoded = canonical_character_operation_bytes(value)
    except (TypeError, ValueError) as exc:
        raise _fail("stored receipt is invalid") from exc
    if not 1 <= len(encoded) <= 65_536:
        raise _fail("stored receipt canonical bytes are outside their bounds")
    return encoded


def creation_receipt_to_storage_bytes(value: StoredCreationSuccessReceipt) -> bytes:
    try:
        value = validate_stored_creation_success_receipt(value)
    except (TypeError, ValueError) as exc:
        raise _fail("creation receipt is invalid") from exc
    return _receipt_to_bytes(value)


def mutation_receipt_to_storage_bytes(value: StoredMutationSuccessReceipt) -> bytes:
    try:
        value = validate_stored_mutation_success_receipt(value)
    except (TypeError, ValueError) as exc:
        raise _fail("mutation receipt is invalid") from exc
    return _receipt_to_bytes(value)


def creation_operation_evidence_to_storage_bytes(
    command: CharacterCreationCommand,
    *,
    source_reference: AuthoritySourceRef,
) -> bytes:
    try:
        creation_fingerprint(command)
        source_reference = revalidate_player_character_model(
            source_reference,
            AuthoritySourceRef,
        )
        return canonical_character_operation_bytes(
            {
                "command": command,
                "source_reference": source_reference,
            }
        )
    except (TypeError, ValueError) as exc:
        raise _fail("creation operation evidence is invalid") from exc


def _creation_operation_evidence_from_storage(
    value: bytes,
) -> tuple[CharacterCreationCommand, AuthoritySourceRef]:
    payload = _strict_object(value)
    if set(payload) != {"command", "source_reference"}:
        raise _fail("creation operation evidence has an invalid shape")
    try:
        command = CharacterCreationCommand.model_validate_json(
            canonical_character_operation_bytes(payload["command"])
        )
        source_reference = AuthoritySourceRef.model_validate_json(
            canonical_character_operation_bytes(payload["source_reference"])
        )
    except (TypeError, ValueError) as exc:
        raise _fail("creation operation evidence is invalid") from exc
    if (
        creation_operation_evidence_to_storage_bytes(
            command,
            source_reference=source_reference,
        )
        != value
    ):
        raise _fail("creation operation evidence is non-canonical")
    return command, source_reference


def creation_operation_evidence_from_storage(value: bytes) -> CharacterCreationCommand:
    command, _ = _creation_operation_evidence_from_storage(value)
    return command


def mutation_operation_evidence_to_storage_bytes(command: CharacterMutationCommand) -> bytes:
    try:
        return canonical_character_operation_bytes(command)
    except (TypeError, ValueError) as exc:
        raise _fail("mutation operation evidence is invalid") from exc


def mutation_operation_evidence_from_storage(value: bytes) -> CharacterMutationCommand:
    _strict_object(value)
    try:
        command = CharacterMutationCommand.model_validate_json(value)
    except (TypeError, ValueError) as exc:
        raise _fail("mutation operation evidence is invalid") from exc
    if mutation_operation_evidence_to_storage_bytes(command) != value:
        raise _fail("mutation operation evidence is non-canonical")
    return command


def _receipt_from_bytes(value: bytes, validator: Callable[[bytes], Any], encoder: Callable[[Any], bytes]) -> Any:
    _strict_object(value)
    try:
        receipt = validator(value)
    except (TypeError, ValueError) as exc:
        raise _fail("stored receipt is invalid") from exc
    if encoder(receipt) != value:
        raise _fail("stored receipt is non-canonical")
    return receipt


def creation_receipt_from_storage(stored: StoredCreationReceiptRecord) -> StoredCreationSuccessReceipt:
    _require_fingerprint_bytes(stored.fingerprint, "fingerprint")
    _require_fingerprint_bytes(
        stored.result_record_fingerprint,
        "result_record_fingerprint",
    )
    _require_exact_revision(
        stored.resulting_revision,
        "stored creation resulting_revision",
    )
    _require_non_empty_bytes(
        stored.receipt_canonical,
        "stored creation receipt_canonical",
    )
    _require_non_empty_bytes(
        stored.operation_evidence_canonical,
        "stored creation operation_evidence_canonical",
    )
    receipt = _receipt_from_bytes(stored.receipt_canonical, validate_stored_creation_success_receipt, creation_receipt_to_storage_bytes)
    result = receipt.result
    command, _ = _creation_operation_evidence_from_storage(
        stored.operation_evidence_canonical
    )
    _, fingerprint = creation_fingerprint(command)
    if (
        receipt.key.controller_binding != stored.controller_binding or receipt.key.operation_namespace.value != stored.operation_namespace
        or receipt.key.operation_id.value != stored.operation_id or fingerprint_to_storage_bytes(receipt.fingerprint) != stored.fingerprint
        or receipt.command_kind != stored.command_kind or receipt.result_schema_version != stored.result_schema_version
        or result.player_character_id != stored.result_player_character_id or result.contract_version.value != stored.result_contract_version
        or result.resulting_revision.value != stored.resulting_revision or result.resulting_lifecycle.value != stored.resulting_lifecycle
        or fingerprint != receipt.fingerprint
    ):
        raise _fail("creation receipt columns do not match canonical receipt")
    return receipt


def mutation_receipt_from_storage(stored: StoredMutationReceiptRecord) -> StoredMutationSuccessReceipt:
    _require_fingerprint_bytes(stored.fingerprint, "fingerprint")
    _require_fingerprint_bytes(
        stored.before_record_fingerprint,
        "before_record_fingerprint",
    )
    _require_fingerprint_bytes(
        stored.after_record_fingerprint,
        "after_record_fingerprint",
    )
    _require_exact_revision(
        stored.expected_revision,
        "stored mutation expected_revision",
    )
    _require_exact_revision(
        stored.resulting_revision,
        "stored mutation resulting_revision",
    )
    _require_non_empty_bytes(
        stored.receipt_canonical,
        "stored mutation receipt_canonical",
    )
    _require_non_empty_bytes(
        stored.operation_evidence_canonical,
        "stored mutation operation_evidence_canonical",
    )
    receipt = _receipt_from_bytes(stored.receipt_canonical, validate_stored_mutation_success_receipt, mutation_receipt_to_storage_bytes)
    result = receipt.result
    command = mutation_operation_evidence_from_storage(stored.operation_evidence_canonical)
    try:
        _, fingerprint = mutation_fingerprint(
            command,
            operation_id=receipt.key.operation_id,
        )
    except (AttributeError, TypeError, ValueError) as exc:
        raise _fail(
            "mutation operation evidence does not bind receipt operation"
        ) from exc
    if stored.expected_revision != command.expected_revision.value:
        raise _fail(
            "mutation receipt prior revision does not match operation evidence"
        )
    if result.resulting_revision.value != stored.expected_revision + 1:
        raise _fail("mutation receipt revision transition is inconsistent")
    if (
        receipt.key.player_character_id != stored.player_character_id or receipt.key.operation_namespace.value != stored.operation_namespace
        or receipt.key.operation_id.value != stored.operation_id or fingerprint_to_storage_bytes(receipt.fingerprint) != stored.fingerprint
        or receipt.command_kind != stored.command_kind or receipt.result_schema_version != stored.result_schema_version
        or result.player_character_id != stored.result_player_character_id or result.contract_version.value != stored.result_contract_version
        or result.command_kind.value != stored.result_command_kind or result.command_result.value != stored.command_result
        or fingerprint != receipt.fingerprint
        or result.resulting_revision.value != stored.resulting_revision or result.resulting_lifecycle.value != stored.resulting_lifecycle
    ):
        raise _fail("mutation receipt columns do not match canonical receipt")
    return receipt


def canonical_state_record_fingerprint(record: CanonicalPlayerCharacter) -> bytes:
    return hashlib.sha256(canonical_record_to_storage_bytes(record)).digest()


def validate_stored_player_character_record_set(
    *,
    creation_receipt: StoredCreationReceiptRecord | None,
    mutation_receipts: tuple[StoredMutationReceiptRecord, ...],
    revisions: tuple[StoredPlayerCharacterRevisionRecord, ...] | None,
    current: StoredCurrentPlayerCharacterRecord | None,
    controller_binding: StoredControllerBindingRecord | None,
    allocation: StoredPlayerCharacterIdAllocationRecord | None,
) -> None:
    """Fail closed unless all six-family evidence describes one complete history."""
    if creation_receipt is None:
        raise _fail("creation receipt record is required")
    if not revisions:
        raise _fail("revision history record family is required")
    if current is None:
        raise _fail("current player-character record is required")
    if controller_binding is None:
        raise _fail("controller-binding record is required")
    if allocation is None:
        raise _fail("player-character allocation record is required")

    history = tuple(canonical_record_from_revision_storage(item) for item in revisions)
    if tuple(item.record_revision.value for item in history) != tuple(
        range(1, len(history) + 1)
    ):
        raise _fail("revision history is missing or discontinuous")
    if any(item.player_character_id != allocation.player_character_id or item.controller_binding != controller_binding.controller_binding for item in history):
        raise _fail("history substitution detected")
    if canonical_record_from_current_storage(current) != history[-1]:
        raise _fail("current record does not equal latest history")
    creation = creation_receipt_from_storage(creation_receipt)
    if (creation.result.player_character_id != allocation.player_character_id or creation.key.controller_binding != controller_binding.controller_binding or creation.result.resulting_revision.value != 1 or creation_receipt.result_record_fingerprint != canonical_state_record_fingerprint(history[0])):
        raise _fail("creation receipt does not bind revision one")
    creation_command, creation_source_reference = (
        _creation_operation_evidence_from_storage(
            creation_receipt.operation_evidence_canonical
        )
    )
    try:
        authoritative_creation = CreatePlayerCharacterPolicy().create(
            player_character_id=creation.result.player_character_id,
            controller_binding=creation.key.controller_binding,
            character_core=creation_command.character_core,
            narration_preferences=creation_command.narration_preferences,
            source_reference=creation_source_reference,
        )
    except (AttributeError, TypeError, ValueError) as exc:
        raise _fail("creation operation evidence is invalid") from exc
    if authoritative_creation != history[0]:
        raise _fail(
            "creation operation evidence does not bind the initial record"
        )
    decoded_mutation_receipts = tuple(
        (stored, mutation_receipt_from_storage(stored))
        for stored in mutation_receipts
    )
    expected_mutation_transitions = {
        (revision - 1, revision)
        for revision in range(2, len(history) + 1)
    }
    transition_owners: dict[
        tuple[int, int],
        tuple[PlayerCharacterId, str, str],
    ] = {}
    receipt_transitions: dict[
        tuple[PlayerCharacterId, str, str],
        tuple[int, int],
    ] = {}
    for stored, receipt in decoded_mutation_receipts:
        transition = (
            stored.expected_revision,
            receipt.result.resulting_revision.value,
        )
        receipt_identity = (
            receipt.key.player_character_id,
            receipt.key.operation_namespace.value,
            receipt.key.operation_id.value,
        )
        if transition in transition_owners:
            raise _fail(
                "multiple mutation receipts claim one successor transition"
            )
        if receipt_identity in receipt_transitions:
            raise _fail(
                "one mutation receipt operation claims multiple transitions"
            )
        transition_owners[transition] = receipt_identity
        receipt_transitions[receipt_identity] = transition
    if set(transition_owners) != expected_mutation_transitions:
        raise _fail("mutation receipts do not cover the complete successor history")
    for stored, receipt in decoded_mutation_receipts:
        before = receipt.result.resulting_revision.value - 2
        after = receipt.result.resulting_revision.value - 1
        if before < 0 or after >= len(history) or stored.before_record_fingerprint != canonical_state_record_fingerprint(history[before]) or stored.after_record_fingerprint != canonical_state_record_fingerprint(history[after]):
            raise _fail("mutation receipt does not bind adjacent history")
        if receipt.key.player_character_id != allocation.player_character_id or history[after].controller_binding != controller_binding.controller_binding:
            raise _fail("mutation receipt substitution detected")
        command = mutation_operation_evidence_from_storage(
            stored.operation_evidence_canonical
        )
        result_record = history[after]
        provenance = result_record.authority_provenance
        if (
            command.target_player_character_id != allocation.player_character_id
            or command.contract_version != result_record.contract_version
            or command.expected_revision.value != history[before].record_revision.value
            or command.applicable_reference.player_character_id != allocation.player_character_id
            or command.applicable_reference.contract_version != result_record.contract_version
            or command.applicable_reference.record_revision.value != history[before].record_revision.value
            or command.command_kind is not provenance.mutation_kind
            or receipt.result.command_kind is not provenance.mutation_kind
            or provenance.prior_revision != history[before].record_revision
        ):
            raise _fail("mutation operation evidence does not bind adjacent history")
        if (
            receipt.result.player_character_id != result_record.player_character_id
            or receipt.result.contract_version != result_record.contract_version
            or receipt.result.resulting_revision != result_record.record_revision
            or receipt.result.resulting_lifecycle is not result_record.lifecycle
        ):
            raise _fail("mutation receipt result does not bind successor history")
        try:
            decision = evaluate_mutation_policy(
                history[before],
                command=command,
                operation_id=receipt.key.operation_id,
            )
        except (AttributeError, TypeError, ValueError) as exc:
            raise _fail("mutation operation evidence is invalid") from exc
        if (
            not decision.accepted
            or decision.resulting_record != result_record
            or decision.applicable_reference != command.applicable_reference
        ):
            raise _fail(
                "mutation operation result does not equal successor history"
            )
        source = (
            command.confirmation.source_reference
            if command.confirmation is not None
            else command.final_death_evidence.source_reference
            if command.final_death_evidence is not None
            else None
        )
        if source != provenance.source_reference:
            raise _fail("mutation operation evidence provenance mismatch")
