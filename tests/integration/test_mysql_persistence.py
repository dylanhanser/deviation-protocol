from __future__ import annotations

import asyncio
from collections.abc import Callable
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from deviation_protocol.application.action_gateway import ActionGateway
from deviation_protocol.application.turn_orchestrator import FirstPhaseTurnOrchestrator
from deviation_protocol.domain.actions import ActionContext, ActionSubmission, ActionType
from deviation_protocol.domain.events import DomainEvent
from deviation_protocol.domain.models import GameSession
from deviation_protocol.infrastructure.errors import OptimisticLockError
from deviation_protocol.infrastructure.orm_models import (
    DomainEventRow,
    GameSessionRow,
    GameSnapshotRow,
    TurnRequestRow,
)
from deviation_protocol.infrastructure.repositories import SqlAlchemyGameSessionRepository
from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


def aggregate(session_id: str) -> GameSession:
    return GameSession(
        session_id=session_id,
        player_id="integration-player",
        scenario_id="integration-scenario",
        scenario_version="1",
        phase="AWAITING_ACTION",
        turn_number=1,
        state_version=0,
        random_seed=42,
    )


def event(session_id: str, *, sequence_no: int = 1) -> DomainEvent:
    return DomainEvent(
        event_id=f"it-event-{uuid4().hex}",
        session_id=session_id,
        turn_id="turn-1",
        sequence_no=sequence_no,
        event_type="IntegrationTestEvent",
        payload={"source": "integration"},
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_snapshot_event_and_version_commit_atomically(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    mysql_session_id: str,
) -> None:
    game_session = aggregate(mysql_session_id)
    domain_event = event(mysql_session_id)

    async with SqlAlchemyUnitOfWork(mysql_session_factory) as uow:
        await uow.sessions.save_snapshot_and_events(
            game_session,
            {"location": "integration-room"},
            (domain_event,),
            expected_state_version=0,
        )
        await uow.commit()

    async with mysql_session_factory() as session:
        session_row = await session.get(GameSessionRow, mysql_session_id)
        snapshot = await session.get(GameSnapshotRow, mysql_session_id)
        stored_event = await session.get(DomainEventRow, domain_event.event_id)

    assert session_row is not None and session_row.state_version == 1
    assert snapshot is not None and snapshot.state_version == 1
    assert snapshot.state_json == {"location": "integration-room"}
    assert stored_event is not None and stored_event.payload_json == {
        "source": "integration"
    }
    assert game_session.state_version == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_uow_exception_rolls_back_session_snapshot_and_event(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    mysql_session_id: str,
) -> None:
    game_session = aggregate(mysql_session_id)
    domain_event = event(mysql_session_id)

    with pytest.raises(RuntimeError, match="force rollback"):
        async with SqlAlchemyUnitOfWork(mysql_session_factory) as uow:
            await uow.sessions.save_snapshot_and_events(
                game_session,
                {"should": "rollback"},
                (domain_event,),
                expected_state_version=0,
            )
            raise RuntimeError("force rollback")

    async with mysql_session_factory() as session:
        session_row = await session.get(GameSessionRow, mysql_session_id)
        snapshot = await session.get(GameSnapshotRow, mysql_session_id)
        stored_event = await session.get(DomainEventRow, domain_event.event_id)

    assert session_row is not None and session_row.state_version == 0
    assert snapshot is None
    assert stored_event is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_optimistic_lock_conflict_uses_real_asyncmy_rowcount(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    mysql_session_id: str,
) -> None:
    game_session = aggregate(mysql_session_id)

    with pytest.raises(OptimisticLockError):
        async with SqlAlchemyUnitOfWork(mysql_session_factory) as uow:
            await uow.sessions.save_snapshot_and_events(
                game_session,
                {"should": "not persist"},
                (event(mysql_session_id),),
                expected_state_version=7,
            )

    async with mysql_session_factory() as session:
        session_row = await session.get(GameSessionRow, mysql_session_id)
        snapshot = await session.get(GameSnapshotRow, mysql_session_id)

    assert session_row is not None and session_row.state_version == 0
    assert snapshot is None
    assert game_session.state_version == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_select_for_update_blocks_competing_asyncmy_transaction(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    mysql_session_id: str,
) -> None:
    first_session = mysql_session_factory()
    second_session = mysql_session_factory()
    try:
        first_repository = SqlAlchemyGameSessionRepository(first_session)
        second_repository = SqlAlchemyGameSessionRepository(second_session)
        assert await first_repository.lock_for_turn(mysql_session_id) is True

        competing_lock = asyncio.create_task(
            second_repository.lock_for_turn(mysql_session_id)
        )
        await asyncio.sleep(0.1)
        assert not competing_lock.done()

        await first_session.commit()
        assert await asyncio.wait_for(competing_lock, timeout=2.0) is True
        await second_session.rollback()
    finally:
        await first_session.close()
        await second_session.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_duplicate_request_runs_business_once_and_returns_stored_result(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    mysql_session_id: str,
) -> None:
    submission = ActionSubmission(
        session_id=mysql_session_id,
        turn_id="turn-1",
        client_request_id=f"it-request-{uuid4().hex}",
        action_type=ActionType.CUSTOM,
        description="我尝试观察门锁",
    )
    business_entered = asyncio.Event()
    release_business = asyncio.Event()
    business_calls = 0

    async def context_loader(action: ActionSubmission) -> ActionContext:
        nonlocal business_calls
        business_calls += 1
        business_entered.set()
        await release_business.wait()
        return ActionContext(submission=action, current_turn_id=action.turn_id)

    uow_factory: Callable[[], SqlAlchemyUnitOfWork] = lambda: SqlAlchemyUnitOfWork(
        mysql_session_factory
    )
    orchestrator = FirstPhaseTurnOrchestrator(
        ActionGateway.from_config(), uow_factory, context_loader
    )

    first = asyncio.create_task(orchestrator.handle(submission))
    await asyncio.wait_for(business_entered.wait(), timeout=2.0)
    second = asyncio.create_task(orchestrator.handle(submission))
    await asyncio.sleep(0.1)
    assert not second.done()
    release_business.set()
    first_result, second_result = await asyncio.gather(first, second)

    async with mysql_session_factory() as session:
        request_count = await session.scalar(
            select(func.count())
            .select_from(TurnRequestRow)
            .where(
                TurnRequestRow.session_id == mysql_session_id,
                TurnRequestRow.client_request_id == submission.client_request_id,
            )
        )

    assert business_calls == 1
    assert first_result == second_result
    assert request_count == 1
