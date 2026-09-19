from __future__ import annotations

from types import TracebackType
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from deviation_protocol.application.ports import UnitOfWork, NativeRunAdmissionUnitOfWork
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
    SqlAlchemyRunProtocolBindingRepository,
    SqlAlchemyRunSessionParticipationRepository,
    SqlAlchemyTurnRequestRepository,
)


class SqlAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession], *, content_registry=None) -> None:
        self._session_factory = session_factory
        self._content_registry = content_registry
        self._session: AsyncSession | None = None
        self._committed = False

    async def __aenter__(self) -> "SqlAlchemyUnitOfWork":
        self._session = self._session_factory()
        self._session.info["session_content_registry"] = self._content_registry
        from deviation_protocol.infrastructure.repositories import SqlAlchemyRunWorldContinuationRepository
        self.run_world_continuations = SqlAlchemyRunWorldContinuationRepository(self._session)
        from deviation_protocol.infrastructure.repositories import SqlAlchemyRunWorldRevisitRepository
        self.run_world_revisits = SqlAlchemyRunWorldRevisitRepository(self._session)
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
        self.run_protocol_bindings = SqlAlchemyRunProtocolBindingRepository(self._session)
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


NATIVE_ADMISSION_LOCK = "deviation_protocol:p33:s3:run_protocol_bindings:ddl_write:v1"


