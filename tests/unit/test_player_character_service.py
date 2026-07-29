from __future__ import annotations

import ast
import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

import deviation_protocol.application.player_character_service as service_module
from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.player_character_operations import (
    CREATION_RESULT_SCHEMA_VERSION,
    MUTATION_RESULT_SCHEMA_VERSION,
    CharacterCreationCommand,
    CharacterMutationCommand,
    CharacterOperationNamespace,
    CharacterOperationProtocolCode,
    CharacterOperationProtocolDecision,
    CreationReceiptKey,
    CreationSuccessResult,
    MutationCommandResult,
    MutationReceiptKey,
    MutationSuccessResult,
    StoredCreationSuccessReceipt,
    StoredMutationSuccessReceipt,
    build_creation_success_receipt,
    build_mutation_success_receipt,
    creation_fingerprint,
    evaluate_mutation_policy,
    mutation_fingerprint,
)
from deviation_protocol.application.player_character_service import (
    PlayerCharacterService,
)
from deviation_protocol.application.ports import (
    ControllerBindingUniquenessConflictError,
    MutationReceiptUniquenessConflictError,
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
    PlayerCharacterRevision,
    PlayerDeclaredText,
    PlayerSubjectiveAuthority,
    revalidate_player_character_model,
)
from deviation_protocol.domain.player_character_policies import (
    CreatePlayerCharacterPolicy,
    PlayerCharacterPolicyCode,
    PlayerCharacterPolicyDecision,
    PlayerConfirmation,
)
from deviation_protocol.infrastructure.errors import (
    PlayerCharacterControllerBindingConflictError,
    PlayerCharacterMutationReceiptConflictError,
    PlayerCharacterRepositoryConflictError,
    PlayerCharacterRepositoryError,
)
from deviation_protocol.infrastructure.orm_models import (
    PlayerCharacterControllerBindingRow,
    PlayerCharacterIdAllocationRow,
)
from deviation_protocol.infrastructure.repositories import (
    SqlAlchemyControllerBindingRegistryRepository,
    SqlAlchemyPlayerCharacterRepository,
)


_NOW = datetime(2026, 7, 29, 10, 11, 12, 123456, tzinfo=UTC)
_PRINCIPAL = RequestPrincipal(
    player_id="player.service",
    authentication_scheme="test",
)


@dataclass(frozen=True, slots=True)
class _CreationFixture:
    binding: ControllerBindingRef
    player_character_id: PlayerCharacterId
    operation_id: PlayerCharacterOperationId
    command: CharacterCreationCommand
    record: CanonicalPlayerCharacter
    receipt: StoredCreationSuccessReceipt


@dataclass(frozen=True, slots=True)
class _MutationFixture:
    binding: ControllerBindingRef
    operation_id: PlayerCharacterOperationId
    command: CharacterMutationCommand
    current: CanonicalPlayerCharacter
    successor: CanonicalPlayerCharacter
    receipt: StoredMutationSuccessReceipt


def _creation_fixture(label: str = "default") -> _CreationFixture:
    binding = ControllerBindingRef(value=f"binding.service-{label}")
    player_character_id = PlayerCharacterId(value=f"pc.service-{label}")
    operation_id = PlayerCharacterOperationId(
        value=f"operation.service-{label}"
    )
    command = CharacterCreationCommand(
        contract_version=PlayerCharacterContractVersion.V1,
        character_core=CharacterCore(),
        narration_preferences=NarrationPreferences(),
    )
    record = CreatePlayerCharacterPolicy().create(
        player_character_id=player_character_id,
        controller_binding=binding,
        character_core=command.character_core,
        narration_preferences=command.narration_preferences,
        source_reference=AuthoritySourceRef(value="source.service-create"),
    )
    _, fingerprint = creation_fingerprint(command)
    result = CreationSuccessResult(
        result_schema_version=CREATION_RESULT_SCHEMA_VERSION,
        player_character_id=record.player_character_id,
        contract_version=record.contract_version,
        resulting_revision=record.record_revision,
        resulting_lifecycle=record.lifecycle,
    )
    receipt = build_creation_success_receipt(
        key=CreationReceiptKey(
            controller_binding=binding,
            operation_namespace=CharacterOperationNamespace.CREATE_V1,
            operation_id=operation_id,
        ),
        fingerprint=fingerprint,
        result=result,
    )
    return _CreationFixture(
        binding=binding,
        player_character_id=player_character_id,
        operation_id=operation_id,
        command=command,
        record=record,
        receipt=receipt,
    )


def _mutation_fixture(label: str = "default") -> _MutationFixture:
    created = _creation_fixture(f"mutation-{label}")
    operation_id = PlayerCharacterOperationId(
        value=f"operation.mutation-{label}"
    )
    command = CharacterMutationCommand(
        contract_version=PlayerCharacterContractVersion.V1,
        command_kind=PlayerCharacterMutationKind.RETIRE,
        target_player_character_id=created.player_character_id,
        expected_revision=created.record.record_revision,
        applicable_reference=ApplicableCharacterReference(
            player_character_id=created.player_character_id,
            contract_version=created.record.contract_version,
            record_revision=created.record.record_revision,
        ),
        confirmation=PlayerConfirmation(
            player_character_id=created.player_character_id,
            expected_revision=created.record.record_revision,
            operation_id=operation_id,
            mutation_kind=PlayerCharacterMutationKind.RETIRE,
            source_reference=AuthoritySourceRef(
                value=f"source.mutation-{label}"
            ),
        ),
    )
    policy_decision = evaluate_mutation_policy(
        created.record,
        command=command,
        operation_id=operation_id,
    )
    assert policy_decision.accepted
    successor = policy_decision.resulting_record
    assert successor is not None
    _, fingerprint = mutation_fingerprint(
        command,
        operation_id=operation_id,
    )
    result = MutationSuccessResult(
        result_schema_version=MUTATION_RESULT_SCHEMA_VERSION,
        player_character_id=successor.player_character_id,
        contract_version=successor.contract_version,
        command_kind=command.command_kind,
        command_result=MutationCommandResult.RETIRED,
        resulting_revision=successor.record_revision,
        resulting_lifecycle=successor.lifecycle,
    )
    receipt = build_mutation_success_receipt(
        key=MutationReceiptKey(
            player_character_id=successor.player_character_id,
            operation_namespace=CharacterOperationNamespace.MUTATE_V1,
            operation_id=operation_id,
        ),
        fingerprint=fingerprint,
        result=result,
    )
    return _MutationFixture(
        binding=created.binding,
        operation_id=operation_id,
        command=command,
        current=created.record,
        successor=successor,
        receipt=receipt,
    )


def _changed_mutation_command(
    fixture: _MutationFixture,
) -> CharacterMutationCommand:
    return fixture.command.model_copy(
        update={
            "confirmation": fixture.command.confirmation.model_copy(
                update={
                    "source_reference": AuthoritySourceRef(
                        value="source.mutation-changed"
                    )
                }
            )
        }
    )


def _changed_command() -> CharacterCreationCommand:
    return CharacterCreationCommand(
        contract_version=PlayerCharacterContractVersion.V1,
        character_core=CharacterCore(
            name_or_code_name=Declaration[PlayerDeclaredText].declared(
                PlayerDeclaredText(
                    authority=PlayerSubjectiveAuthority.PLAYER_EXPRESSION,
                    text="Changed",
                )
            )
        ),
        narration_preferences=NarrationPreferences(),
    )


class _Resolver:
    def __init__(self, values: list[Any], events: list[str]) -> None:
        self._values = values
        self.events = events
        self.calls = 0

    async def resolve(self, principal: RequestPrincipal, /) -> Any:
        assert principal is _PRINCIPAL
        self.calls += 1
        self.events.append(f"resolve:{self.calls}")
        value = self._values[self.calls - 1]
        if isinstance(value, BaseException):
            raise value
        return value


class _Issuer:
    def __init__(
        self,
        value: Any,
        events: list[str],
    ) -> None:
        self.value = value
        self.events = events
        self.calls = 0

    def issue(self) -> Any:
        self.calls += 1
        self.events.append("issue")
        if isinstance(self.value, BaseException):
            raise self.value
        return self.value


