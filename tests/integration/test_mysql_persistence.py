from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from deviation_protocol.application.action_context import TrustedResolutionContext
from deviation_protocol.application.errors import IdempotencyConflictError
from deviation_protocol.application.resolution import ResolutionStatus
from deviation_protocol.application.rule_resolver import DeterministicRuleResolver
from deviation_protocol.application.turn_orchestrator import FirstPhaseTurnOrchestrator
from deviation_protocol.domain.actions import ActionSubmission, ActionType
from deviation_protocol.domain.content import ContentCatalog
from deviation_protocol.domain.events import DomainEvent
from deviation_protocol.domain.models import GameSession
from deviation_protocol.domain.state import GameState, PlayerState
from deviation_protocol.infrastructure.content_loader import JsonContentCatalogLoader
from deviation_protocol.infrastructure.errors import OptimisticLockError
from deviation_protocol.infrastructure.orm_models import (
    DomainEventRow,
    GameSessionRow,
    GameSnapshotRow,
    TurnRequestRow,
)
from deviation_protocol.infrastructure.repositories import SqlAlchemyGameSessionRepository
from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


CONTENT_PACK = Path(__file__).parents[2] / "config" / "demo_content_pack.json"
FIXED_TIME = datetime(2026, 7, 19, 12, 30, tzinfo=timezone.utc)


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


def catalog_and_state() -> tuple[ContentCatalog, GameState]:
    catalog = JsonContentCatalogLoader(CONTENT_PACK).load()
    character = catalog.character("character.player.default")
    assert character is not None
    state = GameState(
        content_version=catalog.content_version,
        player=PlayerState.from_definition("integration-player", character),
    )
    return catalog, state


