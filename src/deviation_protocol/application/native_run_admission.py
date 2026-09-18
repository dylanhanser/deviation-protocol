"""Internal native admission: caller intent, durable evidence and one transaction."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
import struct
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator, model_serializer

from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.run_operations import (
    RunEntryPublicOperationKey, RunOperationFingerprint, RunOperationNamespace,
    RunReceiptKey, StoredRunSuccessReceipt, CreateRunCommand,
    RunEntryCreationEvidence, _RunEntryControllerOperation, _RunEntryPlayerCharacter,
    _RunEntryScenario, _RunEntrySource, construct_created_run, creation_result,
)
from deviation_protocol.domain.run import (
    RunId, ContinuousStoryLineId, RunStateVersion, RunOperationId, RunMutationKind,
    canonical_run_operation_bytes, revalidate_run_model, _validate_actual_pydantic_state,
)
from deviation_protocol.domain.player_character import (
    ApplicableCharacterReference, ControllerBindingRef, PlayerCharacterId,
    PlayerCharacterRevision, PlayerCharacterLifecycle, validate_applicable_character_reference,
)
from deviation_protocol.domain import run_protocol as s1, run_protocol_resolution as s2
from deviation_protocol.domain.entry_world import EntryWorldRefV1, lookup_entry_world, EntryWorldLookupError
from deviation_protocol.domain.run_protocol_binding import (
    NativeRunProtocolBindingV1, RunEntryWorldBindingV1, NativeRunAdmissionV1,
)


class _StrictNative(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, revalidate_instances="always")

    @model_serializer(mode="wrap")
    def _serialize_original(self, handler):
        revalidate_run_model(self, type(self))
        return handler(self)

    @model_validator(mode="before")
    @classmethod
    def _original(cls, value):
        if isinstance(value, BaseModel):
            if type(value) is not cls:
                raise TypeError("unexpected native carrier")
            _validate_actual_pydantic_state(value, path=cls.__name__, visited=set())
        elif type(value) is dict:
            for nested in value.values():
                if isinstance(nested, BaseModel):
                    _validate_actual_pydantic_state(nested, path=cls.__name__, visited=set())
        return value


class NativeRunAdmissionCommand(_StrictNative):
    public_operation_key: RunEntryPublicOperationKey
    player_character_id: PlayerCharacterId
    expected_record_revision: PlayerCharacterRevision
    protocol: s1.RunProtocolEnvelopeV1
    overrides: s2.RunProtocolOverrideProposalV1
    entry_world: EntryWorldRefV1


class NativeRunAdmissionResult(_StrictNative):
    result_schema: Literal["run-entry.native-result/v1"] = "run-entry.native-result/v1"
    run_id: RunId
    continuous_story_line_id: ContinuousStoryLineId
    session_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    scenario_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    scenario_content_version: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    applicable_character_reference: ApplicableCharacterReference
    resolved_protocol: s2.ResolvedRunProtocolObjectivesV1
    entry_world: EntryWorldRefV1
    admitted_run_revision: RunStateVersion

    @model_validator(mode="after")
    def _revision(self):
        if self.admitted_run_revision.value != 3:
            raise ValueError("admitted revision must be three")
        return self


class NativeRunAdmissionDecisionCode(StrEnum):
    AUTHORIZATION_FAILED = "AUTHORIZATION_FAILED"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    PLAYER_CHARACTER_STALE = "PLAYER_CHARACTER_STALE"
    PLAYER_CHARACTER_NOT_ELIGIBLE = "PLAYER_CHARACTER_NOT_ELIGIBLE"
    INVALID_PROTOCOL = "INVALID_PROTOCOL"
    INVALID_ENTRY_WORLD = "INVALID_ENTRY_WORLD"
    INVALID_SCENARIO_DEFINITION = "INVALID_SCENARIO_DEFINITION"
    RUN_ENTRY_CONFLICT = "RUN_ENTRY_CONFLICT"


class NativeRunAdmissionDecision(_StrictNative):
    code: NativeRunAdmissionDecisionCode


class NativeRunAdmissionIntegrityError(RuntimeError):
    """Impossible trusted application association."""


class NativeRunEntryCreationEvidenceV1(_StrictNative):
    evidence_schema: Literal["run-entry.native-creation-evidence/v1"] = "run-entry.native-creation-evidence/v1"
    controller_operation: _RunEntryControllerOperation
    player_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    player_character: _RunEntryPlayerCharacter
    scenario: _RunEntryScenario
    trusted_run_source: _RunEntrySource
    entry_world: EntryWorldRefV1
    resolution_input_hex: str = Field(min_length=2, max_length=2048, pattern=r"^(?:[0-9a-f]{2})+$")
    resolution_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _canonical_resolution_intent(self):
        decode_native_resolution_input(self.resolution_input_hex)
        return self


def decode_native_resolution_input(value: str):
    """Validate retained versioned intent without applying current defaults."""
    raw = bytes.fromhex(value)
    payload = json.loads(raw.decode("utf-8"))
    expected = {"authorized_overrides", "authorized_profile_id", "authorized_profile_version",
                "canonical_envelope_hex", "resolver_version", "schema"}
    if (type(payload) is not dict or set(payload) != expected
            or canonical_run_operation_bytes(payload) != raw
            or type(payload["resolver_version"]) is not int or payload["resolver_version"] != 1
            or payload["schema"] != "run-protocol-resolution/v1"):
        raise ValueError("noncanonical native resolution input")
    encoded = payload["canonical_envelope_hex"]
    if type(encoded) is not str or bytes.fromhex(encoded).hex() != encoded:
        raise ValueError("noncanonical native envelope hex")
    envelope = s1.decode_run_protocol_envelope(bytes.fromhex(encoded), expected_epoch="run-protocol-envelope", expected_version=1)
    profile = s2.lookup_run_protocol_profile(envelope.profile_ref)
    if (type(payload["authorized_profile_version"]) is not int
            or payload["authorized_profile_version"] != envelope.profile_ref.profile_version.value
            or payload["authorized_profile_id"] != envelope.profile_ref.profile_id.value
            or type(payload["authorized_overrides"]) is not list):
        raise ValueError("native resolution profile association")
    entries = []
    for entry in payload["authorized_overrides"]:
        if type(entry) is not dict or set(entry) != {"parameter", "value"}:
            raise ValueError("native override members")
        entries.append(s2.RunProtocolObjectiveOverrideV1(parameter=s2.ObjectiveParameterName(entry["parameter"]),
                                                        value=s2.ObjectiveParameterValue(value=entry["value"])))
    proposal = s2.RunProtocolOverrideProposalV1(profile_ref=envelope.profile_ref, entries=tuple(entries))
    authorized = s2.validate_run_protocol_overrides(profile, proposal)
    result = s2.construct_run_protocol_resolution_input_v1(envelope, authorized_profile=profile, authorized_overrides=authorized)
    if s2.encode_run_protocol_resolution_input_v1(result) != raw:
        raise ValueError("native resolution input is not canonical")
    return result


NATIVE_EVIDENCE_MAGIC = b"\x8aDP33S4E\r\n\x1a\n"


def native_run_entry_evidence_bytes(evidence: NativeRunEntryCreationEvidenceV1) -> bytes:
    revalidate_run_model(evidence, NativeRunEntryCreationEvidenceV1)
    encoded = NATIVE_EVIDENCE_MAGIC + b"\x01" + canonical_run_operation_bytes(evidence)
    if not 14 <= len(encoded) <= 4096:
        raise ValueError("native creation evidence byte bounds")
    return encoded


def native_run_entry_creation_fingerprint(evidence):
    encoded = native_run_entry_evidence_bytes(evidence)
    return encoded, RunOperationFingerprint(value=hashlib.sha256(encoded).hexdigest())


def derive_native_run_entry_internal_id(*, purpose, controller_binding, public_operation_key):
    if type(purpose) is not str or purpose not in (
        "run.create/v1", "run.bind-player-character/v1", "run.attach-session/v1", "session.create/v1",
    ):
        raise ValueError("native internal-id purpose")
    revalidate_run_model(controller_binding, ControllerBindingRef)
    revalidate_run_model(public_operation_key, RunEntryPublicOperationKey)
    parts = (purpose, controller_binding.value, public_operation_key.value)
    encoded = b"deviation-protocol:p33-s4:internal-id:v1\0"
    for part in parts:
        value = part.encode("ascii")
        encoded += struct.pack(">H", len(value)) + value
    return hashlib.sha256(encoded).hexdigest()


def _decision(code):
    return NativeRunAdmissionDecision(code=NativeRunAdmissionDecisionCode(code))


def _result(admission):
    revalidate_run_model(admission, NativeRunAdmissionV1)
    run = admission.canonical_run
    world = admission.world_binding.entry_world
    return NativeRunAdmissionResult(
        run_id=run.run_id, continuous_story_line_id=run.continuous_story_line_id,
        session_id=run.trusted_participation_references[0].session_id,
        scenario_id=world.scenario_id, scenario_content_version=world.scenario_content_version,
        applicable_character_reference=run.player_character_binding.applicable_character_reference,
        resolved_protocol=admission.protocol_binding.resolved_protocol,
        entry_world=EntryWorldRefV1(entry_world_id=world.entry_world_id, entry_world_version=world.entry_world_version),
        admitted_run_revision=run.state_version,
    )


from deviation_protocol.application.run_entry_service import RunEntryService, _RunEntryInternalIds
from deviation_protocol.application.run_service import stage_run_entry_binding, stage_run_entry_activation
from deviation_protocol.application.ports import (
    NativeRunAdmissionWriteConflictError, RunReceiptUniquenessConflictError,
    RunPlayerCharacterBindingUniquenessConflictError, RunSessionParticipationUniquenessConflictError,
    RunWriteConflictError, StoredRunCreationEvidence,
)
from deviation_protocol.application.errors import (
    ConcurrentSessionCreateError, InvalidScenarioDefinitionError,
    SnapshotInvalidError, SnapshotNotFoundError, SnapshotSchemaVersionMismatchError,
    SnapshotStateVersionMismatchError, SnapshotSessionMismatchError, SnapshotContentVersionMismatchError,
)


class _AdmissionCollision(Exception):
    pass


_WRITE_CONFLICTS = (
    _AdmissionCollision, NativeRunAdmissionWriteConflictError, RunReceiptUniquenessConflictError,
    RunPlayerCharacterBindingUniquenessConflictError, RunSessionParticipationUniquenessConflictError,
    RunWriteConflictError, ConcurrentSessionCreateError,
)


@dataclass(slots=True)
class NativeRunAdmissionService(RunEntryService):
    """Uses the existing pure revision constructors, never the legacy coordinator."""

    def __post_init__(self):
        RunEntryService.__post_init__(self)
        # This lookup is file-backed only at composition, before any database lock.
        from deviation_protocol.domain.entry_world import AUTHORED_ENTRY_WORLDS_V1
        for entry in AUTHORED_ENTRY_WORLDS_V1:
            world = lookup_entry_world(EntryWorldRefV1(entry_world_id=entry.entry_world_id,
                                                       entry_world_version=entry.entry_world_version))
            self._definition(world)

    def _definition(self, world):
        definition = self.session_service.resolve_run_entry_definition(world.scenario_id)
        if (definition.scenario_id != world.scenario_id
                or definition.content_version != world.scenario_content_version
                or definition.public_client is None
                or definition.public_client.default_character_definition_id != world.default_character_definition_id):
            raise InvalidScenarioDefinitionError(world.scenario_id)
        return definition

    def _occurred_at(self):
        # Existing Session/event DATETIME columns have second precision. Choose
        # one representable transaction time before constructing any evidence.
        return RunEntryService._occurred_at(self).replace(microsecond=0)

    @staticmethod
    def _derive_ids(controller, public_operation_key):
        ids = [derive_native_run_entry_internal_id(purpose=p, controller_binding=controller,
                                                   public_operation_key=public_operation_key)
               for p in ("run.create/v1", "run.bind-player-character/v1", "run.attach-session/v1", "session.create/v1")]
        return _RunEntryInternalIds(RunOperationId(value=ids[0]), RunOperationId(value=ids[1]),
                                    RunOperationId(value=ids[2]), ids[3])

    async def enter(self, principal: RequestPrincipal, *, command: NativeRunAdmissionCommand) -> NativeRunAdmissionResult | NativeRunAdmissionDecision:
        principal = self._principal(principal)
        revalidate_run_model(command, NativeRunAdmissionCommand)
        controller = await self.controller_binding_resolver.resolve(principal)
        if controller is None:
            return _decision("AUTHORIZATION_FAILED")
        try:
            revalidate_run_model(controller, ControllerBindingRef)
        except (TypeError, ValueError, AttributeError):
            return _decision("AUTHORIZATION_FAILED")
        ids = self._derive_ids(controller, command.public_operation_key)
        key = RunReceiptKey(operation_namespace=RunOperationNamespace.CREATE_V1, operation_id=ids.creation)
        try:
            async with self.uow_factory() as uow:
                character = await self._owned_character(uow, controller, command)
                if character is None:
                    return _decision("AUTHORIZATION_FAILED")
                stored = await uow.run_creation_receipts.get_with_evidence(key)
                if stored is not None:
                    return await self._native_replay(uow, principal, command, controller, stored)
                reference = character.applicable_character_reference
                if reference.record_revision != command.expected_record_revision:
                    return _decision("PLAYER_CHARACTER_STALE")
                if character.lifecycle is not PlayerCharacterLifecycle.ACTIVE or not reference.record_revision.has_successor:
                    return _decision("PLAYER_CHARACTER_NOT_ELIGIBLE")
                if await uow.runs.get_active_for_player_character_for_update(command.player_character_id) is not None:
                    return _decision("PLAYER_CHARACTER_NOT_ELIGIBLE")
                s1.validate_run_protocol_envelope_v1(command.protocol)
                try:
                    resolved = s2.resolve_run_protocol_objectives(command.protocol, command.overrides,
                                expected_epoch=s2.RUN_PROTOCOL_RESOLUTION_EPOCH, expected_version=1)
                except (s2.RunProtocolProfileLookupError, s2.RunProtocolOverrideValidationError):
                    return _decision("INVALID_PROTOCOL")
                try:
                    world = lookup_entry_world(command.entry_world)
                except EntryWorldLookupError:
                    return _decision("INVALID_ENTRY_WORLD")
                try:
                    definition = self._definition(world)
                except InvalidScenarioDefinitionError:
                    return _decision("INVALID_SCENARIO_DEFINITION")
                if await uow.sessions.get_by_creation_request(principal.player_id, ids.session_creation_request_id) is not None:
                    return _decision("RUN_ENTRY_CONFLICT")
                time = self._occurred_at()
                run_id = revalidate_run_model(self.run_id_issuer.issue(), RunId)
                line_id = revalidate_run_model(self.continuous_story_line_id_issuer.issue(), ContinuousStoryLineId)
                prepared = self.session_service.prepare_run_entry_initialization(principal,
                            creation_request_id=ids.session_creation_request_id, definition=definition,
                            character_definition_id=world.default_character_definition_id, created_at=time)
                evidence = NativeRunEntryCreationEvidenceV1(
                    controller_operation=_RunEntryControllerOperation(controller_binding=controller, public_operation_key=command.public_operation_key.value),
                    player_id=principal.player_id,
                    player_character=_RunEntryPlayerCharacter(player_character_id=command.player_character_id, pre_entry_record_revision=command.expected_record_revision),
                    scenario=_RunEntryScenario(scenario_id=world.scenario_id, content_version=world.scenario_content_version, default_character_definition_id=world.default_character_definition_id),
                    trusted_run_source=_RunEntrySource(source_reference=self.source_reference), entry_world=command.entry_world,
                    resolution_input_hex=s2.encode_run_protocol_resolution_input_v1(resolved.resolution_input).hex(),
                    resolution_fingerprint=resolved.fingerprint.value,
                )
                initial = construct_created_run(CreateRunCommand(source_reference=self.source_reference), run_id=run_id,
                          continuous_story_line_id=line_id, operation_id=ids.creation, occurred_at=time)
                _, fingerprint = native_run_entry_creation_fingerprint(evidence)
                receipt = StoredRunSuccessReceipt(key=key, fingerprint=fingerprint, command_kind=RunMutationKind.CREATE, result=creation_result(initial))
                bound, bind_receipt = self._build_binding(initial, reference=reference, ids=ids, occurred_at=time)
                active, attach_receipt = self._build_activation(bound, session_id=prepared.session.session_id, ids=ids, occurred_at=time)
                protocol_binding = NativeRunProtocolBindingV1(run_id=run_id, continuous_story_line_id=line_id,
                                   bound_state_version=RunStateVersion(value=3), resolved_protocol=resolved)
                world_binding = RunEntryWorldBindingV1(run_id=run_id, continuous_story_line_id=line_id,
                                bound_state_version=RunStateVersion(value=3), entry_world=world)
                intended = _result(NativeRunAdmissionV1(canonical_run=active, protocol_binding=protocol_binding, world_binding=world_binding))
                await uow.runs.add_initial(initial, created_at=time)
                await uow.run_creation_receipts.add_native_with_evidence(receipt, evidence, created_at=time)
                if not await stage_run_entry_binding(uow, bound, bind_receipt, created_at=time):
                    raise _AdmissionCollision()
                await self.session_service.stage_run_entry_initialization(uow, prepared)
                if not await stage_run_entry_activation(uow, active, attach_receipt, created_at=time):
                    raise _AdmissionCollision()
                await uow.run_protocol_bindings.add_native(protocol_binding, created_at=time)
                await uow.run_entry_world_bindings.add_native(world_binding, created_at=time)
                reconstructed = await uow.run_protocol_bindings.get_classified_for_update(run_id=run_id)
                if type(reconstructed) is not NativeRunAdmissionV1 or _result(reconstructed) != intended:
                    raise NativeRunAdmissionIntegrityError("staged admission differs from intended result") from None
                await uow.commit()
                return intended
        except _WRITE_CONFLICTS:
            # The failed transaction has exited and cleaned up before this one read-only attempt.
            async with self.uow_factory() as uow:
                if await self._owned_character(uow, controller, command) is None:
                    return _decision("AUTHORIZATION_FAILED")
                stored = await uow.run_creation_receipts.get_with_evidence(key)
                if stored is None:
                    return _decision("RUN_ENTRY_CONFLICT")
                return await self._native_replay(uow, principal, command, controller, stored)

    async def _owned_character(self, uow, controller, command):
        character = await self.player_character_binding_evidence.lock_owned_for_binding(uow,
                    trusted_controller_binding=controller, target_player_character_id=command.player_character_id)
        if character is None:
            return None
        try:
            reference = validate_applicable_character_reference(character.applicable_character_reference)
            if reference.player_character_id != command.player_character_id or type(character.lifecycle) is not PlayerCharacterLifecycle:
                raise ValueError("character evidence association")
        except (TypeError, ValueError, AttributeError):
            raise NativeRunAdmissionIntegrityError("impossible owned character evidence") from None
        return character

    async def _native_replay(self, uow, principal, command, controller, stored):
        if type(stored) is not StoredRunCreationEvidence:
            raise NativeRunAdmissionIntegrityError("invalid stored evidence carrier") from None
        receipt = revalidate_run_model(stored.receipt, StoredRunSuccessReceipt)
        evidence = stored.evidence
        if type(evidence) in (CreateRunCommand, RunEntryCreationEvidence):
            revalidate_run_model(evidence, type(evidence))
            return _decision("IDEMPOTENCY_CONFLICT")
        revalidate_run_model(evidence, NativeRunEntryCreationEvidenceV1)
        if (evidence.player_id != principal.player_id or evidence.controller_operation.controller_binding != controller
                or evidence.trusted_run_source.source_reference != self.source_reference):
            return _decision("AUTHORIZATION_FAILED")
        ids = self._derive_ids(controller, RunEntryPublicOperationKey(value=evidence.controller_operation.public_operation_key))
        if (stored.evidence_canonical != native_run_entry_evidence_bytes(evidence)
                or receipt.key.operation_id != ids.creation
                or receipt.fingerprint != native_run_entry_creation_fingerprint(evidence)[1]):
            raise NativeRunAdmissionIntegrityError("native receipt association") from None
        # Stored S2 input is validated by the complete classifier below; no current defaults are resolved here.
        try:
            intent = json.loads(bytes.fromhex(evidence.resolution_input_hex))
            proposed = [{"parameter": e.parameter.value, "value": e.value.value} for e in command.overrides.entries]
            proposed.sort(key=lambda e: tuple(p.value for p in s2.RUN_PROTOCOL_OBJECTIVE_PARAMETER_ORDER).index(e["parameter"]))
            differs = (intent["canonical_envelope_hex"] != s1.encode_run_protocol_envelope_v1(command.protocol).hex()
                       or intent["authorized_overrides"] != proposed
                       or command.overrides.profile_ref != command.protocol.profile_ref)
        except (ValueError, TypeError, KeyError):
            raise NativeRunAdmissionIntegrityError("invalid stored native intent") from None
        if (differs or evidence.controller_operation.public_operation_key != command.public_operation_key.value
                or evidence.player_character.player_character_id != command.player_character_id
                or evidence.player_character.pre_entry_record_revision != command.expected_record_revision
                or evidence.entry_world != command.entry_world):
            return _decision("IDEMPOTENCY_CONFLICT")
        admission = await uow.run_protocol_bindings.get_classified_for_update(run_id=receipt.result.run_id)
        from deviation_protocol.domain.run_protocol_binding import NativeRunTerminatedV1,NativeRunContinuedV1,NativeRunContinuedTerminatedV1
        if type(admission) in (NativeRunTerminatedV1,NativeRunContinuedV1,NativeRunContinuedTerminatedV1):
            revalidate_run_model(admission, type(admission))
            admission = admission.admission
        if type(admission) is not NativeRunAdmissionV1:
            raise NativeRunAdmissionIntegrityError("missing admitted family") from None
        result = _result(admission)
        persisted = await uow.sessions.get_owned_for_update(result.session_id, principal.player_id)
        event = await uow.sessions.get_initialization_event(result.session_id)
        snapshot = await uow.sessions.get_latest_snapshot_for_update(result.session_id)
        if persisted is None or event is None or snapshot is None:
            raise NativeRunAdmissionIntegrityError("missing owned native Session family") from None
        try:
            self.session_service.validate_native_run_entry_replay_initialization(persisted, snapshot, event, evidence,
                ids.session_creation_request_id, participation=admission.canonical_run.trusted_participation_references[0],
                applicable_character_reference=result.applicable_character_reference,
                transaction_time=admission.canonical_run.creation_provenance.occurred_at)
        except (TypeError, ValueError, SnapshotInvalidError, SnapshotNotFoundError, SnapshotSchemaVersionMismatchError,
                SnapshotStateVersionMismatchError, SnapshotSessionMismatchError, SnapshotContentVersionMismatchError) as error:
            raise NativeRunAdmissionIntegrityError("native Session replay validation") from error
        return result