class _Policy(CreatePlayerCharacterPolicy):
    def __init__(
        self,
        events: list[str],
        *,
        error: BaseException | None = None,
    ) -> None:
        self.events = events
        self.error = error
        self.calls = 0

    def create(self, **kwargs: Any) -> CanonicalPlayerCharacter:
        self.calls += 1
        self.events.append("policy")
        if self.error is not None:
            raise self.error
        return super().create(**kwargs)


class _BindingRepository:
    def __init__(
        self,
        *,
        name: str,
        events: list[str],
        binding: ControllerBindingRef,
        lock_result: Any,
        add_error: BaseException | None = None,
        before_add_error: Callable[[], None] | None = None,
    ) -> None:
        self.name = name
        self.events = events
        self.binding = binding
        self.lock_result = lock_result
        self.add_error = add_error
        self.before_add_error = before_add_error
        self.lock_calls = 0
        self.add_calls = 0

    async def lock(
        self,
        controller_binding: ControllerBindingRef,
    ) -> Any:
        assert controller_binding == self.binding
        self.lock_calls += 1
        self.events.append(f"{self.name}:binding-lock")
        if isinstance(self.lock_result, BaseException):
            raise self.lock_result
        return self.lock_result

    async def add(
        self,
        controller_binding: ControllerBindingRef,
        *,
        created_at: datetime,
    ) -> None:
        assert controller_binding == self.binding
        assert created_at == _NOW
        self.add_calls += 1
        self.events.append(f"{self.name}:binding-add")
        if self.add_error is not None:
            if self.before_add_error is not None:
                self.before_add_error()
            raise self.add_error


class _PlayerCharacterRepository:
    def __init__(
        self,
        *,
        name: str,
        events: list[str],
        allocation_error: BaseException | None = None,
        initial_error: BaseException | None = None,
        current: Any = None,
        append_error: BaseException | None = None,
        cas_result: Any = True,
    ) -> None:
        self.name = name
        self.events = events
        self.allocation_error = allocation_error
        self.initial_error = initial_error
        self.current = current
        self.append_error = append_error
        self.cas_result = cas_result
        self.allocation_calls = 0
        self.initial_calls = 0
        self.lock_calls = 0
        self.append_calls = 0
        self.cas_calls = 0
        self.record: CanonicalPlayerCharacter | None = None
        self.appended: CanonicalPlayerCharacter | None = None
        self.swapped: CanonicalPlayerCharacter | None = None

    async def get_for_update(
        self,
        player_character_id: PlayerCharacterId,
    ) -> Any:
        self.lock_calls += 1
        self.events.append(f"{self.name}:character-lock")
        if isinstance(self.current, BaseException):
            raise self.current
        if self.current is not None:
            assert self.current.player_character_id == player_character_id
        return self.current

    async def add_allocation(
        self,
        player_character_id: PlayerCharacterId,
        *,
        created_at: datetime,
    ) -> None:
        assert created_at == _NOW
        self.allocation_calls += 1
        self.events.append(f"{self.name}:allocation")
        if self.allocation_error is not None:
            raise self.allocation_error

    async def add_initial(
        self,
        record: CanonicalPlayerCharacter,
        *,
        created_at: datetime,
    ) -> None:
        assert created_at == _NOW
        self.initial_calls += 1
        self.events.append(f"{self.name}:initial")
        if self.initial_error is not None:
            raise self.initial_error
        self.record = record

    async def append_revision(
        self,
        record: CanonicalPlayerCharacter,
        *,
        created_at: datetime,
    ) -> None:
        assert created_at == _NOW
        self.append_calls += 1
        self.events.append(f"{self.name}:history-append")
        if self.append_error is not None:
            raise self.append_error
        self.appended = record

    async def compare_and_swap_current(
        self,
        record: CanonicalPlayerCharacter,
        *,
        expected_revision: int,
        created_at: datetime,
    ) -> bool:
        assert created_at == _NOW
        assert expected_revision == record.record_revision.value - 1
        self.cas_calls += 1
        self.events.append(f"{self.name}:current-cas")
        if isinstance(self.cas_result, BaseException):
            raise self.cas_result
        if self.cas_result:
            self.swapped = record
        return self.cas_result


class _CreationReceiptRepository:
    def __init__(
        self,
        *,
        name: str,
        events: list[str],
        stored: StoredCreationSuccessReceipt | None = None,
        get_error: BaseException | None = None,
        add_error: BaseException | None = None,
    ) -> None:
        self.name = name
        self.events = events
        self.stored = stored
        self.get_error = get_error
        self.add_error = add_error
        self.lookups: list[CreationReceiptKey] = []
        self.add_calls = 0
        self.added: StoredCreationSuccessReceipt | None = None

    async def get(
        self,
        key: CreationReceiptKey,
    ) -> StoredCreationSuccessReceipt | None:
        self.lookups.append(key)
        self.events.append(f"{self.name}:receipt-get")
        if self.get_error is not None:
            raise self.get_error
        return self.stored

    async def add(
        self,
        receipt: StoredCreationSuccessReceipt,
        *,
        created_at: datetime,
    ) -> None:
        assert created_at == _NOW
        self.add_calls += 1
        self.events.append(f"{self.name}:receipt-add")
        if self.add_error is not None:
            raise self.add_error
        self.added = receipt


class _MutationReceiptRepository:
    def __init__(
        self,
        *,
        name: str,
        events: list[str],
        stored: StoredMutationSuccessReceipt | None = None,
        get_error: BaseException | None = None,
        add_error: BaseException | None = None,
    ) -> None:
        self.name = name
        self.events = events
        self.stored = stored
        self.get_error = get_error
        self.add_error = add_error
        self.lookups: list[MutationReceiptKey] = []
        self.add_calls = 0
        self.added: StoredMutationSuccessReceipt | None = None

    async def get(
        self,
        key: MutationReceiptKey,
    ) -> StoredMutationSuccessReceipt | None:
        self.lookups.append(key)
        self.events.append(f"{self.name}:mutation-receipt-get")
        if self.get_error is not None:
            raise self.get_error
        return self.stored

    async def add(
        self,
        receipt: StoredMutationSuccessReceipt,
        *,
        created_at: datetime,
    ) -> None:
        assert created_at == _NOW
        self.add_calls += 1
        self.events.append(f"{self.name}:mutation-receipt-add")
        if self.add_error is not None:
            raise self.add_error
        self.added = receipt


class _Uow:
    def __init__(
        self,
        *,
        name: str,
        events: list[str],
        controller_bindings: _BindingRepository,
        player_characters: _PlayerCharacterRepository | None = None,
        creation_receipts: _CreationReceiptRepository | None = None,
        mutation_receipts: _MutationReceiptRepository | None = None,
        enter_error: BaseException | None = None,
        exit_error: BaseException | None = None,
        suppress_exit_exception: bool = False,
        commit_error: BaseException | None = None,
    ) -> None:
        self.name = name
        self.events = events
        self.controller_bindings = controller_bindings
        self.player_characters = player_characters or (
            _PlayerCharacterRepository(name=name, events=events)
        )
        self.creation_receipts = creation_receipts or (
            _CreationReceiptRepository(name=name, events=events)
        )
        self.mutation_receipts = mutation_receipts or (
            _MutationReceiptRepository(name=name, events=events)
        )
        self.enter_error = enter_error
        self.exit_error = exit_error
        self.suppress_exit_exception = suppress_exit_exception
        self.commit_error = commit_error
        self.entered = False
        self.exited = False
        self.exit_exception: BaseException | None = None
        self.rolled_back = False
        self.closed = False
        self.committed = False
        self.commit_calls = 0

    async def __aenter__(self) -> _Uow:
        self.events.append(f"{self.name}:enter")
        if self.enter_error is not None:
            raise self.enter_error
        self.entered = True
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: Any,
    ) -> bool | None:
        self.exit_exception = exc
        self.events.append(
            f"{self.name}:exit:{exc_type.__name__ if exc_type else 'none'}"
        )
        if exc_type is not None or not self.committed:
            self.rolled_back = True
            self.events.append(f"{self.name}:rollback")
        self.closed = True
        self.events.append(f"{self.name}:close")
        self.exited = True
        self.events.append(f"{self.name}:exit-complete")
        if self.exit_error is not None:
            raise self.exit_error
        if self.suppress_exit_exception:
            assert exc is not None
            return True
        return None

    async def commit(self) -> None:
        self.commit_calls += 1
        self.events.append(f"{self.name}:commit")
        if self.commit_error is not None:
            raise self.commit_error
        self.committed = True


