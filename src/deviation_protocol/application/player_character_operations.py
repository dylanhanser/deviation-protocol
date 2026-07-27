from __future__ import annotations

from collections.abc import Callable, Mapping
from enum import StrEnum
import hashlib
import json
from typing import Annotated, Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator

from deviation_protocol.domain.player_character import (
    ApplicableCharacterReference,
    canonical_player_declaration_bytes,
    CanonicalPlayerCharacter,
    canonical_character_operation_bytes,
    CharacterCore,
    ControllerBindingRef,
    NarrationPreferences,
    PlayerCharacterAuthorityClass,
    PlayerCharacterContractVersion,
    PlayerCharacterId,
    PlayerCharacterLifecycle,
    PlayerCharacterMutationKind,
    PlayerCharacterOperationId,
    PlayerCharacterRevision,
    MAX_CANONICAL_INTEGER,
    MIN_CANONICAL_INTEGER,
    revalidate_player_character_model,
    validate_canonical_player_character,
)
from deviation_protocol.domain.player_character_policies import (
    AuthorizedContinuityReturnPolicy,
    FinalDeathPlayerCharacterPolicy,
    PlayerConfirmation,
    PlayerCharacterPolicyDecision,
    ReactivatePlayerCharacterPolicy,
    RetirePlayerCharacterPolicy,
    TrustedFinalDeathEvidence,
)

CREATION_RESULT_SCHEMA_VERSION = "player-character.create-result/v1"
MUTATION_RESULT_SCHEMA_VERSION = "player-character.mutate-result/v1"
MAX_STORED_CHARACTER_RECEIPT_CANONICAL_BYTES = 65_536


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )


class CharacterOperationNamespace(StrEnum):
    CREATE_V1 = "player-character.create/v1"
    MUTATE_V1 = "player-character.mutate/v1"


class CharacterOperationFingerprint(_StrictFrozenModel):
    value: str = Field(strict=True, pattern=r"^[0-9a-f]{64}$")

    def __str__(self) -> str:
        return self.value


class CharacterCreationCommand(_StrictFrozenModel):
    contract_version: PlayerCharacterContractVersion
    character_core: CharacterCore
    narration_preferences: NarrationPreferences

    @model_validator(mode="after")
    def validate_declaration_envelope(self) -> CharacterCreationCommand:
        canonical_player_declaration_bytes(
            character_core=self.character_core,
            narration_preferences=self.narration_preferences,
        )
        return self


class CharacterMutationCommand(_StrictFrozenModel):
    contract_version: PlayerCharacterContractVersion
    command_kind: PlayerCharacterMutationKind
    target_player_character_id: PlayerCharacterId
    expected_revision: PlayerCharacterRevision
    applicable_reference: ApplicableCharacterReference
    confirmation: PlayerConfirmation | None = None
    final_death_evidence: TrustedFinalDeathEvidence | None = None

    @model_validator(mode="after")
    def validate_typed_body(self) -> CharacterMutationCommand:
        if self.command_kind in {
            PlayerCharacterMutationKind.RETIRE,
            PlayerCharacterMutationKind.REACTIVATE,
        }:
            if self.confirmation is None or self.final_death_evidence is not None:
                raise ValueError(
                    "retirement/reactivation requires only player confirmation"
                )
            if (
                self.confirmation.player_character_id
                != self.target_player_character_id
                or self.confirmation.expected_revision != self.expected_revision
                or self.confirmation.mutation_kind is not self.command_kind
            ):
                raise ValueError("player confirmation binding does not match command")
        elif self.command_kind is PlayerCharacterMutationKind.FINAL_DEATH:
            if self.final_death_evidence is None or self.confirmation is not None:
                raise ValueError("final death requires only trusted event evidence")
            if (
                self.final_death_evidence.player_character_id
                != self.target_player_character_id
                or self.final_death_evidence.expected_revision
                != self.expected_revision
            ):
                raise ValueError("final-death evidence binding does not match command")
        elif self.command_kind is PlayerCharacterMutationKind.AUTHORIZED_CONTINUITY_RETURN:
            if self.confirmation is not None or self.final_death_evidence is not None:
                raise ValueError(
                    "continuity return has no admitted first-slice evidence body"
                )
        else:
            raise ValueError("creation is not a mutation command")
        if self.applicable_reference is not None and (
            self.applicable_reference.player_character_id
            != self.target_player_character_id
            or self.applicable_reference.contract_version != self.contract_version
            or self.applicable_reference.record_revision != self.expected_revision
        ):
            raise ValueError("applicable reference binding does not match command")
        return self


def creation_fingerprint(
    command: CharacterCreationCommand,
) -> tuple[bytes, CharacterOperationFingerprint]:
    command = revalidate_player_character_model(
        command,
        CharacterCreationCommand,
    )
    return _creation_fingerprint_from_validated(command)


def _creation_fingerprint_from_validated(
    command: CharacterCreationCommand,
) -> tuple[bytes, CharacterOperationFingerprint]:
    payload = {
        "command_kind": PlayerCharacterMutationKind.CREATE,
        "contract_version": command.contract_version,
        "declarations": {
            "character_core": command.character_core,
            "narration_preferences": command.narration_preferences,
        },
        "operation_namespace": CharacterOperationNamespace.CREATE_V1,
    }
    return _fingerprint_payload(payload)


