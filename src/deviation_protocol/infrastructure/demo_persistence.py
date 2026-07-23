from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import datetime
from types import TracebackType
from typing import Any, Mapping, Sequence

from deviation_protocol.application.action_gateway import ActionRoute
from deviation_protocol.application.errors import (
    ConcurrentSessionCreateError,
    ConcurrentTurnRequestError,
)
from deviation_protocol.application.narrative_jobs import (
    ACTIVE_NARRATIVE_JOB_STATUSES,
    NarrativeJob,
    NarrativeJobStatus,
)
from deviation_protocol.application.ports import (
    GameSessionRepository,
    NarrativeJobRepository,
    PersistedSession,
    PersistedSnapshot,
    PersistedTurnRequest,
    TurnRequestRepository,
    UnitOfWork,
)
from deviation_protocol.domain.actions import ActionSubmission
from deviation_protocol.domain.events import DomainEvent
from deviation_protocol.domain.models import GameSession
from deviation_protocol.domain.persisted_events import (
    PersistedEventReceipt,
    _issue_persisted_event_receipt,
)
from deviation_protocol.infrastructure.errors import OptimisticLockError


def _clone_job(job: NarrativeJob) -> NarrativeJob:
    return NarrativeJob.model_validate(job.model_dump(mode="python"))


def _clone_session(session: GameSession) -> GameSession:
    return replace(session)


@dataclass(frozen=True, slots=True)
class DemoStoreSnapshot:
    sessions: dict[str, PersistedSession]
    snapshots: dict[str, PersistedSnapshot]
    creation_keys: dict[tuple[str, str], str]
    turn_requests: dict[tuple[str, str], PersistedTurnRequest]
    narrative_jobs: dict[str, NarrativeJob]
    events: tuple[DomainEvent, ...]
    provider_progress: dict[str, int]


class DemoProcessStore:
    """Process-lifetime storage used only by the explicit Demo composition root."""

    def __init__(self) -> None:
        self._sessions: dict[str, PersistedSession] = {}
        self._snapshots: dict[str, PersistedSnapshot] = {}
        self._creation_keys: dict[tuple[str, str], str] = {}
        self._turn_requests: dict[tuple[str, str], PersistedTurnRequest] = {}
        self._narrative_jobs: dict[str, NarrativeJob] = {}
        self._events: list[DomainEvent] = []
        self._provider_progress: dict[str, int] = {}
        self._session_locks: dict[str, asyncio.Lock] = {}
        self._commit_lock = asyncio.Lock()
        self._active_uows = 0

    def unit_of_work(self) -> DemoUnitOfWork:
        return DemoUnitOfWork(self)

    @property
    def active_uows(self) -> int:
        return self._active_uows

    @property
    def any_session_lock_held(self) -> bool:
        return any(lock.locked() for lock in self._session_locks.values())

    def session_lock_held(self, session_id: str) -> bool:
        lock = self._session_locks.get(session_id)
        return lock is not None and lock.locked()

    def snapshot(self) -> DemoStoreSnapshot:
        return DemoStoreSnapshot(
            sessions=deepcopy(self._sessions),
            snapshots=deepcopy(self._snapshots),
            creation_keys=deepcopy(self._creation_keys),
            turn_requests=deepcopy(self._turn_requests),
            narrative_jobs={
                key: _clone_job(value) for key, value in self._narrative_jobs.items()
            },
            events=deepcopy(tuple(self._events)),
            provider_progress=dict(self._provider_progress),
        )


@dataclass(slots=True)
class _StateUpdate:
    session: GameSession
    expected_version: int
    next_version: int
    state: dict[str, Any]


@dataclass(slots=True)
class _JobReplacement:
    job: NarrativeJob
    expected_status: NarrativeJobStatus
    expected_lease_token: str | None
    expected_lease_owner: str | None


@dataclass(frozen=True, slots=True)
class _ProviderProgressUpdate:
    session_id: str
    expected_progress: int
    next_progress: int