class _UowFactory:
    def __init__(self, uows: list[_Uow], events: list[str]) -> None:
        self.uows = uows
        self.events = events
        self.calls = 0

    def __call__(self) -> _Uow:
        if self.calls >= len(self.uows):
            raise AssertionError("an unauthorized extra UnitOfWork was created")
        if self.calls:
            assert self.uows[self.calls - 1].exited
            assert self.uows[self.calls - 1].rolled_back
            assert self.uows[self.calls - 1].closed
        uow = self.uows[self.calls]
        self.calls += 1
        self.events.append(f"factory:{uow.name}")
        return uow


def _service(
    *,
    factory: _UowFactory,
    resolver: _Resolver,
    issuer: _Issuer,
    policy: _Policy,
    clock: Callable[[], datetime] | None = None,
) -> PlayerCharacterService:
    return PlayerCharacterService(
        uow_factory=factory,
        controller_binding_resolver=resolver,
        player_character_id_issuer=issuer,
        create_policy=policy,
        source_reference=AuthoritySourceRef(value="source.service-create"),
        clock=clock or (lambda: _NOW),
    )


def _uow(
    fixture: _CreationFixture,
    events: list[str],
    *,
    name: str = "initial",
    lock_result: Any = None,
    binding_add_error: BaseException | None = None,
    before_add_error: Callable[[], None] | None = None,
    stored_receipt: StoredCreationSuccessReceipt | None = None,
    receipt_get_error: BaseException | None = None,
    allocation_error: BaseException | None = None,
    initial_error: BaseException | None = None,
    receipt_add_error: BaseException | None = None,
    enter_error: BaseException | None = None,
    exit_error: BaseException | None = None,
    suppress_exit_exception: bool = False,
    commit_error: BaseException | None = None,
) -> _Uow:
    return _Uow(
        name=name,
        events=events,
        controller_bindings=_BindingRepository(
            name=name,
            events=events,
            binding=fixture.binding,
            lock_result=lock_result,
            add_error=binding_add_error,
            before_add_error=before_add_error,
        ),
        player_characters=_PlayerCharacterRepository(
            name=name,
            events=events,
            allocation_error=allocation_error,
            initial_error=initial_error,
        ),
        creation_receipts=_CreationReceiptRepository(
            name=name,
            events=events,
            stored=stored_receipt,
            get_error=receipt_get_error,
            add_error=receipt_add_error,
        ),
        enter_error=enter_error,
        exit_error=exit_error,
        suppress_exit_exception=suppress_exit_exception,
        commit_error=commit_error,
    )


def _mutation_uow(
    fixture: _MutationFixture,
    events: list[str],
    *,
    name: str = "initial",
    current: Any = None,
    missing_current: bool = False,
    stored_receipt: StoredMutationSuccessReceipt | None = None,
    character_error: BaseException | None = None,
    receipt_get_error: BaseException | None = None,
    append_error: BaseException | None = None,
    cas_result: Any = True,
    receipt_add_error: BaseException | None = None,
    enter_error: BaseException | None = None,
    exit_error: BaseException | None = None,
    suppress_exit_exception: bool = False,
    commit_error: BaseException | None = None,
) -> _Uow:
    return _Uow(
        name=name,
        events=events,
        controller_bindings=_BindingRepository(
            name=name,
            events=events,
            binding=fixture.binding,
            lock_result=fixture.binding,
        ),
        player_characters=_PlayerCharacterRepository(
            name=name,
            events=events,
            current=(
                character_error
                if character_error is not None
                else (
                    None
                    if missing_current
                    else (fixture.current if current is None else current)
                )
            ),
            append_error=append_error,
            cas_result=cas_result,
        ),
        mutation_receipts=_MutationReceiptRepository(
            name=name,
            events=events,
            stored=stored_receipt,
            get_error=receipt_get_error,
            add_error=receipt_add_error,
        ),
        enter_error=enter_error,
        exit_error=exit_error,
        suppress_exit_exception=suppress_exit_exception,
        commit_error=commit_error,
    )


def _mutation_service(
    *,
    factory: _UowFactory,
    resolver: _Resolver,
    events: list[str],
    clock: Callable[[], datetime] | None = None,
) -> PlayerCharacterService:
    return _service(
        factory=factory,
        resolver=resolver,
        issuer=_Issuer(
            AssertionError("mutation must not issue a character identity"),
            events,
        ),
        policy=_Policy(
            events,
            error=AssertionError(
                "mutation must not call the creation policy"
            ),
        ),
        clock=clock,
    )


def test_service_dependency_and_static_catch_boundaries_are_narrow() -> None:
    source_path = Path(service_module.__file__)
    source = source_path.read_text(encoding="utf-8")
    assert "deviation_protocol.infrastructure" not in source
    assert (
        "from deviation_protocol.application.ports import" in source
        and "ControllerBindingUniquenessConflictError" in source
    )

    tree = ast.parse(source)
    matching_handlers = [
        (node, handler)
        for node in ast.walk(tree)
        if isinstance(node, ast.Try)
        for handler in node.handlers
        if isinstance(handler.type, ast.Name)
        and handler.type.id == "ControllerBindingUniquenessConflictError"
    ]
    assert any(
        len(node.body) == 1
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Await)
        and isinstance(node.body[0].value.value, ast.Call)
        and isinstance(node.body[0].value.value.func, ast.Attribute)
        and node.body[0].value.value.func.attr == "add"
        for node, _handler in matching_handlers
    )


def test_controller_binding_conflict_has_exact_static_relationships() -> None:
    conflict = PlayerCharacterControllerBindingConflictError("binding race")

    assert isinstance(conflict, ControllerBindingUniquenessConflictError)
    assert isinstance(conflict, PlayerCharacterRepositoryConflictError)
    assert issubclass(
        PlayerCharacterControllerBindingConflictError,
        ControllerBindingUniquenessConflictError,
    )
    assert issubclass(
        PlayerCharacterControllerBindingConflictError,
        PlayerCharacterRepositoryConflictError,
    )
    assert not isinstance(
        PlayerCharacterRepositoryConflictError("shared"),
        ControllerBindingUniquenessConflictError,
    )
    assert not issubclass(
        PlayerCharacterRepositoryConflictError,
        ControllerBindingUniquenessConflictError,
    )
    assert PlayerCharacterControllerBindingConflictError.__mro__[:5] == (
        PlayerCharacterControllerBindingConflictError,
        PlayerCharacterRepositoryConflictError,
        PlayerCharacterRepositoryError,
        ControllerBindingUniquenessConflictError,
        RuntimeError,
    )


class _DuplicateKeyError(Exception):
    pass


class _FlushFailureSession:
    def __init__(self) -> None:
        self.rows: list[Any] = []
        self.integrity_error = IntegrityError(
            "INSERT",
            {},
            _DuplicateKeyError(1062, "duplicate"),
        )

    def add(self, row: Any) -> None:
        self.rows.append(row)

    async def flush(self, rows: tuple[Any, ...]) -> None:
        assert rows == (self.rows[-1],)
        raise self.integrity_error


