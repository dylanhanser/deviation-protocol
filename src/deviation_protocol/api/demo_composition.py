from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
import hashlib
import os
from pathlib import Path
from typing import Any, Mapping

from deviation_protocol.api.dependencies import ApiServices
from deviation_protocol.api.main import build_run_entry_service
from deviation_protocol.application.dynamic_narrative_models import (
    DynamicNarrativeCandidatePayload,
    DynamicNarrativeProvider,
    DynamicNextScene,
    DynamicPublicFactProposal,
    NarrativeProviderMetadata,
    UntrustedDynamicNarrativeCandidate,
    canonical_json,
)
from deviation_protocol.application.dynamic_narrative_orchestrator import (
    DynamicNarrativeOrchestrator,
    DynamicSessionService,
)
from deviation_protocol.application.narrative_models import (
    NarrativeProposalRejectedError,
    NarrativeProvider,
    NarrativeProviderUnavailableError,
    NarrativeRequest,
    UntrustedNarrativeProposal,
)
from deviation_protocol.application.narrative_jobs import NarrativeJobStatus
from deviation_protocol.application.narrative_prompt import (
    PromptBuilder,
    default_style_profile,
)
from deviation_protocol.application.narrative_outcome_policy import (
    available_narrative_actions,
)
from deviation_protocol.application.narrative_turn_orchestrator import (
    DurableNarrativeTurnOrchestrator,
)
from deviation_protocol.application.player_character_service import (
    PlayerCharacterService,
)
from deviation_protocol.application.resolution import ResolutionResult
from deviation_protocol.application.rule_resolver import DeterministicRuleResolver
from deviation_protocol.application.run_service import RunService
from deviation_protocol.application.scenario_initialization import profession_tags_for
from deviation_protocol.application.session_service import SessionService
from deviation_protocol.domain.actions import ActionSubmission, ActionType
from deviation_protocol.domain.player_character import (
    AuthoritySourceRef,
    PlayerCharacterId,
)
from deviation_protocol.domain.player_character_policies import (
    CreatePlayerCharacterPolicy,
)
from deviation_protocol.domain.run import (
    ContinuousStoryLineId,
    RunAuthoritySourceRef,
    RunId,
)
from deviation_protocol.domain.scenario import EndingStatus, ScenarioDefinition
from deviation_protocol.domain.narrative_outcome import NarrativeOutcomeResult
from deviation_protocol.infrastructure.deepseek_narrative import (
    DeepSeekNarrativeProvider,
    DeepSeekSettings,
)
from deviation_protocol.infrastructure.demo_authority import (
    CanonicalDemoProviderGuard,
    DemoProviderCheckpoint,
    DeterministicDemoScenarioEventIssuer,
)
from deviation_protocol.infrastructure.demo_generators import (
    DemoGenerators,
    new_demo_generators,
)
from deviation_protocol.infrastructure.demo_persistence import DemoProcessStore
from deviation_protocol.infrastructure.deterministic_narrative import (
    DeterministicDemoNarrativeProvider,
)
from deviation_protocol.infrastructure.player_character_authority import (
    ConfiguredControllerBinding,
    ConfiguredControllerBindingResolver,
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


class _DemoPlayerCharacterIdIssuer:
    __slots__ = ("_generator",)

    def __init__(self, generator: Callable[[], str]) -> None:
        self._generator = generator

    def issue(self) -> PlayerCharacterId:
        return PlayerCharacterId(value=self._generator())


class _DemoRunIdIssuer:
    __slots__ = ("_generator",)

    def __init__(self, generator: Callable[[], str]) -> None:
        self._generator = generator

    def issue(self) -> RunId:
        return RunId(value=self._generator())


class _DemoContinuousStoryLineIdIssuer:
    __slots__ = ("_generator",)

    def __init__(self, generator: Callable[[], str]) -> None:
        self._generator = generator

    def issue(self) -> ContinuousStoryLineId:
        return ContinuousStoryLineId(value=self._generator())


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
    provider: Any
    _owned_resources: tuple[Any, ...] = field(default=(), repr=False, compare=False)
    _close_lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False, compare=False)
    _close_task: asyncio.Task[None] | None = field(default=None, repr=False, compare=False)

    async def aclose(self) -> None:
        async with self._close_lock:
            task = self._close_task
            if task is None:
                task = asyncio.create_task(self._close_owned_resources())
                object.__setattr__(self, "_close_task", task)
        owner = asyncio.current_task()
        if owner is None:
            raise RuntimeError("Demo shutdown requires an owner task")
        baseline = owner.cancelling()
        cancellation_requested = baseline > 0

        def balance() -> None:
            nonlocal cancellation_requested
            current = owner.cancelling()
            if current < baseline:
                raise RuntimeError("Demo shutdown cancellation crossed its baseline")
            excess = current - baseline
            if excess:
                cancellation_requested = True
            for _ in range(excess):
                if owner.uncancel() < baseline:
                    raise RuntimeError("Demo shutdown cancellation crossed its baseline")

        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                cancellation_requested = True
            finally:
                balance()
        balance()
        task.result()
        if cancellation_requested:
            raise asyncio.CancelledError

    async def _close_owned_resources(self) -> None:
        failed = False
        for resource in reversed(self._owned_resources):
            try:
                await resource.aclose()
            except BaseException:
                failed = True
        if failed:
            raise DynamicDemoShutdownError() from None


