from __future__ import annotations

import asyncio
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from deviation_protocol.application.action_context import TrustedResolutionContext
from deviation_protocol.application.errors import (
    CandidateStateInvalidError,
    ConcurrentTurnRequestError,
    IdempotencyConflictError,
    SessionNotFoundError,
    SnapshotContentVersionMismatchError,
    SnapshotInvalidError,
    SnapshotNotFoundError,
    SnapshotSchemaVersionMismatchError,
    SnapshotSessionMismatchError,
    SnapshotStateVersionMismatchError,
    StoredTurnResponseInvalidError,
    UnsupportedResolutionError,
)
from deviation_protocol.application.ports import PersistedSnapshot, PersistedTurnRequest
from deviation_protocol.application.resolution import (
    PlayerFeedback,
    ResolutionResult,
    ResolutionStatus,
)
from deviation_protocol.application.rule_resolver import DeterministicRuleResolver
from deviation_protocol.application.scenario_event_bridge import (
    bind_public_decision_frame,
)
from deviation_protocol.application.story_director import (
    DeterministicStoryDirector,
    StoryDirectorError,
)
from deviation_protocol.application.turn_orchestrator import FirstPhaseTurnOrchestrator
from deviation_protocol.application.turn_response import TurnResponse
from deviation_protocol.domain.actions import ActionSubmission, ActionType
from deviation_protocol.domain.content import ContentCatalog
from deviation_protocol.domain.events import DomainEvent, DomainEventDraft
from deviation_protocol.domain.models import GameSession
from deviation_protocol.domain.scenario import EndingStatus, ScenarioCatalog
from deviation_protocol.domain.state import GameState, PlayerState
from deviation_protocol.infrastructure.content_loader import JsonContentCatalogLoader
from deviation_protocol.infrastructure.scenario_loader import JsonScenarioCatalogLoader
from deviation_protocol.infrastructure.errors import OptimisticLockError


CONTENT_PACK = Path(__file__).parents[2] / "config" / "demo_content_pack.json"
SCENARIO_PACK = (
    Path(__file__).parents[2]
    / "config"
    / "scenarios"
    / "death_certificate_v1.json"
)
FIXED_TIME = datetime(2026, 7, 19, 12, 30, tzinfo=timezone.utc)


@pytest.fixture
def catalog() -> ContentCatalog:
    return JsonContentCatalogLoader(CONTENT_PACK).load()


def make_state(catalog: ContentCatalog) -> GameState:
    character = catalog.character("character.player.default")
    assert character is not None
    return GameState(
        content_version=catalog.content_version,
        player=PlayerState.from_definition("player-1", character),
    )


def submission(action_type: ActionType, **overrides: object) -> ActionSubmission:
    values: dict[str, object] = {
        "session_id": "session-1",
        "turn_id": "turn-1",
        "client_request_id": f"request-{action_type.value.lower()}",
        "action_type": action_type,
    }
    values.update(overrides)
    return ActionSubmission(**values)


def current_public_decision_id(
    state: GameState,
    scenario_catalog: ScenarioCatalog,
    *,
    state_version: int = 4,
) -> str:
    definition = scenario_catalog.scenarios[0]
    frame = bind_public_decision_frame(
        DeterministicStoryDirector().plan_frame(state, definition),
        session_id="session-1",
        state_version=state_version,
        scenario_content_version=definition.content_version,
    )
    assert frame.decision_id is not None
    return frame.decision_id


class FakeStore:
    def __init__(
        self,
        state: GameState | None,
        *,
        state_version: int = 4,
        session_exists: bool = True,
    ) -> None:
        self.session = (
            GameSession(
                session_id="session-1",
                player_id="player-1",
                scenario_id="scenario-1",
                scenario_version="1",
                phase="AWAITING_ACTION",
                turn_number=1,
                state_version=state_version,
                random_seed=42,
            )
            if session_exists
            else None
        )
        self.snapshot = (
            PersistedSnapshot(state_version, deepcopy(state.to_snapshot()))
            if state is not None
            else None
        )
        self.requests: dict[tuple[str, str], PersistedTurnRequest] = {}
        self.events: list[DomainEvent] = []
        self.lock = asyncio.Lock()
        self.calls: list[str] = []
        self.commits = 0
        self.rollbacks = 0
        self.fail_snapshot = False
        self.fail_event = False
        self.fail_turn_request = False
        self.optimistic_conflict = False
        self.concurrent_winner: PersistedTurnRequest | None = None


class FakeSessionRepository:
    def __init__(self, store: FakeStore, uow: FakeUnitOfWork) -> None:
        self.store = store
        self.uow = uow

    async def lock_for_turn(self, session_id: str) -> bool:
        self.store.calls.append(f"lock:{session_id}")
        await self.store.lock.acquire()
        self.uow.lock_acquired = True
        return self.store.session is not None and self.store.session.session_id == session_id

    async def get(self, session_id: str) -> GameSession | None:
        self.store.calls.append(f"session:{session_id}")
        if self.store.session is None or self.store.session.session_id != session_id:
            return None
        return replace(self.store.session)

    async def get_latest_snapshot(self, session_id: str) -> PersistedSnapshot | None:
        self.store.calls.append(f"snapshot:{session_id}")
        if self.store.snapshot is None:
            return None
        return PersistedSnapshot(
            self.store.snapshot.state_version,
            deepcopy(dict(self.store.snapshot.state)),
        )

    async def next_event_sequence_no(self, session_id: str) -> int:
        self.store.calls.append(f"sequence:{session_id}")
        return max((event.sequence_no for event in self.store.events), default=0) + 1

    async def save_snapshot_and_events(
        self,
        game_session: GameSession,
        state: Mapping[str, Any],
        events: tuple[DomainEvent, ...],
        expected_state_version: int,
    ) -> None:
        self.store.calls.append("save-state")
        if self.store.optimistic_conflict:
            raise OptimisticLockError("simulated conflict")
        if self.store.fail_snapshot:
            raise RuntimeError("simulated snapshot failure")
        self.uow.pending_state = (
            expected_state_version + 1,
            deepcopy(dict(state)),
            tuple(events),
        )
        if self.store.fail_event:
            raise RuntimeError("simulated event failure")


class FakeTurnRequestRepository:
    def __init__(self, store: FakeStore, uow: FakeUnitOfWork) -> None:
        self.store = store
        self.uow = uow

    async def get_by_client_request_id(
        self, session_id: str, client_request_id: str
    ) -> PersistedTurnRequest | None:
        self.store.calls.append(f"request:{session_id}:{client_request_id}")
        value = self.store.requests.get((session_id, client_request_id))
        return deepcopy(value) if value is not None else None

    async def add(
        self,
        action: ActionSubmission,
        action_signature: str,
        route: object,
        response: Mapping[str, Any],
    ) -> None:
        self.store.calls.append("add-response")
        if self.store.fail_turn_request:
            raise RuntimeError("simulated turn response failure")
        self.uow.pending_request = (
            (action.session_id, action.client_request_id),
            PersistedTurnRequest(
                turn_id=action.turn_id,
                action_signature=action_signature,
                response=deepcopy(dict(response)),
            ),
        )


