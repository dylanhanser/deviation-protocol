from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx
import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from deviation_protocol.api.dependencies import ApiServices, get_current_principal
from deviation_protocol.api.main import create_app
from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.player_character_operations import (
    CharacterCreationCommand,
    CharacterOperationNamespace,
)
from deviation_protocol.application import player_character_service as player_character_service_module
from deviation_protocol.application.player_character_service import (
    PlayerCharacterService,
)
from deviation_protocol.application.run_operations import (
    BindPlayerCharacterCommand,
    CreateRunCommand,
)
from deviation_protocol.application.run_service import RunService
from deviation_protocol.application.ports import ControllerBindingUniquenessConflictError
from deviation_protocol.domain.player_character import (
    AuthoritySourceRef,
    CharacterCore,
    ControllerBindingRef,
    NarrationPreferences,
    PlayerCharacterContractVersion,
    PlayerCharacterId,
    PlayerCharacterOperationId,
)
from deviation_protocol.domain.run import (
    ContinuousStoryLineId,
    RunAuthoritySourceRef,
    RunId,
    RunOperationId,
    RunStateVersion,
)
from deviation_protocol.domain.player_character_policies import (
    CreatePlayerCharacterPolicy,
)
from deviation_protocol.infrastructure.orm_models import (
    PlayerCharacterControllerBindingRow,
    PlayerCharacterCreationReceiptRow,
    PlayerCharacterCurrentRow,
    PlayerCharacterIdAllocationRow,
    PlayerCharacterMutationReceiptRow,
    PlayerCharacterRevisionRow,
    RunCreationReceiptRow,
    RunCurrentRow,
    RunMutationReceiptRow,
    RunRevisionRow,
)
from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from deviation_protocol.infrastructure.repositories import (
    SqlAlchemyControllerBindingRegistryRepository,
    SqlAlchemyPlayerCharacterRepository,
)


pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_NOW = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)


@dataclass(slots=True)
class _Scope:
    token: str
    character_ids: set[str] = field(default_factory=set)
    bindings: set[str] = field(default_factory=set)
    run_ids: set[str] = field(default_factory=set)


@pytest.fixture
async def player_character_api_scope(
    mysql_session_factory: async_sessionmaker[AsyncSession],
):
    scope = _Scope(token=uuid4().hex)
    try:
        yield scope
    finally:
        async with mysql_session_factory.begin() as session:
            if scope.run_ids:
                for row, column in (
                    (RunMutationReceiptRow, RunMutationReceiptRow.run_id),
                    (RunCreationReceiptRow, RunCreationReceiptRow.result_run_id),
                    (RunCurrentRow, RunCurrentRow.run_id),
                    (RunRevisionRow, RunRevisionRow.run_id),
                ):
                    await session.execute(
                        sa.delete(row).where(column.in_(scope.run_ids))
                    )
            if scope.character_ids:
                for row, column in (
                    (PlayerCharacterMutationReceiptRow, PlayerCharacterMutationReceiptRow.player_character_id),
                    (PlayerCharacterCreationReceiptRow, PlayerCharacterCreationReceiptRow.result_player_character_id),
                    (PlayerCharacterCurrentRow, PlayerCharacterCurrentRow.player_character_id),
                    (PlayerCharacterRevisionRow, PlayerCharacterRevisionRow.player_character_id),
                    (PlayerCharacterIdAllocationRow, PlayerCharacterIdAllocationRow.player_character_id),
                ):
                    await session.execute(sa.delete(row).where(column.in_(scope.character_ids)))
            if scope.bindings:
                await session.execute(
                    sa.delete(PlayerCharacterControllerBindingRow).where(
                        PlayerCharacterControllerBindingRow.controller_binding.in_(scope.bindings)
                    )
                )


class _Resolver:
    def __init__(self, binding: ControllerBindingRef) -> None:
        self.binding = binding

    async def resolve(self, _: RequestPrincipal, /) -> ControllerBindingRef:
        return self.binding


class _UnconfiguredResolver:
    async def resolve(
        self,
        _: RequestPrincipal,
        /,
    ) -> ControllerBindingRef | None:
        return None


class _Issuer:
    def __init__(self, player_character_id: PlayerCharacterId) -> None:
        self.player_character_id = player_character_id

    def issue(self) -> PlayerCharacterId:
        return self.player_character_id


def _service(
    session_factory: async_sessionmaker[AsyncSession],
    binding: ControllerBindingRef,
    player_character_id: PlayerCharacterId,
    *,
    uow_factory: Any | None = None,
) -> PlayerCharacterService:
    return PlayerCharacterService(
        uow_factory=(
            uow_factory
            if uow_factory is not None
            else lambda: SqlAlchemyUnitOfWork(session_factory)
        ),
        controller_binding_resolver=_Resolver(binding),
        player_character_id_issuer=_Issuer(player_character_id),
        create_policy=CreatePlayerCharacterPolicy(),
        source_reference=AuthoritySourceRef(value="source.mysql-api"),
        clock=lambda: _NOW,
        binding_integrity_guard_enabled=True,
    )


async def _counts(
    session_factory: async_sessionmaker[AsyncSession],
    player_character_id: str,
    binding: str,
) -> tuple[int, int, int, int, int, int]:
    predicates = (
        (PlayerCharacterControllerBindingRow, PlayerCharacterControllerBindingRow.controller_binding == binding),
        (PlayerCharacterIdAllocationRow, PlayerCharacterIdAllocationRow.player_character_id == player_character_id),
        (PlayerCharacterRevisionRow, PlayerCharacterRevisionRow.player_character_id == player_character_id),
        (PlayerCharacterCurrentRow, PlayerCharacterCurrentRow.player_character_id == player_character_id),
        (PlayerCharacterCreationReceiptRow, PlayerCharacterCreationReceiptRow.result_player_character_id == player_character_id),
        (PlayerCharacterMutationReceiptRow, PlayerCharacterMutationReceiptRow.player_character_id == player_character_id),
    )
    async with session_factory() as session:
        counts: list[int] = []
        for row, predicate in predicates:
            counts.append(
                int(
                    await session.scalar(
                        sa.select(sa.func.count()).select_from(row).where(predicate)
                    )
                    or 0
                )
            )
        return tuple(counts)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class _DurableCharacterSnapshot:
    current: Any
    controller_binding: str | None
    revisions: tuple[tuple[Any, ...], ...]
    creation_receipts: tuple[tuple[Any, ...], ...]
    mutation_receipts: tuple[tuple[Any, ...], ...]


async def _durable_character_snapshot(
    session_factory: async_sessionmaker[AsyncSession],
    player_character_id: PlayerCharacterId,
    controller_binding: ControllerBindingRef,
) -> _DurableCharacterSnapshot:
    """Reload every asserted family through a fresh independent DB session."""

    async with session_factory() as session:
        current = await SqlAlchemyPlayerCharacterRepository(session).get(
            player_character_id
        )
        stored_binding = await session.scalar(
            sa.select(
                PlayerCharacterControllerBindingRow.controller_binding
            ).where(
                PlayerCharacterControllerBindingRow.controller_binding
                == controller_binding.value
            )
        )
        revisions = tuple(
            tuple(row)
            for row in (
                await session.execute(
                    sa.select(
                        PlayerCharacterRevisionRow.record_revision,
                        PlayerCharacterRevisionRow.contract_version,
                        PlayerCharacterRevisionRow.controller_binding,
                        PlayerCharacterRevisionRow.lifecycle,
                        PlayerCharacterRevisionRow.prior_revision,
                        PlayerCharacterRevisionRow.mutation_kind,
                        PlayerCharacterRevisionRow.authority_class,
                        PlayerCharacterRevisionRow.source_reference,
                        PlayerCharacterRevisionRow.record_canonical,
                    )
                    .where(
                        PlayerCharacterRevisionRow.player_character_id
                        == player_character_id.value
                    )
                    .order_by(PlayerCharacterRevisionRow.record_revision)
                )
            ).all()
        )
        creation_receipts = tuple(
            tuple(row)
            for row in (
                await session.execute(
                    sa.select(
                        PlayerCharacterCreationReceiptRow.operation_namespace,
                        PlayerCharacterCreationReceiptRow.operation_id,
                        PlayerCharacterCreationReceiptRow.fingerprint,
                        PlayerCharacterCreationReceiptRow.result_contract_version,
                        PlayerCharacterCreationReceiptRow.resulting_revision,
                        PlayerCharacterCreationReceiptRow.resulting_lifecycle,
                        PlayerCharacterCreationReceiptRow.receipt_canonical,
                    ).where(
                        PlayerCharacterCreationReceiptRow.result_player_character_id
                        == player_character_id.value
                    )
                )
            ).all()
        )
        mutation_receipts = tuple(
            tuple(row)
            for row in (
                await session.execute(
                    sa.select(
                        PlayerCharacterMutationReceiptRow.operation_namespace,
                        PlayerCharacterMutationReceiptRow.operation_id,
                        PlayerCharacterMutationReceiptRow.fingerprint,
                        PlayerCharacterMutationReceiptRow.command_kind,
                        PlayerCharacterMutationReceiptRow.result_schema_version,
                        PlayerCharacterMutationReceiptRow.expected_revision,
                        PlayerCharacterMutationReceiptRow.result_player_character_id,
                        PlayerCharacterMutationReceiptRow.result_contract_version,
                        PlayerCharacterMutationReceiptRow.result_command_kind,
                        PlayerCharacterMutationReceiptRow.command_result,
                        PlayerCharacterMutationReceiptRow.resulting_revision,
                        PlayerCharacterMutationReceiptRow.resulting_lifecycle,
                        PlayerCharacterMutationReceiptRow.receipt_canonical,
                        PlayerCharacterMutationReceiptRow.operation_evidence_canonical,
                    )
                    .where(
                        PlayerCharacterMutationReceiptRow.player_character_id
                        == player_character_id.value
                    )
                    .order_by(
                        PlayerCharacterMutationReceiptRow.resulting_revision,
                        PlayerCharacterMutationReceiptRow.operation_id,
                    )
                )
            ).all()
        )
    return _DurableCharacterSnapshot(
        current=current,
        controller_binding=stored_binding,
        revisions=revisions,
        creation_receipts=creation_receipts,
        mutation_receipts=mutation_receipts,
    )


async def _get(app, path: str) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://testserver",
    ) as client:
        return await client.get(path)


async def _post(
    app,
    *,
    key: str,
    body: dict[str, object] | None = None,
) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://testserver",
    ) as client:
        return await client.post(
            "/v1/player-characters",
            headers={"Idempotency-Key": key},
            json=body
            or {
                "contract_version": "structured-player-character/v1",
                "character_core": {},
                "narration_preferences": {},
            },
        )