class DynamicDemoConfigurationError(RuntimeError):
    code = "DYNAMIC_DEMO_CONFIGURATION_INVALID"

    def __init__(self) -> None:
        super().__init__(self.code)


class DynamicDemoShutdownError(RuntimeError):
    code = "DYNAMIC_DEMO_SHUTDOWN_FAILED"

    def __init__(self) -> None:
        super().__init__(self.code)


class _DynamicFakeProvider:
    __slots__ = ("_failure_at", "_invocations", "_closed")

    def __init__(self, failure_at: int | None = None) -> None:
        if failure_at is not None and not 1 <= failure_at <= 10:
            raise DynamicDemoConfigurationError()
        self._failure_at = failure_at
        self._invocations = 0
        self._closed = False
        if failure_at is not None:
            print(
                "DNVS_FAKE_EVIDENCE event=reset cumulative_invocations=0",
                flush=True,
            )

    @property
    def invocation_count(self) -> int:
        return self._invocations

    async def generate_dynamic(self, request):
        if self._closed:
            raise NarrativeProviderUnavailableError()
        self._invocations += 1
        ordinal = self._invocations
        intentional_failure = ordinal == self._failure_at
        if self._failure_at is not None:
            outcome = "INTENTIONAL_FAILURE" if intentional_failure else "SUCCESS"
            print(
                "DNVS_FAKE_EVIDENCE "
                f"event=invocation ordinal={ordinal} outcome={outcome} "
                f"cumulative_invocations={ordinal}",
                flush=True,
            )
        if intentional_failure:
            raise NarrativeProviderUnavailableError()
        request_bytes = canonical_json(request.model_dump(mode="json")).encode("utf-8")
        request_digest = hashlib.sha256(request_bytes).hexdigest()
        stable_number = int(request_digest[:12], 16)
        stable_label = request_digest[:12]
        result_schedule = (
            NarrativeOutcomeResult.SUCCESS,
            NarrativeOutcomeResult.AMBIGUOUS,
            NarrativeOutcomeResult.FAILURE,
            NarrativeOutcomeResult.NO_EFFECT,
        )
        result = result_schedule[stable_number % len(result_schedule)]
        stem = (
            "你看见琥珀微光轻颤，静候尘埃缓缓落下。"
        )
        narrative = (stem * 8)[: max(350, min(650, request.narrative_length.target))]
        if len(narrative) < request.narrative_length.minimum:
            narrative += "琥珀微光轻颤。" * 50
            narrative = narrative[: request.narrative_length.minimum]
        anchor_key = "manual.continuity.anchor"
        anchor_value = "A visible amber marker appears beside the sealed doorway."
        has_anchor = any(
            fact.key == anchor_key and fact.value == anchor_value
            for fact in request.canonical_facts
        )
        if not has_anchor:
            narrative = (anchor_value + narrative)[: request.narrative_length.maximum]
            proposed_public_facts = (
                DynamicPublicFactProposal(key=anchor_key, value=anchor_value),
            )
            next_scene = DynamicNextScene(
                title=f"Dynamic scene {stable_label}",
                summary=f"The sequence continues at marker {stable_label}.",
            )
        else:
            proposed_public_facts = (
                DynamicPublicFactProposal(
                    key=f"note.{stable_label}",
                    value=f"Visible change {stable_label}.",
                ),
            )
            next_scene = DynamicNextScene(
                title=f"Dynamic scene {stable_label}",
                summary="The visible amber marker established earlier now identifies the route forward.",
            )
        suggestions = (
            f"Consider possibility alpha ({stable_label}).",
            f"Consider possibility beta ({stable_label}).",
            f"Consider possibility gamma ({stable_label}).",
        )
        return UntrustedDynamicNarrativeCandidate(
            candidate=DynamicNarrativeCandidatePayload(
                schema_version="dynamic-narrative-candidate-v1",
                narrative_text=narrative,
                result=result,
                proposed_consequences=("The atmosphere shifts.",),
                proposed_public_facts=proposed_public_facts,
                next_scene=next_scene,
                suggested_actions=suggestions,
                continuation="TERMINAL" if stable_number % 2 == 0 else "CONTINUE",
            ),
            provider_metadata=NarrativeProviderMetadata(
                provider="dynamic-fake",
                model="dynamic-fake-v1",
                finish_reason="stop",
                attempts=1,
                latency_ms=0,
            ),
        )

    async def aclose(self) -> None:
        self._closed = True


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
    controller_binding_resolver = ConfiguredControllerBindingResolver(
        (
            ConfiguredControllerBinding(
                authentication_scheme="demo-dev-only",
                player_id="demo-player",
                controller_id="binding.demo-player",
            ),
        )
    )
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
    session_service = SessionService(
        uow_factory=runtime_store.unit_of_work,
        catalog=catalog,
        scenario_catalog=scenario_catalog,
        clock=runtime_generators.clock,
        session_id_generator=runtime_generators.session_id,
        seed_generator=runtime_generators.seed,
        event_id_generator=runtime_generators.event_id,
    )
    player_character_service = PlayerCharacterService(
        uow_factory=runtime_store.unit_of_work,
        controller_binding_resolver=controller_binding_resolver,
        player_character_id_issuer=_DemoPlayerCharacterIdIssuer(
            runtime_generators.player_character_id
        ),
        create_policy=CreatePlayerCharacterPolicy(),
        source_reference=AuthoritySourceRef(
            value="source.demo-player-character"
        ),
        clock=runtime_generators.clock,
        binding_integrity_guard_enabled=True,
    )
    run_service = RunService(
        uow_factory=runtime_store.unit_of_work,
        run_id_issuer=_DemoRunIdIssuer(runtime_generators.run_id),
        continuous_story_line_id_issuer=(
            _DemoContinuousStoryLineIdIssuer(
                runtime_generators.continuous_story_line_id
            )
        ),
        source_reference=RunAuthoritySourceRef(value="source.demo-run"),
        clock=runtime_generators.clock,
        controller_binding_resolver=controller_binding_resolver,
        player_character_binding_evidence=player_character_service,
    )
    services = ApiServices(
        session_service=session_service,
        turn_orchestrator=orchestrator,
        player_character_service=player_character_service,
        run_service=run_service,
        run_entry_service=build_run_entry_service(
            run_service=run_service,
            session_service=session_service,
        ),
        engine=None,
        narrative_provider=runtime_provider,
    )
    return DemoRuntime(
        services=services,
        store=runtime_store,
        generators=runtime_generators,
        provider=runtime_provider,
        _owned_resources=(runtime_provider,),
    )