class SqlAlchemyNativeRunAdmissionUnitOfWork(SqlAlchemyUnitOfWork, NativeRunAdmissionUnitOfWork):
    """One explicitly owned physical connection, including post-commit cleanup."""

    def __init__(self, engine, *, content_registry=None):
        self._engine = engine
        self._content_registry = content_registry
        self._connection = None
        self._transaction = None
        self._driver = None
        self._pool_connection = None
        self._session = None
        self._committed = False
        self._locked = False
        self._uncertain = False
        self.connection_id = None

    @staticmethod
    def _error(code, cause=None):
        from deviation_protocol.application.ports import NativeRunAdmissionLockError
        error = NativeRunAdmissionLockError(code)
        error.__cause__ = cause
        error.__suppress_context__ = True
        return error

    def _lost(self, error=None):
        from sqlalchemy.exc import DBAPIError
        connection = self._connection
        if connection is None or connection.closed or connection.invalidated:
            return True
        if isinstance(error, DBAPIError) and error.connection_invalidated:
            return True
        original = error.orig if isinstance(error, DBAPIError) else error
        return (original is not None and type(original).__module__.startswith("asyncmy")
                and bool(original.args) and original.args[0] in (2006, 2013, 2055))

    def _writer_guard(self):
        return (self._locked and not self._lost() and self._transaction is not None
                and self._transaction.is_active and not self._committed and not self._uncertain)

    async def __aenter__(self):
        from sqlalchemy import text
        from deviation_protocol.application.ports import NativeRunAdmissionLockError
        from deviation_protocol.infrastructure.repositories import SqlAlchemyRunEntryWorldBindingRepository
        stage = "BEFORE"
        try:
            self._connection = await self._engine.connect()
            self._pool_connection = await self._connection.get_raw_connection()
            self._driver = self._pool_connection.driver_connection
            if self._lost():
                raise self._error("ACQUIRE_CONNECTION_LOST_BEFORE")
            self._transaction = await self._connection.begin()
            self.connection_id = (await self._connection.execute(text("SELECT CONNECTION_ID()"))).scalar_one()
            if self._lost():
                raise self._error("ACQUIRE_CONNECTION_LOST_BEFORE")
            stage = "PENDING"
            result = (await self._connection.execute(text(f"SELECT GET_LOCK('{NATIVE_ADMISSION_LOCK}', 30)"))).scalar_one()
            if type(result) is int and result == 0:
                raise self._error("ACQUIRE_TIMEOUT")
            if result is None:
                raise self._error("ACQUIRE_NULL")
            if type(result) is not int or result != 1:
                raise self._error("ACQUIRE_INVALID_RESULT")
            stage = "AFTER"
            if self._lost():
                raise self._error("ACQUIRE_CONNECTION_LOST_AFTER")
            self._locked = True
            self._session_factory = lambda: AsyncSession(bind=self._connection,
                join_transaction_mode="rollback_only", expire_on_commit=False)
            await super().__aenter__()
            self._session.info["native_admission_guard"] = self._writer_guard
            self.run_protocol_bindings = SqlAlchemyRunProtocolBindingRepository(self._session, native_guard=self._writer_guard)
            self.run_entry_world_bindings = SqlAlchemyRunEntryWorldBindingRepository(self._session, native_guard=self._writer_guard)
            return self
        except BaseException as error:
            if isinstance(error, NativeRunAdmissionLockError) or not isinstance(error, Exception):
                primary = error
            else:
                code = "ACQUIRE_CONNECTION_LOST_" + stage if self._lost(error) else "ACQUIRE_STATEMENT_FAILED"
                primary = self._error(code, error)
            if str(primary) == "ACQUIRE_TIMEOUT":
                await self._await_cleanup(primary)
            else:
                await self._await_discard(primary)
            raise primary

    async def commit(self):
        from deviation_protocol.application.ports import NativeRunAdmissionOutcomeUnknownError
        if not self._writer_guard():
            raise RuntimeError("native UoW is not an active pinned transaction")
        await self._session.flush()
        try:
            await self._transaction.commit()
        except asyncio.CancelledError as error:
            self._uncertain = True
            error.commit_outcome_unknown = True
            raise
        except Exception as error:
            self._uncertain = True
            raise NativeRunAdmissionOutcomeUnknownError("native commit outcome unknown") from error
        self._committed = True
        self.sessions.confirm_pending_versions()

    async def rollback(self):
        try:
            if self._transaction is not None and self._transaction.is_active:
                await self._transaction.rollback()
        finally:
            if self._session is not None:
                self.sessions.restore_pending_versions()

    async def _cleanup(self):
        from sqlalchemy import text
        if not self._committed:
            await self.rollback()
        if self._locked:
            if self._lost():
                raise self._error("RELEASE_CONNECTION_LOST_BEFORE")
            try:
                result = (await self._connection.execute(text(f"SELECT RELEASE_LOCK('{NATIVE_ADMISSION_LOCK}')"))).scalar_one()
            except Exception as error:
                raise self._error("RELEASE_CONNECTION_LOST_PENDING" if self._lost(error) else "RELEASE_STATEMENT_FAILED", error)
            if self._lost():
                raise self._error("RELEASE_CONNECTION_LOST_PENDING")
            if type(result) is int and result == 1:
                self._locked = False
            elif type(result) is int and result == 0:
                raise self._error("RELEASE_NOT_OWNER")
            elif result is None:
                raise self._error("RELEASE_NULL")
            else:
                raise self._error("RELEASE_INVALID_RESULT")
        if self._session is not None:
            await self._session.close()
        if self._connection is not None:
            if self._connection.in_transaction():
                await self._connection.rollback()
            await self._connection.close()

    async def _discard(self, primary):
        # Invalidation terminates the adapter; the retained driver is a fallback if it fails.
        invalidation_failed = False
        if self._connection is not None:
            try:
                await self._connection.invalidate()
            except BaseException as error:
                invalidation_failed = True
                if not hasattr(primary, "close_error"):
                    primary.close_error = error
                if self._pool_connection is not None:
                    try:
                        self._pool_connection.detach()
                    except BaseException as detach_error:
                        if not hasattr(primary, "close_error"):
                            primary.close_error = detach_error
        if self._driver is not None:
            try:
                self._driver.close()
            except BaseException as error:
                if not hasattr(primary, "close_error"):
                    primary.close_error = error
        if invalidation_failed and self._pool_connection is not None:
            try:
                # Clear the detached adapter's validity before wrapper close can
                # attempt another rollback on the physically terminated driver.
                await self._connection.run_sync(lambda _: self._pool_connection.invalidate())
            except BaseException as error:
                if not hasattr(primary, "close_error"):
                    primary.close_error = error
        if self._session is not None:
            try:
                await self._session.close()
            except BaseException as error:
                if not hasattr(primary, "close_error"):
                    primary.close_error = error
            self.sessions.restore_pending_versions()
        if self._connection is not None:
            try:
                await self._connection.close()
            except BaseException as error:
                if not hasattr(primary, "close_error"):
                    primary.close_error = error
        self._locked = False

    async def _retained(self, coroutine, primary):
        task = asyncio.create_task(coroutine)
        cancellation = None
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError as error:
                if cancellation is None:
                    cancellation = error
            except BaseException:
                break
        failure = task.exception() if not task.cancelled() else asyncio.CancelledError()
        return failure, primary if primary is not None else cancellation

    async def _await_discard(self, primary):
        failure, primary = await self._retained(self._discard(primary), primary)
        if failure is not None:
            primary.close_error = failure

    async def _await_cleanup(self, primary):
        failure, primary = await self._retained(asyncio.wait_for(self._cleanup(), timeout=5), primary)
        if failure is not None:
            await self._await_discard(failure)
            if primary is not None:
                primary.cleanup_error = failure
            else:
                raise failure
        if primary is not None:
            return primary
        return None

    async def __aexit__(self, exc_type, exc, traceback):
        if self._uncertain:
            await self._await_discard(exc)
            return
        primary = await self._await_cleanup(exc)
        if exc is None and primary is not None:
            raise primary


class SqlAlchemyNativeRunAdmissionUnitOfWorkFactory:
    def __init__(self, engine, *, content_registry=None):
        self.engine = engine
        self.content_registry = content_registry

    def __call__(self):
        return SqlAlchemyNativeRunAdmissionUnitOfWork(self.engine,content_registry=self.content_registry)
