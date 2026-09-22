"""Owned regional transition and read-only, path-specific journey projection."""
from dataclasses import dataclass
from datetime import timezone

from deviation_protocol.application.errors import SessionNotFoundError, SnapshotInvalidError
from deviation_protocol.application.run_exit_service import RunExitCommand
from deviation_protocol.application.run_continuation_service import (
    RunContinuationService, RunContinuationError, original_admission, _visit,
)
from deviation_protocol.application.run_operations import (
    RunOperationNamespace, RunReceiptKey, RunOperationFingerprint, RunSafeResult,
    StoredRunSuccessReceipt, REVISIT_NATIVE_REGION_RESULT_SCHEMA_VERSION,
)
from deviation_protocol.application.scenario_initialization import _seal_regional_base
from deviation_protocol.application.narrative_outcome_policy import state_fingerprint
from deviation_protocol.domain.player_character import PlayerCharacterLifecycle
from deviation_protocol.domain.run import revalidate_run_model, RunMutationKind
from deviation_protocol.domain.run_protocol_binding import (
    NativeRunAdmissionV1, NativeRunContinuedV1, NativeRunContinuedTerminatedV1,
    NativeRunRegionalRevisitV1, NativeRunRegionalRevisitTerminatedV1, NativeRunRegionalCompletedV1, revisit_native_region,
)
from deviation_protocol.domain.world_continuation import DESTINATION_WORLD, WorldRefV1, RegionRefV1
from deviation_protocol.domain.world_revisit import (
    ARCHIVE_REGION, ARCHIVE_IDENTITY, ARCHIVE_NOTICE, HELD_ENDING,
    NativeRunRegionalRevisitRequestV1, NativeRunRegionalRevisitEvidenceV1,
    RegionalSourceEndingV1, RegionalSelectionInputsV1, RegionalSelectionVisitV1,
    RegionalEntryV1, WorldVisitV2, WorldPositionV2, derive_regional_visit_id,
)


class RunRevisitError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class RunRevisitCommand(RunExitCommand):
    pass


def regional_family(family):
    return family.revisited if type(family) in (NativeRunRegionalRevisitTerminatedV1, NativeRunRegionalCompletedV1) else family


def regional_result(family):
    from deviation_protocol.application.native_run_admission import _result
    from deviation_protocol.application.public_run_protocol import project_native_context
    family = regional_family(family)
    revalidate_run_model(family, NativeRunRegionalRevisitV1)
    e = family.revisit_evidence
    return dict(schema_version="native-run-revisit-result/v1", source_session_id=e.request.source_session_id,
        source_session_state_version=e.source_ending.session_state_version,
        run_id=family.canonical_run.run_id.value, resulting_run_state_version=5,
        session_id=e.destination_session_id, initial_session_state_version=0,
        scenario_id=family.entry.scenario_id, scenario_content_version=family.entry.scenario_content_version,
        run_context=project_native_context(_result(family.admission)), visit=journey_visit(family, 3))


def journey_visit(family, ordinal):
    from deviation_protocol.domain.fog_patrol import FogContinuedV1, FogTerminatedV1
    if type(family) in (FogContinuedV1, FogTerminatedV1):
        from deviation_protocol.application.fog_continuation_service import fog_visit
        return fog_visit(family, ordinal)
    if ordinal != 3:
        return _visit(family, ordinal)
    visit = regional_family(family).visit
    return {key: getattr(visit, key) for key in ("visit_id", "visit_ordinal", "world_id",
                                               "world_version", "region_id", "region_version")}


def regional_arrival():
    return dict(previous_ending_status="RESOLVED", previous_ending_title="回执待核，发运暂缓",
                entry_notice=ARCHIVE_NOTICE)