def mutation_fingerprint(
    command: CharacterMutationCommand,
    *,
    operation_id: PlayerCharacterOperationId,
) -> tuple[bytes, CharacterOperationFingerprint]:
    command = revalidate_player_character_model(
        command,
        CharacterMutationCommand,
    )
    operation_id = revalidate_player_character_model(
        operation_id,
        PlayerCharacterOperationId,
    )
    return _mutation_fingerprint_from_validated(
        command,
        operation_id=operation_id,
    )


def _mutation_fingerprint_from_validated(
    command: CharacterMutationCommand,
    *,
    operation_id: PlayerCharacterOperationId,
) -> tuple[bytes, CharacterOperationFingerprint]:
    if not command.expected_revision.has_successor:
        raise ValueError(
            "mutation command has no representable signed 64-bit successor"
        )
    confirmation = command.confirmation
    evidence = command.final_death_evidence
    if confirmation is not None and confirmation.operation_id != operation_id:
        raise ValueError("confirmation must bind the exact receipt operation ID")
    if evidence is not None and evidence.operation_id != operation_id:
        raise ValueError("trusted evidence must bind the exact receipt operation ID")
    if command.command_kind is PlayerCharacterMutationKind.AUTHORIZED_CONTINUITY_RETURN:
        body: dict[str, Any] = {"policy_state": "unavailable-in-phase-1"}
    elif confirmation is not None:
        body = {
            "confirmation": {
                "mutation_kind": confirmation.mutation_kind,
                "operation_id": confirmation.operation_id,
                "player_character_id": confirmation.player_character_id,
                "source_reference": confirmation.source_reference,
                "expected_revision": confirmation.expected_revision.value,
            }
        }
    else:
        assert evidence is not None
        body = {
            "trusted_final_death_evidence": {
                "operation_id": evidence.operation_id,
                "player_character_id": evidence.player_character_id,
                "source_reference": evidence.source_reference,
                "expected_revision": evidence.expected_revision.value,
            }
        }
    payload = {
        "applicable_reference": command.applicable_reference,
        "command_kind": command.command_kind,
        "contract_version": command.contract_version,
        "expected_revision": command.expected_revision.value,
        "mutation_body": body,
        "operation_namespace": CharacterOperationNamespace.MUTATE_V1,
        "target_player_character_id": command.target_player_character_id,
    }
    return _fingerprint_payload(payload)


def evaluate_mutation_policy(
    record: CanonicalPlayerCharacter,
    *,
    command: CharacterMutationCommand,
    operation_id: PlayerCharacterOperationId,
) -> PlayerCharacterPolicyDecision:
    """Dispatch one typed command without permitting reference substitution."""

    record = validate_canonical_player_character(record)
    command = revalidate_player_character_model(
        command,
        CharacterMutationCommand,
    )
    operation_id = revalidate_player_character_model(
        operation_id,
        PlayerCharacterOperationId,
    )
    common = {
        "target": command.target_player_character_id,
        "expected_revision": command.expected_revision,
        "applicable_reference": command.applicable_reference,
    }
    if command.command_kind is PlayerCharacterMutationKind.RETIRE:
        return RetirePlayerCharacterPolicy().evaluate(
            record, operation_id=operation_id, confirmation=command.confirmation, **common
        )
    if command.command_kind is PlayerCharacterMutationKind.REACTIVATE:
        return ReactivatePlayerCharacterPolicy().evaluate(
            record, operation_id=operation_id, confirmation=command.confirmation, **common
        )
    if command.command_kind is PlayerCharacterMutationKind.FINAL_DEATH:
        return FinalDeathPlayerCharacterPolicy().evaluate(
            record, operation_id=operation_id, evidence=command.final_death_evidence, **common
        )
    return AuthorizedContinuityReturnPolicy().evaluate(record, **common)


def _fingerprint_payload(
    payload: Mapping[str, Any],
) -> tuple[bytes, CharacterOperationFingerprint]:
    encoded = canonical_character_operation_bytes(payload)
    return (
        encoded,
        CharacterOperationFingerprint(value=hashlib.sha256(encoded).hexdigest()),
    )


class CreationReceiptKey(_StrictFrozenModel):
    controller_binding: ControllerBindingRef
    operation_namespace: Literal[CharacterOperationNamespace.CREATE_V1]
    operation_id: PlayerCharacterOperationId


class MutationReceiptKey(_StrictFrozenModel):
    player_character_id: PlayerCharacterId
    operation_namespace: Literal[CharacterOperationNamespace.MUTATE_V1]
    operation_id: PlayerCharacterOperationId


class CreationSuccessResult(_StrictFrozenModel):
    result_schema_version: Literal[CREATION_RESULT_SCHEMA_VERSION]
    player_character_id: PlayerCharacterId
    contract_version: PlayerCharacterContractVersion
    resulting_revision: PlayerCharacterRevision
    resulting_lifecycle: PlayerCharacterLifecycle

    @model_validator(mode="after")
    def validate_creation_result(self) -> CreationSuccessResult:
        if (
            self.resulting_revision.value != 1
            or self.resulting_lifecycle is not PlayerCharacterLifecycle.ACTIVE
        ):
            raise ValueError("creation success must describe the initial active revision")
        return self


