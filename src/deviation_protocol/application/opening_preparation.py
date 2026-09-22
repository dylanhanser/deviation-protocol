"""Persisted preparation and admission coordinated under the owned character lock."""
from __future__ import annotations

from dataclasses import dataclass, replace
import secrets
import json
import re
from uuid import uuid4

from deviation_protocol.application.native_run_admission import (
    NativeRunAdmissionCommand, NativeRunAdmissionResult, NativeRunAdmissionIntegrityError,
)
from deviation_protocol.application.run_operations import RunEntryPublicOperationKey
from deviation_protocol.domain.opening_talents import CATALOG_VERSION, load_catalog, roll_candidates, validate_selection
from deviation_protocol.domain.player_character import PlayerCharacterLifecycle
from deviation_protocol.domain.run import RunId


def encode_command(command):
    from deviation_protocol.domain import run_protocol_resolution as s2
    resolved = s2.resolve_run_protocol_objectives(command.protocol, command.overrides,
        expected_epoch=s2.RUN_PROTOCOL_RESOLUTION_EPOCH, expected_version=1)
    return json.dumps({"key": command.public_operation_key.value,
        "character_id": command.player_character_id.value, "revision": command.expected_record_revision.value,
        "world": command.entry_world.model_dump(mode="json"),
        "resolution_input_hex": s2.encode_run_protocol_resolution_input_v1(resolved.resolution_input).hex()},
        sort_keys=True, separators=(",", ":"))


def decode_command(raw):
    from deviation_protocol.application.native_run_admission import decode_native_resolution_input
    from deviation_protocol.domain import run_protocol_resolution as s2
    from deviation_protocol.domain.player_character import PlayerCharacterId, PlayerCharacterRevision
    from deviation_protocol.domain.entry_world import EntryWorldRefV1
    data = json.loads(raw)
    resolution = decode_native_resolution_input(data["resolution_input_hex"])
    command = NativeRunAdmissionCommand(public_operation_key=RunEntryPublicOperationKey(value=data["key"]),
        player_character_id=PlayerCharacterId(value=data["character_id"]),
        expected_record_revision=PlayerCharacterRevision(value=data["revision"]),
        protocol=resolution.envelope, overrides=s2.RunProtocolOverrideProposalV1(
            profile_ref=resolution.envelope.profile_ref, entries=resolution.authorized_overrides.entries),
        entry_world=EntryWorldRefV1.model_validate_json(json.dumps(data["world"])))
    if encode_command(command) != raw:
        raise NativeRunAdmissionIntegrityError("invalid frozen opening intent")
    return command


def decode_result(raw, command):
    from deviation_protocol.domain import run_protocol_resolution as s2
    data = json.loads(raw)
    resolved = s2.resolve_run_protocol_objectives(command.protocol, command.overrides,
        expected_epoch=s2.RUN_PROTOCOL_RESOLUTION_EPOCH, expected_version=1)
    if data["resolved_protocol"] != resolved.model_dump(mode="json"):
        raise NativeRunAdmissionIntegrityError("invalid opening result protocol")
    data["resolved_protocol"] = resolved
    from deviation_protocol.domain.player_character import ApplicableCharacterReference
    data["applicable_character_reference"] = ApplicableCharacterReference.model_validate_json(
        json.dumps(data["applicable_character_reference"]))
    return NativeRunAdmissionResult.model_validate(data)


