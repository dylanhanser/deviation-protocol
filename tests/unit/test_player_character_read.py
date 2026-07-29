from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.player_character_operations import (
    CharacterMutationCommand,
    evaluate_mutation_policy,
)
from deviation_protocol.application.player_character_projection import (
    PlayerCharacterSelfProjection,
)
from deviation_protocol.application.player_character_service import (
    PlayerCharacterService,
)
from deviation_protocol.domain.player_character import (
    ApplicableCharacterReference,
    AuthoritySourceRef,
    CanonicalPlayerCharacter,
    CharacterCore,
    ControllerBindingRef,
    NarrationPreferences,
    PlayerCharacterContractVersion,
    PlayerCharacterId,
    PlayerCharacterLifecycle,
    PlayerCharacterMutationKind,
    PlayerCharacterOperationId,
    PlayerCharacterRevision,
)
from deviation_protocol.domain.player_character_policies import (
    CreatePlayerCharacterPolicy,
    PlayerConfirmation,
)


_PRINCIPAL = RequestPrincipal(
    player_id="player.read",
    authentication_scheme="test",
)
_BINDING = ControllerBindingRef(value="binding.read")
_CHARACTER_ID = PlayerCharacterId(value="pc.read")
_NOW = datetime(2026, 7, 29, 12, 30, tzinfo=UTC)


def _created_record(
    *,
    binding: ControllerBindingRef = _BINDING,
    player_character_id: PlayerCharacterId = _CHARACTER_ID,
) -> CanonicalPlayerCharacter:
    return CreatePlayerCharacterPolicy().create(
        player_character_id=player_character_id,
        controller_binding=binding,
        character_core=CharacterCore(),
        narration_preferences=NarrationPreferences(),
        source_reference=AuthoritySourceRef(value="source.read-create"),
    )


def _retired_record(
    initial: CanonicalPlayerCharacter,
) -> CanonicalPlayerCharacter:
    operation_id = PlayerCharacterOperationId(value="operation.read-retire")
    command = CharacterMutationCommand(
        contract_version=initial.contract_version,
        command_kind=PlayerCharacterMutationKind.RETIRE,
        target_player_character_id=initial.player_character_id,
        expected_revision=initial.record_revision,
        applicable_reference=ApplicableCharacterReference(
            player_character_id=initial.player_character_id,
            contract_version=initial.contract_version,
            record_revision=initial.record_revision,
        ),
        confirmation=PlayerConfirmation(
            player_character_id=initial.player_character_id,
            expected_revision=initial.record_revision,
            operation_id=operation_id,
            mutation_kind=PlayerCharacterMutationKind.RETIRE,
            source_reference=AuthoritySourceRef(
                value="source.read-retire"
            ),
        ),
    )
    decision = evaluate_mutation_policy(
        initial,
        command=command,
        operation_id=operation_id,
    )
    assert decision.accepted
    assert decision.resulting_record is not None
    return decision.resulting_record


class _Resolver:
    def __init__(
        self,
        value: Any,
        events: list[str],
    ) -> None:
        self.value = value
        self.events = events
        self.calls = 0

    async def resolve(self, principal: RequestPrincipal, /) -> Any:
        assert principal is _PRINCIPAL
        self.calls += 1
        self.events.append("resolve")
        if isinstance(self.value, BaseException):
            raise self.value
        return self.value


class _Repository:
    def __init__(
        self,
        current: Any,
        events: list[str],
    ) -> None:
        self.current = current
        self.events = events
        self.requests: list[PlayerCharacterId] = []

    async def get(
        self,
        player_character_id: PlayerCharacterId,
    ) -> Any:
        self.requests.append(player_character_id)
        self.events.append("character-get")
        if isinstance(self.current, BaseException):
            raise self.current
        return self.current


class _ReadUnitOfWork:
    def __init__(
        self,
        repository: _Repository,
        events: list[str],
        *,
        enter_error: BaseException | None = None,
        exit_error: BaseException | None = None,
    ) -> None:
        self.player_characters = repository
        self.events = events
        self.enter_error = enter_error
        self.exit_error = exit_error
        self.commit_calls = 0

    async def __aenter__(self) -> _ReadUnitOfWork:
        self.events.append("enter")
        if self.enter_error is not None:
            raise self.enter_error
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: Any,
    ) -> None:
        self.events.append(
            f"exit:{exc_type.__name__ if exc_type else 'none'}"
        )
        if self.exit_error is not None:
            raise self.exit_error

    async def commit(self) -> None:
        self.commit_calls += 1
        raise AssertionError("owned reads must not commit")


class _Factory:
    def __init__(
        self,
        uow: _ReadUnitOfWork,
        events: list[str],
    ) -> None:
        self.uow = uow
        self.events = events
        self.calls = 0

    def __call__(self) -> _ReadUnitOfWork:
        self.calls += 1
        self.events.append("factory")
        return self.uow


class _UnusedIssuer:
    def issue(self) -> PlayerCharacterId:
        raise AssertionError("owned reads must not issue an identity")


def _service(
    *,
    resolver: _Resolver,
    factory: _Factory,
    clock: Callable[[], datetime] = lambda: _NOW,
) -> PlayerCharacterService:
    return PlayerCharacterService(
        uow_factory=factory,
        controller_binding_resolver=resolver,
        player_character_id_issuer=_UnusedIssuer(),
        create_policy=CreatePlayerCharacterPolicy(),
        source_reference=AuthoritySourceRef(value="source.read-service"),
        clock=clock,
    )