@pytest.mark.asyncio
async def test_only_binding_add_selects_narrow_duplicate_translation() -> None:
    binding_session = _FlushFailureSession()
    with pytest.raises(
        PlayerCharacterControllerBindingConflictError,
        match="controller-binding insertion conflict",
    ) as binding_exc:
        await SqlAlchemyControllerBindingRegistryRepository(
            binding_session  # type: ignore[arg-type]
        ).add(
            ControllerBindingRef(value="binding.translation"),
            created_at=_NOW,
        )
    assert type(binding_exc.value) is (
        PlayerCharacterControllerBindingConflictError
    )
    assert binding_exc.value.__cause__ is binding_session.integrity_error
    assert isinstance(
        binding_session.rows[0],
        PlayerCharacterControllerBindingRow,
    )

    allocation_session = _FlushFailureSession()
    with pytest.raises(
        PlayerCharacterRepositoryConflictError,
        match="player-character allocation conflict",
    ) as allocation_exc:
        await SqlAlchemyPlayerCharacterRepository(
            allocation_session  # type: ignore[arg-type]
        ).add_allocation(
            PlayerCharacterId(value="pc.translation"),
            created_at=_NOW,
        )
    assert type(allocation_exc.value) is PlayerCharacterRepositoryConflictError
    assert not isinstance(
        allocation_exc.value,
        ControllerBindingUniquenessConflictError,
    )
    assert allocation_exc.value.__cause__ is allocation_session.integrity_error
    assert isinstance(
        allocation_session.rows[0],
        PlayerCharacterIdAllocationRow,
    )


@pytest.mark.asyncio
async def test_create_first_execution_has_exact_write_and_commit_order() -> None:
    fixture = _creation_fixture("first")
    events: list[str] = []
    initial = _uow(fixture, events)
    factory = _UowFactory([initial], events)
    resolver = _Resolver([fixture.binding], events)
    issuer = _Issuer(fixture.player_character_id, events)
    policy = _Policy(events)

    result = await _service(
        factory=factory,
        resolver=resolver,
        issuer=issuer,
        policy=policy,
    ).create(
        _PRINCIPAL,
        operation_id=fixture.operation_id,
        command=fixture.command,
    )

    assert result == fixture.receipt.result
    assert events == [
        "resolve:1",
        "factory:initial",
        "initial:enter",
        "initial:binding-lock",
        "initial:binding-add",
        "initial:receipt-get",
        "issue",
        "initial:allocation",
        "policy",
        "initial:initial",
        "initial:receipt-add",
        "initial:commit",
        "initial:exit:none",
        "initial:close",
        "initial:exit-complete",
    ]
    assert initial.commit_calls == 1
    assert not initial.rolled_back
    assert initial.closed
    assert initial.player_characters.record == fixture.record
    assert initial.creation_receipts.added == fixture.receipt


@pytest.mark.asyncio
async def test_exact_replay_returns_stored_result_without_mutation() -> None:
    fixture = _creation_fixture("replay")
    events: list[str] = []
    initial = _uow(
        fixture,
        events,
        lock_result=fixture.binding,
        stored_receipt=fixture.receipt,
    )
    factory = _UowFactory([initial], events)
    issuer = _Issuer(AssertionError("issuer must not be called"), events)
    policy = _Policy(
        events,
        error=AssertionError("policy must not be called"),
    )

    result = await _service(
        factory=factory,
        resolver=_Resolver([fixture.binding], events),
        issuer=issuer,
        policy=policy,
    ).create(
        _PRINCIPAL,
        operation_id=fixture.operation_id,
        command=fixture.command,
    )

    assert result == fixture.receipt.result
    assert issuer.calls == 0
    assert policy.calls == 0
    assert initial.player_characters.allocation_calls == 0
    assert initial.player_characters.initial_calls == 0
    assert initial.creation_receipts.add_calls == 0
    assert initial.commit_calls == 0
    assert initial.rolled_back and initial.closed


@pytest.mark.asyncio
async def test_changed_payload_conflict_discloses_no_stored_result() -> None:
    fixture = _creation_fixture("changed")
    events: list[str] = []
    initial = _uow(
        fixture,
        events,
        lock_result=fixture.binding,
        stored_receipt=fixture.receipt,
    )
    issuer = _Issuer(AssertionError("issuer must not be called"), events)
    policy = _Policy(events)

    decision = await _service(
        factory=_UowFactory([initial], events),
        resolver=_Resolver([fixture.binding], events),
        issuer=issuer,
        policy=policy,
    ).create(
        _PRINCIPAL,
        operation_id=fixture.operation_id,
        command=_changed_command(),
    )

    assert isinstance(decision, CharacterOperationProtocolDecision)
    assert (
        decision.code is CharacterOperationProtocolCode.IDEMPOTENCY_CONFLICT
    )
    assert decision.stored_success_result is None
    assert issuer.calls == 0
    assert initial.commit_calls == 0
    assert initial.creation_receipts.add_calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("resolved", [None, object()])
async def test_unresolved_or_invalid_controller_opens_no_uow(
    resolved: Any,
) -> None:
    fixture = _creation_fixture("unauthorized")
    events: list[str] = []
    initial = _uow(fixture, events)
    factory = _UowFactory([initial], events)

    decision = await _service(
        factory=factory,
        resolver=_Resolver([resolved], events),
        issuer=_Issuer(fixture.player_character_id, events),
        policy=_Policy(events),
    ).create(
        _PRINCIPAL,
        operation_id=fixture.operation_id,
        command=fixture.command,
    )

    assert isinstance(decision, CharacterOperationProtocolDecision)
    assert decision.code is CharacterOperationProtocolCode.AUTHORIZATION_FAILED
    assert factory.calls == 0
    assert not initial.entered


@pytest.mark.asyncio
async def test_stored_binding_mismatch_rejects_before_receipt_disclosure() -> None:
    fixture = _creation_fixture("binding-mismatch")
    events: list[str] = []
    initial = _uow(
        fixture,
        events,
        lock_result=ControllerBindingRef(value="binding.other"),
    )

    decision = await _service(
        factory=_UowFactory([initial], events),
        resolver=_Resolver([fixture.binding], events),
        issuer=_Issuer(fixture.player_character_id, events),
        policy=_Policy(events),
    ).create(
        _PRINCIPAL,
        operation_id=fixture.operation_id,
        command=fixture.command,
    )

    assert isinstance(decision, CharacterOperationProtocolDecision)
    assert decision.code is CharacterOperationProtocolCode.AUTHORIZATION_FAILED
    assert initial.creation_receipts.lookups == []
    assert initial.commit_calls == 0


@pytest.mark.asyncio
async def test_operation_validation_precedes_receipt_key_and_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _creation_fixture("invalid-operation")
    events: list[str] = []
    initial = _uow(
        fixture,
        events,
        lock_result=fixture.binding,
    )
    object.__setattr__(fixture.operation_id, "value", "not valid")
    constructed_keys: list[dict[str, Any]] = []
    original_key = service_module.CreationReceiptKey

    def track_key(**kwargs: Any) -> CreationReceiptKey:
        constructed_keys.append(kwargs)
        return original_key(**kwargs)

    monkeypatch.setattr(service_module, "CreationReceiptKey", track_key)
    with pytest.raises(ValidationError):
        await _service(
            factory=_UowFactory([initial], events),
            resolver=_Resolver([fixture.binding], events),
            issuer=_Issuer(fixture.player_character_id, events),
            policy=_Policy(events),
        ).create(
            _PRINCIPAL,
            operation_id=fixture.operation_id,
            command=fixture.command,
        )

    assert constructed_keys == []
    assert initial.creation_receipts.lookups == []
    assert initial.rolled_back and initial.closed


@pytest.mark.asyncio
async def test_exact_binding_add_conflict_uses_one_disposed_then_fresh_uow() -> None:
    fixture = _creation_fixture("race")
    events: list[str] = []
    conflict = ControllerBindingUniquenessConflictError("binding race")
    initial = _uow(
        fixture,
        events,
        binding_add_error=conflict,
    )
    recovery = _uow(
        fixture,
        events,
        name="recovery",
        lock_result=fixture.binding,
        stored_receipt=fixture.receipt,
    )
    factory = _UowFactory([initial, recovery], events)
    resolver = _Resolver([fixture.binding, fixture.binding], events)
    issuer = _Issuer(
        AssertionError("recovery must not issue an identity"),
        events,
    )
    policy = _Policy(events)

    result = await _service(
        factory=factory,
        resolver=resolver,
        issuer=issuer,
        policy=policy,
    ).create(
        _PRINCIPAL,
        operation_id=fixture.operation_id,
        command=fixture.command,
    )

    assert result == fixture.receipt.result
    assert factory.calls == 2
    assert resolver.calls == 2
    assert issuer.calls == 0
    assert policy.calls == 0
    assert initial.exit_exception is conflict
    assert initial.rolled_back and initial.closed and initial.exited
    assert recovery.rolled_back and recovery.closed and recovery.exited
    assert recovery.commit_calls == 0
    assert events.index("initial:exit-complete") < events.index(
        "factory:recovery"
    )
    assert events.index("resolve:2") < events.index("recovery:binding-lock")
    assert events.index("recovery:binding-lock") < events.index(
        "recovery:receipt-get"
    )


