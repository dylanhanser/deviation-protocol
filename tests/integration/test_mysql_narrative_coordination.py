from __future__ import annotations

from datetime import datetime, timedelta, timezone
import asyncio
import json
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.errors import (
    IdempotencyConflictError,
    NarrativeJobActiveError,
    NarrativeJobStaleError,
    NarrativeOutcomeUnknownError,
)
from deviation_protocol.application.narrative_jobs import NarrativeJob
from deviation_protocol.application.narrative_models import (
    NarrativeProposalPayload,
    NarrativeProposalRejectedError,
    NarrativeProviderMetadata,
    NarrativeRequest,
    NpcUtterance,
    SelectedNarrativeOutcome,
    UntrustedNarrativeProposal,
)
from deviation_protocol.application.narrative_turn_orchestrator import (
    DurableNarrativeTurnOrchestrator,
)
from deviation_protocol.application.resolution import ResolutionStatus
from deviation_protocol.application.rule_resolver import DeterministicRuleResolver
from deviation_protocol.application.session_service import SessionService
from deviation_protocol.domain.actions import ActionSubmission, ActionType
from deviation_protocol.domain.narrative_outcome import NarrativeOutcomeResult
from deviation_protocol.infrastructure.orm_models import (
    DomainEventRow,
    GameSessionRow,
    GameSnapshotRow,
    NarrativeJobRow,
    TurnRequestRow,
)
from deviation_protocol.infrastructure.scenario_loader import JsonScenarioCatalogLoader
from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from deviation_protocol.application.turn_orchestrator import FirstPhaseTurnOrchestrator


SCENARIO_PACK = Path(__file__).parents[2] / "config" / "scenarios" / "death_certificate_v1.json"
NOW = datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc)


class LockCheckingProvider:
    def __init__(
        self,
        factory: async_sessionmaker[AsyncSession],
        session_id: str,
        active_uows: list[int] | None = None,
    ) -> None:
        self.factory = factory
        self.session_id = session_id
        self.active_uows = active_uows
        self.calls = 0

    async def generate(self, request: NarrativeRequest) -> UntrustedNarrativeProposal:
        self.calls += 1
        if self.active_uows is not None:
            assert self.active_uows == [0]
        # Acquiring the same session row proves Phase A committed and released its
        # SELECT FOR UPDATE before this external boundary was entered.
        async with self.factory.begin() as database:
            row = await database.scalar(
                select(GameSessionRow)
                .where(GameSessionRow.session_id == self.session_id)
                .with_for_update()
            )
            assert row is not None
        candidate = request.outcome_candidates[0]
        speaker = candidate.allowed_entity_ids[0]
        text = "你用仍能控制的手指重复敲出节奏。监护设备上的变化被护士注意到，她停下原本的处置并重新核对你的反应。" * 8
        return UntrustedNarrativeProposal(
            proposal=NarrativeProposalPayload(
                schema_version="narrative-proposal-v1",
                narrative_text=text,
                referenced_entity_ids=(speaker,),
                npc_utterances=(
                    NpcUtterance(
                        speaker_entity_id=speaker,
                        text="我看到你的反应了，你有意识。",
                    ),
                ),
                selected_outcome=SelectedNarrativeOutcome(
                    outcome_token=candidate.outcome_token,
                    result=NarrativeOutcomeResult.SUCCESS,
                    referenced_entity_ids=(speaker,),
                ),
                continuity_notes=("仅供候选校验的非权威连续性备注",),
            ),
            provider_metadata=NarrativeProviderMetadata(
                provider="fake",
                model="fake-model",
                finish_reason="stop",
                attempts=1,
                latency_ms=1,
            ),
        )

    async def aclose(self) -> None:
        return None


class TrackingUnitOfWork(SqlAlchemyUnitOfWork):
    def __init__(
        self,
        factory: async_sessionmaker[AsyncSession],
        active_uows: list[int],
    ) -> None:
        super().__init__(factory)
        self.active_uows = active_uows

    async def __aenter__(self) -> "TrackingUnitOfWork":
        await super().__aenter__()
        self.active_uows[0] += 1
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        try:
            await super().__aexit__(exc_type, exc, traceback)
        finally:
            self.active_uows[0] -= 1


class BlockingProvider(LockCheckingProvider):
    def __init__(self, factory: async_sessionmaker[AsyncSession], session_id: str) -> None:
        super().__init__(factory, session_id)
        self.entered = asyncio.Event()
        self.release = asyncio.Event()

    async def generate(self, request: NarrativeRequest) -> UntrustedNarrativeProposal:
        self.entered.set()
        await self.release.wait()
        return await super().generate(request)