class DemoSessionRepository(GameSessionRepository):
    def __init__(self, store: DemoProcessStore, uow: DemoUnitOfWork) -> None:
        self._store = store
        self._uow = uow

    async def add_initial_session(
        self,
        session: GameSession,
        *,
        character_definition_id: str,
        creation_client_request_id: str,
        created_at: datetime,
    ) -> None:
        self._uow._ensure_open()
        if self._uow._pending_session is not None:
            raise ConcurrentSessionCreateError()
        persisted = PersistedSession(
            session=_clone_session(session),
            character_definition_id=character_definition_id,
            creation_client_request_id=creation_client_request_id,
            created_at=created_at,
            updated_at=created_at,
        )
        self._uow._pending_session = deepcopy(persisted)

    async def add_initial_snapshot(
        self,
        session: GameSession,
        *,
        state: Mapping[str, Any],
        created_at: datetime,
    ) -> None:
        del created_at
        self._uow._ensure_open()
        if self._uow._pending_snapshot is not None:
            raise OptimisticLockError("Demo initial snapshot is already staged")
        self._uow._pending_snapshot = (
            session.session_id,
            PersistedSnapshot(
                state_version=session.state_version,
                state=deepcopy(dict(state)),
            ),
        )

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

    async def get_owned(
        self, session_id: str, player_id: str
    ) -> PersistedSession | None:
        self._uow._ensure_open()
        value = self._visible_session(session_id)
        if value is None or value.session.player_id != player_id:
            return None
        return deepcopy(value)

    async def get_by_creation_request(
        self, player_id: str, client_request_id: str
    ) -> PersistedSession | None:
        self._uow._ensure_open()
        pending = self._uow._pending_session
        if (
            pending is not None
            and pending.session.player_id == player_id
            and pending.creation_client_request_id == client_request_id
        ):
            return deepcopy(pending)
        session_id = self._store._creation_keys.get((player_id, client_request_id))
        value = self._store._sessions.get(session_id) if session_id else None
        return deepcopy(value) if value is not None else None

    async def lock_for_turn(self, session_id: str) -> bool:
        self._uow._ensure_open()
        if self._uow._held_session_lock is not None:
            if self._uow._held_session_id != session_id:
                raise RuntimeError("one Demo UoW cannot lock multiple sessions")
            return self._visible_session(session_id) is not None
        lock = self._store._session_locks.setdefault(session_id, asyncio.Lock())
        await lock.acquire()
        self._uow._held_session_lock = lock
        self._uow._held_session_id = session_id
        return self._visible_session(session_id) is not None

    async def get(self, session_id: str) -> GameSession | None:
        self._uow._ensure_open()
        value = self._visible_session(session_id)
        return _clone_session(value.session) if value is not None else None

    async def get_latest_snapshot(self, session_id: str) -> PersistedSnapshot | None:
        self._uow._ensure_open()
        pending = self._uow._pending_snapshot
        if pending is not None and pending[0] == session_id:
            return deepcopy(pending[1])
        update = self._uow._pending_state_update
        if update is not None and update.session.session_id == session_id:
            return PersistedSnapshot(
                state_version=update.next_version,
                state=deepcopy(update.state),
            )
        value = self._store._snapshots.get(session_id)
        return deepcopy(value) if value is not None else None

    async def next_event_sequence_no(self, session_id: str) -> int:
        self._uow._ensure_open()
        return (
            max(
                (
                    event.sequence_no
                    for event in (*self._store._events, *self._uow._pending_events)
                    if event.session_id == session_id
                ),
                default=0,
            )
            + 1
        )

    async def persist_events(
        self, events: Sequence[DomainEvent], *, state_version: int
    ) -> tuple[PersistedEventReceipt, ...]:
        self._uow._ensure_open()
        detached = deepcopy(tuple(events))
        existing_ids = {
            item.event_id for item in (*self._store._events, *self._uow._pending_events)
        }
        existing_sequences = {
            (item.session_id, item.sequence_no)
            for item in (*self._store._events, *self._uow._pending_events)
        }
        batch_ids: set[str] = set()
        batch_sequences: set[tuple[str, int]] = set()
        for event in detached:
            sequence_key = (event.session_id, event.sequence_no)
            if (
                event.event_id in existing_ids
                or event.event_id in batch_ids
                or sequence_key in existing_sequences
                or sequence_key in batch_sequences
                or event.sequence_no < 1
            ):
                raise OptimisticLockError("Demo event identity or sequence conflict")
            if self._visible_session(event.session_id) is None:
                raise ValueError("Demo event refers to an unknown session")
            batch_ids.add(event.event_id)
            batch_sequences.add(sequence_key)
        self._uow._pending_events = (*self._uow._pending_events, *detached)
        return tuple(
            _issue_persisted_event_receipt(event, state_version=state_version)
            for event in detached
        )

    async def save_snapshot_and_events(
        self,
        session: GameSession,
        state: Mapping[str, Any],
        events: Sequence[DomainEvent],
        expected_state_version: int,
    ) -> None:
        self._uow._ensure_open()
        current = self._visible_session(session.session_id)
        if current is None or current.session.state_version != expected_state_version:
            raise OptimisticLockError(
                f"session {session.session_id!r} state_version changed concurrently"
            )
        if self._uow._pending_state_update is not None:
            raise RuntimeError("one Demo UoW cannot stage multiple snapshot updates")
        if events:
            await self.persist_events(events, state_version=expected_state_version + 1)
        original_version = session.state_version
        next_version = expected_state_version + 1
        session.state_version = next_version
        self._uow._pending_session_versions.append((session, original_version))
        self._uow._pending_state_update = _StateUpdate(
            session=_clone_session(session),
            expected_version=expected_state_version,
            next_version=next_version,
            state=deepcopy(dict(state)),
        )

    def _visible_session(self, session_id: str) -> PersistedSession | None:
        pending = self._uow._pending_session
        if pending is not None and pending.session.session_id == session_id:
            return pending
        return self._store._sessions.get(session_id)


