from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

import httpx
import pytest
from fastapi import Request

from deviation_protocol.api import main
from deviation_protocol.api.dependencies import (
    ApiServices,
    get_current_principal,
    get_player_character_service,
)
from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.player_character_projection import (
    PlayerCharacterSelfProjection,
)
from deviation_protocol.domain.player_character import (
    PlayerCharacterContractVersion,
    PlayerCharacterId,
    PlayerCharacterLifecycle,
    PlayerCharacterRevision,
)


_PRINCIPAL = RequestPrincipal(player_id="player.test", authentication_scheme="test")
_PATH = "/v1/player-characters/pc.test-owned"


@dataclass(frozen=True, slots=True)
class _Response:
    status_code: int
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body)

    @property
    def text(self) -> str:
        return self.body.decode("utf-8")


def _get(app: Any, path: str) -> _Response:
    async def request() -> _Response:
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            response = await client.get(path)
        return _Response(response.status_code, response.content)

    return asyncio.run(request())


class _PlayerCharacterService:
    def __init__(self, result: PlayerCharacterSelfProjection | None = None) -> None:
        self.result = result
        self.error: Exception | None = None
        self.calls: list[tuple[RequestPrincipal, PlayerCharacterId]] = []

    async def get_owned(
        self,
        principal: RequestPrincipal,
        *,
        player_character_id: PlayerCharacterId,
    ) -> PlayerCharacterSelfProjection | None:
        self.calls.append((principal, player_character_id))
        if self.error is not None:
            raise self.error
        return self.result


def _projection(lifecycle: PlayerCharacterLifecycle) -> PlayerCharacterSelfProjection:
    return PlayerCharacterSelfProjection(
        player_character_id=PlayerCharacterId(value="pc.test-owned"),
        contract_version=PlayerCharacterContractVersion.V1,
        record_revision=PlayerCharacterRevision(value=1),
        lifecycle=lifecycle,
    )


def _app(service: _PlayerCharacterService | None) -> Any:
    services = ApiServices(
        session_service=object(),  # type: ignore[arg-type]
        turn_orchestrator=object(),  # type: ignore[arg-type]
        player_character_service=service,  # type: ignore[arg-type]
    )
    app = main.create_app(services=services)
    app.state.api_services = services
    app.dependency_overrides[get_current_principal] = lambda: _PRINCIPAL
    return app


@pytest.mark.parametrize("lifecycle", tuple(PlayerCharacterLifecycle))
def test_owned_read_returns_exact_detached_projection(
    lifecycle: PlayerCharacterLifecycle,
) -> None:
    service = _PlayerCharacterService(_projection(lifecycle))

    response = _get(_app(service), _PATH)

    assert response.status_code == 200
    assert response.json() == {
        "player_character_id": {"value": "pc.test-owned"},
        "contract_version": "structured-player-character/v1",
        "record_revision": {"value": 1},
        "lifecycle": lifecycle.value,
    }
    assert service.calls == [(_PRINCIPAL, PlayerCharacterId(value="pc.test-owned"))]
    rendered = response.text.casefold()
    for private_name in (
        "controller_binding",
        "authority_provenance",
        "receipt",
        "repository",
        "unitofwork",
        "orm",
        "character_core",
        "narration_preferences",
        "run",
    ):
        assert private_name not in rendered


def test_absent_foreign_and_unmapped_reads_are_indistinguishable() -> None:
    responses = [_get(_app(_PlayerCharacterService()), _PATH) for _ in range(3)]

    assert [response.status_code for response in responses] == [404, 404, 404]
    assert [response.json() for response in responses] == [
        {
            "error": {
                "error_code": "PLAYER_CHARACTER_NOT_FOUND",
                "message": "Player character was not found",
            }
        }
    ] * 3


@pytest.mark.parametrize(
    "path",
    (
        "/v1/player-characters/invalid space",
        "/v1/player-characters/.not-an-id",
        "/v1/player-characters/" + "x" * 129,
    ),
)
def test_invalid_path_identifier_uses_the_standard_sanitized_422(path: str) -> None:
    service = _PlayerCharacterService()

    response = _get(_app(service), path)

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "error_code": "REQUEST_VALIDATION_FAILED",
            "message": "Request validation failed",
        }
    }
    assert service.calls == []


def test_path_boundaries_and_query_cannot_supply_authority() -> None:
    service = _PlayerCharacterService()
    app = _app(service)

    one = _get(app, "/v1/player-characters/a?player_id=other")
    maximum = _get(app, "/v1/player-characters/" + "x" * 128)

    assert one.status_code == maximum.status_code == 404
    assert service.calls == [
        (_PRINCIPAL, PlayerCharacterId(value="a")),
        (_PRINCIPAL, PlayerCharacterId(value="x" * 128)),
    ]


@pytest.mark.parametrize("error", (ValueError("corrupt record"), RuntimeError("mysql secret")))
def test_read_failures_are_sanitized_without_internal_detail(error: Exception) -> None:
    service = _PlayerCharacterService()
    service.error = error

    response = _get(_app(service), _PATH)

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "Internal server error",
        }
    }
    assert "corrupt" not in response.text
    assert "mysql" not in response.text


def test_dependency_fails_closed_when_service_is_not_composed() -> None:
    app = _app(None)
    request = Request({"type": "http", "app": app})

    with pytest.raises(RuntimeError, match="not configured"):
        get_player_character_service(request)
    assert _PATH.removeprefix("/v1") not in app.openapi()["paths"]


def test_normal_openapi_declares_only_the_safe_owned_read_contract() -> None:
    schema = _app(_PlayerCharacterService()).openapi()
    operation = schema["paths"]["/v1/player-characters/{player_character_id}"]["get"]

    parameter = operation["parameters"][0]
    assert operation["tags"] == ["player-characters"]
    assert parameter == {
        "name": "player_character_id",
        "in": "path",
        "required": True,
        "schema": {
            "type": "string",
            "minLength": 1,
            "maxLength": 128,
            "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$",
            "title": "Player Character Id",
        },
    }
    assert "requestBody" not in operation
    assert set(operation["responses"]) == {"200", "404", "422", "500"}
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/PlayerCharacterSelfProjection"
    }
    assert all(
        operation["responses"][status]["content"]["application/json"]["schema"]
        == {"$ref": "#/components/schemas/ErrorResponse"}
        for status in ("404", "422", "500")
    )
    rendered = json.dumps(schema).casefold()
    for forbidden in (
        "canonicalplayercharacter",
        "controllerbindingref",
        "authorityprovenance",
        "sqlalchemy",
        "receipt",
    ):
        assert forbidden not in rendered
