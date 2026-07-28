from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.exc import IntegrityError

from deviation_protocol.application.errors import (
    ConcurrentSessionCreateError,
    ConcurrentTurnRequestError,
)
from deviation_protocol.application.action_gateway import ActionRoute
from deviation_protocol.domain.actions import ActionSubmission, ActionType
from deviation_protocol.domain.models import GameSession
from deviation_protocol.domain.events import DomainEvent
from deviation_protocol.domain.persisted_events import PersistedEventReceipt
from deviation_protocol.infrastructure.orm_models import GameSnapshotRow
from deviation_protocol.infrastructure.errors import OptimisticLockError
from deviation_protocol.infrastructure.repositories import (
    SqlAlchemyControllerBindingRegistryRepository,
    SqlAlchemyGameSessionRepository,
    SqlAlchemyPlayerCharacterCreationReceiptRepository,
    SqlAlchemyPlayerCharacterMutationReceiptRepository,
    SqlAlchemyPlayerCharacterRepository,
)
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


@pytest.mark.asyncio
async def test_repository_returns_receipt_only_after_event_insert_flush() -> None:
    sql_session = AsyncMock()
    sql_session.add_all = Mock()
    repository = SqlAlchemyGameSessionRepository(sql_session)
    event = DomainEvent(
        event_id="event-1",
        session_id="session-1",
        turn_id="turn-1",
        sequence_no=3,
        event_type="ScenarioStarted",
        payload={"scenario_id": "scenario-1"},
        occurred_at=datetime(2026, 7, 20, tzinfo=timezone.utc),
    )

    receipts = await repository.persist_events((event,), state_version=4)

    sql_session.add_all.assert_called_once()
    sql_session.flush.assert_awaited_once()
    assert len(receipts) == 1
    receipt = receipts[0]
    assert receipt.is_authentic()
    assert (
        receipt.session_id,
        receipt.event_id,
        receipt.sequence_no,
        receipt.turn_id,
        receipt.state_version,
        receipt.event_type,
    ) == ("session-1", "event-1", 3, "turn-1", 4, "ScenarioStarted")
    with pytest.raises(TypeError):
        PersistedEventReceipt()  # type: ignore[call-arg]


@pytest.mark.asyncio
async def test_event_flush_failure_returns_no_receipt_capability() -> None:
    sql_session = AsyncMock()
    sql_session.add_all = Mock()
    sql_session.flush.side_effect = RuntimeError("simulated event flush failure")
    repository = SqlAlchemyGameSessionRepository(sql_session)
    event = DomainEvent(
        event_id="event-1",
        session_id="session-1",
        turn_id="turn-1",
        sequence_no=1,
        event_type="ScenarioStarted",
        payload={},
        occurred_at=datetime(2026, 7, 20, tzinfo=timezone.utc),
    )

    with pytest.raises(RuntimeError, match="flush failure"):
        await repository.persist_events((event,), state_version=0)
    sql_session.flush.assert_awaited_once()


class FakeSession:
    def __init__(self) -> None:
        self.add = Mock()
        self.begin = Mock()
        self.execute = AsyncMock()
        self.flush = AsyncMock()
        self.get = AsyncMock()
        self.scalar = AsyncMock()
        self.commit = AsyncMock()
        self.rollback = AsyncMock()
        self.close = AsyncMock()


@pytest.mark.asyncio
async def test_unit_of_work_exposes_all_player_character_repositories_on_same_session_without_explicit_begin() -> None:
    session = FakeSession()
    uow = SqlAlchemyUnitOfWork(lambda: session)  # type: ignore[arg-type]

    async with uow:
        assert isinstance(
            uow.controller_bindings,
            SqlAlchemyControllerBindingRegistryRepository,
        )
        assert isinstance(
            uow.player_characters,
            SqlAlchemyPlayerCharacterRepository,
        )
        assert isinstance(
            uow.creation_receipts,
            SqlAlchemyPlayerCharacterCreationReceiptRepository,
        )
        assert isinstance(
            uow.mutation_receipts,
            SqlAlchemyPlayerCharacterMutationReceiptRepository,
        )
        assert (
            uow.controller_bindings._session
            is uow.player_characters._session
            is uow.creation_receipts._session
            is uow.mutation_receipts._session
            is session
        )
        session.begin.assert_not_called()
        session.add.assert_not_called()
        session.execute.assert_not_awaited()
        session.flush.assert_not_awaited()
        session.get.assert_not_awaited()
        session.scalar.assert_not_awaited()
        session.commit.assert_not_awaited()


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
async def test_unit_of_work_rolls_back_and_closes_on_cancellation() -> None:
    session = FakeSession()
    uow = SqlAlchemyUnitOfWork(lambda: session)  # type: ignore[arg-type]

    with pytest.raises(asyncio.CancelledError):
        async with uow:
            raise asyncio.CancelledError

    session.rollback.assert_awaited_once()
    session.close.assert_awaited_once()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_unit_of_work_translates_only_the_idempotency_unique_constraint() -> None:
    session = FakeSession()
    session.flush.side_effect = IntegrityError(
        "INSERT turn_requests",
        {},
        Exception(1062, "opaque duplicate"),
    )
    uow = SqlAlchemyUnitOfWork(lambda: session)  # type: ignore[arg-type]

    with pytest.raises(ConcurrentTurnRequestError):
        async with uow:
            await uow.turn_requests.add(
                ActionSubmission(
                    session_id="session-1",
                    turn_id="turn-1",
                    client_request_id="request-1",
                    action_type=ActionType.INSPECT_STATUS,
                ),
                "a" * 64,
                ActionRoute.RESOLVE_LOCAL,
                {},
            )

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
    session.flush.side_effect = IntegrityError(
        "INSERT game_sessions",
        {},
        Exception(1062, "opaque duplicate"),
    )
    uow = SqlAlchemyUnitOfWork(lambda: session)  # type: ignore[arg-type]

    with pytest.raises(ConcurrentSessionCreateError):
        async with uow:
            await uow.sessions.add_initial(
                GameSession(
                    session_id="session-1",
                    player_id="player-1",
                    scenario_id="scenario-1",
                    scenario_version="1",
                    phase="AWAITING_ACTION",
                    turn_number=0,
                    state_version=0,
                    random_seed=42,
                ),
                character_definition_id="character.player.default",
                creation_client_request_id="create-1",
                state={},
                created_at=datetime(2026, 7, 19, tzinfo=timezone.utc),
            )

    session.rollback.assert_awaited_once()
    session.close.assert_awaited_once()