class DemoTurnRequestRepository(TurnRequestRepository):
    def __init__(self, store: DemoProcessStore, uow: DemoUnitOfWork) -> None:
        self._store = store
        self._uow = uow

    async def get_by_client_request_id(
        self, session_id: str, client_request_id: str
    ) -> PersistedTurnRequest | None:
        self._uow._ensure_open()
        key = (session_id, client_request_id)
        pending = self._uow._pending_turn_requests.get(key)
        value = pending if pending is not None else self._store._turn_requests.get(key)
        return deepcopy(value) if value is not None else None

    async def add(
        self,
        submission: ActionSubmission,
        action_signature: str,
        route: ActionRoute,
        response: Mapping[str, Any],
    ) -> None:
        del route
        self._uow._ensure_open()
        key = (submission.session_id, submission.client_request_id)
        if key in self._store._turn_requests or key in self._uow._pending_turn_requests:
            raise ConcurrentTurnRequestError()
        self._uow._pending_turn_requests[key] = PersistedTurnRequest(
            turn_id=submission.turn_id,
            action_signature=action_signature,
            response=deepcopy(dict(response)),
        )


class DemoNarrativeJobRepository(NarrativeJobRepository):
    def __init__(self, store: DemoProcessStore, uow: DemoUnitOfWork) -> None:
        self._store = store
        self._uow = uow

    async def get_by_client_request_id(
        self,
        session_id: str,
        client_request_id: str,
        *,
        for_update: bool = False,
    ) -> NarrativeJob | None:
        del for_update
        self._uow._ensure_open()
        return next(
            (
                _clone_job(job)
                for job in self._visible_jobs().values()
                if job.session_id == session_id
                and job.client_request_id == client_request_id
            ),
            None,
        )

    async def get(
        self, job_id: str, *, for_update: bool = False
    ) -> NarrativeJob | None:
        del for_update
        self._uow._ensure_open()
        job = self._visible_jobs().get(job_id)
        return _clone_job(job) if job is not None else None

    async def get_active_for_session(self, session_id: str) -> NarrativeJob | None:
        self._uow._ensure_open()
        jobs = sorted(
            (
                job
                for job in self._visible_jobs().values()
                if job.session_id == session_id
                and job.status in ACTIVE_NARRATIVE_JOB_STATUSES
            ),
            key=lambda item: (item.created_at, item.job_id),
        )
        return _clone_job(jobs[0]) if jobs else None

    async def add(self, job: NarrativeJob) -> None:
        self._uow._ensure_open()
        visible = self._visible_jobs()
        if job.job_id in visible or any(
            item.session_id == job.session_id
            and item.client_request_id == job.client_request_id
            for item in visible.values()
        ):
            raise ConcurrentTurnRequestError()
        self._uow._pending_job_adds[job.job_id] = _clone_job(job)

    async def replace(
        self,
        job: NarrativeJob,
        *,
        expected_status: NarrativeJobStatus,
        expected_lease_token: str | None = None,
        expected_lease_owner: str | None = None,
    ) -> bool:
        self._uow._ensure_open()
        current = self._visible_jobs().get(job.job_id)
        if not _job_matches(
            current,
            expected_status=expected_status,
            expected_lease_token=expected_lease_token,
            expected_lease_owner=expected_lease_owner,
        ):
            return False
        self._uow._pending_job_replacements.setdefault(job.job_id, []).append(
            _JobReplacement(
                job=_clone_job(job),
                expected_status=expected_status,
                expected_lease_token=expected_lease_token,
                expected_lease_owner=expected_lease_owner,
            )
        )
        return True

    async def recent_committed_texts(
        self, session_id: str, *, limit: int
    ) -> tuple[str, ...]:
        self._uow._ensure_open()
        if limit == 0:
            return ()
        jobs = sorted(
            (
                job
                for job in self._visible_jobs().values()
                if job.session_id == session_id
                and job.status is NarrativeJobStatus.COMMITTED
                and job.accepted_narrative_text is not None
            ),
            key=lambda item: (item.updated_at, item.job_id),
        )[-limit:]
        return tuple(
            job.accepted_narrative_text
            for job in jobs
            if job.accepted_narrative_text is not None
        )

    def _visible_jobs(self) -> dict[str, NarrativeJob]:
        visible = dict(self._store._narrative_jobs)
        visible.update(self._uow._pending_job_adds)
        visible.update(
            {
                key: replacements[-1].job
                for key, replacements in self._uow._pending_job_replacements.items()
            }
        )
        return visible


