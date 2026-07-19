from __future__ import annotations

import os

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

from deviation_protocol.infrastructure.database import create_engine


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mysql_8_integration_database_is_reachable() -> None:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured; no SQLite fallback is used")
    if make_url(database_url).drivername != "mysql+asyncmy":
        pytest.fail("TEST_DATABASE_URL must use mysql+asyncmy")

    engine = create_engine(database_url)
    try:
        async with engine.connect() as connection:
            version = (await connection.execute(text("SELECT VERSION()"))).scalar_one()
            assert int(str(version).split(".", 1)[0]) >= 8
    finally:
        await engine.dispose()
