"""Explicit completion consent over the existing pinned native transaction."""
from dataclasses import dataclass
from datetime import datetime

from deviation_protocol.application.errors import SessionNotFoundError, SnapshotInvalidError
from deviation_protocol.application.narrative_outcome_policy import state_fingerprint
from deviation_protocol.application.run_exit_service import RunExitCommand
from deviation_protocol.application.run_revisit_service import RunRegionalRevisitService, journey_visit
from deviation_protocol.application.run_operations import (
    RunOperationNamespace, RunReceiptKey, RunOperationFingerprint, RunSafeResult,
    StoredRunSuccessReceipt, COMPLETE_REVISITED_NATIVE_RUN_RESULT_SCHEMA_VERSION,
)
from deviation_protocol.domain.events import DomainEvent
from deviation_protocol.domain.player_character import PlayerCharacterLifecycle
from deviation_protocol.domain.run import RunMutationKind, revalidate_run_model
from deviation_protocol.domain.run_completion import (
    NativeRunCompletionRequestV1, NativeRunCompletionEvidenceV1,
    CompletionSourceV1, CompletionDecisionEventV1, CanonTransitionV1,
    CompletionPreservedFactsV1, RunCompletionEligibilityPolicy,
)
from deviation_protocol.domain.run_protocol_binding import (
    NativeRunRegionalRevisitV1, NativeRunRegionalCompletedV1, complete_revisited_native_run,
)
from deviation_protocol.domain.world_continuation import WorldRefV1, RegionRefV1, DESTINATION_WORLD


class RunCompletionError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class RunCompletionCommand(RunExitCommand):
    pass


def completion_projection(family):
    revalidate_run_model(family, NativeRunRegionalCompletedV1)
    return dict(completion_id=family.completion_evidence.completion_id,
        outcome="unresolved_record_preserved", title="待核事项保留，核验旅程已结案",
        notice="本次旅程已正常完成。发运暂缓继续有效，送达仍未得到证明；旧记录与资源保持原状。",
        canon_outcome=dict(dispatch="held", delivery="unproven", record="sealed", verification="closed_unresolved"))


def completion_result(family):
    from deviation_protocol.application.native_run_admission import _result
    from deviation_protocol.application.public_run_protocol import project_native_context
    evidence = family.completion_evidence
    return dict(schema_version="native-run-completion-result/v1",
        source_session_id=evidence.request.source_session_id,
        source_session_state_version=evidence.sources[2].session_state_version,
        run_id=family.canonical_run.run_id.value, resulting_run_state_version=6,
        lifecycle_status="completed", run_context=project_native_context(_result(family.admission)),
        visit=journey_visit(family.revisited, 3), completion=completion_projection(family))


def validated_completion_decision(session_id, state, events, *, seal):
    """Bind actual repository events to runtime and completed memory before use."""
    scenario = "receipt_archive" if seal else "undelivered_receipt"
    decision = scenario + (".decision.record" if seal else ".decision.dispatch")
    action = scenario + (".action.seal" if seal else ".action.hold")
    inner = "receipt_archive.record.sealed" if seal else "dispatch.held"
    runtime = state.scenario_runtime
    by_id, by_sequence, scenario_ids, matches = {}, set(), set(), []
    for event in events:
        if (type(event) is not DomainEvent or event.session_id != session_id
                or type(event.event_id) is not str or not event.event_id
                or type(event.sequence_no) is not int or not 1 <= event.sequence_no <= 2**63 - 1
                or event.event_id in by_id or event.sequence_no in by_sequence
                or type(event.payload) is not dict):
            raise ValueError("invalid persisted completion event")
        by_id[event.event_id] = event
        by_sequence.add(event.sequence_no)
        scenario_id = event.payload.get("scenario_event_id")
        if scenario_id is not None:
            if type(scenario_id) is not str or scenario_id in scenario_ids:
                raise ValueError("ambiguous applied completion event")
            scenario_ids.add(scenario_id)
        if event.event_type == "ScenarioDecisionSelected" and event.payload.get("scenario_event_type") == inner:
            matches.append(event)
    records = state.player_memory.scenario_records
    if (len(matches) != 1 or runtime is None
            or not set(runtime.applied_event_ids) <= scenario_ids or len(records) != 1):
        raise ValueError("completion requires exact persisted decision provenance")
    event, record = matches[0], records[0]
    if (event.payload.get("decision_id") != decision or event.payload.get("selected_action_id") != action
            or event.payload.get("scenario_event_id") not in runtime.applied_event_ids
            or record.status.value != "COMPLETED" or record.scenario_id != scenario
            or record.scenario_content_version != state.content_version
            or record.ending_id != runtime.ending_id
            or record.last_source_event_id != event.event_id or record.last_source_sequence_no != event.sequence_no
            or state.player_memory.last_applied_source_event_id != event.event_id
            or state.player_memory.last_applied_source_sequence_no != event.sequence_no):
        raise ValueError("completion decision/memory association")
    return CompletionDecisionEventV1(session_id=session_id, event_id=event.event_id,
        sequence_no=event.sequence_no, scenario_event_id=event.payload["scenario_event_id"],
        decision_id=decision, selected_action_id=action)


