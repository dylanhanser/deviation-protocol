from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, AsyncIterator
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.player_character_operations import (
    MUTATION_RESULT_SCHEMA_VERSION,
    CharacterCreationCommand,
    CharacterMutationCommand,
    CharacterOperationNamespace,
    CharacterOperationProtocolCode,
    CharacterOperationProtocolDecision,
    CreationReceiptKey,
    MutationCommandResult,
    MutationReceiptKey,
    MutationSuccessResult,
    StoredMutationSuccessReceipt,
    build_mutation_success_receipt,
    evaluate_mutation_policy,
    mutation_fingerprint,
)
from deviation_protocol.application.player_character_service import (
    PlayerCharacterService,
)
from deviation_protocol.application.ports import (
    ControllerBindingUniquenessConflictError,
)
from deviation_protocol.domain.player_character import (
    ApplicableCharacterReference,
    AuthoritySourceRef,
    CanonicalPlayerCharacter,
    CharacterCore,
    ControllerBindingRef,
    Declaration,
    NarrationPreferences,
    PlayerCharacterContractVersion,
    PlayerCharacterId,
    PlayerCharacterMutationKind,
    PlayerCharacterOperationId,
    PlayerDeclaredText,
    PlayerSubjectiveAuthority,
)
from deviation_protocol.domain.player_character_policies import (
    CreatePlayerCharacterPolicy,
    PlayerConfirmation,
)
from deviation_protocol.infrastructure.errors import (
    PlayerCharacterControllerBindingConflictError,
    PlayerCharacterRepositoryConflictError,
)
from deviation_protocol.infrastructure.orm_models import (
    PlayerCharacterControllerBindingRow,
    PlayerCharacterCreationReceiptRow,
    PlayerCharacterCurrentRow,
    PlayerCharacterIdAllocationRow,
    PlayerCharacterMutationReceiptRow,
    PlayerCharacterRevisionRow,
)
from deviation_protocol.infrastructure.repositories import (
    SqlAlchemyControllerBindingRegistryRepository,
    SqlAlchemyPlayerCharacterCreationReceiptRepository,
    SqlAlchemyPlayerCharacterMutationReceiptRepository,
    SqlAlchemyPlayerCharacterRepository,
)
from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_NOW = datetime(2026, 7, 29, 13, 14, 15, 123456, tzinfo=UTC)
_TIMEOUT = 5.0
_PRINCIPAL = RequestPrincipal(
    player_id="integration.player-character-service",
    authentication_scheme="test",
)


@dataclass(frozen=True, slots=True)
class _CreationInput:
    binding: ControllerBindingRef
    player_character_id: PlayerCharacterId
    operation_id: PlayerCharacterOperationId
    command: CharacterCreationCommand


@dataclass(slots=True)
class _ServiceScope:
    token: str
    character_ids: set[str] = field(default_factory=set)
    bindings: set[str] = field(default_factory=set)

    def creation(
        self,
        suffix: str,
        *,
        binding: ControllerBindingRef | None = None,
        player_character_id: PlayerCharacterId | None = None,
        operation_id: PlayerCharacterOperationId | None = None,
        command: CharacterCreationCommand | None = None,
    ) -> _CreationInput:
        binding = binding or ControllerBindingRef(
            value=f"binding.service-{self.token}-{suffix}"
        )
        player_character_id = player_character_id or PlayerCharacterId(
            value=f"pc.service-{self.token}-{suffix}"
        )
        operation_id = operation_id or PlayerCharacterOperationId(
            value=f"operation.service-{self.token}-{suffix}"
        )
        command = command or CharacterCreationCommand(
            contract_version=PlayerCharacterContractVersion.V1,
            character_core=CharacterCore(),
            narration_preferences=NarrationPreferences(),
        )
        self.bindings.add(binding.value)
        self.character_ids.add(player_character_id.value)
        return _CreationInput(
            binding=binding,
            player_character_id=player_character_id,
            operation_id=operation_id,
            command=command,
        )


