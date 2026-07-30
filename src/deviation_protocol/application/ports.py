from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from types import TracebackType
from typing import Any, Mapping, Protocol, Sequence

from deviation_protocol.application.action_context import TrustedResolutionContext
from deviation_protocol.application.action_gateway import ActionRoute
from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.narrative_models import NarrativeProvider
from deviation_protocol.application.narrative_jobs import NarrativeJob, NarrativeJobStatus
from deviation_protocol.application.resolution import ResolutionResult
from deviation_protocol.application.turn_response import TurnResponse
from deviation_protocol.domain.actions import ActionContext, ActionSubmission
from deviation_protocol.domain.content import ContentCatalog
from deviation_protocol.domain.events import DomainEvent
from deviation_protocol.domain.persisted_events import PersistedEventReceipt
from deviation_protocol.domain.models import GameSession
from deviation_protocol.domain.state import GameState
from deviation_protocol.domain.player_character import (
    ApplicableCharacterReference,
    CanonicalPlayerCharacter,
    ControllerBindingRef,
    PlayerCharacterId,
    PlayerCharacterLifecycle,
)
from deviation_protocol.application.player_character_operations import (
    CreationReceiptKey,
    MutationReceiptKey,
    StoredCreationSuccessReceipt,
    StoredMutationSuccessReceipt,
)
from deviation_protocol.application.run_operations import (
    RunReceiptKey,
    StoredRunSuccessReceipt,
)
from deviation_protocol.domain.run import (
    CanonicalRun,
    ContinuousStoryLineId,
    RunId,
    RunSessionParticipationReference,
)


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


