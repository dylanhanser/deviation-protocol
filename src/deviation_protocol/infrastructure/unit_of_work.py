from __future__ import annotations

from types import TracebackType

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from deviation_protocol.application.errors import ConcurrentTurnRequestError
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
                try:
                    await self._session.rollback()
                finally:
                    self.sessions.restore_pending_versions()
        finally:
            await self._session.close()

    async def commit(self) -> None:
        if self._session is None:
            raise RuntimeError("UnitOfWork has not been entered")
        try:
            await self._session.commit()
        except IntegrityError as exc:
            if _is_turn_request_idempotency_conflict(exc):
                raise ConcurrentTurnRequestError from exc
            raise
        self.sessions.confirm_pending_versions()
        self._committed = True

    async def rollback(self) -> None:
        if self._session is None:
            raise RuntimeError("UnitOfWork has not been entered")
        try:
            await self._session.rollback()
        finally:
            self.sessions.restore_pending_versions()
        self._committed = False


def _is_turn_request_idempotency_conflict(error: IntegrityError) -> bool:
    original = error.orig
    arguments = getattr(original, "args", ())
    error_code = arguments[0] if arguments else None
    return (
        str(error_code) == "1062"
        and "uq_turn_requests_session_client_request" in str(original)
    )
