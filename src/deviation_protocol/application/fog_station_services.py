"""Shared SQL/Demo native composition for authored, Provider-free station play."""
from dataclasses import dataclass, replace

from deviation_protocol.application.errors import SnapshotInvalidError
from deviation_protocol.application.fog_station import CONTENT_IDENTITY, CONTENT_SHA256, FogStationPolicy
from deviation_protocol.application.narrative_turn_orchestrator import DurableNarrativeTurnOrchestrator
from deviation_protocol.application.native_turn_mechanics import NativeTurnMechanicsCoordinator
from deviation_protocol.application.resolution import ResolutionStatus
from deviation_protocol.application.rule_resolver import DeterministicRuleResolver
from deviation_protocol.application.session_content_registry import SessionContentBundle
from deviation_protocol.application.session_service import SessionService
from deviation_protocol.application.turn_orchestrator import FirstPhaseTurnOrchestrator
from deviation_protocol.domain.actions import ActionType


@dataclass(slots=True)
class FogStationTurnOrchestrator(DurableNarrativeTurnOrchestrator):
    async def handle(self, submission):
        return await FirstPhaseTurnOrchestrator.handle(self, submission)

    async def _handle_once(self, submission):
        return await FirstPhaseTurnOrchestrator._handle_once(self, submission)

    def _load_state(self, payload, session_id):
        state = FirstPhaseTurnOrchestrator._load_state(self, payload, session_id)
        FogStationPolicy().validate(state, session_id, self.scenario_catalog.scenarios[0])
        return state

    def _coordinate_scenario(self, submission, state, resolution, definition, **kwargs):
        policy = FogStationPolicy()
        codes = policy.validate(state, submission.session_id, definition)
        if kwargs["native_family"] is None or kwargs["state_version"] != len(codes):
            raise SnapshotInvalidError(submission.session_id)
        if submission.action_type is not ActionType.CHOOSE:
            return self._scenario_rejection("DECISION_RESPONSE_REQUIRED"), None
        result, frame = FirstPhaseTurnOrchestrator._coordinate_scenario(
            self, submission, state, resolution, definition, **kwargs)
        if result.state_changed:
            new_codes = policy.validate(result.updated_state, submission.session_id, definition)
            if (result.updated_state.player != state.player or result.updated_state.npcs != state.npcs
                    or len(new_codes) != len(codes) + 1):
                raise SnapshotInvalidError(submission.session_id)
            if new_codes[-1] == "farewell":
                from deviation_protocol.application.resolution import PlayerFeedback
                projected = policy.project(result.updated_state, submission.session_id, definition)
                activities = "、".join(projected.activities_used)
                text = result.feedback.parameters["_server_narrative_text"]
                text += ("他还提起暂住时的" + activities + "。") if activities else "你们这次没有进行暂住活动，他没有编造更多共同经历。"
                text += "岑舟回站值守，你继续行程。没有新增承诺或奖励，也不再开放入住。"
                result = replace(result, feedback=PlayerFeedback(result.feedback.code,
                    {**result.feedback.parameters, "_server_narrative_text": text}))
        return result, frame

    async def _commit_local_result(self, uow, submission, game_session, original_state, resolution, frame, definition):
        if resolution.status is ResolutionStatus.REJECTED_LOCAL:
            return self._build_response(submission, resolution, game_session.state_version, frame)
        return await DurableNarrativeTurnOrchestrator._commit_local_result(
            self, uow, submission, game_session, original_state, resolution, frame, definition)


def build_fog_station_bundle(path, *, uow_factory, controller_resolver, generators=None):
    payload = path.read_bytes()
    raw = SessionContentBundle.from_bytes(payload)
    if (raw.scenario_id, raw.content_version) != CONTENT_IDENTITY or raw.content_sha256 != CONTENT_SHA256:
        raise ValueError("station content identity mismatch")
    common = {} if generators is None else dict(clock=generators.clock, event_id_generator=generators.event_id)
    coordinator = NativeTurnMechanicsCoordinator(raw.scenario_catalog.content_catalog, raw.scenario_catalog)
    service = SessionService(uow_factory=uow_factory, catalog=coordinator.catalog,
        scenario_catalog=coordinator.scenario_catalog, native_view_coordinator=coordinator,
        native_controller_resolver=controller_resolver, relationship_policy=FogStationPolicy(), **common,
        **({} if generators is None else dict(session_id_generator=generators.session_id, seed_generator=generators.seed)))
    orchestrator = FogStationTurnOrchestrator(resolver=DeterministicRuleResolver(), uow_factory=uow_factory,
        catalog=service.catalog, scenario_catalog=service.scenario_catalog, native_coordinator=coordinator,
        narrative_provider=None, **common,
        **({} if generators is None else dict(job_id_generator=generators.job_id)))
    return SessionContentBundle.from_bytes(payload, session_service=service, turn_orchestrator=orchestrator)
