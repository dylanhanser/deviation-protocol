from __future__ import annotations

from typing import Any, Mapping, Sequence
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from deviation_protocol.application.action_gateway import ActionRoute
from deviation_protocol.application.ports import GameSessionRepository, TurnRequestRepository
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
        return GameSession(
            session_id=row.session_id,
            player_id=row.player_id,
            scenario_id=row.scenario_id,
            scenario_version=row.scenario_version,
            phase=row.phase,
            turn_number=row.turn_number,
            state_version=row.state_version,
            random_seed=row.random_seed,
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

        snapshot = mysql_insert(GameSnapshotRow).values(
            session_id=session.session_id,
            state_version=next_version,
            state_json=dict(state),
            updated_at=utc_now(),
        )
        await self._session.execute(
            snapshot.on_duplicate_key_update(
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
                    payload_json=event.payload,
                    occurred_at=event.occurred_at,
                )
                for event in events
            ]
        )
        session.state_version = next_version


class SqlAlchemyTurnRequestRepository(TurnRequestRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_client_request_id(
        self, session_id: str, client_request_id: str
    ) -> Mapping[str, Any] | None:
        row = await self._session.scalar(
            select(TurnRequestRow).where(
                TurnRequestRow.session_id == session_id,
                TurnRequestRow.client_request_id == client_request_id,
            )
        )
        if row is None:
            return None
        if row.response_json is not None:
            return row.response_json
        return {
            "route": row.route,
            "action_signature": row.action_signature,
            "error": row.error_text,
        }

    async def add(
        self,
        submission: ActionSubmission,
        action_signature: str,
        route: ActionRoute,
        response: Mapping[str, Any] | None = None,
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
                response_json=dict(response) if response is not None else None,
                error_text=None,
            )
        )