async def _retire(
    app,
    player_character_id: PlayerCharacterId,
    *,
    key: str,
    revision: int = 1,
) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://testserver",
    ) as client:
        return await client.post(
            f"/v1/player-characters/{player_character_id.value}/retirement",
            headers={"Idempotency-Key": key},
            json={
                "contract_version": "structured-player-character/v1",
                "expected_revision": {"value": revision},
                "confirm_retirement": True,
            },
        )


def _app(service: PlayerCharacterService, principal: RequestPrincipal):
    services = ApiServices(
        session_service=object(),  # type: ignore[arg-type]
        turn_orchestrator=object(),  # type: ignore[arg-type]
        player_character_service=service,
    )
    app = create_app(services=services)
    app.state.api_services = services
    app.dependency_overrides[get_current_principal] = lambda: principal
    return app


class _PreCommitFailureUnitOfWork(SqlAlchemyUnitOfWork):
    async def commit(self) -> None:
        raise RuntimeError("controlled API pre-COMMIT failure")


class _CountingUnitOfWork(SqlAlchemyUnitOfWork):
    def __init__(self, factory, commits: list[int]) -> None:
        super().__init__(factory)
        self._commits = commits

    async def commit(self) -> None:
        self._commits.append(1)
        await super().commit()


class _UncertainCommitUnitOfWork(SqlAlchemyUnitOfWork):
    async def commit(self) -> None:
        await super().commit()
        raise RuntimeError("controlled uncertain COMMIT")


def _recording_uow(
    uow_type: type[SqlAlchemyUnitOfWork],
    factory: async_sessionmaker[AsyncSession],
    created: list[Any],
) -> SqlAlchemyUnitOfWork:
    uow = uow_type(factory)
    created.append(uow)
    return uow


class _CancelledCommitUnitOfWork(SqlAlchemyUnitOfWork):
    async def commit(self) -> None:
        raise asyncio.CancelledError()


@dataclass(slots=True)
class _BindingRaceCoordinator:
    ready: asyncio.Event = field(default_factory=asyncio.Event)
    start: asyncio.Event = field(default_factory=asyncio.Event)
    arrivals: int = 0


class _BindingRaceRepository:
    def __init__(self, repository: SqlAlchemyControllerBindingRegistryRepository, coordinator: _BindingRaceCoordinator) -> None:
        self._repository = repository
        self._coordinator = coordinator

    async def lock(self, binding: ControllerBindingRef) -> ControllerBindingRef | None:
        result = await self._repository.lock(binding)
        if result is None and self._coordinator.arrivals < 2:
            self._coordinator.arrivals += 1
            if self._coordinator.arrivals == 2:
                self._coordinator.ready.set()
            await self._coordinator.start.wait()
        return result

    async def add(self, binding: ControllerBindingRef, *, created_at: datetime) -> None:
        await self._repository.add(binding, created_at=created_at)


class _BindingRaceUnitOfWork(SqlAlchemyUnitOfWork):
    def __init__(self, factory, coordinator: _BindingRaceCoordinator, created: list[Any]) -> None:
        super().__init__(factory)
        self._coordinator = coordinator
        self._created = created
        created.append(self)

    async def __aenter__(self):
        await super().__aenter__()
        assert self._session is not None
        await self._session.connection(execution_options={"isolation_level": "READ COMMITTED"})
        self.controller_bindings = _BindingRaceRepository(self.controller_bindings, self._coordinator)  # type: ignore[assignment]
        return self


class _NoWinnerBindingRepository:
    async def lock(self, _: ControllerBindingRef) -> ControllerBindingRef | None:
        return None

    async def add(self, _: ControllerBindingRef, *, created_at: datetime) -> None:
        del created_at
        raise ControllerBindingUniquenessConflictError("controlled binding conflict")


class _NoWinnerUnitOfWork(SqlAlchemyUnitOfWork):
    def __init__(self, factory, created: list[Any]) -> None:
        super().__init__(factory)
        created.append(self)

    async def __aenter__(self):
        await super().__aenter__()
        self.controller_bindings = _NoWinnerBindingRepository()  # type: ignore[assignment]
        return self


class _ForcedBindingRaceRepository:
    def __init__(self, repository: SqlAlchemyControllerBindingRegistryRepository) -> None:
        self._repository = repository

    async def lock(self, _: ControllerBindingRef) -> ControllerBindingRef | None:
        return None

    async def add(self, binding: ControllerBindingRef, *, created_at: datetime) -> None:
        await self._repository.add(binding, created_at=created_at)


class _RecoveryReceiptFailureRepository:
    def __init__(self, repository: Any, receipt_reads: list[bool]) -> None:
        self._repository = repository
        self._receipt_reads = receipt_reads

    async def get(self, key):
        receipt = await self._repository.get(key)
        self._receipt_reads.append(receipt is not None)
        raise RuntimeError("controlled recovery receipt failure: private detail")

    async def add(self, receipt, *, created_at: datetime) -> None:
        await self._repository.add(receipt, created_at=created_at)


class _RecoveryFailureUnitOfWork(SqlAlchemyUnitOfWork):
    def __init__(
        self,
        factory,
        created: list[Any],
        receipt_reads: list[bool],
        commits: list[int],
    ) -> None:
        super().__init__(factory)
        self._created = created
        self._receipt_reads = receipt_reads
        self._commits = commits
        created.append(self)

    async def __aenter__(self):
        await super().__aenter__()
        if len(self._created) == 1:
            self.controller_bindings = _ForcedBindingRaceRepository(
                self.controller_bindings
            )  # type: ignore[assignment]
        else:
            self.creation_receipts = _RecoveryReceiptFailureRepository(
                self.creation_receipts,
                self._receipt_reads,
            )  # type: ignore[assignment]
        return self

    async def commit(self) -> None:
        self._commits.append(1)
        await super().commit()


class _ReceiptLookupRecorder:
    def __init__(self, repository: Any, reads: list[Any]) -> None:
        self._repository = repository
        self._reads = reads

    async def get(self, key: Any) -> Any:
        self._reads.append(key)
        return await self._repository.get(key)

    async def add(self, receipt: Any, *, created_at: datetime) -> None:
        await self._repository.add(receipt, created_at=created_at)


class _ReceiptLookupRecordingUnitOfWork(SqlAlchemyUnitOfWork):
    def __init__(self, factory: Any, reads: list[Any]) -> None:
        super().__init__(factory)
        self._reads = reads

    async def __aenter__(self):
        await super().__aenter__()
        self.mutation_receipts = _ReceiptLookupRecorder(
            self.mutation_receipts,
            self._reads,
        )  # type: ignore[assignment]
        return self


@dataclass(slots=True)
class _SerializedRetirementProbe:
    """Observe normal retirement serialization without replacing production work."""

    counts: dict[str, int] = field(default_factory=dict)
    events: list[str] = field(default_factory=list)
    first_lock_acquired: asyncio.Event = field(default_factory=asyncio.Event)
    release_first: asyncio.Event = field(default_factory=asyncio.Event)
    second_lock_entered: asyncio.Event = field(default_factory=asyncio.Event)
    second_lock_completed: asyncio.Event = field(default_factory=asyncio.Event)
    session_ids: dict[str, int] = field(default_factory=dict)
    connection_ids: dict[str, int] = field(default_factory=dict)
    receipt_reads: dict[str, list[bool]] = field(default_factory=dict)
    receipt_errors: list[BaseException] = field(default_factory=list)
    exit_errors: list[BaseException] = field(default_factory=list)

    def observe(self, event: str, *, role: str | None = None) -> None:
        key = f"{role}.{event}" if role is not None else event
        self.counts[key] = self.counts.get(key, 0) + 1
        self.events.append(key)


class _SerializedRetirementCharacters:
    """Pause after the real aggregate lock and delegate every repository call."""

    def __init__(
        self,
        repository: Any,
        session: AsyncSession,
        probe: _SerializedRetirementProbe,
        *,
        role: str,
    ) -> None:
        self._repository = repository
        self._session = session
        self._probe = probe
        self._role = role

    async def get_for_update(self, player_character_id: PlayerCharacterId) -> Any:
        self._probe.observe("character-get-for-update-entry", role=self._role)
        if self._role == "second":
            self._probe.second_lock_entered.set()
        result = await self._repository.get_for_update(player_character_id)
        connection_id = await self._session.scalar(sa.text("SELECT CONNECTION_ID()"))
        assert connection_id is not None
        self._probe.connection_ids[self._role] = int(connection_id)
        self._probe.observe("character-get-for-update-completion", role=self._role)
        if self._role == "first":
            self._probe.first_lock_acquired.set()
            await asyncio.wait_for(
                self._probe.release_first.wait(),
                timeout=5,
            )
            self._probe.observe("character-lock-release", role=self._role)
        else:
            self._probe.second_lock_completed.set()
        return result

    async def append_revision(self, record: Any, *, created_at: datetime) -> None:
        self._probe.observe("append-revision-entry", role=self._role)
        await self._repository.append_revision(record, created_at=created_at)
        self._probe.observe("append-revision-completion", role=self._role)

    async def compare_and_swap_current(
        self,
        record: Any,
        *,
        expected_revision: int,
        created_at: datetime,
    ) -> bool:
        self._probe.observe("compare-and-swap-entry", role=self._role)
        result = await self._repository.compare_and_swap_current(
            record,
            expected_revision=expected_revision,
            created_at=created_at,
        )
        self._probe.observe("compare-and-swap-completion", role=self._role)
        return result

    def __getattr__(self, name: str) -> Any:
        return getattr(self._repository, name)


class _SerializedRetirementReceipts:
    """Record receipt calls while delegating to the production repository."""

    def __init__(
        self,
        repository: Any,
        probe: _SerializedRetirementProbe,
        *,
        role: str,
    ) -> None:
        self._repository = repository
        self._probe = probe
        self._role = role

    async def get(self, key: Any) -> Any:
        self._probe.observe("receipt-get-entry", role=self._role)
        result = await self._repository.get(key)
        self._probe.receipt_reads.setdefault(self._role, []).append(
            result is not None
        )
        self._probe.observe("receipt-get-completion", role=self._role)
        return result

    async def add(self, receipt: Any, *, created_at: datetime) -> None:
        self._probe.observe("receipt-add-entry", role=self._role)
        try:
            await self._repository.add(receipt, created_at=created_at)
        except BaseException as exc:
            self._probe.observe("receipt-add-error", role=self._role)
            self._probe.receipt_errors.append(exc)
            raise
        self._probe.observe("receipt-add-completion", role=self._role)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._repository, name)


