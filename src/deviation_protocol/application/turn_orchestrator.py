from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from deviation_protocol.application.action_context import (
    AuthoritativeActionContextFactory,
)
from deviation_protocol.application.action_gateway import ActionRoute
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
from deviation_protocol.application.ports import (
    PersistedTurnRequest,
    RuleResolver,
    UnitOfWorkFactory,
)
from deviation_protocol.application.resolution import ResolutionResult, ResolutionStatus
from deviation_protocol.application.turn_response import TurnResponse
from deviation_protocol.domain.actions import ActionSubmission
from deviation_protocol.domain.content import ContentCatalog
from deviation_protocol.domain.events import DomainEvent
from deviation_protocol.domain.state import (
    DomainErrorCode,
    DomainRuleViolation,
    GameState,
)


Clock = Callable[[], datetime]
EventIdGenerator = Callable[[], str]


def system_utc_clock() -> datetime:
    return datetime.now(timezone.utc)


def uuid_event_id() -> str:
    return str(uuid4())


@dataclass(slots=True)
class FirstPhaseTurnOrchestrator:
    """Deterministic Phase 1.3 turn pipeline with one atomic commit boundary."""

    resolver: RuleResolver
    uow_factory: UnitOfWorkFactory
    catalog: ContentCatalog
    context_factory: AuthoritativeActionContextFactory = field(
        default_factory=AuthoritativeActionContextFactory
    )
    clock: Clock = system_utc_clock
    event_id_generator: EventIdGenerator = uuid_event_id

    async def handle(self, submission: ActionSubmission) -> TurnResponse:
        try:
            return await self._handle_once(submission)
        except ConcurrentTurnRequestError:
            # The failed transaction has left the context manager and rolled back.
            # Re-read the winner in a fresh locked transaction without resolving
            # the action a second time.
            return await self._restore_concurrent_winner(submission)

    async def _handle_once(self, submission: ActionSubmission) -> TurnResponse:
        async with self.uow_factory() as uow:
            if not await uow.sessions.lock_for_turn(submission.session_id):
                raise SessionNotFoundError(submission.session_id)

            stored = await uow.turn_requests.get_by_client_request_id(
                submission.session_id,
                submission.client_request_id,
            )
            if stored is not None:
                return self._replay_response(stored, submission)

            game_session = await uow.sessions.get(submission.session_id)
            if game_session is None:
                raise SessionNotFoundError(submission.session_id)
            snapshot = await uow.sessions.get_latest_snapshot(submission.session_id)
            if snapshot is None:
                raise SnapshotNotFoundError(submission.session_id)
            if snapshot.state_version != game_session.state_version:
                raise SnapshotStateVersionMismatchError(submission.session_id)

            state = self._load_state(snapshot.state, submission.session_id)
            if state.player.player_id != game_session.player_id:
                raise SnapshotSessionMismatchError(submission.session_id)

            # This capability is minted only after the authoritative state has been
            # loaded. Scene visibility and skill-learning authority remain empty
            # until backed by trusted persisted sources in a later phase.
            trusted_context = self.context_factory.create_trusted(
                submission,
                state=state,
                catalog=self.catalog,
                current_turn_id=submission.turn_id,
                session_phase=game_session.phase,
                visible_entity_ids=(),
                interactable_entity_ids=(),
                environment_tool_ids=(),
                skill_learning_authorization=None,
                processed_client_request_ids=(),
            )
            resolution = await self.resolver.resolve(
                trusted_context,
                state,
                self.catalog,
            )
            if resolution.status is ResolutionStatus.ANOMALY_EVALUATION_REQUIRED:
                raise UnsupportedResolutionError(submission.session_id)

            expected_version = game_session.state_version
            resulting_version = expected_version
            if resolution.state_changed:
                candidate_snapshot = self._validated_candidate_snapshot(
                    resolution,
                    submission.session_id,
                    expected_player_id=game_session.player_id,
                )
                resulting_version = expected_version + 1
                first_sequence_no = await uow.sessions.next_event_sequence_no(
                    submission.session_id
                )
                events = self._envelope_events(
                    resolution,
                    submission,
                    first_sequence_no,
                )
                await uow.sessions.save_snapshot_and_events(
                    game_session,
                    candidate_snapshot,
                    events,
                    expected_state_version=expected_version,
                )

            response = self._build_response(
                submission,
                resolution,
                resulting_version,
            )
            await uow.turn_requests.add(
                submission,
                response.action_signature,
                self._route_for(resolution.status),
                response=response.to_persistence(),
            )
            await uow.commit()
            return response

    async def _restore_concurrent_winner(
        self, submission: ActionSubmission
    ) -> TurnResponse:
        async with self.uow_factory() as uow:
            if not await uow.sessions.lock_for_turn(submission.session_id):
                raise SessionNotFoundError(submission.session_id)
            stored = await uow.turn_requests.get_by_client_request_id(
                submission.session_id,
                submission.client_request_id,
            )
            if stored is None:
                raise RuntimeError(
                    "turn request uniqueness conflict has no committed winner"
                )
            return self._replay_response(stored, submission)

    def _load_state(
        self,
        payload: Mapping[str, Any],
        session_id: str,
    ) -> GameState:
        schema_version = payload.get("schema_version")
        if type(schema_version) is not int or schema_version not in (1, 2):
            raise SnapshotSchemaVersionMismatchError(session_id)
        if payload.get("content_version") != self.catalog.content_version:
            raise SnapshotContentVersionMismatchError(session_id)
        try:
            return GameState.from_snapshot(payload, catalog=self.catalog)
        except DomainRuleViolation as exc:
            if exc.code is DomainErrorCode.SNAPSHOT_CONTENT_MISMATCH:
                raise SnapshotContentVersionMismatchError(session_id) from None
            raise SnapshotInvalidError(session_id) from None
        except (ValidationError, TypeError, ValueError):
            raise SnapshotInvalidError(session_id) from None

    def _validated_candidate_snapshot(
        self,
        resolution: ResolutionResult,
        session_id: str,
        *,
        expected_player_id: str,
    ) -> dict[str, Any]:
        candidate = resolution.updated_state
        if (
            candidate is None
            or not resolution.events
            or candidate.player.player_id != expected_player_id
        ):
            raise CandidateStateInvalidError(session_id)
        try:
            snapshot = candidate.to_snapshot()
            GameState.from_snapshot(snapshot, catalog=self.catalog)
            return snapshot
        except (DomainRuleViolation, ValidationError, TypeError, ValueError):
            raise CandidateStateInvalidError(session_id) from None

    def _envelope_events(
        self,
        resolution: ResolutionResult,
        submission: ActionSubmission,
        first_sequence_no: int,
    ) -> tuple[DomainEvent, ...]:
        if first_sequence_no < 1:
            raise ValueError("event sequence numbers must start at one")
        events: list[DomainEvent] = []
        event_ids: set[str] = set()
        for offset, draft in enumerate(resolution.events):
            event_id = self.event_id_generator()
            if (
                not isinstance(event_id, str)
                or not 1 <= len(event_id) <= 64
                or event_id in event_ids
            ):
                raise ValueError("event ID generator returned an invalid or duplicate ID")
            event_ids.add(event_id)
            occurred_at = self.clock()
            if occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
                raise ValueError("event clock must return a timezone-aware datetime")
            events.append(
                DomainEvent(
                    event_id=event_id,
                    session_id=submission.session_id,
                    turn_id=submission.turn_id,
                    sequence_no=first_sequence_no + offset,
                    event_type=draft.event_type,
                    payload=_writable_json_copy(draft.payload),
                    occurred_at=occurred_at.astimezone(timezone.utc),
                )
            )
        return tuple(events)

    @staticmethod
    def _build_response(
        submission: ActionSubmission,
        resolution: ResolutionResult,
        resulting_state_version: int,
    ) -> TurnResponse:
        is_query = (
            resolution.status is ResolutionStatus.RESOLVED_LOCAL
            and not resolution.state_changed
        )
        is_narrative = resolution.status is ResolutionStatus.NARRATIVE_REQUIRED
        feedback_parameters = _writable_json_copy(resolution.feedback.parameters)
        return TurnResponse(
            session_id=submission.session_id,
            client_request_id=submission.client_request_id,
            action_signature=submission.action_signature(),
            resolution_kind=resolution.status,
            result_code=resolution.result_code,
            feedback_code=resolution.feedback.code,
            feedback_parameters=feedback_parameters,
            resulting_state_version=resulting_state_version,
            state_changed=resolution.state_changed,
            narrative_required=is_narrative,
            narrative_pending=is_narrative,
            local_query_result=(
                _writable_json_copy(resolution.feedback.parameters) if is_query else None
            ),
        )

    @staticmethod
    def _route_for(status: ResolutionStatus) -> ActionRoute:
        if status is ResolutionStatus.REJECTED_LOCAL:
            return ActionRoute.REJECT_LOCAL
        if status is ResolutionStatus.RESOLVED_LOCAL:
            return ActionRoute.RESOLVE_LOCAL
        if status is ResolutionStatus.NARRATIVE_REQUIRED:
            return ActionRoute.NARRATIVE_NORMAL
        raise ValueError("unsupported resolution status")

    @staticmethod
    def _replay_response(
        stored: PersistedTurnRequest,
        submission: ActionSubmission,
    ) -> TurnResponse:
        expected_signature = submission.action_signature()
        if (
            stored.turn_id != submission.turn_id
            or stored.action_signature != expected_signature
        ):
            raise IdempotencyConflictError(submission.session_id)
        try:
            response = TurnResponse.model_validate(stored.response)
        except (ValidationError, TypeError, ValueError):
            raise StoredTurnResponseInvalidError(submission.session_id) from None
        if (
            response.session_id != submission.session_id
            or response.client_request_id != submission.client_request_id
            or response.action_signature != stored.action_signature
        ):
            raise StoredTurnResponseInvalidError(submission.session_id)
        return response


def _writable_json_copy(value: Any) -> Any:
    """Detach frozen domain JSON into ordinary dict/list values for MySQL JSON."""

    return json.loads(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    )
