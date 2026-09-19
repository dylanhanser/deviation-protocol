"""Deterministic native rendering; S4/S5 retain all gameplay authority."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

from deviation_protocol.application.errors import SessionNotFoundError, SnapshotInvalidError
from deviation_protocol.application.narrative_models import NarrativeProposalRejectedError
from deviation_protocol.application.narrative_jobs import NarrativeJobStatus
from deviation_protocol.application.narrative_prompt import PromptBuilder, default_style_profile
from deviation_protocol.application.narrative_turn_orchestrator import DurableNarrativeTurnOrchestrator
from deviation_protocol.application.native_turn_mechanics import canonical
from deviation_protocol.application.run_protocol_prompt_context import CompiledRunProtocolContextV1
from deviation_protocol.infrastructure.demo_authority import CanonicalDemoProviderGuard, _CURRENT_AUTHORIZATION


@dataclass(slots=True)
class _NativeAllowance:
    authority_marker: object
    originating_task: object
    submission: object
    provider_call_consumed: bool = False
    request: object = None
    job: object = None


def build_native_demo_orchestrator(*, store, provider, **dependencies):
    """Keep the rendering capability and implementation in a private closure."""
    marker = object()
    locks = {}

    class Renderer:
        async def generate(self, request):
            allowance = _CURRENT_AUTHORIZATION.get()
            if (type(allowance) is not _NativeAllowance or allowance.authority_marker is not marker
                    or allowance.originating_task is not asyncio.current_task() or allowance.provider_call_consumed):
                raise NarrativeProposalRejectedError()
            allowance.provider_call_consumed = True
            if request is not allowance.request or allowance.job is None:
                raise NarrativeProposalRejectedError()
            job, submission = allowance.job, allowance.submission
            context = getattr(request, "_compiled_run_protocol_context", None)
            if type(context) is not CompiledRunProtocolContextV1:
                raise NarrativeProposalRejectedError()
            compiled = context.validated_object()
            visit = getattr(request,"_compiled_world_visit_context",None)
            if job.narrative_request.get("schema") in ("native-visit-turn-request/v1", "native-regional-turn-request/v1"):
                from deviation_protocol.application.world_visit_context import CompiledWorldVisitContextV1, CompiledRegionalVisitContextV1
                expected = CompiledRegionalVisitContextV1 if job.narrative_request["schema"] == "native-regional-turn-request/v1" else CompiledWorldVisitContextV1
                if type(visit) is not expected:
                    raise NarrativeProposalRejectedError()
                visit.validated_object()
            elif visit is not None:
                raise NarrativeProposalRejectedError()
            snapshot = store.snapshot()
            stored = snapshot.narrative_jobs.get(job.job_id)
            if (stored != job or job.status is not NarrativeJobStatus.IN_PROGRESS or job.attempt_count != 1
                    or (job.session_id, job.turn_id, job.client_request_id, job.action_signature) != (
                        submission.session_id, submission.turn_id, submission.client_request_id, submission.action_signature())
                    or store.active_uows or store.any_session_lock_held
                    or len(request.outcome_candidates) != 1 or len(request.outcome_candidates[0].allowed_results) != 1
                    or request.outcome_candidates[0].allowed_results[0].value != compiled["selected_result"]
                    or canonical(request.model_dump(mode="json")) != canonical(job.narrative_request["request"])
                    or compiled["selected_result"] != job.narrative_request["mechanics"]["selected_result"]):
                raise NarrativeProposalRejectedError()
            PromptBuilder(profiles=(default_style_profile(),)).build(request)
            return await provider.generate(request)

        async def aclose(self):
            return None  # Composition owns the shared renderer once.

    class NativeOrchestrator(DurableNarrativeTurnOrchestrator):
        async def handle(self, submission):
            CanonicalDemoProviderGuard._reject_active_authorization()
            async with locks.setdefault(submission.session_id, asyncio.Lock()):
                token = _CURRENT_AUTHORIZATION.set(_NativeAllowance(marker, asyncio.current_task(), submission))
                try:
                    return await super().handle(submission)
                finally:
                    _CURRENT_AUTHORIZATION.reset(token)

        async def _detach_request(self, job, submission):
            request = await super()._detach_request(job, submission)
            allowance = _CURRENT_AUTHORIZATION.get()
            if (type(allowance) is not _NativeAllowance or allowance.authority_marker is not marker
                    or allowance.originating_task is not asyncio.current_task() or allowance.provider_call_consumed
                    or allowance.job is not None):
                raise NarrativeProposalRejectedError()
            allowance.request, allowance.job = request, type(job).model_validate(job.model_dump(mode="python"))
            return request

    return NativeOrchestrator(narrative_provider=Renderer(), **dependencies)


class DemoNarrativeDispatcher:
    def __init__(self, *, legacy, native, session_service):
        self.__legacy, self.__native, self.__sessions = legacy, native, session_service
        self.native_coordinator = native.native_coordinator

    async def handle(self, submission):
        # This shared gate precedes UoW, locks, request/snapshot reads and delegates.
        CanonicalDemoProviderGuard._reject_active_authorization()
        async with self.__sessions.uow_factory() as uow:
            session = await uow.sessions.get(submission.session_id)
            if session is None:
                raise SessionNotFoundError(submission.session_id)
            snapshot = await uow.sessions.get_latest_snapshot(submission.session_id)
            if snapshot is None or snapshot.state_version != session.state_version:
                raise SnapshotInvalidError(submission.session_id)
            state = self.__native._load_state(snapshot.state, submission.session_id)
            definition = self.__native._scenario_definition(state, session.scenario_id, session.scenario_version, session.session_id)
            family = await self.native_coordinator.load(uow, session, state, definition)
        delegate = self.__native if family is not None else self.__legacy
        return await delegate.handle(submission)