class MutationCommandResult(StrEnum):
    RETIRED = "RETIRED"
    REACTIVATED = "REACTIVATED"
    DECEASED = "DECEASED"
    CONTINUITY_RETURNED = "CONTINUITY_RETURNED"


_SUCCESSFUL_MUTATION_SEMANTICS = {
    PlayerCharacterMutationKind.RETIRE: (
        MutationCommandResult.RETIRED,
        PlayerCharacterLifecycle.RETIRED,
        PlayerCharacterAuthorityClass.AUTHENTICATED_CONTROLLER,
    ),
    PlayerCharacterMutationKind.FINAL_DEATH: (
        MutationCommandResult.DECEASED,
        PlayerCharacterLifecycle.DECEASED,
        PlayerCharacterAuthorityClass.TRUSTED_SERVER_OUTCOME,
    ),
}


class MutationSuccessResult(_StrictFrozenModel):
    result_schema_version: Literal[MUTATION_RESULT_SCHEMA_VERSION]
    player_character_id: PlayerCharacterId
    contract_version: PlayerCharacterContractVersion
    command_kind: PlayerCharacterMutationKind
    command_result: MutationCommandResult
    resulting_revision: PlayerCharacterRevision
    resulting_lifecycle: PlayerCharacterLifecycle

    @model_validator(mode="after")
    def validate_mutation_result(self) -> MutationSuccessResult:
        expected = _SUCCESSFUL_MUTATION_SEMANTICS.get(self.command_kind)
        if expected is None:
            raise ValueError(
                "an unavailable Phase 1 mutation cannot have a success result"
            )
        if (
            self.command_result,
            self.resulting_lifecycle,
        ) != expected[:2]:
            raise ValueError("mutation result does not match its command")
        if self.resulting_revision.value < 2:
            raise ValueError("mutation success must advance beyond revision one")
        return self


class StoredCreationSuccessReceipt(_StrictFrozenModel):
    key: CreationReceiptKey
    fingerprint: CharacterOperationFingerprint
    command_kind: str = Field(strict=True, min_length=1, max_length=64)
    result_schema_version: str = Field(strict=True, min_length=1, max_length=64)
    result: CreationSuccessResult

    @model_validator(mode="after")
    def validate_internal_bindings(self) -> StoredCreationSuccessReceipt:
        if (
            self.command_kind != PlayerCharacterMutationKind.CREATE.value
            or self.result_schema_version != CREATION_RESULT_SCHEMA_VERSION
            or self.result.result_schema_version != self.result_schema_version
            or self.result.contract_version is not PlayerCharacterContractVersion.V1
        ):
            raise ValueError("stored creation receipt bindings are inconsistent")
        return self


class StoredMutationSuccessReceipt(_StrictFrozenModel):
    key: MutationReceiptKey
    fingerprint: CharacterOperationFingerprint
    command_kind: str = Field(strict=True, min_length=1, max_length=64)
    result_schema_version: str = Field(strict=True, min_length=1, max_length=64)
    result: MutationSuccessResult

    @model_validator(mode="after")
    def validate_internal_bindings(self) -> StoredMutationSuccessReceipt:
        if (
            self.key.player_character_id != self.result.player_character_id
            or self.command_kind != self.result.command_kind.value
            or self.result_schema_version != MUTATION_RESULT_SCHEMA_VERSION
            or self.result.result_schema_version != self.result_schema_version
            or self.result.contract_version is not PlayerCharacterContractVersion.V1
        ):
            raise ValueError("stored mutation receipt bindings are inconsistent")
        return self


def build_creation_success_receipt(
    *,
    key: CreationReceiptKey,
    fingerprint: CharacterOperationFingerprint,
    result: CreationSuccessResult,
) -> StoredCreationSuccessReceipt:
    key = revalidate_player_character_model(key, CreationReceiptKey)
    fingerprint = revalidate_player_character_model(
        fingerprint,
        CharacterOperationFingerprint,
    )
    result = revalidate_player_character_model(result, CreationSuccessResult)
    return StoredCreationSuccessReceipt(
        key=key,
        fingerprint=fingerprint,
        command_kind=PlayerCharacterMutationKind.CREATE.value,
        result_schema_version=CREATION_RESULT_SCHEMA_VERSION,
        result=result,
    )


def build_mutation_success_receipt(
    *,
    key: MutationReceiptKey,
    fingerprint: CharacterOperationFingerprint,
    result: MutationSuccessResult,
) -> StoredMutationSuccessReceipt:
    key = revalidate_player_character_model(key, MutationReceiptKey)
    fingerprint = revalidate_player_character_model(
        fingerprint,
        CharacterOperationFingerprint,
    )
    result = revalidate_player_character_model(result, MutationSuccessResult)
    return StoredMutationSuccessReceipt(
        key=key,
        fingerprint=fingerprint,
        command_kind=result.command_kind.value,
        result_schema_version=MUTATION_RESULT_SCHEMA_VERSION,
        result=result,
    )


class CharacterOperationProtocolCode(StrEnum):
    AUTHORIZATION_FAILED = "AUTHORIZATION_FAILED"
    READY_FOR_NEW_OPERATION = "READY_FOR_NEW_OPERATION"
    EXACT_REPLAY = "EXACT_REPLAY"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    STORED_RECEIPT_INTEGRITY_FAILURE = "STORED_RECEIPT_INTEGRITY_FAILURE"
    STALE_REVISION = "STALE_REVISION"
    REVISION_EXHAUSTED = "REVISION_EXHAUSTED"