@dataclass(frozen=True)
class RunRegionalRevisitService:
    continuation: RunContinuationService

    @property
    def authority(self):
        return self.continuation.authority

    @property
    def registry(self):
        return self.continuation.content_registry

    async def _read(self, *args, **kwargs):
        try:
            return await self.continuation._read(*args, **kwargs)
        except RunContinuationError as error:
            raise RunRevisitError(error.code) from None

    def _eligible(self, family, character, persisted, state):
        runtime = state.scenario_runtime
        return (type(family) is NativeRunContinuedV1
            and character.lifecycle is PlayerCharacterLifecycle.ACTIVE
            and family.position.session_id == persisted.session.session_id
            and runtime is not None and runtime.ending_id == HELD_ENDING
            and runtime.ending_status.value == "RESOLVED")

    async def _base(self, uow, persisted, state, *, locking=False):
        try:
            return _seal_regional_base(session_id=persisted.session.session_id, state=state,
                bundle=self.registry.for_session(persisted.session),
                events=await uow.run_world_revisits.source_events(persisted.session.session_id, locking=locking))
        except (TypeError, ValueError, AttributeError):
            raise SnapshotInvalidError(persisted.session.session_id) from None

    async def journey(self, principal, *, session_id):
        from deviation_protocol.application.native_run_admission import _result
        from deviation_protocol.application.public_run_protocol import project_native_context
        from deviation_protocol.application.world_visit_context import project_world_arrival
        controller = await self.authority._controller(principal, session_id)
        async with self.authority.session_service.uow_factory() as uow:
            _, (family, character, persisted, state) = await self._read(uow, principal, session_id, controller)
            from deviation_protocol.domain.fog_patrol import FogContinuedV1, FogTerminatedV1
            from deviation_protocol.application.fog_continuation_service import FogContinuationService, fog_visit, fog_arrival, NOTICE
            fog = original_admission(family).world_binding.entry_world.scenario_id == "fog_station"
            run = family.canonical_run
            associations = []
            for ordinal, participation in enumerate(run.trusted_participation_references, 1):
                owned = await uow.sessions.get_owned(participation.session_id, principal.player_id)
                if owned is None:
                    raise SnapshotInvalidError(session_id)
                game = owned.session
                associations.append(dict(session_id=game.session_id, session_state_version=game.state_version,
                    scenario_id=game.scenario_id, scenario_content_version=game.scenario_version,
                    visit=(fog_visit(family, ordinal) if fog else journey_visit(family, ordinal)) if len(run.trusted_participation_references) > 1 else None))
            index = next(i for i, row in enumerate(associations) if row["session_id"] == session_id)
            transition = None
            if fog and self.continuation._eligible(family, character, persisted, state):
                await FogContinuationService(self.continuation).history(uow, persisted, state)
                transition = dict(kind="fog_patrol", world_title="雾哨站", region_title="巡路风口", notice=NOTICE)
            elif self.continuation._eligible(family, character, persisted, state):
                transition = dict(kind="first_continuation", world_title="未送达的回执", region_title="发运大厅",
                    notice="沿用当前角色和剩余资源进入发运大厅；原有资源不会恢复。")
            elif self._eligible(family, character, persisted, state):
                await self._base(uow, persisted, state)
                self.registry.regional_pool()
                transition = dict(kind="regional_revisit", world_title="未送达的回执", region_title="核验档案室", notice=ARCHIVE_NOTICE)
            arrival = None
            if fog and index == 1:
                arrival = fog_arrival(family, self.registry)
            elif index == 1:
                prefix = regional_family(family).continued if type(family) in (NativeRunRegionalRevisitV1, NativeRunRegionalRevisitTerminatedV1, NativeRunRegionalCompletedV1) else family
                if type(prefix) is NativeRunContinuedTerminatedV1:
                    prefix = prefix.continued
                arrival = project_world_arrival(prefix)
            elif index == 2:
                arrival = regional_arrival()
            result = dict(schema_version="native-run-journey/v1", session_id=session_id,
                run_id=run.run_id.value, run_state_version=run.state_version.value,
                lifecycle_status=run.lifecycle_status.value,
                run_context=project_native_context(_result(original_admission(family))),
                path=associations[index], current=associations[-1],
                predecessor=associations[index - 1] if index else None,
                successor=associations[index + 1] if index + 1 < len(associations) else None,
                next_transition=transition, arrival=arrival)
            if type(family) is NativeRunRegionalCompletedV1:
                from deviation_protocol.application.run_completion_service import completion_projection
                result.update(schema_version="native-run-journey/v2", completion=completion_projection(family))
            return result

    async def revisit(self, principal, *, session_id, command):
        revalidate_run_model(command, RunRevisitCommand)
        controller = await self.authority._controller(principal, session_id)
        async with self.authority.session_service.uow_factory() as reader:
            participation, (family, character, persisted, state) = await self._read(reader, principal, session_id, controller)
            run = family.canonical_run
            request = NativeRunRegionalRevisitRequestV1(schema="run.revisit-native-region-request/v1",
                controller_binding=controller.value, player_id=principal.player_id,
                public_operation_key=command.public_operation_key.value, run_id=run.run_id.value,
                continuous_story_line_id=run.continuous_story_line_id.value, source_session_id=session_id,
                expected_run_state_version=command.expected_run_state_version,
                expected_session_state_version=command.expected_session_state_version,
                source_reference=self.authority.source_reference.value)
            key = RunReceiptKey(run_id=run.run_id, operation_namespace=RunOperationNamespace.REVISIT_NATIVE_REGION_V1,
                                operation_id=request.operation_id())
            receipt = await reader.run_mutation_receipts.get(key)
            if receipt is not None:
                return self._replay(family, receipt, request, session_id)
            if not self._eligible(family, character, persisted, state):
                raise RunRevisitError("RUN_REVISIT_NOT_AVAILABLE")
            base = await self._base(reader, persisted, state)
            target = run.player_character_binding.applicable_character_reference.player_character_id
        service = self.registry.resolve(*ARCHIVE_IDENTITY).session_service
        time = self.authority.clock().astimezone(timezone.utc).replace(microsecond=0)
        prepared = service.prepare_regional_revisit_initialization(principal,
            creation_request_id=request.creation_request_id(), base=base, created_at=time)
        commit_issued = False
        try:
            async with self.authority.uow_factory() as uow:
                character = await uow.player_characters.get_for_update(target)
                if character is None or character.controller_binding != controller:
                    raise SessionNotFoundError(session_id)
                current_participation, (family, character, persisted, state) = await self._read(
                    uow, principal, session_id, controller, locking=True)
                if current_participation != participation:
                    raise SnapshotInvalidError(session_id)
                receipt = await uow.run_mutation_receipts.get(key)
                if receipt is not None:
                    return self._replay(family, receipt, request, session_id)
                if not self._eligible(family, character, persisted, state):
                    raise RunRevisitError("RUN_REVISIT_NOT_AVAILABLE")
                if command.expected_run_state_version != 4 or command.expected_session_state_version != persisted.session.state_version:
                    raise RunRevisitError("RUN_REVISIT_STALE")
                current_base = await self._base(uow, persisted, state, locking=True)
                if current_base.snapshot != base.snapshot:
                    raise RunRevisitError("RUN_REVISIT_STALE")
                initial = await service.stage_run_entry_initialization(uow, prepared)
                run = family.canonical_run
                common = dict(run_id=run.run_id.value, continuous_story_line_id=run.continuous_story_line_id.value)
                visit_id = derive_regional_visit_id(**common, session_id=prepared.session.session_id, joined_state_version=5).value
                inputs = RegionalSelectionInputsV1(selector_version="regional-revisit/v1", **common,
                    source_session_id=session_id, source_session_state_version=persisted.session.state_version,
                    source_snapshot_sha256=base.digest(), resolution_fingerprint=family.admission.protocol_binding.resolved_protocol.fingerprint.value,
                    visits=tuple(RegionalSelectionVisitV1(visit_id=v.visit_id, visit_ordinal=v.visit_ordinal,
                        session_id=v.session_id, world=WorldRefV1(world_id=v.world_id, world_version=v.world_version),
                        region=RegionRefV1(region_id=v.region_id, region_version=v.region_version)) for v in family.visits),
                    eligible_pool=self.registry.regional_pool())
                entry = RegionalEntryV1(schema="run-regional-entry/v1", **common, visit_id=visit_id,
                    session_id=prepared.session.session_id, world=DESTINATION_WORLD, region=ARCHIVE_REGION,
                    scenario_id=ARCHIVE_IDENTITY[0], scenario_content_version=ARCHIVE_IDENTITY[1],
                    content_sha256=inputs.eligible_pool[0].content_sha256, base_visit_id=family.position.visit_id,
                    base_session_id=session_id, base_session_state_version=persisted.session.state_version,
                    base_snapshot_sha256=base.digest(), unlock_ending_id=HELD_ENDING,
                    snapshot_state_version=0, snapshot=initial.to_snapshot(), snapshot_sha256=state_fingerprint(initial))
                evidence = NativeRunRegionalRevisitEvidenceV1(schema="run.revisit-native-region-evidence/v1", request=request,
                    source_ending=RegionalSourceEndingV1(scenario_id="undelivered_receipt", scenario_content_version="undelivered-receipt-1.0.0",
                        ending_id=HELD_ENDING, ending_status="RESOLVED", session_state_version=persisted.session.state_version,
                        snapshot_sha256=base.digest()), selection_inputs=inputs, selection_seed=inputs.seed(),
                    source_visit_id=family.position.visit_id, destination_visit_id=visit_id,
                    destination_session_id=prepared.session.session_id, destination_creation_request_id=request.creation_request_id(),
                    destination_initial_event_id=prepared.initialization_event.event_id, destination_random_seed=prepared.session.random_seed,
                    world_base_snapshot_sha256=base.digest(), destination_entry_sha256=entry.digest(),
                    carryover_rule="carry-player-state/v1", occurred_at=time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"))
                successor = revisit_native_region(family, evidence)
                revisited = NativeRunRegionalRevisitV1(continued=family, canonical_run=successor,
                    revisit_evidence=evidence, entry=entry, visit=WorldVisitV2(**common, visit_id=visit_id,
                        session_id=prepared.session.session_id, visit_ordinal=3, world_id=DESTINATION_WORLD.world_id,
                        world_version=1, region_id=ARCHIVE_REGION.region_id, region_version=1, joined_state_version=5,
                        materialized_state_version=5, operation_id=request.operation_id().value,
                        source_reference=request.source_reference, entered_at=time, created_at=time),
                    position=WorldPositionV2(**common, visit_id=visit_id, session_id=prepared.session.session_id,
                        position_state_version=5, created_at=family.position.created_at))
                await uow.runs.append_revision(successor, created_at=time)
                await uow.run_participations.add(successor.trusted_participation_references[2], joined_at=time)
                if not await uow.runs.compare_and_swap_current(successor, expected_state_version=4, updated_at=time):
                    raise RunRevisitError("RUN_REVISIT_CONFLICT")
                receipt = StoredRunSuccessReceipt(key=key, fingerprint=RunOperationFingerprint(value=request.fingerprint()),
                    command_kind=RunMutationKind.REVISIT_NATIVE_REGION,
                    result=RunSafeResult(result_schema_version=REVISIT_NATIVE_REGION_RESULT_SCHEMA_VERSION,
                        run_id=run.run_id, continuous_story_line_id=run.continuous_story_line_id,
                        lifecycle_status=successor.lifecycle_status, resulting_state_version=successor.state_version,
                        participation_reference=successor.trusted_participation_references[2]))
                await uow.run_mutation_receipts.add(receipt, created_at=time, revisit_evidence=evidence)
                await uow.run_world_revisits.add(revisited)
                classified = await uow.run_protocol_bindings.get_classified_for_update(run_id=run.run_id)
                if classified != revisited:
                    raise SnapshotInvalidError(session_id)
                result = regional_result(classified)
                commit_issued = True
                await uow.commit()
                return result
        except BaseException as error:
            if commit_issued:
                from deviation_protocol.application.ports import NativeRunAdmissionOutcomeUnknownError
                if not isinstance(error, Exception):
                    error.commit_outcome_unknown = True
                    raise
                if not isinstance(error, NativeRunAdmissionOutcomeUnknownError):
                    raise NativeRunAdmissionOutcomeUnknownError("regional commit or cleanup outcome unknown") from error
            raise

    @staticmethod
    def _replay(family, receipt, request, session_id):
        if receipt.fingerprint.value != request.fingerprint():
            raise RunRevisitError("IDEMPOTENCY_CONFLICT")
        if (type(family) not in (NativeRunRegionalRevisitV1, NativeRunRegionalRevisitTerminatedV1, NativeRunRegionalCompletedV1)
                or regional_family(family).revisit_evidence.request != request):
            raise SnapshotInvalidError(session_id)
        return regional_result(family)
