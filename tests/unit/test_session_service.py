from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import pytest
from pydantic import ValidationError

from deviation_protocol.application.errors import (
    ConcurrentSessionCreateError,
    IdempotencyConflictError,
    InvalidCharacterDefinitionError,
    SessionNotFoundError,
    SnapshotContentVersionMismatchError,
)
from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.ports import PersistedSession, PersistedSnapshot
from deviation_protocol.application.session_service import SessionService
from deviation_protocol.domain.models import GameSession
from deviation_protocol.domain.state import GameState, NpcState
from deviation_protocol.infrastructure.content_loader import JsonContentCatalogLoader


CONTENT_PACK = Path(__file__).parents[2] / "config" / "demo_content_pack.json"
NOW = datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc)


class Store:
    def __init__(self) -> None:
        self.sessions: dict[str, PersistedSession] = {}
        self.snapshots: dict[str, PersistedSnapshot] = {}
        self.creation_keys: dict[tuple[str, str], str] = {}
        self.commit_lock = asyncio.Lock()
        self.fail_commit = False
        self.hidden_creation_lookups = 0


class Repository:
    def __init__(self, store: Store, uow: Uow) -> None:
        self.store = store
        self.uow = uow

    async def get_owned(self, session_id: str, player_id: str) -> PersistedSession | None:
        value = self.store.sessions.get(session_id)
        if value is None or value.session.player_id != player_id:
            return None
        return deepcopy(value)

    async def get_by_creation_request(
        self, player_id: str, client_request_id: str
    ) -> PersistedSession | None:
        await asyncio.sleep(0)
        if self.store.hidden_creation_lookups:
            self.store.hidden_creation_lookups -= 1
            return None
        session_id = self.store.creation_keys.get((player_id, client_request_id))
        return deepcopy(self.store.sessions.get(session_id)) if session_id else None

    async def add_initial(
        self,
        session: GameSession,
        *,
        character_definition_id: str,
        creation_client_request_id: str,
        state: Mapping[str, Any],
        created_at: datetime,
    ) -> None:
        self.uow.pending = (
            PersistedSession(
                session=replace(session),
                character_definition_id=character_definition_id,
                creation_client_request_id=creation_client_request_id,
                created_at=created_at,
                updated_at=created_at,
            ),
            PersistedSnapshot(session.state_version, deepcopy(dict(state))),
        )

    async def get_latest_snapshot(self, session_id: str) -> PersistedSnapshot | None:
        return deepcopy(self.store.snapshots.get(session_id))


class Uow:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.sessions = Repository(store, self)
        self.turn_requests = None
        self.pending: tuple[PersistedSession, PersistedSnapshot] | None = None
        self.committed = False

    async def __aenter__(self) -> Uow:
        return self

    async def __aexit__(self, *args: object) -> None:
        if not self.committed:
            self.pending = None

    async def commit(self) -> None:
        if self.store.fail_commit:
            raise RuntimeError("simulated commit failure")
        assert self.pending is not None
        persisted, snapshot = self.pending
        key = (
            persisted.session.player_id,
            persisted.creation_client_request_id,
        )
        async with self.store.commit_lock:
            if key in self.store.creation_keys:
                raise ConcurrentSessionCreateError
            session_id = persisted.session.session_id
            self.store.sessions[session_id] = deepcopy(persisted)
            self.store.snapshots[session_id] = deepcopy(snapshot)
            self.store.creation_keys[key] = session_id  # type: ignore[index]
        self.committed = True

    async def rollback(self) -> None:
        self.pending = None


@pytest.fixture
def service_and_store() -> tuple[SessionService, Store]:
    catalog = JsonContentCatalogLoader(CONTENT_PACK).load()
    store = Store()
    ids = iter((f"session-{index}" for index in range(1, 20)))
    service = SessionService(
        uow_factory=lambda: Uow(store),  # type: ignore[arg-type]
        catalog=catalog,
        clock=lambda: NOW,
        session_id_generator=lambda: next(ids),
        seed_generator=lambda: 42,
    )
    return service, store