async def seed_snapshot(
    session_factory: async_sessionmaker[AsyncSession],
    session_id: str,
    state: GameState,
) -> None:
    async with session_factory.begin() as session:
        session.add(
            GameSnapshotRow(
                session_id=session_id,
                state_version=0,
                state_json=state.to_snapshot(),
            )
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_v1_snapshot_loads_through_pure_migration_while_v2_is_current(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    mysql_session_id: str,
) -> None:
    catalog, state = catalog_and_state()
    v1 = state.to_snapshot()
    v1["schema_version"] = 1
    v1.pop("scenario_runtime")
    async with mysql_session_factory.begin() as session:
        session.add(
            GameSnapshotRow(
                session_id=mysql_session_id,
                state_version=0,
                state_json=v1,
            )
        )
    service = FirstPhaseTurnOrchestrator(
        DeterministicRuleResolver(),
        lambda: SqlAlchemyUnitOfWork(mysql_session_factory),
        catalog,
    )
    response = await service.handle(
        ActionSubmission(
            session_id=mysql_session_id,
            turn_id="turn-v1-snapshot",
            client_request_id=f"it-v1-{uuid4().hex}",
            action_type=ActionType.INSPECT_STATUS,
        )
    )
    assert response.resolution_kind is ResolutionStatus.RESOLVED_LOCAL
    assert GameState.from_snapshot(v1, catalog=catalog).schema_version == 2
    assert state.to_snapshot()["schema_version"] == 2


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
    assert game_session.state_version == 0


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
    catalog, state = catalog_and_state()
    await seed_snapshot(mysql_session_factory, mysql_session_id, state)
    submission = ActionSubmission(
        session_id=mysql_session_id,
        turn_id="turn-1",
        client_request_id=f"it-request-{uuid4().hex}",
        action_type=ActionType.INSPECT_STATUS,
    )
    business_entered = asyncio.Event()
    release_business = asyncio.Event()
    business_calls = 0

    class BlockingResolver:
        async def resolve(
            self,
            trusted_context: TrustedResolutionContext,
            loaded_state: GameState,
            loaded_catalog: ContentCatalog,
        ):
            nonlocal business_calls
            business_calls += 1
            business_entered.set()
            await release_business.wait()
            return await DeterministicRuleResolver().resolve(
                trusted_context, loaded_state, loaded_catalog
            )

    uow_factory: Callable[[], SqlAlchemyUnitOfWork] = lambda: SqlAlchemyUnitOfWork(
        mysql_session_factory
    )
    orchestrator = FirstPhaseTurnOrchestrator(
        BlockingResolver(),
        uow_factory,
        catalog,
        clock=lambda: FIXED_TIME,
        event_id_generator=lambda: "unused-event-id",
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


@pytest.mark.integration
@pytest.mark.asyncio
async def test_orchestrator_mutation_persists_snapshot_events_version_and_response_atomically(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    mysql_session_id: str,
) -> None:
    catalog, state = catalog_and_state()
    state.grant_item(catalog, "item.training_sword", instance_id="it-sword-1")
    await seed_snapshot(mysql_session_factory, mysql_session_id, state)
    action = ActionSubmission(
        session_id=mysql_session_id,
        turn_id="turn-equip",
        client_request_id=f"it-request-{uuid4().hex}",
        action_type=ActionType.EQUIP,
        item_instance_id="it-sword-1",
        equipment_slot_id="hand.main",
    )
    service = FirstPhaseTurnOrchestrator(
        DeterministicRuleResolver(),
        lambda: SqlAlchemyUnitOfWork(mysql_session_factory),
        catalog,
        clock=lambda: FIXED_TIME,
        event_id_generator=lambda: "it-fixed-equip-event",
    )

    response = await service.handle(action)

    async with mysql_session_factory() as session:
        session_row = await session.get(GameSessionRow, mysql_session_id)
        snapshot_row = await session.get(GameSnapshotRow, mysql_session_id)
        event_row = await session.get(DomainEventRow, "it-fixed-equip-event")
        request_row = await session.scalar(
            select(TurnRequestRow).where(
                TurnRequestRow.session_id == mysql_session_id,
                TurnRequestRow.client_request_id == action.client_request_id,
            )
        )

    assert response.resulting_state_version == 1
    assert session_row is not None and session_row.state_version == 1
    assert snapshot_row is not None and snapshot_row.state_version == 1
    restored = GameState.from_snapshot(snapshot_row.state_json, catalog=catalog)
    equipment = restored.player.inventory.items["it-sword-1"].equipment
    assert equipment is not None and equipment.equipped_slot == "hand.main"
    assert event_row is not None and event_row.sequence_no == 1
    assert event_row.turn_id == action.turn_id
    assert request_row is not None and request_row.response_json == response.to_persistence()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_orchestrator_event_insert_failure_rolls_back_all_turn_writes(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    mysql_session_id: str,
) -> None:
    catalog, state = catalog_and_state()
    state.grant_item(catalog, "item.training_sword", instance_id="it-sword-rollback")
    await seed_snapshot(mysql_session_factory, mysql_session_id, state)
    duplicate_event_id = f"it-existing-{uuid4().hex}"
    async with mysql_session_factory.begin() as session:
        session.add(
            DomainEventRow(
                event_id=duplicate_event_id,
                session_id=mysql_session_id,
                turn_id="turn-old",
                sequence_no=1,
                event_type="ExistingEvent",
                payload_json={"existing": True},
                occurred_at=FIXED_TIME,
            )
        )
    action = ActionSubmission(
        session_id=mysql_session_id,
        turn_id="turn-rollback",
        client_request_id=f"it-request-{uuid4().hex}",
        action_type=ActionType.EQUIP,
        item_instance_id="it-sword-rollback",
        equipment_slot_id="hand.main",
    )
    service = FirstPhaseTurnOrchestrator(
        DeterministicRuleResolver(),
        lambda: SqlAlchemyUnitOfWork(mysql_session_factory),
        catalog,
        clock=lambda: FIXED_TIME,
        event_id_generator=lambda: duplicate_event_id,
    )

    with pytest.raises(IntegrityError):
        await service.handle(action)

    async with mysql_session_factory() as session:
        session_row = await session.get(GameSessionRow, mysql_session_id)
        snapshot_row = await session.get(GameSnapshotRow, mysql_session_id)
        event_count = await session.scalar(
            select(func.count())
            .select_from(DomainEventRow)
            .where(DomainEventRow.session_id == mysql_session_id)
        )
        request_count = await session.scalar(
            select(func.count())
            .select_from(TurnRequestRow)
            .where(TurnRequestRow.session_id == mysql_session_id)
        )

    assert session_row is not None and session_row.state_version == 0
    assert snapshot_row is not None and snapshot_row.state_version == 0
    restored = GameState.from_snapshot(snapshot_row.state_json, catalog=catalog)
    equipment = restored.player.inventory.items["it-sword-rollback"].equipment
    assert equipment is not None and equipment.equipped_slot is None
    assert event_count == 1
    assert request_count == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_different_client_requests_are_serialized_by_real_session_row_lock(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    mysql_session_id: str,
) -> None:
    catalog, state = catalog_and_state()
    await seed_snapshot(mysql_session_factory, mysql_session_id, state)
    entered = asyncio.Event()
    release = asyncio.Event()
    calls = 0

    class BlockingFirstResolver:
        async def resolve(
            self,
            trusted_context: TrustedResolutionContext,
            loaded_state: GameState,
            loaded_catalog: ContentCatalog,
        ):
            nonlocal calls
            calls += 1
            if calls == 1:
                entered.set()
                await release.wait()
            return await DeterministicRuleResolver().resolve(
                trusted_context, loaded_state, loaded_catalog
            )

    service = FirstPhaseTurnOrchestrator(
        BlockingFirstResolver(),
        lambda: SqlAlchemyUnitOfWork(mysql_session_factory),
        catalog,
    )
    first_action = ActionSubmission(
        session_id=mysql_session_id,
        turn_id="turn-query",
        client_request_id=f"it-a-{uuid4().hex}",
        action_type=ActionType.INSPECT_STATUS,
    )
    second_action = first_action.model_copy(
        update={"client_request_id": f"it-b-{uuid4().hex}"}
    )

    first = asyncio.create_task(service.handle(first_action))
    await asyncio.wait_for(entered.wait(), timeout=2)
    second = asyncio.create_task(service.handle(second_action))
    await asyncio.sleep(0.1)
    assert calls == 1
    assert not second.done()
    release.set()
    await asyncio.gather(first, second)

    assert calls == 2
    async with mysql_session_factory() as session:
        request_count = await session.scalar(
            select(func.count())
            .select_from(TurnRequestRow)
            .where(TurnRequestRow.session_id == mysql_session_id)
        )
    assert request_count == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_same_mysql_idempotency_key_replays_same_action_and_rejects_a_different_action(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    mysql_session_id: str,
) -> None:
    catalog, state = catalog_and_state()
    await seed_snapshot(mysql_session_factory, mysql_session_id, state)
    service = FirstPhaseTurnOrchestrator(
        DeterministicRuleResolver(),
        lambda: SqlAlchemyUnitOfWork(mysql_session_factory),
        catalog,
    )
    original = ActionSubmission(
        session_id=mysql_session_id,
        turn_id="turn-idempotency",
        client_request_id=f"it-shared-{uuid4().hex}",
        action_type=ActionType.INSPECT_STATUS,
    )
    conflicting = ActionSubmission(
        session_id=mysql_session_id,
        turn_id=original.turn_id,
        client_request_id=original.client_request_id,
        action_type=ActionType.EXPLORE,
        description="我查看走廊。",
    )

    first = await service.handle(original)
    replayed = await service.handle(original)
    with pytest.raises(IdempotencyConflictError):
        await service.handle(conflicting)

    async with mysql_session_factory() as session:
        requests = (
            await session.scalars(
                select(TurnRequestRow).where(
                    TurnRequestRow.session_id == mysql_session_id
                )
            )
        ).all()
    assert first == replayed
    assert len(requests) == 1
    assert requests[0].action_signature == original.action_signature()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_different_mysql_actions_reusing_one_key_resolve_once_then_conflict(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    mysql_session_id: str,
) -> None:
    catalog, state = catalog_and_state()
    await seed_snapshot(mysql_session_factory, mysql_session_id, state)
    entered = asyncio.Event()
    release = asyncio.Event()
    resolver_calls = 0

    class BlockingResolver:
        async def resolve(
            self,
            trusted_context: TrustedResolutionContext,
            loaded_state: GameState,
            loaded_catalog: ContentCatalog,
        ):
            nonlocal resolver_calls
            resolver_calls += 1
            entered.set()
            await release.wait()
            return await DeterministicRuleResolver().resolve(
                trusted_context, loaded_state, loaded_catalog
            )

    service = FirstPhaseTurnOrchestrator(
        BlockingResolver(),
        lambda: SqlAlchemyUnitOfWork(mysql_session_factory),
        catalog,
    )
    first_action = ActionSubmission(
        session_id=mysql_session_id,
        turn_id="turn-concurrent-conflict",
        client_request_id=f"it-conflict-{uuid4().hex}",
        action_type=ActionType.INSPECT_STATUS,
    )
    conflicting_action = ActionSubmission(
        session_id=mysql_session_id,
        turn_id=first_action.turn_id,
        client_request_id=first_action.client_request_id,
        action_type=ActionType.EXPLORE,
        description="我选择另一条路。",
    )

    first_task = asyncio.create_task(service.handle(first_action))
    await asyncio.wait_for(entered.wait(), timeout=2)
    second_task = asyncio.create_task(service.handle(conflicting_action))
    await asyncio.sleep(0.1)
    assert not second_task.done()
    release.set()
    await first_task
    with pytest.raises(IdempotencyConflictError):
        await second_task

    async with mysql_session_factory() as session:
        request_count = await session.scalar(
            select(func.count())
            .select_from(TurnRequestRow)
            .where(TurnRequestRow.session_id == mysql_session_id)
        )
    assert resolver_calls == 1
    assert request_count == 1


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("action_type", "action_fields", "expected_status"),
    [
        (ActionType.INSPECT_STATUS, {}, ResolutionStatus.RESOLVED_LOCAL),
        (
            ActionType.CUSTOM,
            {"description": "啊啊啊啊啊啊啊"},
            ResolutionStatus.REJECTED_LOCAL,
        ),
        (
            ActionType.EXPLORE,
            {"description": "我仔细查看走廊。"},
            ResolutionStatus.NARRATIVE_REQUIRED,
        ),
    ],
)
async def test_non_state_mysql_results_are_committed_and_idempotently_replayed(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    mysql_session_id: str,
    action_type: ActionType,
    action_fields: dict[str, str],
    expected_status: ResolutionStatus,
) -> None:
    catalog, state = catalog_and_state()
    await seed_snapshot(mysql_session_factory, mysql_session_id, state)
    action = ActionSubmission(
        session_id=mysql_session_id,
        turn_id=f"turn-{action_type.value.lower()}",
        client_request_id=f"it-non-state-{uuid4().hex}",
        action_type=action_type,
        **action_fields,
    )
    service = FirstPhaseTurnOrchestrator(
        DeterministicRuleResolver(),
        lambda: SqlAlchemyUnitOfWork(mysql_session_factory),
        catalog,
    )

    first = await service.handle(action)
    replayed = await service.handle(action)

    async with mysql_session_factory() as session:
        session_row = await session.get(GameSessionRow, mysql_session_id)
        snapshot_row = await session.get(GameSnapshotRow, mysql_session_id)
        event_count = await session.scalar(
            select(func.count())
            .select_from(DomainEventRow)
            .where(DomainEventRow.session_id == mysql_session_id)
        )
        request_count = await session.scalar(
            select(func.count())
            .select_from(TurnRequestRow)
            .where(TurnRequestRow.session_id == mysql_session_id)
        )

    assert first == replayed
    assert first.resolution_kind is expected_status
    assert first.resulting_state_version == 0
    assert first.state_changed is False
    assert session_row is not None and session_row.state_version == 0
    assert snapshot_row is not None and snapshot_row.state_version == 0
    assert event_count == 0
    assert request_count == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_mysql_snapshot_serialization_failure_rolls_back_session_and_events(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    mysql_session_id: str,
) -> None:
    game_session = aggregate(mysql_session_id)
    domain_event = event(mysql_session_id)

    with pytest.raises(StatementError):
        async with SqlAlchemyUnitOfWork(mysql_session_factory) as uow:
            await uow.sessions.save_snapshot_and_events(
                game_session,
                {"not_json": object()},
                (domain_event,),
                expected_state_version=0,
            )
            await uow.commit()

    async with mysql_session_factory() as session:
        session_row = await session.get(GameSessionRow, mysql_session_id)
        snapshot_row = await session.get(GameSnapshotRow, mysql_session_id)
        stored_event = await session.get(DomainEventRow, domain_event.event_id)
    assert session_row is not None and session_row.state_version == 0
    assert snapshot_row is None
    assert stored_event is None
    assert game_session.state_version == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_mysql_turn_response_insert_failure_rolls_back_mutation(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    mysql_session_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    catalog, state = catalog_and_state()
    state.grant_item(catalog, "item.training_sword", instance_id="it-response-failure")
    await seed_snapshot(mysql_session_factory, mysql_session_id, state)
    duplicate_request_uuid = uuid4()
    async with mysql_session_factory.begin() as session:
        session.add(
            TurnRequestRow(
                request_id=str(duplicate_request_uuid),
                session_id=mysql_session_id,
                turn_id="turn-existing-response",
                client_request_id=f"it-existing-{uuid4().hex}",
                action_signature="a" * 64,
                route="REJECT_LOCAL",
                request_json={"existing": True},
                response_json={"existing": True},
                error_text=None,
            )
        )
    monkeypatch.setattr(
        "deviation_protocol.infrastructure.repositories.uuid4",
        lambda: duplicate_request_uuid,
    )
    action = ActionSubmission(
        session_id=mysql_session_id,
        turn_id="turn-response-failure",
        client_request_id=f"it-new-{uuid4().hex}",
        action_type=ActionType.EQUIP,
        item_instance_id="it-response-failure",
        equipment_slot_id="hand.main",
    )
    service = FirstPhaseTurnOrchestrator(
        DeterministicRuleResolver(),
        lambda: SqlAlchemyUnitOfWork(mysql_session_factory),
        catalog,
        clock=lambda: FIXED_TIME,
        event_id_generator=lambda: "it-response-failure-event",
    )

    with pytest.raises(IntegrityError):
        await service.handle(action)

    async with mysql_session_factory() as session:
        session_row = await session.get(GameSessionRow, mysql_session_id)
        snapshot_row = await session.get(GameSnapshotRow, mysql_session_id)
        new_request = await session.scalar(
            select(TurnRequestRow).where(
                TurnRequestRow.session_id == mysql_session_id,
                TurnRequestRow.client_request_id == action.client_request_id,
            )
        )
        stored_event = await session.get(
            DomainEventRow, "it-response-failure-event"
        )
    assert session_row is not None and session_row.state_version == 0
    assert snapshot_row is not None and snapshot_row.state_version == 0
    restored = GameState.from_snapshot(snapshot_row.state_json, catalog=catalog)
    equipment = restored.player.inventory.items["it-response-failure"].equipment
    assert equipment is not None and equipment.equipped_slot is None
    assert new_request is None
    assert stored_event is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_mysql_snapshot_version_conflict_does_not_overwrite_newer_snapshot(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    mysql_session_id: str,
) -> None:
    async with mysql_session_factory.begin() as session:
        session.add(
            GameSnapshotRow(
                session_id=mysql_session_id,
                state_version=9,
                state_json={"newer": True},
            )
        )
    game_session = aggregate(mysql_session_id)

    with pytest.raises(OptimisticLockError, match="snapshot version"):
        async with SqlAlchemyUnitOfWork(mysql_session_factory) as uow:
            await uow.sessions.save_snapshot_and_events(
                game_session,
                {"older": True},
                (event(mysql_session_id),),
                expected_state_version=0,
            )

    async with mysql_session_factory() as session:
        session_row = await session.get(GameSessionRow, mysql_session_id)
        snapshot_row = await session.get(GameSnapshotRow, mysql_session_id)
        event_count = await session.scalar(
            select(func.count())
            .select_from(DomainEventRow)
            .where(DomainEventRow.session_id == mysql_session_id)
        )
    assert session_row is not None and session_row.state_version == 0
    assert snapshot_row is not None and snapshot_row.state_version == 9
    assert snapshot_row.state_json == {"newer": True}
    assert event_count == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_two_mysql_mutations_increment_versions_once_and_keep_event_sequence(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    mysql_session_id: str,
) -> None:
    catalog, state = catalog_and_state()
    state.grant_item(catalog, "item.training_sword", instance_id="it-two-turn-sword")
    await seed_snapshot(mysql_session_factory, mysql_session_id, state)
    generated_ids = iter(["it-sequence-equip", "it-sequence-unequip"])
    service = FirstPhaseTurnOrchestrator(
        DeterministicRuleResolver(),
        lambda: SqlAlchemyUnitOfWork(mysql_session_factory),
        catalog,
        clock=lambda: FIXED_TIME,
        event_id_generator=generated_ids.__next__,
    )
    equip = ActionSubmission(
        session_id=mysql_session_id,
        turn_id="turn-sequence-1",
        client_request_id=f"it-sequence-a-{uuid4().hex}",
        action_type=ActionType.EQUIP,
        item_instance_id="it-two-turn-sword",
        equipment_slot_id="hand.main",
    )
    unequip = ActionSubmission(
        session_id=mysql_session_id,
        turn_id="turn-sequence-2",
        client_request_id=f"it-sequence-b-{uuid4().hex}",
        action_type=ActionType.UNEQUIP,
        item_instance_id="it-two-turn-sword",
    )

    first = await service.handle(equip)
    second = await service.handle(unequip)

    async with mysql_session_factory() as session:
        session_row = await session.get(GameSessionRow, mysql_session_id)
        snapshot_row = await session.get(GameSnapshotRow, mysql_session_id)
        events = (
            await session.scalars(
                select(DomainEventRow)
                .where(DomainEventRow.session_id == mysql_session_id)
                .order_by(DomainEventRow.sequence_no)
            )
        ).all()
        request_count = await session.scalar(
            select(func.count())
            .select_from(TurnRequestRow)
            .where(TurnRequestRow.session_id == mysql_session_id)
        )

    assert [first.resulting_state_version, second.resulting_state_version] == [1, 2]
    assert session_row is not None and session_row.state_version == 2
    assert snapshot_row is not None and snapshot_row.state_version == 2
    assert [item.sequence_no for item in events] == [1, 2]
    assert [item.event_type for item in events] == ["ItemEquipped", "ItemUnequipped"]
    assert [item.turn_id for item in events] == [equip.turn_id, unequip.turn_id]
    assert events[0].payload_json == {
        "item_instance_id": "it-two-turn-sword",
        "equipment_slot_id": "hand.main",
    }
    assert request_count == 2
