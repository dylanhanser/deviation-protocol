from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field as dataclass_field
from datetime import datetime, timezone
from enum import StrEnum
import secrets
from typing import Annotated, Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from deviation_protocol.application.errors import (
    ConcurrentSessionCreateError,
    IdempotencyConflictError,
    InvalidCharacterDefinitionError,
    InvalidScenarioDefinitionError,
    NarrativeRequestNotFoundError,
    SessionNotFoundError,
    SnapshotContentVersionMismatchError,
    SnapshotInvalidError,
    SnapshotNotFoundError,
    SnapshotSchemaVersionMismatchError,
    SnapshotSessionMismatchError,
    SnapshotStateVersionMismatchError,
    StoredTurnResponseInvalidError,
)
from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.narrative_jobs import NarrativeJobStatus
from deviation_protocol.application.continue_policy import ScenarioContinuePolicy
from deviation_protocol.application.narrative_outcome_policy import (
    NarrativeActionAvailability,
    available_narrative_actions,
)
from deviation_protocol.application.ports import PersistedSession, UnitOfWorkFactory
from deviation_protocol.application.player_memory import (
    DeclarativePlayerMemoryRuleEngine,
    PlayerMemoryProjection,
    PlayerMemoryProjector,
)
from deviation_protocol.application.scenario_event_bridge import (
    bind_public_decision_frame,
)
from deviation_protocol.application.scenario_initialization import (
    ScenarioInitializationError,
    initialize_scenario_state,
    profession_tags_for,
)
from deviation_protocol.application.story_director import (
    DeterministicStoryDirector,
    StoryDirectorError,
)
from deviation_protocol.application.turn_response import TurnResponse
from deviation_protocol.domain.content import ContentCatalog
from deviation_protocol.domain.models import GameSession
from deviation_protocol.domain.events import DomainEvent
from deviation_protocol.domain.actions import ActionType
from deviation_protocol.domain.narrative import NarrativeFrame, VisibleClock
from deviation_protocol.domain.policies import ActionInputKind, InputContractPolicy
from deviation_protocol.domain.scenario import EndingStatus, ScenarioCatalog, ScenarioDefinition
from deviation_protocol.domain.state import DomainRuleViolation, GameState, PlayerState


Clock = Callable[[], datetime]
SessionIdGenerator = Callable[[], str]
SeedGenerator = Callable[[], int]
EventIdGenerator = Callable[[], str]
MAX_VIEW_RECENT_NARRATIVES = 6
MAX_VIEW_RECENT_NARRATIVE_CHARACTERS = 12_000
MAX_VIEW_RECENT_NARRATIVE_UTF8_BYTES = 24_000
NARRATIVE_REQUEST_RETRY_AFTER_SECONDS = 2


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