class FakeUnitOfWork:
    def __init__(self, store: FakeStore) -> None:
        self.store = store
        self.sessions = FakeSessionRepository(store, self)
        self.turn_requests = FakeTurnRequestRepository(store, self)
        self.pending_state: tuple[int, dict[str, Any], tuple[DomainEvent, ...]] | None = None
        self.pending_request: tuple[tuple[str, str], PersistedTurnRequest] | None = None
        self.lock_acquired = False
        self.committed = False

    async def __aenter__(self) -> FakeUnitOfWork:
        return self

    async def __aexit__(self, *args: object) -> None:
        if not self.committed:
            self.store.rollbacks += 1
        if self.lock_acquired:
            self.store.lock.release()

    async def commit(self) -> None:
        self.store.calls.append("commit")
        if self.store.concurrent_winner is not None:
            assert self.pending_request is not None
            key, _ = self.pending_request
            self.store.requests[key] = deepcopy(self.store.concurrent_winner)
            self.store.concurrent_winner = None
            raise ConcurrentTurnRequestError
        if self.pending_state is not None:
            version, state, events = self.pending_state
            assert self.store.session is not None
            self.store.session.state_version = version
            self.store.snapshot = PersistedSnapshot(version, deepcopy(state))
            self.store.events.extend(events)
        if self.pending_request is not None:
            key, request = self.pending_request
            self.store.requests[key] = deepcopy(request)
        self.store.commits += 1
        self.committed = True

    async def rollback(self) -> None:
        self.pending_state = None
        self.pending_request = None


class SpyResolver:
    def __init__(self, delegate: object | None = None) -> None:
        self.delegate = delegate or DeterministicRuleResolver()
        self.calls = 0
        self.contexts: list[TrustedResolutionContext] = []
        self.entered = asyncio.Event()
        self.release: asyncio.Event | None = None

    async def resolve(
        self,
        trusted_context: TrustedResolutionContext,
        state: GameState,
        catalog: ContentCatalog,
    ) -> ResolutionResult:
        self.calls += 1
        self.contexts.append(trusted_context)
        self.entered.set()
        if self.release is not None:
            await self.release.wait()
        resolver = self.delegate
        return await resolver.resolve(trusted_context, state, catalog)  # type: ignore[attr-defined]


