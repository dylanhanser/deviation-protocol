from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from deviation_protocol.api.dependencies import ApiServices
from deviation_protocol.application.narrative_models import (
    NarrativeProposalRejectedError,
    NarrativeProvider,
    NarrativeRequest,
    UntrustedNarrativeProposal,
)
from deviation_protocol.application.narrative_jobs import NarrativeJobStatus
from deviation_protocol.application.narrative_outcome_policy import (
    available_narrative_actions,
)
from deviation_protocol.application.narrative_turn_orchestrator import (
    DurableNarrativeTurnOrchestrator,
)
from deviation_protocol.application.resolution import ResolutionResult
from deviation_protocol.application.rule_resolver import DeterministicRuleResolver
from deviation_protocol.application.scenario_initialization import profession_tags_for
from deviation_protocol.application.session_service import SessionService
from deviation_protocol.domain.actions import ActionSubmission, ActionType
from deviation_protocol.domain.scenario import EndingStatus, ScenarioDefinition
from deviation_protocol.infrastructure.demo_generators import (
    DemoGenerators,
    new_demo_generators,
)
from deviation_protocol.infrastructure.demo_authority import (
    CanonicalDemoProviderGuard,
    DemoProviderCheckpoint,
    DeterministicDemoScenarioEventIssuer,
)
from deviation_protocol.infrastructure.demo_persistence import DemoProcessStore
from deviation_protocol.infrastructure.deterministic_narrative import (
    DeterministicDemoNarrativeProvider,
)
from deviation_protocol.infrastructure.scenario_loader import (
    JsonScenarioCatalogLoader,
)


SCENARIO_PACK = (
    Path(__file__).parents[3]
    / "config"
    / "scenarios"
    / "death_certificate_v1.json"
)


class _CanonicalDemoNarrativeProvider:
    """Public Provider view with no authorization or wrapped-Provider access."""

    __slots__ = ("__guard",)

    def __init__(self, guard: CanonicalDemoProviderGuard) -> None:
        self.__guard = guard

    async def generate(
        self, request: NarrativeRequest
    ) -> UntrustedNarrativeProposal:
        return await self.__guard.generate(request)

    async def aclose(self) -> None:
        await self.__guard.aclose()


@dataclass(frozen=True, slots=True)
class DemoRuntime:
    services: ApiServices
    store: DemoProcessStore
    generators: DemoGenerators
    provider: NarrativeProvider


