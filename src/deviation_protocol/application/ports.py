from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from types import TracebackType
from typing import Any, Mapping, Protocol, Sequence

from deviation_protocol.application.action_context import TrustedResolutionContext
from deviation_protocol.application.action_gateway import ActionRoute
from deviation_protocol.application.resolution import ResolutionResult
from deviation_protocol.application.turn_response import TurnResponse
from deviation_protocol.domain.actions import ActionContext, ActionSubmission
from deviation_protocol.domain.content import ContentCatalog
from deviation_protocol.domain.events import DomainEvent
from deviation_protocol.domain.models import GameSession
from deviation_protocol.domain.state import GameState


@dataclass(frozen=True, slots=True)
class RuleResolution:
    accepted: bool
    events: tuple[DomainEvent, ...] = ()
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class PersistedSnapshot:
    state_version: int
    state: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class PersistedTurnRequest:
    turn_id: str
    action_signature: str
    response: Mapping[str, Any] | None


@dataclass(frozen=True, slots=True)
class PersistedSession:
    session: GameSession
    character_definition_id: str | None
    creation_client_request_id: str | None
    created_at: datetime
    updated_at: datetime


class RuleResolver(Protocol):
    async def resolve(
        self,
        trusted_context: TrustedResolutionContext,
        state: GameState,
        catalog: ContentCatalog,
    ) -> ResolutionResult: ...


class AnomalyEvaluator(Protocol):
    """Only evaluates feasible actions already accepted by the local gateway."""

    async def evaluate(self, context: ActionContext) -> ActionRoute: ...


class StoryDirector(Protocol):
    async def build_prompt_context(
        self, context: ActionContext, events: Sequence[DomainEvent]
    ) -> Mapping[str, Any]: ...


class NarrativeProvider(Protocol):
    async def generate(self, narrative_context: Mapping[str, Any]) -> str: ...


class GameSessionRepository(ABC):
    @abstractmethod
    async def get_owned(self, session_id: str, player_id: str) -> PersistedSession | None:
        """Load safe session metadata using ownership as part of the query."""
        raise NotImplementedError

    @abstractmethod
    async def get_by_creation_request(
        self, player_id: str, client_request_id: str
    ) -> PersistedSession | None:
        raise NotImplementedError

    @abstractmethod
    async def add_initial(
        self,
        session: GameSession,
        *,
        character_definition_id: str,
        creation_client_request_id: str,
        state: Mapping[str, Any],
        created_at: datetime,
    ) -> None:
        """Stage a session and its version-zero snapshot in one UoW."""
        raise NotImplementedError

    @abstractmethod
    async def lock_for_turn(self, session_id: str) -> bool:
        """Serialize turn handling for one existing session within the UoW transaction."""
        raise NotImplementedError

    @abstractmethod
    async def get(self, session_id: str) -> GameSession | None:
        raise NotImplementedError

    @abstractmethod
    async def get_latest_snapshot(self, session_id: str) -> PersistedSnapshot | None:
        raise NotImplementedError

    @abstractmethod
    async def next_event_sequence_no(self, session_id: str) -> int:
        raise NotImplementedError

    @abstractmethod
    async def save_snapshot_and_events(
        self,
        session: GameSession,
        state: Mapping[str, Any],
        events: Sequence[DomainEvent],
        expected_state_version: int,
    ) -> None:
        raise NotImplementedError


class TurnRequestRepository(ABC):
    @abstractmethod
    async def get_by_client_request_id(
        self, session_id: str, client_request_id: str
    ) -> PersistedTurnRequest | None:
        raise NotImplementedError

    @abstractmethod
    async def add(
        self,
        submission: ActionSubmission,
        action_signature: str,
        route: ActionRoute,
        response: Mapping[str, Any],
    ) -> None:
        raise NotImplementedError


class UnitOfWork(ABC):
    sessions: GameSessionRepository
    turn_requests: TurnRequestRepository

    @abstractmethod
    async def __aenter__(self) -> "UnitOfWork":
        raise NotImplementedError

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def commit(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def rollback(self) -> None:
        raise NotImplementedError


class UnitOfWorkFactory(Protocol):
    def __call__(self) -> UnitOfWork: ...


class TurnOrchestrator(Protocol):
    """Stable boundary for deterministic, transactional turn processing."""

    async def handle(self, submission: ActionSubmission) -> TurnResponse: ...