class ResultResolver:
    def __init__(self, result: ResolutionResult | None = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.calls = 0

    async def resolve(self, *args: object) -> ResolutionResult:
        self.calls += 1
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


def orchestrator(
    store: FakeStore,
    catalog: ContentCatalog,
    resolver: object | None = None,
    *,
    ids: list[str] | None = None,
    scenario_catalog: ScenarioCatalog | None = None,
    story_director: DeterministicStoryDirector | None = None,
) -> FirstPhaseTurnOrchestrator:
    event_ids = iter(ids or [f"event-{index}" for index in range(1, 20)])
    return FirstPhaseTurnOrchestrator(
        resolver=resolver or DeterministicRuleResolver(),  # type: ignore[arg-type]
        uow_factory=lambda: FakeUnitOfWork(store),
        catalog=catalog,
        scenario_catalog=scenario_catalog,
        story_director=story_director or DeterministicStoryDirector(),
        clock=lambda: FIXED_TIME,
        event_id_generator=lambda: next(event_ids),
    )


def scenario_state_and_store(
    scenario_catalog: ScenarioCatalog,
) -> tuple[GameState, FakeStore]:
    definition = scenario_catalog.scenario("death_certificate")
    character = scenario_catalog.content_catalog.character(
        "character.death_certificate.investigator"
    )
    assert definition is not None and character is not None
    state = GameState(
        content_version=scenario_catalog.content_version,
        player=PlayerState.from_definition("player-1", character),
    )
    for index, reference in enumerate(definition.npc_references, start=1):
        state.spawn_npc(
            scenario_catalog.content_catalog,
            reference.npc_definition_id,
            f"scenario-npc-{index}",
        )
    state = DeterministicStoryDirector().start_scenario(
        state, definition
    ).candidate_state
    store = FakeStore(state)
    assert store.session is not None
    store.session.scenario_id = definition.scenario_id
    store.session.scenario_version = definition.content_version
    return state, store


class SpyStoryDirector(DeterministicStoryDirector):
    def __init__(self) -> None:
        super().__init__()
        self.plan_calls = 0
        self.advance_calls = 0

    def plan_frame(self, *args: object, **kwargs: object):
        self.plan_calls += 1
        return super().plan_frame(*args, **kwargs)  # type: ignore[arg-type]

    def advance_after_verified_result(self, *args: object, **kwargs: object):
        self.advance_calls += 1
        return super().advance_after_verified_result(  # type: ignore[arg-type]
            *args, **kwargs
        )


@pytest.mark.asyncio
async def test_missing_session_is_an_explicit_application_error(catalog: ContentCatalog) -> None:
    store = FakeStore(None, session_exists=False)
    resolver = SpyResolver()

    with pytest.raises(SessionNotFoundError) as error:
        await orchestrator(store, catalog, resolver).handle(
            submission(ActionType.INSPECT_STATUS)
        )

    assert error.value.code == "SESSION_NOT_FOUND"
    assert resolver.calls == 0
    assert store.requests == {}


@pytest.mark.asyncio
async def test_missing_snapshot_stops_without_default_state(catalog: ContentCatalog) -> None:
    store = FakeStore(None)
    with pytest.raises(SnapshotNotFoundError):
        await orchestrator(store, catalog).handle(submission(ActionType.INSPECT_STATUS))
    assert store.requests == {}


@pytest.mark.asyncio
async def test_snapshot_state_version_mismatch_stops(catalog: ContentCatalog) -> None:
    store = FakeStore(make_state(catalog), state_version=4)
    assert store.snapshot is not None
    store.snapshot = PersistedSnapshot(3, store.snapshot.state)
    with pytest.raises(SnapshotStateVersionMismatchError):
        await orchestrator(store, catalog).handle(submission(ActionType.INSPECT_STATUS))


@pytest.mark.asyncio
@pytest.mark.parametrize("schema_version", [3, True, 1.0, "1", None])
async def test_snapshot_schema_version_mismatch_stops(
    catalog: ContentCatalog, schema_version: object
) -> None:
    store = FakeStore(make_state(catalog))
    assert store.snapshot is not None
    payload = dict(store.snapshot.state)
    payload["schema_version"] = schema_version
    store.snapshot = PersistedSnapshot(4, payload)
    with pytest.raises(SnapshotSchemaVersionMismatchError):
        await orchestrator(store, catalog).handle(submission(ActionType.INSPECT_STATUS))


@pytest.mark.asyncio
async def test_snapshot_content_version_mismatch_stops(catalog: ContentCatalog) -> None:
    store = FakeStore(make_state(catalog))
    assert store.snapshot is not None
    payload = dict(store.snapshot.state)
    payload["content_version"] = "other-content"
    store.snapshot = PersistedSnapshot(4, payload)
    with pytest.raises(SnapshotContentVersionMismatchError):
        await orchestrator(store, catalog).handle(submission(ActionType.INSPECT_STATUS))


@pytest.mark.asyncio
async def test_corrupt_snapshot_stops_without_replacement(catalog: ContentCatalog) -> None:
    store = FakeStore(make_state(catalog))
    assert store.snapshot is not None
    payload = deepcopy(dict(store.snapshot.state))
    payload["player"]["resources"]["stamina"]["current"] = -1
    store.snapshot = PersistedSnapshot(4, payload)
    with pytest.raises(SnapshotInvalidError):
        await orchestrator(store, catalog).handle(submission(ActionType.INSPECT_STATUS))
    assert store.snapshot.state == payload


@pytest.mark.asyncio
async def test_snapshot_player_mismatch_stops_before_resolver(
    catalog: ContentCatalog,
) -> None:
    character = catalog.character("character.player.default")
    assert character is not None
    state = GameState(
        content_version=catalog.content_version,
        player=PlayerState.from_definition("other-player", character),
    )
    store = FakeStore(state)
    resolver = SpyResolver()

    with pytest.raises(SnapshotSessionMismatchError):
        await orchestrator(store, catalog, resolver).handle(
            submission(ActionType.INSPECT_STATUS)
        )

    assert resolver.calls == 0
    assert store.requests == {}


@pytest.mark.asyncio
async def test_orchestrator_mints_fresh_empty_authority_context(
    catalog: ContentCatalog,
) -> None:
    state = make_state(catalog)
    state.spawn_npc(catalog, "npc.demo.guard", "npc-runtime-guard")
    store = FakeStore(state)
    resolver = SpyResolver()
    action = submission(ActionType.INSPECT_STATUS)

    await orchestrator(store, catalog, resolver).handle(action)

    trusted = resolver.contexts[0]
    assert trusted.is_authentic_for(state, catalog)
    assert trusted.action_context.visible_entity_ids == frozenset()
    assert trusted.action_context.interactable_entity_ids == frozenset()
    assert trusted.action_context.environment_tool_ids == frozenset()
    assert not trusted.authorizes_skill_learning("skill.observation")


@pytest.mark.asyncio
async def test_state_change_forces_a_new_context_bound_to_new_snapshot(
    catalog: ContentCatalog,
) -> None:
    state = make_state(catalog)
    state.grant_item(catalog, "item.training_sword", instance_id="sword-context")
    store = FakeStore(state)
    resolver = SpyResolver()
    service = orchestrator(store, catalog, resolver)

    await service.handle(
        submission(
            ActionType.EQUIP,
            client_request_id="request-equip-context",
            item_instance_id="sword-context",
            equipment_slot_id="hand.main",
        )
    )
    await service.handle(
        submission(
            ActionType.INSPECT_STATUS,
            client_request_id="request-query-new-version",
        )
    )

    assert store.snapshot is not None
    updated = GameState.from_snapshot(store.snapshot.state, catalog=catalog)
    first_context, second_context = resolver.contexts
    assert first_context is not second_context
    assert not first_context.is_authentic_for(updated, catalog)
    assert second_context.is_authentic_for(updated, catalog)


def test_player_request_cannot_inject_gateway_or_authority_fields() -> None:
    for field_name in (
        "gateway_route",
        "gateway_decision",
        "narrative_fact",
        "skill_learning_authorization",
        "trusted_context",
        "context_digest",
        "catalog",
    ):
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            submission(ActionType.INSPECT_STATUS, **{field_name: "forged"})


@pytest.mark.asyncio
async def test_skill_learning_has_no_default_authorization(catalog: ContentCatalog) -> None:
    store = FakeStore(make_state(catalog))
    response = await orchestrator(store, catalog).handle(
        submission(ActionType.LEARN_SKILL, skill_definition_id="skill.observation")
    )
    assert response.resolution_kind is ResolutionStatus.REJECTED_LOCAL
    assert response.result_code == "SKILL_LEARNING_NOT_AUTHORIZED"
    assert response.resulting_state_version == 4
    assert store.events == []


@pytest.mark.asyncio
async def test_local_query_persists_result_without_state_change_or_narrative(
    catalog: ContentCatalog,
) -> None:
    state = make_state(catalog)
    store = FakeStore(state)
    before = deepcopy(store.snapshot)
    response = await orchestrator(store, catalog).handle(
        submission(ActionType.INSPECT_STATUS)
    )

    assert response.resolution_kind is ResolutionStatus.RESOLVED_LOCAL
    assert response.state_changed is False
    assert response.resulting_state_version == 4
    assert response.local_query_result is not None
    assert response.local_query_result["player_id"] == "player-1"
    assert response.narrative_required is False
    assert store.snapshot == before
    assert store.events == []
    assert "sequence:session-1" not in store.calls
    assert store.commits == 1


@pytest.mark.asyncio
async def test_local_rejection_persists_without_version_or_events(catalog: ContentCatalog) -> None:
    store = FakeStore(make_state(catalog))
    before = deepcopy(store.snapshot)
    response = await orchestrator(store, catalog).handle(
        submission(ActionType.CUSTOM, description="啊啊啊啊啊啊啊")
    )
    assert response.resolution_kind is ResolutionStatus.REJECTED_LOCAL
    assert response.resulting_state_version == 4
    assert response.state_changed is False
    assert store.snapshot == before
    assert store.events == []


@pytest.mark.asyncio
async def test_narrative_required_is_persisted_pending_without_state_change(
    catalog: ContentCatalog,
) -> None:
    store = FakeStore(make_state(catalog))
    before = deepcopy(store.snapshot)
    response = await orchestrator(store, catalog).handle(
        submission(ActionType.EXPLORE, description="我仔细查看走廊。")
    )
    assert response.resolution_kind is ResolutionStatus.NARRATIVE_REQUIRED
    assert response.narrative_required is True
    assert response.narrative_pending is True
    assert response.resulting_state_version == 4
    assert store.snapshot == before
    assert store.events == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("action_type", "action_fields"),
    [
        (ActionType.INSPECT_STATUS, {}),
        (ActionType.CUSTOM, {"description": "啊啊啊啊啊啊啊"}),
        (ActionType.EXPLORE, {"description": "我仔细查看走廊。"}),
    ],
)
async def test_non_state_response_write_failure_rolls_back_without_version_or_events(
    catalog: ContentCatalog,
    action_type: ActionType,
    action_fields: dict[str, str],
) -> None:
    store = FakeStore(make_state(catalog))
    before = deepcopy(store.snapshot)
    store.fail_turn_request = True

    with pytest.raises(RuntimeError, match="turn response failure"):
        await orchestrator(store, catalog).handle(
            submission(action_type, **action_fields)
        )

    assert store.snapshot == before
    assert store.session is not None and store.session.state_version == 4
    assert store.events == []
    assert store.requests == {}
    assert store.commits == 0
    assert store.rollbacks == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["equip", "consume", "skill"])
async def test_local_mutations_save_one_new_snapshot(
    catalog: ContentCatalog, mutation: str
) -> None:
    state = make_state(catalog)
    if mutation == "equip":
        state.grant_item(catalog, "item.training_sword", instance_id="sword-1")
        action = submission(
            ActionType.EQUIP,
            item_instance_id="sword-1",
            equipment_slot_id="hand.main",
        )
    elif mutation == "consume":
        state.grant_item(catalog, "item.medkit", 2, instance_id="medkit-1")
        action = submission(ActionType.USE_ITEM, item_instance_id="medkit-1")
    else:
        state.learn_skill(catalog, "skill.observation")
        action = submission(
            ActionType.USE_SKILL,
            skill_definition_id="skill.observation",
        )
    store = FakeStore(state)

    response = await orchestrator(store, catalog).handle(action)

    assert response.state_changed is True
    assert response.resulting_state_version == 5
    assert store.session is not None and store.session.state_version == 5
    assert store.snapshot is not None and store.snapshot.state_version == 5
    GameState.from_snapshot(store.snapshot.state, catalog=catalog)
    assert store.commits == 1


