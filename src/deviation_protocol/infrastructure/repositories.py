from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
from uuid import uuid4

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from deviation_protocol.application.action_gateway import ActionRoute
from deviation_protocol.application.errors import (
    ConcurrentSessionCreateError,
    ConcurrentTurnRequestError,
)
from deviation_protocol.application.ports import (
    GameSessionRepository,
    PersistedSession,
    PersistedSnapshot,
    PersistedTurnRequest,
    TurnRequestRepository,
    NarrativeJobRepository,
)
from deviation_protocol.application.narrative_jobs import (
    ACTIVE_NARRATIVE_JOB_STATUSES,
    NarrativeJob,
    NarrativeJobStatus,
)
from deviation_protocol.domain.actions import ActionSubmission
from deviation_protocol.domain.events import DomainEvent
from deviation_protocol.domain.persisted_events import (
    PersistedEventReceipt,
    _issue_persisted_event_receipt,
)
from deviation_protocol.domain.models import GameSession
from deviation_protocol.infrastructure.errors import OptimisticLockError
from deviation_protocol.infrastructure.orm_models import (
    DomainEventRow,
    GameSessionRow,
    GameSnapshotRow,
    TurnRequestRow,
    NarrativeJobRow,
    utc_now,
)


def _as_utc(value: datetime) -> datetime:
    """Restore MySQL DATETIME values to the application UTC contract."""

    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )


class SqlAlchemyGameSessionRepository(GameSessionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._pending_session_versions: list[tuple[GameSession, int]] = []

    @staticmethod
    def _persisted(row: GameSessionRow) -> PersistedSession:
        return PersistedSession(
            session=GameSession(
                session_id=row.session_id,
                player_id=row.player_id,
                scenario_id=row.scenario_id,
                scenario_version=row.scenario_version,
                phase=row.phase,
                turn_number=row.turn_number,
                state_version=row.state_version,
                random_seed=row.random_seed,
            ),
            character_definition_id=row.character_definition_id,
            creation_client_request_id=row.creation_client_request_id,
            created_at=_as_utc(row.created_at),
            updated_at=_as_utc(row.updated_at),
        )

    async def get_owned(self, session_id: str, player_id: str) -> PersistedSession | None:
        row = await self._session.scalar(
            select(GameSessionRow).where(
                GameSessionRow.session_id == session_id,
                GameSessionRow.player_id == player_id,
            )
        )
        return self._persisted(row) if row is not None else None

    async def get_by_creation_request(
        self, player_id: str, client_request_id: str
    ) -> PersistedSession | None:
        row = await self._session.scalar(
            select(GameSessionRow).where(
                GameSessionRow.player_id == player_id,
                GameSessionRow.creation_client_request_id == client_request_id,
            )
        )
        return self._persisted(row) if row is not None else None

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
        await self.add_initial_snapshot(
            session, state=state, created_at=created_at
        )

    async def add_initial_session(
        self,
        session: GameSession,
        *,
        character_definition_id: str,
        creation_client_request_id: str,
        created_at: datetime,
    ) -> None:
        session_row = GameSessionRow(
            session_id=session.session_id,
            player_id=session.player_id,
            creation_client_request_id=creation_client_request_id,
            character_definition_id=character_definition_id,
            scenario_id=session.scenario_id,
            scenario_version=session.scenario_version,
            phase=session.phase,
            turn_number=session.turn_number,
            state_version=session.state_version,
            random_seed=session.random_seed,
            created_at=created_at,
            updated_at=created_at,
        )
        self._session.add(session_row)
        try:
            await self._session.flush((session_row,))
        except IntegrityError as exc:
            if _is_mysql_duplicate_key(exc):
                raise ConcurrentSessionCreateError from exc
            raise

    async def add_initial_snapshot(
        self,
        session: GameSession,
        *,
        state: Mapping[str, Any],
        created_at: datetime,
    ) -> None:
        self._session.add(
            GameSnapshotRow(
                session_id=session.session_id,
                state_version=session.state_version,
                state_json=dict(state),
                updated_at=created_at,
            )
        )

    async def lock_for_turn(self, session_id: str) -> bool:
        result = await self._session.execute(
            select(GameSessionRow.session_id)
            .where(GameSessionRow.session_id == session_id)
            .with_for_update()
        )
        return result.scalar_one_or_none() is not None

    async def get(self, session_id: str) -> GameSession | None:
        row = await self._session.get(GameSessionRow, session_id)
        if row is None:
            return None
        return self._persisted(row).session

    async def get_latest_snapshot(self, session_id: str) -> PersistedSnapshot | None:
        row = await self._session.get(GameSnapshotRow, session_id)
        if row is None:
            return None
        return PersistedSnapshot(
            state_version=row.state_version,
            state=dict(row.state_json),
        )

    async def next_event_sequence_no(self, session_id: str) -> int:
        latest = await self._session.scalar(
            select(func.max(DomainEventRow.sequence_no)).where(
                DomainEventRow.session_id == session_id
            )
        )
        return int(latest or 0) + 1

    async def persist_events(
        self,
        events: Sequence[DomainEvent],
        *,
        state_version: int,
    ) -> tuple[PersistedEventReceipt, ...]:
        rows = tuple(
            DomainEventRow(
                event_id=event.event_id,
                session_id=event.session_id,
                turn_id=event.turn_id,
                sequence_no=event.sequence_no,
                event_type=event.event_type,
                payload_json=dict(event.payload),
                occurred_at=event.occurred_at,
            )
            for event in events
        )
        if not rows:
            return ()
        self._session.add_all(rows)
        await self._session.flush(rows)
        return tuple(
            _issue_persisted_event_receipt(event, state_version=state_version)
            for event in events
        )

    async def save_snapshot_and_events(
        self,
        session: GameSession,
        state: Mapping[str, Any],
        events: Sequence[DomainEvent],
        expected_state_version: int,
    ) -> None:
        next_version = expected_state_version + 1
        result = await self._session.execute(
            update(GameSessionRow)
            .where(
                GameSessionRow.session_id == session.session_id,
                GameSessionRow.state_version == expected_state_version,
            )
            .values(
                phase=session.phase,
                turn_number=session.turn_number,
                state_version=next_version,
                updated_at=utc_now(),
            )
        )
        if result.rowcount != 1:
            raise OptimisticLockError(
                f"session {session.session_id!r} state_version changed concurrently"
            )

        snapshot_result = await self._session.execute(
            update(GameSnapshotRow)
            .where(
                GameSnapshotRow.session_id == session.session_id,
                GameSnapshotRow.state_version == expected_state_version,
            )
            .values(
                state_version=next_version,
                state_json=dict(state),
                updated_at=utc_now(),
            )
        )
        if snapshot_result.rowcount != 1:
            persisted_snapshot_version = await self._session.scalar(
                select(GameSnapshotRow.state_version).where(
                    GameSnapshotRow.session_id == session.session_id
                )
            )
            if persisted_snapshot_version is not None:
                raise OptimisticLockError(
                    f"session {session.session_id!r} snapshot version changed concurrently"
                )
            self._session.add(
                GameSnapshotRow(
                    session_id=session.session_id,
                    state_version=next_version,
                    state_json=dict(state),
                    updated_at=utc_now(),
                )
            )
        if events:
            await self.persist_events(events, state_version=next_version)
        self._pending_session_versions.append((session, session.state_version))
        session.state_version = next_version

    def confirm_pending_versions(self) -> None:
        self._pending_session_versions.clear()

    def restore_pending_versions(self) -> None:
        for session, previous_version in reversed(self._pending_session_versions):
            session.state_version = previous_version
        self._pending_session_versions.clear()


class SqlAlchemyTurnRequestRepository(TurnRequestRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_client_request_id(
        self, session_id: str, client_request_id: str
    ) -> PersistedTurnRequest | None:
        row = await self._session.scalar(
            select(TurnRequestRow).where(
                TurnRequestRow.session_id == session_id,
                TurnRequestRow.client_request_id == client_request_id,
            )
        )
        if row is None:
            return None
        return PersistedTurnRequest(
            turn_id=row.turn_id,
            action_signature=row.action_signature,
            response=(
                dict(row.response_json) if row.response_json is not None else None
            ),
        )

    async def add(
        self,
        submission: ActionSubmission,
        action_signature: str,
        route: ActionRoute,
        response: Mapping[str, Any],
    ) -> None:
        row = TurnRequestRow(
            request_id=str(uuid4()),
            session_id=submission.session_id,
            turn_id=submission.turn_id,
            client_request_id=submission.client_request_id,
            action_signature=action_signature,
            route=route.value,
            request_json=submission.model_dump(mode="json"),
            response_json=dict(response),
            error_text=None,
        )
        self._session.add(row)
        try:
            await self._session.flush((row,))
        except IntegrityError as exc:
            if _is_mysql_duplicate_key(exc):
                raise ConcurrentTurnRequestError from exc
            raise


class SqlAlchemyNarrativeJobRepository(NarrativeJobRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _persisted(row: NarrativeJobRow) -> NarrativeJob:
        return NarrativeJob(
            job_id=row.job_id,
            session_id=row.session_id,
            turn_id=row.turn_id,
            client_request_id=row.client_request_id,
            action_signature=row.action_signature,
            prepared_state_version=row.prepared_state_version,
            state_fingerprint=row.state_fingerprint,
            scenario_id=row.scenario_id,
            scenario_content_version=row.scenario_content_version,
            request_fingerprint=row.request_fingerprint,
            narrative_request=dict(row.narrative_request_json),
            prompt_schema_version=row.prompt_schema_version,
            style_profile_version=row.style_profile_version,
            provider_name=row.provider_name,
            model_name=row.model_name,
            status=NarrativeJobStatus(row.status),
            attempt_count=row.attempt_count,
            lease_token=row.lease_token,
            lease_owner=row.lease_owner,
            lease_expires_at=row.lease_expires_at,
            validated_proposal=(
                dict(row.validated_proposal_json)
                if row.validated_proposal_json is not None
                else None
            ),
            validated_proposal_digest=row.validated_proposal_digest,
            outcome_rule_id=row.outcome_rule_id,
            accepted_narrative_text=row.accepted_narrative_text,
            error_code=row.error_code,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def get_by_client_request_id(
        self, session_id: str, client_request_id: str, *, for_update: bool = False
    ) -> NarrativeJob | None:
        statement = select(NarrativeJobRow).where(
            NarrativeJobRow.session_id == session_id,
            NarrativeJobRow.client_request_id == client_request_id,
        )
        if for_update:
            statement = statement.with_for_update()
        row = await self._session.scalar(statement)
        return self._persisted(row) if row is not None else None

    async def get(self, job_id: str, *, for_update: bool = False) -> NarrativeJob | None:
        statement = select(NarrativeJobRow).where(NarrativeJobRow.job_id == job_id)
        if for_update:
            statement = statement.with_for_update()
        row = await self._session.scalar(statement)
        return self._persisted(row) if row is not None else None

    async def get_active_for_session(self, session_id: str) -> NarrativeJob | None:
        row = await self._session.scalar(
            select(NarrativeJobRow)
            .where(
                NarrativeJobRow.session_id == session_id,
                NarrativeJobRow.status.in_(
                    tuple(item.value for item in ACTIVE_NARRATIVE_JOB_STATUSES)
                ),
            )
            .order_by(NarrativeJobRow.created_at)
            .limit(1)
        )
        return self._persisted(row) if row is not None else None

    async def add(self, job: NarrativeJob) -> None:
        row = NarrativeJobRow(
            job_id=job.job_id,
            session_id=job.session_id,
            turn_id=job.turn_id,
            client_request_id=job.client_request_id,
            action_signature=job.action_signature,
            prepared_state_version=job.prepared_state_version,
            state_fingerprint=job.state_fingerprint,
            scenario_id=job.scenario_id,
            scenario_content_version=job.scenario_content_version,
            request_fingerprint=job.request_fingerprint,
            narrative_request_json=dict(job.narrative_request),
            prompt_schema_version=job.prompt_schema_version,
            style_profile_version=job.style_profile_version,
            provider_name=job.provider_name,
            model_name=job.model_name,
            status=job.status.value,
            attempt_count=job.attempt_count,
            lease_token=job.lease_token,
            lease_owner=job.lease_owner,
            lease_expires_at=job.lease_expires_at,
            validated_proposal_json=job.validated_proposal,
            validated_proposal_digest=job.validated_proposal_digest,
            outcome_rule_id=job.outcome_rule_id,
            accepted_narrative_text=job.accepted_narrative_text,
            error_code=job.error_code,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
        self._session.add(row)
        try:
            await self._session.flush((row,))
        except IntegrityError as exc:
            if _is_mysql_duplicate_key(exc):
                raise ConcurrentTurnRequestError from exc
            raise

    async def replace(
        self,
        job: NarrativeJob,
        *,
        expected_status: NarrativeJobStatus,
        expected_lease_token: str | None = None,
        expected_lease_owner: str | None = None,
    ) -> bool:
        result = await self._session.execute(
            update(NarrativeJobRow)
            .where(
                NarrativeJobRow.job_id == job.job_id,
                NarrativeJobRow.status == expected_status.value,
                NarrativeJobRow.lease_token == expected_lease_token,
                NarrativeJobRow.lease_owner == expected_lease_owner,
            )
            .values(
                status=job.status.value,
                attempt_count=job.attempt_count,
                lease_token=job.lease_token,
                lease_owner=job.lease_owner,
                lease_expires_at=job.lease_expires_at,
                validated_proposal_json=job.validated_proposal,
                validated_proposal_digest=job.validated_proposal_digest,
                outcome_rule_id=job.outcome_rule_id,
                accepted_narrative_text=job.accepted_narrative_text,
                error_code=job.error_code,
                updated_at=job.updated_at,
            )
        )
        return result.rowcount == 1

    async def recent_committed_texts(
        self, session_id: str, *, limit: int
    ) -> tuple[str, ...]:
        rows = (
            await self._session.scalars(
                select(NarrativeJobRow.accepted_narrative_text)
                .where(
                    NarrativeJobRow.session_id == session_id,
                    NarrativeJobRow.status == NarrativeJobStatus.COMMITTED.value,
                    NarrativeJobRow.accepted_narrative_text.is_not(None),
                )
                .order_by(
                    NarrativeJobRow.updated_at.desc(),
                    NarrativeJobRow.job_id.desc(),
                )
                .limit(limit)
            )
        ).all()
        return tuple(reversed(tuple(item for item in rows if item is not None)))


def _is_mysql_duplicate_key(error: IntegrityError) -> bool:
    arguments = getattr(error.orig, "args", ())
    error_code = arguments[0] if arguments else None
    return type(error_code) is int and error_code == 1062