class DemoUnitOfWork(UnitOfWork):
    def __init__(self, store: DemoProcessStore) -> None:
        self._store = store
        self.sessions = DemoSessionRepository(store, self)
        self.turn_requests = DemoTurnRequestRepository(store, self)
        self.narrative_jobs = DemoNarrativeJobRepository(store, self)
        self._pending_session: PersistedSession | None = None
        self._pending_snapshot: tuple[str, PersistedSnapshot] | None = None
        self._pending_state_update: _StateUpdate | None = None
        self._pending_events: tuple[DomainEvent, ...] = ()
        self._pending_turn_requests: dict[
            tuple[str, str], PersistedTurnRequest
        ] = {}
        self._pending_job_adds: dict[str, NarrativeJob] = {}
        self._pending_job_replacements: dict[
            str, list[_JobReplacement]
        ] = {}
        self._pending_session_versions: list[tuple[GameSession, int]] = []
        self._pending_provider_progress: _ProviderProgressUpdate | None = None
        self._held_session_lock: asyncio.Lock | None = None
        self._held_session_id: str | None = None
        self._entered = False
        self._closed = False
        self._committed = False

    async def __aenter__(self) -> DemoUnitOfWork:
        if self._entered or self._closed:
            raise RuntimeError("Demo UnitOfWork cannot be re-entered")
        self._entered = True
        self._store._active_uows += 1
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc, traceback
        try:
            if exc_type is not None or not self._committed:
                await self.rollback()
        finally:
            if self._held_session_lock is not None:
                self._held_session_lock.release()
                self._held_session_lock = None
                self._held_session_id = None
            self._closed = True
            self._store._active_uows -= 1

    async def commit(self) -> None:
        self._ensure_open()
        if self._committed:
            raise RuntimeError("Demo UnitOfWork has already committed")
        async with self._store._commit_lock:
            self._publish_atomically()
        self._pending_session_versions.clear()
        self._committed = True

    async def rollback(self) -> None:
        self._ensure_open(allow_committed=True)
        for session, previous_version in reversed(self._pending_session_versions):
            session.state_version = previous_version
        self._pending_session_versions.clear()
        self._clear_staged()
        if self._held_session_lock is not None:
            self._held_session_lock.release()
            self._held_session_lock = None
            self._held_session_id = None
        self._committed = False

    def stage_provider_progress(
        self,
        session_id: str,
        *,
        expected_progress: int,
        next_progress: int,
    ) -> None:
        """Stage Demo-only Provider authority in the gameplay transaction."""

        self._ensure_open()
        if self._pending_provider_progress is not None:
            raise RuntimeError("one Demo UoW cannot stage multiple Provider advances")
        if (
            type(expected_progress) is not int
            or type(next_progress) is not int
            or expected_progress < 0
            or next_progress != expected_progress + 1
        ):
            raise ValueError("invalid Demo Provider progress transition")
        if self._store._provider_progress.get(session_id) != expected_progress:
            raise OptimisticLockError("Demo Provider progress changed concurrently")
        self._pending_provider_progress = _ProviderProgressUpdate(
            session_id=session_id,
            expected_progress=expected_progress,
            next_progress=next_progress,
        )

    def _publish_atomically(self) -> None:
        sessions = deepcopy(self._store._sessions)
        snapshots = deepcopy(self._store._snapshots)
        creation_keys = dict(self._store._creation_keys)
        turn_requests = deepcopy(self._store._turn_requests)
        jobs = {
            key: _clone_job(value) for key, value in self._store._narrative_jobs.items()
        }
        events = deepcopy(self._store._events)
        provider_progress = dict(self._store._provider_progress)

        pending_session = self._pending_session
        if pending_session is not None:
            session_id = pending_session.session.session_id
            creation_id = pending_session.creation_client_request_id
            if creation_id is None:
                raise ValueError("Demo initial session requires a creation request ID")
            creation_key = (pending_session.session.player_id, creation_id)
            if session_id in sessions or creation_key in creation_keys:
                raise ConcurrentSessionCreateError()
            sessions[session_id] = deepcopy(pending_session)
            creation_keys[creation_key] = session_id
            provider_progress[session_id] = 0

        if self._pending_snapshot is not None:
            session_id, snapshot = self._pending_snapshot
            if session_id not in sessions:
                raise ValueError("Demo initial snapshot refers to an unknown session")
            if session_id in snapshots:
                raise OptimisticLockError("Demo initial snapshot already exists")
            snapshots[session_id] = deepcopy(snapshot)

        update = self._pending_state_update
        if update is not None:
            session_id = update.session.session_id
            current = sessions.get(session_id)
            current_snapshot = snapshots.get(session_id)
            if (
                current is None
                or current.session.state_version != update.expected_version
                or current_snapshot is None
                or current_snapshot.state_version != update.expected_version
            ):
                raise OptimisticLockError(
                    f"session {session_id!r} state changed before Demo commit"
                )
            updated_at = max(
                (
                    event.occurred_at
                    for event in self._pending_events
                    if event.session_id == session_id
                ),
                default=current.updated_at,
            )
            sessions[session_id] = replace(
                current,
                session=_clone_session(update.session),
                updated_at=updated_at,
            )
            snapshots[session_id] = PersistedSnapshot(
                state_version=update.next_version,
                state=deepcopy(update.state),
            )

        for key, value in self._pending_turn_requests.items():
            if key in turn_requests:
                raise ConcurrentTurnRequestError()
            if key[0] not in sessions:
                raise ValueError("Demo turn request refers to an unknown session")
            turn_requests[key] = deepcopy(value)

        for job_id, job in self._pending_job_adds.items():
            if job_id in jobs or any(
                item.session_id == job.session_id
                and item.client_request_id == job.client_request_id
                for item in jobs.values()
            ):
                raise ConcurrentTurnRequestError()
            if job.session_id not in sessions:
                raise ValueError("Demo narrative job refers to an unknown session")
            jobs[job_id] = _clone_job(job)

        for job_id, replacements in self._pending_job_replacements.items():
            current = jobs.get(job_id)
            for replacement in replacements:
                if not _job_matches(
                    current,
                    expected_status=replacement.expected_status,
                    expected_lease_token=replacement.expected_lease_token,
                    expected_lease_owner=replacement.expected_lease_owner,
                ):
                    raise OptimisticLockError(
                        "Demo narrative job fencing check failed"
                    )
                current = replacement.job
            assert current is not None
            jobs[job_id] = _clone_job(current)

        event_ids = {event.event_id for event in events}
        event_sequences = {(event.session_id, event.sequence_no) for event in events}
        for event in self._pending_events:
            key = (event.session_id, event.sequence_no)
            if event.event_id in event_ids or key in event_sequences:
                raise OptimisticLockError("Demo event identity or sequence conflict")
            if event.session_id not in sessions:
                raise ValueError("Demo event refers to an unknown session")
            event_ids.add(event.event_id)
            event_sequences.add(key)
            events.append(deepcopy(event))

        progress_update = self._pending_provider_progress
        if progress_update is not None:
            if progress_update.session_id not in sessions:
                raise ValueError("Demo Provider progress refers to an unknown session")
            if (
                provider_progress.get(progress_update.session_id)
                != progress_update.expected_progress
            ):
                raise OptimisticLockError("Demo Provider progress changed before commit")
            provider_progress[progress_update.session_id] = progress_update.next_progress

        self._store._sessions = sessions
        self._store._snapshots = snapshots
        self._store._creation_keys = creation_keys
        self._store._turn_requests = turn_requests
        self._store._narrative_jobs = jobs
        self._store._events = events
        self._store._provider_progress = provider_progress
        self._clear_staged()

    def _clear_staged(self) -> None:
        self._pending_session = None
        self._pending_snapshot = None
        self._pending_state_update = None
        self._pending_events = ()
        self._pending_turn_requests.clear()
        self._pending_job_adds.clear()
        self._pending_job_replacements.clear()
        self._pending_provider_progress = None

    def _ensure_open(self, *, allow_committed: bool = False) -> None:
        if not self._entered or self._closed:
            raise RuntimeError("Demo UnitOfWork is not active")
        if self._committed and not allow_committed:
            raise RuntimeError("Demo UnitOfWork has already committed")


def _job_matches(
    job: NarrativeJob | None,
    *,
    expected_status: NarrativeJobStatus,
    expected_lease_token: str | None,
    expected_lease_owner: str | None,
) -> bool:
    return (
        job is not None
        and job.status is expected_status
        and job.lease_token == expected_lease_token
        and job.lease_owner == expected_lease_owner
    )