@pytest.mark.asyncio
async def test_multiple_drafts_keep_order_sequence_clock_and_writable_payload(
    catalog: ContentCatalog,
) -> None:
    state = make_state(catalog)
    state.learn_skill(catalog, "skill.observation")
    store = FakeStore(state)
    store.events.append(
        DomainEvent("old", "session-1", "turn-0", 7, "OldEvent", {"old": True}, FIXED_TIME)
    )
    action = submission(ActionType.USE_SKILL, skill_definition_id="skill.observation")

    response = await orchestrator(
        store,
        catalog,
        ids=["fixed-a", "fixed-b", "fixed-c"],
    ).handle(action)

    written = store.events[1:]
    assert [event.event_type for event in written] == [
        "SkillResourceSpent",
        "PlayerResourceChanged",
        "SkillUsed",
    ]
    assert [event.sequence_no for event in written] == [8, 9, 10]
    assert [event.event_id for event in written] == ["fixed-a", "fixed-b", "fixed-c"]
    assert all(event.occurred_at == FIXED_TIME for event in written)
    assert all(event.turn_id == action.turn_id for event in written)
    assert type(written[0].payload) is dict
    written[0].payload["writable"] = True
    assert response.resulting_state_version == 5


@pytest.mark.asyncio
async def test_duplicate_client_request_returns_deserialized_equal_response_once(
    catalog: ContentCatalog,
) -> None:
    store = FakeStore(make_state(catalog))
    resolver = SpyResolver()
    service = orchestrator(store, catalog, resolver)
    action = submission(ActionType.INSPECT_STATUS)

    first = await service.handle(action)
    second = await service.handle(action)

    assert first == second
    assert first is not second
    assert resolver.calls == 1
    assert len(store.requests) == 1
    assert store.commits == 1


@pytest.mark.asyncio
async def test_reused_idempotency_key_with_different_action_is_an_explicit_conflict(
    catalog: ContentCatalog,
) -> None:
    store = FakeStore(make_state(catalog))
    resolver = SpyResolver()
    service = orchestrator(store, catalog, resolver)
    original = submission(
        ActionType.INSPECT_STATUS,
        client_request_id="request-shared-idempotency-key",
    )
    conflicting = submission(
        ActionType.EXPLORE,
        client_request_id=original.client_request_id,
        description="我检查走廊。",
    )

    await service.handle(original)
    with pytest.raises(IdempotencyConflictError) as error:
        await service.handle(conflicting)

    assert error.value.code == "IDEMPOTENCY_CONFLICT"
    assert resolver.calls == 1
    assert len(store.requests) == 1


@pytest.mark.asyncio
async def test_reused_idempotency_key_cannot_mix_turn_ids(
    catalog: ContentCatalog,
) -> None:
    store = FakeStore(make_state(catalog))
    resolver = SpyResolver()
    service = orchestrator(store, catalog, resolver)
    original = submission(
        ActionType.INSPECT_STATUS,
        client_request_id="request-shared-turn-key",
    )

    await service.handle(original)
    with pytest.raises(IdempotencyConflictError):
        await service.handle(original.model_copy(update={"turn_id": "turn-2"}))

    assert resolver.calls == 1


@pytest.mark.asyncio
async def test_concurrent_duplicate_request_resolves_once(catalog: ContentCatalog) -> None:
    store = FakeStore(make_state(catalog))
    resolver = SpyResolver()
    resolver.release = asyncio.Event()
    service = orchestrator(store, catalog, resolver)
    action = submission(ActionType.INSPECT_STATUS)

    first_task = asyncio.create_task(service.handle(action))
    await asyncio.wait_for(resolver.entered.wait(), timeout=1)
    second_task = asyncio.create_task(service.handle(action))
    await asyncio.sleep(0.05)
    assert not second_task.done()
    resolver.release.set()
    first, second = await asyncio.gather(first_task, second_task)

    assert first == second
    assert resolver.calls == 1
    assert len(store.requests) == 1


@pytest.mark.asyncio
async def test_concurrent_different_actions_reusing_one_key_conflict_after_lock(
    catalog: ContentCatalog,
) -> None:
    store = FakeStore(make_state(catalog))
    resolver = SpyResolver()
    resolver.release = asyncio.Event()
    service = orchestrator(store, catalog, resolver)
    first_action = submission(
        ActionType.INSPECT_STATUS,
        client_request_id="request-concurrent-conflict",
    )
    conflicting_action = submission(
        ActionType.EXPLORE,
        client_request_id=first_action.client_request_id,
        description="我查看另一条路。",
    )

    first_task = asyncio.create_task(service.handle(first_action))
    await asyncio.wait_for(resolver.entered.wait(), timeout=1)
    second_task = asyncio.create_task(service.handle(conflicting_action))
    await asyncio.sleep(0.05)
    assert not second_task.done()
    resolver.release.set()
    await first_task
    with pytest.raises(IdempotencyConflictError):
        await second_task

    assert resolver.calls == 1
    assert len(store.requests) == 1


@pytest.mark.asyncio
async def test_unique_constraint_winner_is_replayed_without_resolving_twice(
    catalog: ContentCatalog,
) -> None:
    store = FakeStore(make_state(catalog))
    action = submission(ActionType.INSPECT_STATUS)
    winner_response = TurnResponse(
        session_id=action.session_id,
        client_request_id=action.client_request_id,
        action_signature=action.action_signature(),
        resolution_kind=ResolutionStatus.RESOLVED_LOCAL,
        result_code="STATUS_INSPECTED",
        feedback_code="STATUS_INSPECTED",
        feedback_parameters={"winner": True},
        resulting_state_version=4,
        state_changed=False,
        narrative_required=False,
        narrative_pending=False,
        local_query_result={"winner": True},
    )
    store.concurrent_winner = PersistedTurnRequest(
        turn_id=action.turn_id,
        action_signature=action.action_signature(),
        response=winner_response.to_persistence(),
    )
    resolver = SpyResolver()

    replayed = await orchestrator(store, catalog, resolver).handle(action)

    assert replayed == winner_response
    assert resolver.calls == 1
    assert len(store.requests) == 1
    assert store.commits == 0


@pytest.mark.asyncio
async def test_same_signature_with_different_request_ids_is_not_idempotent(
    catalog: ContentCatalog,
) -> None:
    store = FakeStore(make_state(catalog))
    resolver = SpyResolver()
    service = orchestrator(store, catalog, resolver)
    first_action = submission(ActionType.INSPECT_STATUS, client_request_id="request-a")
    second_action = submission(ActionType.INSPECT_STATUS, client_request_id="request-b")
    assert first_action.action_signature() == second_action.action_signature()

    first = await service.handle(first_action)
    second = await service.handle(second_action)

    assert first.client_request_id != second.client_request_id
    assert resolver.calls == 2
    assert len(store.requests) == 2