class ParallelProvider:
    def __init__(self) -> None:
        self.calls = 0
        self.both_entered = asyncio.Event()
        self.release = asyncio.Event()

    async def generate(self, request: NarrativeRequest) -> UntrustedNarrativeProposal:
        self.calls += 1
        if self.calls == 2:
            self.both_entered.set()
        await self.release.wait()
        candidate = request.outcome_candidates[0]
        speaker = candidate.allowed_entity_ids[0]
        return UntrustedNarrativeProposal(
            proposal=NarrativeProposalPayload(
                schema_version="narrative-proposal-v1",
                narrative_text=("你用仍能控制的手指重复敲出节奏，设备变化被护士注意到。" * 15),
                referenced_entity_ids=(speaker,),
                npc_utterances=(
                    NpcUtterance(
                        speaker_entity_id=speaker,
                        text="我看到了，你有意识。",
                    ),
                ),
                selected_outcome=SelectedNarrativeOutcome(
                    outcome_token=candidate.outcome_token,
                    result=NarrativeOutcomeResult.SUCCESS,
                    referenced_entity_ids=(speaker,),
                ),
            ),
            provider_metadata=NarrativeProviderMetadata(
                provider="fake",
                model="fake-model",
                finish_reason="stop",
                attempts=1,
                latency_ms=1,
            ),
        )

    async def aclose(self) -> None:
        return None


class LeaseExpiringProvider(LockCheckingProvider):
    def __init__(
        self,
        factory: async_sessionmaker[AsyncSession],
        session_id: str,
        clock_value: list[datetime],
    ) -> None:
        super().__init__(factory, session_id)
        self.clock_value = clock_value

    async def generate(self, request: NarrativeRequest) -> UntrustedNarrativeProposal:
        proposal = await super().generate(request)
        self.clock_value[0] += timedelta(minutes=3)
        return proposal


class FailNthCommitUnitOfWork(SqlAlchemyUnitOfWork):
    def __init__(
        self,
        factory: async_sessionmaker[AsyncSession],
        commit_count: list[int],
        fail_at: int,
    ) -> None:
        super().__init__(factory)
        self.commit_count = commit_count
        self.fail_at = fail_at

    async def commit(self) -> None:
        self.commit_count[0] += 1
        if self.commit_count[0] == self.fail_at:
            raise RuntimeError("simulated narrative finalize commit failure")
        await super().commit()


class DisconnectAfterFinalizeOrchestrator(DurableNarrativeTurnOrchestrator):
    disconnect_once: bool = True

    async def _finalize(
        self, job: NarrativeJob, submission: ActionSubmission
    ):
        response = await super()._finalize(job, submission)
        if self.disconnect_once:
            self.disconnect_once = False
            raise asyncio.CancelledError
        return response


class ContradictoryFailureProvider(LockCheckingProvider):
    async def generate(self, request: NarrativeRequest) -> UntrustedNarrativeProposal:
        self.calls += 1
        candidate = request.outcome_candidates[0]
        speaker = candidate.allowed_entity_ids[0]
        return UntrustedNarrativeProposal(
            proposal=NarrativeProposalPayload(
                schema_version="narrative-proposal-v1",
                narrative_text="分诊协调员确认你还活着，并宣布这次生命信号成功。" * 20,
                referenced_entity_ids=(speaker,),
                npc_utterances=(
                    NpcUtterance(
                        speaker_entity_id=speaker,
                        text="我确认你还活着。",
                    ),
                ),
                selected_outcome=SelectedNarrativeOutcome(
                    outcome_token=candidate.outcome_token,
                    result=NarrativeOutcomeResult.FAILURE,
                    referenced_entity_ids=(speaker,),
                ),
            ),
            provider_metadata=NarrativeProviderMetadata(
                provider="fake",
                model="fake-model",
                finish_reason="stop",
                attempts=1,
                latency_ms=1,
            ),
        )


class CancelledProvider(LockCheckingProvider):
    async def generate(self, request: NarrativeRequest) -> UntrustedNarrativeProposal:
        self.calls += 1
        raise asyncio.CancelledError


async def _store_proposal_without_finalizing(
    orchestrator: DurableNarrativeTurnOrchestrator,
    provider: LockCheckingProvider,
    action: ActionSubmission,
) -> NarrativeJob:
    prepared = await orchestrator._prepare_or_execute(action)
    assert not hasattr(prepared, "resolution_kind")
    claimed = await orchestrator._claim(prepared.job.job_id)
    assert claimed is not None
    request = NarrativeRequest.model_validate(claimed.narrative_request, strict=False)
    untrusted = await provider.generate(request)
    validated = orchestrator.proposal_validator.validate(
        untrusted,
        request=request,
        public_references=orchestrator._public_references(request),
    )
    return await orchestrator._store_validated_proposal(claimed, validated)


async def _create_narrative_session(
    factory: async_sessionmaker[AsyncSession],
    *,
    prefix: str,
    clock_value: list[datetime],
) -> tuple[object, str, ActionSubmission]:
    catalog = JsonScenarioCatalogLoader(SCENARIO_PACK).load()
    session_id = f"{prefix}-{uuid4().hex}"
    service = SessionService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(factory),
        catalog=catalog.content_catalog,
        scenario_catalog=catalog,
        clock=lambda: clock_value[0],
        session_id_generator=lambda: session_id,
        seed_generator=lambda: 42,
    )
    await service.create(
        RequestPrincipal(
            player_id=f"{prefix}-player-{uuid4().hex}",
            authentication_scheme="integration",
        ),
        client_request_id=f"create-{prefix}",
        character_definition_id="character.death_certificate.investigator",
        scenario_id="death_certificate",
    )
    return (
        catalog,
        session_id,
        ActionSubmission(
            session_id=session_id,
            turn_id=f"{prefix}-turn",
            client_request_id=f"{prefix}-request",
            action_type=ActionType.CUSTOM,
            description="我尝试有规律地移动手指发出生命信号",
        ),
    )