SafeCharacterOperationResult: TypeAlias = (
    CreationSuccessResult | MutationSuccessResult
)


class CharacterOperationProtocolDecision(_StrictFrozenModel):
    operation_namespace: CharacterOperationNamespace
    code: CharacterOperationProtocolCode
    stored_success_result: SafeCharacterOperationResult | None = None

    @model_validator(mode="after")
    def validate_result_disclosure(self) -> CharacterOperationProtocolDecision:
        if self.code is CharacterOperationProtocolCode.EXACT_REPLAY:
            if self.stored_success_result is None:
                raise ValueError("exact replay requires the stored safe result")
            if (
                self.operation_namespace is CharacterOperationNamespace.CREATE_V1
                and not isinstance(
                    self.stored_success_result, CreationSuccessResult
                )
            ) or (
                self.operation_namespace is CharacterOperationNamespace.MUTATE_V1
                and not isinstance(
                    self.stored_success_result, MutationSuccessResult
                )
            ):
                raise ValueError(
                    "stored result must match the receipt namespace"
                )
        elif self.stored_success_result is not None:
            raise ValueError("only exact replay may disclose a stored result")
        return self

    @property
    def may_allocate_permanent_id(self) -> bool:
        return (
            self.operation_namespace is CharacterOperationNamespace.CREATE_V1
            and self.code is CharacterOperationProtocolCode.READY_FOR_NEW_OPERATION
        )

    @property
    def may_apply_mutation(self) -> bool:
        return (
            self.operation_namespace is CharacterOperationNamespace.MUTATE_V1
            and self.code is CharacterOperationProtocolCode.READY_FOR_NEW_OPERATION
        )

    @property
    def requires_atomic_success_receipt_on_commit(self) -> bool:
        return self.code is CharacterOperationProtocolCode.READY_FOR_NEW_OPERATION


CreationReceiptLookup: TypeAlias = Callable[
    [CreationReceiptKey], StoredCreationSuccessReceipt | Mapping[str, Any] | None
]
MutationReceiptLookup: TypeAlias = Callable[
    [MutationReceiptKey], StoredMutationSuccessReceipt | Mapping[str, Any] | None
]


def validate_stored_creation_success_receipt(
    value: StoredCreationSuccessReceipt | Mapping[str, Any] | str | bytes,
) -> StoredCreationSuccessReceipt:
    return StoredCreationSuccessReceipt.model_validate_json(
        _stored_receipt_json_bytes(
            value,
            opaque_reference_fields=(
                (("key", "controller_binding", "value"), ControllerBindingRef),
                (("key", "operation_id", "value"), PlayerCharacterOperationId),
                (("result", "player_character_id", "value"), PlayerCharacterId),
            ),
        )
    )


def validate_stored_mutation_success_receipt(
    value: StoredMutationSuccessReceipt | Mapping[str, Any] | str | bytes,
) -> StoredMutationSuccessReceipt:
    return StoredMutationSuccessReceipt.model_validate_json(
        _stored_receipt_json_bytes(
            value,
            opaque_reference_fields=(
                (("key", "player_character_id", "value"), PlayerCharacterId),
                (("key", "operation_id", "value"), PlayerCharacterOperationId),
                (("result", "player_character_id", "value"), PlayerCharacterId),
            ),
        )
    )


_OpaqueReceiptReferenceType: TypeAlias = type[
    ControllerBindingRef | PlayerCharacterId | PlayerCharacterOperationId
]
_OpaqueReceiptReferenceField: TypeAlias = tuple[
    tuple[str, ...],
    _OpaqueReceiptReferenceType,
]
_MISSING_RECEIPT_VALUE = object()


def _stored_receipt_json_bytes(
    value: BaseModel | Mapping[str, Any] | str | bytes,
    *,
    opaque_reference_fields: tuple[_OpaqueReceiptReferenceField, ...],
) -> bytes:
    if isinstance(value, BaseModel):
        _validate_original_receipt_opaque_references(
            value,
            opaque_reference_fields=opaque_reference_fields,
        )
        encoded = canonical_character_operation_bytes(value)
    elif isinstance(value, Mapping):
        snapshot = _snapshot_receipt_mapping(value)
        _validate_original_receipt_opaque_references(
            snapshot,
            opaque_reference_fields=opaque_reference_fields,
        )
        encoded = canonical_character_operation_bytes(snapshot)
    elif isinstance(value, (str, bytes)):
        try:
            decoded = json.loads(
                value,
                object_pairs_hook=_strict_json_object,
                parse_float=_reject_json_float,
                parse_constant=_reject_json_constant,
            )
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("stored receipt must be valid strict JSON") from None
        if not isinstance(decoded, Mapping):
            raise TypeError("stored receipt JSON must be an object")
        _validate_original_receipt_opaque_references(
            decoded,
            opaque_reference_fields=opaque_reference_fields,
        )
        encoded = canonical_character_operation_bytes(decoded)
    else:
        raise TypeError("stored receipt must be a strict JSON object or JSON bytes")
    if len(encoded) > MAX_STORED_CHARACTER_RECEIPT_CANONICAL_BYTES:
        raise ValueError("stored character receipt exceeds the Phase 1 byte bound")
    return encoded