@pytest.mark.asyncio
async def test_different_requests_for_one_session_are_serialized(
    catalog: ContentCatalog,
) -> None:
    store = FakeStore(make_state(catalog))
    resolver = SpyResolver()
    resolver.release = asyncio.Event()
    service = orchestrator(store, catalog, resolver)
    first_action = submission(ActionType.INSPECT_STATUS, client_request_id="request-a")
    second_action = submission(ActionType.INSPECT_STATUS, client_request_id="request-b")

    first_task = asyncio.create_task(service.handle(first_action))
    await asyncio.wait_for(resolver.entered.wait(), timeout=1)
    second_task = asyncio.create_task(service.handle(second_action))
    await asyncio.sleep(0.05)
    assert resolver.calls == 1
    resolver.release.set()
    await asyncio.gather(first_task, second_task)

    assert resolver.calls == 2
    assert len(store.requests) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("failure", "error_type"),
    [
        ("resolver", RuntimeError),
        ("snapshot", RuntimeError),
        ("event", RuntimeError),
        ("response", RuntimeError),
        ("optimistic", OptimisticLockError),
    ],
)
async def test_any_technical_failure_rolls_back_every_write(
    catalog: ContentCatalog,
    failure: str,
    error_type: type[Exception],
) -> None:
    state = make_state(catalog)
    state.grant_item(catalog, "item.training_sword", instance_id="sword-1")
    store = FakeStore(state)
    before_snapshot = deepcopy(store.snapshot)
    resolver: object = DeterministicRuleResolver()
    if failure == "resolver":
        resolver = ResultResolver(error=RuntimeError("simulated resolver failure"))
    elif failure == "snapshot":
        store.fail_snapshot = True
    elif failure == "event":
        store.fail_event = True
    elif failure == "response":
        store.fail_turn_request = True
    else:
        store.optimistic_conflict = True
    action = submission(
        ActionType.EQUIP,
        item_instance_id="sword-1",
        equipment_slot_id="hand.main",
    )

    with pytest.raises(error_type):
        await orchestrator(store, catalog, resolver).handle(action)

    assert store.snapshot == before_snapshot
    assert store.session is not None and store.session.state_version == 4
    assert store.events == []
    assert store.requests == {}
    assert store.commits == 0
    assert store.rollbacks == 1


@pytest.mark.asyncio
async def test_invalid_candidate_state_rolls_back(catalog: ContentCatalog) -> None:
    candidate = make_state(catalog)
    candidate.player.wallet.balances["credits"] = -1
    result = ResolutionResult(
        status=ResolutionStatus.RESOLVED_LOCAL,
        success=True,
        result_code="BROKEN_CANDIDATE",
        updated_state=candidate,
        state_changed=True,
        events=(DomainEventDraft("CandidateChanged", {"safe": True}),),
        feedback=PlayerFeedback("BROKEN_CANDIDATE"),
    )
    store = FakeStore(make_state(catalog))

    with pytest.raises(CandidateStateInvalidError):
        await orchestrator(store, catalog, ResultResolver(result)).handle(
            submission(ActionType.INSPECT_STATUS)
        )
    assert store.requests == {}
    assert store.events == []


@pytest.mark.asyncio
async def test_candidate_state_cannot_replace_the_session_player(
    catalog: ContentCatalog,
) -> None:
    character = catalog.character("character.player.default")
    assert character is not None
    candidate = GameState(
        content_version=catalog.content_version,
        player=PlayerState.from_definition("other-player", character),
    )
    result = ResolutionResult(
        status=ResolutionStatus.RESOLVED_LOCAL,
        success=True,
        result_code="BROKEN_PLAYER_REPLACEMENT",
        updated_state=candidate,
        state_changed=True,
        events=(DomainEventDraft("PlayerReplaced", {"safe": True}),),
        feedback=PlayerFeedback("BROKEN_PLAYER_REPLACEMENT"),
    )
    store = FakeStore(make_state(catalog))

    with pytest.raises(CandidateStateInvalidError):
        await orchestrator(store, catalog, ResultResolver(result)).handle(
            submission(ActionType.INSPECT_STATUS)
        )

    assert store.snapshot is not None
    assert store.snapshot.state["player"]["player_id"] == "player-1"
    assert store.events == []


@pytest.mark.asyncio
async def test_duplicate_event_ids_and_clock_failures_roll_back_before_commit(
    catalog: ContentCatalog,
) -> None:
    state = make_state(catalog)
    state.learn_skill(catalog, "skill.observation")
    action = submission(ActionType.USE_SKILL, skill_definition_id="skill.observation")

    duplicate_store = FakeStore(state)
    with pytest.raises(ValueError, match="duplicate ID"):
        await orchestrator(
            duplicate_store,
            catalog,
            ids=["duplicate-event", "duplicate-event"],
        ).handle(action)
    assert duplicate_store.snapshot is not None
    assert duplicate_store.snapshot.state_version == 4
    assert duplicate_store.events == []
    assert duplicate_store.requests == {}

    clock_store = FakeStore(state)
    clock_calls = 0

    def failing_clock() -> datetime:
        nonlocal clock_calls
        clock_calls += 1
        if clock_calls == 2:
            raise RuntimeError("clock failed")
        return FIXED_TIME

    service = FirstPhaseTurnOrchestrator(
        resolver=DeterministicRuleResolver(),
        uow_factory=lambda: FakeUnitOfWork(clock_store),
        catalog=catalog,
        clock=failing_clock,
        event_id_generator=iter(["clock-a", "clock-b", "clock-c"]).__next__,
    )
    with pytest.raises(RuntimeError, match="clock failed"):
        await service.handle(action)
    assert clock_store.snapshot is not None
    assert clock_store.snapshot.state_version == 4
    assert clock_store.events == []
    assert clock_store.requests == {}


@pytest.mark.asyncio
async def test_anomaly_resolution_cannot_enter_default_pipeline(catalog: ContentCatalog) -> None:
    result = ResolutionResult(
        status=ResolutionStatus.ANOMALY_EVALUATION_REQUIRED,
        success=False,
        result_code="ANOMALY_EVALUATION_DEFERRED",
        feedback=PlayerFeedback("ANOMALY_EVALUATION_DEFERRED"),
    )
    store = FakeStore(make_state(catalog))
    with pytest.raises(UnsupportedResolutionError):
        await orchestrator(store, catalog, ResultResolver(result)).handle(
            submission(ActionType.INSPECT_STATUS)
        )
    assert store.requests == {}


@pytest.mark.asyncio
async def test_corrupt_stored_response_is_not_returned_as_success(catalog: ContentCatalog) -> None:
    store = FakeStore(make_state(catalog))
    action = submission(ActionType.INSPECT_STATUS)
    store.requests[(action.session_id, action.client_request_id)] = PersistedTurnRequest(
        turn_id=action.turn_id,
        action_signature=action.action_signature(),
        response={"bad": "shape"},
    )
    with pytest.raises(StoredTurnResponseInvalidError):
        await orchestrator(store, catalog).handle(action)


