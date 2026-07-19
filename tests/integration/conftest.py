from __future__ import annotations

import os
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from deviation_protocol.infrastructure.database import create_engine, create_session_factory
from deviation_protocol.infrastructure.orm_models import GameSessionRow


def validated_test_database_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured; no SQLite fallback is used")
    url = make_url(database_url)
    if url.drivername != "mysql+asyncmy":
        pytest.fail("TEST_DATABASE_URL must use mysql+asyncmy")
    if url.database != "deviation_protocol_test":
        pytest.fail("integration tests may only use deviation_protocol_test")
    return database_url


@pytest.fixture
async def mysql_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_engine(validated_test_database_url())
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
def mysql_session_factory(
    mysql_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return create_session_factory(mysql_engine)


@pytest.fixture
async def mysql_session_id(
    mysql_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[str]:
    session_id = f"it-{uuid4().hex}"
    async with mysql_session_factory.begin() as session:
        session.add(
            GameSessionRow(
                session_id=session_id,
                player_id="integration-player",
                scenario_id="integration-scenario",
                scenario_version="1",
                phase="AWAITING_ACTION",
                turn_number=0,
                state_version=0,
                random_seed=42,
            )
        )
    try:
        yield session_id
    finally:
        async with mysql_session_factory.begin() as session:
            await session.execute(
                delete(GameSessionRow).where(GameSessionRow.session_id == session_id)
            )