@pytest.mark.asyncio
async def test_suppressed_binding_add_conflict_fails_closed_without_recovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _creation_fixture("suppressed-race")
    events: list[str] = []
    conflict = ControllerBindingUniquenessConflictError("binding race")
    initial = _uow(
        fixture,
        events,
        binding_add_error=conflict,
        suppress_exit_exception=True,
    )
    factory = _UowFactory([initial], events)
    resolver = _Resolver([fixture.binding], events)
    issuer = _Issuer(
        AssertionError("suppressed conflict must not issue an identity"),
        events,
    )
    policy = _Policy(
        events,
        error=AssertionError("suppressed conflict must not call policy"),
    )
    constructed_keys: list[dict[str, Any]] = []
    original_key = service_module.CreationReceiptKey

    def track_key(**kwargs: Any) -> CreationReceiptKey:
        constructed_keys.append(kwargs)
        return original_key(**kwargs)

    monkeypatch.setattr(service_module, "CreationReceiptKey", track_key)

    with pytest.raises(
        ControllerBindingUniquenessConflictError
    ) as exc_info:
        await _service(
            factory=factory,
            resolver=resolver,
            issuer=issuer,
            policy=policy,
        ).create(
            _PRINCIPAL,
            operation_id=fixture.operation_id,
            command=fixture.command,
        )

    assert exc_info.value is conflict
    assert initial.exit_exception is conflict
    assert factory.calls == 1
    assert resolver.calls == 1
    assert initial.entered and initial.exited
    assert initial.rolled_back and initial.closed
    assert initial.controller_bindings.lock_calls == 1
    assert initial.controller_bindings.add_calls == 1
    assert constructed_keys == []
    assert initial.creation_receipts.lookups == []
    assert issuer.calls == 0
    assert policy.calls == 0
    assert initial.player_characters.allocation_calls == 0
    assert initial.player_characters.initial_calls == 0
    assert initial.creation_receipts.add_calls == 0
    assert initial.commit_calls == 0
    assert not initial.committed
    assert not any("recovery" in event for event in events)


@pytest.mark.asyncio
async def test_recovery_absent_winner_stops_without_third_uow_or_retry() -> None:
    fixture = _creation_fixture("absent-winner")
    events: list[str] = []
    initial = _uow(
        fixture,
        events,
        binding_add_error=ControllerBindingUniquenessConflictError(
            "binding race"
        ),
    )
    recovery = _uow(
        fixture,
        events,
        name="recovery",
        lock_result=fixture.binding,
    )
    factory = _UowFactory([initial, recovery], events)
    issuer = _Issuer(fixture.player_character_id, events)

    decision = await _service(
        factory=factory,
        resolver=_Resolver(
            [fixture.binding, fixture.binding],
            events,
        ),
        issuer=issuer,
        policy=_Policy(events),
    ).create(
        _PRINCIPAL,
        operation_id=fixture.operation_id,
        command=fixture.command,
    )

    assert isinstance(decision, CharacterOperationProtocolDecision)
    assert (
        decision.code
        is CharacterOperationProtocolCode.STORED_RECEIPT_INTEGRITY_FAILURE
    )
    assert factory.calls == 2
    assert issuer.calls == 0
    assert initial.controller_bindings.add_calls == 1
    assert recovery.controller_bindings.add_calls == 0
    assert recovery.creation_receipts.lookups == [fixture.receipt.key]


@pytest.mark.asyncio
@pytest.mark.parametrize("recovery_state", ["changed-authority", "missing-lock"])
async def test_recovery_reauthorizes_and_relocks_before_receipt_lookup(
    recovery_state: str,
) -> None:
    fixture = _creation_fixture(f"recovery-{recovery_state}")
    events: list[str] = []
    initial = _uow(
        fixture,
        events,
        binding_add_error=ControllerBindingUniquenessConflictError(
            "binding race"
        ),
    )
    recovered_binding = (
        ControllerBindingRef(value="binding.changed-authority")
        if recovery_state == "changed-authority"
        else fixture.binding
    )
    recovery = _uow(
        fixture,
        events,
        name="recovery",
        lock_result=(
            None if recovery_state == "missing-lock" else fixture.binding
        ),
    )
    factory = _UowFactory([initial, recovery], events)

    decision = await _service(
        factory=factory,
        resolver=_Resolver(
            [fixture.binding, recovered_binding],
            events,
        ),
        issuer=_Issuer(fixture.player_character_id, events),
        policy=_Policy(events),
    ).create(
        _PRINCIPAL,
        operation_id=fixture.operation_id,
        command=fixture.command,
    )

    assert isinstance(decision, CharacterOperationProtocolDecision)
    assert decision.code is CharacterOperationProtocolCode.AUTHORIZATION_FAILED
    assert recovery.creation_receipts.lookups == []
    assert recovery.commit_calls == 0
    if recovery_state == "changed-authority":
        assert recovery.controller_bindings.lock_calls == 0
    else:
        assert recovery.controller_bindings.lock_calls == 1


@pytest.mark.asyncio
async def test_corrupted_operation_id_fails_second_validation_before_key_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _creation_fixture("corrupted-race")
    assert (
        revalidate_player_character_model(
            fixture.operation_id,
            PlayerCharacterOperationId,
        )
        is fixture.operation_id
    )
    events: list[str] = []

    def corrupt_operation_id() -> None:
        object.__setattr__(fixture.operation_id, "value", "corrupted value")

    initial = _uow(
        fixture,
        events,
        binding_add_error=ControllerBindingUniquenessConflictError(
            "binding race"
        ),
        before_add_error=corrupt_operation_id,
    )
    recovery = _uow(
        fixture,
        events,
        name="recovery",
        lock_result=fixture.binding,
    )
    factory = _UowFactory([initial, recovery], events)
    original_revalidate = service_module.revalidate_player_character_model
    validation_failures: list[BaseException] = []

    def track_revalidation(value: Any, model_type: Any) -> Any:
        try:
            return original_revalidate(value, model_type)
        except (AttributeError, TypeError, ValueError) as exc:
            if model_type is PlayerCharacterOperationId:
                validation_failures.append(exc)
            raise

    constructed_keys: list[dict[str, Any]] = []
    original_key = service_module.CreationReceiptKey

    def track_key(**kwargs: Any) -> CreationReceiptKey:
        constructed_keys.append(kwargs)
        return original_key(**kwargs)

    monkeypatch.setattr(
        service_module,
        "revalidate_player_character_model",
        track_revalidation,
    )
    monkeypatch.setattr(service_module, "CreationReceiptKey", track_key)

    with pytest.raises(ValidationError) as exc_info:
        await _service(
            factory=factory,
            resolver=_Resolver(
                [fixture.binding, fixture.binding],
                events,
            ),
            issuer=_Issuer(fixture.player_character_id, events),
            policy=_Policy(events),
        ).create(
            _PRINCIPAL,
            operation_id=fixture.operation_id,
            command=fixture.command,
        )

    assert validation_failures == [exc_info.value]
    assert validation_failures[0] is exc_info.value
    assert factory.calls == 2
    assert initial.rolled_back and initial.closed
    assert recovery.controller_bindings.lock_calls == 1
    assert constructed_keys == []
    assert recovery.creation_receipts.lookups == []
    assert "recovery:receipt-get" not in events


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure_site",
    ["receipt-get", "allocation", "initial", "receipt-add", "commit"],
)
async def test_same_narrow_type_from_unapproved_later_site_propagates(
    failure_site: str,
) -> None:
    fixture = _creation_fixture(f"later-{failure_site}")
    events: list[str] = []
    error = ControllerBindingUniquenessConflictError(failure_site)
    options: dict[str, Any] = {
        "lock_result": fixture.binding,
        "receipt_get_error": (
            error if failure_site == "receipt-get" else None
        ),
        "allocation_error": (
            error if failure_site == "allocation" else None
        ),
        "initial_error": error if failure_site == "initial" else None,
        "receipt_add_error": (
            error if failure_site == "receipt-add" else None
        ),
        "commit_error": error if failure_site == "commit" else None,
    }
    initial = _uow(fixture, events, **options)
    factory = _UowFactory([initial], events)

    with pytest.raises(
        ControllerBindingUniquenessConflictError
    ) as exc_info:
        await _service(
            factory=factory,
            resolver=_Resolver([fixture.binding], events),
            issuer=_Issuer(fixture.player_character_id, events),
            policy=_Policy(events),
        ).create(
            _PRINCIPAL,
            operation_id=fixture.operation_id,
            command=fixture.command,
        )

    assert exc_info.value is error
    assert factory.calls == 1
    assert initial.rolled_back and initial.closed