class PreparationRejected(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


async def load_run_talents(uow, family, player_id):
    if family is None:
        return None
    run = family.canonical_run
    repository = getattr(uow, "opening_preparations", None)
    record = await repository.by_run(run.run_id.value) if repository is not None else None
    if record is None:
        if run.run_id.value.startswith("opening."):
            raise NativeRunAdmissionIntegrityError("missing confirmed opening talents")
        return None
    record.validate()
    if (record.state != "CONFIRMED" or record.player_id != player_id
            or record.character_id != run.player_character_binding.applicable_character_reference.player_character_id.value):
        raise NativeRunAdmissionIntegrityError("opening Run association")
    return record


@dataclass(frozen=True, slots=True)
class OpeningPreparation:
    preparation_id: str
    owner: str
    player_id: str
    character_id: str
    ordinal: int
    request_key: str
    command_json: str
    catalog_version: str
    seed: str
    candidates: tuple[str, ...]
    state: str = "PENDING"
    selections: tuple[str, ...] = ()
    run_id: str | None = None
    result_json: str | None = None

    def validate(self):
        if (type(self.preparation_id) is not str or re.fullmatch(r"[0-9a-f]{32}", self.preparation_id) is None
                or any(type(value) is not str or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", value) is None
                    for value in (self.owner, self.player_id, self.character_id, self.request_key))
                or type(self.candidates) is not tuple or type(self.selections) is not tuple):
            raise NativeRunAdmissionIntegrityError("invalid opening identity")
        command = decode_command(self.command_json)
        if (command.player_character_id.value != self.character_id
                or command.public_operation_key.value != "opening." + self.preparation_id
                or self.candidates != roll_candidates(self.seed, self.catalog_version)
                or type(self.ordinal) is not int or self.ordinal < 1):
            raise NativeRunAdmissionIntegrityError("invalid opening preparation")
        if self.state == "PENDING":
            if self.selections or self.run_id is not None or self.result_json is not None:
                raise NativeRunAdmissionIntegrityError("invalid pending preparation")
        elif self.state == "CONFIRMED":
            validate_selection(self.candidates, self.selections, self.catalog_version)
            result = decode_result(self.result_json, command)
            if (result.run_id.value != self.run_id or not self.run_id.startswith("opening.")
                    or result.applicable_character_reference.player_character_id.value != self.character_id):
                raise NativeRunAdmissionIntegrityError("invalid confirmed preparation")
        else:
            raise NativeRunAdmissionIntegrityError("invalid preparation lifecycle")
        return self


class OpeningPreparationService:
    def __init__(self, admission):
        self.admission = admission
        load_catalog()  # Pin and validate authored content before acquiring locks.

    async def _owner(self, principal):
        principal = self.admission._principal(principal)
        owner = await self.admission.controller_binding_resolver.resolve(principal)
        if owner is None:
            raise PreparationRejected("PLAYER_CHARACTER_NOT_FOUND")
        from deviation_protocol.domain.player_character import ControllerBindingRef
        from deviation_protocol.domain.run import revalidate_run_model
        revalidate_run_model(owner, ControllerBindingRef)
        return owner

    async def prepare(self, principal, command):
        from deviation_protocol.domain.run import revalidate_run_model
        revalidate_run_model(command, NativeRunAdmissionCommand)
        owner = await self._owner(principal)
        async with self.admission.uow_factory() as uow:
            character = await self.admission._owned_character(uow, owner, command)
            if character is None:
                raise PreparationRejected("PLAYER_CHARACTER_NOT_FOUND")
            repository = uow.opening_preparations
            prior = await repository.by_request(owner.value, command.public_operation_key.value)
            if prior is not None:
                if prior.character_id != command.player_character_id.value:
                    raise PreparationRejected("IDEMPOTENCY_CONFLICT")
                return prior.validate()
            latest = await repository.latest(command.player_character_id.value)
            if latest is not None:
                latest.validate()
                if latest.owner != owner.value or latest.player_id != principal.player_id:
                    raise PreparationRejected("PLAYER_CHARACTER_NOT_FOUND")
                if latest.state == "PENDING":
                    return latest
            active = await uow.runs.get_active_for_player_character_for_update(command.player_character_id)
            if active is not None:
                if latest is not None and latest.run_id == active.run_id.value:
                    return latest
                raise PreparationRejected("PLAYER_CHARACTER_NOT_ELIGIBLE")
            reference = character.applicable_character_reference
            if character.lifecycle is not PlayerCharacterLifecycle.ACTIVE or not reference.record_revision.has_successor:
                raise PreparationRejected("PLAYER_CHARACTER_NOT_ELIGIBLE")
            if reference.record_revision != command.expected_record_revision:
                raise PreparationRejected("PLAYER_CHARACTER_STALE")
            from deviation_protocol.domain import run_protocol_resolution as resolution
            from deviation_protocol.domain.entry_world import lookup_entry_world, EntryWorldLookupError
            from deviation_protocol.application.errors import InvalidScenarioDefinitionError
            try:
                resolution.resolve_run_protocol_objectives(command.protocol, command.overrides,
                    expected_epoch=resolution.RUN_PROTOCOL_RESOLUTION_EPOCH, expected_version=1)
            except (resolution.RunProtocolProfileLookupError, resolution.RunProtocolOverrideValidationError):
                raise PreparationRejected("INVALID_RUN_PROTOCOL") from None
            try:
                self.admission._definition(lookup_entry_world(command.entry_world))
            except EntryWorldLookupError:
                raise PreparationRejected("INVALID_ENTRY_WORLD") from None
            except InvalidScenarioDefinitionError:
                raise PreparationRejected("INVALID_SCENARIO_DEFINITION") from None
            identity, seed = uuid4().hex, secrets.token_hex(32)
            frozen = NativeRunAdmissionCommand.model_validate({**{name: getattr(command, name) for name in type(command).model_fields},
                "public_operation_key": RunEntryPublicOperationKey(value="opening." + identity)})
            record = OpeningPreparation(identity, owner.value, principal.player_id,
                command.player_character_id.value, 1 if latest is None else latest.ordinal + 1,
                command.public_operation_key.value, encode_command(frozen), CATALOG_VERSION,
                seed, roll_candidates(seed)).validate()
            await repository.save(record)
            await uow.commit()
            return record

    async def get(self, principal, character_id):
        owner = await self._owner(principal)
        async with self.admission.uow_factory() as uow:
            from types import SimpleNamespace
            from deviation_protocol.domain.player_character import PlayerCharacterId
            target = SimpleNamespace(player_character_id=PlayerCharacterId(value=character_id))
            if await self.admission._owned_character(uow, owner, target) is None:
                raise PreparationRejected("PLAYER_CHARACTER_NOT_FOUND")
            record = await uow.opening_preparations.latest(character_id)
            if record is None:
                return None
            if record.owner != owner.value or record.player_id != principal.player_id:
                raise PreparationRejected("PLAYER_CHARACTER_NOT_FOUND")
            return record.validate()

    async def confirm(self, principal, preparation_id, character_id, catalog_version, selections):
        owner = await self._owner(principal)
        async with self.admission.uow_factory() as uow:
            record = await uow.opening_preparations.get(preparation_id)
            if record is None or (record.owner, record.player_id, record.character_id) != (owner.value, principal.player_id, character_id):
                raise PreparationRejected("PLAYER_CHARACTER_NOT_FOUND")
            record.validate()
            command = decode_command(record.command_json)
            character = await self.admission._owned_character(uow, owner, command)
            if character is None:
                raise PreparationRejected("PLAYER_CHARACTER_NOT_FOUND")
            # Re-read after the character lock: a concurrent confirmation may have committed.
            record = (await uow.opening_preparations.get(preparation_id, locked=True)).validate()
            if catalog_version != record.catalog_version:
                raise PreparationRejected("OPENING_PREPARATION_STALE")
            try:
                chosen = validate_selection(record.candidates, selections, catalog_version)
            except ValueError:
                raise PreparationRejected("INVALID_TALENT_SELECTION") from None
            if record.state == "CONFIRMED":
                if chosen != record.selections:
                    raise PreparationRejected("IDEMPOTENCY_CONFLICT")
                # Revalidate the original exact admission receipt without staging again.
                from deviation_protocol.application.run_operations import RunReceiptKey, RunOperationNamespace
                ids = self.admission._derive_ids(owner, command.public_operation_key)
                stored = await uow.run_creation_receipts.get_with_evidence(RunReceiptKey(
                    operation_namespace=RunOperationNamespace.CREATE_V1, operation_id=ids.creation))
                replay = await self.admission._native_replay(uow, principal, command, owner, stored)
                if replay != decode_result(record.result_json, command):
                    raise NativeRunAdmissionIntegrityError("opening replay mismatch")
                return record
            latest = await uow.opening_preparations.latest(character_id)
            if latest.preparation_id != preparation_id:
                raise PreparationRejected("OPENING_PREPARATION_STALE")
            result = await self.admission.stage_entry(uow, principal, command, owner, character,
                run_id=RunId(value="opening." + uuid4().hex))
            if type(result) is not NativeRunAdmissionResult:
                raise PreparationRejected(result.code.value)
            confirmed = replace(record, state="CONFIRMED", selections=chosen,
                run_id=result.run_id.value, result_json=result.model_dump_json()).validate()
            await uow.opening_preparations.save(confirmed)
            await uow.commit()
            return confirmed
