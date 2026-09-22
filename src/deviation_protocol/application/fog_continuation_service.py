"""One explicitly confirmed, atomically bound patrol continuation."""
from dataclasses import dataclass
from datetime import timezone
from deviation_protocol.application.errors import SessionNotFoundError, SnapshotInvalidError
from deviation_protocol.application.fog_history import event_records, verify_history
from deviation_protocol.application.narrative_outcome_policy import state_fingerprint
from deviation_protocol.application.run_operations import (
    RunOperationNamespace, RunReceiptKey, StoredRunSuccessReceipt, RunSafeResult,
    RunOperationFingerprint, CONTINUE_NATIVE_RUN_RESULT_SCHEMA_VERSION,
)
from deviation_protocol.domain.player_character import PlayerCharacterLifecycle
from deviation_protocol.domain.run import RunMutationKind, revalidate_run_model
from deviation_protocol.domain.run_protocol_binding import NativeRunAdmissionV1
from deviation_protocol.domain.world_continuation import NativeRunContinuationRequestV1, WorldPositionV1, derive_world_visit_id
from deviation_protocol.domain.fog_patrol import (
    FogContinuedV1, FogTerminatedV1, FogSourceV1, FogEntryV1, FogVisitV1,
    FogContinuationEvidenceV1, continue_fog_run, SOURCE, DESTINATION, ENDINGS, SOURCE_REGION, REGION,
)

NOTICE = "沿着雾哨站的巡路走到风口，与岑舟再会；沿用当前角色与剩余资源。"
ENDING_TITLES = dict(zip(ENDINGS, ("带着平安离开", "道谢之后", "各自继续", "门口的告别")))


def fog_arrival(family, registry):
    source = fog_prefix(family).source_root
    definition = registry.resolve(source.scenario_id, source.scenario_content_version).scenario_catalog.scenarios[0]
    ending = next(e for e in definition.public_client.endings
        if e.ending_id == source.snapshot["scenario_runtime"]["ending_id"])
    return dict(previous_ending_status="RESOLVED", previous_ending_title=ending.title, entry_notice=NOTICE)


def fog_prefix(family):
    return family.continued if type(family) is FogTerminatedV1 else family


def fog_visit(family, ordinal):
    visit = fog_prefix(family).visits[ordinal - 1]
    return {name: getattr(visit, name) for name in (
        "visit_id", "visit_ordinal", "world_id", "world_version", "region_id", "region_version")}


def fog_result(family):
    from deviation_protocol.application.native_run_admission import _result
    from deviation_protocol.application.public_run_protocol import project_native_context
    family = fog_prefix(family)
    revalidate_run_model(family, FogContinuedV1)
    source, entry = family.source_root, family.entry
    return dict(schema_version="native-run-continuation-result/v1",
        source_session_id=source.session_id, source_session_state_version=source.snapshot_state_version,
        run_id=family.canonical_run.run_id.value, resulting_run_state_version=4,
        session_id=entry.session_id, initial_session_state_version=0,
        scenario_id=entry.scenario_id, scenario_content_version=entry.scenario_content_version,
        run_context=project_native_context(_result(family.admission)), visit=fog_visit(family, 2))