class _SerializedRetirementUnitOfWork(SqlAlchemyUnitOfWork):
    def __init__(
        self,
        factory: Any,
        probe: _SerializedRetirementProbe,
        created: list[Any],
    ) -> None:
        super().__init__(factory)
        self._probe = probe
        self._role = (
            "first"
            if len(created) == 0
            else "second"
            if len(created) == 1
            else f"unexpected-{len(created) + 1}"
        )
        created.append(self)
        self._probe.observe("uow-created", role=self._role)

    async def __aenter__(self):
        self._probe.observe("uow-entry", role=self._role)
        await super().__aenter__()
        assert self._session is not None
        self._probe.session_ids[self._role] = id(self._session)
        self.player_characters = _SerializedRetirementCharacters(
            self.player_characters,
            self._session,
            self._probe,
            role=self._role,
        )  # type: ignore[assignment]
        self.mutation_receipts = _SerializedRetirementReceipts(
            self.mutation_receipts,
            self._probe,
            role=self._role,
        )  # type: ignore[assignment]
        self._probe.observe("uow-entry-completion", role=self._role)
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        self._probe.observe("uow-exit", role=self._role)
        if exc is not None:
            self._probe.exit_errors.append(exc)
        await super().__aexit__(exc_type, exc, traceback)
        self._probe.observe("uow-exit-completion", role=self._role)

    async def commit(self) -> None:
        self._probe.observe("uow-commit-entry", role=self._role)
        await super().commit()
        self._probe.observe("uow-commit-completion", role=self._role)


async def _run_serialized_retirements(
    app: Any,
    player_character_id: PlayerCharacterId,
    *,
    key: str,
    second_revision: int,
    probe: _SerializedRetirementProbe,
) -> tuple[httpx.Response, httpx.Response]:
    """Hold only the first delegated aggregate lock while the second queues."""

    first = asyncio.create_task(
        _retire(app, player_character_id, key=key, revision=1)
    )
    second: asyncio.Task[httpx.Response] | None = None
    try:
        await asyncio.wait_for(probe.first_lock_acquired.wait(), timeout=5)
        assert not first.done()
        second = asyncio.create_task(
            _retire(
                app,
                player_character_id,
                key=key,
                revision=second_revision,
            )
        )
        await asyncio.wait_for(probe.second_lock_entered.wait(), timeout=5)
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                probe.second_lock_completed.wait(),
                timeout=0.25,
            )
        assert not first.done()
        assert not second.done()
        probe.release_first.set()
        responses = await asyncio.wait_for(
            asyncio.gather(first, second),
            timeout=5,
        )
        return responses[0], responses[1]
    finally:
        probe.release_first.set()
        tasks = [first, *([second] if second is not None else [])]
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


def _assert_one_serialized_retirement(
    probe: _SerializedRetirementProbe,
    uows: list[Any],
    *,
    policy_calls: int,
) -> None:
    assert len(uows) == 2
    assert [uow._role for uow in uows] == ["first", "second"]
    assert len(set(probe.session_ids.values())) == 2
    assert len(set(probe.connection_ids.values())) == 2
    assert probe.receipt_reads == {"first": [False], "second": [True]}
    assert probe.receipt_errors == []
    assert probe.exit_errors == []
    assert policy_calls == 1
    for role in ("first", "second"):
        assert probe.counts[f"{role}.uow-created"] == 1
        assert probe.counts[f"{role}.uow-entry"] == 1
        assert probe.counts[f"{role}.uow-entry-completion"] == 1
        assert probe.counts[f"{role}.uow-exit"] == 1
        assert probe.counts[f"{role}.uow-exit-completion"] == 1
        assert probe.counts[f"{role}.character-get-for-update-entry"] == 1
        assert probe.counts[f"{role}.character-get-for-update-completion"] == 1
        assert probe.counts[f"{role}.receipt-get-entry"] == 1
        assert probe.counts[f"{role}.receipt-get-completion"] == 1
    assert probe.counts["first.character-lock-release"] == 1
    assert probe.counts["first.append-revision-entry"] == 1
    assert probe.counts["first.append-revision-completion"] == 1
    assert probe.counts["first.compare-and-swap-entry"] == 1
    assert probe.counts["first.compare-and-swap-completion"] == 1
    assert probe.counts["first.receipt-add-entry"] == 1
    assert probe.counts["first.receipt-add-completion"] == 1
    assert probe.counts["first.uow-commit-entry"] == 1
    assert probe.counts["first.uow-commit-completion"] == 1
    assert not any(key.startswith("second.append-revision") for key in probe.counts)
    assert not any(key.startswith("second.compare-and-swap") for key in probe.counts)
    assert not any(key.startswith("second.receipt-add") for key in probe.counts)
    assert "second.uow-commit-entry" not in probe.counts
    assert not any(key.startswith("unexpected-") for key in probe.counts)


async def test_mysql_retirement_replay_and_precedence_preserve_durable_state(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    player_character_api_scope: _Scope,
) -> None:
    token = player_character_api_scope.token
    principal = RequestPrincipal(
        player_id=f"player.retirement-{token}",
        authentication_scheme="test",
    )
    binding = ControllerBindingRef(value=f"binding.retirement-{token}")
    player_character_id = PlayerCharacterId(value=f"pc.retirement-{token}")
    player_character_api_scope.bindings.add(binding.value)
    player_character_api_scope.character_ids.add(player_character_id.value)
    app = _app(_service(mysql_session_factory, binding, player_character_id), principal)

    created = await _post(app, key=f"create-{token}")
    assert created.status_code == 200
    retired = await _retire(app, player_character_id, key=f"retire-{token}")
    assert retired.status_code == 200
    assert retired.json() == {
        "player_character_id": {"value": player_character_id.value},
        "contract_version": "structured-player-character/v1",
        "record_revision": {"value": 2},
        "lifecycle": "retired",
    }
    after_success = await _counts(
        mysql_session_factory, player_character_id.value, binding.value
    )
    assert after_success == (1, 1, 2, 1, 1, 1)
    success_snapshot = await _durable_character_snapshot(
        mysql_session_factory,
        player_character_id,
        binding,
    )
    assert success_snapshot.current is not None
    assert success_snapshot.current.player_character_id == player_character_id
    assert success_snapshot.current.controller_binding == binding
    assert success_snapshot.current.contract_version is PlayerCharacterContractVersion.V1
    assert success_snapshot.current.record_revision.value == 2
    assert success_snapshot.current.lifecycle.value == "retired"
    assert success_snapshot.controller_binding == binding.value
    assert len(success_snapshot.revisions) == 2
    assert [row[0] for row in success_snapshot.revisions] == [1, 2]
    assert [row[3] for row in success_snapshot.revisions] == ["active", "retired"]
    assert len(success_snapshot.creation_receipts) == 1
    assert len(success_snapshot.mutation_receipts) == 1
    original_receipt = success_snapshot.mutation_receipts[0]
    assert original_receipt[0] == CharacterOperationNamespace.MUTATE_V1.value
    assert original_receipt[1] == f"retire-{token}"
    assert len(original_receipt[2]) == 32
    assert original_receipt[3:12] == (
        "RETIRE",
        "player-character.mutate-result/v1",
        1,
        player_character_id.value,
        PlayerCharacterContractVersion.V1.value,
        "RETIRE",
        "RETIRED",
        2,
        "retired",
    )
    assert original_receipt[12]
    assert original_receipt[13]

    replay = await _retire(app, player_character_id, key=f"retire-{token}")
    assert replay.status_code == 200
    assert replay.json() == retired.json()
    assert await _counts(mysql_session_factory, player_character_id.value, binding.value) == after_success
    assert await _durable_character_snapshot(
        mysql_session_factory,
        player_character_id,
        binding,
    ) == success_snapshot

    differing_reuse = await _retire(
        app, player_character_id, key=f"retire-{token}", revision=2
    )
    assert differing_reuse.status_code == 409
    assert differing_reuse.json()["error"]["error_code"] == "IDEMPOTENCY_CONFLICT"
    assert await _durable_character_snapshot(
        mysql_session_factory,
        player_character_id,
        binding,
    ) == success_snapshot
    reused_maximum = await _retire(
        app,
        player_character_id,
        key=f"retire-{token}",
        revision=9223372036854775807,
    )
    assert reused_maximum.status_code == 409
    assert reused_maximum.json()["error"]["error_code"] == "PLAYER_CHARACTER_REVISION_CONFLICT"
    assert await _durable_character_snapshot(
        mysql_session_factory,
        player_character_id,
        binding,
    ) == success_snapshot
    lifecycle = await _retire(
        app, player_character_id, key=f"retire-new-{token}", revision=2
    )
    assert lifecycle.status_code == 409
    assert lifecycle.json()["error"]["error_code"] == "PLAYER_CHARACTER_LIFECYCLE_CONFLICT"
    assert await _durable_character_snapshot(
        mysql_session_factory,
        player_character_id,
        binding,
    ) == success_snapshot
    new_maximum = await _retire(
        app,
        player_character_id,
        key=f"retire-maximum-{token}",
        revision=9223372036854775807,
    )
    assert new_maximum.status_code == 409
    assert new_maximum.json()["error"]["error_code"] == "PLAYER_CHARACTER_REVISION_CONFLICT"
    assert await _counts(mysql_session_factory, player_character_id.value, binding.value) == after_success
    assert await _durable_character_snapshot(
        mysql_session_factory,
        player_character_id,
        binding,
    ) == success_snapshot


async def test_mysql_retirement_maximum_revision_does_not_lookup_a_receipt(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    player_character_api_scope: _Scope,
) -> None:
    token = player_character_api_scope.token
    principal = RequestPrincipal(player_id=f"player.receipt-{token}", authentication_scheme="test")
    binding = ControllerBindingRef(value=f"binding.receipt-{token}")
    player_character_id = PlayerCharacterId(value=f"pc.receipt-{token}")
    player_character_api_scope.bindings.add(binding.value)
    player_character_api_scope.character_ids.add(player_character_id.value)
    normal = _service(mysql_session_factory, binding, player_character_id)
    app = _app(normal, principal)
    assert (await _post(app, key=f"create-{token}")).status_code == 200
    assert (await _retire(app, player_character_id, key=f"retire-{token}")).status_code == 200
    before = await _counts(mysql_session_factory, player_character_id.value, binding.value)

    receipt_reads: list[Any] = []
    recorded = _service(
        mysql_session_factory,
        binding,
        player_character_id,
        uow_factory=lambda: _ReceiptLookupRecordingUnitOfWork(
            mysql_session_factory,
            receipt_reads,
        ),
    )
    response = await _retire(
        _app(recorded, principal),
        player_character_id,
        key=f"retire-{token}",
        revision=9223372036854775807,
    )

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "error_code": "PLAYER_CHARACTER_REVISION_CONFLICT",
            "message": "Player character revision does not permit retirement",
        }
    }
    assert receipt_reads == []
    assert await _counts(mysql_session_factory, player_character_id.value, binding.value) == before


