from __future__ import annotations

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from deviation_protocol.application.ports import UnitOfWork
from deviation_protocol.infrastructure.repositories import (
    SqlAlchemyGameSessionRepository,
    SqlAlchemyTurnRequestRepository,
)


class SqlAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self._committed = False

    async def __aenter__(self) -> "SqlAlchemyUnitOfWork":
        self._session = self._session_factory()
        self.sessions = SqlAlchemyGameSessionRepository(self._session)
        self.turn_requests = SqlAlchemyTurnRequestRepository(self._session)
        self._committed = False
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._session is None:
            return
        try:
            if exc_type is not None or not self._committed:
                await self._session.rollback()
        finally:
            await self._session.close()

    async def commit(self) -> None:
        if self._session is None:
            raise RuntimeError("UnitOfWork has not been entered")
        await self._session.commit()
        self._committed = True

    async def rollback(self) -> None:
        if self._session is None:
            raise RuntimeError("UnitOfWork has not been entered")
        await self._session.rollback()
        self._committed = False
