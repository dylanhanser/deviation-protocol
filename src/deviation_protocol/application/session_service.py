from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field as dataclass_field
from datetime import datetime, timezone
import secrets
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from deviation_protocol.application.errors import (
    ConcurrentSessionCreateError,
    IdempotencyConflictError,
    InvalidCharacterDefinitionError,
    InvalidScenarioDefinitionError,
    SessionNotFoundError,
    SnapshotContentVersionMismatchError,
    SnapshotInvalidError,
    SnapshotNotFoundError,
    SnapshotSchemaVersionMismatchError,
    SnapshotSessionMismatchError,
    SnapshotStateVersionMismatchError,
)
from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.ports import PersistedSession, UnitOfWorkFactory
from deviation_protocol.application.scenario_event_bridge import (
    bind_public_decision_frame,
)
from deviation_protocol.application.story_director import (
    DeterministicStoryDirector,
    StoryDirectorError,
)
from deviation_protocol.domain.content import ContentCatalog
from deviation_protocol.domain.models import GameSession
from deviation_protocol.domain.narrative import NarrativeFrame
from deviation_protocol.domain.scenario import ScenarioCatalog, ScenarioDefinition
from deviation_protocol.domain.state import DomainRuleViolation, GameState, PlayerState


Clock = Callable[[], datetime]
SessionIdGenerator = Callable[[], str]
SeedGenerator = Callable[[], int]


def system_utc_clock() -> datetime:
    return datetime.now(timezone.utc)


def uuid_session_id() -> str:
    return f"session-{uuid4().hex}"