async def test_mysql_concurrent_identical_retirements_serialize_to_one_mutation_and_exact_replay(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    player_character_api_scope: _Scope,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prove the reachable production path queues at the aggregate lock."""

    token = player_character_api_scope.token
    principal = RequestPrincipal(
        player_id=f"player.concurrent-replay-{token}",
        authentication_scheme="test",
    )
    binding = ControllerBindingRef(value=f"binding.concurrent-replay-{token}")
    player_character_id = PlayerCharacterId(
        value=f"pc.concurrent-replay-{token}"
    )
    key = f"retire-concurrent-replay-{token}"
    player_character_api_scope.bindings.add(binding.value)
    player_character_api_scope.character_ids.add(player_character_id.value)
    normal = _service(mysql_session_factory, binding, player_character_id)
    normal_app = _app(normal, principal)
    assert (await _post(normal_app, key=f"create-{token}")).status_code == 200

    probe = _SerializedRetirementProbe()
    uows: list[Any] = []
    policy_calls = 0
    original_evaluate_policy = player_character_service_module.evaluate_mutation_policy

    def recording_evaluate_policy(*args: Any, **kwargs: Any) -> Any:
        nonlocal policy_calls
        policy_calls += 1
        result = original_evaluate_policy(*args, **kwargs)
        return result

    monkeypatch.setattr(
        player_character_service_module,
        "evaluate_mutation_policy",
        recording_evaluate_policy,
    )
    service = _service(
        mysql_session_factory,
        binding,
        player_character_id,
        uow_factory=lambda: _SerializedRetirementUnitOfWork(
            mysql_session_factory,
            probe,
            uows,
        ),
    )

    first, replay = await _run_serialized_retirements(
        _app(service, principal),
        player_character_id,
        key=key,
        second_revision=1,
        probe=probe,
    )

    expected_projection = {
        "player_character_id": {"value": player_character_id.value},
        "contract_version": "structured-player-character/v1",
        "record_revision": {"value": 2},
        "lifecycle": "retired",
    }
    assert first.status_code == replay.status_code == 200
    assert first.json() == replay.json() == expected_projection
    _assert_one_serialized_retirement(
        probe,
        uows,
        policy_calls=policy_calls,
    )

    final_snapshot = await _durable_character_snapshot(
        mysql_session_factory,
        player_character_id,
        binding,
    )
    assert final_snapshot.current is not None
    assert final_snapshot.current.player_character_id == player_character_id
    assert final_snapshot.current.controller_binding == binding
    assert (
        final_snapshot.current.contract_version
        is PlayerCharacterContractVersion.V1
    )
    assert final_snapshot.current.record_revision.value == 2
    assert final_snapshot.current.lifecycle.value == "retired"
    assert final_snapshot.controller_binding == binding.value
    assert len(final_snapshot.revisions) == 2
    assert len(final_snapshot.creation_receipts) == 1
    assert len(final_snapshot.mutation_receipts) == 1
    stored_row = final_snapshot.mutation_receipts[0]
    assert stored_row[0] == CharacterOperationNamespace.MUTATE_V1.value
    assert stored_row[1] == key
    assert stored_row[3:12] == (
        "RETIRE",
        "player-character.mutate-result/v1",
        1,
        player_character_id.value,
        PlayerCharacterContractVersion.V1.value,
        "RETIRE",
        "RETIRED",
        2,
        "retired",
    )
    assert await _counts(
        mysql_session_factory,
        player_character_id.value,
        binding.value,
    ) == (1, 1, 2, 1, 1, 1)


async def test_mysql_concurrent_different_retirement_fingerprints_serialize_to_idempotency_conflict(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    player_character_api_scope: _Scope,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A differing normal HTTP request waits at the same aggregate boundary."""

    token = player_character_api_scope.token
    principal = RequestPrincipal(
        player_id=f"player.concurrent-conflict-{token}",
        authentication_scheme="test",
    )
    binding = ControllerBindingRef(value=f"binding.concurrent-conflict-{token}")
    player_character_id = PlayerCharacterId(
        value=f"pc.concurrent-conflict-{token}"
    )
    key = f"retire-concurrent-conflict-{token}"
    player_character_api_scope.bindings.add(binding.value)
    player_character_api_scope.character_ids.add(player_character_id.value)
    normal = _service(mysql_session_factory, binding, player_character_id)
    assert (
        await _post(_app(normal, principal), key=f"create-{token}")
    ).status_code == 200

    probe = _SerializedRetirementProbe()
    uows: list[Any] = []
    policy_calls = 0
    original_evaluate_policy = player_character_service_module.evaluate_mutation_policy

    def recording_evaluate_policy(*args: Any, **kwargs: Any) -> Any:
        nonlocal policy_calls
        policy_calls += 1
        return original_evaluate_policy(*args, **kwargs)

    monkeypatch.setattr(
        player_character_service_module,
        "evaluate_mutation_policy",
        recording_evaluate_policy,
    )
    service = _service(
        mysql_session_factory,
        binding,
        player_character_id,
        uow_factory=lambda: _SerializedRetirementUnitOfWork(
            mysql_session_factory,
            probe,
            uows,
        ),
    )

    first, conflict = await _run_serialized_retirements(
        _app(service, principal),
        player_character_id,
        key=key,
        second_revision=2,
        probe=probe,
    )

    assert first.status_code == 200
    assert first.json() == {
        "player_character_id": {"value": player_character_id.value},
        "contract_version": "structured-player-character/v1",
        "record_revision": {"value": 2},
        "lifecycle": "retired",
    }
    assert conflict.status_code == 409
    assert conflict.json() == {
        "error": {
            "error_code": "IDEMPOTENCY_CONFLICT",
            "message": "Idempotency key was reused",
        }
    }
    _assert_one_serialized_retirement(
        probe,
        uows,
        policy_calls=policy_calls,
    )

    final_snapshot = await _durable_character_snapshot(
        mysql_session_factory,
        player_character_id,
        binding,
    )
    assert final_snapshot.current is not None
    assert final_snapshot.current.record_revision.value == 2
    assert final_snapshot.current.lifecycle.value == "retired"
    assert len(final_snapshot.revisions) == 2
    assert len(final_snapshot.creation_receipts) == 1
    assert len(final_snapshot.mutation_receipts) == 1
    assert final_snapshot.mutation_receipts[0][1] == key
    assert await _counts(
        mysql_session_factory,
        player_character_id.value,
        binding.value,
    ) == (1, 1, 2, 1, 1, 1)


async def test_mysql_retirement_active_binding_rejects_without_mutating_run_or_character(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    player_character_api_scope: _Scope,
) -> None:
    token = player_character_api_scope.token
    principal = RequestPrincipal(player_id=f"player.bound-{token}", authentication_scheme="test")
    binding = ControllerBindingRef(value=f"binding.bound-{token}")
    player_character_id = PlayerCharacterId(value=f"pc.bound-{token}")
    run_id = RunId(value=f"run.bound-{token}")
    line_id = ContinuousStoryLineId(value=f"line.bound-{token}")
    player_character_api_scope.bindings.add(binding.value)
    player_character_api_scope.character_ids.add(player_character_id.value)
    player_character_api_scope.run_ids.add(run_id.value)
    service = _service(mysql_session_factory, binding, player_character_id)
    app = _app(service, principal)
    assert (await _post(app, key=f"create-{token}")).status_code == 200
    run_service = RunService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(mysql_session_factory),
        run_id_issuer=_Issuer(run_id),
        continuous_story_line_id_issuer=_Issuer(line_id),
        source_reference=RunAuthoritySourceRef(value="source.mysql-api-run"),
        clock=lambda: _NOW,
        controller_binding_resolver=_Resolver(binding),
        player_character_binding_evidence=service,
    )
    await run_service.create_run(
        operation_id=RunOperationId(value=f"create-run-{token}"),
        command=CreateRunCommand(
            source_reference=RunAuthoritySourceRef(value="source.mysql-api-run")
        ),
    )
    await run_service.bind_player_character_internal(
        principal,
        operation_id=RunOperationId(value=f"bind-run-{token}"),
        command=BindPlayerCharacterCommand(
            run_id=run_id,
            continuous_story_line_id=line_id,
            target_player_character_id=player_character_id,
            expected_state_version=RunStateVersion(value=1),
            source_reference=RunAuthoritySourceRef(value="source.mysql-api-run"),
        ),
    )
    character_before = await _counts(mysql_session_factory, player_character_id.value, binding.value)
    durable_character_before = await _durable_character_snapshot(
        mysql_session_factory,
        player_character_id,
        binding,
    )
    async with mysql_session_factory() as session:
        run_before = await session.get(RunCurrentRow, run_id.value)
        assert run_before is not None
        run_before_state = (
            run_before.state_version,
            run_before.lifecycle_status,
            run_before.binding_player_character_id,
            run_before.binding_record_revision,
            run_before.binding_state,
            run_before.active_player_character_id,
            run_before.operation_id,
        )

    response = await _retire(app, player_character_id, key=f"retire-{token}")

    assert response.status_code == 409
    assert response.json()["error"]["error_code"] == "PLAYER_CHARACTER_ACTIVE_BINDING_CONFLICT"
    assert await _counts(mysql_session_factory, player_character_id.value, binding.value) == character_before
    assert await _durable_character_snapshot(
        mysql_session_factory,
        player_character_id,
        binding,
    ) == durable_character_before
    async with mysql_session_factory() as session:
        run_after = await session.get(RunCurrentRow, run_id.value)
        assert run_after is not None
        assert (
            run_after.state_version,
            run_after.lifecycle_status,
            run_after.binding_player_character_id,
            run_after.binding_record_revision,
            run_after.binding_state,
            run_after.active_player_character_id,
            run_after.operation_id,
        ) == run_before_state


async def test_mysql_retirement_missing_and_foreign_targets_are_non_enumerating(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    player_character_api_scope: _Scope,
) -> None:
    token = player_character_api_scope.token
    principal = RequestPrincipal(player_id=f"player.owner-{token}", authentication_scheme="test")
    binding = ControllerBindingRef(value=f"binding.owner-{token}")
    player_character_id = PlayerCharacterId(value=f"pc.owner-{token}")
    player_character_api_scope.bindings.add(binding.value)
    player_character_api_scope.character_ids.add(player_character_id.value)
    owner_app = _app(_service(mysql_session_factory, binding, player_character_id), principal)
    assert (await _post(owner_app, key=f"create-{token}")).status_code == 200
    foreign_app = _app(
        _service(
            mysql_session_factory,
            ControllerBindingRef(value=f"binding.foreign-{token}"),
            player_character_id,
        ),
        principal,
    )
    missing = await _retire(
        owner_app,
        PlayerCharacterId(value=f"pc.missing-{token}"),
        key=f"missing-{token}",
    )
    foreign = await _retire(foreign_app, player_character_id, key=f"foreign-{token}")

    assert missing.status_code == foreign.status_code == 404
    assert missing.json() == foreign.json() == {
        "error": {
            "error_code": "PLAYER_CHARACTER_NOT_FOUND",
            "message": "Player character was not found",
        }
    }