def completion_evidence(*, prefix, request, states, versions, event_sets, registry, occurred_at):
    """Construct from fully reconstructed sources, never from public supplied facts."""
    revalidate_run_model(prefix, NativeRunRegionalRevisitV1)
    if len(states) != 3 or len(versions) != 3 or len(event_sets) != 3:
        raise ValueError("completion needs exactly three source snapshots")
    sources = []
    for visit, state, version in zip((*prefix.continued.visits, prefix.visit), states, versions):
        runtime = state.scenario_runtime
        bundle = registry.resolve(runtime.scenario_id, runtime.scenario_content_version)
        state = bundle.validate_snapshot(state.to_snapshot())
        sources.append(CompletionSourceV1(visit_id=visit.visit_id, visit_ordinal=visit.visit_ordinal,
            session_id=visit.session_id, session_state_version=version,
            world=WorldRefV1(world_id=visit.world_id, world_version=visit.world_version),
            region=RegionRefV1(region_id=visit.region_id, region_version=visit.region_version),
            scenario_id=bundle.scenario_id, scenario_content_version=bundle.content_version,
            content_sha256=bundle.content_sha256, snapshot_sha256=state_fingerprint(state),
            ending_id=runtime.ending_id, ending_status=runtime.ending_status.value))
    if (not RunCompletionEligibilityPolicy().qualifies(states[2])
            or states[1].scenario_runtime.mutable_fact_values.get("undelivered_receipt.fact.dispatch_held") is not True):
        raise ValueError("completion ending facts do not qualify")
    archive = registry.resolve("receipt_archive", "receipt-archive-1.0.0")
    fixed = {f.fact_id: f.value for f in archive.scenario_catalog.scenarios[0].facts}
    if (fixed.get("receipt_archive.fact.hold_effective") is not True
            or fixed.get("receipt_archive.fact.delivery_unproven") is not True):
        raise ValueError("completion cannot change archive canon")
    return NativeRunCompletionEvidenceV1(schema="run.complete-revisited-native-evidence/v1",
        request=request, completion_id=request.completion_id(), rule_version="receipt-archive-closure/v1",
        sources=tuple(sources),
        held_event=validated_completion_decision(sources[1].session_id, states[1], event_sets[1], seal=False),
        sealed_event=validated_completion_decision(sources[2].session_id, states[2], event_sets[2], seal=True),
        transition=CanonTransitionV1(schema="run.canon-transition/v1", kind="close_unresolved_verification/v1",
            world=DESTINATION_WORLD, from_disposition="open_unresolved", to_disposition="closed_unresolved",
            preserved_facts=CompletionPreservedFactsV1(dispatch_held=True, delivery_unproven=True, unresolved_sealed=True)),
        occurred_at=occurred_at.strftime("%Y-%m-%dT%H:%M:%S.%fZ"))


