"""The sole atomic owner of the approved first-to-second world handoff."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone

from deviation_protocol.application.errors import SessionNotFoundError, SnapshotInvalidError
from deviation_protocol.application.run_exit_service import RunExitCommand, RunExitService, RunExitError
from deviation_protocol.application.run_operations import (
    RunOperationNamespace, RunReceiptKey, StoredRunSuccessReceipt, RunSafeResult,
    RunOperationFingerprint, CONTINUE_NATIVE_RUN_RESULT_SCHEMA_VERSION,
)
from deviation_protocol.application.narrative_outcome_policy import state_fingerprint
from deviation_protocol.application.session_content_registry import SessionContentRegistry
from deviation_protocol.domain.player_character import PlayerCharacterLifecycle
from deviation_protocol.domain.run import RunMutationKind, revalidate_run_model
from deviation_protocol.domain.run_protocol_binding import (
    NativeRunAdmissionV1, NativeRunTerminatedV1, NativeRunContinuedV1,
    NativeRunContinuedTerminatedV1, continue_native_run,
    NativeRunRegionalRevisitV1, NativeRunRegionalRevisitTerminatedV1,
)
from deviation_protocol.domain.world_continuation import (
    NativeRunContinuationRequestV1, NativeRunContinuationEvidenceV1,
    ContinuationSelectionInputsV1, ContinuationSourceEndingV1,
    WorldStateRootV1, WorldVisitV1, WorldPositionV1, derive_world_visit_id,
    SOURCE_WORLD, SOURCE_REGION, DESTINATION_WORLD, DESTINATION_REGION, SOURCE_ENDINGS,
)


class RunContinuationError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class RunContinuationCommand(RunExitCommand):
    pass


def original_admission(family):
    if type(family) is NativeRunAdmissionV1:
        return family
    if type(family) in (NativeRunTerminatedV1,NativeRunContinuedV1,NativeRunContinuedTerminatedV1,NativeRunRegionalRevisitV1,NativeRunRegionalRevisitTerminatedV1):
        return family.admission
    raise ValueError("complete native family required")


def _continued(family):
    if type(family) is NativeRunRegionalRevisitTerminatedV1:
        return family.revisited.continued
    if type(family) is NativeRunRegionalRevisitV1:
        return family.continued
    return family.continued if type(family) is NativeRunContinuedTerminatedV1 else family


def _visit(family, ordinal):
    run = family.canonical_run
    participation = run.trusted_participation_references[ordinal-1]
    world, region = (SOURCE_WORLD,SOURCE_REGION) if ordinal == 1 else (DESTINATION_WORLD,DESTINATION_REGION)
    return dict(visit_id=derive_world_visit_id(run_id=run.run_id.value,
        continuous_story_line_id=run.continuous_story_line_id.value,
        session_id=participation.session_id,joined_state_version=participation.joined_state_version.value).value,
        visit_ordinal=ordinal,world_id=world.world_id,world_version=world.world_version,
        region_id=region.region_id,region_version=region.region_version)


def continuation_result(family):
    from deviation_protocol.application.native_run_admission import _result
    from deviation_protocol.application.public_run_protocol import project_native_context
    family = _continued(family)
    revalidate_run_model(family,NativeRunContinuedV1)
    e = family.continuation_evidence
    return dict(schema_version="native-run-continuation-result/v1",
        source_session_id=e.request.source_session_id,
        source_session_state_version=e.source_ending.session_state_version,
        run_id=family.canonical_run.run_id.value,resulting_run_state_version=4,
        session_id=e.destination_session_id,initial_session_state_version=0,
        scenario_id=family.destination_root.scenario_id,
        scenario_content_version=family.destination_root.scenario_content_version,
        run_context=project_native_context(_result(family.admission)),visit=_visit(family,2))


@dataclass(frozen=True)
class RunContinuationService:
    authority: RunExitService
    content_registry: SessionContentRegistry

    def _eligible(self, family, character, persisted, state):
        runtime = state.scenario_runtime
        return (type(family) is NativeRunAdmissionV1
            and character.lifecycle is PlayerCharacterLifecycle.ACTIVE
            and family.canonical_run.trusted_participation_references[0].session_id == persisted.session.session_id
            and runtime is not None and (runtime.ending_id,runtime.ending_status.value) in SOURCE_ENDINGS
            and bool(self.content_registry.continuation_pool()))

    def _status(self, family, character, persisted, state):
        if type(family) in (NativeRunRegionalRevisitV1, NativeRunRegionalRevisitTerminatedV1):
            raise RunContinuationError("RUN_CONTINUATION_NOT_AVAILABLE")
        run = family.canonical_run
        ordinal = next(i for i,p in enumerate(run.trusted_participation_references,1) if p.session_id == persisted.session.session_id)
        continued = type(family) in (NativeRunContinuedV1,NativeRunContinuedTerminatedV1)
        predecessor = None
        arrival = None
        if ordinal == 2:
            from deviation_protocol.application.world_visit_context import project_world_arrival
            arrival = project_world_arrival(_continued(family))
            source = _continued(family).source_root
            predecessor = dict(session_id=source.session_id,session_state_version=source.snapshot_state_version,
                scenario_id=source.scenario_id,scenario_content_version=source.scenario_content_version,visit=_visit(family,1))
        return dict(schema_version="native-run-continuation-status/v1",session_id=persisted.session.session_id,
            run_id=run.run_id.value,run_state_version=run.state_version.value,
            session_state_version=persisted.session.state_version,lifecycle_status=run.lifecycle_status.value,
            can_continue=self._eligible(family,character,persisted,state),
            current_session_id=run.trusted_participation_references[-1].session_id,
            visit=_visit(family,ordinal) if continued else None,predecessor=predecessor,arrival=arrival,
            successor=continuation_result(family) if continued and ordinal == 1 else None)

    async def _read(self, uow, principal, session_id, controller, *, locking=False):
        try:
            participation = await self.authority._target(uow,principal,session_id)
            values = await self.authority._owned_family(uow,principal,session_id,controller,participation,locking=locking)
            if (values[3].scenario_runtime is not None and values[3].scenario_runtime.ending_status.value in ("RESOLVED","FAILED")
                    and await uow.narrative_jobs.get_active_for_session(session_id,for_update=locking) is not None):
                raise SnapshotInvalidError(session_id)
            return participation, values
        except RunExitError as error:
            raise RunContinuationError(error.code) from None

    async def status(self, principal, *, session_id):
        controller = await self.authority._controller(principal,session_id)
        async with self.authority.session_service.uow_factory() as uow:
            _, values = await self._read(uow,principal,session_id,controller)
            return self._status(*values)

    async def continue_run(self, principal, *, session_id, command):
        revalidate_run_model(command,RunContinuationCommand)
        controller = await self.authority._controller(principal,session_id)
        async with self.authority.session_service.uow_factory() as reader:
            participation, (family,character,persisted,state) = await self._read(reader,principal,session_id,controller)
            target = family.canonical_run.player_character_binding.applicable_character_reference.player_character_id
            run = family.canonical_run
            request = NativeRunContinuationRequestV1(schema="run.continue-native-request/v1",
                controller_binding=controller.value,player_id=principal.player_id,
                public_operation_key=command.public_operation_key.value,run_id=run.run_id.value,
                continuous_story_line_id=run.continuous_story_line_id.value,source_session_id=session_id,
                expected_run_state_version=command.expected_run_state_version,
                expected_session_state_version=command.expected_session_state_version,
                source_reference=self.authority.source_reference.value)
            key = RunReceiptKey(run_id=run.run_id,operation_namespace=RunOperationNamespace.CONTINUE_NATIVE_V1,
                operation_id=request.operation_id())
            # Replay is resolved under final locked authority too; no new identity
            # is issued for an already-continued or otherwise unavailable family.
            prepare = self._eligible(family,character,persisted,state)
            source_fingerprint = state_fingerprint(state)
        prepared = None
        if prepare:
            time = self.authority.clock().astimezone(timezone.utc).replace(microsecond=0)
            destination_service = self.content_registry.resolve("undelivered_receipt","undelivered-receipt-1.0.0").session_service
            prepared = destination_service.prepare_world_continuation_initialization(principal,
                creation_request_id=request.creation_request_id(),source_state=state,
                entry_variant=state.scenario_runtime.ending_status.value.lower(),created_at=time)
        commit_issued = False
        try:
            async with self.authority.uow_factory() as uow:
                character = await uow.player_characters.get_for_update(target)
                if character is None or character.controller_binding != controller:
                    raise SessionNotFoundError(session_id)
                current_participation, (family,character,persisted,state) = await self._read(uow,principal,session_id,controller,locking=True)
                if current_participation != participation:
                    raise SnapshotInvalidError(session_id)
                receipt = await uow.run_mutation_receipts.get(key)
                if receipt is not None:
                    if receipt.fingerprint.value != request.fingerprint():
                        raise RunContinuationError("IDEMPOTENCY_CONFLICT")
                    if (type(family) not in (NativeRunContinuedV1,NativeRunContinuedTerminatedV1,NativeRunRegionalRevisitV1,NativeRunRegionalRevisitTerminatedV1)
                            or _continued(family).continuation_evidence.request != request):
                        raise SnapshotInvalidError(session_id)
                    return continuation_result(family)
                if type(family) is not NativeRunAdmissionV1 or character.lifecycle is not PlayerCharacterLifecycle.ACTIVE:
                    raise RunContinuationError("RUN_CONTINUATION_NOT_AVAILABLE")
                if command.expected_run_state_version != 3 or command.expected_session_state_version != persisted.session.state_version:
                    raise RunContinuationError("RUN_CONTINUATION_STALE")
                if not self._eligible(family,character,persisted,state):
                    raise RunContinuationError("RUN_CONTINUATION_NOT_AVAILABLE")
                if prepared is None or source_fingerprint != state_fingerprint(state):
                    raise RunContinuationError("RUN_CONTINUATION_STALE")
                initial_state = await destination_service.stage_run_entry_initialization(uow,prepared)
                run = family.canonical_run
                common = dict(run_id=run.run_id.value,continuous_story_line_id=run.continuous_story_line_id.value)
                source_visit = derive_world_visit_id(**common,session_id=session_id,joined_state_version=3).value
                destination_visit = derive_world_visit_id(**common,session_id=prepared.session.session_id,joined_state_version=4).value
                def root(world,region,visit,game_session,state,basis):
                    bundle = self.content_registry.for_session(game_session)
                    return WorldStateRootV1(schema="run-world-state/v1",**common,world=world,region=region,
                        first_visit_id=visit,session_id=game_session.session_id,scenario_id=game_session.scenario_id,
                        scenario_content_version=game_session.scenario_version,content_sha256=bundle.content_sha256,
                        basis=basis,snapshot_state_version=game_session.state_version,snapshot=state.to_snapshot(),snapshot_sha256=state_fingerprint(state))
                source_root = root(SOURCE_WORLD,SOURCE_REGION,source_visit,persisted.session,state,"sealed_ending")
                destination_root = root(DESTINATION_WORLD,DESTINATION_REGION,destination_visit,prepared.session,initial_state,"session_initialization")
                ending = ContinuationSourceEndingV1(scenario_id=persisted.session.scenario_id,
                    scenario_content_version=state.content_version,ending_id=state.scenario_runtime.ending_id,
                    ending_status=state.scenario_runtime.ending_status.value,session_state_version=persisted.session.state_version,
                    snapshot_sha256=source_fingerprint)
                inputs = ContinuationSelectionInputsV1(selector_version="same-line-continuation/v1",**common,
                    source_session_id=session_id,source_session_state_version=persisted.session.state_version,
                    source_snapshot_sha256=source_fingerprint,source_world=SOURCE_WORLD,
                    source_ending_id=ending.ending_id,source_ending_status=ending.ending_status,
                    resolution_fingerprint=family.protocol_binding.resolved_protocol.fingerprint.value,
                    visited_worlds=(SOURCE_WORLD,),eligible_pool=self.content_registry.continuation_pool())
                evidence = NativeRunContinuationEvidenceV1(schema="run.continue-native-evidence/v1",request=request,
                    source_ending=ending,selection_inputs=inputs,selection_seed=inputs.seed(),
                    source_visit_id=source_visit,destination_visit_id=destination_visit,
                    destination_session_id=prepared.session.session_id,destination_creation_request_id=request.creation_request_id(),
                    destination_initial_event_id=prepared.initialization_event.event_id,destination_random_seed=prepared.session.random_seed,
                    source_world_state_sha256=source_root.digest(),destination_world_state_sha256=destination_root.digest(),
                    carryover_rule="carry-player-state/v1",entry_variant=ending.ending_status.lower(),occurred_at=time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"))
                successor = continue_native_run(family,evidence)
                visits = tuple(WorldVisitV1(**common,visit_id=visit,visit_ordinal=ordinal,
                    world_id=world.world_id,world_version=world.world_version,region_id=region.region_id,region_version=region.region_version,
                    session_id=sid,joined_state_version=ordinal+2,materialized_state_version=4,
                    operation_id=request.operation_id().value,source_reference=request.source_reference,
                    entered_at=run.creation_provenance.occurred_at if ordinal==1 else time,created_at=time)
                    for ordinal,world,region,visit,sid in ((1,SOURCE_WORLD,SOURCE_REGION,source_visit,session_id),
                        (2,DESTINATION_WORLD,DESTINATION_REGION,destination_visit,prepared.session.session_id)))
                continued = NativeRunContinuedV1(admission=family,canonical_run=successor,continuation_evidence=evidence,
                    source_root=source_root,destination_root=destination_root,visits=visits,
                    position=WorldPositionV1(**common,visit_id=destination_visit,session_id=prepared.session.session_id,position_state_version=4,created_at=time))
                await uow.runs.append_revision(successor,created_at=time)
                await uow.run_participations.add(successor.trusted_participation_references[1],joined_at=time)
                if not await uow.runs.compare_and_swap_current(successor,expected_state_version=3,updated_at=time):
                    raise RunContinuationError("RUN_CONTINUATION_CONFLICT")
                receipt = StoredRunSuccessReceipt(key=key,fingerprint=RunOperationFingerprint(value=request.fingerprint()),
                    command_kind=RunMutationKind.CONTINUE_NATIVE_RUN,result=RunSafeResult(
                        result_schema_version=CONTINUE_NATIVE_RUN_RESULT_SCHEMA_VERSION,run_id=run.run_id,
                        continuous_story_line_id=run.continuous_story_line_id,lifecycle_status=successor.lifecycle_status,
                        resulting_state_version=successor.state_version,participation_reference=successor.trusted_participation_references[1]))
                await uow.run_mutation_receipts.add(receipt,created_at=time,continuation_evidence=evidence)
                await uow.run_world_continuations.add(continued)
                classified = await uow.run_protocol_bindings.get_classified_for_update(run_id=run.run_id)
                if classified != continued:
                    raise SnapshotInvalidError(session_id)
                result = continuation_result(classified)
                commit_issued = True
                await uow.commit()
                return result
        except BaseException as error:
            if commit_issued:
                from deviation_protocol.application.ports import NativeRunAdmissionOutcomeUnknownError
                if not isinstance(error,Exception):
                    error.commit_outcome_unknown = True
                    raise
                if not isinstance(error,NativeRunAdmissionOutcomeUnknownError):
                    raise NativeRunAdmissionOutcomeUnknownError("continuation commit or cleanup outcome unknown") from error
            raise
