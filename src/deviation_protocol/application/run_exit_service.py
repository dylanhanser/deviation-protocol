"""Owned, post-ending native Run termination over the pinned native UoW."""
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from pydantic import BaseModel, ConfigDict, Field

from deviation_protocol.application.errors import SessionNotFoundError, SnapshotInvalidError, SnapshotNotFoundError
from deviation_protocol.application.narrative_outcome_policy import state_fingerprint
from deviation_protocol.application.ports import NativeRunAdmissionUnitOfWorkFactory, ControllerBindingResolver
from deviation_protocol.application.session_service import SessionService
from deviation_protocol.application.run_operations import (
    RunEntryPublicOperationKey, RunOperationFingerprint, RunOperationNamespace,
    RunReceiptKey, RunSafeResult, StoredRunSuccessReceipt,
    TERMINATE_NATIVE_RUN_RESULT_SCHEMA_VERSION,
)
from deviation_protocol.domain.player_character import ControllerBindingRef, PlayerCharacterLifecycle, validate_canonical_player_character
from deviation_protocol.domain.run import RunAuthoritySourceRef, RunMutationKind, revalidate_run_model
from deviation_protocol.domain.run_protocol_binding import (
    NativeRunAdmissionV1, NativeRunTerminatedV1, NativeRunExitRequestV1,
    NativeRunExitEvidenceV1, LegacyRunCompatibilityV1, terminate_native_run,
)


class RunExitError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class RunExitCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, revalidate_instances="always")
    public_operation_key: RunEntryPublicOperationKey
    expected_run_state_version: int = Field(ge=1, le=2**63 - 1)
    expected_session_state_version: int = Field(ge=0, le=2**63 - 1)