def principal(player_id: str = "player-1") -> RequestPrincipal:
    return RequestPrincipal(player_id=player_id, authentication_scheme="test")


@pytest.mark.asyncio
async def test_create_builds_version_zero_state_atomically(
    service_and_store: tuple[SessionService, Store],
) -> None:
    service, store = service_and_store
    result = await service.create(
        principal(),
        client_request_id="create-1",
        character_definition_id="character.player.default",
    )

    assert result.session_id == "session-1"
    assert result.state_version == 0
    assert result.content_version == "demo-1"
    assert set(store.sessions) == {"session-1"}
    state = GameState.from_snapshot(
        store.snapshots["session-1"].state, catalog=service.catalog
    )
    assert state.player.player_id == "player-1"
    assert state.player.attributes == {"strength": 5, "focus": 4}


@pytest.mark.asyncio
async def test_invalid_character_does_not_leave_a_partial_session(
    service_and_store: tuple[SessionService, Store],
) -> None:
    service, store = service_and_store
    with pytest.raises(InvalidCharacterDefinitionError):
        await service.create(
            principal(),
            client_request_id="create-invalid",
            character_definition_id="missing-character",
        )
    assert store.sessions == {}
    assert store.snapshots == {}


@pytest.mark.asyncio
async def test_create_commit_failure_rolls_back_session_and_snapshot(
    service_and_store: tuple[SessionService, Store],
) -> None:
    service, store = service_and_store
    store.fail_commit = True
    with pytest.raises(RuntimeError, match="commit failure"):
        await service.create(
            principal(),
            client_request_id="create-fail",
            character_definition_id="character.player.default",
        )
    assert store.sessions == {}
    assert store.snapshots == {}


@pytest.mark.asyncio
async def test_create_retry_and_concurrent_create_return_one_session(
    service_and_store: tuple[SessionService, Store],
) -> None:
    service, store = service_and_store

    first, second = await asyncio.gather(
        *(
            service.create(
                principal(),
                client_request_id="create-concurrent",
                character_definition_id="character.player.default",
            )
            for _ in range(2)
        )
    )
    replay = await service.create(
        principal(),
        client_request_id="create-concurrent",
        character_definition_id="character.player.default",
    )

    assert first.session_id == second.session_id == replay.session_id
    assert len(store.sessions) == len(store.snapshots) == 1


@pytest.mark.asyncio
async def test_different_players_can_reuse_the_same_creation_key(
    service_and_store: tuple[SessionService, Store],
) -> None:
    service, store = service_and_store
    first = await service.create(
        principal("player-1"),
        client_request_id="shared-create-key",
        character_definition_id="character.player.default",
    )
    second = await service.create(
        principal("player-2"),
        client_request_id="shared-create-key",
        character_definition_id="character.player.default",
    )

    assert first.session_id != second.session_id
    assert len(store.sessions) == len(store.snapshots) == 2


@pytest.mark.asyncio
async def test_create_key_cannot_be_reused_for_a_different_supported_character(
    service_and_store: tuple[SessionService, Store],
) -> None:
    service, _ = service_and_store
    payload = service.catalog.model_dump(mode="json")
    alternative = dict(payload["characters"][0])
    alternative["definition_id"] = "character.player.alternative"
    alternative["display_name"] = "Alternative"
    payload["characters"].append(alternative)
    service.catalog = type(service.catalog).model_validate(payload)
    await service.create(
        principal(),
        client_request_id="create-conflict",
        character_definition_id="character.player.default",
    )

    with pytest.raises(IdempotencyConflictError):
        await service.create(
            principal(),
            client_request_id="create-conflict",
            character_definition_id="character.player.alternative",
        )


