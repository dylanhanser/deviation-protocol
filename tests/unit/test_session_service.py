from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import pytest
from pydantic import ValidationError

from deviation_protocol.application.errors import (
    ConcurrentSessionCreateError,
    IdempotencyConflictError,
    InvalidCharacterDefinitionError,
    InvalidScenarioDefinitionError,
    SessionNotFoundError,
    SnapshotContentVersionMismatchError,
    SnapshotInvalidError,
    SnapshotSchemaVersionMismatchError,
    SnapshotSessionMismatchError,
    SnapshotStateVersionMismatchError,
)
from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.ports import PersistedSession, PersistedSnapshot
from deviation_protocol.application.session_service import (
    PreparedRunEntryInitialization,
    SessionCreationResult,
    SessionService,
)
from deviation_protocol.application.run_operations import RunEntryCreationEvidence
from deviation_protocol.domain.models import GameSession
from deviation_protocol.domain.events import DomainEvent
from deviation_protocol.domain.persisted_events import _issue_persisted_event_receipt
from deviation_protocol.domain.player_character import (
    ApplicableCharacterReference,
    PlayerCharacterContractVersion,
    PlayerCharacterId,
    PlayerCharacterRevision,
)
from deviation_protocol.domain.run import (
    ContinuousStoryLineId,
    RunAuthoritySourceRef,
    RunId,
    RunOperationId,
    RunSessionParticipationReference,
    RunStateVersion,
)
from deviation_protocol.domain.state import DomainRuleViolation, GameState, NpcState
from deviation_protocol.infrastructure.content_loader import JsonContentCatalogLoader
from deviation_protocol.infrastructure.scenario_loader import JsonScenarioCatalogLoader


CONTENT_PACK = Path(__file__).parents[2] / "config" / "demo_content_pack.json"
SCENARIO_PACK = (
    Path(__file__).parents[2]
    / "config"
    / "scenarios"
    / "death_certificate_v1.json"
)
NOW = datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc)


class Store:
    def __init__(self) -> None:
        self.sessions: dict[str, PersistedSession] = {}
        self.snapshots: dict[str, PersistedSnapshot] = {}
        self.events: list[DomainEvent] = []
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
        await self.add_initial_session(
            session,
            character_definition_id=character_definition_id,
            creation_client_request_id=creation_client_request_id,
            created_at=created_at,
        )
        await self.add_initial_snapshot(session, state=state, created_at=created_at)

    async def add_initial_session(
        self,
        session: GameSession,
        *,
        character_definition_id: str,
        creation_client_request_id: str,
        created_at: datetime,
    ) -> None:
        self.uow.pending_session = PersistedSession(
            session=replace(session),
            character_definition_id=character_definition_id,
            creation_client_request_id=creation_client_request_id,
            created_at=created_at,
            updated_at=created_at,
        )

    async def add_initial_snapshot(
        self,
        session: GameSession,
        *,
        state: Mapping[str, Any],
        created_at: datetime,
    ) -> None:
        self.uow.pending_snapshot = PersistedSnapshot(
            session.state_version, deepcopy(dict(state))
        )

    async def next_event_sequence_no(self, session_id: str) -> int:
        return max(
            (
                event.sequence_no
                for event in self.store.events
                if event.session_id == session_id
            ),
            default=0,
        ) + 1

    async def persist_events(
        self, events: tuple[DomainEvent, ...], *, state_version: int
    ):
        self.uow.pending_events = tuple(events)
        return tuple(
            _issue_persisted_event_receipt(event, state_version=state_version)
            for event in events
        )

    async def get_latest_snapshot(self, session_id: str) -> PersistedSnapshot | None:
        return deepcopy(self.store.snapshots.get(session_id))


class Uow:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.sessions = Repository(store, self)
        self.turn_requests = None
        self.pending_session: PersistedSession | None = None
        self.pending_snapshot: PersistedSnapshot | None = None
        self.pending_events: tuple[DomainEvent, ...] = ()
        self.committed = False

    async def __aenter__(self) -> Uow:
        return self

    async def __aexit__(self, *args: object) -> None:
        if not self.committed:
            self.pending_session = None
            self.pending_snapshot = None
            self.pending_events = ()

    async def commit(self) -> None:
        if self.store.fail_commit:
            raise RuntimeError("simulated commit failure")
        assert self.pending_session is not None and self.pending_snapshot is not None
        persisted, snapshot = self.pending_session, self.pending_snapshot
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
            self.store.events.extend(deepcopy(self.pending_events))
            self.store.creation_keys[key] = session_id  # type: ignore[index]
        self.committed = True

    async def rollback(self) -> None:
        self.pending_session = None
        self.pending_snapshot = None
        self.pending_events = ()


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