async def test_mysql_retirement_precommit_and_uncertain_commit_are_sanitized_without_recovery(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    player_character_api_scope: _Scope,
) -> None:
    token = player_character_api_scope.token
    principal = RequestPrincipal(player_id=f"player.failure-{token}", authentication_scheme="test")
    binding = ControllerBindingRef(value=f"binding.failure-{token}")
    player_character_id = PlayerCharacterId(value=f"pc.failure-{token}")
    player_character_api_scope.bindings.add(binding.value)
    player_character_api_scope.character_ids.add(player_character_id.value)
    normal_app = _app(_service(mysql_session_factory, binding, player_character_id), principal)
    assert (await _post(normal_app, key=f"create-{token}")).status_code == 200
    before = await _counts(mysql_session_factory, player_character_id.value, binding.value)
    durable_before = await _durable_character_snapshot(
        mysql_session_factory,
        player_character_id,
        binding,
    )

    precommit_uows: list[Any] = []
    precommit = _service(
        mysql_session_factory,
        binding,
        player_character_id,
        uow_factory=lambda: _recording_uow(
            _PreCommitFailureUnitOfWork,
            mysql_session_factory,
            precommit_uows,
        ),
    )
    precommit_response = await _retire(
        _app(precommit, principal), player_character_id, key=f"precommit-{token}"
    )
    assert precommit_response.status_code == 500
    assert precommit_response.json()["error"]["error_code"] == "INTERNAL_SERVER_ERROR"
    assert len(precommit_uows) == 1
    assert await _counts(mysql_session_factory, player_character_id.value, binding.value) == before
    assert await _durable_character_snapshot(
        mysql_session_factory,
        player_character_id,
        binding,
    ) == durable_before

    uncertain_uows: list[Any] = []
    uncertain = _service(
        mysql_session_factory,
        binding,
        player_character_id,
        uow_factory=lambda: _recording_uow(
            _UncertainCommitUnitOfWork,
            mysql_session_factory,
            uncertain_uows,
        ),
    )
    uncertain_response = await _retire(
        _app(uncertain, principal), player_character_id, key=f"uncertain-{token}"
    )
    assert uncertain_response.status_code == 500
    assert uncertain_response.json()["error"]["error_code"] == "INTERNAL_SERVER_ERROR"
    assert len(uncertain_uows) == 1
    assert await _counts(mysql_session_factory, player_character_id.value, binding.value) == (1, 1, 2, 1, 1, 1)
    uncertain_snapshot = await _durable_character_snapshot(
        mysql_session_factory,
        player_character_id,
        binding,
    )
    assert uncertain_snapshot.current is not None
    assert uncertain_snapshot.current.player_character_id == player_character_id
    assert uncertain_snapshot.current.controller_binding == binding
    assert uncertain_snapshot.current.contract_version is PlayerCharacterContractVersion.V1
    assert uncertain_snapshot.current.record_revision.value == 2
    assert uncertain_snapshot.current.lifecycle.value == "retired"
    assert uncertain_snapshot.controller_binding == binding.value
    assert len(uncertain_snapshot.revisions) == 2
    assert len(uncertain_snapshot.creation_receipts) == 1
    assert len(uncertain_snapshot.mutation_receipts) == 1
    uncertain_receipt = uncertain_snapshot.mutation_receipts[0]
    assert uncertain_receipt[0] == CharacterOperationNamespace.MUTATE_V1.value
    assert uncertain_receipt[1] == f"uncertain-{token}"
    assert uncertain_receipt[3:12] == (
        "RETIRE",
        "player-character.mutate-result/v1",
        1,
        player_character_id.value,
        PlayerCharacterContractVersion.V1.value,
        "RETIRE",
        "RETIRED",
        2,
        "retired",
    )

async def test_mysql_owned_read_is_non_enumerating_and_has_no_write_side_effect(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    player_character_api_scope: _Scope,
) -> None:
    token = player_character_api_scope.token
    principal = RequestPrincipal(player_id=f"player.api-{token}", authentication_scheme="test")
    binding = ControllerBindingRef(value=f"binding.api-{token}")
    player_character_id = PlayerCharacterId(value=f"pc.api-{token}")
    player_character_api_scope.bindings.add(binding.value)
    player_character_api_scope.character_ids.add(player_character_id.value)
    service = _service(mysql_session_factory, binding, player_character_id)
    created = await service.create(
        principal,
        operation_id=PlayerCharacterOperationId(value=f"operation.api-{token}"),
        command=CharacterCreationCommand(
            contract_version=PlayerCharacterContractVersion.V1,
            character_core=CharacterCore(),
            narration_preferences=NarrationPreferences(),
        ),
    )
    assert created.player_character_id == player_character_id
    before = await _counts(mysql_session_factory, player_character_id.value, binding.value)

    services = ApiServices(
        session_service=object(),  # type: ignore[arg-type]
        turn_orchestrator=object(),  # type: ignore[arg-type]
        player_character_service=service,
    )
    app = create_app(services=services)
    app.state.api_services = services
    app.dependency_overrides[get_current_principal] = lambda: principal
    owned = await _get(app, f"/v1/player-characters/{player_character_id.value}")
    absent = await _get(app, f"/v1/player-characters/pc.absent-{token}")

    other_service = _service(
        mysql_session_factory,
        ControllerBindingRef(value=f"binding.other-{token}"),
        player_character_id,
    )
    foreign_services = ApiServices(
        session_service=object(),  # type: ignore[arg-type]
        turn_orchestrator=object(),  # type: ignore[arg-type]
        player_character_service=other_service,
    )
    foreign_app = create_app(services=foreign_services)
    foreign_app.state.api_services = foreign_services
    foreign_app.dependency_overrides[get_current_principal] = lambda: principal
    foreign = await _get(
        foreign_app,
        f"/v1/player-characters/{player_character_id.value}",
    )

    assert owned.status_code == 200
    assert owned.json() == {
        "player_character_id": {"value": player_character_id.value},
        "contract_version": "structured-player-character/v1",
        "record_revision": {"value": 1},
        "lifecycle": "active",
    }
    assert absent.status_code == foreign.status_code == 404
    assert absent.json() == foreign.json() == {
        "error": {
            "error_code": "PLAYER_CHARACTER_NOT_FOUND",
            "message": "Player character was not found",
        }
    }
    assert await _counts(mysql_session_factory, player_character_id.value, binding.value) == before


async def test_mysql_eligible_discovery_is_binary_ordered_bounded_isolated_and_read_only(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    player_character_api_scope: _Scope,
) -> None:
    token = player_character_api_scope.token
    principal = RequestPrincipal(
        player_id=f"player.eligible-{token}", authentication_scheme="test"
    )
    binding = ControllerBindingRef(value=f"binding.eligible-{token}")
    foreign_binding = ControllerBindingRef(value=f"binding.eligible-foreign-{token}")
    player_character_api_scope.bindings.update((binding.value, foreign_binding.value))
    ids = [
        PlayerCharacterId(value=f"pc.eligible-{token}-{suffix}")
        for suffix in ("A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", "a", "b", "c", "d", "e", "f", "g", "h", "i")
    ]
    foreign_id = PlayerCharacterId(value=f"pc.eligible-{token}-foreign")
    player_character_api_scope.character_ids.update(
        [character_id.value for character_id in ids] + [foreign_id.value]
    )
    command = CharacterCreationCommand(
        contract_version=PlayerCharacterContractVersion.V1,
        character_core=CharacterCore(),
        narration_preferences=NarrationPreferences(),
    )
    for index, player_character_id in enumerate(ids):
        service = _service(mysql_session_factory, binding, player_character_id)
        result = await service.create(
            principal,
            operation_id=PlayerCharacterOperationId(
                value=f"operation.eligible-{token}-{index}"
            ),
            command=command,
        )
        assert result.player_character_id == player_character_id
    foreign_service = _service(mysql_session_factory, foreign_binding, foreign_id)
    await foreign_service.create(
        principal,
        operation_id=PlayerCharacterOperationId(value=f"operation.eligible-foreign-{token}"),
        command=command,
    )
    run_id = RunId(value=f"run.eligible-{token}")
    line_id = ContinuousStoryLineId(value=f"line.eligible-{token}")
    player_character_api_scope.run_ids.add(run_id.value)
    binding_service = _service(mysql_session_factory, binding, ids[0])
    run_service = RunService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(mysql_session_factory),
        run_id_issuer=_Issuer(run_id),
        continuous_story_line_id_issuer=_Issuer(line_id),
        source_reference=RunAuthoritySourceRef(value="source.mysql-eligible-run"),
        clock=lambda: _NOW,
        controller_binding_resolver=_Resolver(binding),
        player_character_binding_evidence=binding_service,
    )
    await run_service.create_run(
        operation_id=RunOperationId(value=f"create-eligible-run-{token}"),
        command=CreateRunCommand(
            source_reference=RunAuthoritySourceRef(value="source.mysql-eligible-run")
        ),
    )
    await run_service.bind_player_character_internal(
        principal,
        operation_id=RunOperationId(value=f"bind-eligible-run-{token}"),
        command=BindPlayerCharacterCommand(
            run_id=run_id,
            continuous_story_line_id=line_id,
            target_player_character_id=ids[0],
            expected_state_version=RunStateVersion(value=1),
            source_reference=RunAuthoritySourceRef(value="source.mysql-eligible-run"),
        ),
    )
    retirement_app = _app(binding_service, principal)
    retired = await _retire(
        retirement_app,
        ids[1],
        key=f"retire-eligible-{token}",
    )
    assert retired.status_code == 200

    commits: list[int] = []
    discovery = _service(
        mysql_session_factory,
        binding,
        ids[0],
        uow_factory=lambda: _CountingUnitOfWork(mysql_session_factory, commits),
    )
    app = _app(discovery, principal)
    observed_sql: list[str] = []

    def observe_statement(
        _connection, _cursor, statement, _parameters, _context, _executemany
    ) -> None:
        observed_sql.append(statement)

    engine = mysql_session_factory.kw["bind"].sync_engine
    sa.event.listen(engine, "before_cursor_execute", observe_statement)
    try:
        response = await _get(app, "/v1/player-characters/eligible-for-run-entry")
    finally:
        sa.event.remove(engine, "before_cursor_execute", observe_statement)

    assert response.status_code == 200
    body = response.json()
    returned_ids = [item["player_character_id"]["value"] for item in body["eligible_player_characters"]]
    expected_ids = sorted(
        character_id.value for character_id in ids if character_id not in (ids[0], ids[1])
    )
    assert returned_ids == expected_ids[:32]
    assert len(returned_ids) == 32
    assert foreign_id.value not in returned_ids
    assert ids[0].value not in returned_ids
    assert ids[1].value not in returned_ids
    assert body["truncated"] is True
    assert commits == []
    assert len(observed_sql) == 1
    assert observed_sql[0].lstrip().upper().startswith("SELECT")
    assert "FOR UPDATE" not in observed_sql[0].upper()

    # The previous query discarded every active binding before decoding it.  A
    # current/revision disagreement must instead become the sanitized integrity
    # result for this owner, while the foreign row remains outside the query.
    async with mysql_session_factory.begin() as session:
        await session.execute(
            sa.update(RunRevisionRow)
            .where(
                RunRevisionRow.run_id == run_id.value,
                RunRevisionRow.state_version == 2,
            )
            .values(binding_authority_source_ref="source.mysql-corrupt-binding")
        )
    corrupt_response = await _get(app, "/v1/player-characters/eligible-for-run-entry")
    assert corrupt_response.status_code == 500
    assert corrupt_response.json() == {
        "error": {
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "Internal server error",
        }
    }