@pytest.mark.asyncio
@pytest.mark.parametrize("lifecycle_site", ["resolve", "enter", "exit"])
async def test_narrow_type_from_unapproved_lifecycle_site_propagates(
    lifecycle_site: str,
) -> None:
    fixture = _creation_fixture(f"lifecycle-{lifecycle_site}")
    events: list[str] = []
    error = ControllerBindingUniquenessConflictError(lifecycle_site)
    initial = _uow(
        fixture,
        events,
        lock_result=fixture.binding,
        enter_error=error if lifecycle_site == "enter" else None,
        exit_error=error if lifecycle_site == "exit" else None,
        stored_receipt=(
            fixture.receipt if lifecycle_site == "exit" else None
        ),
    )
    factory = _UowFactory([initial], events)
    resolver_value: Any = (
        error if lifecycle_site == "resolve" else fixture.binding
    )

    with pytest.raises(
        ControllerBindingUniquenessConflictError
    ) as exc_info:
        await _service(
            factory=factory,
            resolver=_Resolver([resolver_value], events),
            issuer=_Issuer(fixture.player_character_id, events),
            policy=_Policy(events),
        ).create(
            _PRINCIPAL,
            operation_id=fixture.operation_id,
            command=fixture.command,
        )

    assert exc_info.value is error
    assert factory.calls == (0 if lifecycle_site == "resolve" else 1)


class _UncertainCommitOutcomeError(RuntimeError):
    pass


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "commit_error",
    [
        RuntimeError("commit failed"),
        _UncertainCommitOutcomeError("commit outcome unknown"),
    ],
    ids=["commit-failure", "uncertain-commit"],
)
async def test_commit_failures_never_recover_or_reread(
    commit_error: BaseException,
) -> None:
    fixture = _creation_fixture("commit")
    events: list[str] = []
    initial = _uow(
        fixture,
        events,
        lock_result=fixture.binding,
        commit_error=commit_error,
    )
    factory = _UowFactory([initial], events)

    with pytest.raises(type(commit_error)) as exc_info:
        await _service(
            factory=factory,
            resolver=_Resolver([fixture.binding], events),
            issuer=_Issuer(fixture.player_character_id, events),
            policy=_Policy(events),
        ).create(
            _PRINCIPAL,
            operation_id=fixture.operation_id,
            command=fixture.command,
        )

    assert exc_info.value is commit_error
    assert factory.calls == 1
    assert initial.creation_receipts.lookups == [fixture.receipt.key]
    assert initial.commit_calls == 1
    assert not initial.committed
    assert initial.rolled_back and initial.closed


@pytest.mark.asyncio
async def test_allocation_shared_conflict_and_cancellation_never_recover() -> None:
    fixture = _creation_fixture("excluded")
    for error in (
        PlayerCharacterRepositoryConflictError("allocation conflict"),
        asyncio.CancelledError(),
    ):
        events: list[str] = []
        initial = _uow(
            fixture,
            events,
            lock_result=fixture.binding,
            allocation_error=error,
        )
        factory = _UowFactory([initial], events)

        with pytest.raises(type(error)) as exc_info:
            await _service(
                factory=factory,
                resolver=_Resolver([fixture.binding], events),
                issuer=_Issuer(fixture.player_character_id, events),
                policy=_Policy(events),
            ).create(
                _PRINCIPAL,
                operation_id=fixture.operation_id,
                command=fixture.command,
            )

        assert exc_info.value is error
        assert factory.calls == 1
        assert initial.rolled_back and initial.closed
        assert initial.commit_calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("failure_site", ["issuer", "policy", "uow-exit"])
async def test_issuer_policy_and_uow_exit_failures_never_recover(
    failure_site: str,
) -> None:
    fixture = _creation_fixture(f"excluded-{failure_site}")
    events: list[str] = []
    error = RuntimeError(failure_site)
    initial = _uow(
        fixture,
        events,
        lock_result=fixture.binding,
        exit_error=error if failure_site == "uow-exit" else None,
        stored_receipt=(
            fixture.receipt if failure_site == "uow-exit" else None
        ),
    )
    factory = _UowFactory([initial], events)

    with pytest.raises(RuntimeError) as exc_info:
        await _service(
            factory=factory,
            resolver=_Resolver([fixture.binding], events),
            issuer=_Issuer(
                error if failure_site == "issuer" else fixture.player_character_id,
                events,
            ),
            policy=_Policy(
                events,
                error=error if failure_site == "policy" else None,
            ),
        ).create(
            _PRINCIPAL,
            operation_id=fixture.operation_id,
            command=fixture.command,
        )

    assert exc_info.value is error
    assert factory.calls == 1


def test_mutation_receipt_conflict_has_exact_static_relationships() -> None:
    conflict = PlayerCharacterMutationReceiptConflictError("receipt race")

    assert isinstance(conflict, MutationReceiptUniquenessConflictError)
    assert isinstance(conflict, PlayerCharacterRepositoryConflictError)
    assert not isinstance(
        PlayerCharacterRepositoryConflictError("shared"),
        MutationReceiptUniquenessConflictError,
    )
    assert PlayerCharacterMutationReceiptConflictError.__mro__[:5] == (
        PlayerCharacterMutationReceiptConflictError,
        PlayerCharacterRepositoryConflictError,
        PlayerCharacterRepositoryError,
        MutationReceiptUniquenessConflictError,
        RuntimeError,
    )

    repository_source = (
        Path(service_module.__file__).parents[1]
        / "infrastructure"
        / "repositories.py"
    ).read_text(encoding="utf-8")
    assert (
        repository_source.count(
            "conflict_type=PlayerCharacterMutationReceiptConflictError"
        )
        == 1
    )
    receipt_class_source = repository_source.split(
        "class SqlAlchemyPlayerCharacterMutationReceiptRepository",
        maxsplit=1,
    )[1]
    assert (
        "conflict_type=PlayerCharacterMutationReceiptConflictError"
        in receipt_class_source
    )


@pytest.mark.asyncio
async def test_mutate_success_has_exact_write_commit_and_return_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _mutation_fixture("success")
    events: list[str] = []
    initial = _mutation_uow(fixture, events)
    factory = _UowFactory([initial], events)
    policy_calls = 0

    def tracked_policy(
        record: CanonicalPlayerCharacter,
        *,
        command: CharacterMutationCommand,
        operation_id: PlayerCharacterOperationId,
    ) -> PlayerCharacterPolicyDecision:
        nonlocal policy_calls
        policy_calls += 1
        events.append("mutation-policy")
        return evaluate_mutation_policy(
            record,
            command=command,
            operation_id=operation_id,
        )

    def clock() -> datetime:
        events.append("clock")
        return _NOW

    monkeypatch.setattr(
        service_module,
        "evaluate_mutation_policy",
        tracked_policy,
    )
    result = await _mutation_service(
        factory=factory,
        resolver=_Resolver([fixture.binding], events),
        events=events,
        clock=clock,
    ).mutate(
        _PRINCIPAL,
        operation_id=fixture.operation_id,
        command=fixture.command,
    )

    assert result == fixture.receipt.result
    assert policy_calls == 1
    assert events == [
        "resolve:1",
        "factory:initial",
        "initial:enter",
        "initial:character-lock",
        "initial:mutation-receipt-get",
        "mutation-policy",
        "clock",
        "initial:history-append",
        "initial:current-cas",
        "initial:mutation-receipt-add",
        "initial:commit",
        "initial:exit:none",
        "initial:close",
        "initial:exit-complete",
    ]
    assert initial.player_characters.appended == fixture.successor
    assert initial.player_characters.swapped == fixture.successor
    assert initial.mutation_receipts.added == fixture.receipt
    assert initial.commit_calls == 1
    assert initial.committed and initial.closed
    assert events.index("initial:commit") < events.index(
        "initial:exit-complete"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["missing", "wrong-owner"])
