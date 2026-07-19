from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from types import TracebackType
from typing import Any, Mapping, Protocol, Sequence

from deviation_protocol.application.action_gateway import ActionRoute
from deviation_protocol.domain.actions import ActionContext, ActionSubmission
from deviation_protocol.domain.events import DomainEvent
from deviation_protocol.domain.models import GameSession


@dataclass(frozen=True, slots=True)
class RuleResolution:
    accepted: bool
    events: tuple[DomainEvent, ...] = ()
    reason: str | None = None


class RuleResolver(Protocol):
    async def resolve(self, context: ActionContext) -> RuleResolution: ...


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
    async def lock_for_turn(self, session_id: str) -> bool:
        """Serialize turn handling for one existing session within the UoW transaction."""
        raise NotImplementedError

    @abstractmethod
    async def get(self, session_id: str) -> GameSession | None:
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
    ) -> Mapping[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    async def add(
        self,
        submission: ActionSubmission,
        action_signature: str,
        route: ActionRoute,
        response: Mapping[str, Any] | None = None,
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
    """Stable boundary for the full turn pipeline implemented in a later phase."""

    async def handle(self, submission: ActionSubmission) -> Mapping[str, Any]: ...