@pytest.mark.parametrize("count", (0, 1, 32, 33))
async def test_mysql_eligible_discovery_has_exact_zero_one_thirty_two_and_thirty_three_boundaries(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    player_character_api_scope: _Scope,
    count: int,
) -> None:
    token = player_character_api_scope.token
    principal = RequestPrincipal(player_id=f"player.bound-{token}", authentication_scheme="test")
    binding = ControllerBindingRef(value=f"binding.bound-{token}")
    player_character_api_scope.bindings.add(binding.value)
    command = CharacterCreationCommand(
        contract_version=PlayerCharacterContractVersion.V1,
        character_core=CharacterCore(),
        narration_preferences=NarrationPreferences(),
    )
    ids = [PlayerCharacterId(value=f"pc.bound-{token}-{index:02d}") for index in range(count)]
    player_character_api_scope.character_ids.update(item.value for item in ids)
    for index, player_character_id in enumerate(ids):
        await _service(mysql_session_factory, binding, player_character_id).create(
            principal,
            operation_id=PlayerCharacterOperationId(value=f"operation.bound-{token}-{index}"),
            command=command,
        )

    observed_sql: list[str] = []

    def observe_statement(
        _connection, _cursor, statement, _parameters, _context, _executemany
    ) -> None:
        observed_sql.append(statement)

    engine = mysql_session_factory.kw["bind"].sync_engine
    app = _app(
        _service(
            mysql_session_factory,
            binding,
            PlayerCharacterId(value=f"pc.bound-issuer-{token}"),
        ),
        principal,
    )
    sa.event.listen(engine, "before_cursor_execute", observe_statement)
    try:
        response = await _get(app, "/v1/player-characters/eligible-for-run-entry")
    finally:
        sa.event.remove(engine, "before_cursor_execute", observe_statement)

    assert response.status_code == 200
    body = response.json()
    assert [item["player_character_id"]["value"] for item in body["eligible_player_characters"]] == [
        item.value for item in ids[:32]
    ]
    assert body["truncated"] is (count == 33)
    assert len(observed_sql) == 1
    assert observed_sql[0].lstrip().upper().startswith("SELECT")


async def test_mysql_eligible_discovery_fails_closed_for_owned_scalar_and_active_binding_contradictions(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    player_character_api_scope: _Scope,
) -> None:
    token = player_character_api_scope.token
    principal = RequestPrincipal(player_id=f"player.corrupt-{token}", authentication_scheme="test")
    binding = ControllerBindingRef(value=f"binding.corrupt-{token}")
    foreign_binding = ControllerBindingRef(value=f"binding.corrupt-foreign-{token}")
    owned_id = PlayerCharacterId(value=f"pc.corrupt-{token}")
    foreign_id = PlayerCharacterId(value=f"pc.corrupt-foreign-{token}")
    player_character_api_scope.bindings.update((binding.value, foreign_binding.value))
    player_character_api_scope.character_ids.update((owned_id.value, foreign_id.value))
    await _service(mysql_session_factory, binding, owned_id).create(principal, operation_id=PlayerCharacterOperationId(value=f"operation.corrupt-{token}"), command=CharacterCreationCommand(contract_version=PlayerCharacterContractVersion.V1, character_core=CharacterCore(), narration_preferences=NarrationPreferences()))
    await _service(mysql_session_factory, foreign_binding, foreign_id).create(principal, operation_id=PlayerCharacterOperationId(value=f"operation.corrupt-foreign-{token}"), command=CharacterCreationCommand(contract_version=PlayerCharacterContractVersion.V1, character_core=CharacterCore(), narration_preferences=NarrationPreferences()))
    app = _app(_service(mysql_session_factory, binding, owned_id), principal)
    async with mysql_session_factory.begin() as session:
        await session.execute(
            sa.update(PlayerCharacterCurrentRow)
            .where(PlayerCharacterCurrentRow.player_character_id == foreign_id.value)
            .values(lifecycle="retired")
        )

    isolated_response = await _get(app, "/v1/player-characters/eligible-for-run-entry")
    assert isolated_response.status_code == 200
    assert [item["player_character_id"]["value"] for item in isolated_response.json()["eligible_player_characters"]] == [owned_id.value]

    async with mysql_session_factory.begin() as session:
        await session.execute(
            sa.update(PlayerCharacterCurrentRow)
            .where(PlayerCharacterCurrentRow.player_character_id == owned_id.value)
            .values(lifecycle="retired")
        )

    response = await _get(app, "/v1/player-characters/eligible-for-run-entry")

    assert response.status_code == 500
    assert response.json() == {"error": {"error_code": "INTERNAL_SERVER_ERROR", "message": "Internal server error"}}
    assert owned_id.value not in response.text
    assert foreign_id.value not in response.text


async def test_mysql_eligible_discovery_rejects_stale_current_behind_later_retirement(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    player_character_api_scope: _Scope,
) -> None:
    token = player_character_api_scope.token
    principal = RequestPrincipal(
        player_id=f"player.stale-current-{token}",
        authentication_scheme="test",
    )
    binding = ControllerBindingRef(value=f"binding.stale-current-{token}")
    character_id = PlayerCharacterId(value=f"pc.stale-current-{token}")
    player_character_api_scope.bindings.add(binding.value)
    player_character_api_scope.character_ids.add(character_id.value)
    service = _service(mysql_session_factory, binding, character_id)
    app = _app(service, principal)
    created = await _post(app, key=f"create-stale-current-{token}")
    assert created.status_code == 200
    retired = await _retire(
        app,
        character_id,
        key=f"retire-stale-current-{token}",
    )
    assert retired.status_code == 200

    async with mysql_session_factory.begin() as session:
        revision_one = (
            await session.execute(
                sa.select(
                    PlayerCharacterRevisionRow.contract_version,
                    PlayerCharacterRevisionRow.record_revision,
                    PlayerCharacterRevisionRow.controller_binding,
                    PlayerCharacterRevisionRow.lifecycle,
                    PlayerCharacterRevisionRow.record_canonical,
                    PlayerCharacterRevisionRow.created_at,
                ).where(
                    PlayerCharacterRevisionRow.player_character_id
                    == character_id.value,
                    PlayerCharacterRevisionRow.record_revision == 1,
                )
            )
        ).one()
        await session.execute(
            sa.update(PlayerCharacterCurrentRow)
            .where(
                PlayerCharacterCurrentRow.player_character_id
                == character_id.value
            )
            .values(
                contract_version=revision_one.contract_version,
                record_revision=revision_one.record_revision,
                controller_binding=revision_one.controller_binding,
                lifecycle=revision_one.lifecycle,
                record_canonical=revision_one.record_canonical,
                updated_at=revision_one.created_at,
            )
        )

    response = await _get(
        app,
        "/v1/player-characters/eligible-for-run-entry",
    )

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "Internal server error",
        }
    }
    assert all(
        value not in response.text
        for value in (
            character_id.value,
            binding.value,
            PlayerCharacterContractVersion.V1.value,
            "1",
            "2",
        )
    )
    assert all(
        detail not in response.text.casefold()
        for detail in (
            "select ",
            "player_character_current",
            "player_character_revisions",
            "record_revision",
            "binding_contract_version",
            "retired",
        )
    )


async def test_mysql_eligible_discovery_rejects_equal_unsupported_binding_contract_versions(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    player_character_api_scope: _Scope,
) -> None:
    token = player_character_api_scope.token
    principal = RequestPrincipal(
        player_id=f"player.unsupported-binding-{token}",
        authentication_scheme="test",
    )
    binding = ControllerBindingRef(value=f"binding.unsupported-{token}")
    character_id = PlayerCharacterId(value=f"pc.unsupported-{token}")
    run_id = RunId(value=f"run.unsupported-{token}")
    line_id = ContinuousStoryLineId(value=f"line.unsupported-{token}")
    unsupported_version = "structured-player-character/unsupported"
    player_character_api_scope.bindings.add(binding.value)
    player_character_api_scope.character_ids.add(character_id.value)
    player_character_api_scope.run_ids.add(run_id.value)
    character_service = _service(mysql_session_factory, binding, character_id)
    await character_service.create(
        principal,
        operation_id=PlayerCharacterOperationId(
            value=f"operation.unsupported-{token}"
        ),
        command=CharacterCreationCommand(
            contract_version=PlayerCharacterContractVersion.V1,
            character_core=CharacterCore(),
            narration_preferences=NarrationPreferences(),
        ),
    )
    run_service = RunService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(mysql_session_factory),
        run_id_issuer=_Issuer(run_id),
        continuous_story_line_id_issuer=_Issuer(line_id),
        source_reference=RunAuthoritySourceRef(
            value="source.mysql-unsupported-binding"
        ),
        clock=lambda: _NOW,
        controller_binding_resolver=_Resolver(binding),
        player_character_binding_evidence=character_service,
    )
    await run_service.create_run(
        operation_id=RunOperationId(value=f"create-unsupported-run-{token}"),
        command=CreateRunCommand(
            source_reference=RunAuthoritySourceRef(
                value="source.mysql-unsupported-binding"
            )
        ),
    )
    await run_service.bind_player_character_internal(
        principal,
        operation_id=RunOperationId(value=f"bind-unsupported-run-{token}"),
        command=BindPlayerCharacterCommand(
            run_id=run_id,
            continuous_story_line_id=line_id,
            target_player_character_id=character_id,
            expected_state_version=RunStateVersion(value=1),
            source_reference=RunAuthoritySourceRef(
                value="source.mysql-unsupported-binding"
            ),
        ),
    )
    async with mysql_session_factory.begin() as session:
        await session.execute(
            sa.update(RunCurrentRow)
            .where(RunCurrentRow.run_id == run_id.value)
            .values(binding_contract_version=unsupported_version)
        )
        await session.execute(
            sa.update(RunRevisionRow)
            .where(
                RunRevisionRow.run_id == run_id.value,
                RunRevisionRow.state_version == 2,
            )
            .values(binding_contract_version=unsupported_version)
        )

    response = await _get(
        _app(character_service, principal),
        "/v1/player-characters/eligible-for-run-entry",
    )

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "Internal server error",
        }
    }
    assert all(
        value not in response.text
        for value in (
            character_id.value,
            binding.value,
            run_id.value,
            line_id.value,
            unsupported_version,
            "1",
            "2",
        )
    )
    assert all(
        detail not in response.text.casefold()
        for detail in (
            "select ",
            "run_current",
            "run_revisions",
            "binding_contract_version",
            "unsupported",
        )
    )