def _snapshot_receipt_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    """Materialize untrusted mappings once before validation and canonicalization."""

    snapshot: dict[str, Any] = {}
    for key, nested in value.items():
        if key in snapshot:
            raise ValueError("stored receipt mapping contains a duplicate object key")
        snapshot[key] = _snapshot_receipt_value(nested)
    return snapshot


def _snapshot_receipt_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _snapshot_receipt_mapping(value)
    if isinstance(value, list):
        return [_snapshot_receipt_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_snapshot_receipt_value(item) for item in value)
    return value


def _validate_original_receipt_opaque_references(
    value: BaseModel | Mapping[str, Any],
    *,
    opaque_reference_fields: tuple[_OpaqueReceiptReferenceField, ...],
) -> None:
    for path, reference_type in opaque_reference_fields:
        current: Any = value
        for field_name in path:
            if isinstance(current, BaseModel):
                current = current.__dict__.get(
                    field_name,
                    _MISSING_RECEIPT_VALUE,
                )
            elif isinstance(current, Mapping):
                current = current.get(field_name, _MISSING_RECEIPT_VALUE)
            else:
                current = _MISSING_RECEIPT_VALUE
            if current is _MISSING_RECEIPT_VALUE:
                break
        if current is not _MISSING_RECEIPT_VALUE:
            reference_type(value=current)


def _strict_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("stored receipt JSON contains a duplicate object key")
        result[key] = value
    return result


def _reject_json_float(value: str) -> Any:
    raise ValueError(f"stored receipt JSON contains unsupported float {value}")


def _reject_json_constant(value: str) -> Any:
    raise ValueError(f"stored receipt JSON contains unsupported constant {value}")


def evaluate_creation_receipt_protocol(
    *,
    authentication_succeeded: bool,
    trusted_controller_binding: ControllerBindingRef | None,
    operation_id: PlayerCharacterOperationId,
    command: CharacterCreationCommand,
    lookup_receipt: CreationReceiptLookup,
) -> CharacterOperationProtocolDecision:
    """Authorize before lookup; a failed authorization invokes no lookup."""

    if not authentication_succeeded or trusted_controller_binding is None:
        return CharacterOperationProtocolDecision(
            operation_namespace=CharacterOperationNamespace.CREATE_V1,
            code=CharacterOperationProtocolCode.AUTHORIZATION_FAILED
        )
    try:
        trusted_controller_binding = revalidate_player_character_model(
            trusted_controller_binding,
            ControllerBindingRef,
        )
        operation_id = revalidate_player_character_model(
            operation_id,
            PlayerCharacterOperationId,
        )
        command = revalidate_player_character_model(
            command,
            CharacterCreationCommand,
        )
    except (AttributeError, TypeError, ValueError):
        return CharacterOperationProtocolDecision(
            operation_namespace=CharacterOperationNamespace.CREATE_V1,
            code=CharacterOperationProtocolCode.AUTHORIZATION_FAILED,
        )
    key = CreationReceiptKey(
        controller_binding=trusted_controller_binding,
        operation_namespace=CharacterOperationNamespace.CREATE_V1,
        operation_id=operation_id,
    )
    _, fingerprint = _creation_fingerprint_from_validated(command)
    stored = lookup_receipt(key)
    if stored is None:
        return CharacterOperationProtocolDecision(
            operation_namespace=CharacterOperationNamespace.CREATE_V1,
            code=CharacterOperationProtocolCode.READY_FOR_NEW_OPERATION
        )
    return _evaluate_creation_reuse(
        stored=stored,
        key=key,
        fingerprint=fingerprint,
    )


def recover_creation_unique_race_winner(
    *,
    losing_transaction_rolled_back: bool,
    authentication_succeeded: bool,
    trusted_controller_binding: ControllerBindingRef | None,
    operation_id: PlayerCharacterOperationId,
    command: CharacterCreationCommand,
    reread_receipt_in_fresh_transaction: CreationReceiptLookup,
) -> CharacterOperationProtocolDecision:
    """A uniqueness loser may only reread; it can never allocate again."""

    if not losing_transaction_rolled_back:
        raise RuntimeError("creation uniqueness loser must roll back before reread")
    decision = evaluate_creation_receipt_protocol(
        authentication_succeeded=authentication_succeeded,
        trusted_controller_binding=trusted_controller_binding,
        operation_id=operation_id,
        command=command,
        lookup_receipt=reread_receipt_in_fresh_transaction,
    )
    if decision.code is CharacterOperationProtocolCode.READY_FOR_NEW_OPERATION:
        return CharacterOperationProtocolDecision(
            operation_namespace=CharacterOperationNamespace.CREATE_V1,
            code=CharacterOperationProtocolCode.STORED_RECEIPT_INTEGRITY_FAILURE
        )
    return decision