@pytest.mark.asyncio
async def test_incomplete_stored_response_is_an_explicit_failure(
    catalog: ContentCatalog,
) -> None:
    store = FakeStore(make_state(catalog))
    action = submission(ActionType.INSPECT_STATUS)
    store.requests[(action.session_id, action.client_request_id)] = PersistedTurnRequest(
        turn_id=action.turn_id,
        action_signature=action.action_signature(),
        response=None,
    )

    with pytest.raises(StoredTurnResponseInvalidError):
        await orchestrator(store, catalog).handle(action)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field_name", "bad_value"),
    [
        ("session_id", "other-session"),
        ("client_request_id", "other-request"),
        ("action_signature", "b" * 64),
    ],
)
async def test_stored_response_metadata_cannot_be_mixed(
    catalog: ContentCatalog,
    field_name: str,
    bad_value: str,
) -> None:
    store = FakeStore(make_state(catalog))
    action = submission(ActionType.INSPECT_STATUS)
    service = orchestrator(store, catalog)
    response = await service.handle(action)
    key = (action.session_id, action.client_request_id)
    stored = store.requests[key]
    damaged_response = response.to_persistence()
    damaged_response[field_name] = bad_value
    store.requests[key] = replace(stored, response=damaged_response)

    with pytest.raises(StoredTurnResponseInvalidError):
        await service.handle(action)


@pytest.mark.asyncio
async def test_local_query_response_is_detached_from_later_state_changes(
    catalog: ContentCatalog,
) -> None:
    state = make_state(catalog)
    state.grant_item(catalog, "item.training_sword", instance_id="detached-sword")
    store = FakeStore(state)
    service = orchestrator(store, catalog)
    query_action = submission(
        ActionType.INSPECT_EQUIPMENT,
        client_request_id="request-equipment-before",
    )
    query_response = await service.handle(query_action)
    original_payload = query_response.to_persistence()

    await service.handle(
        submission(
            ActionType.EQUIP,
            client_request_id="request-equip-after",
            item_instance_id="detached-sword",
            equipment_slot_id="hand.main",
        )
    )

    replayed = await service.handle(query_action)
    assert query_response.to_persistence() == original_payload
    assert replayed == query_response
    assert replayed.resulting_state_version == 4
    assert query_response.local_query_result is not None
    with pytest.raises(TypeError, match="frozen JSON"):
        query_response.local_query_result["changed"] = True


def test_turn_response_rejects_internal_or_non_json_fields() -> None:
    payload = {
        "session_id": "session-1",
        "client_request_id": "request-1",
        "action_signature": "a" * 64,
        "resolution_kind": "RESOLVED_LOCAL",
        "result_code": "STATUS_INSPECTED",
        "feedback_code": "STATUS_INSPECTED",
        "feedback_parameters": {},
        "resulting_state_version": 4,
        "state_changed": False,
        "narrative_required": False,
        "narrative_pending": False,
        "local_query_result": {},
    }
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        TurnResponse.model_validate({**payload, "trusted_context": "secret"})
    with pytest.raises(ValidationError, match="valid boolean"):
        TurnResponse.model_validate({**payload, "state_changed": 0})
    with pytest.raises(TypeError, match="non-JSON"):
        TurnResponse.model_validate({**payload, "feedback_parameters": {"error": object()}})
    with pytest.raises(ValidationError, match="must preserve its result"):
        TurnResponse.model_validate({**payload, "local_query_result": None})
    with pytest.raises(ValidationError, match="must match feedback parameters"):
        TurnResponse.model_validate(
            {**payload, "local_query_result": {"different": True}}
        )

    reordered = dict(reversed(list(payload.items())))
    assert TurnResponse.model_validate(reordered) == TurnResponse.model_validate(payload)


@pytest.fixture
def scenario_catalog() -> ScenarioCatalog:
    return JsonScenarioCatalogLoader(SCENARIO_PACK).load()


@pytest.mark.asyncio
async def test_scenario_rejection_and_query_never_advance_story_or_version(
    scenario_catalog: ScenarioCatalog,
) -> None:
    original, store = scenario_state_and_store(scenario_catalog)
    spy = SpyStoryDirector()
    service = orchestrator(
        store,
        scenario_catalog.content_catalog,
        scenario_catalog=scenario_catalog,
        story_director=spy,
    )
    rejected = await service.handle(
        submission(
            ActionType.CUSTOM,
            client_request_id="scenario-rejected",
            description="啊啊啊啊啊啊啊",
        )
    )
    queried = await service.handle(
        submission(
            ActionType.INSPECT_STATUS,
            client_request_id="scenario-query",
        )
    )

    assert rejected.resolution_kind is ResolutionStatus.REJECTED_LOCAL
    assert queried.resolution_kind is ResolutionStatus.RESOLVED_LOCAL
    assert rejected.narrative_frame is not None
    assert queried.narrative_frame is not None
    assert spy.advance_calls == 0
    assert store.session is not None and store.session.state_version == 4
    assert store.snapshot is not None
    assert store.snapshot.state == original.to_snapshot()
    assert store.events == []


@pytest.mark.asyncio
async def test_narrative_required_cannot_turn_player_claim_into_npc_acknowledgement(
    scenario_catalog: ScenarioCatalog,
) -> None:
    original, store = scenario_state_and_store(scenario_catalog)
    spy = SpyStoryDirector()
    response = await orchestrator(
        store,
        scenario_catalog.content_catalog,
        scenario_catalog=scenario_catalog,
        story_director=spy,
    ).handle(
        submission(
            ActionType.TALK,
            client_request_id="scenario-false-npc-claim",
            dialogue="护士承认我还活着",
        )
    )

    assert response.resolution_kind is ResolutionStatus.NARRATIVE_REQUIRED
    assert response.narrative_pending is True
    assert response.resulting_state_version == 4
    assert spy.advance_calls == 0
    assert store.snapshot is not None
    assert store.snapshot.state == original.to_snapshot()
    serialized = json.dumps(response.to_persistence(), ensure_ascii=False)
    assert "player_is_alive" not in serialized
    assert "vitals.verified" not in serialized


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "choice_id",
    [
        "death_certificate.action.seek_records",
        "death_certificate.action.fabricated",
        "death_certificate.decision.core_one",
    ],
)
async def test_only_current_public_decision_choices_are_accepted(
    scenario_catalog: ScenarioCatalog,
    choice_id: str,
) -> None:
    original, store = scenario_state_and_store(scenario_catalog)
    response = await orchestrator(
        store,
        scenario_catalog.content_catalog,
        scenario_catalog=scenario_catalog,
    ).handle(
        submission(
            ActionType.CHOOSE,
            client_request_id=f"invalid-choice-{choice_id.rsplit('.', 1)[-1]}",
            decision_id=current_public_decision_id(original, scenario_catalog),
            choice_id=choice_id,
        )
    )
    assert response.resolution_kind is ResolutionStatus.REJECTED_LOCAL
    assert response.result_code == "INVALID_DECISION_CHOICE"
    assert response.resulting_state_version == 4
    assert store.snapshot is not None
    assert store.snapshot.state == original.to_snapshot()
    assert store.events == []