def _run_entry_evidence(*, content_version: str) -> RunEntryCreationEvidence:
    return RunEntryCreationEvidence.model_validate(
        {
            "controller_operation": {
                "controller_binding": {"value": "controller.example"},
                "public_operation_key": "entry.example",
            },
            "player_character": {
                "player_character_id": {"value": "pc.example"},
                "pre_entry_record_revision": {"value": 1},
            },
            "scenario": {
                "scenario_id": "death_certificate",
                "content_version": content_version,
                "default_character_definition_id": (
                    "character.death_certificate.investigator"
                ),
            },
            "trusted_run_source": {
                "source_reference": {"value": "source.production-run"}
            },
        }
    )


async def _staged_run_entry(
    service: SessionService,
    store: Store,
) -> tuple[
    PreparedRunEntryInitialization,
    PersistedSession,
    PersistedSnapshot,
    DomainEvent,
]:
    definition = service.resolve_run_entry_definition("death_certificate")
    prepared = service.prepare_run_entry_initialization(
        principal(),
        creation_request_id="a" * 64,
        definition=definition,
        character_definition_id=(
            "character.death_certificate.investigator"
        ),
        created_at=NOW,
    )
    uow = Uow(store)
    await service.stage_run_entry_initialization(uow, prepared)
    assert uow.pending_session is not None
    assert uow.pending_snapshot is not None
    assert len(uow.pending_events) == 1
    return (
        prepared,
        uow.pending_session,
        uow.pending_snapshot,
        uow.pending_events[0],
    )


@pytest.fixture
def scenario_service_and_store() -> tuple[SessionService, Store]:
    scenario_catalog = JsonScenarioCatalogLoader(SCENARIO_PACK).load()
    store = Store()
    ids = iter((f"scenario-session-{index}" for index in range(1, 20)))
    return (
        SessionService(
            uow_factory=lambda: Uow(store),  # type: ignore[arg-type]
            catalog=scenario_catalog.content_catalog,
            scenario_catalog=scenario_catalog,
            clock=lambda: NOW,
            session_id_generator=lambda: next(ids),
            seed_generator=lambda: 42,
            event_id_generator=lambda: "scenario-start-event",
        ),
        store,
    )


@pytest.mark.asyncio
async def test_create_scenario_builds_v3_runtime_and_safe_initial_frame(
    scenario_service_and_store: tuple[SessionService, Store],
) -> None:
    service, store = scenario_service_and_store
    result = await service.create(
        principal(),
        client_request_id="create-death-certificate",
        character_definition_id="character.death_certificate.investigator",
        scenario_id="death_certificate",
    )

    assert isinstance(result, SessionCreationResult)
    assert result.scenario_id == "death_certificate"
    assert result.narrative_frame.decision_id is not None
    assert result.narrative_frame.decision_id.startswith("decision.")
    assert result.narrative_frame.decision_id != (
        "death_certificate.decision.immediate_survival"
    )
    snapshot = store.snapshots[result.session_id]
    state = GameState.from_snapshot(
        snapshot.state,
        catalog=service.catalog,
        scenario_catalog=service.scenario_catalog,
    )
    assert snapshot.state["schema_version"] == 3
    assert state.scenario_runtime is not None
    assert state.scenario_runtime.scenario_id == "death_certificate"
    assert state.scenario_runtime.scenario_content_version == (
        "death-certificate-1.1.0"
    )
    assert set(state.npcs) == {
        "scenario-npc-1",
        "scenario-npc-2",
        "scenario-npc-3",
    }
    assert tuple(state.npcs) == (
        "scenario-npc-1",
        "scenario-npc-2",
        "scenario-npc-3",
    )
    assert [
        (npc_id, npc.definition_id)
        for npc_id, npc in state.npcs.items()
    ] == [
        (
            "scenario-npc-1",
            "npc.death_certificate.triage_coordinator",
        ),
        (
            "scenario-npc-2",
            "npc.death_certificate.records_custodian",
        ),
        (
            "scenario-npc-3",
            "npc.death_certificate.underground_patient",
        ),
    ]
    stable_json = lambda value: json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    assert hashlib.sha256(stable_json(snapshot.state)).hexdigest() == (
        "90c67ba155dc5613fed1fc2df78b85012fe1606e5b25d22d2eb2db4861446441"
    )
    assert len(store.events) == 1
    assert store.events[0].event_type == "ScenarioStarted"
    assert len(state.player_memory.scenario_records) == 1
    assert len(state.player_memory.known_public_facts) == 7
    assert len(state.player_memory.significant_experiences) == 1
    assert result.narrative_frame.decision_id == (
        "decision.6403b6c1ecc381356e375b4b717ba593"
    )
    assert result.narrative_frame.frame_id == "frame.82f4a302af086d3f1d55b1e2"
    assert result.narrative_frame.allowed_custom_action_constraints is None
    assert all(
        item.action_type == "choice" and not item.target_ids
        for item in result.narrative_frame.suggested_actions
    )
    assert hashlib.sha256(
        stable_json(result.narrative_frame.model_dump(mode="json"))
    ).hexdigest() == "5c417270d577f0b6a5c887e82426c439b42d01c4a70419a12903521ccae3eefd"
    assert hashlib.sha256(
        stable_json(result.model_dump(mode="json"))
    ).hexdigest() == "b40c79ee96369b21c615503892749438e2e06314ad923993d1f67ca5cdd8738e"
    projection = await service.get_visible_state(principal(), result.session_id)
    assert [(item.npc_id, item.npc_definition_id) for item in projection.visible_npcs] == [
        (
            "scenario-npc-1",
            "npc.death_certificate.triage_coordinator",
        )
    ]
    serialized = result.model_dump_json()
    for forbidden in (
        "prediction_causes_outcome",
        "underground_patient_alive",
        "death_certificate.ending.",
        "death_certificate.decision.",
        "_issuer",
        "sealed_payload",
    ):
        assert forbidden not in serialized


