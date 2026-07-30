from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
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