def _evaluate_creation_reuse(
    *,
    stored: StoredCreationSuccessReceipt | Mapping[str, Any],
    key: CreationReceiptKey,
    fingerprint: CharacterOperationFingerprint,
) -> CharacterOperationProtocolDecision:
    try:
        validated = validate_stored_creation_success_receipt(stored)
    except (AttributeError, TypeError, ValueError):
        return CharacterOperationProtocolDecision(
            operation_namespace=CharacterOperationNamespace.CREATE_V1,
            code=CharacterOperationProtocolCode.STORED_RECEIPT_INTEGRITY_FAILURE
        )
    if (
        validated.key != key
        or validated.fingerprint != fingerprint
        or validated.command_kind != PlayerCharacterMutationKind.CREATE.value
        or validated.result_schema_version != CREATION_RESULT_SCHEMA_VERSION
    ):
        return CharacterOperationProtocolDecision(
            operation_namespace=CharacterOperationNamespace.CREATE_V1,
            code=CharacterOperationProtocolCode.IDEMPOTENCY_CONFLICT
        )
    if (
        validated.result.result_schema_version
        != validated.result_schema_version
        or validated.result.contract_version
        is not PlayerCharacterContractVersion.V1
    ):
        return CharacterOperationProtocolDecision(
            operation_namespace=CharacterOperationNamespace.CREATE_V1,
            code=CharacterOperationProtocolCode.IDEMPOTENCY_CONFLICT
        )
    return CharacterOperationProtocolDecision(
        operation_namespace=CharacterOperationNamespace.CREATE_V1,
        code=CharacterOperationProtocolCode.EXACT_REPLAY,
        stored_success_result=validated.result,
    )


def evaluate_mutation_receipt_protocol(
    *,
    authentication_succeeded: bool,
    trusted_controller_binding: ControllerBindingRef | None,
    current_record: CanonicalPlayerCharacter | None,
    operation_id: PlayerCharacterOperationId,
    command: CharacterMutationCommand,
    lookup_receipt: MutationReceiptLookup,
) -> CharacterOperationProtocolDecision:
    """Authorize the current owner before receipt/character/result disclosure.

    Exact replay is evaluated before expected revision so a committed result
    remains replayable after later canonical revisions.
    """

    if (
        not authentication_succeeded
        or trusted_controller_binding is None
        or current_record is None
    ):
        return CharacterOperationProtocolDecision(
            operation_namespace=CharacterOperationNamespace.MUTATE_V1,
            code=CharacterOperationProtocolCode.AUTHORIZATION_FAILED
        )
    try:
        current_record = validate_canonical_player_character(current_record)
        trusted_controller_binding = revalidate_player_character_model(
            trusted_controller_binding,
            ControllerBindingRef,
        )
        operation_id = revalidate_player_character_model(
            operation_id,
            PlayerCharacterOperationId,
        )
        command = revalidate_player_character_model(
            command,
            CharacterMutationCommand,
        )
    except (AttributeError, TypeError, ValueError):
        return CharacterOperationProtocolDecision(
            operation_namespace=CharacterOperationNamespace.MUTATE_V1,
            code=CharacterOperationProtocolCode.AUTHORIZATION_FAILED
        )
    if (
        current_record.controller_binding != trusted_controller_binding
        or current_record.player_character_id
        != command.target_player_character_id
    ):
        return CharacterOperationProtocolDecision(
            operation_namespace=CharacterOperationNamespace.MUTATE_V1,
            code=CharacterOperationProtocolCode.AUTHORIZATION_FAILED
        )
    if not command.expected_revision.has_successor:
        return CharacterOperationProtocolDecision(
            operation_namespace=CharacterOperationNamespace.MUTATE_V1,
            code=CharacterOperationProtocolCode.REVISION_EXHAUSTED,
        )
    key = MutationReceiptKey(
        player_character_id=current_record.player_character_id,
        operation_namespace=CharacterOperationNamespace.MUTATE_V1,
        operation_id=operation_id,
    )
    _, fingerprint = _mutation_fingerprint_from_validated(
        command,
        operation_id=operation_id,
    )
    stored = lookup_receipt(key)
    if stored is not None:
        return _evaluate_mutation_reuse(
            stored=stored,
            key=key,
            fingerprint=fingerprint,
            command=command,
            current_record=current_record,
        )
    if command.expected_revision != current_record.record_revision:
        return CharacterOperationProtocolDecision(
            operation_namespace=CharacterOperationNamespace.MUTATE_V1,
            code=CharacterOperationProtocolCode.STALE_REVISION
        )
    return CharacterOperationProtocolDecision(
        operation_namespace=CharacterOperationNamespace.MUTATE_V1,
        code=CharacterOperationProtocolCode.READY_FOR_NEW_OPERATION
    )


def recover_mutation_unique_race_winner(
    *,
    losing_transaction_rolled_back: bool,
    authentication_succeeded: bool,
    trusted_controller_binding: ControllerBindingRef | None,
    current_record: CanonicalPlayerCharacter | None,
    operation_id: PlayerCharacterOperationId,
    command: CharacterMutationCommand,
    reread_receipt_in_fresh_transaction: MutationReceiptLookup,
) -> CharacterOperationProtocolDecision:
    """A mutation uniqueness loser may return only a durable replay/conflict."""

    if not losing_transaction_rolled_back:
        raise RuntimeError("mutation uniqueness loser must roll back before reread")
    decision = evaluate_mutation_receipt_protocol(
        authentication_succeeded=authentication_succeeded,
        trusted_controller_binding=trusted_controller_binding,
        current_record=current_record,
        operation_id=operation_id,
        command=command,
        lookup_receipt=reread_receipt_in_fresh_transaction,
    )
    if decision.code in {
        CharacterOperationProtocolCode.READY_FOR_NEW_OPERATION,
        CharacterOperationProtocolCode.STALE_REVISION,
    }:
        return CharacterOperationProtocolDecision(
            operation_namespace=CharacterOperationNamespace.MUTATE_V1,
            code=CharacterOperationProtocolCode.STORED_RECEIPT_INTEGRITY_FAILURE
        )
    return decision