@pytest.mark.asyncio
async def test_scenario_creation_replay_returns_same_frame_and_conflicts_on_scenario(
    scenario_service_and_store: tuple[SessionService, Store],
) -> None:
    service, store = scenario_service_and_store
    kwargs = {
        "client_request_id": "create-replay-frame",
        "character_definition_id": "character.death_certificate.investigator",
        "scenario_id": "death_certificate",
    }
    first = await service.create(principal(), **kwargs)
    snapshot_before = deepcopy(store.snapshots[first.session_id])
    replay = await service.create(principal(), **kwargs)
    assert first == replay
    assert store.snapshots[first.session_id] == snapshot_before
    assert len(store.sessions) == len(store.snapshots) == 1

    scenario_catalog = service.scenario_catalog
    assert scenario_catalog is not None
    payload = scenario_catalog.model_dump(mode="json")
    alternate = deepcopy(payload["scenarios"][0])
    alternate["scenario_id"] = "death_certificate_alternate"
    payload["scenarios"].append(alternate)
    service.scenario_catalog = type(scenario_catalog).model_validate(payload)
    with pytest.raises(IdempotencyConflictError):
        await service.create(
            principal(),
            client_request_id="create-replay-frame",
            character_definition_id="character.death_certificate.investigator",
            scenario_id="death_certificate_alternate",
        )


@pytest.mark.asyncio
async def test_creation_replay_fails_explicitly_after_catalog_version_upgrade(
    scenario_service_and_store: tuple[SessionService, Store],
) -> None:
    service, store = scenario_service_and_store
    kwargs = {
        "client_request_id": "create-before-upgrade",
        "character_definition_id": "character.death_certificate.investigator",
        "scenario_id": "death_certificate",
    }
    created = await service.create(principal(), **kwargs)
    before = deepcopy(store.snapshots[created.session_id])
    assert service.scenario_catalog is not None
    payload = service.scenario_catalog.model_dump(mode="json")
    payload["content_version"] = "death-certificate-2.0.0"
    payload["content_catalog"]["content_version"] = "death-certificate-2.0.0"
    payload["scenarios"][0]["content_version"] = "death-certificate-2.0.0"
    upgraded = type(service.scenario_catalog).model_validate(payload)
    service.scenario_catalog = upgraded
    service.catalog = upgraded.content_catalog

    with pytest.raises(SnapshotContentVersionMismatchError):
        await service.create(principal(), **kwargs)

    assert store.snapshots[created.session_id] == before
    assert len(store.sessions) == len(store.snapshots) == 1


@pytest.mark.asyncio
async def test_public_decision_ids_are_bound_to_the_created_session(
    scenario_service_and_store: tuple[SessionService, Store],
) -> None:
    service, _ = scenario_service_and_store
    common = {
        "character_definition_id": "character.death_certificate.investigator",
        "scenario_id": "death_certificate",
    }
    first = await service.create(
        principal(), client_request_id="create-decision-a", **common
    )
    second = await service.create(
        principal(), client_request_id="create-decision-b", **common
    )
    assert isinstance(first, SessionCreationResult)
    assert isinstance(second, SessionCreationResult)
    assert first.narrative_frame.decision_id != second.narrative_frame.decision_id