def _read_scope(
    current: Any,
    *,
    resolved_binding: Any = _BINDING,
    enter_error: BaseException | None = None,
    exit_error: BaseException | None = None,
) -> tuple[
    PlayerCharacterService,
    _Resolver,
    _Repository,
    _ReadUnitOfWork,
    _Factory,
    list[str],
]:
    events: list[str] = []
    resolver = _Resolver(resolved_binding, events)
    repository = _Repository(current, events)
    uow = _ReadUnitOfWork(
        repository,
        events,
        enter_error=enter_error,
        exit_error=exit_error,
    )
    factory = _Factory(uow, events)
    return (
        _service(resolver=resolver, factory=factory),
        resolver,
        repository,
        uow,
        factory,
        events,
    )


@pytest.mark.parametrize("use_mutated_record", [False, True])
async def test_get_owned_projects_created_and_mutated_current_state(
    use_mutated_record: bool,
) -> None:
    initial = _created_record()
    current = _retired_record(initial) if use_mutated_record else initial
    service, resolver, repository, uow, factory, events = _read_scope(
        current
    )

    result = await service.get_owned(
        _PRINCIPAL,
        player_character_id=_CHARACTER_ID,
    )

    assert isinstance(result, PlayerCharacterSelfProjection)
    assert result.model_dump(mode="json") == {
        "player_character_id": {"value": _CHARACTER_ID.value},
        "contract_version": PlayerCharacterContractVersion.V1.value,
        "record_revision": {"value": current.record_revision.value},
        "lifecycle": current.lifecycle.value,
    }
    assert result.player_character_id is not current.player_character_id
    assert result.record_revision is not current.record_revision
    assert set(type(result).model_fields) == {
        "player_character_id",
        "contract_version",
        "record_revision",
        "lifecycle",
    }
    serialized = result.model_dump_json()
    assert current.controller_binding.value not in serialized
    assert (
        current.authority_provenance.source_reference.value
        not in serialized
    )
    assert resolver.calls == 1
    assert repository.requests == [_CHARACTER_ID]
    assert factory.calls == 1
    assert uow.commit_calls == 0
    assert events == [
        "resolve",
        "factory",
        "enter",
        "character-get",
        "exit:none",
    ]

    with pytest.raises(ValidationError):
        result.record_revision = PlayerCharacterRevision(value=99)


@pytest.mark.parametrize(
    "current",
    [
        None,
        _created_record(
            binding=ControllerBindingRef(value="binding.other")
        ),
    ],
)
async def test_get_owned_missing_and_wrong_owner_share_no_result(
    current: CanonicalPlayerCharacter | None,
) -> None:
    service, _, repository, uow, factory, events = _read_scope(current)

    result = await service.get_owned(
        _PRINCIPAL,
        player_character_id=_CHARACTER_ID,
    )

    assert result is None
    assert repository.requests == [_CHARACTER_ID]
    assert factory.calls == 1
    assert uow.commit_calls == 0
    assert events == [
        "resolve",
        "factory",
        "enter",
        "character-get",
        "exit:none",
    ]


@pytest.mark.parametrize(
    "resolved_binding",
    [
        None,
        ControllerBindingRef.model_construct(value="invalid binding"),
    ],
)
async def test_get_owned_invalid_controller_opens_no_uow(
    resolved_binding: Any,
) -> None:
    service, resolver, repository, uow, factory, events = _read_scope(
        _created_record(),
        resolved_binding=resolved_binding,
    )

    result = await service.get_owned(
        _PRINCIPAL,
        player_character_id=_CHARACTER_ID,
    )

    assert result is None
    assert resolver.calls == 1
    assert repository.requests == []
    assert factory.calls == 0
    assert uow.commit_calls == 0
    assert events == ["resolve"]


async def test_get_owned_revalidates_target_before_repository_access() -> None:
    service, _, repository, uow, factory, events = _read_scope(
        _created_record()
    )
    invalid_id = PlayerCharacterId.model_construct(value="invalid id")

    with pytest.raises(ValueError):
        await service.get_owned(
            _PRINCIPAL,
            player_character_id=invalid_id,
        )

    assert repository.requests == []
    assert factory.calls == 0
    assert uow.commit_calls == 0
    assert events == ["resolve"]


async def test_get_owned_rejects_invalid_or_mismatched_repository_state() -> None:
    initial = _created_record()
    corrupted = initial.model_copy(
        update={"record_revision": PlayerCharacterRevision(value=2)}
    )
    service, _, _, uow, _, _ = _read_scope(corrupted)

    with pytest.raises(ValueError):
        await service.get_owned(
            _PRINCIPAL,
            player_character_id=_CHARACTER_ID,
        )
    assert uow.commit_calls == 0

    mismatched = _created_record(
        player_character_id=PlayerCharacterId(value="pc.wrong")
    )
    service, _, _, uow, _, _ = _read_scope(mismatched)
    with pytest.raises(
        ValueError,
        match="read returned a mismatched identity",
    ):
        await service.get_owned(
            _PRINCIPAL,
            player_character_id=_CHARACTER_ID,
        )
    assert uow.commit_calls == 0


@pytest.mark.parametrize(
    ("repository_value", "enter_error", "exit_error", "expected"),
    [
        (RuntimeError("read failed"), None, None, "read failed"),
        (_created_record(), RuntimeError("enter failed"), None, "enter failed"),
        (_created_record(), None, RuntimeError("exit failed"), "exit failed"),
    ],
)
async def test_get_owned_propagates_repository_and_uow_failures(
    repository_value: Any,
    enter_error: BaseException | None,
    exit_error: BaseException | None,
    expected: str,
) -> None:
    service, _, _, uow, _, _ = _read_scope(
        repository_value,
        enter_error=enter_error,
        exit_error=exit_error,
    )

    with pytest.raises(RuntimeError, match=expected):
        await service.get_owned(
            _PRINCIPAL,
            player_character_id=_CHARACTER_ID,
        )

    assert uow.commit_calls == 0