async def test_mysql_eligible_discovery_includes_a_character_after_its_run_binding_is_historical(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    player_character_api_scope: _Scope,
) -> None:
    token = player_character_api_scope.token
    principal = RequestPrincipal(player_id=f"player.historical-{token}", authentication_scheme="test")
    binding = ControllerBindingRef(value=f"binding.historical-{token}")
    character_id = PlayerCharacterId(value=f"pc.historical-{token}")
    run_id = RunId(value=f"run.historical-{token}")
    line_id = ContinuousStoryLineId(value=f"line.historical-{token}")
    player_character_api_scope.bindings.add(binding.value)
    player_character_api_scope.character_ids.add(character_id.value)
    player_character_api_scope.run_ids.add(run_id.value)
    character_service = _service(mysql_session_factory, binding, character_id)
    await character_service.create(
        principal,
        operation_id=PlayerCharacterOperationId(value=f"operation.historical-{token}"),
        command=CharacterCreationCommand(
            contract_version=PlayerCharacterContractVersion.V1,
            character_core=CharacterCore(),
            narration_preferences=NarrationPreferences(),
        ),
    )
    run_service = RunService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(mysql_session_factory),
        run_id_issuer=_Issuer(run_id),
        continuous_story_line_id_issuer=_Issuer(line_id),
        source_reference=RunAuthoritySourceRef(value="source.mysql-historical-run"),
        clock=lambda: _NOW,
        controller_binding_resolver=_Resolver(binding),
        player_character_binding_evidence=character_service,
    )
    await run_service.create_run(
        operation_id=RunOperationId(value=f"create-historical-run-{token}"),
        command=CreateRunCommand(source_reference=RunAuthoritySourceRef(value="source.mysql-historical-run")),
    )
    await run_service.bind_player_character_internal(
        principal,
        operation_id=RunOperationId(value=f"bind-historical-run-{token}"),
        command=BindPlayerCharacterCommand(
            run_id=run_id,
            continuous_story_line_id=line_id,
            target_player_character_id=character_id,
            expected_state_version=RunStateVersion(value=1),
            source_reference=RunAuthoritySourceRef(value="source.mysql-historical-run"),
        ),
    )
    terminal_values = {
        "lifecycle_status": "completed",
        "binding_state": "historical",
        "inactivated_at": _NOW,
    }
    async with mysql_session_factory.begin() as session:
        await session.execute(
            sa.update(RunRevisionRow)
            .where(RunRevisionRow.run_id == run_id.value, RunRevisionRow.state_version == 2)
            .values(**terminal_values)
        )
        await session.execute(
            sa.update(RunCurrentRow)
            .where(RunCurrentRow.run_id == run_id.value)
            .values(**terminal_values, active_player_character_id=None)
        )

    response = await _get(_app(character_service, principal), "/v1/player-characters/eligible-for-run-entry")

    assert response.status_code == 200
    assert response.json() == {
        "eligible_player_characters": [
            {
                "player_character_id": {"value": character_id.value},
                "contract_version": "structured-player-character/v1",
                "record_revision": {"value": 1},
                "lifecycle": "active",
            }
        ],
        "truncated": False,
    }


async def test_mysql_create_replay_conflict_and_durable_owned_read(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    player_character_api_scope: _Scope,
) -> None:
    token = player_character_api_scope.token
    principal = RequestPrincipal(player_id=f"player.api-{token}", authentication_scheme="test")
    binding = ControllerBindingRef(value=f"binding.api-{token}")
    character_id = PlayerCharacterId(value=f"pc.api-{token}")
    player_character_api_scope.bindings.add(binding.value)
    player_character_api_scope.character_ids.add(character_id.value)
    app = _app(_service(mysql_session_factory, binding, character_id), principal)

    created = await _post(app, key=f"create-{token}")
    expected = {
        "player_character_id": {"value": character_id.value},
        "contract_version": "structured-player-character/v1",
        "record_revision": {"value": 1},
        "lifecycle": "active",
    }
    assert created.status_code == 200
    assert created.json() == expected
    assert await _counts(mysql_session_factory, character_id.value, binding.value) == (1, 1, 1, 1, 1, 0)

    replay = await _post(app, key=f"create-{token}")
    assert replay.status_code == 200
    assert replay.json() == expected
    assert await _counts(mysql_session_factory, character_id.value, binding.value) == (1, 1, 1, 1, 1, 0)

    conflict = await _post(
        app,
        key=f"create-{token}",
        body={
            "contract_version": "structured-player-character/v1",
            "character_core": {"name_or_code_name": {"state": "declared", "value": {"authority": "player-expression", "text": "Changed"}}},
            "narration_preferences": {},
        },
    )
    assert conflict.status_code == 409
    assert conflict.json() == {"error": {"error_code": "IDEMPOTENCY_CONFLICT", "message": "Idempotency key was reused"}}
    assert await _counts(mysql_session_factory, character_id.value, binding.value) == (1, 1, 1, 1, 1, 0)

    owned = await _get(app, f"/v1/player-characters/{character_id.value}")
    assert owned.status_code == 200
    assert owned.json() == expected


async def test_mysql_exact_replay_uses_real_uow_without_a_second_commit(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    player_character_api_scope: _Scope,
) -> None:
    token = player_character_api_scope.token
    principal = RequestPrincipal(player_id=f"player.api-{token}", authentication_scheme="test")
    binding = ControllerBindingRef(value=f"binding.api-{token}")
    character_id = PlayerCharacterId(value=f"pc.api-{token}")
    player_character_api_scope.bindings.add(binding.value)
    player_character_api_scope.character_ids.add(character_id.value)
    commits: list[int] = []
    service = _service(mysql_session_factory, binding, character_id)
    service.uow_factory = lambda: _CountingUnitOfWork(mysql_session_factory, commits)
    app = _app(service, principal)
    first = await _post(app, key=f"commit-{token}")
    before = await _counts(mysql_session_factory, character_id.value, binding.value)
    replay = await _post(app, key=f"commit-{token}")
    assert first.status_code == replay.status_code == 200
    assert first.json() == replay.json()
    assert commits == [1]
    assert await _counts(mysql_session_factory, character_id.value, binding.value) == before


async def test_mysql_distinct_creation_keys_allocate_distinct_characters(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    player_character_api_scope: _Scope,
) -> None:
    token = player_character_api_scope.token
    principal = RequestPrincipal(
        player_id=f"player.api-{token}",
        authentication_scheme="test",
    )
    binding = ControllerBindingRef(value=f"binding.api-{token}")
    first_id = PlayerCharacterId(value=f"pc.api-{token}-one")
    second_id = PlayerCharacterId(value=f"pc.api-{token}-two")
    player_character_api_scope.bindings.add(binding.value)
    player_character_api_scope.character_ids.update(
        (first_id.value, second_id.value)
    )

    first = await _post(
        _app(_service(mysql_session_factory, binding, first_id), principal),
        key=f"create-{token}-one",
    )
    second = await _post(
        _app(_service(mysql_session_factory, binding, second_id), principal),
        key=f"create-{token}-two",
    )

    assert first.status_code == second.status_code == 200
    assert first.json()["player_character_id"] == {"value": first_id.value}
    assert second.json()["player_character_id"] == {"value": second_id.value}
    assert first.json() != second.json()
    assert await _counts(
        mysql_session_factory,
        first_id.value,
        binding.value,
    ) == (1, 1, 1, 1, 1, 0)
    assert await _counts(
        mysql_session_factory,
        second_id.value,
        binding.value,
    ) == (1, 1, 1, 1, 1, 0)


async def test_mysql_corrupt_receipt_and_uncertain_commit_are_sanitized(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    player_character_api_scope: _Scope,
) -> None:
    token = player_character_api_scope.token
    principal = RequestPrincipal(player_id=f"player.api-{token}", authentication_scheme="test")
    binding = ControllerBindingRef(value=f"binding.api-{token}")
    character_id = PlayerCharacterId(value=f"pc.api-{token}")
    player_character_api_scope.bindings.add(binding.value)
    player_character_api_scope.character_ids.add(character_id.value)
    app = _app(_service(mysql_session_factory, binding, character_id), principal)
    key = f"corrupt-{token}"
    assert (await _post(app, key=key)).status_code == 200
    async with mysql_session_factory.begin() as session:
        await session.execute(sa.update(PlayerCharacterCreationReceiptRow).where(
            PlayerCharacterCreationReceiptRow.result_player_character_id == character_id.value
        ).values(receipt_canonical=b"x"))
    corrupt = await _post(app, key=key)
    assert corrupt.status_code == 500
    assert corrupt.json() == {"error": {"error_code": "INTERNAL_SERVER_ERROR", "message": "Internal server error"}}
    assert "receipt" not in corrupt.text.casefold()

    uncertain_id = PlayerCharacterId(value=f"pc.api-{token}-uncertain")
    uncertain_binding = ControllerBindingRef(value=f"binding.api-{token}-uncertain")
    player_character_api_scope.character_ids.add(uncertain_id.value)
    player_character_api_scope.bindings.add(uncertain_binding.value)
    uncertain_service = _service(mysql_session_factory, uncertain_binding, uncertain_id)
    uncertain_service.uow_factory = lambda: _UncertainCommitUnitOfWork(mysql_session_factory)
    uncertain = await _post(_app(uncertain_service, principal), key=f"uncertain-{token}")
    assert uncertain.status_code == 500
    assert uncertain.json() == {"error": {"error_code": "INTERNAL_SERVER_ERROR", "message": "Internal server error"}}
    assert await _counts(mysql_session_factory, uncertain_id.value, uncertain_binding.value) == (1, 1, 1, 1, 1, 0)