def _evaluate_mutation_reuse(
    *,
    stored: StoredMutationSuccessReceipt | Mapping[str, Any],
    key: MutationReceiptKey,
    fingerprint: CharacterOperationFingerprint,
    command: CharacterMutationCommand,
    current_record: CanonicalPlayerCharacter,
) -> CharacterOperationProtocolDecision:
    try:
        validated = validate_stored_mutation_success_receipt(stored)
    except (AttributeError, TypeError, ValueError):
        return CharacterOperationProtocolDecision(
            operation_namespace=CharacterOperationNamespace.MUTATE_V1,
            code=CharacterOperationProtocolCode.STORED_RECEIPT_INTEGRITY_FAILURE
        )
    if (
        validated.key != key
        or validated.fingerprint != fingerprint
        or validated.command_kind != command.command_kind.value
        or validated.result_schema_version != MUTATION_RESULT_SCHEMA_VERSION
        or validated.result.result_schema_version
        != validated.result_schema_version
        or validated.result.player_character_id
        != command.target_player_character_id
        or validated.result.contract_version != command.contract_version
        or validated.result.command_kind is not command.command_kind
        or validated.result.resulting_revision.value
        != command.expected_revision.value + 1
        or validated.result.player_character_id
        != command.applicable_reference.player_character_id
        or validated.result.contract_version
        != command.applicable_reference.contract_version
        or command.expected_revision
        != command.applicable_reference.record_revision
    ):
        return CharacterOperationProtocolDecision(
            operation_namespace=CharacterOperationNamespace.MUTATE_V1,
            code=CharacterOperationProtocolCode.IDEMPOTENCY_CONFLICT
        )
    expected_semantics = _SUCCESSFUL_MUTATION_SEMANTICS.get(command.command_kind)
    if expected_semantics is None or (
        validated.result.command_result,
        validated.result.resulting_lifecycle,
    ) != expected_semantics[:2]:
        return CharacterOperationProtocolDecision(
            operation_namespace=CharacterOperationNamespace.MUTATE_V1,
            code=CharacterOperationProtocolCode.STORED_RECEIPT_INTEGRITY_FAILURE,
        )
    if (
        current_record.record_revision.value
        < validated.result.resulting_revision.value
    ):
        return CharacterOperationProtocolDecision(
            operation_namespace=CharacterOperationNamespace.MUTATE_V1,
            code=CharacterOperationProtocolCode.STORED_RECEIPT_INTEGRITY_FAILURE,
        )
    if current_record.record_revision == validated.result.resulting_revision:
        provenance = current_record.authority_provenance
        if (
            current_record.player_character_id
            != validated.result.player_character_id
            or current_record.contract_version
            != validated.result.contract_version
            or current_record.lifecycle
            is not validated.result.resulting_lifecycle
            or provenance.target_player_character_id
            != validated.result.player_character_id
            or provenance.prior_revision != command.expected_revision
            or provenance.resulting_revision
            != validated.result.resulting_revision
            or provenance.mutation_kind is not command.command_kind
            or provenance.authority_class is not expected_semantics[2]
        ):
            return CharacterOperationProtocolDecision(
                operation_namespace=CharacterOperationNamespace.MUTATE_V1,
                code=(
                    CharacterOperationProtocolCode.STORED_RECEIPT_INTEGRITY_FAILURE
                ),
            )
    return CharacterOperationProtocolDecision(
        operation_namespace=CharacterOperationNamespace.MUTATE_V1,
        code=CharacterOperationProtocolCode.EXACT_REPLAY,
        stored_success_result=validated.result,
    )


class CreationProtocolStep(StrEnum):
    AUTHENTICATE = "authenticate"
    RESOLVE_TRUSTED_CONTROLLER_BINDING = "resolve-trusted-controller-binding"
    LOCK_BINDING_OWNER = "lock-binding-owner"
    VALIDATE_TYPED_OPERATION = "validate-typed-operation"
    LOOK_UP_CREATION_RECEIPT = "look-up-creation-receipt"
    RESOLVE_REPLAY_OR_CONFLICT = "resolve-replay-or-conflict"
    ALLOCATE_PERMANENT_ID = "allocate-permanent-id"
    INSERT_ALLOCATION_RECORD_HISTORY_AND_SUCCESS_RECEIPT = (
        "insert-allocation-record-history-and-success-receipt"
    )
    COMMIT_ONCE = "commit-once"