class GameSessionRepository(ABC):
    @abstractmethod
    async def add_initial_session(
        self,
        session: GameSession,
        *,
        character_definition_id: str,
        creation_client_request_id: str,
        created_at: datetime,
    ) -> None:
        """Insert and flush the session row without committing."""
        raise NotImplementedError

    @abstractmethod
    async def add_initial_snapshot(
        self,
        session: GameSession,
        *,
        state: Mapping[str, Any],
        created_at: datetime,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_owned(self, session_id: str, player_id: str) -> PersistedSession | None:
        """Load safe session metadata using ownership as part of the query."""
        raise NotImplementedError

    async def get_owned_for_update(
        self,
        session_id: str,
        player_id: str,
    ) -> PersistedSession | None:
        """Lock an owned Session when a separate aggregate claims its identity."""
        return await self.get_owned(session_id, player_id)

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
    async def persist_events(
        self,
        events: Sequence[DomainEvent],
        *,
        state_version: int,
    ) -> tuple[PersistedEventReceipt, ...]:
        """Insert/flush events and return transaction-local receipts; never commit."""
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


class NarrativeJobRepository(ABC):
    @abstractmethod
    async def get_by_client_request_id(
        self, session_id: str, client_request_id: str, *, for_update: bool = False
    ) -> NarrativeJob | None:
        raise NotImplementedError

    @abstractmethod
    async def get(self, job_id: str, *, for_update: bool = False) -> NarrativeJob | None:
        raise NotImplementedError

    @abstractmethod
    async def get_active_for_session(self, session_id: str) -> NarrativeJob | None:
        raise NotImplementedError

    @abstractmethod
    async def add(self, job: NarrativeJob) -> None:
        raise NotImplementedError

    @abstractmethod
    async def replace(
        self,
        job: NarrativeJob,
        *,
        expected_status: NarrativeJobStatus,
        expected_lease_token: str | None = None,
        expected_lease_owner: str | None = None,
    ) -> bool:
        """CAS one lifecycle transition, including the current fencing lease."""
        raise NotImplementedError

    @abstractmethod
    async def recent_committed_texts(self, session_id: str, *, limit: int) -> tuple[str, ...]:
        raise NotImplementedError


class ControllerBindingUniquenessConflictError(RuntimeError):
    """Only the approved controller-binding add uniqueness race."""


class MutationReceiptUniquenessConflictError(RuntimeError):
    """Only the approved mutation-receipt add uniqueness race."""


class ControllerBindingResolver(Protocol):
    async def resolve(
        self,
        principal: RequestPrincipal,
        /,
    ) -> ControllerBindingRef | None: ...


class PlayerCharacterIdIssuer(Protocol):
    def issue(self) -> PlayerCharacterId: ...


class PlayerCharacterBindingEvidence(Protocol):
    applicable_character_reference: ApplicableCharacterReference
    lifecycle: PlayerCharacterLifecycle


class PlayerCharacterBindingEvidenceReader(Protocol):
    async def lock_owned_for_binding(
        self,
        uow: UnitOfWork,
        *,
        trusted_controller_binding: ControllerBindingRef,
        target_player_character_id: PlayerCharacterId,
    ) -> PlayerCharacterBindingEvidence | None: ...


class ControllerBindingRegistryRepository(ABC):
    @abstractmethod
    async def get(self, controller_binding: ControllerBindingRef) -> ControllerBindingRef | None:
        raise NotImplementedError

    @abstractmethod
    async def add(self, controller_binding: ControllerBindingRef, *, created_at: datetime) -> None:
        raise NotImplementedError

    @abstractmethod
    async def lock(self, controller_binding: ControllerBindingRef) -> ControllerBindingRef | None:
        raise NotImplementedError


class PlayerCharacterRepository(ABC):
    @abstractmethod
    async def allocation_exists(self, player_character_id: PlayerCharacterId) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def add_allocation(self, player_character_id: PlayerCharacterId, *, created_at: datetime) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get(self, player_character_id: PlayerCharacterId) -> CanonicalPlayerCharacter | None:
        raise NotImplementedError

    @abstractmethod
    async def get_for_update(self, player_character_id: PlayerCharacterId) -> CanonicalPlayerCharacter | None:
        raise NotImplementedError

    @abstractmethod
    async def add_initial(self, record: CanonicalPlayerCharacter, *, created_at: datetime) -> None:
        raise NotImplementedError

    @abstractmethod
    async def append_revision(self, record: CanonicalPlayerCharacter, *, created_at: datetime) -> None:
        raise NotImplementedError

    @abstractmethod
    async def compare_and_swap_current(self, record: CanonicalPlayerCharacter, *, expected_revision: int, created_at: datetime) -> bool:
        raise NotImplementedError


class PlayerCharacterCreationReceiptRepository(ABC):
    @abstractmethod
    async def get(self, key: CreationReceiptKey) -> StoredCreationSuccessReceipt | None:
        raise NotImplementedError

    @abstractmethod
    async def add(self, receipt: StoredCreationSuccessReceipt, *, created_at: datetime) -> None:
        raise NotImplementedError


class PlayerCharacterMutationReceiptRepository(ABC):
    @abstractmethod
    async def get(self, key: MutationReceiptKey) -> StoredMutationSuccessReceipt | None:
        raise NotImplementedError

    @abstractmethod
    async def add(self, receipt: StoredMutationSuccessReceipt, *, created_at: datetime) -> None:
        raise NotImplementedError


class RunSessionParticipationUniquenessConflictError(RuntimeError):
    """Only the immutable Session-participation primary-key race."""


class RunReceiptUniquenessConflictError(RuntimeError):
    """Only a Run successful-receipt unique-key race."""


class RunPlayerCharacterBindingUniquenessConflictError(RuntimeError):
    """Only the active-player-character current-row uniqueness race."""


@dataclass(frozen=True, slots=True)
class RunSessionAttachmentLockEvidence:
    """Complete canonical Run-family evidence read under the Run lock."""

    canonical_run: CanonicalRun
    attachment_receipt: StoredRunSuccessReceipt | None


class RunIdIssuer(Protocol):
    def issue(self) -> RunId: ...


class ContinuousStoryLineIdIssuer(Protocol):
    def issue(self) -> ContinuousStoryLineId: ...


class RunRepository(ABC):
    @abstractmethod
    async def get(self, run_id: RunId) -> CanonicalRun | None:
        raise NotImplementedError

    @abstractmethod
    async def get_for_update(self, run_id: RunId) -> CanonicalRun | None:
        raise NotImplementedError

    @abstractmethod
    async def get_session_attachment_lock_evidence(
        self,
        run_id: RunId,
        *,
        receipt_key: RunReceiptKey,
    ) -> RunSessionAttachmentLockEvidence | None:
        raise NotImplementedError

    @abstractmethod
    async def get_active_for_player_character(
        self,
        player_character_id: PlayerCharacterId,
    ) -> CanonicalRun | None:
        raise NotImplementedError

    @abstractmethod
    async def get_active_for_player_character_for_update(
        self,
        player_character_id: PlayerCharacterId,
    ) -> CanonicalRun | None:
        raise NotImplementedError

    @abstractmethod
    async def add_initial(self, run: CanonicalRun, *, created_at: datetime) -> None:
        raise NotImplementedError

    @abstractmethod
    async def append_revision(self, run: CanonicalRun, *, created_at: datetime) -> None:
        raise NotImplementedError

    @abstractmethod
    async def compare_and_swap_current(
        self,
        run: CanonicalRun,
        *,
        expected_state_version: int,
        updated_at: datetime,
    ) -> bool:
        raise NotImplementedError


class RunSessionParticipationRepository(ABC):
    @abstractmethod
    async def get(
        self, session_id: str
    ) -> RunSessionParticipationReference | None:
        raise NotImplementedError

    @abstractmethod
    async def add(
        self,
        participation: RunSessionParticipationReference,
        *,
        joined_at: datetime,
    ) -> None:
        raise NotImplementedError


class RunCreationReceiptRepository(ABC):
    @abstractmethod
    async def get(self, key: RunReceiptKey) -> StoredRunSuccessReceipt | None:
        raise NotImplementedError

    @abstractmethod
    async def add(
        self, receipt: StoredRunSuccessReceipt, *, created_at: datetime
    ) -> None:
        raise NotImplementedError


class RunMutationReceiptRepository(ABC):
    @abstractmethod
    async def get(self, key: RunReceiptKey) -> StoredRunSuccessReceipt | None:
        raise NotImplementedError

    @abstractmethod
    async def add(
        self, receipt: StoredRunSuccessReceipt, *, created_at: datetime
    ) -> None:
        raise NotImplementedError


class UnitOfWork(ABC):
    sessions: GameSessionRepository
    turn_requests: TurnRequestRepository
    narrative_jobs: NarrativeJobRepository
    controller_bindings: ControllerBindingRegistryRepository
    player_characters: PlayerCharacterRepository
    creation_receipts: PlayerCharacterCreationReceiptRepository
    mutation_receipts: PlayerCharacterMutationReceiptRepository
    runs: RunRepository
    run_participations: RunSessionParticipationRepository
    run_creation_receipts: RunCreationReceiptRepository
    run_mutation_receipts: RunMutationReceiptRepository

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
