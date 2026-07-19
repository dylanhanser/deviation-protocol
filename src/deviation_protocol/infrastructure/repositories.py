from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Sequence
from uuid import uuid4

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from deviation_protocol.application.action_gateway import ActionRoute
from deviation_protocol.application.ports import (
    GameSessionRepository,
    PersistedSession,
    PersistedSnapshot,
    PersistedTurnRequest,
    TurnRequestRepository,
)
from deviation_protocol.domain.actions import ActionSubmission
from deviation_protocol.domain.events import DomainEvent
from deviation_protocol.domain.models import GameSession
from deviation_protocol.infrastructure.errors import OptimisticLockError
from deviation_protocol.infrastructure.orm_models import (
    DomainEventRow,
    GameSessionRow,
    GameSnapshotRow,
    TurnRequestRow,
    utc_now,
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
            created_at=row.created_at,
            updated_at=row.updated_at,
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
        self._session.add(
            GameSessionRow(
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
        )
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
        self._session.add_all(
            [
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
            ]
        )
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
        self._session.add(
            TurnRequestRow(
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
        )