@dataclass(frozen=True)
class FogContinuationService:
    owner: object

    def eligible(self, family, character, persisted, state):
        runtime = state.scenario_runtime
        eligible = (type(family) is NativeRunAdmissionV1
            and family.canonical_run.state_version.value == 3
            and character.lifecycle is PlayerCharacterLifecycle.ACTIVE
            and family.canonical_run.trusted_participation_references[0].session_id == persisted.session.session_id
            and (persisted.session.scenario_id, persisted.session.scenario_version) == SOURCE
            and runtime is not None and runtime.ending_id in ENDINGS and runtime.ending_status.value == "RESOLVED")
        if eligible:
            self.owner.content_registry.resolve(*DESTINATION)
        return eligible

    async def history(self, uow, persisted, state, *, locking=False):
        records = event_records(await uow.run_world_revisits.source_events(persisted.session.session_id, locking=locking))
        verify_history(self.owner.content_registry.for_session(persisted.session), state,
            persisted.session.session_id, persisted.session.state_version, records)
        return records

    async def continue_run(self, principal, *, session_id, command):
        from deviation_protocol.application.run_continuation_service import RunContinuationCommand, RunContinuationError
        revalidate_run_model(command,RunContinuationCommand)
        controller = await self.owner.authority._controller(principal,session_id)
        async with self.owner.authority.session_service.uow_factory() as reader:
            participation, (family,character,persisted,state) = await self.owner._read(reader,principal,session_id,controller)
            target = family.canonical_run.player_character_binding.applicable_character_reference.player_character_id
            run = family.canonical_run
            request = NativeRunContinuationRequestV1(schema="run.continue-native-request/v1",
                controller_binding=controller.value,player_id=principal.player_id,
                public_operation_key=command.public_operation_key.value,run_id=run.run_id.value,
                continuous_story_line_id=run.continuous_story_line_id.value,source_session_id=session_id,
                expected_run_state_version=command.expected_run_state_version,
                expected_session_state_version=command.expected_session_state_version,
                source_reference=self.owner.authority.source_reference.value)
            key = RunReceiptKey(run_id=run.run_id,operation_namespace=RunOperationNamespace.CONTINUE_NATIVE_V1,
                operation_id=request.operation_id())
            # Replay is resolved under final locked authority too; no new identity
            # is issued for an already-continued or otherwise unavailable family.
            prepare = self.eligible(family,character,persisted,state)
            source_fingerprint = state_fingerprint(state)
            if prepare:
                await self.history(reader, persisted, state)
        prepared = None
        if prepare:
            time = self.owner.authority.clock().astimezone(timezone.utc).replace(microsecond=0)
            destination_service = self.owner.content_registry.resolve(*DESTINATION).session_service
            prepared = destination_service.prepare_fog_patrol_initialization(principal,
                creation_request_id=request.creation_request_id(),source_state=state,
                created_at=time)
        commit_issued = False
        try:
            async with self.owner.authority.uow_factory() as uow:
                character = await uow.player_characters.get_for_update(target)
                if character is None or character.controller_binding != controller:
                    raise SessionNotFoundError(session_id)
                current_participation, (family,character,persisted,state) = await self.owner._read(uow,principal,session_id,controller,locking=True)
                if current_participation != participation:
                    raise SnapshotInvalidError(session_id)
                receipt = await uow.run_mutation_receipts.get(key)
                if receipt is not None:
                    if receipt.fingerprint.value != request.fingerprint():
                        raise RunContinuationError("IDEMPOTENCY_CONFLICT")
                    if (type(family) not in (FogContinuedV1, FogTerminatedV1)
                            or fog_prefix(family).continuation_evidence.request != request):
                        raise SnapshotInvalidError(session_id)
                    return fog_result(family)
                if type(family) is not NativeRunAdmissionV1 or character.lifecycle is not PlayerCharacterLifecycle.ACTIVE:
                    raise RunContinuationError("RUN_CONTINUATION_NOT_AVAILABLE")
                if command.expected_run_state_version != 3 or command.expected_session_state_version != persisted.session.state_version:
                    raise RunContinuationError("RUN_CONTINUATION_STALE")
                if not self.eligible(family,character,persisted,state):
                    raise RunContinuationError("RUN_CONTINUATION_NOT_AVAILABLE")
                if prepared is None or source_fingerprint != state_fingerprint(state):
                    raise RunContinuationError("RUN_CONTINUATION_STALE")
                records = await self.history(uow, persisted, state, locking=True)
                initial_state = await destination_service.stage_run_entry_initialization(uow, prepared)
                run = family.canonical_run
                common = dict(run_id=run.run_id.value, continuous_story_line_id=run.continuous_story_line_id.value)
                source_visit = derive_world_visit_id(**common, session_id=session_id, joined_state_version=3).value
                destination_visit = derive_world_visit_id(**common, session_id=prepared.session.session_id, joined_state_version=4).value
                source_root = FogSourceV1(schema="fog-world-state/v1", **common,
                    first_visit_id=source_visit, session_id=session_id,
                    snapshot_state_version=persisted.session.state_version,
                    snapshot=state.to_snapshot(), snapshot_sha256=source_fingerprint, events=records)
                entry = FogEntryV1(schema="fog-patrol-entry/v1", **common,
                    visit_id=destination_visit, session_id=prepared.session.session_id,
                    source_session_id=session_id, source_digest=source_root.digest(),
                    content_sha256=self.owner.content_registry.resolve(*DESTINATION).content_sha256,
                    snapshot=initial_state.to_snapshot(), snapshot_sha256=state_fingerprint(initial_state))
                evidence = FogContinuationEvidenceV1(schema="run.fog-patrol-evidence/v1", request=request,
                    source_digest=source_root.digest(), destination_entry_digest=entry.digest(),
                    destination_session_id=prepared.session.session_id,
                    destination_creation_request_id=request.creation_request_id(),
                    destination_initial_event_id=prepared.initialization_event.event_id,
                    destination_random_seed=prepared.session.random_seed,
                    resolution_fingerprint=family.protocol_binding.resolved_protocol.fingerprint.value,
                    occurred_at=time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"))
                successor = continue_fog_run(family, evidence)
                visits = tuple(FogVisitV1(**common, visit_id=visit, visit_ordinal=ordinal,
                    region_id=SOURCE_REGION if ordinal == 1 else REGION,
                    session_id=sid, joined_state_version=ordinal+2,
                    operation_id=request.operation_id().value, source_reference=request.source_reference,
                    entered_at=run.creation_provenance.occurred_at if ordinal == 1 else time, created_at=time)
                    for ordinal,visit,sid in ((1,source_visit,session_id),(2,destination_visit,prepared.session.session_id)))
                continued = FogContinuedV1(admission=family, canonical_run=successor,
                    continuation_evidence=evidence, source_root=source_root, entry=entry, visits=visits,
                    position=WorldPositionV1(**common, visit_id=destination_visit,
                        session_id=prepared.session.session_id, position_state_version=4, created_at=time))
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
                result = fog_result(classified)
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