@pytest.mark.asyncio
async def test_scenario_creation_rejects_player_npc_runtime_id_collision(
    scenario_service_and_store: tuple[SessionService, Store],
) -> None:
    service, store = scenario_service_and_store
    with pytest.raises(DomainRuleViolation):
        await service.create(
            principal("scenario-npc-1"),
            client_request_id="create-colliding-runtime-id",
            character_definition_id="character.death_certificate.investigator",
            scenario_id="death_certificate",
        )
    assert store.sessions == store.snapshots == {}


@pytest.mark.asyncio
async def test_unknown_scenario_is_stable_and_leaves_no_partial_rows(
    scenario_service_and_store: tuple[SessionService, Store],
) -> None:
    service, store = scenario_service_and_store
    with pytest.raises(InvalidScenarioDefinitionError):
        await service.create(
            principal(),
            client_request_id="create-missing-scenario",
            character_definition_id="character.death_certificate.investigator",
            scenario_id="missing_scenario",
        )
    assert store.sessions == store.snapshots == {}


@pytest.mark.asyncio
async def test_scenario_creation_commit_failure_rolls_back_runtime_snapshot(
    scenario_service_and_store: tuple[SessionService, Store],
) -> None:
    service, store = scenario_service_and_store
    store.fail_commit = True
    with pytest.raises(RuntimeError, match="commit failure"):
        await service.create(
            principal(),
            client_request_id="create-scenario-failure",
            character_definition_id="character.death_certificate.investigator",
            scenario_id="death_certificate",
        )
    assert store.sessions == store.snapshots == {}


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


def test_run_entry_definition_enforces_the_exact_32_character_boundary(
    scenario_service_and_store: tuple[SessionService, Store],
) -> None:
    service, _ = scenario_service_and_store
    original = service.resolve_run_entry_definition("death_certificate")

    def install_version(value: str) -> None:
        content = service.catalog.model_copy(update={"content_version": value})
        definition = original.model_copy(update={"content_version": value})
        assert service.scenario_catalog is not None
        service.catalog = content
        service.scenario_catalog = service.scenario_catalog.model_copy(
            update={
                "content_version": value,
                "content_catalog": content,
                "scenarios": (definition,),
            }
        )

    install_version("v" * 32)
    assert (
        service.resolve_run_entry_definition("death_certificate").content_version
        == "v" * 32
    )

    install_version("v" * 33)
    with pytest.raises(InvalidScenarioDefinitionError):
        service.resolve_run_entry_definition("death_certificate")


