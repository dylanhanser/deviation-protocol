from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import IntegrityError

from deviation_protocol.application.errors import (
    ConcurrentSessionCreateError,
    ConcurrentTurnRequestError,
)
from deviation_protocol.domain.models import GameSession
from deviation_protocol.infrastructure.orm_models import GameSnapshotRow
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


@pytest.mark.asyncio
async def test_repository_refuses_to_overwrite_a_mismatched_snapshot_version() -> None:
    sql_session = AsyncMock()
    sql_session.execute.side_effect = [
        SimpleNamespace(rowcount=1),
        SimpleNamespace(rowcount=0),
    ]
    sql_session.scalar.return_value = 9
    repository = SqlAlchemyGameSessionRepository(sql_session)
    aggregate = GameSession(
        session_id="session-1",
        player_id="player-1",
        scenario_id="scenario-1",
        scenario_version="1",
        phase="AWAITING_ACTION",
        turn_number=3,
        state_version=4,
        random_seed=42,
    )

    with pytest.raises(OptimisticLockError, match="snapshot version"):
        await repository.save_snapshot_and_events(
            aggregate,
            {"new": "state"},
            (),
            expected_state_version=4,
        )

    assert aggregate.state_version == 4
    assert sql_session.execute.await_count == 2
    sql_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_repository_loads_latest_snapshot_with_its_persisted_version() -> None:
    sql_session = AsyncMock()
    sql_session.get.return_value = SimpleNamespace(
        state_version=7,
        state_json={"schema_version": 1, "content_version": "demo-1"},
    )
    repository = SqlAlchemyGameSessionRepository(sql_session)

    snapshot = await repository.get_latest_snapshot("session-1")

    assert snapshot is not None
    assert snapshot.state_version == 7
    assert snapshot.state == {"schema_version": 1, "content_version": "demo-1"}
    sql_session.get.assert_awaited_once_with(GameSnapshotRow, "session-1")


@pytest.mark.asyncio
@pytest.mark.parametrize(("latest", "expected"), [(None, 1), (8, 9)])
async def test_repository_allocates_next_session_event_sequence(
    latest: int | None, expected: int
) -> None:
    sql_session = AsyncMock()
    sql_session.scalar.return_value = latest
    repository = SqlAlchemyGameSessionRepository(sql_session)

    assert await repository.next_event_sequence_no("session-1") == expected
    statement = sql_session.scalar.await_args.args[0]
    assert "max(domain_events.sequence_no)" in str(statement)


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


@pytest.mark.asyncio
async def test_unit_of_work_translates_only_the_idempotency_unique_constraint() -> None:
    session = FakeSession()
    session.commit.side_effect = IntegrityError(
        "INSERT turn_requests",
        {},
        Exception(
            1062,
            "Duplicate entry for key 'turn_requests.uq_turn_requests_session_client_request'",
        ),
    )
    uow = SqlAlchemyUnitOfWork(lambda: session)  # type: ignore[arg-type]

    with pytest.raises(ConcurrentTurnRequestError):
        async with uow:
            await uow.commit()

    session.rollback.assert_awaited_once()
    session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_unit_of_work_preserves_unrelated_integrity_errors() -> None:
    session = FakeSession()
    integrity_error = IntegrityError(
        "INSERT domain_events",
        {},
        Exception(1062, "Duplicate entry for key 'domain_events.PRIMARY'"),
    )
    session.commit.side_effect = integrity_error
    uow = SqlAlchemyUnitOfWork(lambda: session)  # type: ignore[arg-type]

    with pytest.raises(IntegrityError) as raised:
        async with uow:
            await uow.commit()

    assert raised.value is integrity_error
    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_unit_of_work_translates_session_creation_unique_constraint() -> None:
    session = FakeSession()
    session.commit.side_effect = IntegrityError(
        "INSERT game_sessions",
        {},
        Exception(
            1062,
            "Duplicate entry for key "
            "'game_sessions.uq_game_sessions_player_creation_request'",
        ),
    )
    uow = SqlAlchemyUnitOfWork(lambda: session)  # type: ignore[arg-type]

    with pytest.raises(ConcurrentSessionCreateError):
        async with uow:
            await uow.commit()

    session.rollback.assert_awaited_once()
    session.close.assert_awaited_once()
