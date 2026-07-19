from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from deviation_protocol.domain.models import GameSession
from deviation_protocol.infrastructure.errors import OptimisticLockError
from deviation_protocol.infrastructure.repositories import SqlAlchemyGameSessionRepository
from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


@pytest.mark.asyncio
async def test_repository_locks_session_row_for_turn_processing() -> None:
    sql_session = AsyncMock()
    sql_session.execute.return_value = SimpleNamespace(
        scalar_one_or_none=lambda: "session-1"
    )
    repository = SqlAlchemyGameSessionRepository(sql_session)

    assert await repository.lock_for_turn("session-1") is True
    statement = sql_session.execute.await_args.args[0]
    assert statement._for_update_arg is not None


@pytest.mark.asyncio
async def test_repository_detects_optimistic_lock_conflict() -> None:
    sql_session = AsyncMock()
    sql_session.execute.return_value = SimpleNamespace(rowcount=0)
    repository = SqlAlchemyGameSessionRepository(sql_session)
    aggregate = GameSession(
        session_id="session-1",
        player_id="player-1",
        scenario_id="scenario-1",
        scenario_version="1",
        phase="AWAITING_ACTION",
        turn_number=3,
        state_version=5,
        random_seed=42,
    )
    with pytest.raises(OptimisticLockError):
        await repository.save_snapshot_and_events(aggregate, {}, (), expected_state_version=4)
    assert sql_session.execute.await_count == 1


class FakeSession:
    def __init__(self) -> None:
        self.commit = AsyncMock()
        self.rollback = AsyncMock()
        self.close = AsyncMock()


@pytest.mark.asyncio
async def test_unit_of_work_commit() -> None:
    session = FakeSession()
    uow = SqlAlchemyUnitOfWork(lambda: session)  # type: ignore[arg-type]
    async with uow:
        await uow.commit()
    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()
    session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_unit_of_work_rolls_back_uncommitted_work() -> None:
    session = FakeSession()
    uow = SqlAlchemyUnitOfWork(lambda: session)  # type: ignore[arg-type]
    async with uow:
        pass
    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()
    session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_unit_of_work_rolls_back_on_exception() -> None:
    session = FakeSession()
    uow = SqlAlchemyUnitOfWork(lambda: session)  # type: ignore[arg-type]
    with pytest.raises(RuntimeError, match="boom"):
        async with uow:
            raise RuntimeError("boom")
    session.rollback.assert_awaited_once()
    session.close.assert_awaited_once()