@pytest.mark.asyncio
async def test_run_entry_snapshot_uses_strict_json_mode_and_full_round_trip(
    scenario_service_and_store: tuple[SessionService, Store],
) -> None:
    service, store = scenario_service_and_store
    prepared, persisted, snapshot, event = await _staged_run_entry(service, store)
    payload_before = deepcopy(snapshot.state)
    evidence = _run_entry_evidence(
        content_version=prepared.definition.content_version
    )
    participation = RunSessionParticipationReference(
        session_id=prepared.session.session_id,
        run_id=RunId(value="run.entry"),
        continuous_story_line_id=ContinuousStoryLineId(value="csl.entry"),
        joined_state_version=RunStateVersion(value=3),
        operation_id=RunOperationId(value="operation.attach"),
        source_reference=RunAuthoritySourceRef(value="source.production-run"),
    )
    reference = ApplicableCharacterReference(
        player_character_id=PlayerCharacterId(value="pc.example"),
        contract_version=PlayerCharacterContractVersion.V1,
        record_revision=PlayerCharacterRevision(value=1),
    )

    with pytest.raises(ValidationError):
        GameState.model_validate(snapshot.state, strict=True)
    json_state = GameState.model_validate_json(
        json.dumps(
            snapshot.state,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
        strict=True,
    )
    assert json_state.to_snapshot() == snapshot.state
    assert any(
        isinstance(value, tuple)
        for value in vars(json_state.scenario_runtime).values()
    )

    service.catalog = service.catalog.model_copy(
        update={"content_version": "catalogue-replaced"}
    )
    service.scenario_catalog = None
    validated = service.validate_run_entry_replay_initialization(
        persisted,
        snapshot,
        event,
        evidence,
        "a" * 64,
        participation=participation,
        applicable_character_reference=reference,
        transaction_time=NOW,
    )
    assert validated.to_snapshot() == payload_before
    assert snapshot.state == payload_before


@pytest.mark.asyncio
async def test_run_entry_snapshot_strict_and_semantic_negative_matrix(
    scenario_service_and_store: tuple[SessionService, Store],
) -> None:
    service, store = scenario_service_and_store
    prepared, persisted, snapshot, event = await _staged_run_entry(service, store)
    evidence = _run_entry_evidence(
        content_version=prepared.definition.content_version
    )
    participation = RunSessionParticipationReference(
        session_id=prepared.session.session_id,
        run_id=RunId(value="run.entry"),
        continuous_story_line_id=ContinuousStoryLineId(value="csl.entry"),
        joined_state_version=RunStateVersion(value=3),
        operation_id=RunOperationId(value="operation.attach"),
        source_reference=RunAuthoritySourceRef(value="source.production-run"),
    )
    reference = ApplicableCharacterReference(
        player_character_id=PlayerCharacterId(value="pc.example"),
        contract_version=PlayerCharacterContractVersion.V1,
        record_revision=PlayerCharacterRevision(value=1),
    )

    def validate(
        candidate: PersistedSnapshot = snapshot,
        *,
        session: PersistedSession = persisted,
        started: DomainEvent = event,
        run_participation: RunSessionParticipationReference = participation,
        character_reference: ApplicableCharacterReference = reference,
    ) -> GameState:
        return service.validate_run_entry_replay_initialization(
            session,
            candidate,
            started,
            evidence,
            "a" * 64,
            participation=run_participation,
            applicable_character_reference=character_reference,
            transaction_time=NOW,
        )

    payload = snapshot.state
    default_supplied = {
        key: value for key, value in payload.items() if key != "npcs"
    }
    normalized_collection = deepcopy(payload)
    normalized_collection["player_memory"]["scenario_records"][0][
        "milestone_refs"
    ] = ["STARTED", "IMPORTANT_FACT_CONFIRMED"]
    for normalized in (default_supplied, normalized_collection):
        reconstructed = GameState.model_validate_json(
            json.dumps(
                normalized,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
            strict=True,
        )
        assert reconstructed.to_snapshot() != normalized
        with pytest.raises(SnapshotInvalidError):
            validate(PersistedSnapshot(snapshot.state_version, normalized))

    malformed_payloads = (
        {**payload, "unknown": "x"},
        {key: value for key, value in payload.items() if key != "schema_version"},
        {**payload, "schema_version": True},
        {**payload, "content_version": 1},
        {**payload, "npcs": []},
        {**payload, "scenario_runtime": {**payload["scenario_runtime"], "ending_status": "UNKNOWN"}},
        {**payload, "player": {**payload["player"], "unknown": "x"}},
        {**payload, "player": {**payload["player"], "player_id": "bad identifier"}},
        {
            **payload,
            "player_memory": {
                **payload["player_memory"],
                "scenario_records": [
                    {
                        **payload["player_memory"]["scenario_records"][0],
                        "milestone_refs": [
                            *payload["player_memory"]["scenario_records"][0][
                                "milestone_refs"
                            ],
                            *payload["player_memory"]["scenario_records"][0][
                                "milestone_refs"
                            ],
                        ],
                    }
                ],
            },
        },
    )
    for index, malformed in enumerate(malformed_payloads):
        try:
            validate(PersistedSnapshot(snapshot.state_version, malformed))
        except (
            SnapshotInvalidError,
            SnapshotSchemaVersionMismatchError,
            SnapshotContentVersionMismatchError,
        ):
            continue
        pytest.fail(f"malformed snapshot case {index} was accepted")

    semantic_cases = (
        {"session": replace(persisted.session, state_version=1)},
        {"session": replace(persisted.session, scenario_id="other")},
        {"session": replace(persisted.session, scenario_version="other")},
        {"character_definition_id": "character.other"},
        {"creation_client_request_id": "b" * 64},
    )
    for change in semantic_cases:
        changed_session = replace(persisted, **change)
        with pytest.raises(
            (
                SnapshotInvalidError,
                SnapshotSessionMismatchError,
                SnapshotStateVersionMismatchError,
                SnapshotContentVersionMismatchError,
            )
        ):
            validate(session=changed_session)

    with pytest.raises(SnapshotSessionMismatchError):
        validate(
            run_participation=participation.model_copy(
                update={"session_id": "session.other"}
            )
        )
    with pytest.raises(SnapshotSessionMismatchError):
        validate(
            character_reference=reference.model_copy(
                update={
                    "record_revision": PlayerCharacterRevision(value=2)
                }
            )
        )
    with pytest.raises(SnapshotSessionMismatchError):
        validate(started=replace(event, sequence_no=2))