@dataclass(slots=True)
class CanonicalDemoNarrativeTurnOrchestrator(DurableNarrativeTurnOrchestrator):
    _canonical_provider_guard: CanonicalDemoProviderGuard | None = field(
        default=None,
        repr=False,
    )
    _demo_authority_capability: object | None = field(
        default=None,
        repr=False,
    )

    async def handle(self, submission: ActionSubmission):
        guard = self._guard()
        guard._reject_active_authorization()
        async with guard.sequence_lock(submission.session_id):
            if not guard.governs(submission) or guard.has_committed_request(submission):
                return await super(
                    CanonicalDemoNarrativeTurnOrchestrator, self
                ).handle(submission)
            token = guard.authorize_submission(
                self._capability(),
                submission,
                checkpoint_factory=lambda: self._provider_checkpoint(
                    submission.session_id
                ),
            )
            try:
                return await super(
                    CanonicalDemoNarrativeTurnOrchestrator, self
                ).handle(submission)
            finally:
                guard.reset_authorization(token)

    async def _persist_state_change(
        self,
        *,
        uow: object,
        submission: ActionSubmission,
        game_session: object,
        resolution: ResolutionResult,
        definition: ScenarioDefinition | None,
        expected_version: int,
    ):
        candidate = resolution.updated_state
        runtime = candidate.scenario_runtime if candidate is not None else None
        if runtime is not None and runtime.ending_status is not EndingStatus.ACTIVE:
            self._guard().assert_complete(submission.session_id)
        result = await super(
            CanonicalDemoNarrativeTurnOrchestrator, self
        )._persist_state_change(
            uow=uow,
            submission=submission,
            game_session=game_session,
            resolution=resolution,
            definition=definition,
            expected_version=expected_version,
        )
        guard = self._guard()
        if guard.governs(submission):
            guard.stage_progress(self._capability(), uow, submission)
        return result

    def _provider_checkpoint(self, session_id: str) -> DemoProviderCheckpoint:
        store = self._guard().authority_snapshot()
        persisted = store.sessions.get(session_id)
        persisted_snapshot = store.snapshots.get(session_id)
        if persisted is None or persisted_snapshot is None:
            raise NarrativeProposalRejectedError()
        game_session = persisted.session
        if persisted_snapshot.state_version != game_session.state_version:
            raise NarrativeProposalRejectedError()
        state = self._load_state(persisted_snapshot.state, session_id)
        runtime = state.scenario_runtime
        if runtime is None:
            raise NarrativeProposalRejectedError()
        definition = self._scenario_definition(
            state,
            game_session.scenario_id,
            game_session.scenario_version,
            session_id,
        )
        character = self.catalog.character(state.player.character_definition_id)
        if definition is None or character is None:
            raise NarrativeProposalRejectedError()
        frame = self.story_director.plan_frame(
            state,
            definition,
            profession_tags=profession_tags_for(character.tags, definition),
        )
        public_action_types = {
            item.action_type
            for item in available_narrative_actions(
                state=state,
                definition=definition,
                frame=frame,
            )
        }
        if self.continue_policy.allows(state=state, frame=frame):
            public_action_types.add(ActionType.CONTINUE)

        events = tuple(
            event for event in store.events if event.session_id == session_id
        )
        turn_requests = tuple(
            value
            for (stored_session_id, _), value in store.turn_requests.items()
            if stored_session_id == session_id
        )
        try:
            resulting_state_versions = tuple(
                sorted(
                    int(value.response["resulting_state_version"])
                    for value in turn_requests
                    if value.response is not None
                )
            )
        except (KeyError, TypeError, ValueError):
            raise NarrativeProposalRejectedError() from None
        provider_jobs = tuple(
            sorted(
                (
                    job
                    for job in store.narrative_jobs.values()
                    if job.session_id == session_id
                    and job.status is NarrativeJobStatus.COMMITTED
                    and job.provider_name == "deterministic-demo"
                ),
                key=lambda item: item.prepared_state_version,
            )
        )
        return DemoProviderCheckpoint(
            state_version=game_session.state_version,
            turn_number=game_session.turn_number,
            session_phase=game_session.phase,
            scenario_id=game_session.scenario_id,
            scenario_version=game_session.scenario_version,
            character_definition_id=persisted.character_definition_id,
            snapshot_state_version=persisted_snapshot.state_version,
            snapshot_round_trips_exactly=(
                state.to_snapshot() == dict(persisted_snapshot.state)
            ),
            state_schema_version=state.schema_version,
            state_content_version=state.content_version,
            player_id=state.player.player_id,
            phase_id=runtime.current_phase_id,
            phase_beat_index=runtime.phase_beat_index,
            current_location_id=runtime.current_location_id,
            ending_status=runtime.ending_status.value,
            current_decision_id=runtime.current_decision_id,
            event_count=len(events),
            event_sequence_numbers=tuple(event.sequence_no for event in events),
            turn_request_count=len(turn_requests),
            resulting_state_versions=resulting_state_versions,
            narrative_job_count=sum(
                job.session_id == session_id
                for job in store.narrative_jobs.values()
            ),
            provider_job_prepared_versions=tuple(
                job.prepared_state_version for job in provider_jobs
            ),
            provider_job_statuses=tuple(job.status.value for job in provider_jobs),
            frame_scenario_id=frame.scenario_id,
            frame_phase_id=frame.phase_id,
            frame_location_id=frame.current_location_id,
            frame_decision_required=frame.decision_required,
            public_action_types=tuple(
                sorted(public_action_types, key=lambda item: item.value)
            ),
        )

    def _guard(self) -> CanonicalDemoProviderGuard:
        guard = self._canonical_provider_guard
        if guard is None:
            raise RuntimeError("Demo Provider guard is not configured")
        return guard

    def _capability(self) -> object:
        capability = self._demo_authority_capability
        if capability is None:
            raise RuntimeError("Demo Provider authority capability is not configured")
        return capability


def build_demo_runtime(
    *,
    store: DemoProcessStore | None = None,
    generators: DemoGenerators | None = None,
    provider: NarrativeProvider | None = None,
) -> DemoRuntime:
    """Build the explicit process-local Demo without DB or external Provider fallback."""

    runtime_store = store or DemoProcessStore()
    runtime_generators = generators or new_demo_generators()
    provider_delegate = provider or DeterministicDemoNarrativeProvider()
    authority_capability = object()
    runtime_guard = CanonicalDemoProviderGuard(
        provider_delegate,
        runtime_store,
        authority_capability=authority_capability,
    )
    runtime_provider = _CanonicalDemoNarrativeProvider(runtime_guard)
    scenario_catalog = JsonScenarioCatalogLoader(SCENARIO_PACK).load()
    catalog = scenario_catalog.content_catalog
    orchestrator = CanonicalDemoNarrativeTurnOrchestrator(
        resolver=DeterministicRuleResolver(),
        uow_factory=runtime_store.unit_of_work,
        catalog=catalog,
        scenario_catalog=scenario_catalog,
        narrative_provider=runtime_provider,
        provider_name="deterministic-demo",
        model_name="deterministic-demo-v1",
        scenario_event_issuer=DeterministicDemoScenarioEventIssuer(),
        clock=runtime_generators.clock,
        event_id_generator=runtime_generators.event_id,
        job_id_generator=runtime_generators.job_id,
        lease_token_generator=runtime_generators.lease_token,
        worker_id_generator=runtime_generators.worker_id,
        _canonical_provider_guard=runtime_guard,
        _demo_authority_capability=authority_capability,
    )
    services = ApiServices(
        session_service=SessionService(
            uow_factory=runtime_store.unit_of_work,
            catalog=catalog,
            scenario_catalog=scenario_catalog,
            clock=runtime_generators.clock,
            session_id_generator=runtime_generators.session_id,
            seed_generator=runtime_generators.seed,
            event_id_generator=runtime_generators.event_id,
        ),
        turn_orchestrator=orchestrator,
        engine=None,
        narrative_provider=runtime_provider,
    )
    return DemoRuntime(
        services=services,
        store=runtime_store,
        generators=runtime_generators,
        provider=runtime_provider,
    )
