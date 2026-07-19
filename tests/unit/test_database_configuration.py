from __future__ import annotations

import pytest
from pydantic import ValidationError

from deviation_protocol.infrastructure.database import DatabaseSettings, create_engine


def test_database_settings_reject_sqlite_without_fallback() -> None:
    with pytest.raises(ValidationError, match="mysql\\+asyncmy"):
        DatabaseSettings(database_url="sqlite+aiosqlite:///local.db")


@pytest.mark.asyncio
async def test_engine_accepts_only_configured_async_mysql_driver() -> None:
    engine = create_engine(
        "mysql+asyncmy://placeholder:placeholder@localhost/deviation_protocol"
        "?charset=utf8mb4"
    )
    try:
        assert engine.dialect.name == "mysql"
        assert engine.dialect.driver == "asyncmy"
    finally:
        await engine.dispose()
