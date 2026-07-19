from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.session_service import SessionService
from deviation_protocol.domain.state import GameState
from deviation_protocol.infrastructure.content_loader import JsonContentCatalogLoader
from deviation_protocol.infrastructure.orm_models import GameSessionRow, GameSnapshotRow
from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


CONTENT_PACK = Path(__file__).parents[2] / "config" / "demo_content_pack.json"
NOW = datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_mysql_session_create_snapshot_and_idempotency_are_atomic(
    mysql_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    catalog = JsonContentCatalogLoader(CONTENT_PACK).load()
    player_id = f"session-api-{uuid4().hex}"
    ids = iter((f"session-api-{uuid4().hex}" for _ in range(4)))
    service = SessionService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(mysql_session_factory),
        catalog=catalog,
        clock=lambda: NOW,
        session_id_generator=lambda: next(ids),
        seed_generator=lambda: 42,
    )
    principal = RequestPrincipal(player_id=player_id, authentication_scheme="integration")
    created_session_id: str | None = None

    try:
        first, concurrent_retry = await asyncio.gather(
            *(
                service.create(
                    principal,
                    client_request_id="create-real-mysql",
                    character_definition_id="character.player.default",
                )
                for _ in range(2)
            )
        )
        replay = await service.create(
            principal,
            client_request_id="create-real-mysql",
            character_definition_id="character.player.default",
        )
        created_session_id = first.session_id

        assert first.session_id == concurrent_retry.session_id == replay.session_id
        async with mysql_session_factory() as database:
            rows = (
                await database.scalars(
                    select(GameSessionRow).where(GameSessionRow.player_id == player_id)
                )
            ).all()
            assert len(rows) == 1
            row = rows[0]
            assert row.creation_client_request_id == "create-real-mysql"
            assert row.character_definition_id == "character.player.default"
            assert row.state_version == 0
            snapshot = await database.get(GameSnapshotRow, row.session_id)
            assert snapshot is not None and snapshot.state_version == 0
            state = GameState.from_snapshot(snapshot.state_json, catalog=catalog)
            assert state.player.player_id == player_id
    finally:
        async with mysql_session_factory.begin() as database:
            await database.execute(
                delete(GameSessionRow).where(GameSessionRow.player_id == player_id)
            )

    async with mysql_session_factory() as database:
        session_count = await database.scalar(
            select(func.count())
            .select_from(GameSessionRow)
            .where(GameSessionRow.player_id == player_id)
        )
        snapshot_count = (
            await database.scalar(
                select(func.count())
                .select_from(GameSnapshotRow)
                .where(GameSnapshotRow.session_id == created_session_id)
            )
            if created_session_id is not None
            else 0
        )
    assert session_count == snapshot_count == 0
