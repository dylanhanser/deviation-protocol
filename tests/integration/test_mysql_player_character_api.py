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
)
from deviation_protocol.application.player_character_service import (
    PlayerCharacterService,
)
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
)
from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from deviation_protocol.infrastructure.repositories import SqlAlchemyControllerBindingRegistryRepository


pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_NOW = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)


@dataclass(slots=True)
class _Scope:
    token: str
    character_ids: set[str] = field(default_factory=set)
    bindings: set[str] = field(default_factory=set)


@pytest.fixture
async def player_character_api_scope(
    mysql_session_factory: async_sessionmaker[AsyncSession],
):
    scope = _Scope(token=uuid4().hex)
    try:
        yield scope
    finally:
        async with mysql_session_factory.begin() as session:
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
) -> PlayerCharacterService:
    return PlayerCharacterService(
        uow_factory=lambda: SqlAlchemyUnitOfWork(session_factory),
        controller_binding_resolver=_Resolver(binding),
        player_character_id_issuer=_Issuer(player_character_id),
        create_policy=CreatePlayerCharacterPolicy(),
        source_reference=AuthoritySourceRef(value="source.mysql-api"),
        clock=lambda: _NOW,
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