def build_dynamic_demo_runtime(
    *,
    store: DemoProcessStore | None = None,
    generators: DemoGenerators | None = None,
    provider: DynamicNarrativeProvider | None = None,
    own_injected_provider: bool = False,
    environ: Mapping[str, str] | None = None,
) -> DemoRuntime:
    """Build the one process-lifetime, director-free Dynamic Narrative Demo."""

    source = os.environ if environ is None else environ
    selector = source.get("DEVIATION_DEMO_DYNAMIC_PROVIDER", "fake")
    if selector not in {"fake", "live"}:
        raise DynamicDemoConfigurationError()
    if own_injected_provider and provider is None:
        raise DynamicDemoConfigurationError()
    if provider is not None and selector == "live":
        raise DynamicDemoConfigurationError()
    failure_text = source.get("DEVIATION_DEMO_DYNAMIC_FAKE_FAILURE_AT_ACTION")
    if failure_text is not None and (selector != "fake" or provider is not None):
        raise DynamicDemoConfigurationError()
    failure_at: int | None = None
    if failure_text is not None:
        try:
            failure_at = int(failure_text)
        except ValueError:
            raise DynamicDemoConfigurationError() from None
        if not 1 <= failure_at <= 10:
            raise DynamicDemoConfigurationError()

    runtime_store = store or DemoProcessStore()
    runtime_generators = generators or new_demo_generators()
    scenario_catalog = JsonScenarioCatalogLoader(SCENARIO_PACK).load()
    catalog = scenario_catalog.content_catalog
    controller_binding_resolver = ConfiguredControllerBindingResolver(
        (
            ConfiguredControllerBinding(
                authentication_scheme="demo-dev-only",
                player_id="demo-player",
                controller_id="binding.demo-player",
            ),
        )
    )
    player_character_service = PlayerCharacterService(
        uow_factory=runtime_store.unit_of_work,
        controller_binding_resolver=controller_binding_resolver,
        player_character_id_issuer=_DemoPlayerCharacterIdIssuer(
            runtime_generators.player_character_id
        ),
        create_policy=CreatePlayerCharacterPolicy(),
        source_reference=AuthoritySourceRef(value="source.demo-player-character"),
        clock=runtime_generators.clock,
        binding_integrity_guard_enabled=True,
    )
    run_service = RunService(
        uow_factory=runtime_store.unit_of_work,
        run_id_issuer=_DemoRunIdIssuer(runtime_generators.run_id),
        continuous_story_line_id_issuer=_DemoContinuousStoryLineIdIssuer(
            runtime_generators.continuous_story_line_id
        ),
        source_reference=RunAuthoritySourceRef(value="source.demo-run"),
        clock=runtime_generators.clock,
        controller_binding_resolver=controller_binding_resolver,
        player_character_binding_evidence=player_character_service,
    )
    session_service = DynamicSessionService(
        uow_factory=runtime_store.unit_of_work,
        catalog=catalog,
        scenario_catalog=scenario_catalog,
        clock=runtime_generators.clock,
        session_id_generator=runtime_generators.session_id,
        seed_generator=runtime_generators.seed,
        event_id_generator=runtime_generators.event_id,
    )

    owned = False
    selected_provider: DynamicNarrativeProvider
    provider_name: str
    model_name: str
    live_provider_references: tuple[str, ...] = ()
    if provider is not None:
        selected_provider = provider
        owned = own_injected_provider
        provider_name = "dynamic-injected"
        model_name = "dynamic-injected-v1"
    elif selector == "fake":
        selected_provider = _DynamicFakeProvider(failure_at)
        owned = True
        provider_name = "dynamic-fake"
        model_name = "dynamic-fake-v1"
    else:
        if failure_text is not None:
            raise DynamicDemoConfigurationError()
        try:
            settings = DeepSeekSettings.from_environment(source)
        except (TypeError, ValueError):
            raise DynamicDemoConfigurationError() from None
        if settings.max_retries != 0:
            raise DynamicDemoConfigurationError()
        selected_provider = DeepSeekNarrativeProvider(
            settings,
            PromptBuilder(profiles=(default_style_profile(),)),
        )
        owned = True
        provider_name = "deepseek"
        model_name = settings.model
        live_provider_references = (settings.base_url, settings.model)

    orchestrator = DynamicNarrativeOrchestrator(
        resolver=DeterministicRuleResolver(),
        uow_factory=runtime_store.unit_of_work,
        catalog=catalog,
        scenario_catalog=scenario_catalog,
        provider=selected_provider,
        dynamic_session_service=session_service,
        provider_name=provider_name,
        model_name=model_name,
        live_provider_references=live_provider_references,
        publication_event_reader=lambda session_id, sequence_no: tuple(
            event
            for event in runtime_store.snapshot().events
            if event.session_id == session_id and event.sequence_no == sequence_no
        ),
        clock=runtime_generators.clock,
        event_id_generator=runtime_generators.event_id,
        job_id_generator=runtime_generators.job_id,
        lease_token_generator=runtime_generators.lease_token,
        worker_id_generator=runtime_generators.worker_id,
    )
    session_service.narrative_terminal_uncertainty_probe = (
        orchestrator.request_is_terminal_uncertain
    )
    services = ApiServices(
        session_service=session_service,
        turn_orchestrator=orchestrator,
        player_character_service=player_character_service,
        run_service=run_service,
        run_entry_service=build_run_entry_service(
            run_service=run_service,
            session_service=session_service,
        ),
        engine=None,
        narrative_provider=selected_provider,  # type: ignore[arg-type]
    )
    return DemoRuntime(
        services=services,
        store=runtime_store,
        generators=runtime_generators,
        provider=selected_provider,
        _owned_resources=(selected_provider,) if owned else (),
    )