async def test_mysql_cancellation_propagates_and_rolls_back(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    player_character_api_scope: _Scope,
) -> None:
    token = player_character_api_scope.token
    principal = RequestPrincipal(player_id=f"player.api-{token}", authentication_scheme="test")
    binding = ControllerBindingRef(value=f"binding.api-{token}")
    character_id = PlayerCharacterId(value=f"pc.api-{token}")
    player_character_api_scope.bindings.add(binding.value)
    player_character_api_scope.character_ids.add(character_id.value)
    service = _service(mysql_session_factory, binding, character_id)
    service.uow_factory = lambda: _CancelledCommitUnitOfWork(mysql_session_factory)
    app = _app(service, principal)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        with pytest.raises(asyncio.CancelledError):
            await client.post("/v1/player-characters", headers={"Idempotency-Key": f"cancel-{token}"}, json={"contract_version":"structured-player-character/v1","character_core":{},"narration_preferences":{}})
    assert await _counts(mysql_session_factory, character_id.value, binding.value) == (0, 0, 0, 0, 0, 0)


async def test_mysql_http_binding_add_race_recovers_the_durable_winner(
    mysql_session_factory: async_sessionmaker[AsyncSession], player_character_api_scope: _Scope,
) -> None:
    token = player_character_api_scope.token
    principal = RequestPrincipal(player_id=f"player.api-{token}", authentication_scheme="test")
    binding = ControllerBindingRef(value=f"binding.api-{token}-race")
    first_id = PlayerCharacterId(value=f"pc.api-{token}-race-a")
    second_id = PlayerCharacterId(value=f"pc.api-{token}-race-b")
    player_character_api_scope.bindings.add(binding.value)
    player_character_api_scope.character_ids.update((first_id.value, second_id.value))
    coordinator = _BindingRaceCoordinator()
    uows: list[Any] = []
    def factory(): return _BindingRaceUnitOfWork(mysql_session_factory, coordinator, uows)
    first = _service(mysql_session_factory, binding, first_id); first.uow_factory = factory
    second = _service(mysql_session_factory, binding, second_id); second.uow_factory = factory
    tasks = (asyncio.create_task(_post(_app(first, principal), key=f"race-{token}")), asyncio.create_task(_post(_app(second, principal), key=f"race-{token}")))
    await asyncio.wait_for(coordinator.ready.wait(), timeout=5)
    coordinator.start.set()
    responses = await asyncio.wait_for(asyncio.gather(*tasks), timeout=5)
    assert [response.status_code for response in responses] == [200, 200]
    assert responses[0].json() == responses[1].json()
    winner_id = responses[0].json()["player_character_id"]["value"]
    assert winner_id in {first_id.value, second_id.value}
    assert len(uows) == 3
    winner = first_id if winner_id == first_id.value else second_id
    loser = second_id if winner is first_id else first_id
    assert await _counts(mysql_session_factory, winner.value, binding.value) == (1, 1, 1, 1, 1, 0)
    assert (await _counts(mysql_session_factory, loser.value, binding.value))[1:] == (0, 0, 0, 0, 0)


async def test_mysql_http_binding_recovery_without_winner_is_sanitized(
    mysql_session_factory: async_sessionmaker[AsyncSession], player_character_api_scope: _Scope,
) -> None:
    token = player_character_api_scope.token
    principal = RequestPrincipal(player_id=f"player.api-{token}", authentication_scheme="test")
    binding = ControllerBindingRef(value=f"binding.api-{token}-nowinner")
    character_id = PlayerCharacterId(value=f"pc.api-{token}-nowinner")
    player_character_api_scope.bindings.add(binding.value); player_character_api_scope.character_ids.add(character_id.value)
    uows: list[Any] = []
    service = _service(mysql_session_factory, binding, character_id)
    service.uow_factory = lambda: _NoWinnerUnitOfWork(mysql_session_factory, uows)
    response = await _post(_app(service, principal), key=f"nowinner-{token}")
    assert response.status_code == 404
    assert response.json() == {"error": {"error_code": "PLAYER_CHARACTER_NOT_FOUND", "message": "Player character was not found"}}
    assert len(uows) == 2
    assert await _counts(mysql_session_factory, character_id.value, binding.value) == (0, 0, 0, 0, 0, 0)


async def test_mysql_http_recovery_receipt_failure_is_sanitized_without_retry(
    mysql_session_factory: async_sessionmaker[AsyncSession], player_character_api_scope: _Scope,
) -> None:
    token = player_character_api_scope.token
    principal = RequestPrincipal(player_id=f"player.api-{token}", authentication_scheme="test")
    binding = ControllerBindingRef(value=f"binding.api-{token}-recovery-failure")
    winner_id = PlayerCharacterId(value=f"pc.api-{token}-recovery-winner")
    candidate_id = PlayerCharacterId(value=f"pc.api-{token}-recovery-candidate")
    key = f"recovery-failure-{token}"
    player_character_api_scope.bindings.add(binding.value)
    player_character_api_scope.character_ids.update((winner_id.value, candidate_id.value))

    winner = await _post(_app(_service(mysql_session_factory, binding, winner_id), principal), key=key)
    assert winner.status_code == 200
    assert await _counts(mysql_session_factory, winner_id.value, binding.value) == (1, 1, 1, 1, 1, 0)

    uows: list[Any] = []
    receipt_reads: list[bool] = []
    commits: list[int] = []
    service = _service(mysql_session_factory, binding, candidate_id)
    service.uow_factory = lambda: _RecoveryFailureUnitOfWork(
        mysql_session_factory,
        uows,
        receipt_reads,
        commits,
    )
    failed = await _post(_app(service, principal), key=key)

    assert failed.status_code == 500
    assert failed.json() == {
        "error": {
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "Internal server error",
        }
    }
    assert len(uows) == 2
    assert receipt_reads == [True]
    assert commits == []
    assert "controlled recovery receipt failure" not in failed.text
    assert all(
        value not in failed.text
        for value in (binding.value, winner_id.value, candidate_id.value, key, token)
    )
    assert await _counts(mysql_session_factory, winner_id.value, binding.value) == (1, 1, 1, 1, 1, 0)
    assert (await _counts(mysql_session_factory, candidate_id.value, binding.value))[1:] == (0, 0, 0, 0, 0)


async def test_mysql_creation_scopes_same_key_by_controller_and_rejects_unconfigured_principal(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    player_character_api_scope: _Scope,
) -> None:
    token = player_character_api_scope.token
    key = f"shared-{token}"
    first_id = PlayerCharacterId(value=f"pc.api-{token}-one")
    second_id = PlayerCharacterId(value=f"pc.api-{token}-two")
    first_binding = ControllerBindingRef(value=f"binding.api-{token}-one")
    second_binding = ControllerBindingRef(value=f"binding.api-{token}-two")
    player_character_api_scope.character_ids.update((first_id.value, second_id.value))
    player_character_api_scope.bindings.update((first_binding.value, second_binding.value))
    first_principal = RequestPrincipal(player_id=f"player.api-{token}-one", authentication_scheme="test")
    second_principal = RequestPrincipal(player_id=f"player.api-{token}-two", authentication_scheme="test")
    first_app = _app(_service(mysql_session_factory, first_binding, first_id), first_principal)
    second_app = _app(_service(mysql_session_factory, second_binding, second_id), second_principal)
    assert (await _post(first_app, key=key)).status_code == 200
    assert (await _post(second_app, key=key)).status_code == 200
    assert await _counts(mysql_session_factory, first_id.value, first_binding.value) == (1, 1, 1, 1, 1, 0)
    assert await _counts(mysql_session_factory, second_id.value, second_binding.value) == (1, 1, 1, 1, 1, 0)
    foreign = await _get(second_app, f"/v1/player-characters/{first_id.value}")
    assert foreign.status_code == 404
    assert foreign.json() == {"error": {"error_code": "PLAYER_CHARACTER_NOT_FOUND", "message": "Player character was not found"}}

    unconfigured_service = _service(
        mysql_session_factory,
        first_binding,
        first_id,
    )
    unconfigured_service.controller_binding_resolver = _UnconfiguredResolver()
    uow_calls: list[int] = []
    configured_uow_factory = unconfigured_service.uow_factory

    def recording_uow_factory() -> SqlAlchemyUnitOfWork:
        uow_calls.append(1)
        return configured_uow_factory()  # type: ignore[return-value]

    unconfigured_service.uow_factory = recording_uow_factory
    before_first = await _counts(
        mysql_session_factory,
        first_id.value,
        first_binding.value,
    )
    before_second = await _counts(
        mysql_session_factory,
        second_id.value,
        second_binding.value,
    )
    unconfigured = await _post(
        _app(
            unconfigured_service,
            RequestPrincipal(
                player_id=f"player.api-{token}-unconfigured",
                authentication_scheme="test",
            ),
        ),
        key=key,
    )

    assert unconfigured.status_code == foreign.status_code == 404
    assert unconfigured.json() == foreign.json()
    assert uow_calls == []
    assert await _counts(
        mysql_session_factory,
        first_id.value,
        first_binding.value,
    ) == before_first
    assert await _counts(
        mysql_session_factory,
        second_id.value,
        second_binding.value,
    ) == before_second


async def test_mysql_create_precommit_failure_is_sanitized_and_atomic(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    player_character_api_scope: _Scope,
) -> None:
    token = player_character_api_scope.token
    principal = RequestPrincipal(player_id=f"player.api-{token}", authentication_scheme="test")
    binding = ControllerBindingRef(value=f"binding.api-{token}")
    character_id = PlayerCharacterId(value=f"pc.api-{token}")
    player_character_api_scope.bindings.add(binding.value)
    player_character_api_scope.character_ids.add(character_id.value)
    service = _service(mysql_session_factory, binding, character_id)
    service.uow_factory = lambda: _PreCommitFailureUnitOfWork(mysql_session_factory)
    failed = await _post(_app(service, principal), key=f"failure-{token}")
    assert failed.status_code == 500
    assert failed.json() == {"error": {"error_code": "INTERNAL_SERVER_ERROR", "message": "Internal server error"}}
    assert "controlled" not in failed.text
    assert await _counts(mysql_session_factory, character_id.value, binding.value) == (0, 0, 0, 0, 0, 0)