@pytest.mark.asyncio
async def test_create_key_reused_with_unknown_character_is_still_a_conflict(
    service_and_store: tuple[SessionService, Store],
) -> None:
    service, _ = service_and_store
    await service.create(
        principal(),
        client_request_id="create-conflict-unknown",
        character_definition_id="character.player.default",
    )

    with pytest.raises(IdempotencyConflictError):
        await service.create(
            principal(),
            client_request_id="create-conflict-unknown",
            character_definition_id="missing-character",
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("mismatched_binding", ["player", "request", "character", "content"])
async def test_create_winner_recovery_revalidates_all_bindings(
    service_and_store: tuple[SessionService, Store], mismatched_binding: str
) -> None:
    service, store = service_and_store
    created = await service.create(
        principal(),
        client_request_id="create-winner-binding",
        character_definition_id="character.player.default",
    )
    winner = store.sessions[created.session_id]
    if mismatched_binding == "player":
        winner = replace(
            winner,
            session=replace(winner.session, player_id="other-player"),
        )
    elif mismatched_binding == "request":
        winner = replace(winner, creation_client_request_id="other-request")
    elif mismatched_binding == "character":
        winner = replace(winner, character_definition_id="other-character")
    else:
        winner = replace(
            winner,
            session=replace(winner.session, scenario_version="other-content"),
        )
    store.sessions[created.session_id] = winner
    store.hidden_creation_lookups = 1

    expected_error = (
        SnapshotContentVersionMismatchError
        if mismatched_binding == "content"
        else IdempotencyConflictError
    )
    with pytest.raises(expected_error):
        await service.create(
            principal(),
            client_request_id="create-winner-binding",
            character_definition_id="character.player.default",
        )


@pytest.mark.asyncio
async def test_other_player_gets_same_safe_not_found_boundary(
    service_and_store: tuple[SessionService, Store],
) -> None:
    service, _ = service_and_store
    created = await service.create(
        principal(),
        client_request_id="create-owned",
        character_definition_id="character.player.default",
    )

    with pytest.raises(SessionNotFoundError):
        await service.get_metadata(principal("other-player"), created.session_id)
    with pytest.raises(SessionNotFoundError):
        await service.get_visible_state(principal("other-player"), created.session_id)
    with pytest.raises(SessionNotFoundError):
        await service.require_owner(principal("other-player"), created.session_id)


@pytest.mark.asyncio
async def test_visible_projection_hides_authoritative_npcs_and_is_deeply_isolated(
    service_and_store: tuple[SessionService, Store],
) -> None:
    service, store = service_and_store
    created = await service.create(
        principal(),
        client_request_id="create-projection",
        character_definition_id="character.player.default",
    )
    snapshot = store.snapshots[created.session_id]
    state = GameState.from_snapshot(snapshot.state, catalog=service.catalog)
    npc_definition = service.catalog.npc("npc.demo.guard")
    npc_character = service.catalog.character("character.npc.guard")
    assert npc_definition is not None and npc_character is not None
    state.npcs["runtime-hidden-guard"] = NpcState.from_definition(
        "runtime-hidden-guard", npc_definition, npc_character
    )
    store.snapshots[created.session_id] = PersistedSnapshot(0, state.to_snapshot())

    projection = await service.get_visible_state(principal(), created.session_id)

    assert projection.visible_npcs == ()
    assert "npcs" not in projection.model_dump()
    with pytest.raises(ValidationError):
        projection.resources[0].current = 0
    authoritative = GameState.from_snapshot(
        store.snapshots[created.session_id].state, catalog=service.catalog
    )
    assert authoritative.player.resources["stamina"].current == 10


@pytest.mark.asyncio
async def test_metadata_does_not_contain_snapshot_or_internal_fields(
    service_and_store: tuple[SessionService, Store],
) -> None:
    service, _ = service_and_store
    created = await service.create(
        principal(),
        client_request_id="create-metadata",
        character_definition_id="character.player.default",
    )
    payload = (await service.get_metadata(principal(), created.session_id)).model_dump()
    assert set(payload) == {
        "session_id",
        "phase",
        "state_version",
        "content_version",
        "created_at",
        "updated_at",
        "character_definition_id",
        "character_display_name",
    }
    assert not ({"random_seed", "snapshot", "npcs", "trusted_context"} & set(payload))