async def test_mutate_missing_and_wrong_owner_are_non_enumerating(
    state: str,
) -> None:
    fixture = _mutation_fixture(state)
    events: list[str] = []
    wrong_owner = fixture.current.detached_validated_copy(
        controller_binding=ControllerBindingRef(value="binding.other-owner")
    )
    initial = _mutation_uow(
        fixture,
        events,
        missing_current=state == "missing",
        current=wrong_owner if state == "wrong-owner" else None,
    )

    decision = await _mutation_service(
        factory=_UowFactory([initial], events),
        resolver=_Resolver([fixture.binding], events),
        events=events,
    ).mutate(
        _PRINCIPAL,
        operation_id=fixture.operation_id,
        command=fixture.command,
    )

    assert isinstance(decision, CharacterOperationProtocolDecision)
    assert decision.code is CharacterOperationProtocolCode.AUTHORIZATION_FAILED
    assert initial.mutation_receipts.lookups == []
    assert initial.player_characters.append_calls == 0
    assert initial.commit_calls == 0
    assert initial.rolled_back and initial.closed


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_input",
    ["command", "operation-id", "revision"],
)
async def test_mutate_invalid_typed_inputs_precede_key_construction(
    invalid_input: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _mutation_fixture(f"invalid-{invalid_input}")
    command = fixture.command.model_copy(deep=True)
    operation_id = fixture.operation_id.model_copy(deep=True)
    if invalid_input == "command":
        object.__setattr__(command, "contract_version", "invalid")
    elif invalid_input == "operation-id":
        object.__setattr__(operation_id, "value", "not valid")
    else:
        object.__setattr__(command.expected_revision, "value", 0)

    events: list[str] = []
    initial = _mutation_uow(fixture, events)
    constructed_keys: list[dict[str, Any]] = []
    original_key = service_module.MutationReceiptKey

    def track_key(**kwargs: Any) -> MutationReceiptKey:
        constructed_keys.append(kwargs)
        return original_key(**kwargs)

    monkeypatch.setattr(service_module, "MutationReceiptKey", track_key)
    with pytest.raises((ValidationError, TypeError, ValueError)):
        await _mutation_service(
            factory=_UowFactory([initial], events),
            resolver=_Resolver([fixture.binding], events),
            events=events,
        ).mutate(
            _PRINCIPAL,
            operation_id=operation_id,
            command=command,
        )

    assert constructed_keys == []
    assert initial.mutation_receipts.lookups == []
    assert initial.rolled_back and initial.closed


@pytest.mark.asyncio
async def test_mutate_revision_exhaustion_precedes_receipt_lookup() -> None:
    fixture = _mutation_fixture("revision-exhausted")
    maximum_revision = PlayerCharacterRevision(
        value=9_223_372_036_854_775_807
    )
    command = CharacterMutationCommand(
        contract_version=fixture.command.contract_version,
        command_kind=fixture.command.command_kind,
        target_player_character_id=fixture.command.target_player_character_id,
        expected_revision=maximum_revision,
        applicable_reference=ApplicableCharacterReference(
            player_character_id=fixture.current.player_character_id,
            contract_version=fixture.current.contract_version,
            record_revision=maximum_revision,
        ),
        confirmation=PlayerConfirmation(
            player_character_id=fixture.current.player_character_id,
            expected_revision=maximum_revision,
            operation_id=fixture.operation_id,
            mutation_kind=fixture.command.command_kind,
            source_reference=AuthoritySourceRef(
                value="source.revision-exhausted"
            ),
        ),
    )
    events: list[str] = []
    initial = _mutation_uow(fixture, events)

    decision = await _mutation_service(
        factory=_UowFactory([initial], events),
        resolver=_Resolver([fixture.binding], events),
        events=events,
    ).mutate(
        _PRINCIPAL,
        operation_id=fixture.operation_id,
        command=command,
    )

    assert isinstance(decision, CharacterOperationProtocolDecision)
    assert decision.code is CharacterOperationProtocolCode.REVISION_EXHAUSTED
    assert initial.mutation_receipts.lookups == []
    assert initial.player_characters.append_calls == 0
    assert initial.commit_calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("reuse", ["compatible", "incompatible"])
async def test_mutate_receipt_is_evaluated_before_stale_revision(
    reuse: str,
) -> None:
    fixture = _mutation_fixture(f"receipt-before-stale-{reuse}")
    events: list[str] = []
    initial = _mutation_uow(
        fixture,
        events,
        current=fixture.successor,
        stored_receipt=fixture.receipt,
    )
    command = (
        fixture.command
        if reuse == "compatible"
        else _changed_mutation_command(fixture)
    )

    result = await _mutation_service(
        factory=_UowFactory([initial], events),
        resolver=_Resolver([fixture.binding], events),
        events=events,
        clock=lambda: (_ for _ in ()).throw(
            AssertionError("replay must not read the clock")
        ),
    ).mutate(
        _PRINCIPAL,
        operation_id=fixture.operation_id,
        command=command,
    )

    if reuse == "compatible":
        assert result == fixture.receipt.result
    else:
        assert isinstance(result, CharacterOperationProtocolDecision)
        assert (
            result.code
            is CharacterOperationProtocolCode.IDEMPOTENCY_CONFLICT
        )
        assert result.stored_success_result is None
    assert initial.mutation_receipts.lookups == [fixture.receipt.key]
    assert initial.player_characters.append_calls == 0
    assert initial.player_characters.cas_calls == 0
    assert initial.mutation_receipts.add_calls == 0
    assert initial.commit_calls == 0
    assert initial.rolled_back and initial.closed


@pytest.mark.asyncio
async def test_mutate_new_stale_revision_stops_before_policy() -> None:
    fixture = _mutation_fixture("new-stale")
    events: list[str] = []
    initial = _mutation_uow(
        fixture,
        events,
        current=fixture.successor,
    )

    decision = await _mutation_service(
        factory=_UowFactory([initial], events),
        resolver=_Resolver([fixture.binding], events),
        events=events,
    ).mutate(
        _PRINCIPAL,
        operation_id=fixture.operation_id,
        command=fixture.command,
    )

    assert isinstance(decision, CharacterOperationProtocolDecision)
    assert decision.code is CharacterOperationProtocolCode.STALE_REVISION
    assert initial.mutation_receipts.lookups == [fixture.receipt.key]
    assert initial.player_characters.append_calls == 0
    assert initial.commit_calls == 0


@pytest.mark.asyncio
async def test_mutate_policy_denial_returns_exact_object_without_persistence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _mutation_fixture("denial")
    events: list[str] = []
    initial = _mutation_uow(fixture, events)
    denied = PlayerCharacterPolicyDecision(
        code=PlayerCharacterPolicyCode.INVALID_TRANSITION
    )
    policy_calls = 0

    def deny(*args: Any, **kwargs: Any) -> PlayerCharacterPolicyDecision:
        nonlocal policy_calls
        policy_calls += 1
        return denied

    monkeypatch.setattr(service_module, "evaluate_mutation_policy", deny)
    result = await _mutation_service(
        factory=_UowFactory([initial], events),
        resolver=_Resolver([fixture.binding], events),
        events=events,
        clock=lambda: (_ for _ in ()).throw(
            AssertionError("denial must not read the clock")
        ),
    ).mutate(
        _PRINCIPAL,
        operation_id=fixture.operation_id,
        command=fixture.command,
    )

    assert result is denied
    assert policy_calls == 1
    assert initial.player_characters.append_calls == 0
    assert initial.player_characters.cas_calls == 0
    assert initial.mutation_receipts.add_calls == 0
    assert initial.commit_calls == 0
    assert initial.rolled_back and initial.closed


@pytest.mark.asyncio
async def test_mutate_cas_false_returns_stale_and_rolls_back_history() -> None:
    fixture = _mutation_fixture("cas-loss")
    events: list[str] = []
    initial = _mutation_uow(fixture, events, cas_result=False)
    factory = _UowFactory([initial], events)

    decision = await _mutation_service(
        factory=factory,
        resolver=_Resolver([fixture.binding], events),
        events=events,
    ).mutate(
        _PRINCIPAL,
        operation_id=fixture.operation_id,
        command=fixture.command,
    )

    assert isinstance(decision, CharacterOperationProtocolDecision)
    assert decision.code is CharacterOperationProtocolCode.STALE_REVISION
    assert initial.player_characters.append_calls == 1
    assert initial.player_characters.cas_calls == 1
    assert initial.mutation_receipts.add_calls == 0
    assert initial.commit_calls == 0
    assert factory.calls == 1
    assert initial.rolled_back and initial.closed


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure_site",
    ["lock", "history", "cas", "receipt", "commit", "cancel"],
)
async def test_mutate_failures_propagate_and_never_retry(
    failure_site: str,
) -> None:
    fixture = _mutation_fixture(f"failure-{failure_site}")
    events: list[str] = []
    error: BaseException = (
        asyncio.CancelledError()
        if failure_site == "cancel"
        else RuntimeError(failure_site)
    )
    initial = _mutation_uow(
        fixture,
        events,
        character_error=error if failure_site == "lock" else None,
        append_error=(
            error if failure_site in {"history", "cancel"} else None
        ),
        cas_result=error if failure_site == "cas" else True,
        receipt_add_error=error if failure_site == "receipt" else None,
        commit_error=error if failure_site == "commit" else None,
    )
    factory = _UowFactory([initial], events)

    with pytest.raises(type(error)) as exc_info:
        await _mutation_service(
            factory=factory,
            resolver=_Resolver([fixture.binding], events),
            events=events,
        ).mutate(
            _PRINCIPAL,
            operation_id=fixture.operation_id,
            command=fixture.command,
        )

    assert exc_info.value is error
    assert factory.calls == 1
    assert initial.rolled_back and initial.closed
    assert initial.commit_calls == (1 if failure_site == "commit" else 0)