class MutationProtocolStep(StrEnum):
    AUTHENTICATE = "authenticate"
    LOCK_CURRENT_CHARACTER = "lock-current-character"
    AUTHORIZE_STORED_CONTROLLER_BINDING = "authorize-stored-controller-binding"
    VALIDATE_TYPED_OPERATION_AND_REVISION_DOMAIN = (
        "validate-typed-operation-and-revision-domain"
    )
    LOOK_UP_MUTATION_RECEIPT = "look-up-mutation-receipt"
    RESOLVE_REPLAY_OR_CONFLICT = "resolve-replay-or-conflict"
    VALIDATE_CONTEXT_REFERENCE_AND_EXPECTED_REVISION = (
        "validate-context-reference-and-expected-revision"
    )
    APPLY_POLICY_AND_VALIDATE_COMPLETE_CANDIDATE = (
        "apply-policy-and-validate-complete-candidate"
    )
    CAS_RECORD_AND_INSERT_HISTORY_EFFECT_AND_SUCCESS_RECEIPT = (
        "cas-record-and-insert-history-effect-and-success-receipt"
    )
    COMMIT_ONCE = "commit-once"


CREATION_TRANSACTION_ORDER = (
    CreationProtocolStep.AUTHENTICATE,
    CreationProtocolStep.RESOLVE_TRUSTED_CONTROLLER_BINDING,
    CreationProtocolStep.LOCK_BINDING_OWNER,
    CreationProtocolStep.VALIDATE_TYPED_OPERATION,
    CreationProtocolStep.LOOK_UP_CREATION_RECEIPT,
    CreationProtocolStep.RESOLVE_REPLAY_OR_CONFLICT,
    CreationProtocolStep.ALLOCATE_PERMANENT_ID,
    CreationProtocolStep.INSERT_ALLOCATION_RECORD_HISTORY_AND_SUCCESS_RECEIPT,
    CreationProtocolStep.COMMIT_ONCE,
)

MUTATION_TRANSACTION_ORDER = (
    MutationProtocolStep.AUTHENTICATE,
    MutationProtocolStep.LOCK_CURRENT_CHARACTER,
    MutationProtocolStep.AUTHORIZE_STORED_CONTROLLER_BINDING,
    MutationProtocolStep.VALIDATE_TYPED_OPERATION_AND_REVISION_DOMAIN,
    MutationProtocolStep.LOOK_UP_MUTATION_RECEIPT,
    MutationProtocolStep.RESOLVE_REPLAY_OR_CONFLICT,
    MutationProtocolStep.VALIDATE_CONTEXT_REFERENCE_AND_EXPECTED_REVISION,
    MutationProtocolStep.APPLY_POLICY_AND_VALIDATE_COMPLETE_CANDIDATE,
    MutationProtocolStep.CAS_RECORD_AND_INSERT_HISTORY_EFFECT_AND_SUCCESS_RECEIPT,
    MutationProtocolStep.COMMIT_ONCE,
)


class UniqueRaceRecoveryStep(StrEnum):
    ROLL_BACK_LOSING_TRANSACTION = "roll-back-losing-transaction"
    OPEN_FRESH_TRANSACTION = "open-fresh-transaction"
    REAUTHORIZE_OWNER = "reauthorize-owner"
    REREAD_DURABLE_WINNER_RECEIPT = "reread-durable-winner-receipt"
    VALIDATE_EXACT_REPLAY = "validate-exact-replay"
    RETURN_STORED_SAFE_RESULT = "return-stored-safe-result"


UNIQUE_RACE_RECOVERY_ORDER = (
    UniqueRaceRecoveryStep.ROLL_BACK_LOSING_TRANSACTION,
    UniqueRaceRecoveryStep.OPEN_FRESH_TRANSACTION,
    UniqueRaceRecoveryStep.REAUTHORIZE_OWNER,
    UniqueRaceRecoveryStep.REREAD_DURABLE_WINNER_RECEIPT,
    UniqueRaceRecoveryStep.VALIDATE_EXACT_REPLAY,
    UniqueRaceRecoveryStep.RETURN_STORED_SAFE_RESULT,
)


class FirstSliceRetentionBoundary(_StrictFrozenModel):
    successful_receipts_only: Literal[True] = True
    pending_state_supported: Literal[False] = False
    rejected_receipts_supported: Literal[False] = False
    cleanup_supported: Literal[False] = False
    deletion_supported: Literal[False] = False
    archival_supported: Literal[False] = False
    permanent_retention_policy_selected: Literal[False] = False
    production_rollout_supported: Literal[False] = False


FIRST_SLICE_RETENTION_BOUNDARY = FirstSliceRetentionBoundary()


class LaterPersistenceAtomicityRequirements(_StrictFrozenModel):
    binding_owner_locked_before_creation_receipt_lookup: Literal[True] = True
    permanent_id_allocated_only_after_authorization_and_validation: Literal[
        True
    ] = True
    allocation_ledger_is_append_only: Literal[True] = True
    issued_ids_are_never_reusable: Literal[True] = True
    allocation_record_initial_revision_and_success_receipt_commit_together: Literal[
        True
    ] = True
    rejected_operations_create_no_success_receipt: Literal[True] = True
    uniqueness_is_a_database_backstop: Literal[True] = True
    uniqueness_loser_rolls_back_before_fresh_reread: Literal[True] = True
    losing_attempt_leaves_no_reusable_orphan_id: Literal[True] = True
    equivalent_concurrent_creation_has_at_most_one_committed_winner: Literal[
        True
    ] = True
    mutation_cas_history_effect_and_success_receipt_commit_together: Literal[
        True
    ] = True
    repository_methods_commit_independently: Literal[False] = False
    response_may_report_success_before_commit: Literal[False] = False


LATER_PERSISTENCE_ATOMICITY_REQUIREMENTS = LaterPersistenceAtomicityRequirements()