@dataclass(frozen=True)
class RunExitService:
    uow_factory: NativeRunAdmissionUnitOfWorkFactory
    session_service: SessionService
    controller_binding_resolver: ControllerBindingResolver
    source_reference: RunAuthoritySourceRef
    clock: Callable[[], datetime]

    async def _target(self, uow, principal, session_id):
        owned = await uow.sessions.get_owned(session_id, principal.player_id)
        if owned is None:
            raise SessionNotFoundError(session_id)
        participation = await uow.run_participations.get(session_id)
        reverse = await uow.run_participations.find_attachment_run_ids(session_id)
        if participation is None:
            if reverse:
                raise SnapshotInvalidError(session_id)
            raise RunExitError("NATIVE_RUN_REQUIRED")
        if reverse != (participation.run_id,):
            raise SnapshotInvalidError(session_id)
        return participation

    async def _owned_family(self, uow, principal, session_id, controller, participation, *, locking):
        get = uow.run_protocol_bindings.get_classified_for_update if locking else uow.run_protocol_bindings.get_classified
        family = await get(run_id=participation.run_id)
        if type(family) is LegacyRunCompatibilityV1:
            raise RunExitError("NATIVE_RUN_REQUIRED")
        if type(family) not in (NativeRunAdmissionV1, NativeRunTerminatedV1):
            raise SnapshotInvalidError(session_id)
        revalidate_run_model(family, type(family))
        if family.canonical_run.trusted_participation_references != (participation,):
            raise SnapshotInvalidError(session_id)
        reference = family.canonical_run.player_character_binding.applicable_character_reference
        character = await uow.player_characters.get(reference.player_character_id)
        if character is None or character.controller_binding != controller:
            raise SessionNotFoundError(session_id)
        validate_canonical_player_character(character)
        registered = await uow.controller_bindings.get(controller)
        if registered != controller:
            raise SessionNotFoundError(session_id)
        owned_get = uow.sessions.get_owned_for_update if locking else uow.sessions.get_owned
        persisted = await owned_get(session_id, principal.player_id)
        if persisted is None:
            raise SessionNotFoundError(session_id)
        snapshot_get = uow.sessions.get_latest_snapshot_for_update if locking else uow.sessions.get_latest_snapshot
        snapshot = await snapshot_get(session_id)
        if snapshot is None:
            raise SnapshotNotFoundError(session_id)
        state = self.session_service._load_state(persisted, snapshot.state_version, snapshot.state)
        runtime = state.scenario_runtime
        if runtime is not None and runtime.ending_status.value in ("RESOLVED", "FAILED"):
            records = tuple(record for record in state.player_memory.scenario_records if record.scenario_id == runtime.scenario_id)
            if (len(records) != 1 or records[0].status.value != "COMPLETED"
                    or records[0].ending_id != runtime.ending_id
                    or records[0].scenario_content_version != runtime.scenario_content_version):
                raise SnapshotInvalidError(session_id)
        if type(family) is NativeRunTerminatedV1 and state_fingerprint(state) != family.exit_evidence.snapshot_sha256:
            raise SnapshotInvalidError(session_id)
        return family, character, persisted, state

    async def _controller(self, principal, session_id):
        controller = await self.controller_binding_resolver.resolve(principal)
        if controller is None:
            raise SessionNotFoundError(session_id)
        revalidate_run_model(controller, ControllerBindingRef)
        return controller

    @staticmethod
    def _status(family, character, persisted, state):
        run = family.canonical_run
        ended = state.scenario_runtime is not None and state.scenario_runtime.ending_status.value in ("RESOLVED", "FAILED")
        return dict(schema_version="native-run-status/v1", session_id=persisted.session.session_id,
            run_id=run.run_id.value, run_state_version=run.state_version.value,
            session_state_version=persisted.session.state_version, lifecycle_status=run.lifecycle_status.value,
            can_exit=type(family) is NativeRunAdmissionV1 and character.lifecycle is PlayerCharacterLifecycle.ACTIVE and ended)

    async def status(self, principal, *, session_id):
        controller = await self._controller(principal, session_id)
        async with self.session_service.uow_factory() as uow:
            participation = await self._target(uow, principal, session_id)
            values = await self._owned_family(uow, principal, session_id, controller, participation, locking=False)
            return self._status(*values)

    async def exit(self, principal, *, session_id, command):
        revalidate_run_model(command, RunExitCommand)
        controller = await self._controller(principal, session_id)
        # Resolve only a lock target in a separate read transaction. No authority
        # from that transaction survives the character-first locked revalidation.
        async with self.session_service.uow_factory() as reader:
            participation = await self._target(reader, principal, session_id)
            family, _, _, _ = await self._owned_family(reader, principal, session_id, controller, participation, locking=False)
            target = family.canonical_run.player_character_binding.applicable_character_reference.player_character_id
        commit_issued = False
        try:
            async with self.uow_factory() as uow:
                character = await uow.player_characters.get_for_update(target)
                if character is None or character.controller_binding != controller:
                    raise SessionNotFoundError(session_id)
                family, character, persisted, state = await self._owned_family(
                    uow, principal, session_id, controller, participation, locking=True)
                if (await self._target(uow, principal, session_id) != participation
                        or family.canonical_run.player_character_binding.applicable_character_reference.player_character_id != target):
                    raise SnapshotInvalidError(session_id)
                run = family.canonical_run
                request = NativeRunExitRequestV1(schema="run.terminate-native-request/v1",
                    controller_binding=controller.value, player_id=principal.player_id,
                    public_operation_key=command.public_operation_key.value, run_id=run.run_id.value,
                    continuous_story_line_id=run.continuous_story_line_id.value, session_id=session_id,
                    expected_run_state_version=command.expected_run_state_version,
                    expected_session_state_version=command.expected_session_state_version,
                    source_reference=self.source_reference.value)
                key = RunReceiptKey(run_id=run.run_id, operation_namespace=RunOperationNamespace.TERMINATE_NATIVE_V1,
                                    operation_id=request.operation_id())
                receipt = await uow.run_mutation_receipts.get(key)
                if receipt is not None:
                    if receipt.fingerprint.value != request.fingerprint():
                        raise RunExitError("IDEMPOTENCY_CONFLICT")
                    if type(family) is not NativeRunTerminatedV1 or family.exit_evidence.request != request:
                        raise SnapshotInvalidError(session_id)
                    return self._status(family, character, persisted, state)
                if type(family) is NativeRunTerminatedV1 or character.lifecycle is not PlayerCharacterLifecycle.ACTIVE:
                    raise RunExitError("RUN_EXIT_NOT_AVAILABLE")
                if (command.expected_run_state_version != 3
                        or command.expected_session_state_version != persisted.session.state_version):
                    raise RunExitError("RUN_EXIT_STALE")
                if not self._status(family, character, persisted, state)["can_exit"]:
                    raise RunExitError("RUN_EXIT_NOT_AVAILABLE")
                runtime = state.scenario_runtime
                evidence = NativeRunExitEvidenceV1(schema="run.terminate-native-evidence/v1", request=request,
                    scenario_id=persisted.session.scenario_id, scenario_content_version=state.content_version,
                    ending_id=runtime.ending_id, ending_status=runtime.ending_status.value,
                    session_state_version=persisted.session.state_version, snapshot_sha256=state_fingerprint(state))
                time = self.clock()
                terminal = terminate_native_run(family, request, occurred_at=time)
                receipt = StoredRunSuccessReceipt(key=key, fingerprint=RunOperationFingerprint(value=request.fingerprint()),
                    command_kind=RunMutationKind.TERMINATE_NATIVE_RUN,
                    result=RunSafeResult(result_schema_version=TERMINATE_NATIVE_RUN_RESULT_SCHEMA_VERSION,
                        run_id=run.run_id, continuous_story_line_id=run.continuous_story_line_id,
                        lifecycle_status=terminal.lifecycle_status, resulting_state_version=terminal.state_version))
                await uow.runs.append_revision(terminal, created_at=time)
                if not await uow.runs.compare_and_swap_current(terminal, expected_state_version=3, updated_at=time):
                    raise RunExitError("RUN_EXIT_CONFLICT")
                await uow.run_mutation_receipts.add(receipt, created_at=time, exit_evidence=evidence)
                classified = await uow.run_protocol_bindings.get_classified_for_update(run_id=run.run_id)
                if classified != NativeRunTerminatedV1(admission=family, canonical_run=terminal, exit_evidence=evidence):
                    raise SnapshotInvalidError(session_id)
                result = self._status(classified, character, persisted, state)
                commit_issued = True
                await uow.commit()
                return result
        except BaseException as error:
            if commit_issued:
                if not isinstance(error, Exception):
                    error.commit_outcome_unknown = True
                    raise
                from deviation_protocol.application.ports import NativeRunAdmissionOutcomeUnknownError
                if isinstance(error, NativeRunAdmissionOutcomeUnknownError):
                    raise
                raise NativeRunAdmissionOutcomeUnknownError("Run exit commit or cleanup outcome unknown") from error
            raise
