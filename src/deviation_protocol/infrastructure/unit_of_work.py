from __future__ import annotations

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from deviation_protocol.application.ports import UnitOfWork
from deviation_protocol.infrastructure.repositories import (
    SqlAlchemyControllerBindingRegistryRepository,
    SqlAlchemyGameSessionRepository,
    SqlAlchemyNarrativeJobRepository,
    SqlAlchemyPlayerCharacterCreationReceiptRepository,
    SqlAlchemyPlayerCharacterMutationReceiptRepository,
    SqlAlchemyPlayerCharacterRepository,
    SqlAlchemyRunCreationReceiptRepository,
    SqlAlchemyRunMutationReceiptRepository,
    SqlAlchemyRunRepository,
    SqlAlchemyRunSessionParticipationRepository,
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
        self.narrative_jobs = SqlAlchemyNarrativeJobRepository(self._session)
        self.controller_bindings = SqlAlchemyControllerBindingRegistryRepository(
            self._session
        )
        self.player_characters = SqlAlchemyPlayerCharacterRepository(self._session)
        self.creation_receipts = (
            SqlAlchemyPlayerCharacterCreationReceiptRepository(self._session)
        )
        self.mutation_receipts = (
            SqlAlchemyPlayerCharacterMutationReceiptRepository(self._session)
        )
        self.runs = SqlAlchemyRunRepository(self._session)
        self.run_participations = SqlAlchemyRunSessionParticipationRepository(
            self._session
        )
        self.run_creation_receipts = SqlAlchemyRunCreationReceiptRepository(
            self._session
        )
        self.run_mutation_receipts = SqlAlchemyRunMutationReceiptRepository(
            self._session
        )
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
        await self._session.commit()
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
