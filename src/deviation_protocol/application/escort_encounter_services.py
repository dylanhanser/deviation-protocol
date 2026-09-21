"""Composition for the standalone local-template Session (SQL and Demo alike)."""
from __future__ import annotations

from dataclasses import dataclass, field, replace

from deviation_protocol.application.escort_encounter import CONTENT_IDENTITY, CONTENT_SHA256, FACT, EscortEncounterPolicy
from deviation_protocol.application.errors import SnapshotInvalidError
from deviation_protocol.application.narrative_turn_orchestrator import DurableNarrativeTurnOrchestrator
from deviation_protocol.application.resolution import ResolutionStatus
from deviation_protocol.application.rule_resolver import DeterministicRuleResolver
from deviation_protocol.application.session_content_registry import SessionContentBundle
from deviation_protocol.application.session_service import SessionService
from deviation_protocol.application.turn_orchestrator import FirstPhaseTurnOrchestrator
from deviation_protocol.domain.actions import ActionType
from deviation_protocol.domain.events import DomainEventDraft


@dataclass(slots=True)
class EscortTurnOrchestrator(DurableNarrativeTurnOrchestrator):
    encounter_policy: EscortEncounterPolicy = field(default_factory=EscortEncounterPolicy)

    async def handle(self, submission):
        # Reuse the locked local pipeline and its local-template commit helper.
        # Never enter durable Provider prepare/claim/generate/finalize machinery.
        return await FirstPhaseTurnOrchestrator.handle(self, submission)

    async def _handle_once(self, submission):
        return await FirstPhaseTurnOrchestrator._handle_once(self, submission)

    def _load_state(self, payload, session_id):
        state = FirstPhaseTurnOrchestrator._load_state(self, payload, session_id)
        self.encounter_policy.validate(state, session_id, self.scenario_catalog.scenarios[0])
        return state

    def _coordinate_scenario(self, submission, state, resolution, definition, **kwargs):
        self.encounter_policy.validate(state, submission.session_id, definition)
        if kwargs["state_version"] != len(state.scenario_runtime.decisions_made):
            raise SnapshotInvalidError(submission.session_id)
        if submission.action_type is not ActionType.CHOOSE:
            return self._scenario_rejection("DECISION_RESPONSE_REQUIRED"), None
        result, frame = FirstPhaseTurnOrchestrator._coordinate_scenario(
            self, submission, state, resolution, definition, **kwargs)
        if result.state_changed:
            self.encounter_policy.validate(result.updated_state, submission.session_id, definition)
            if result.updated_state.player != state.player or result.updated_state.npcs != state.npcs:
                raise SnapshotInvalidError(submission.session_id)
            result = replace(result, events=(*result.events, DomainEventDraft(
                "EscortTransitionRecorded", {
                    "player_id": state.player.player_id,
                    "companion_id": self.encounter_policy.companion_id(submission.session_id),
                    "from_state": state.scenario_runtime.mutable_fact_values[FACT],
                    "to_state": result.updated_state.scenario_runtime.mutable_fact_values[FACT],
                    "accepted_step": kwargs["state_version"] + 1,
                })))
        return result, frame

    async def _commit_local_result(self, uow, submission, game_session, original_state, resolution, frame, definition):
        if resolution.status is ResolutionStatus.REJECTED_LOCAL:
            # A refused choice establishes no persisted response authority.
            return self._build_response(submission, resolution, game_session.state_version, frame)
        return await DurableNarrativeTurnOrchestrator._commit_local_result(
            self, uow, submission, game_session, original_state, resolution, frame, definition)


def build_escort_bundle(path, *, uow_factory, generators=None):
    payload = path.read_bytes()
    raw = SessionContentBundle.from_bytes(payload)
    if (raw.scenario_id, raw.content_version) != CONTENT_IDENTITY or raw.content_sha256 != CONTENT_SHA256:
        raise ValueError("standalone encounter content identity mismatch")
    policy = EscortEncounterPolicy()
    options = {} if generators is None else dict(
        clock=generators.clock, event_id_generator=generators.event_id)
    service = SessionService(
        uow_factory=uow_factory, catalog=raw.scenario_catalog.content_catalog,
        scenario_catalog=raw.scenario_catalog, encounter_policy=policy, **options,
        **({} if generators is None else dict(session_id_generator=generators.session_id, seed_generator=generators.seed)))
    orchestrator = EscortTurnOrchestrator(
        resolver=DeterministicRuleResolver(), uow_factory=uow_factory,
        catalog=service.catalog, scenario_catalog=service.scenario_catalog,
        encounter_policy=policy, narrative_provider=None, **options,
        **({} if generators is None else dict(job_id_generator=generators.job_id)))
    return SessionContentBundle.from_bytes(payload, session_service=service,
        turn_orchestrator=orchestrator, standalone=True)