@pytest.mark.asyncio
async def test_exact_mutation_receipt_conflict_recovers_one_committed_winner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _mutation_fixture("race-winner")
    events: list[str] = []
    conflict = MutationReceiptUniquenessConflictError("receipt race")
    initial = _mutation_uow(
        fixture,
        events,
        receipt_add_error=conflict,
    )
    recovery = _mutation_uow(
        fixture,
        events,
        name="recovery",
        current=fixture.successor,
        stored_receipt=fixture.receipt,
    )
    factory = _UowFactory([initial, recovery], events)
    policy_calls = 0
    original_policy = service_module.evaluate_mutation_policy

    def tracked_policy(*args: Any, **kwargs: Any) -> Any:
        nonlocal policy_calls
        policy_calls += 1
        return original_policy(*args, **kwargs)

    monkeypatch.setattr(
        service_module,
        "evaluate_mutation_policy",
        tracked_policy,
    )
    result = await _mutation_service(
        factory=factory,
        resolver=_Resolver(
            [fixture.binding, fixture.binding],
            events,
        ),
        events=events,
    ).mutate(
        _PRINCIPAL,
        operation_id=fixture.operation_id,
        command=fixture.command,
    )

    assert result == fixture.receipt.result
    assert policy_calls == 1
    assert factory.calls == 2
    assert initial.exit_exception is conflict
    assert initial.rolled_back and initial.closed and initial.exited
    assert recovery.rolled_back and recovery.closed and recovery.exited
    assert recovery.player_characters.append_calls == 0
    assert recovery.player_characters.cas_calls == 0
    assert recovery.mutation_receipts.add_calls == 0
    assert recovery.commit_calls == 0
    assert events.index("initial:exit-complete") < events.index(
        "factory:recovery"
    )
    assert events.index("resolve:2") < events.index(
        "recovery:character-lock"
    )
    assert events.index("recovery:character-lock") < events.index(
        "recovery:mutation-receipt-get"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("winner_evidence", ["incompatible", "missing"])
async def test_mutation_recovery_conflict_or_missing_evidence_fails_closed(
    winner_evidence: str,
) -> None:
    fixture = _mutation_fixture(f"recovery-{winner_evidence}")
    events: list[str] = []
    command = (
        _changed_mutation_command(fixture)
        if winner_evidence == "incompatible"
        else fixture.command
    )
    initial = _mutation_uow(
        fixture,
        events,
        receipt_add_error=MutationReceiptUniquenessConflictError(
            "receipt race"
        ),
    )
    recovery = _mutation_uow(
        fixture,
        events,
        name="recovery",
        current=fixture.successor,
        stored_receipt=(
            fixture.receipt
            if winner_evidence == "incompatible"
            else None
        ),
    )
    factory = _UowFactory([initial, recovery], events)

    decision = await _mutation_service(
        factory=factory,
        resolver=_Resolver(
            [fixture.binding, fixture.binding],
            events,
        ),
        events=events,
    ).mutate(
        _PRINCIPAL,
        operation_id=fixture.operation_id,
        command=command,
    )

    assert isinstance(decision, CharacterOperationProtocolDecision)
    assert decision.code is (
        CharacterOperationProtocolCode.IDEMPOTENCY_CONFLICT
        if winner_evidence == "incompatible"
        else CharacterOperationProtocolCode.STORED_RECEIPT_INTEGRITY_FAILURE
    )
    assert factory.calls == 2
    assert recovery.commit_calls == 0


@pytest.mark.asyncio
async def test_mutation_conflict_requires_exact_escaped_exception_provenance() -> None:
    fixture = _mutation_fixture("provenance")
    for exit_behavior in ("suppressed", "replacement"):
        events: list[str] = []
        recorded = MutationReceiptUniquenessConflictError("recorded")
        replacement = MutationReceiptUniquenessConflictError("replacement")
        initial = _mutation_uow(
            fixture,
            events,
            receipt_add_error=recorded,
            suppress_exit_exception=exit_behavior == "suppressed",
            exit_error=(
                replacement if exit_behavior == "replacement" else None
            ),
        )
        factory = _UowFactory([initial], events)

        with pytest.raises(
            MutationReceiptUniquenessConflictError
        ) as exc_info:
            await _mutation_service(
                factory=factory,
                resolver=_Resolver([fixture.binding], events),
                events=events,
            ).mutate(
                _PRINCIPAL,
                operation_id=fixture.operation_id,
                command=fixture.command,
            )

        assert exc_info.value is (
            recorded if exit_behavior == "suppressed" else replacement
        )
        assert factory.calls == 1
        assert initial.rolled_back and initial.closed


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "unapproved_error",
    [
        PlayerCharacterRepositoryConflictError("shared receipt conflict"),
        MutationReceiptUniquenessConflictError("commit narrow type"),
    ],
    ids=["shared-receipt-conflict", "narrow-type-at-commit"],
)
async def test_mutation_unapproved_conflicts_never_recover(
    unapproved_error: BaseException,
) -> None:
    fixture = _mutation_fixture("unapproved")
    events: list[str] = []
    is_commit = isinstance(
        unapproved_error,
        MutationReceiptUniquenessConflictError,
    )
    initial = _mutation_uow(
        fixture,
        events,
        receipt_add_error=None if is_commit else unapproved_error,
        commit_error=unapproved_error if is_commit else None,
    )
    factory = _UowFactory([initial], events)

    with pytest.raises(type(unapproved_error)) as exc_info:
        await _mutation_service(
            factory=factory,
            resolver=_Resolver([fixture.binding], events),
            events=events,
        ).mutate(
            _PRINCIPAL,
            operation_id=fixture.operation_id,
            command=fixture.command,
        )

    assert exc_info.value is unapproved_error
    assert factory.calls == 1
    assert initial.rolled_back and initial.closed