class PublicPlayableCharacter(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    character_definition_id: str
    display_name: str
    description: str


class PublicScenarioDescription(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    scenario_id: str
    content_version: str
    title: str
    hook: str
    playable_characters: tuple[PublicPlayableCharacter, ...] = Field(
        max_length=16
    )
    default_character_definition_id: str


class PublicScenarioCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    scenarios: tuple[PublicScenarioDescription, ...] = Field(max_length=32)


class PublicEndingPresentation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    title: str
    summary: str


class PublicScenarioPresentation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    title: str
    scene_title: str
    scene_summary: str
    ending: PublicEndingPresentation | None = None


class PublicActionTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    target_id: str
    display_name: str


class PublicActionAffordance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    action_type: ActionType
    label: str
    input_kind: ActionInputKind
    max_input_length: int | None = Field(default=None, ge=1, le=2_000)
    target_required: bool
    targets: tuple[PublicActionTarget, ...] = Field(default=(), max_length=128)

    @model_validator(mode="after")
    def validate_input_shape(self) -> PublicActionAffordance:
        if (self.input_kind is ActionInputKind.NONE) != (
            self.max_input_length is None
        ):
            raise ValueError("action input length does not match its input kind")
        if self.target_required and not self.targets:
            raise ValueError("required action target list cannot be empty")
        return self


class PublicDecisionChoice(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    action_type: Literal[ActionType.CHOOSE] = ActionType.CHOOSE
    choice_id: str
    label: str
    target_ids: tuple[str, ...] = Field(default=(), max_length=16)


class PublicActionMode(StrEnum):
    FREE_ACTIONS = "FREE_ACTIONS"
    DECISION = "DECISION"
    ENDED = "ENDED"


class PublicActionAffordanceSet(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    mode: PublicActionMode
    actions: tuple[PublicActionAffordance, ...] = Field(default=(), max_length=16)
    decision_id: str | None = None
    choices: tuple[PublicDecisionChoice, ...] = Field(default=(), max_length=32)

    @model_validator(mode="after")
    def validate_mode_shape(self) -> PublicActionAffordanceSet:
        if self.mode is PublicActionMode.DECISION:
            valid = self.decision_id is not None and bool(self.choices) and not self.actions
        elif self.mode is PublicActionMode.FREE_ACTIONS:
            valid = self.decision_id is None and not self.choices
        else:
            valid = self.decision_id is None and not self.choices and not self.actions
        if not valid:
            raise ValueError("public action affordance mode has an invalid shape")
        return self


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
    player_memory: PlayerMemoryProjection = Field(
        default_factory=PlayerMemoryProjection
    )


class PublicNarrativeRequestStatus(StrEnum):
    PENDING = "PENDING"
    COMMITTED = "COMMITTED"
    STALE = "STALE"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
    FAILED = "FAILED"


class NarrativeRequestClientAction(StrEnum):
    POLL_SAME_REQUEST = "POLL_SAME_REQUEST"
    RESPONSE_AVAILABLE = "RESPONSE_AVAILABLE"
    REFRESH_VIEW = "REFRESH_VIEW"
    DO_NOT_RETRY = "DO_NOT_RETRY"


class NarrativeRequestStatusResult(BaseModel):
    """Application result; API code must project TurnResponse before serialization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: Annotated[str, Field(strict=True, min_length=1, max_length=64)]
    client_request_id: Annotated[str, Field(strict=True, min_length=1, max_length=64)]
    status: PublicNarrativeRequestStatus
    client_action: NarrativeRequestClientAction
    error_code: Annotated[
        str, Field(strict=True, pattern=r"^[A-Z][A-Z0-9_]{0,127}$")
    ] | None = None
    retry_after_seconds: int | None = Field(default=None, ge=1, le=60)
    response: TurnResponse | None = None

    @model_validator(mode="after")
    def validate_public_status_shape(self) -> NarrativeRequestStatusResult:
        if self.status is PublicNarrativeRequestStatus.PENDING:
            if (
                self.client_action is not NarrativeRequestClientAction.POLL_SAME_REQUEST
                or self.retry_after_seconds is None
                or self.error_code is not None
                or self.response is not None
            ):
                raise ValueError("pending narrative status has an invalid shape")
            return self
        if self.status is PublicNarrativeRequestStatus.COMMITTED:
            if (
                self.client_action
                is not NarrativeRequestClientAction.RESPONSE_AVAILABLE
                or self.response is None
                or self.retry_after_seconds is not None
                or self.error_code is not None
            ):
                raise ValueError("committed narrative status has an invalid shape")
            return self
        expected = {
            PublicNarrativeRequestStatus.STALE: (
                NarrativeRequestClientAction.REFRESH_VIEW,
                "NARRATIVE_REQUEST_STALE",
            ),
            PublicNarrativeRequestStatus.OUTCOME_UNKNOWN: (
                NarrativeRequestClientAction.DO_NOT_RETRY,
                "NARRATIVE_OUTCOME_UNKNOWN",
            ),
            PublicNarrativeRequestStatus.FAILED: (
                NarrativeRequestClientAction.DO_NOT_RETRY,
                "NARRATIVE_REQUEST_FAILED",
            ),
        }[self.status]
        if (
            (self.client_action, self.error_code) != expected
            or self.retry_after_seconds is not None
            or self.response is not None
        ):
            raise ValueError("terminal narrative status has an invalid shape")
        return self


class PlayerSessionView(BaseModel):
    """Reconnect-safe aggregate built only from validated player projections."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    metadata: SessionMetadata
    narrative_frame: NarrativeFrame
    player_state: PlayerVisibleStateProjection
    player_memory: PlayerMemoryProjection
    presentation: PublicScenarioPresentation
    action_affordances: PublicActionAffordanceSet
    scenario_status: Literal["ACTIVE", "ENDED"]
    public_clocks: tuple[VisibleClock, ...] = Field(default=(), max_length=32)
    recent_narrative_texts: tuple[
        Annotated[str, Field(strict=True, min_length=1, max_length=10_000)], ...
    ] = Field(default=(), max_length=MAX_VIEW_RECENT_NARRATIVES)
    ending_id: str | None = None

    @model_validator(mode="after")
    def validate_view_shape(self) -> PlayerSessionView:
        if (
            self.metadata.session_id != self.player_state.session_id
            or self.metadata.state_version != self.player_state.state_version
            or self.metadata.phase != self.player_state.phase
            or self.metadata.content_version != self.player_state.content_version
            or self.player_memory != self.player_state.player_memory
            or self.public_clocks != self.narrative_frame.player_visible_clocks
        ):
            raise ValueError("player session view projections do not share one authority")
        if (self.scenario_status == "ACTIVE") != (self.ending_id is None):
            raise ValueError("ending is visible only for an ended scenario")
        if (self.scenario_status == "ACTIVE") != (
            self.presentation.ending is None
        ):
            raise ValueError("ending presentation is visible only after settlement")
        if (self.scenario_status == "ENDED") != (
            self.action_affordances.mode is PublicActionMode.ENDED
        ):
            raise ValueError("ended scenario cannot expose action affordances")
        if sum(map(len, self.recent_narrative_texts)) > (
            MAX_VIEW_RECENT_NARRATIVE_CHARACTERS
        ) or sum(
            len(text.encode("utf-8")) for text in self.recent_narrative_texts
        ) > MAX_VIEW_RECENT_NARRATIVE_UTF8_BYTES:
            raise ValueError("recent narrative texts exceed the public view budget")
        return self


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
    event_id_generator: EventIdGenerator = lambda: str(uuid4())
    memory_rule_engine: DeclarativePlayerMemoryRuleEngine = dataclass_field(
        default_factory=DeclarativePlayerMemoryRuleEngine
    )
    memory_projector: PlayerMemoryProjector = dataclass_field(
        default_factory=PlayerMemoryProjector
    )
    continue_policy: ScenarioContinuePolicy = dataclass_field(
        default_factory=ScenarioContinuePolicy
    )

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

    def list_public_scenarios(self) -> PublicScenarioCatalog:
        definitions = (
            self.scenario_catalog.scenarios
            if self.scenario_catalog is not None
            else ()
        )
        scenarios: list[PublicScenarioDescription] = []
        for definition in sorted(definitions, key=lambda item: item.scenario_id):
            public = definition.public_client
            if public is None:
                continue
            playable = tuple(
                PublicPlayableCharacter(
                    character_definition_id=item.character_definition_id,
                    display_name=self.catalog.character(
                        item.character_definition_id
                    ).display_name,  # type: ignore[union-attr]
                    description=item.description,
                )
                for item in sorted(
                    public.playable_characters,
                    key=lambda value: value.character_definition_id,
                )
            )
            scenarios.append(
                PublicScenarioDescription(
                    scenario_id=definition.scenario_id,
                    content_version=definition.content_version,
                    title=public.title,
                    hook=public.hook,
                    playable_characters=playable,
                    default_character_definition_id=(
                        public.default_character_definition_id
                    ),
                )
            )
        return PublicScenarioCatalog(scenarios=tuple(scenarios))

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
                try:
                    started = initialize_scenario_state(
                        state,
                        self.catalog,
                        definition,
                        character_tags=character.tags,
                        story_director=self.story_director,
                    )
                except ScenarioInitializationError:
                    raise InvalidScenarioDefinitionError(definition.scenario_id) from None
                state = started.candidate_state
                initial_frame = bind_public_decision_frame(
                    started.frame,
                    session_id=session.session_id,
                    state_version=0,
                    scenario_content_version=definition.content_version,
                )
            state.validate_against(self.catalog)
            if definition is None:
                await uow.sessions.add_initial(
                    session,
                    character_definition_id=character_definition_id,
                    creation_client_request_id=client_request_id,
                    state=state.to_snapshot(),
                    created_at=created_at,
                )
            else:
                await uow.sessions.add_initial_session(
                    session,
                    character_definition_id=character_definition_id,
                    creation_client_request_id=client_request_id,
                    created_at=created_at,
                )
                event_id = self.event_id_generator()
                if not isinstance(event_id, str) or not 1 <= len(event_id) <= 64:
                    raise ValueError("event ID generator returned an invalid value")
                sequence_no = await uow.sessions.next_event_sequence_no(
                    session.session_id
                )
                started_event = DomainEvent(
                    event_id=event_id,
                    session_id=session.session_id,
                    turn_id="session-created",
                    sequence_no=sequence_no,
                    event_type="ScenarioStarted",
                    payload={
                        "scenario_id": definition.scenario_id,
                        "scenario_content_version": definition.content_version,
                    },
                    occurred_at=created_at,
                )
                receipts = await uow.sessions.persist_events(
                    (started_event,), state_version=0
                )
                state = self.memory_rule_engine.apply(
                    state=state,
                    definition=definition,
                    session_id=session.session_id,
                    turn_id="session-created",
                    state_version=0,
                    receipts=receipts,
                )
                await uow.sessions.add_initial_snapshot(
                    session, state=state.to_snapshot(), created_at=created_at
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

    async def get_view(
        self, principal: RequestPrincipal, session_id: str
    ) -> PlayerSessionView:
        async with self.uow_factory() as uow:
            persisted = await uow.sessions.get_owned(session_id, principal.player_id)
            if persisted is None:
                raise SessionNotFoundError(session_id)
            try:
                snapshot = await uow.sessions.get_latest_snapshot(session_id)
                if snapshot is None:
                    raise SnapshotNotFoundError(session_id)
                state = self._load_state(
                    persisted, snapshot.state_version, snapshot.state
                )
                runtime = state.scenario_runtime
                if runtime is None:
                    raise SnapshotInvalidError(session_id)
                definition = self._scenario_definition(runtime.scenario_id)
                if definition is None:  # pragma: no cover - helper raises
                    raise SnapshotInvalidError(session_id)
                character = self.catalog.character(
                    state.player.character_definition_id
                )
                if character is None:
                    raise SnapshotInvalidError(session_id)
                frame = bind_public_decision_frame(
                    self.story_director.plan_frame(
                        state,
                        definition,
                        profession_tags=profession_tags_for(
                            character.tags, definition
                        ),
                    ),
                    session_id=session_id,
                    state_version=persisted.session.state_version,
                    scenario_content_version=definition.content_version,
                )
                projected = self._project(persisted, state)
                ended = runtime.ending_status is not EndingStatus.ACTIVE
                presentation = self._public_presentation(
                    definition,
                    phase_id=runtime.current_phase_id,
                    ending_id=runtime.ending_id if ended else None,
                )
                action_affordances = self._public_action_affordances(
                    state=state,
                    definition=definition,
                    frame=frame,
                    visible_npcs=projected.visible_npcs,
                    ended=ended,
                )
            except (
                InvalidScenarioDefinitionError,
                SnapshotContentVersionMismatchError,
                SnapshotInvalidError,
                SnapshotNotFoundError,
                SnapshotSchemaVersionMismatchError,
                SnapshotSessionMismatchError,
                SnapshotStateVersionMismatchError,
                StoryDirectorError,
            ):
                raise SnapshotInvalidError(session_id) from None
            recent = await uow.narrative_jobs.recent_committed_texts(
                session_id, limit=MAX_VIEW_RECENT_NARRATIVES
            )
            return PlayerSessionView(
                metadata=self._metadata(persisted),
                narrative_frame=frame,
                player_state=projected,
                player_memory=projected.player_memory,
                presentation=presentation,
                action_affordances=action_affordances,
                scenario_status="ENDED" if ended else "ACTIVE",
                public_clocks=frame.player_visible_clocks,
                recent_narrative_texts=self._bounded_recent_texts(recent),
                ending_id=runtime.ending_id if ended else None,
            )

    async def get_narrative_request_status(
        self,
        principal: RequestPrincipal,
        session_id: str,
        client_request_id: str,
    ) -> NarrativeRequestStatusResult:
        async with self.uow_factory() as uow:
            if await uow.sessions.get_owned(session_id, principal.player_id) is None:
                raise SessionNotFoundError(session_id)
            stored = await uow.turn_requests.get_by_client_request_id(
                session_id, client_request_id
            )
            if stored is not None:
                try:
                    response = TurnResponse.model_validate(stored.response)
                except (ValidationError, TypeError, ValueError):
                    raise StoredTurnResponseInvalidError(session_id) from None
                if (
                    response.session_id != session_id
                    or response.client_request_id != client_request_id
                    or response.action_signature != stored.action_signature
                ):
                    raise StoredTurnResponseInvalidError(session_id)
                return NarrativeRequestStatusResult(
                    session_id=session_id,
                    client_request_id=client_request_id,
                    status=PublicNarrativeRequestStatus.COMMITTED,
                    client_action=NarrativeRequestClientAction.RESPONSE_AVAILABLE,
                    response=response,
                )
            job = await uow.narrative_jobs.get_by_client_request_id(
                session_id, client_request_id
            )
            if job is None:
                raise NarrativeRequestNotFoundError(session_id)
            if job.status in {
                NarrativeJobStatus.PREPARED,
                NarrativeJobStatus.IN_PROGRESS,
                NarrativeJobStatus.PROPOSAL_VALIDATED,
            }:
                return NarrativeRequestStatusResult(
                    session_id=session_id,
                    client_request_id=client_request_id,
                    status=PublicNarrativeRequestStatus.PENDING,
                    client_action=NarrativeRequestClientAction.POLL_SAME_REQUEST,
                    retry_after_seconds=NARRATIVE_REQUEST_RETRY_AFTER_SECONDS,
                )
            if job.status is NarrativeJobStatus.STALE:
                return NarrativeRequestStatusResult(
                    session_id=session_id,
                    client_request_id=client_request_id,
                    status=PublicNarrativeRequestStatus.STALE,
                    client_action=NarrativeRequestClientAction.REFRESH_VIEW,
                    error_code="NARRATIVE_REQUEST_STALE",
                )
            if job.status is NarrativeJobStatus.OUTCOME_UNKNOWN:
                return NarrativeRequestStatusResult(
                    session_id=session_id,
                    client_request_id=client_request_id,
                    status=PublicNarrativeRequestStatus.OUTCOME_UNKNOWN,
                    client_action=NarrativeRequestClientAction.DO_NOT_RETRY,
                    error_code="NARRATIVE_OUTCOME_UNKNOWN",
                )
            if job.status in {
                NarrativeJobStatus.FAILED_RETRYABLE,
                NarrativeJobStatus.FAILED_TERMINAL,
            }:
                return NarrativeRequestStatusResult(
                    session_id=session_id,
                    client_request_id=client_request_id,
                    status=PublicNarrativeRequestStatus.FAILED,
                    client_action=NarrativeRequestClientAction.DO_NOT_RETRY,
                    error_code="NARRATIVE_REQUEST_FAILED",
                )
            raise StoredTurnResponseInvalidError(session_id)

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
        if type(payload.get("schema_version")) is not int or payload.get("schema_version") not in (1, 2, 3):
            raise SnapshotSchemaVersionMismatchError(session.session_id)
        if payload.get("content_version") != self.catalog.content_version:
            raise SnapshotContentVersionMismatchError(session.session_id)
        try:
            state = GameState.from_snapshot(
                payload,
                catalog=self.catalog,
                scenario_catalog=self.scenario_catalog,
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
                profession_tags=profession_tags_for(character.tags, definition),
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

    @staticmethod
    def _public_presentation(
        definition: ScenarioDefinition,
        *,
        phase_id: str,
        ending_id: str | None,
    ) -> PublicScenarioPresentation:
        public = definition.public_client
        if public is None:
            raise InvalidScenarioDefinitionError(definition.scenario_id)
        scene = next((item for item in public.scenes if item.phase_id == phase_id), None)
        if scene is None:
            raise InvalidScenarioDefinitionError(definition.scenario_id)
        ending = None
        if ending_id is not None:
            declared = next(
                (item for item in public.endings if item.ending_id == ending_id),
                None,
            )
            if declared is None:
                raise InvalidScenarioDefinitionError(definition.scenario_id)
            ending = PublicEndingPresentation(
                title=declared.title,
                summary=declared.summary,
            )
        return PublicScenarioPresentation(
            title=public.title,
            scene_title=scene.title,
            scene_summary=scene.summary,
            ending=ending,
        )

    def _public_action_affordances(
        self,
        *,
        state: GameState,
        definition: ScenarioDefinition,
        frame: NarrativeFrame,
        visible_npcs: tuple[PublicNpc, ...],
        ended: bool,
    ) -> PublicActionAffordanceSet:
        if ended:
            return PublicActionAffordanceSet(mode=PublicActionMode.ENDED)
        if frame.decision_required:
            return PublicActionAffordanceSet(
                mode=PublicActionMode.DECISION,
                decision_id=frame.decision_id,
                choices=tuple(
                    PublicDecisionChoice(
                        choice_id=item.action_id,
                        label=item.label_hint,
                        target_ids=item.target_ids,
                    )
                    for item in frame.suggested_actions
                ),
            )
        public = definition.public_client
        if public is None:
            raise InvalidScenarioDefinitionError(definition.scenario_id)
        labels = {item.action_type: item.label for item in public.actions}
        targets = tuple(
            PublicActionTarget(target_id=item.npc_id, display_name=item.display_name)
            for item in visible_npcs
            if item.npc_id in frame.visible_entities
        )
        available_by_type = {
            item.action_type: item
            for item in available_narrative_actions(
                state=state,
                definition=definition,
                frame=frame,
            )
        }
        if self.continue_policy.allows(state=state, frame=frame):
            available_by_type[ActionType.CONTINUE] = NarrativeActionAvailability(
                action_type=ActionType.CONTINUE,
            )
        actions: list[PublicActionAffordance] = []
        for item in sorted(
            available_by_type.values(), key=lambda value: value.action_type.value
        ):
            contract = InputContractPolicy.contract_for(item.action_type)
            label = labels.get(item.action_type)
            if contract is None or label is None:
                raise InvalidScenarioDefinitionError(definition.scenario_id)
            if contract.target_required and not targets:
                continue
            actions.append(
                PublicActionAffordance(
                    action_type=item.action_type,
                    label=label,
                    input_kind=contract.input_kind,
                    max_input_length=contract.max_length,
                    target_required=contract.target_required,
                    targets=targets if contract.target_supported else (),
                )
            )
        return PublicActionAffordanceSet(
            mode=PublicActionMode.FREE_ACTIONS,
            actions=tuple(actions),
        )

    @staticmethod
    def _bounded_recent_texts(texts: tuple[str, ...]) -> tuple[str, ...]:
        selected: list[str] = []
        character_count = 0
        byte_count = 0
        for text in reversed(texts[-MAX_VIEW_RECENT_NARRATIVES:]):
            text_characters = len(text)
            text_bytes = len(text.encode("utf-8"))
            if (
                character_count + text_characters
                > MAX_VIEW_RECENT_NARRATIVE_CHARACTERS
                or byte_count + text_bytes > MAX_VIEW_RECENT_NARRATIVE_UTF8_BYTES
            ):
                continue
            selected.append(text)
            character_count += text_characters
            byte_count += text_bytes
        return tuple(reversed(selected))

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
            player_memory=self.memory_projector.project(state, self.scenario_catalog),
        )