@pytest.mark.asyncio
async def test_valid_decision_is_sealed_recorded_once_without_claiming_outcomes(
    scenario_catalog: ScenarioCatalog,
) -> None:
    original, store = scenario_state_and_store(scenario_catalog)
    spy = SpyStoryDirector()
    service = orchestrator(
        store,
        scenario_catalog.content_catalog,
        scenario_catalog=scenario_catalog,
        story_director=spy,
        ids=["decision-domain-event"],
    )
    action = submission(
        ActionType.CHOOSE,
        client_request_id="valid-current-choice",
        decision_id=current_public_decision_id(original, scenario_catalog),
        choice_id="death_certificate.action.move_fingers_rhythmically",
    )
    first = await service.handle(action)
    replay = await service.handle(action)
    stale = await service.handle(
        action.model_copy(update={"client_request_id": "stale-after-completion"})
    )

    assert first == replay
    assert first.resolution_kind is ResolutionStatus.RESOLVED_LOCAL
    assert first.result_code == "SCENARIO_DECISION_RECORDED"
    assert first.resulting_state_version == 5
    assert spy.advance_calls == 1
    assert stale.resolution_kind is ResolutionStatus.REJECTED_LOCAL
    assert stale.result_code == "STALE_DECISION"
    assert stale.resulting_state_version == 5
    assert len(store.events) == 1
    audit = store.events[0]
    assert audit.event_type == "ScenarioDecisionSelected"
    assert audit.payload["source"] == "VALIDATED_DECISION_RESPONSE"
    assert audit.payload["decision_id"] == (
        "death_certificate.decision.immediate_survival"
    )
    assert audit.payload["selected_action_id"] == action.choice_id
    assert not (
        {"npc_acknowledged", "clues", "facts", "clock_delta", "sealed_payload"}
        & set(audit.payload)
    )
    serialized = json.dumps(
        first.model_dump(mode="json", exclude={"action_signature"}),
        ensure_ascii=False,
    )
    for forbidden in (
        "prediction_causes_outcome",
        "underground_patient_alive",
        "security_alert",
        "death_certificate.decision.",
        "_issuer",
        "_sealed_payload",
        "action_signature",
        "policy_trace",
        "database_url",
    ):
        assert forbidden not in serialized
    assert store.snapshot is not None
    runtime = store.snapshot.state["scenario_runtime"]
    assert runtime["current_phase_id"] == "death_certificate.life_disputed"
    assert runtime["decisions_made"] == [
        "death_certificate.decision.immediate_survival"
    ]


@pytest.mark.asyncio
async def test_public_decision_id_from_another_session_is_stale(
    scenario_catalog: ScenarioCatalog,
) -> None:
    original, store = scenario_state_and_store(scenario_catalog)
    definition = scenario_catalog.scenarios[0]
    foreign_frame = bind_public_decision_frame(
        DeterministicStoryDirector().plan_frame(original, definition),
        session_id="session-2",
        state_version=4,
        scenario_content_version=definition.content_version,
    )
    response = await orchestrator(
        store,
        scenario_catalog.content_catalog,
        scenario_catalog=scenario_catalog,
    ).handle(
        submission(
            ActionType.CHOOSE,
            client_request_id="cross-session-decision",
            decision_id=foreign_frame.decision_id,
            choice_id="death_certificate.action.observe_quietly",
        )
    )
    assert response.resolution_kind is ResolutionStatus.REJECTED_LOCAL
    assert response.result_code == "STALE_DECISION"
    assert response.resulting_state_version == 4
    assert store.events == []


@pytest.mark.asyncio
async def test_mechanical_and_scenario_candidates_merge_without_lost_update(
    scenario_catalog: ScenarioCatalog,
) -> None:
    payload = scenario_catalog.model_dump(mode="json")
    payload["content_catalog"]["items"].append(
        {
            "definition_id": "item.scenario.token",
            "display_name": "事务测试令牌",
            "stack_limit": 2,
            "tags": ["consumable"],
        }
    )
    extended = ScenarioCatalog.model_validate(payload)
    original, store = scenario_state_and_store(extended)
    original.grant_item(
        extended.content_catalog,
        "item.scenario.token",
        2,
        instance_id="scenario-token",
    )
    store.snapshot = PersistedSnapshot(4, original.to_snapshot())
    candidate = original.detached_copy(extended.content_catalog)
    candidate.remove_item("scenario-token", 1)
    resolver = ResultResolver(
        ResolutionResult(
            status=ResolutionStatus.RESOLVED_LOCAL,
            success=True,
            result_code="MECHANICAL_DECISION_APPLIED",
            updated_state=candidate,
            state_changed=True,
            events=(
                DomainEventDraft(
                    "MechanicalDecisionApplied", {"item_instance_id": "scenario-token"}
                ),
            ),
            feedback=PlayerFeedback("MECHANICAL_DECISION_APPLIED"),
        )
    )
    action = submission(
        ActionType.CHOOSE,
        client_request_id="combined-decision",
        decision_id=current_public_decision_id(original, extended),
        choice_id="death_certificate.action.observe_quietly",
    )
    response = await orchestrator(
        store,
        extended.content_catalog,
        resolver,
        scenario_catalog=extended,
        ids=["mechanical-event", "decision-event"],
    ).handle(action)

    assert response.resulting_state_version == 5
    assert store.snapshot is not None
    restored = GameState.from_snapshot(
        store.snapshot.state,
        catalog=extended.content_catalog,
        scenario_catalog=extended,
    )
    assert restored.player.inventory.items["scenario-token"].quantity == 1
    assert restored.scenario_runtime is not None
    assert restored.scenario_runtime.current_phase_id == (
        "death_certificate.life_disputed"
    )
    assert [event.event_type for event in store.events] == [
        "MechanicalDecisionApplied",
        "ScenarioDecisionSelected",
    ]
    assert [event.sequence_no for event in store.events] == [1, 2]
    assert original.player.inventory.items["scenario-token"].quantity == 2
    assert original.scenario_runtime is not None
    assert original.scenario_runtime.current_decision_id is not None


@pytest.mark.asyncio
async def test_mechanical_candidate_is_rolled_back_when_story_coordination_fails(
    scenario_catalog: ScenarioCatalog,
) -> None:
    class FailingDirector(DeterministicStoryDirector):
        def advance_after_verified_result(self, *args: object, **kwargs: object):
            raise StoryDirectorError("simulated combined story failure")

    original, store = scenario_state_and_store(scenario_catalog)
    candidate = original.detached_copy(scenario_catalog.content_catalog)
    candidate.player.resources["composure"].current -= 1
    resolver = ResultResolver(
        ResolutionResult(
            status=ResolutionStatus.RESOLVED_LOCAL,
            success=True,
            result_code="MECHANICAL_DECISION_APPLIED",
            updated_state=candidate,
            state_changed=True,
            events=(DomainEventDraft("ComposureSpent", {"amount": 1}),),
            feedback=PlayerFeedback("MECHANICAL_DECISION_APPLIED"),
        )
    )
    action = submission(
        ActionType.CHOOSE,
        client_request_id="combined-story-failure",
        decision_id=current_public_decision_id(original, scenario_catalog),
        choice_id="death_certificate.action.observe_quietly",
    )
    with pytest.raises(CandidateStateInvalidError):
        await orchestrator(
            store,
            scenario_catalog.content_catalog,
            resolver,
            scenario_catalog=scenario_catalog,
            story_director=FailingDirector(),
        ).handle(action)
    assert store.snapshot is not None
    assert store.snapshot.state == original.to_snapshot()
    assert store.session is not None and store.session.state_version == 4
    assert store.events == []
    assert store.requests == {}