class PublicResource(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    resource_id: str
    current: int = Field(ge=0)
    maximum: int = Field(ge=0)


class PublicInventoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    item_instance_id: str
    item_definition_id: str
    display_name: str
    quantity: int = Field(ge=1)
    durability: int | None = Field(default=None, ge=0)
    charges: int | None = Field(default=None, ge=0)
    equipped_slot: str | None = None


class PublicSkill(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    skill_definition_id: str
    display_name: str
    level: int = Field(ge=1)
    proficiency: int = Field(ge=0)
    cooldown_remaining: int = Field(ge=0)
    uses: int = Field(ge=0)


class PublicNpc(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    npc_id: str
    npc_definition_id: str
    display_name: str


class PublicQuest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    quest_definition_id: str
    status: str


class SessionMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    session_id: str
    phase: str
    state_version: int = Field(ge=0)
    content_version: str
    created_at: datetime
    updated_at: datetime
    character_definition_id: str
    character_display_name: str


class SessionCreationResult(SessionMetadata):
    scenario_id: str
    narrative_frame: NarrativeFrame


class PlayerVisibleStateProjection(BaseModel):
    """Fresh player-safe data; never a reference to the authoritative aggregate."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    session_id: str
    phase: str
    state_version: int = Field(ge=0)
    content_version: str
    player_id: str
    character_definition_id: str
    attributes: tuple[tuple[str, int], ...]
    resources: tuple[PublicResource, ...]
    wallet: tuple[tuple[str, int], ...]
    inventory: tuple[PublicInventoryItem, ...]
    equipped_items: tuple[PublicInventoryItem, ...]
    skills: tuple[PublicSkill, ...]
    visible_npcs: tuple[PublicNpc, ...] = ()
    quests: tuple[PublicQuest, ...] = ()


@dataclass(slots=True)
class SessionService:
    uow_factory: UnitOfWorkFactory
    catalog: ContentCatalog
    scenario_catalog: ScenarioCatalog | None = None
    story_director: DeterministicStoryDirector = dataclass_field(
        default_factory=DeterministicStoryDirector
    )
    clock: Clock = system_utc_clock
    session_id_generator: SessionIdGenerator = uuid_session_id
    seed_generator: SeedGenerator = lambda: secrets.randbits(63)

    def __post_init__(self) -> None:
        if (
            self.scenario_catalog is not None
            and self.scenario_catalog.content_catalog != self.catalog
        ):
            raise ValueError("SessionService catalogs must describe the same content")

    async def create(
        self,
        principal: RequestPrincipal,
        *,
        client_request_id: str,
        character_definition_id: str,
        scenario_id: str | None = None,
    ) -> SessionMetadata | SessionCreationResult:
        try:
            return await self._create_once(
                principal,
                client_request_id=client_request_id,
                character_definition_id=character_definition_id,
                scenario_id=scenario_id,
            )
        except ConcurrentSessionCreateError:
            return await self._restore_create_winner(
                principal,
                client_request_id=client_request_id,
                character_definition_id=character_definition_id,
                scenario_id=scenario_id,
            )

    async def _create_once(
        self,
        principal: RequestPrincipal,
        *,
        client_request_id: str,
        character_definition_id: str,
        scenario_id: str | None,
    ) -> SessionMetadata | SessionCreationResult:
        async with self.uow_factory() as uow:
            existing = await uow.sessions.get_by_creation_request(
                principal.player_id, client_request_id
            )
            if existing is not None:
                metadata = self._validate_create_replay(
                    existing,
                    player_id=principal.player_id,
                    client_request_id=client_request_id,
                    character_definition_id=character_definition_id,
                    scenario_id=scenario_id,
                )
                if scenario_id is None:
                    return metadata
                return await self._creation_replay_result(uow, existing, metadata)

            character = self.catalog.character(character_definition_id)
            if character is None or "npc" in character.tags:
                raise InvalidCharacterDefinitionError(character_definition_id)
            definition = self._scenario_definition(scenario_id)
            created_at = self.clock()
            if created_at.tzinfo is None or created_at.utcoffset() is None:
                raise ValueError("session clock must return a timezone-aware datetime")
            created_at = created_at.astimezone(timezone.utc)
            session = GameSession(
                session_id=self.session_id_generator(),
                player_id=principal.player_id,
                scenario_id=(definition.scenario_id if definition is not None else "phase-1"),
                scenario_version=(
                    definition.content_version
                    if definition is not None
                    else self.catalog.content_version
                ),
                phase="AWAITING_ACTION",
                turn_number=0,
                state_version=0,
                random_seed=self.seed_generator(),
            )
            state = GameState(
                content_version=self.catalog.content_version,
                player=PlayerState.from_definition(principal.player_id, character),
            )
            initial_frame: NarrativeFrame | None = None
            if definition is not None:
                self._spawn_scenario_npcs(state, definition)
                started = self.story_director.start_scenario(
                    state,
                    definition,
                    profession_tags=self._profession_tags(
                        character.tags, definition
                    ),
                )
                state = started.candidate_state
                initial_frame = bind_public_decision_frame(
                    started.frame,
                    session_id=session.session_id,
                    state_version=0,
                    scenario_content_version=definition.content_version,
                )
            state.validate_against(self.catalog)
            await uow.sessions.add_initial(
                session,
                character_definition_id=character_definition_id,
                creation_client_request_id=client_request_id,
                state=state.to_snapshot(),
                created_at=created_at,
            )
            await uow.commit()
            metadata = self._metadata(
                PersistedSession(
                    session=session,
                    character_definition_id=character_definition_id,
                    creation_client_request_id=client_request_id,
                    created_at=created_at,
                    updated_at=created_at,
                )
            )
            if definition is None or initial_frame is None:
                return metadata
            return SessionCreationResult(
                **metadata.model_dump(),
                scenario_id=definition.scenario_id,
                narrative_frame=initial_frame,
            )

    async def _restore_create_winner(
        self,
        principal: RequestPrincipal,
        *,
        client_request_id: str,
        character_definition_id: str,
        scenario_id: str | None,
    ) -> SessionMetadata | SessionCreationResult:
        async with self.uow_factory() as uow:
            winner = await uow.sessions.get_by_creation_request(
                principal.player_id, client_request_id
            )
            if winner is None:
                raise RuntimeError("session creation conflict has no committed winner")
            metadata = self._validate_create_replay(
                winner,
                player_id=principal.player_id,
                client_request_id=client_request_id,
                character_definition_id=character_definition_id,
                scenario_id=scenario_id,
            )
            if scenario_id is None:
                return metadata
            return await self._creation_replay_result(uow, winner, metadata)

    async def get_metadata(
        self, principal: RequestPrincipal, session_id: str
    ) -> SessionMetadata:
        async with self.uow_factory() as uow:
            persisted = await uow.sessions.get_owned(session_id, principal.player_id)
            if persisted is None:
                raise SessionNotFoundError(session_id)
            return self._metadata(persisted)

    async def get_visible_state(
        self, principal: RequestPrincipal, session_id: str
    ) -> PlayerVisibleStateProjection:
        async with self.uow_factory() as uow:
            persisted = await uow.sessions.get_owned(session_id, principal.player_id)
            if persisted is None:
                raise SessionNotFoundError(session_id)
            snapshot = await uow.sessions.get_latest_snapshot(session_id)
            if snapshot is None:
                raise SnapshotNotFoundError(session_id)
            state = self._load_state(persisted, snapshot.state_version, snapshot.state)
            return self._project(persisted, state)

    async def require_owner(
        self, principal: RequestPrincipal, session_id: str
    ) -> None:
        async with self.uow_factory() as uow:
            if await uow.sessions.get_owned(session_id, principal.player_id) is None:
                raise SessionNotFoundError(session_id)

    def _load_state(
        self,
        persisted: PersistedSession,
        snapshot_version: int,
        payload: Mapping[str, Any],
    ) -> GameState:
        session = persisted.session
        if snapshot_version != session.state_version:
            raise SnapshotStateVersionMismatchError(session.session_id)
        if type(payload.get("schema_version")) is not int or payload.get("schema_version") not in (1, 2):
            raise SnapshotSchemaVersionMismatchError(session.session_id)
        if payload.get("content_version") != self.catalog.content_version:
            raise SnapshotContentVersionMismatchError(session.session_id)
        try:
            state = GameState.from_snapshot(
                payload,
                catalog=self.catalog,
                scenario_catalog=(
                    self.scenario_catalog
                    if payload.get("scenario_runtime") is not None
                    else None
                ),
            )
        except (DomainRuleViolation, ValidationError, TypeError, ValueError):
            raise SnapshotInvalidError(session.session_id) from None
        if state.player.player_id != session.player_id:
            raise SnapshotSessionMismatchError(session.session_id)
        runtime = state.scenario_runtime
        if runtime is not None and (
            runtime.scenario_id != session.scenario_id
            or runtime.scenario_content_version != session.scenario_version
        ):
            raise SnapshotSessionMismatchError(session.session_id)
        return state

    def _validate_create_replay(
        self,
        persisted: PersistedSession,
        *,
        player_id: str,
        client_request_id: str,
        character_definition_id: str,
        scenario_id: str | None,
    ) -> SessionMetadata:
        if scenario_id is not None:
            definition = self._scenario_definition(scenario_id)
            assert definition is not None
            if persisted.session.scenario_version != definition.content_version:
                raise SnapshotContentVersionMismatchError(
                    persisted.session.session_id
                )
        if (
            persisted.session.player_id != player_id
            or persisted.creation_client_request_id != client_request_id
            or persisted.character_definition_id != character_definition_id
            or (
                scenario_id is not None
                and persisted.session.scenario_id != scenario_id
            )
        ):
            raise IdempotencyConflictError(persisted.session.session_id)
        return self._metadata(persisted)

    async def _creation_replay_result(
        self,
        uow: Any,
        persisted: PersistedSession,
        metadata: SessionMetadata,
    ) -> SessionCreationResult:
        definition = self._scenario_definition(persisted.session.scenario_id)
        if definition is None:  # pragma: no cover - guarded by caller
            raise InvalidScenarioDefinitionError(persisted.session.scenario_id)
        snapshot = await uow.sessions.get_latest_snapshot(
            persisted.session.session_id
        )
        if snapshot is None:
            raise SnapshotNotFoundError(persisted.session.session_id)
        state = self._load_state(persisted, snapshot.state_version, snapshot.state)
        character = self.catalog.character(state.player.character_definition_id)
        assert character is not None
        try:
            frame = self.story_director.plan_initial_frame(
                state,
                definition,
                profession_tags=self._profession_tags(character.tags, definition),
            )
            frame = bind_public_decision_frame(
                frame,
                session_id=persisted.session.session_id,
                state_version=persisted.session.state_version,
                scenario_content_version=definition.content_version,
            )
        except StoryDirectorError:
            raise SnapshotInvalidError(persisted.session.session_id) from None
        return SessionCreationResult(
            **metadata.model_dump(),
            scenario_id=definition.scenario_id,
            narrative_frame=frame,
        )

    def _scenario_definition(
        self, scenario_id: str | None
    ) -> ScenarioDefinition | None:
        if scenario_id is None:
            return None
        definition = (
            self.scenario_catalog.scenario(scenario_id)
            if self.scenario_catalog is not None
            else None
        )
        if definition is None:
            raise InvalidScenarioDefinitionError(scenario_id)
        return definition

    def _spawn_scenario_npcs(
        self, state: GameState, definition: ScenarioDefinition
    ) -> None:
        for index, reference in enumerate(definition.npc_references, start=1):
            npc_definition = self.catalog.npc(reference.npc_definition_id)
            if npc_definition is None:  # protected by catalog validation
                raise InvalidScenarioDefinitionError(definition.scenario_id)
            npc_character = self.catalog.character(
                npc_definition.character_definition_id
            )
            if (
                npc_character is None
                or "npc" not in npc_character.tags
                or npc_character.definition_id
                == state.player.character_definition_id
            ):
                raise InvalidScenarioDefinitionError(definition.scenario_id)
            state.spawn_npc(
                self.catalog,
                reference.npc_definition_id,
                f"scenario-npc-{index}",
            )

    @staticmethod
    def _profession_tags(
        character_tags: tuple[str, ...], definition: ScenarioDefinition
    ) -> frozenset[str]:
        return frozenset(character_tags) & set(definition.available_profession_tags)

    def _metadata(self, persisted: PersistedSession) -> SessionMetadata:
        character_id = persisted.character_definition_id
        character = self.catalog.character(character_id or "")
        if character is None or persisted.session.scenario_version != self.catalog.content_version:
            raise SnapshotContentVersionMismatchError(persisted.session.session_id)
        return SessionMetadata(
            session_id=persisted.session.session_id,
            phase=persisted.session.phase,
            state_version=persisted.session.state_version,
            content_version=persisted.session.scenario_version,
            created_at=persisted.created_at,
            updated_at=persisted.updated_at,
            character_definition_id=character.definition_id,
            character_display_name=character.display_name,
        )

    def _project(
        self, persisted: PersistedSession, state: GameState
    ) -> PlayerVisibleStateProjection:
        items = tuple(
            PublicInventoryItem(
                item_instance_id=item.instance_id,
                item_definition_id=item.definition_id,
                display_name=(self.catalog.item(item.definition_id).display_name),  # type: ignore[union-attr]
                quantity=item.quantity,
                durability=item.durability,
                charges=item.charges,
                equipped_slot=(item.equipment.equipped_slot if item.equipment else None),
            )
            for _, item in sorted(state.player.inventory.items.items())
        )
        skills = tuple(
            PublicSkill(
                skill_definition_id=definition_id,
                display_name=(self.catalog.skill(definition_id).display_name),  # type: ignore[union-attr]
                level=skill.level,
                proficiency=skill.proficiency,
                cooldown_remaining=skill.cooldown_remaining,
                uses=skill.uses,
            )
            for definition_id, skill in sorted(state.player.skills.items())
        )
        visible_npcs: tuple[PublicNpc, ...] = ()
        runtime = state.scenario_runtime
        if runtime is not None and self.scenario_catalog is not None:
            definition = self.scenario_catalog.scenario(runtime.scenario_id)
            if definition is None:  # protected by _load_state
                raise SnapshotInvalidError(persisted.session.session_id)
            location = next(
                item
                for item in definition.locations
                if item.location_id == runtime.current_location_id
            )
            visible_definition_ids = set(location.visible_entity_ids)
            visible_npcs = tuple(
                PublicNpc(
                    npc_id=npc_id,
                    npc_definition_id=npc.definition_id,
                    display_name=self.catalog.npc(npc.definition_id).display_name,  # type: ignore[union-attr]
                )
                for npc_id, npc in sorted(state.npcs.items())
                if npc.definition_id in visible_definition_ids
            )
        return PlayerVisibleStateProjection(
            session_id=persisted.session.session_id,
            phase=persisted.session.phase,
            state_version=persisted.session.state_version,
            content_version=state.content_version,
            player_id=state.player.player_id,
            character_definition_id=state.player.character_definition_id,
            attributes=tuple(sorted(state.player.attributes.items())),
            resources=tuple(
                PublicResource(resource_id=key, current=value.current, maximum=value.maximum)
                for key, value in sorted(state.player.resources.items())
            ),
            wallet=tuple(sorted(state.player.wallet.balances.items())),
            inventory=items,
            equipped_items=tuple(item for item in items if item.equipped_slot is not None),
            skills=skills,
            visible_npcs=visible_npcs,
            quests=(),
        )
