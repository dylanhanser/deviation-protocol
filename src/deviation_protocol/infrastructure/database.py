from __future__ import annotations

from collections.abc import AsyncIterator

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


class DatabaseSettings(BaseSettings):
    # Runtime configuration comes only from the process environment or an
    # explicit injected URL. Import/build paths never load a repository .env.
    model_config = SettingsConfigDict(extra="ignore")

    database_url: str

    @field_validator("database_url")
    @classmethod
    def require_async_mysql(cls, value: str) -> str:
        url = make_url(value)
        if url.drivername != "mysql+asyncmy":
            raise ValueError("DATABASE_URL must use mysql+asyncmy; SQLite is not supported")
        return value


def create_engine(database_url: str | None = None, *, echo: bool = False) -> AsyncEngine:
    url = database_url or DatabaseSettings().database_url
    DatabaseSettings(database_url=url)  # validate explicit URLs as well
    engine = create_async_engine(url, echo=echo, pool_pre_ping=True, pool_recycle=1800)

    @event.listens_for(engine.sync_engine, "connect")
    def set_utc_session_time(dbapi_connection: object, _: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        try:
            cursor.execute("SET time_zone = '+00:00'")
        finally:
            cursor.close()

    return engine


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def session_dependency() -> AsyncIterator[AsyncSession]:
    engine = create_engine()
    try:
        factory = create_session_factory(engine)
        async with factory() as session:
            yield session
    finally:
        await engine.dispose()