@dataclass(frozen=True)
class RunCompletionService:
    revisit: RunRegionalRevisitService

    @property
    def authority(self):
        return self.revisit.authority

    def _reason(self, family, character, persisted, state):
        run = family.canonical_run
        if not run.lifecycle_status.is_active_line:
            return "run_terminal"
        if run.trusted_participation_references[-1].session_id != persisted.session.session_id:
            return "not_current_visit"
        if character.lifecycle is not PlayerCharacterLifecycle.ACTIVE:
            return "character_ineligible"
        if type(family) is not NativeRunRegionalRevisitV1:
            return "route_not_eligible"
        if state.scenario_runtime.ending_status.value == "ACTIVE":
            return "session_not_ended"
        return "eligible" if RunCompletionEligibilityPolicy().qualifies(state) else "ending_not_eligible"

    async def status(self, principal, *, session_id):
        # All four public projections share the same full reconstruction authority.
        controller = await self.authority._controller(principal, session_id)
        async with self.authority.session_service.uow_factory() as uow:
            _, values = await self.revisit._read(uow, principal, session_id, controller)
            family, character, persisted, state = values
            reason = self._reason(*values)
            associations = []
            run = family.canonical_run
            for ordinal, participation in enumerate(run.trusted_participation_references, 1):
                owned = await uow.sessions.get_owned(participation.session_id, principal.player_id)
                if owned is None:
                    raise SnapshotInvalidError(session_id)
                game = owned.session
                associations.append(dict(session_id=game.session_id, session_state_version=game.state_version,
                    scenario_id=game.scenario_id, scenario_content_version=game.scenario_version,
                    visit=journey_visit(family, ordinal) if len(run.trusted_participation_references) > 1 else None))
            from deviation_protocol.application.native_run_admission import _result
            from deviation_protocol.application.public_run_protocol import project_native_context
            from deviation_protocol.application.run_continuation_service import original_admission
            return dict(schema_version="native-run-completion-status/v1", session_id=session_id,
                run_id=run.run_id.value, run_state_version=run.state_version.value,
                lifecycle_status=run.lifecycle_status.value,
                run_context=project_native_context(_result(original_admission(family))),
                path=next(a for a in associations if a["session_id"] == session_id), current=associations[-1],
                can_complete=reason == "eligible", reason=reason,
                offer=dict(title="完成本次旅程：保留待核事项",
                    notice="封存待核记录已确认；可以将本次旅程以待核事项保留结案。发运暂缓继续有效，送达仍未得到证明。") if reason == "eligible" else None,
                completion=completion_projection(family) if type(family) is NativeRunRegionalCompletedV1 else None)

    async def complete(self, principal, *, session_id, command):
        revalidate_run_model(command, RunCompletionCommand)
        controller = await self.authority._controller(principal, session_id)
        async with self.authority.session_service.uow_factory() as reader:
            participation, (family, _, _, _) = await self.revisit._read(reader, principal, session_id, controller)
            run = family.canonical_run
            request = NativeRunCompletionRequestV1(schema="run.complete-revisited-native-request/v1",
                controller_binding=controller.value, player_id=principal.player_id,
                public_operation_key=command.public_operation_key.value, run_id=run.run_id.value,
                continuous_story_line_id=run.continuous_story_line_id.value, source_session_id=session_id,
                expected_run_state_version=command.expected_run_state_version,
                expected_session_state_version=command.expected_session_state_version,
                source_reference=self.authority.source_reference.value)
            key = RunReceiptKey(run_id=run.run_id, operation_namespace=RunOperationNamespace.COMPLETE_REVISITED_NATIVE_V1,
                                operation_id=request.operation_id())
            receipt = await reader.run_mutation_receipts.get(key)
            if receipt is not None:
                replayed = self._replay_family(family, receipt, request, session_id)
            target = run.player_character_binding.applicable_character_reference.player_character_id
        if receipt is not None:
            return completion_result(replayed)
        commit_issued = False
        try:
            async with self.authority.uow_factory() as uow:
                character = await uow.player_characters.get_for_update(target)
                if character is None or character.controller_binding != controller:
                    raise SessionNotFoundError(session_id)
                current_participation, values = await self.revisit._read(uow, principal, session_id, controller, locking=True)
                family, character, persisted, state = values
                if current_participation != participation:
                    raise SnapshotInvalidError(session_id)
                receipt = await uow.run_mutation_receipts.get(key)
                if receipt is not None:
                    classified = self._replay_family(family, receipt, request, session_id)
                else:
                    if (type(family) is not NativeRunRegionalRevisitV1
                            or character.lifecycle is not PlayerCharacterLifecycle.ACTIVE
                            or family.position.session_id != session_id):
                        raise RunCompletionError("RUN_COMPLETION_NOT_AVAILABLE")
                    if (command.expected_run_state_version != 5
                            or command.expected_session_state_version != persisted.session.state_version):
                        raise RunCompletionError("RUN_COMPLETION_STALE")
                    if self._reason(*values) != "eligible":
                        raise RunCompletionError("RUN_COMPLETION_NOT_AVAILABLE")
                    states, versions, events = [], [], []
                    for reference in family.canonical_run.trusted_participation_references:
                        # The locked classifier has already validated and locked the
                        # ended historical sources in visit order. They are immutable;
                        # only the archive's final-turn state can be a fresh prerequisite.
                        current = reference.session_id == session_id
                        owned_get = uow.sessions.get_owned_for_update if current else uow.sessions.get_owned
                        snapshot_get = uow.sessions.get_latest_snapshot_for_update if current else uow.sessions.get_latest_snapshot
                        owned = await owned_get(reference.session_id, principal.player_id)
                        snapshot = await snapshot_get(reference.session_id)
                        bundle = self.revisit.registry.for_session(owned.session)
                        states.append(bundle.session_service._load_state(owned, snapshot.state_version, snapshot.state))
                        versions.append(owned.session.state_version)
                        events.append(await uow.run_world_revisits.source_events(reference.session_id, locking=True))
                    time = self.authority.clock()
                    evidence = completion_evidence(prefix=family, request=request, states=states, versions=versions,
                        event_sets=events, registry=self.revisit.registry, occurred_at=time)
                    completed = complete_revisited_native_run(family, evidence, occurred_at=time)
                    receipt = StoredRunSuccessReceipt(key=key, fingerprint=RunOperationFingerprint(value=request.fingerprint()),
                        command_kind=RunMutationKind.COMPLETE_REVISITED_NATIVE_RUN,
                        result=RunSafeResult(result_schema_version=COMPLETE_REVISITED_NATIVE_RUN_RESULT_SCHEMA_VERSION,
                            run_id=run.run_id, continuous_story_line_id=run.continuous_story_line_id,
                            lifecycle_status=completed.lifecycle_status, resulting_state_version=completed.state_version))
                    await uow.runs.append_revision(completed, created_at=time)
                    if not await uow.runs.compare_and_swap_current(completed, expected_state_version=5, updated_at=time):
                        raise RunCompletionError("RUN_COMPLETION_CONFLICT")
                    await uow.run_mutation_receipts.add(receipt, created_at=time, completion_evidence=evidence)
                    classified = await uow.run_protocol_bindings.get_classified_for_update(run_id=run.run_id)
                    if classified != NativeRunRegionalCompletedV1(revisited=family, canonical_run=completed, completion_evidence=evidence):
                        raise SnapshotInvalidError(session_id)
                    commit_issued = True
                    await uow.commit()
            return completion_result(classified)
        except BaseException as error:
            if commit_issued:
                from deviation_protocol.application.ports import NativeRunAdmissionOutcomeUnknownError
                if not isinstance(error, Exception):
                    error.commit_outcome_unknown = True
                    raise
                if not isinstance(error, NativeRunAdmissionOutcomeUnknownError):
                    raise NativeRunAdmissionOutcomeUnknownError("completion commit or cleanup outcome unknown") from error
            raise

    @staticmethod
    def _replay_family(family, receipt, request, session_id):
        if receipt.fingerprint.value != request.fingerprint():
            raise RunCompletionError("IDEMPOTENCY_CONFLICT")
        if type(family) is not NativeRunRegionalCompletedV1 or family.completion_evidence.request != request:
            raise SnapshotInvalidError(session_id)
        return family