@pytest.fixture
async def player_character_service_scope(
    mysql_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[_ServiceScope]:
    scope = _ServiceScope(token=uuid4().hex)
    try:
        yield scope
    finally:
        async with mysql_session_factory.begin() as session:
            if scope.character_ids:
                await session.execute(
                    sa.delete(PlayerCharacterMutationReceiptRow).where(
                        PlayerCharacterMutationReceiptRow.player_character_id.in_(
                            scope.character_ids
                        )
                    )
                )
                await session.execute(
                    sa.delete(PlayerCharacterCreationReceiptRow).where(
                        PlayerCharacterCreationReceiptRow.result_player_character_id.in_(
                            scope.character_ids
                        )
                    )
                )
                await session.execute(
                    sa.delete(PlayerCharacterCurrentRow).where(
                        PlayerCharacterCurrentRow.player_character_id.in_(
                            scope.character_ids
                        )
                    )
                )
                await session.execute(
                    sa.delete(PlayerCharacterRevisionRow).where(
                        PlayerCharacterRevisionRow.player_character_id.in_(
                            scope.character_ids
                        )
                    )
                )
                await session.execute(
                    sa.delete(PlayerCharacterIdAllocationRow).where(
                        PlayerCharacterIdAllocationRow.player_character_id.in_(
                            scope.character_ids
                        )
                    )
                )
            if scope.bindings:
                await session.execute(
                    sa.delete(PlayerCharacterControllerBindingRow).where(
                        PlayerCharacterControllerBindingRow.controller_binding.in_(
                            scope.bindings
                        )
                    )
                )


class _Resolver:
    def __init__(self, binding: ControllerBindingRef) -> None:
        self.binding = binding
        self.calls = 0

    async def resolve(
        self,
        principal: RequestPrincipal,
        /,
    ) -> ControllerBindingRef:
        assert principal == _PRINCIPAL
        self.calls += 1
        return self.binding


class _Issuer:
    def __init__(self, player_character_id: PlayerCharacterId) -> None:
        self.player_character_id = player_character_id
        self.calls = 0

    def issue(self) -> PlayerCharacterId:
        self.calls += 1
        return self.player_character_id


class _FailIfCalledIssuer:
    def issue(self) -> PlayerCharacterId:
        raise AssertionError("exact replay must not issue another identity")


def _service(
    creation: _CreationInput,
    session_factory: async_sessionmaker[AsyncSession],
    *,
    issuer: Any | None = None,
    uow_factory: Any | None = None,
) -> PlayerCharacterService:
    return PlayerCharacterService(
        uow_factory=(
            uow_factory
            or (lambda: SqlAlchemyUnitOfWork(session_factory))
        ),
        controller_binding_resolver=_Resolver(creation.binding),
        player_character_id_issuer=issuer or _Issuer(
            creation.player_character_id
        ),
        create_policy=CreatePlayerCharacterPolicy(),
        source_reference=AuthoritySourceRef(
            value=f"source.service-{creation.player_character_id.value}"
        ),
        clock=lambda: _NOW,
    )


async def _family_counts(
    session_factory: async_sessionmaker[AsyncSession],
    creation: _CreationInput,
) -> tuple[int, int, int, int, int, int]:
    predicates = (
        (
            PlayerCharacterControllerBindingRow,
            PlayerCharacterControllerBindingRow.controller_binding
            == creation.binding.value,
        ),
        (
            PlayerCharacterIdAllocationRow,
            PlayerCharacterIdAllocationRow.player_character_id
            == creation.player_character_id.value,
        ),
        (
            PlayerCharacterRevisionRow,
            PlayerCharacterRevisionRow.player_character_id
            == creation.player_character_id.value,
        ),
        (
            PlayerCharacterCurrentRow,
            PlayerCharacterCurrentRow.player_character_id
            == creation.player_character_id.value,
        ),
        (
            PlayerCharacterCreationReceiptRow,
            PlayerCharacterCreationReceiptRow.result_player_character_id
            == creation.player_character_id.value,
        ),
        (
            PlayerCharacterMutationReceiptRow,
            PlayerCharacterMutationReceiptRow.player_character_id
            == creation.player_character_id.value,
        ),
    )
    async with session_factory() as session:
        counts: list[int] = []
        for row_type, predicate in predicates:
            counts.append(
                int(
                    await session.scalar(
                        sa.select(sa.func.count())
                        .select_from(row_type)
                        .where(predicate)
                    )
                    or 0
                )
            )
        return tuple(counts)  # type: ignore[return-value]


def _changed_command() -> CharacterCreationCommand:
    return CharacterCreationCommand(
        contract_version=PlayerCharacterContractVersion.V1,
        character_core=CharacterCore(
            name_or_code_name=Declaration[PlayerDeclaredText].declared(
                PlayerDeclaredText(
                    authority=PlayerSubjectiveAuthority.PLAYER_EXPRESSION,
                    text="Changed integration command",
                )
            )
        ),
        narration_preferences=NarrationPreferences(),
    )


@pytest.mark.usefixtures("player_character_service_scope")
async def test_mysql_service_creation_reload_replay_and_changed_payload(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    player_character_service_scope: _ServiceScope,
) -> None:
    creation = player_character_service_scope.creation("normal")
    issuer = _Issuer(creation.player_character_id)
    service = _service(
        creation,
        mysql_session_factory,
        issuer=issuer,
    )

    created = await service.create(
        _PRINCIPAL,
        operation_id=creation.operation_id,
        command=creation.command,
    )
    assert not isinstance(created, CharacterOperationProtocolDecision)
    assert created.player_character_id == creation.player_character_id
    assert issuer.calls == 1
    assert await _family_counts(
        mysql_session_factory,
        creation,
    ) == (1, 1, 1, 1, 1, 0)

    receipt_key = _receipt_key(creation)
    async with mysql_session_factory() as session:
        record = await SqlAlchemyPlayerCharacterRepository(session).get(
            creation.player_character_id
        )
        receipt = await SqlAlchemyPlayerCharacterCreationReceiptRepository(
            session
        ).get(receipt_key)
    assert record is not None
    assert record.player_character_id == creation.player_character_id
    assert receipt is not None
    assert receipt.result == created

    replay = await _service(
        creation,
        mysql_session_factory,
        issuer=_FailIfCalledIssuer(),
    ).create(
        _PRINCIPAL,
        operation_id=creation.operation_id,
        command=creation.command,
    )
    assert replay == created
    assert await _family_counts(
        mysql_session_factory,
        creation,
    ) == (1, 1, 1, 1, 1, 0)

    conflict = await _service(
        creation,
        mysql_session_factory,
        issuer=_FailIfCalledIssuer(),
    ).create(
        _PRINCIPAL,
        operation_id=creation.operation_id,
        command=_changed_command(),
    )
    assert isinstance(conflict, CharacterOperationProtocolDecision)
    assert (
        conflict.code is CharacterOperationProtocolCode.IDEMPOTENCY_CONFLICT
    )
    assert conflict.stored_success_result is None
    assert await _family_counts(
        mysql_session_factory,
        creation,
    ) == (1, 1, 1, 1, 1, 0)


def _receipt_key(
    creation: _CreationInput,
) -> CreationReceiptKey:
    return CreationReceiptKey(
        controller_binding=creation.binding,
        operation_namespace=CharacterOperationNamespace.CREATE_V1,
        operation_id=creation.operation_id,
    )


class _PreCommitFailureUnitOfWork(SqlAlchemyUnitOfWork):
    async def commit(self) -> None:
        raise RuntimeError("controlled pre-COMMIT service failure")


async def test_mysql_service_pre_commit_failure_rolls_back_before_fresh_success(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    player_character_service_scope: _ServiceScope,
) -> None:
    creation = player_character_service_scope.creation("pre-commit")

    with pytest.raises(
        RuntimeError,
        match="controlled pre-COMMIT service failure",
    ):
        await _service(
            creation,
            mysql_session_factory,
            uow_factory=lambda: _PreCommitFailureUnitOfWork(
                mysql_session_factory
            ),
        ).create(
            _PRINCIPAL,
            operation_id=creation.operation_id,
            command=creation.command,
        )

    assert await _family_counts(
        mysql_session_factory,
        creation,
    ) == (0, 0, 0, 0, 0, 0)

    created = await _service(
        creation,
        mysql_session_factory,
    ).create(
        _PRINCIPAL,
        operation_id=creation.operation_id,
        command=creation.command,
    )
    assert not isinstance(created, CharacterOperationProtocolDecision)
    assert await _family_counts(
        mysql_session_factory,
        creation,
    ) == (1, 1, 1, 1, 1, 0)


def _retirement(
    record: CanonicalPlayerCharacter,
    *,
    label: str,
) -> tuple[CanonicalPlayerCharacter, StoredMutationSuccessReceipt]:
    operation_id = PlayerCharacterOperationId(
        value=f"operation.retire-{label}"
    )
    command = CharacterMutationCommand(
        contract_version=record.contract_version,
        command_kind=PlayerCharacterMutationKind.RETIRE,
        target_player_character_id=record.player_character_id,
        expected_revision=record.record_revision,
        applicable_reference=ApplicableCharacterReference(
            player_character_id=record.player_character_id,
            contract_version=record.contract_version,
            record_revision=record.record_revision,
        ),
        confirmation=PlayerConfirmation(
            player_character_id=record.player_character_id,
            expected_revision=record.record_revision,
            operation_id=operation_id,
            mutation_kind=PlayerCharacterMutationKind.RETIRE,
            source_reference=AuthoritySourceRef(
                value=f"source.retire-{label}"
            ),
        ),
    )
    decision = evaluate_mutation_policy(
        record,
        command=command,
        operation_id=operation_id,
    )
    assert decision.resulting_record is not None
    successor = decision.resulting_record
    _, fingerprint = mutation_fingerprint(
        command,
        operation_id=operation_id,
    )
    receipt = build_mutation_success_receipt(
        key=MutationReceiptKey(
            player_character_id=record.player_character_id,
            operation_namespace=CharacterOperationNamespace.MUTATE_V1,
            operation_id=operation_id,
        ),
        fingerprint=fingerprint,
        result=MutationSuccessResult(
            result_schema_version=MUTATION_RESULT_SCHEMA_VERSION,
            player_character_id=record.player_character_id,
            contract_version=record.contract_version,
            command_kind=PlayerCharacterMutationKind.RETIRE,
            command_result=MutationCommandResult.RETIRED,
            resulting_revision=successor.record_revision,
            resulting_lifecycle=successor.lifecycle,
        ),
    )
    return successor, receipt


def _assert_shared_not_narrow(error: BaseException) -> None:
    assert type(error) is PlayerCharacterRepositoryConflictError
    assert not isinstance(
        error,
        ControllerBindingUniquenessConflictError,
    )


async def test_mysql_only_controller_binding_duplicate_is_narrow(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    player_character_service_scope: _ServiceScope,
) -> None:
    creation = player_character_service_scope.creation("conflicts")
    created = await _service(
        creation,
        mysql_session_factory,
    ).create(
        _PRINCIPAL,
        operation_id=creation.operation_id,
        command=creation.command,
    )
    assert not isinstance(created, CharacterOperationProtocolDecision)

    async with mysql_session_factory() as session:
        with pytest.raises(
            PlayerCharacterControllerBindingConflictError
        ) as binding_exc:
            await SqlAlchemyControllerBindingRegistryRepository(session).add(
                creation.binding,
                created_at=_NOW,
            )
        await session.rollback()
    assert type(binding_exc.value) is (
        PlayerCharacterControllerBindingConflictError
    )
    assert isinstance(
        binding_exc.value,
        ControllerBindingUniquenessConflictError,
    )
    assert isinstance(
        binding_exc.value,
        PlayerCharacterRepositoryConflictError,
    )

    async with mysql_session_factory() as session:
        with pytest.raises(PlayerCharacterRepositoryConflictError) as exc:
            await SqlAlchemyPlayerCharacterRepository(
                session
            ).add_allocation(
                creation.player_character_id,
                created_at=_NOW,
            )
        _assert_shared_not_narrow(exc.value)
        await session.rollback()

    async with mysql_session_factory() as session:
        record = await SqlAlchemyPlayerCharacterRepository(session).get(
            creation.player_character_id
        )
        assert record is not None
        with pytest.raises(PlayerCharacterRepositoryConflictError) as exc:
            await SqlAlchemyPlayerCharacterRepository(session).add_initial(
                record,
                created_at=_NOW,
            )
        _assert_shared_not_narrow(exc.value)
        await session.rollback()

    async with mysql_session_factory() as session:
        receipt = await SqlAlchemyPlayerCharacterCreationReceiptRepository(
            session
        ).get(_receipt_key(creation))
        assert receipt is not None
        with pytest.raises(PlayerCharacterRepositoryConflictError) as exc:
            await SqlAlchemyPlayerCharacterCreationReceiptRepository(
                session
            ).add(
                receipt,
                created_at=_NOW,
            )
        _assert_shared_not_narrow(exc.value)
        await session.rollback()

    async with mysql_session_factory() as session:
        repository = SqlAlchemyPlayerCharacterRepository(session)
        record = await repository.get_for_update(
            creation.player_character_id
        )
        assert record is not None
        successor, mutation_receipt = _retirement(
            record,
            label=f"{player_character_service_scope.token}-conflicts",
        )
        await repository.append_revision(successor, created_at=_NOW)
        assert await repository.compare_and_swap_current(
            successor,
            expected_revision=record.record_revision.value,
            created_at=_NOW,
        )
        await SqlAlchemyPlayerCharacterMutationReceiptRepository(
            session
        ).add(
            mutation_receipt,
            created_at=_NOW,
        )
        await session.commit()

    async with mysql_session_factory() as session:
        with pytest.raises(PlayerCharacterRepositoryConflictError) as exc:
            await SqlAlchemyPlayerCharacterMutationReceiptRepository(
                session
            ).add(
                mutation_receipt,
                created_at=_NOW,
            )
        _assert_shared_not_narrow(exc.value)
        await session.rollback()

    async with mysql_session_factory() as session:
        with pytest.raises(PlayerCharacterRepositoryConflictError) as exc:
            await SqlAlchemyPlayerCharacterRepository(
                session
            ).append_revision(
                successor,
                created_at=_NOW,
            )
        _assert_shared_not_narrow(exc.value)
        await session.rollback()

    missing = player_character_service_scope.creation("missing-current")
    local_initial = CreatePlayerCharacterPolicy().create(
        player_character_id=missing.player_character_id,
        controller_binding=missing.binding,
        character_core=missing.command.character_core,
        narration_preferences=missing.command.narration_preferences,
        source_reference=AuthoritySourceRef(value="source.missing-current"),
    )
    missing_successor, _ = _retirement(
        local_initial,
        label=f"{player_character_service_scope.token}-missing",
    )
    async with mysql_session_factory() as session:
        with pytest.raises(PlayerCharacterRepositoryConflictError) as exc:
            await SqlAlchemyPlayerCharacterRepository(
                session
            ).append_revision(
                missing_successor,
                created_at=_NOW,
            )
        _assert_shared_not_narrow(exc.value)
        await session.rollback()

    async with mysql_session_factory() as session:
        current = await SqlAlchemyPlayerCharacterRepository(
            session
        ).get(creation.player_character_id)
        assert current == successor
        assert not await SqlAlchemyPlayerCharacterRepository(
            session
        ).compare_and_swap_current(
            successor,
            expected_revision=record.record_revision.value,
            created_at=_NOW,
        )


@dataclass(slots=True)
class _RaceCoordinator:
    ready: asyncio.Event = field(default_factory=asyncio.Event)
    start: asyncio.Event = field(default_factory=asyncio.Event)
    arrivals: int = 0


class _RaceBindingRepository:
    def __init__(
        self,
        repository: SqlAlchemyControllerBindingRegistryRepository,
        coordinator: _RaceCoordinator,
    ) -> None:
        self._repository = repository
        self._coordinator = coordinator

    async def lock(
        self,
        controller_binding: ControllerBindingRef,
    ) -> ControllerBindingRef | None:
        result = await self._repository.lock(controller_binding)
        if result is None and self._coordinator.arrivals < 2:
            self._coordinator.arrivals += 1
            if self._coordinator.arrivals == 2:
                self._coordinator.ready.set()
            await asyncio.wait_for(
                self._coordinator.start.wait(),
                timeout=_TIMEOUT,
            )
        return result

    async def add(
        self,
        controller_binding: ControllerBindingRef,
        *,
        created_at: datetime,
    ) -> None:
        await self._repository.add(
            controller_binding,
            created_at=created_at,
        )


class _RaceUnitOfWork(SqlAlchemyUnitOfWork):
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        coordinator: _RaceCoordinator,
        created: list[_RaceUnitOfWork],
    ) -> None:
        super().__init__(session_factory)
        self.coordinator = coordinator
        self.created = created
        self.exited = False
        self.created.append(self)

    async def __aenter__(self) -> _RaceUnitOfWork:
        await super().__aenter__()
        assert self._session is not None
        await self._session.connection(
            execution_options={"isolation_level": "READ COMMITTED"}
        )
        self.controller_bindings = _RaceBindingRepository(
            self.controller_bindings,
            self.coordinator,
        )  # type: ignore[assignment]
        return self

    async def __aexit__(self, *args: Any) -> None:
        try:
            await super().__aexit__(*args)
        finally:
            self.exited = True