def _orchestrator(
    factory: async_sessionmaker[AsyncSession],
    catalog,
    provider,
    clock_value: list[datetime],
    *,
    uow_factory=None,
    orchestrator_type=DurableNarrativeTurnOrchestrator,
) -> DurableNarrativeTurnOrchestrator:
    return orchestrator_type(
        resolver=DeterministicRuleResolver(),
        uow_factory=uow_factory or (lambda: SqlAlchemyUnitOfWork(factory)),
        catalog=catalog.content_catalog,
        scenario_catalog=catalog,
        narrative_provider=provider,
        provider_name="fake",
        model_name="fake-model",
        clock=lambda: clock_value[0],
        lease_duration=timedelta(minutes=2),
        job_id_generator=lambda: f"job-{uuid4().hex}",
        lease_token_generator=lambda: uuid4().hex,
        worker_id_generator=lambda: f"worker-{uuid4().hex}",
        event_id_generator=lambda: f"event-{uuid4().hex}",
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_mysql_narrative_prepare_call_finalize_is_atomic_and_replay_safe(
    mysql_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    catalog = JsonScenarioCatalogLoader(SCENARIO_PACK).load()
    session_id = f"narrative-{uuid4().hex}"
    player_id = f"narrative-player-{uuid4().hex}"
    active_uows = [0]
    uow_factory = lambda: TrackingUnitOfWork(mysql_session_factory, active_uows)
    session_service = SessionService(
        uow_factory=uow_factory,
        catalog=catalog.content_catalog,
        scenario_catalog=catalog,
        clock=lambda: NOW,
        session_id_generator=lambda: session_id,
        seed_generator=lambda: 42,
    )
    provider = LockCheckingProvider(mysql_session_factory, session_id, active_uows)
    orchestrator = DurableNarrativeTurnOrchestrator(
        resolver=DeterministicRuleResolver(),
        uow_factory=uow_factory,
        catalog=catalog.content_catalog,
        scenario_catalog=catalog,
        narrative_provider=provider,
        provider_name="fake",
        model_name="fake-model",
        clock=lambda: NOW,
        job_id_generator=lambda: f"job-{uuid4().hex}",
        lease_token_generator=lambda: uuid4().hex,
        worker_id_generator=lambda: f"worker-{uuid4().hex}",
        event_id_generator=lambda: f"event-{uuid4().hex}",
    )
    principal = RequestPrincipal(player_id=player_id, authentication_scheme="integration")
    try:
        await session_service.create(
            principal,
            client_request_id="create-narrative-session",
            character_definition_id="character.death_certificate.investigator",
            scenario_id="death_certificate",
        )
        action = ActionSubmission(
            session_id=session_id,
            turn_id="narrative-turn-1",
            client_request_id="narrative-request-1",
            action_type=ActionType.CUSTOM,
            description="我尝试有规律地移动手指发出生命信号",
        )
        response = await orchestrator.handle(action)
        replay = await orchestrator.handle(action)

        assert response == replay
        assert response.resolution_kind is ResolutionStatus.NARRATIVE_COMMITTED
        assert response.narrative_text is not None
        assert response.resulting_state_version == 1
        assert provider.calls == 1
        async with mysql_session_factory() as database:
            session_row = await database.get(GameSessionRow, session_id)
            snapshot = await database.get(GameSnapshotRow, session_id)
            job = await database.scalar(
                select(NarrativeJobRow).where(NarrativeJobRow.session_id == session_id)
            )
            turn = await database.scalar(
                select(TurnRequestRow).where(TurnRequestRow.session_id == session_id)
            )
        assert session_row is not None and session_row.state_version == 1
        assert snapshot is not None
        assert response.narrative_text not in json.dumps(
            snapshot.state_json, ensure_ascii=False
        )
        assert "仅供候选校验的非权威连续性备注" not in json.dumps(
            snapshot.state_json, ensure_ascii=False
        )
        assert job is not None and job.status == "COMMITTED"
        assert job.accepted_narrative_text == response.narrative_text
        assert job.lease_token is None
        assert turn is not None and turn.response_json == response.to_persistence()
    finally:
        async with mysql_session_factory.begin() as database:
            await database.execute(
                delete(GameSessionRow).where(GameSessionRow.session_id == session_id)
            )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_provider_wait_releases_session_lock_deduplicates_and_allows_queries(
    mysql_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    catalog = JsonScenarioCatalogLoader(SCENARIO_PACK).load()
    session_id = f"narrative-wait-{uuid4().hex}"
    player_id = f"narrative-player-{uuid4().hex}"
    uow_factory = lambda: SqlAlchemyUnitOfWork(mysql_session_factory)
    session_service = SessionService(
        uow_factory=uow_factory,
        catalog=catalog.content_catalog,
        scenario_catalog=catalog,
        clock=lambda: NOW,
        session_id_generator=lambda: session_id,
        seed_generator=lambda: 42,
    )
    provider = BlockingProvider(mysql_session_factory, session_id)
    orchestrator = DurableNarrativeTurnOrchestrator(
        resolver=DeterministicRuleResolver(),
        uow_factory=uow_factory,
        catalog=catalog.content_catalog,
        scenario_catalog=catalog,
        narrative_provider=provider,
        provider_name="fake",
        model_name="fake-model",
        clock=lambda: NOW,
        job_id_generator=lambda: f"job-{uuid4().hex}",
        lease_token_generator=lambda: uuid4().hex,
        worker_id_generator=lambda: f"worker-{uuid4().hex}",
        event_id_generator=lambda: f"event-{uuid4().hex}",
    )
    principal = RequestPrincipal(player_id=player_id, authentication_scheme="integration")
    try:
        created = await session_service.create(
            principal,
            client_request_id="create-wait-session",
            character_definition_id="character.death_certificate.investigator",
            scenario_id="death_certificate",
        )
        action = ActionSubmission(
            session_id=session_id,
            turn_id="narrative-wait-turn",
            client_request_id="narrative-wait-request",
            action_type=ActionType.CUSTOM,
            description="我尝试有规律地移动手指发出生命信号",
        )
        first = asyncio.create_task(orchestrator.handle(action))
        await asyncio.wait_for(provider.entered.wait(), timeout=2)

        duplicate = await asyncio.wait_for(orchestrator.handle(action), timeout=2)
        assert duplicate.resolution_kind is ResolutionStatus.NARRATIVE_REQUIRED
        assert duplicate.narrative_pending is True
        async with mysql_session_factory() as database:
            pending_turn = await database.scalar(
                select(TurnRequestRow).where(
                    TurnRequestRow.session_id == session_id,
                    TurnRequestRow.client_request_id == action.client_request_id,
                )
            )
        assert pending_turn is None

        query = await asyncio.wait_for(
            orchestrator.handle(
                ActionSubmission(
                    session_id=session_id,
                    turn_id="query-during-provider",
                    client_request_id="query-during-provider",
                    action_type=ActionType.INSPECT_STATUS,
                )
            ),
            timeout=2,
        )
        assert query.resolution_kind is ResolutionStatus.RESOLVED_LOCAL
        assert query.state_changed is False
        assert query.resulting_state_version == 0
        with pytest.raises(NarrativeJobActiveError):
            await orchestrator.handle(
                ActionSubmission(
                    session_id=session_id,
                    turn_id="blocked-decision-turn",
                    client_request_id="blocked-decision-request",
                    action_type=ActionType.CHOOSE,
                    decision_id=created.narrative_frame.decision_id,
                    choice_id="death_certificate.action.observe_quietly",
                )
            )

        provider.release.set()
        committed = await asyncio.wait_for(first, timeout=2)
        assert committed.resolution_kind is ResolutionStatus.NARRATIVE_COMMITTED
        assert provider.calls == 1
    finally:
        provider.release.set()
        async with mysql_session_factory.begin() as database:
            await database.execute(
                delete(GameSessionRow).where(GameSessionRow.session_id == session_id)
            )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_state_change_while_provider_runs_marks_job_stale_without_text(
    mysql_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    catalog = JsonScenarioCatalogLoader(SCENARIO_PACK).load()
    session_id = f"narrative-stale-{uuid4().hex}"
    player_id = f"narrative-player-{uuid4().hex}"
    uow_factory = lambda: SqlAlchemyUnitOfWork(mysql_session_factory)
    session_service = SessionService(
        uow_factory=uow_factory,
        catalog=catalog.content_catalog,
        scenario_catalog=catalog,
        clock=lambda: NOW,
        session_id_generator=lambda: session_id,
        seed_generator=lambda: 42,
    )
    provider = BlockingProvider(mysql_session_factory, session_id)
    orchestrator = DurableNarrativeTurnOrchestrator(
        resolver=DeterministicRuleResolver(),
        uow_factory=uow_factory,
        catalog=catalog.content_catalog,
        scenario_catalog=catalog,
        narrative_provider=provider,
        provider_name="fake",
        model_name="fake-model",
        clock=lambda: NOW,
        job_id_generator=lambda: f"job-{uuid4().hex}",
        lease_token_generator=lambda: uuid4().hex,
        worker_id_generator=lambda: f"worker-{uuid4().hex}",
        event_id_generator=lambda: f"event-{uuid4().hex}",
    )
    principal = RequestPrincipal(player_id=player_id, authentication_scheme="integration")
    try:
        created = await session_service.create(
            principal,
            client_request_id="create-stale-session",
            character_definition_id="character.death_certificate.investigator",
            scenario_id="death_certificate",
        )
        narrative = ActionSubmission(
            session_id=session_id,
            turn_id="stale-narrative-turn",
            client_request_id="stale-narrative-request",
            action_type=ActionType.CUSTOM,
            description="我尝试有规律地移动手指发出生命信号",
        )
        worker = asyncio.create_task(orchestrator.handle(narrative))
        await asyncio.wait_for(provider.entered.wait(), timeout=2)

        bypass = FirstPhaseTurnOrchestrator(
            resolver=DeterministicRuleResolver(),
            uow_factory=uow_factory,
            catalog=catalog.content_catalog,
            scenario_catalog=catalog,
            clock=lambda: NOW,
            event_id_generator=lambda: f"bypass-{uuid4().hex}",
        )
        await bypass.handle(
            ActionSubmission(
                session_id=session_id,
                turn_id="authoritative-other-turn",
                client_request_id="authoritative-other-request",
                action_type=ActionType.CHOOSE,
                decision_id=created.narrative_frame.decision_id,
                choice_id="death_certificate.action.observe_quietly",
            )
        )
        provider.release.set()
        with pytest.raises(NarrativeJobStaleError):
            await worker

        async with mysql_session_factory() as database:
            job = await database.scalar(
                select(NarrativeJobRow).where(
                    NarrativeJobRow.session_id == session_id,
                    NarrativeJobRow.client_request_id == narrative.client_request_id,
                )
            )
            narrative_turn = await database.scalar(
                select(TurnRequestRow).where(
                    TurnRequestRow.session_id == session_id,
                    TurnRequestRow.client_request_id == narrative.client_request_id,
                )
            )
        assert job is not None and job.status == "STALE"
        assert job.accepted_narrative_text is None
        assert narrative_turn is None
    finally:
        provider.release.set()
        async with mysql_session_factory.begin() as database:
            await database.execute(
                delete(GameSessionRow).where(GameSessionRow.session_id == session_id)
            )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_different_sessions_enter_provider_concurrently(
    mysql_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    catalog = JsonScenarioCatalogLoader(SCENARIO_PACK).load()
    session_ids = [f"parallel-{uuid4().hex}" for _ in range(2)]
    uow_factory = lambda: SqlAlchemyUnitOfWork(mysql_session_factory)
    principal = RequestPrincipal(
        player_id=f"parallel-player-{uuid4().hex}", authentication_scheme="integration"
    )
    generated_session_ids = iter(session_ids)
    session_service = SessionService(
        uow_factory=uow_factory,
        catalog=catalog.content_catalog,
        scenario_catalog=catalog,
        clock=lambda: NOW,
        session_id_generator=lambda: next(generated_session_ids),
        seed_generator=lambda: 42,
    )
    provider = ParallelProvider()
    orchestrator = DurableNarrativeTurnOrchestrator(
        resolver=DeterministicRuleResolver(),
        uow_factory=uow_factory,
        catalog=catalog.content_catalog,
        scenario_catalog=catalog,
        narrative_provider=provider,
        provider_name="fake",
        model_name="fake-model",
        clock=lambda: NOW,
        job_id_generator=lambda: f"job-{uuid4().hex}",
        lease_token_generator=lambda: uuid4().hex,
        worker_id_generator=lambda: f"worker-{uuid4().hex}",
        event_id_generator=lambda: f"event-{uuid4().hex}",
    )
    try:
        for index in range(2):
            await session_service.create(
                principal,
                client_request_id=f"create-parallel-{index}",
                character_definition_id="character.death_certificate.investigator",
                scenario_id="death_certificate",
            )
        tasks = [
            asyncio.create_task(
                orchestrator.handle(
                    ActionSubmission(
                        session_id=session_id,
                        turn_id=f"turn-{index}",
                        client_request_id=f"request-{index}",
                        action_type=ActionType.CUSTOM,
                        description="我尝试有规律地移动手指发出生命信号",
                    )
                )
            )
            for index, session_id in enumerate(session_ids)
        ]
        await asyncio.wait_for(provider.both_entered.wait(), timeout=5)
        provider.release.set()
        responses = await asyncio.gather(*tasks)
        assert all(
            item.resolution_kind is ResolutionStatus.NARRATIVE_COMMITTED
            for item in responses
        )
        assert provider.calls == 2
    finally:
        provider.release.set()
        async with mysql_session_factory.begin() as database:
            await database.execute(
                delete(GameSessionRow).where(GameSessionRow.session_id.in_(session_ids))
            )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_expired_provider_lease_cannot_commit_and_is_not_retried(
    mysql_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    catalog = JsonScenarioCatalogLoader(SCENARIO_PACK).load()
    session_id = f"expired-{uuid4().hex}"
    player_id = f"expired-player-{uuid4().hex}"
    clock_value = [NOW]
    uow_factory = lambda: SqlAlchemyUnitOfWork(mysql_session_factory)
    service = SessionService(
        uow_factory=uow_factory,
        catalog=catalog.content_catalog,
        scenario_catalog=catalog,
        clock=lambda: clock_value[0],
        session_id_generator=lambda: session_id,
        seed_generator=lambda: 42,
    )
    provider = LeaseExpiringProvider(mysql_session_factory, session_id, clock_value)
    orchestrator = DurableNarrativeTurnOrchestrator(
        resolver=DeterministicRuleResolver(),
        uow_factory=uow_factory,
        catalog=catalog.content_catalog,
        scenario_catalog=catalog,
        narrative_provider=provider,
        provider_name="fake",
        model_name="fake-model",
        clock=lambda: clock_value[0],
        lease_duration=timedelta(minutes=2),
        job_id_generator=lambda: f"job-{uuid4().hex}",
        lease_token_generator=lambda: uuid4().hex,
        worker_id_generator=lambda: f"worker-{uuid4().hex}",
        event_id_generator=lambda: f"event-{uuid4().hex}",
    )
    principal = RequestPrincipal(player_id=player_id, authentication_scheme="integration")
    action = ActionSubmission(
        session_id=session_id,
        turn_id="expired-turn",
        client_request_id="expired-request",
        action_type=ActionType.CUSTOM,
        description="我尝试有规律地移动手指发出生命信号",
    )
    try:
        await service.create(
            principal,
            client_request_id="create-expired-session",
            character_definition_id="character.death_certificate.investigator",
            scenario_id="death_certificate",
        )
        with pytest.raises(NarrativeOutcomeUnknownError):
            await orchestrator.handle(action)
        with pytest.raises(NarrativeOutcomeUnknownError):
            await orchestrator.handle(action)
        async with mysql_session_factory() as database:
            session_row = await database.get(GameSessionRow, session_id)
            job = await database.scalar(
                select(NarrativeJobRow).where(NarrativeJobRow.session_id == session_id)
            )
            turn = await database.scalar(
                select(TurnRequestRow).where(
                    TurnRequestRow.session_id == session_id,
                    TurnRequestRow.client_request_id == action.client_request_id,
                )
            )
        assert provider.calls == 1
        assert session_row is not None and session_row.state_version == 0
        assert job is not None and job.status == "OUTCOME_UNKNOWN"
        assert job.accepted_narrative_text is None
        assert turn is None
    finally:
        async with mysql_session_factory.begin() as database:
            await database.execute(
                delete(GameSessionRow).where(GameSessionRow.session_id == session_id)
            )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_proposal_validated_crash_recovery_finalizes_without_provider_reinvocation(
    mysql_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    clock_value = [NOW]
    catalog, session_id, action = await _create_narrative_session(
        mysql_session_factory, prefix="proposal-recovery", clock_value=clock_value
    )
    provider = LockCheckingProvider(mysql_session_factory, session_id)
    orchestrator = _orchestrator(
        mysql_session_factory, catalog, provider, clock_value
    )
    try:
        stored = await _store_proposal_without_finalizing(
            orchestrator, provider, action
        )
        assert stored.status.value == "PROPOSAL_VALIDATED"
        assert provider.calls == 1

        clock_value[0] += timedelta(minutes=3)
        response = await orchestrator.handle(action)

        assert response.resolution_kind is ResolutionStatus.NARRATIVE_COMMITTED
        assert provider.calls == 1
        async with mysql_session_factory() as database:
            job = await database.get(NarrativeJobRow, stored.job_id)
        assert job is not None and job.status == "COMMITTED"
        assert job.accepted_narrative_text == response.narrative_text
    finally:
        async with mysql_session_factory.begin() as database:
            await database.execute(
                delete(GameSessionRow).where(GameSessionRow.session_id == session_id)
            )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_expired_in_progress_is_unknown_even_when_transport_was_not_observed(
    mysql_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    clock_value = [NOW]
    catalog, session_id, action = await _create_narrative_session(
        mysql_session_factory, prefix="claim-crash", clock_value=clock_value
    )
    provider = LockCheckingProvider(mysql_session_factory, session_id)
    orchestrator = _orchestrator(
        mysql_session_factory, catalog, provider, clock_value
    )
    try:
        prepared = await orchestrator._prepare_or_execute(action)
        claimed = await orchestrator._claim(prepared.job.job_id)
        assert claimed is not None and claimed.status.value == "IN_PROGRESS"
        assert provider.calls == 0

        # Durable state is identical for a crash immediately before send and a
        # crash after send but before a response. It therefore cannot prove the
        # provider was not called or billed and must not resend.
        clock_value[0] += timedelta(minutes=3)
        with pytest.raises(NarrativeOutcomeUnknownError):
            await orchestrator.handle(action)
        with pytest.raises(NarrativeOutcomeUnknownError):
            await orchestrator.handle(action)

        assert provider.calls == 0
        async with mysql_session_factory() as database:
            job = await database.get(NarrativeJobRow, claimed.job_id)
        assert job is not None and job.status == "OUTCOME_UNKNOWN"
        assert job.accepted_narrative_text is None
    finally:
        async with mysql_session_factory.begin() as database:
            await database.execute(
                delete(GameSessionRow).where(GameSessionRow.session_id == session_id)
            )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_prepared_job_rejects_same_idempotency_key_with_different_signature(
    mysql_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    clock_value = [NOW]
    catalog, session_id, action = await _create_narrative_session(
        mysql_session_factory, prefix="job-idempotency", clock_value=clock_value
    )
    provider = LockCheckingProvider(mysql_session_factory, session_id)
    orchestrator = _orchestrator(
        mysql_session_factory, catalog, provider, clock_value
    )
    try:
        prepared = await orchestrator._prepare_or_execute(action)
        assert prepared.job.client_request_id == action.client_request_id
        conflicting = action.model_copy(
            update={"description": "我改成安静观察，但复用原来的请求键"}
        )

        with pytest.raises(IdempotencyConflictError):
            await orchestrator.handle(conflicting)

        async with mysql_session_factory() as database:
            jobs = (
                await database.scalars(
                    select(NarrativeJobRow).where(
                        NarrativeJobRow.session_id == session_id
                    )
                )
            ).all()
        assert len(jobs) == 1
        assert jobs[0].status == "PREPARED"
        assert provider.calls == 0
    finally:
        async with mysql_session_factory.begin() as database:
            await database.execute(
                delete(GameSessionRow).where(GameSessionRow.session_id == session_id)
            )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_old_proposal_lease_cannot_finalize_or_overwrite_resumed_job(
    mysql_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    clock_value = [NOW]
    catalog, session_id, action = await _create_narrative_session(
        mysql_session_factory, prefix="proposal-fence", clock_value=clock_value
    )
    provider = LockCheckingProvider(mysql_session_factory, session_id)
    orchestrator = _orchestrator(
        mysql_session_factory, catalog, provider, clock_value
    )
    try:
        old_lease = await _store_proposal_without_finalizing(
            orchestrator, provider, action
        )
        clock_value[0] += timedelta(minutes=3)

        with pytest.raises(NarrativeJobStaleError):
            await orchestrator._finalize_or_record(old_lease, action)
        async with mysql_session_factory() as database:
            expired_unchanged = await database.get(NarrativeJobRow, old_lease.job_id)
        assert expired_unchanged is not None
        assert expired_unchanged.status == "PROPOSAL_VALIDATED"
        assert expired_unchanged.lease_token == old_lease.lease_token

        resumed = await orchestrator._claim(old_lease.job_id)
        assert resumed is not None
        assert resumed.lease_token != old_lease.lease_token

        with pytest.raises(NarrativeJobStaleError):
            await orchestrator._finalize_or_record(old_lease, action)
        async with mysql_session_factory() as database:
            still_resumed = await database.get(NarrativeJobRow, old_lease.job_id)
        assert still_resumed is not None
        assert still_resumed.status == "PROPOSAL_VALIDATED"
        assert still_resumed.lease_token == resumed.lease_token

        response = await orchestrator._finalize_or_record(resumed, action)
        assert response.resolution_kind is ResolutionStatus.NARRATIVE_COMMITTED
        assert provider.calls == 1
    finally:
        async with mysql_session_factory.begin() as database:
            await database.execute(
                delete(GameSessionRow).where(GameSessionRow.session_id == session_id)
            )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_finalize_commit_failure_rolls_back_all_authority_but_retains_candidate(
    mysql_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    clock_value = [NOW]
    catalog, session_id, action = await _create_narrative_session(
        mysql_session_factory, prefix="finalize-rollback", clock_value=clock_value
    )
    provider = LockCheckingProvider(mysql_session_factory, session_id)
    commit_count = [0]
    failing_uow_factory = lambda: FailNthCommitUnitOfWork(
        mysql_session_factory, commit_count, fail_at=4
    )
    orchestrator = _orchestrator(
        mysql_session_factory,
        catalog,
        provider,
        clock_value,
        uow_factory=failing_uow_factory,
    )
    try:
        async with mysql_session_factory() as database:
            before_session = await database.get(GameSessionRow, session_id)
            before_snapshot = await database.get(GameSnapshotRow, session_id)
            before_events = tuple(
                (row.event_id, row.sequence_no, row.event_type, dict(row.payload_json))
                for row in (
                    await database.scalars(
                        select(DomainEventRow)
                        .where(DomainEventRow.session_id == session_id)
                        .order_by(DomainEventRow.sequence_no)
                    )
                ).all()
            )
            baseline = (
                before_session.state_version,
                before_session.phase,
                before_session.turn_number,
                before_snapshot.state_version,
                dict(before_snapshot.state_json),
                before_events,
            )

        with pytest.raises(RuntimeError, match="finalize commit failure"):
            await orchestrator.handle(action)

        async with mysql_session_factory() as database:
            after_session = await database.get(GameSessionRow, session_id)
            after_snapshot = await database.get(GameSnapshotRow, session_id)
            after_events = tuple(
                (row.event_id, row.sequence_no, row.event_type, dict(row.payload_json))
                for row in (
                    await database.scalars(
                        select(DomainEventRow)
                        .where(DomainEventRow.session_id == session_id)
                        .order_by(DomainEventRow.sequence_no)
                    )
                ).all()
            )
            turn = await database.scalar(
                select(TurnRequestRow).where(
                    TurnRequestRow.session_id == session_id,
                    TurnRequestRow.client_request_id == action.client_request_id,
                )
            )
            job = await database.scalar(
                select(NarrativeJobRow).where(NarrativeJobRow.session_id == session_id)
            )
            after = (
                after_session.state_version,
                after_session.phase,
                after_session.turn_number,
                after_snapshot.state_version,
                dict(after_snapshot.state_json),
                after_events,
            )
        assert after == baseline
        assert turn is None
        assert job is not None and job.status == "PROPOSAL_VALIDATED"
        assert job.validated_proposal_json is not None
        assert job.accepted_narrative_text is None
    finally:
        async with mysql_session_factory.begin() as database:
            await database.execute(
                delete(GameSessionRow).where(GameSessionRow.session_id == session_id)
            )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_disconnect_after_finalize_commit_replays_exact_persisted_response(
    mysql_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    clock_value = [NOW]
    catalog, session_id, action = await _create_narrative_session(
        mysql_session_factory, prefix="post-commit-disconnect", clock_value=clock_value
    )
    provider = LockCheckingProvider(mysql_session_factory, session_id)
    orchestrator = _orchestrator(
        mysql_session_factory,
        catalog,
        provider,
        clock_value,
        orchestrator_type=DisconnectAfterFinalizeOrchestrator,
    )
    try:
        with pytest.raises(asyncio.CancelledError):
            await orchestrator.handle(action)

        replay = await orchestrator.handle(action)
        async with mysql_session_factory() as database:
            turn = await database.scalar(
                select(TurnRequestRow).where(
                    TurnRequestRow.session_id == session_id,
                    TurnRequestRow.client_request_id == action.client_request_id,
                )
            )
            job = await database.scalar(
                select(NarrativeJobRow).where(NarrativeJobRow.session_id == session_id)
            )
        assert turn is not None and turn.response_json == replay.to_persistence()
        assert job is not None and job.status == "COMMITTED"
        assert replay.narrative_text == job.accepted_narrative_text
        assert provider.calls == 1
    finally:
        async with mysql_session_factory.begin() as database:
            await database.execute(
                delete(GameSessionRow).where(GameSessionRow.session_id == session_id)
            )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_client_cancellation_during_provider_is_conservatively_unknown(
    mysql_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    clock_value = [NOW]
    catalog, session_id, action = await _create_narrative_session(
        mysql_session_factory, prefix="provider-cancel", clock_value=clock_value
    )
    provider = CancelledProvider(mysql_session_factory, session_id)
    orchestrator = _orchestrator(
        mysql_session_factory, catalog, provider, clock_value
    )
    try:
        with pytest.raises(asyncio.CancelledError):
            await orchestrator.handle(action)
        with pytest.raises(NarrativeOutcomeUnknownError):
            await orchestrator.handle(action)

        async with mysql_session_factory() as database:
            session_row = await database.get(GameSessionRow, session_id)
            job = await database.scalar(
                select(NarrativeJobRow).where(NarrativeJobRow.session_id == session_id)
            )
        assert session_row is not None and session_row.state_version == 0
        assert job is not None and job.status == "OUTCOME_UNKNOWN"
        assert job.accepted_narrative_text is None
        assert provider.calls == 1
    finally:
        async with mysql_session_factory.begin() as database:
            await database.execute(
                delete(GameSessionRow).where(GameSessionRow.session_id == session_id)
            )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rejected_outcome_retains_only_non_authoritative_candidate_text(
    mysql_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    clock_value = [NOW]
    catalog, session_id, action = await _create_narrative_session(
        mysql_session_factory, prefix="candidate-isolation", clock_value=clock_value
    )
    provider = ContradictoryFailureProvider(mysql_session_factory, session_id)
    orchestrator = _orchestrator(
        mysql_session_factory, catalog, provider, clock_value
    )
    try:
        with pytest.raises(NarrativeProposalRejectedError):
            await orchestrator.handle(action)

        async with mysql_session_factory() as database:
            session_row = await database.get(GameSessionRow, session_id)
            snapshot = await database.get(GameSnapshotRow, session_id)
            job = await database.scalar(
                select(NarrativeJobRow).where(NarrativeJobRow.session_id == session_id)
            )
            turn = await database.scalar(
                select(TurnRequestRow).where(
                    TurnRequestRow.session_id == session_id,
                    TurnRequestRow.client_request_id == action.client_request_id,
                )
            )
            events = (
                await database.scalars(
                    select(DomainEventRow).where(DomainEventRow.session_id == session_id)
                )
            ).all()
        async with SqlAlchemyUnitOfWork(mysql_session_factory) as uow:
            recent = await uow.narrative_jobs.recent_committed_texts(
                session_id, limit=6
            )

        assert session_row is not None and session_row.state_version == 0
        assert snapshot is not None and snapshot.state_version == 0
        assert turn is None and not events
        assert job is not None and job.status == "FAILED_TERMINAL"
        assert job.validated_proposal_json is not None
        assert job.accepted_narrative_text is None
        assert recent == ()
        assert provider.calls == 1
    finally:
        async with mysql_session_factory.begin() as database:
            await database.execute(
                delete(GameSessionRow).where(GameSessionRow.session_id == session_id)
            )