@pytest.mark.asyncio
async def test_open_decision_blocks_mechanical_mutation_without_advancing(
    scenario_catalog: ScenarioCatalog,
) -> None:
    payload = scenario_catalog.model_dump(mode="json")
    payload["content_catalog"]["items"].append(
        {
            "definition_id": "item.scenario.medkit",
            "display_name": "场景测试医疗包",
            "stack_limit": 2,
            "tags": ["consumable"],
        }
    )
    extended = ScenarioCatalog.model_validate(payload)
    original, store = scenario_state_and_store(extended)
    original.grant_item(
        extended.content_catalog,
        "item.scenario.medkit",
        2,
        instance_id="scenario-medkit",
    )
    store.snapshot = PersistedSnapshot(4, original.to_snapshot())
    before_runtime = deepcopy(original.to_snapshot()["scenario_runtime"])
    spy = SpyStoryDirector()
    response = await orchestrator(
        store,
        extended.content_catalog,
        scenario_catalog=extended,
        story_director=spy,
        ids=["scenario-mechanical-event"],
    ).handle(
        submission(
            ActionType.USE_ITEM,
            client_request_id="scenario-mechanical",
            item_instance_id="scenario-medkit",
        )
    )

    assert response.resolution_kind is ResolutionStatus.REJECTED_LOCAL
    assert response.result_code == "DECISION_RESPONSE_REQUIRED"
    assert response.resulting_state_version == 4
    assert spy.advance_calls == 0
    assert store.snapshot is not None
    assert store.snapshot.state["scenario_runtime"] == before_runtime
    assert store.snapshot.state["player"]["inventory"]["items"][
        "scenario-medkit"
    ]["quantity"] == 2
    assert store.events == []


@pytest.mark.asyncio
async def test_mechanical_mutation_after_decision_preserves_scenario_runtime(
    scenario_catalog: ScenarioCatalog,
) -> None:
    payload = scenario_catalog.model_dump(mode="json")
    payload["content_catalog"]["items"].append(
        {
            "definition_id": "item.scenario.medkit",
            "display_name": "场景测试医疗包",
            "stack_limit": 2,
            "tags": ["consumable"],
        }
    )
    extended = ScenarioCatalog.model_validate(payload)
    original, store = scenario_state_and_store(extended)
    original.grant_item(
        extended.content_catalog,
        "item.scenario.medkit",
        2,
        instance_id="scenario-medkit",
    )
    store.snapshot = PersistedSnapshot(4, original.to_snapshot())
    spy = SpyStoryDirector()
    service = orchestrator(
        store,
        extended.content_catalog,
        scenario_catalog=extended,
        story_director=spy,
        ids=["decision-event", "mechanical-event"],
    )
    decision = await service.handle(
        submission(
            ActionType.CHOOSE,
            client_request_id="decision-before-mechanical",
            decision_id=current_public_decision_id(original, extended),
            choice_id="death_certificate.action.observe_quietly",
        )
    )
    assert decision.resulting_state_version == 5
    assert store.snapshot is not None
    runtime_before = deepcopy(store.snapshot.state["scenario_runtime"])

    response = await service.handle(
        submission(
            ActionType.USE_ITEM,
            client_request_id="scenario-mechanical-after-decision",
            item_instance_id="scenario-medkit",
        )
    )

    assert response.resolution_kind is ResolutionStatus.RESOLVED_LOCAL
    assert response.resulting_state_version == 6
    assert spy.advance_calls == 1
    assert store.snapshot is not None
    assert store.snapshot.state["scenario_runtime"] == runtime_before
    assert store.snapshot.state["player"]["inventory"]["items"][
        "scenario-medkit"
    ]["quantity"] == 1
    assert [event.event_type for event in store.events] == [
        "ScenarioDecisionSelected",
        "ItemConsumed",
    ]


@pytest.mark.asyncio
async def test_story_failure_and_event_write_failure_rollback_the_whole_decision(
    scenario_catalog: ScenarioCatalog,
) -> None:
    class FailingDirector(DeterministicStoryDirector):
        def advance_after_verified_result(self, *args: object, **kwargs: object):
            raise StoryDirectorError("simulated story failure")

    original, story_store = scenario_state_and_store(scenario_catalog)
    action = submission(
        ActionType.CHOOSE,
        client_request_id="rollback-current-choice",
        decision_id=current_public_decision_id(original, scenario_catalog),
        choice_id="death_certificate.action.observe_quietly",
    )
    with pytest.raises(CandidateStateInvalidError):
        await orchestrator(
            story_store,
            scenario_catalog.content_catalog,
            scenario_catalog=scenario_catalog,
            story_director=FailingDirector(),
        ).handle(action)
    assert story_store.snapshot is not None
    assert story_store.snapshot.state == original.to_snapshot()
    assert story_store.events == []
    assert story_store.requests == {}

    original, write_store = scenario_state_and_store(scenario_catalog)
    write_store.fail_event = True
    with pytest.raises(RuntimeError, match="event failure"):
        await orchestrator(
            write_store,
            scenario_catalog.content_catalog,
            scenario_catalog=scenario_catalog,
        ).handle(action)
    assert write_store.snapshot is not None
    assert write_store.snapshot.state == original.to_snapshot()
    assert write_store.session is not None and write_store.session.state_version == 4
    assert write_store.events == []
    assert write_store.requests == {}


@pytest.mark.asyncio
async def test_ended_scenario_rejects_further_narrative_progress(
    scenario_catalog: ScenarioCatalog,
) -> None:
    _, store = scenario_state_and_store(scenario_catalog)
    assert store.snapshot is not None
    state = GameState.from_snapshot(
        store.snapshot.state,
        catalog=scenario_catalog.content_catalog,
        scenario_catalog=scenario_catalog,
    )
    runtime = state.scenario_runtime
    assert runtime is not None
    runtime.current_phase_id = "death_certificate.resolution"
    runtime.current_location_id = "death_certificate.control_room"
    runtime.opened_location_ids = runtime.opened_location_ids | {
        "death_certificate.control_room"
    }
    runtime.current_decision_id = None
    runtime.phase_beat_index = 0
    runtime.phase_visit_counts["death_certificate.resolution"] = 1
    runtime.ending_status = EndingStatus.RESOLVED
    runtime.ending_id = "death_certificate.ending.record_challenged"
    store.snapshot = PersistedSnapshot(4, state.to_snapshot())

    response = await orchestrator(
        store,
        scenario_catalog.content_catalog,
        scenario_catalog=scenario_catalog,
    ).handle(
        submission(
            ActionType.OBSERVE,
            client_request_id="ended-observe",
            description="继续观察",
        )
    )
    assert response.resolution_kind is ResolutionStatus.REJECTED_LOCAL
    assert response.result_code == "SCENARIO_ENDED"
    assert response.resulting_state_version == 4
    assert response.narrative_frame is not None
    assert response.narrative_frame.stop_condition == "SCENARIO_ENDED"