async def test_mysql_real_binding_race_service_recovers_in_one_fresh_uow(
    mysql_session_factory: async_sessionmaker[AsyncSession],
    player_character_service_scope: _ServiceScope,
) -> None:
    shared_binding = ControllerBindingRef(
        value=(
            f"binding.service-{player_character_service_scope.token}-race"
        )
    )
    shared_operation = PlayerCharacterOperationId(
        value=(
            f"operation.service-{player_character_service_scope.token}-race"
        )
    )
    command = CharacterCreationCommand(
        contract_version=PlayerCharacterContractVersion.V1,
        character_core=CharacterCore(),
        narration_preferences=NarrationPreferences(),
    )
    first = player_character_service_scope.creation(
        "race-a",
        binding=shared_binding,
        operation_id=shared_operation,
        command=command,
    )
    second = player_character_service_scope.creation(
        "race-b",
        binding=shared_binding,
        operation_id=shared_operation,
        command=command,
    )
    coordinator = _RaceCoordinator()
    created_uows: list[_RaceUnitOfWork] = []
    first_issuer = _Issuer(first.player_character_id)
    second_issuer = _Issuer(second.player_character_id)

    def race_uow_factory() -> _RaceUnitOfWork:
        return _RaceUnitOfWork(
            mysql_session_factory,
            coordinator,
            created_uows,
        )

    tasks = (
        asyncio.create_task(
            _service(
                first,
                mysql_session_factory,
                issuer=first_issuer,
                uow_factory=race_uow_factory,
            ).create(
                _PRINCIPAL,
                operation_id=shared_operation,
                command=command,
            )
        ),
        asyncio.create_task(
            _service(
                second,
                mysql_session_factory,
                issuer=second_issuer,
                uow_factory=race_uow_factory,
            ).create(
                _PRINCIPAL,
                operation_id=shared_operation,
                command=command,
            )
        ),
    )
    try:
        await asyncio.wait_for(coordinator.ready.wait(), timeout=_TIMEOUT)
        coordinator.start.set()
        results = await asyncio.wait_for(
            asyncio.gather(*tasks),
            timeout=_TIMEOUT,
        )
    finally:
        coordinator.start.set()
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    assert results[0] == results[1]
    assert not isinstance(results[0], CharacterOperationProtocolDecision)
    assert sorted((first_issuer.calls, second_issuer.calls)) == [0, 1]
    assert len(created_uows) == 3
    assert all(uow.exited for uow in created_uows)
    winner = first if first_issuer.calls else second
    loser = second if winner is first else first
    assert await _family_counts(
        mysql_session_factory,
        winner,
    ) == (1, 1, 1, 1, 1, 0)
    assert (
        await _family_counts(mysql_session_factory, loser)
    )[1:] == (0, 0, 0, 0, 0)
