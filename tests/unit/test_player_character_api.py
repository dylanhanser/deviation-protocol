from __future__ import annotations

import asyncio
from copy import deepcopy
import json
from dataclasses import dataclass
import inspect
from typing import Any

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from pydantic import ValidationError

from deviation_protocol.api import main
from deviation_protocol.api.dependencies import (
    ApiServices,
    get_current_principal,
    get_player_character_service,
)
from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.player_character_operations import (
    CREATION_RESULT_SCHEMA_VERSION,
    CharacterCreationCommand,
    CharacterMutationCommand,
    CharacterOperationNamespace,
    CharacterOperationProtocolCode,
    CharacterOperationProtocolDecision,
    CreationSuccessResult,
    MUTATION_RESULT_SCHEMA_VERSION,
    MutationCommandResult,
    MutationSuccessResult,
)
from deviation_protocol.application.player_character_projection import (
    EligiblePlayerCharacterCollection,
    PlayerCharacterSelfProjection,
)
from deviation_protocol.domain.player_character import (
    CharacterCore,
    NarrationPreferences,
    PlayerCharacterContractVersion,
    PlayerCharacterId,
    PlayerCharacterLifecycle,
    PlayerCharacterMutationKind,
    PlayerCharacterOperationId,
    PlayerCharacterRevision,
)
from deviation_protocol.domain.player_character_policies import (
    PlayerCharacterPolicyCode,
    PlayerCharacterPolicyDecision,
)


_PRINCIPAL = RequestPrincipal(player_id="player.test", authentication_scheme="test")
_PATH = "/v1/player-characters/pc.test-owned"
_CREATE_PATH = "/v1/player-characters"
_RETIREMENT_PATH = "/v1/player-characters/pc.test-owned/retirement"
_ELIGIBLE_PATH = "/v1/player-characters/eligible-for-run-entry"
_VALID_KEY = "Create.Key:Case-1"
_UNSET = object()


@dataclass(frozen=True, slots=True)
class _Response:
    status_code: int
    body: bytes
    headers: httpx.Headers

    def json(self) -> Any:
        return json.loads(self.body)

    @property
    def text(self) -> str:
        return self.body.decode("utf-8")


async def _request_async(
    app: Any,
    method: str,
    path: str,
    *,
    json_body: Any = _UNSET,
    content: bytes | str | None = None,
    headers: Any = None,
    raise_app_exceptions: bool = False,
) -> httpx.Response:
    transport = httpx.ASGITransport(
        app=app,
        raise_app_exceptions=raise_app_exceptions,
    )
    request_options: dict[str, Any] = {"headers": headers}
    if json_body is not _UNSET:
        request_options["json"] = json_body
    if content is not None:
        request_options["content"] = content
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        return await client.request(method, path, **request_options)


def _request(
    app: Any,
    method: str,
    path: str,
    **kwargs: Any,
) -> _Response:
    async def request() -> _Response:
        response = await _request_async(app, method, path, **kwargs)
        return _Response(response.status_code, response.content, response.headers)

    return asyncio.run(request())


def _get(app: Any, path: str) -> _Response:
    return _request(app, "GET", path)


def _post(
    app: Any,
    *,
    json_body: Any = _UNSET,
    content: bytes | str | None = None,
    headers: Any = None,
    path: str = _CREATE_PATH,
) -> _Response:
    return _request(
        app,
        "POST",
        path,
        json_body=json_body,
        content=content,
        headers=headers,
    )


async def _raw_asgi_request(
    app: Any,
    *,
    headers: list[tuple[bytes, bytes]],
    body: bytes,
    path: str = _CREATE_PATH,
    events: list[str] | None = None,
) -> _Response:
    request_sent = False
    response_start: dict[str, Any] | None = None
    response_body = bytearray()

    async def receive() -> dict[str, Any]:
        nonlocal request_sent
        if events is not None:
            events.append("body-receive")
        if request_sent:
            return {"type": "http.disconnect"}
        request_sent = True
        return {
            "type": "http.request",
            "body": body,
            "more_body": False,
        }

    async def send(message: dict[str, Any]) -> None:
        nonlocal response_start
        if message["type"] == "http.response.start":
            response_start = message
        elif message["type"] == "http.response.body":
            response_body.extend(message.get("body", b""))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "headers": headers,
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "root_path": "",
    }
    await app(scope, receive, send)
    assert response_start is not None
    return _Response(
        response_start["status"],
        bytes(response_body),
        httpx.Headers(response_start["headers"]),
    )


def _creation_route(app: FastAPI) -> APIRoute:
    return next(
        route
        for route in app.routes
        if isinstance(route, APIRoute)
        and route.path == _CREATE_PATH
        and route.methods == {"POST"}
    )


def _retirement_route(app: FastAPI) -> APIRoute:
    return next(
        route
        for route in app.routes
        if isinstance(route, APIRoute)
        and route.path == "/v1/player-characters/{player_character_id}/retirement"
        and route.methods == {"POST"}
    )


def _mark_creation_route_entry(app: FastAPI, events: list[str]) -> None:
    route = _creation_route(app)
    original_endpoint = route.dependant.call
    assert original_endpoint is not None

    async def traced_endpoint(**values: Any) -> Any:
        events.append("route")
        return await original_endpoint(**values)

    route.endpoint = traced_endpoint
    route.dependant.call = traced_endpoint


def _mark_retirement_route_entry(app: FastAPI, events: list[str]) -> None:
    route = _retirement_route(app)
    original_endpoint = route.dependant.call
    assert original_endpoint is not None

    async def traced_endpoint(**values: Any) -> Any:
        events.append("route")
        return await original_endpoint(**values)

    route.endpoint = traced_endpoint
    route.dependant.call = traced_endpoint


def _generated_creation_components() -> dict[str, dict[str, Any]]:
    root = CharacterCreationCommand.model_json_schema(
        mode="validation",
        ref_template="#/components/schemas/{model}",
    )
    definitions = root.pop("$defs")
    return {"CharacterCreationCommand": root, **definitions}


def _assert_all_local_refs_resolve(schema: dict[str, Any]) -> None:
    pending: list[Any] = [schema]
    while pending:
        current = pending.pop()
        if isinstance(current, dict):
            for key, value in current.items():
                if key != "$ref":
                    pending.append(value)
                    continue
                assert isinstance(value, str)
                assert value.startswith("#/")
                target: Any = schema
                for encoded_part in value[2:].split("/"):
                    part = encoded_part.replace("~1", "/").replace("~0", "~")
                    if isinstance(target, dict):
                        target = target[part]
                    else:
                        assert isinstance(target, list)
                        target = target[int(part)]
        elif isinstance(current, list):
            pending.extend(current)


class _PlayerCharacterService:
    def __init__(
        self,
        result: PlayerCharacterSelfProjection | None = None,
        *,
        creation_result: Any = None,
    ) -> None:
        self.result = result
        self.creation_result = creation_result
        self.error: BaseException | None = None
        self.creation_error: BaseException | None = None
        self.calls: list[tuple[RequestPrincipal, PlayerCharacterId]] = []
        self.creation_calls: list[
            tuple[
                RequestPrincipal,
                PlayerCharacterOperationId,
                CharacterCreationCommand,
            ]
        ] = []
        self.mutation_result: Any = None
        self.mutation_error: BaseException | None = None
        self.mutation_calls: list[
            tuple[RequestPrincipal, PlayerCharacterOperationId, CharacterMutationCommand]
        ] = []
        self.eligible_result: Any = EligiblePlayerCharacterCollection(
            eligible_player_characters=(), truncated=False
        )
        self.eligible_error: BaseException | None = None
        self.eligible_calls: list[RequestPrincipal] = []

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

    async def list_eligible_for_run_entry(
        self,
        principal: RequestPrincipal,
    ) -> Any:
        self.eligible_calls.append(principal)
        if self.eligible_error is not None:
            raise self.eligible_error
        return self.eligible_result


    async def create(
        self,
        principal: RequestPrincipal,
        *,
        operation_id: PlayerCharacterOperationId,
        command: CharacterCreationCommand,
    ) -> Any:
        self.creation_calls.append((principal, operation_id, command))
        if self.creation_error is not None:
            raise self.creation_error
        return self.creation_result

    async def mutate(
        self,
        principal: RequestPrincipal,
        *,
        operation_id: PlayerCharacterOperationId,
        command: CharacterMutationCommand,
    ) -> Any:
        self.mutation_calls.append((principal, operation_id, command))
        if self.mutation_error is not None:
            raise self.mutation_error
        return self.mutation_result


def _projection(lifecycle: PlayerCharacterLifecycle) -> PlayerCharacterSelfProjection:
    return PlayerCharacterSelfProjection(
        player_character_id=PlayerCharacterId(value="pc.test-owned"),
        contract_version=PlayerCharacterContractVersion.V1,
        record_revision=PlayerCharacterRevision(value=1),
        lifecycle=lifecycle,
    )


def _creation_success() -> CreationSuccessResult:
    return CreationSuccessResult(
        result_schema_version=CREATION_RESULT_SCHEMA_VERSION,
        player_character_id=PlayerCharacterId(value="pc.created"),
        contract_version=PlayerCharacterContractVersion.V1,
        resulting_revision=PlayerCharacterRevision(value=1),
        resulting_lifecycle=PlayerCharacterLifecycle.ACTIVE,
    )


def _retirement_success() -> MutationSuccessResult:
    return MutationSuccessResult(
        result_schema_version=MUTATION_RESULT_SCHEMA_VERSION,
        player_character_id=PlayerCharacterId(value="pc.test-owned"),
        contract_version=PlayerCharacterContractVersion.V1,
        command_kind=PlayerCharacterMutationKind.RETIRE,
        command_result=MutationCommandResult.RETIRED,
        resulting_revision=PlayerCharacterRevision(value=2),
        resulting_lifecycle=PlayerCharacterLifecycle.RETIRED,
    )


def _retirement_body(revision: int = 1) -> dict[str, Any]:
    return {
        "contract_version": "structured-player-character/v1",
        "expected_revision": {"value": revision},
        "confirm_retirement": True,
    }


def _mutated_retirement_success(**changes: Any) -> MutationSuccessResult:
    """Construct an otherwise typed result whose actual state crosses the API seam."""

    result = _retirement_success()
    for name, value in changes.items():
        object.__setattr__(result, name, value)
    return result


def _minimal_creation_body() -> dict[str, Any]:
    return {
        "contract_version": "structured-player-character/v1",
        "character_core": {},
        "narration_preferences": {},
    }


def _full_creation_body() -> dict[str, Any]:
    declared_text = {
        "authority": "player-expression",
        "text": "A declared value",
    }
    return {
        "contract_version": "structured-player-character/v1",
        "character_core": {
            "name_or_code_name": {
                "state": "declared",
                "value": declared_text,
            },
            "preferred_form_of_address": {
                "state": "explicitly-absent",
                "value": None,
            },
            "adult_identity_and_gender_expression": {
                "state": "intentionally-undecided",
                "value": None,
            },
            "broad_adult_age_presentation": {
                "state": "declared",
                "value": {"adult_only": True},
            },
            "broad_appearance_direction": {
                "state": "declared",
                "value": {
                    "authority": "player-confirmation",
                    "text": "Practical",
                },
            },
            "distinguishing_features": {
                "state": "declared",
                "value": {
                    "features": [
                        {
                            "authority": "player-expression",
                            "text": "Silver streak",
                        },
                        {
                            "authority": "player-confirmation",
                            "text": "Measured posture",
                        },
                    ]
                },
            },
            "outward_presentation": {
                "state": "omitted",
                "value": None,
            },
            "inward_tendency": {
                "state": "declared",
                "value": declared_text,
            },
            "reality_anchor": {
                "state": "declared",
                "value": declared_text,
            },
            "custom_values": {
                "state": "declared",
                "value": {
                    "entries": [
                        {
                            "key": "manner",
                            "declaration": {
                                "state": "declared",
                                "value": declared_text,
                            },
                        },
                        {
                            "key": "boundary",
                            "declaration": {
                                "state": "intentionally-undecided",
                                "value": None,
                            },
                        },
                    ]
                },
            },
        },
        "narration_preferences": {
            "internal_thoughts": {
                "state": "declared",
                "value": {
                    "authority": "player-confirmation",
                    "value": "high-agency",
                },
            }
        },
    }


def _valid_headers(
    key: str | bytes = _VALID_KEY,
    *,
    content_type: str | bytes = "application/json",
) -> list[tuple[str | bytes, str | bytes]]:
    return [
        ("Content-Type", content_type),
        ("Idempotency-Key", key),
    ]


def _assert_error(response: _Response, status_code: int, code: str, message: str) -> None:
    assert response.status_code == status_code
    assert response.json() == {
        "error": {
            "error_code": code,
            "message": message,
        }
    }


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


def test_create_first_success_has_exact_public_projection_and_single_call() -> None:
    success = _creation_success()
    service = _PlayerCharacterService(creation_result=success)
    body = _minimal_creation_body()

    response = _post(
        _app(service),
        json_body=body,
        headers=_valid_headers(),
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert "location" not in response.headers
    assert response.json() == {
        "player_character_id": {"value": "pc.created"},
        "contract_version": "structured-player-character/v1",
        "record_revision": {"value": 1},
        "lifecycle": "active",
    }
    assert set(response.json()) == {
        "player_character_id",
        "contract_version",
        "record_revision",
        "lifecycle",
    }
    assert service.creation_calls == [
        (
            _PRINCIPAL,
            PlayerCharacterOperationId(value=_VALID_KEY),
            CharacterCreationCommand(
                contract_version=PlayerCharacterContractVersion.V1,
                character_core=CharacterCore(),
                narration_preferences=NarrationPreferences(),
            ),
        )
    ]


def test_create_and_exact_replay_have_identical_public_semantics() -> None:
    service = _PlayerCharacterService(creation_result=_creation_success())
    app = _app(service)

    first = _post(
        app,
        json_body=_minimal_creation_body(),
        headers=_valid_headers(),
    )
    replay = _post(
        app,
        json_body=_minimal_creation_body(),
        headers=_valid_headers(),
    )

    assert first.status_code == replay.status_code == 200
    assert first.body == replay.body
    assert first.headers["content-type"] == replay.headers["content-type"]
    assert "location" not in first.headers
    assert "location" not in replay.headers
    assert "replay" not in first.text.casefold()
    assert len(service.creation_calls) == 2
    assert service.creation_calls[0] == service.creation_calls[1]


def test_retirement_success_binds_the_exact_command_and_projects_only_safe_fields() -> None:
    service = _PlayerCharacterService()
    service.mutation_result = _retirement_success()

    response = _post(
        _app(service),
        path=_RETIREMENT_PATH,
        json_body=_retirement_body(),
        headers=_valid_headers(),
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {
        "player_character_id": {"value": "pc.test-owned"},
        "contract_version": "structured-player-character/v1",
        "record_revision": {"value": 2},
        "lifecycle": "retired",
    }
    assert len(service.mutation_calls) == 1
    principal, operation_id, command = service.mutation_calls[0]
    assert principal == _PRINCIPAL
    assert operation_id == PlayerCharacterOperationId(value=_VALID_KEY)
    assert command.command_kind is PlayerCharacterMutationKind.RETIRE
    assert command.target_player_character_id == PlayerCharacterId(value="pc.test-owned")
    assert command.confirmation is not None
    assert command.confirmation.source_reference == main._PUBLIC_RETIREMENT_SOURCE_REFERENCE


def test_retirement_request_model_rejects_json_numeric_confirmation_before_literal_coercion() -> None:
    for confirmation in (b"1", b"1.0", b"0", b"-1", b'"true"', b'"1"', b"[]", b"{}", b"null", b"false"):
        raw = (
            b'{"contract_version":"structured-player-character/v1",'
            b'"expected_revision":{"value":1},"confirm_retirement":'
            + confirmation
            + b"}"
        )
        with pytest.raises(ValidationError):
            main.PlayerCharacterRetirementRequest.model_validate_json(raw)

    parsed = main.PlayerCharacterRetirementRequest.model_validate_json(
        b'{"contract_version":"structured-player-character/v1",'
        b'"expected_revision":{"value":1},"confirm_retirement":true}'
    )
    assert parsed.confirm_retirement is True


@pytest.mark.parametrize("confirmation", (1, 1.0, 2, 2.5))
def test_retirement_request_model_rejects_python_numeric_confirmation_before_coercion(
    confirmation: int | float,
) -> None:
    body: dict[str, Any] = {
        "contract_version": PlayerCharacterContractVersion.V1,
        "expected_revision": PlayerCharacterRevision(value=1),
        "confirm_retirement": True,
    }
    body["confirm_retirement"] = confirmation

    with pytest.raises(ValidationError):
        main.PlayerCharacterRetirementRequest.model_validate(body)


@pytest.mark.parametrize(
    ("confirmation", "accepted"),
    (
        (True, True),
        (False, False),
        (None, False),
        (_UNSET, False),
        ("true", False),
        ("false", False),
        ([], False),
        ([True], False),
        ({}, False),
        ({"value": True}, False),
        (1, False),
        (1.0, False),
        (2, False),
        (-7, False),
        (2.5, False),
        (-0.5, False),
    ),
    ids=(
        "literal-true",
        "literal-false",
        "null",
        "missing",
        "string-true",
        "string-false",
        "empty-array",
        "nonempty-array",
        "empty-object",
        "nonempty-object",
        "integer-one",
        "float-one",
        "other-positive-integer",
        "other-negative-integer",
        "other-positive-float",
        "other-negative-float",
    ),
)
def test_retirement_request_model_literal_confirmation_matrix_is_complete(
    confirmation: Any,
    accepted: bool,
) -> None:
    body: dict[str, Any] = {
        "contract_version": PlayerCharacterContractVersion.V1,
        "expected_revision": PlayerCharacterRevision(value=1),
        "confirm_retirement": True,
    }
    if confirmation is _UNSET:
        del body["confirm_retirement"]
    else:
        body["confirm_retirement"] = confirmation

    if accepted:
        parsed = main.PlayerCharacterRetirementRequest.model_validate(body)
        assert parsed.confirm_retirement is True
    else:
        with pytest.raises(ValidationError):
            main.PlayerCharacterRetirementRequest.model_validate(body)


@pytest.mark.parametrize(
    ("confirmation", "accepted"),
    (
        (b"true", True),
        (b"false", False),
        (b"null", False),
        (None, False),
        (b'"true"', False),
        (b'"false"', False),
        (b"[]", False),
        (b"[true]", False),
        (b"{}", False),
        (b'{"value":true}', False),
        (b"1", False),
        (b"1.0", False),
        (b"2", False),
        (b"-7", False),
        (b"2.5", False),
        (b"-0.5", False),
    ),
    ids=(
        "literal-true",
        "literal-false",
        "null",
        "missing",
        "string-true",
        "string-false",
        "empty-array",
        "nonempty-array",
        "empty-object",
        "nonempty-object",
        "integer-one",
        "float-one",
        "other-positive-integer",
        "other-negative-integer",
        "other-positive-float",
        "other-negative-float",
    ),
)
def test_retirement_http_literal_confirmation_matrix_precedes_mutation(
    confirmation: bytes | None,
    accepted: bool,
) -> None:
    service = _PlayerCharacterService()
    service.mutation_result = _retirement_success()
    member = (
        b""
        if confirmation is None
        else b',"confirm_retirement":' + confirmation
    )
    raw = (
        b'{"contract_version":"structured-player-character/v1",'
        b'"expected_revision":{"value":1}' + member + b"}"
    )

    response = _post(
        _app(service),
        path=_RETIREMENT_PATH,
        content=raw,
        headers=_valid_headers(),
    )

    if accepted:
        assert response.status_code == 200
        assert len(service.mutation_calls) == 1
    else:
        _assert_error(
            response,
            422,
            "REQUEST_VALIDATION_FAILED",
            "Request validation failed",
        )
        assert service.mutation_calls == []


@pytest.mark.parametrize(
    "result",
    (
        MutationSuccessResult(
            result_schema_version=MUTATION_RESULT_SCHEMA_VERSION,
            player_character_id=PlayerCharacterId(value="pc.someone-else"),
            contract_version=PlayerCharacterContractVersion.V1,
            command_kind=PlayerCharacterMutationKind.RETIRE,
            command_result=MutationCommandResult.RETIRED,
            resulting_revision=PlayerCharacterRevision(value=2),
            resulting_lifecycle=PlayerCharacterLifecycle.RETIRED,
        ),
        _mutated_retirement_success(contract_version="not-a-contract"),
        _mutated_retirement_success(resulting_revision=PlayerCharacterRevision(value=1)),
        _mutated_retirement_success(resulting_revision=PlayerCharacterRevision(value=3)),
        _mutated_retirement_success(resulting_lifecycle=PlayerCharacterLifecycle.ACTIVE),
        MutationSuccessResult(
            result_schema_version=MUTATION_RESULT_SCHEMA_VERSION,
            player_character_id=PlayerCharacterId(value="pc.test-owned"),
            contract_version=PlayerCharacterContractVersion.V1,
            command_kind=PlayerCharacterMutationKind.FINAL_DEATH,
            command_result=MutationCommandResult.DECEASED,
            resulting_revision=PlayerCharacterRevision(value=2),
            resulting_lifecycle=PlayerCharacterLifecycle.DECEASED,
        ),
    ),
    ids=(
        "other-character",
        "malformed-contract",
        "unchanged-revision",
        "skipped-revision",
        "active-lifecycle",
        "wrong-command-kind",
    ),
)
def test_retirement_impossible_success_result_is_sanitized_and_not_retried(
    result: MutationSuccessResult,
) -> None:
    service = _PlayerCharacterService()
    service.mutation_result = result

    response = _post(
        _app(service),
        path=_RETIREMENT_PATH,
        json_body=_retirement_body(),
        headers=_valid_headers(),
    )

    _assert_error(response, 500, "INTERNAL_SERVER_ERROR", "Internal server error")
    assert len(service.mutation_calls) == 1
    assert service.calls == []
    assert service.creation_calls == []


def test_retirement_malformed_constructed_success_result_is_sanitized_and_not_retried() -> None:
    malformed = object.__new__(MutationSuccessResult)
    service = _PlayerCharacterService()
    service.mutation_result = malformed

    response = _post(
        _app(service),
        path=_RETIREMENT_PATH,
        json_body=_retirement_body(),
        headers=_valid_headers(),
    )

    _assert_error(response, 500, "INTERNAL_SERVER_ERROR", "Internal server error")
    assert len(service.mutation_calls) == 1
    assert service.calls == []
    assert service.creation_calls == []


def test_retirement_exact_replay_result_is_projected_when_bound_to_the_same_command() -> None:
    service = _PlayerCharacterService()
    service.mutation_result = _retirement_success()
    app = _app(service)

    first = _post(app, path=_RETIREMENT_PATH, json_body=_retirement_body(), headers=_valid_headers())
    replay = _post(app, path=_RETIREMENT_PATH, json_body=_retirement_body(), headers=_valid_headers())

    assert first.status_code == replay.status_code == 200
    assert replay.body == first.body
    assert len(service.mutation_calls) == 2


@pytest.mark.parametrize(
    "content",
    (
        b"",
        b"null",
        b'{"contract_version":"structured-player-character/v1","expected_revision":{"value":1},"confirm_retirement":false}',
        b'{"contract_version":"structured-player-character/v1","expected_revision":{"value":1},"confirm_retirement":true,"unexpected":1}',
        b'{"contract_version":"structured-player-character/v1","expected_revision":{"value":1,"value":1},"confirm_retirement":true}',
        b'{"contract_version":"structured-player-character/v1","expected_revision":{"value":1},"confirm_retirement":true,"confirm_retirement":true}',
    ),
)
def test_retirement_strict_body_validation_fails_before_mutate(content: bytes) -> None:
    service = _PlayerCharacterService()
    response = _post(
        _app(service),
        path=_RETIREMENT_PATH,
        content=content,
        headers=_valid_headers(),
    )

    _assert_error(response, 422, "REQUEST_VALIDATION_FAILED", "Request validation failed")
    assert service.mutation_calls == []


@pytest.mark.parametrize(
    "content",
    (
        b'{"expected_revision":{"value":1},"confirm_retirement":true}',
        b'{"contract_version":"structured-player-character/v1","confirm_retirement":true}',
        b'{"contract_version":"structured-player-character/v1","expected_revision":1,"confirm_retirement":true}',
        b'{"contract_version":"structured-player-character/v1","expected_revision":{"extra":1,"value":1},"confirm_retirement":true}',
        b'{"contract_version":"structured-player-character/v1","expected_revision":{"value":true},"confirm_retirement":true}',
        b'{"contract_version":"structured-player-character/v1","expected_revision":{"value":0},"confirm_retirement":true}',
        b'{"contract_version":"structured-player-character/v1","expected_revision":{"value":1.0},"confirm_retirement":true}',
        b'{"contract_version":"structured-player-character/v2","expected_revision":{"value":1},"confirm_retirement":true}',
    ),
)
def test_retirement_complete_contract_and_revision_shape_fail_before_mutate(content: bytes) -> None:
    service = _PlayerCharacterService()
    response = _post(_app(service), path=_RETIREMENT_PATH, content=content, headers=_valid_headers())

    _assert_error(response, 422, "REQUEST_VALIDATION_FAILED", "Request validation failed")
    assert service.mutation_calls == []


@pytest.mark.asyncio
async def test_retirement_raw_transport_header_matrix_precedes_body_and_mutate() -> None:
    body = json.dumps(_retirement_body(), separators=(",", ":")).encode()
    valid_content_type = (b"content-type", b"application/json")
    valid_key = (b"idempotency-key", _VALID_KEY.encode("ascii"))
    invalid_headers = (
        ("content-type-missing", [valid_key]),
        ("content-type-empty", [(b"content-type", b""), valid_key]),
        (
            "content-type-duplicate-occurrences",
            [valid_content_type, valid_content_type, valid_key],
        ),
        (
            "content-type-combined-values",
            [(b"content-type", b"application/json,application/json"), valid_key],
        ),
        (
            "content-type-invalid-media-type",
            [(b"content-type", b"text/plain"), valid_key],
        ),
        (
            "content-type-combined-mixed-values",
            [(b"content-type", b"application/json, text/plain"), valid_key],
        ),
        (
            "content-type-malformed-token",
            [(b"content-type", b"application /json"), valid_key],
        ),
        (
            "content-type-non-ascii-token",
            [(b"content-type", b"\xff"), valid_key],
        ),
        (
            "content-type-non-ascii-parameter",
            [(b"content-type", b"application/json;\xff"), valid_key],
        ),
        ("idempotency-key-missing", [valid_content_type]),
        (
            "idempotency-key-empty",
            [valid_content_type, (b"idempotency-key", b"")],
        ),
        (
            "idempotency-key-duplicate-occurrences",
            [valid_content_type, valid_key, (b"idempotency-key", b"other")],
        ),
        (
            "idempotency-key-combined-values",
            [valid_content_type, (b"idempotency-key", _VALID_KEY.encode() + b",other")],
        ),
        (
            "idempotency-key-malformed-space",
            [valid_content_type, (b"idempotency-key", b"bad key")],
        ),
        (
            "idempotency-key-invalid-leading-character",
            [valid_content_type, (b"idempotency-key", b".leading")],
        ),
        (
            "idempotency-key-non-ascii",
            [valid_content_type, (b"idempotency-key", b"\xff")],
        ),
        (
            "idempotency-key-overlength",
            [valid_content_type, (b"idempotency-key", b"a" * 129)],
        ),
        (
            "idempotency-key-wrong-namespace-syntax",
            [valid_content_type, (b"idempotency-key", b"player-character.create/v1")],
        ),
    )
    for case_id, headers in invalid_headers:
        service = _PlayerCharacterService()
        body_events: list[str] = []
        response = await _raw_asgi_request(
            _app(service),
            headers=headers,
            body=body,
            path=_RETIREMENT_PATH,
            events=body_events,
        )
        _assert_error(response, 422, "REQUEST_VALIDATION_FAILED", "Request validation failed")
        assert service.mutation_calls == [], case_id
        assert body_events == [], case_id

    # Parameters are deliberately opaque under the frozen P5-S2 contract; the
    # raw media-type token before the first semicolon is the only authority.
    for content_type, operation_id in (
        (b"application/json", _VALID_KEY.encode("ascii")),
        (b"application/json", b"A" * 128),
        (b"application/json", b"A.z_9:-case"),
        (b"Application/Json; charset=utf-8", _VALID_KEY.encode("ascii")),
        (b" application/json\t; charset=utf-8", _VALID_KEY.encode("ascii")),
        (b"application/json; =", _VALID_KEY.encode("ascii")),
        (b"application/json; charset", _VALID_KEY.encode("ascii")),
        (b"application/json; ; malformed", _VALID_KEY.encode("ascii")),
    ):
        valid_service = _PlayerCharacterService()
        valid_service.mutation_result = _retirement_success()
        body_events = []
        response = await _raw_asgi_request(
            _app(valid_service),
            headers=[
                (b"content-type", content_type),
                (b"idempotency-key", operation_id),
            ],
            body=body,
            path=_RETIREMENT_PATH,
            events=body_events,
        )
        assert response.status_code == 200
        assert len(valid_service.mutation_calls) == 1
        assert body_events == ["body-receive"]


@pytest.mark.parametrize(
    ("path", "status_code"),
    (
        ("/v1/player-characters//retirement", 422),
        ("/v1/player-characters/.leading-dot/retirement", 422),
        ("/v1/player-characters/pc%20space/retirement", 422),
        ("/v1/player-characters/pc%E2%98%83/retirement", 422),
        ("/v1/player-characters/" + "p" * 129 + "/retirement", 422),
    ),
)
def test_retirement_invalid_path_never_reaches_mutate(path: str, status_code: int) -> None:
    service = _PlayerCharacterService()
    response = _post(_app(service), path=path, json_body=_retirement_body(), headers=_valid_headers())
    _assert_error(response, status_code, "REQUEST_VALIDATION_FAILED", "Request validation failed")
    assert service.mutation_calls == []


def test_empty_retirement_identifier_is_sanitized_without_a_public_route() -> None:
    service = _PlayerCharacterService()
    app = _app(service)

    empty = _post(
        app,
        path="/v1/player-characters//retirement",
        json_body=_retirement_body(),
        headers=_valid_headers(),
    )
    unrelated = _post(
        app,
        path="/v1/unrelated-missing-route",
        json_body=_retirement_body(),
        headers=_valid_headers(),
    )

    _assert_error(empty, 422, "REQUEST_VALIDATION_FAILED", "Request validation failed")
    assert unrelated.status_code == 404
    assert unrelated.json() == {"detail": "Not Found"}
    assert all(
        not isinstance(route, APIRoute)
        or route.path != "/v1/player-characters//retirement"
        for route in app.routes
    )
    assert "/v1/player-characters//retirement" not in app.openapi()["paths"]
    assert service.mutation_calls == []


def test_retirement_path_boundary_is_preserved_without_normalization() -> None:
    identifier = "p" + "a" * 127
    service = _PlayerCharacterService()
    service.mutation_result = MutationSuccessResult(
        result_schema_version=MUTATION_RESULT_SCHEMA_VERSION,
        player_character_id=PlayerCharacterId(value=identifier),
        contract_version=PlayerCharacterContractVersion.V1,
        command_kind=PlayerCharacterMutationKind.RETIRE,
        command_result=MutationCommandResult.RETIRED,
        resulting_revision=PlayerCharacterRevision(value=2),
        resulting_lifecycle=PlayerCharacterLifecycle.RETIRED,
    )
    response = _post(
        _app(service),
        path=f"/v1/player-characters/{identifier}/retirement",
        json_body=_retirement_body(),
        headers=_valid_headers(),
    )
    assert response.status_code == 200
    assert service.mutation_calls[0][2].target_player_character_id.value == identifier


@pytest.mark.parametrize(
    ("decision", "code", "message"),
    (
        (
            CharacterOperationProtocolDecision(
                operation_namespace=CharacterOperationNamespace.MUTATE_V1,
                code=CharacterOperationProtocolCode.AUTHORIZATION_FAILED,
            ),
            "PLAYER_CHARACTER_NOT_FOUND",
            "Player character was not found",
        ),
        (
            CharacterOperationProtocolDecision(
                operation_namespace=CharacterOperationNamespace.MUTATE_V1,
                code=CharacterOperationProtocolCode.REVISION_EXHAUSTED,
            ),
            "PLAYER_CHARACTER_REVISION_CONFLICT",
            "Player character revision does not permit retirement",
        ),
        (
            CharacterOperationProtocolDecision(
                operation_namespace=CharacterOperationNamespace.MUTATE_V1,
                code=CharacterOperationProtocolCode.IDEMPOTENCY_CONFLICT,
            ),
            "IDEMPOTENCY_CONFLICT",
            "Idempotency key was reused",
        ),
        (
            PlayerCharacterPolicyDecision(
                code=PlayerCharacterPolicyCode.INVALID_TRANSITION,
            ),
            "PLAYER_CHARACTER_LIFECYCLE_CONFLICT",
            "Player character cannot be retired",
        ),
        (
            PlayerCharacterPolicyDecision(
                code=(
                    PlayerCharacterPolicyCode.ACTIVE_BINDING_ATOMIC_LIFECYCLE_TRANSITION_REQUIRED
                ),
            ),
            "PLAYER_CHARACTER_ACTIVE_BINDING_CONFLICT",
            "Player character is bound to an active Run",
        ),
    ),
)
def test_retirement_safe_decision_mappings(
    decision: Any,
    code: str,
    message: str,
) -> None:
    service = _PlayerCharacterService()
    service.mutation_result = decision
    response = _post(
        _app(service),
        path=_RETIREMENT_PATH,
        json_body=_retirement_body(9223372036854775807),
        headers=_valid_headers(),
    )

    _assert_error(response, 404 if code.endswith("NOT_FOUND") else 409, code, message)
    assert len(service.mutation_calls) == 1


@pytest.mark.parametrize(
    "decision",
    (
        CharacterOperationProtocolDecision(
            operation_namespace=CharacterOperationNamespace.MUTATE_V1,
            code=CharacterOperationProtocolCode.STORED_RECEIPT_INTEGRITY_FAILURE,
        ),
        CharacterOperationProtocolDecision(
            operation_namespace=CharacterOperationNamespace.CREATE_V1,
            code=CharacterOperationProtocolCode.AUTHORIZATION_FAILED,
        ),
        _mutated_retirement_success(command_kind="not-a-mutation-kind"),
    ),
    ids=("stored-receipt-integrity", "wrong-operation-namespace", "impossible-result-kind"),
)
def test_retirement_impossible_protocol_or_result_is_fail_closed_once(decision: Any) -> None:
    service = _PlayerCharacterService()
    service.mutation_result = decision

    response = _post(
        _app(service),
        path=_RETIREMENT_PATH,
        json_body=_retirement_body(),
        headers=_valid_headers(),
    )

    _assert_error(response, 500, "INTERNAL_SERVER_ERROR", "Internal server error")
    assert len(service.mutation_calls) == 1
    assert service.calls == []
    assert service.creation_calls == []


def test_retirement_impossible_policy_decision_is_fail_closed_once() -> None:
    decision = PlayerCharacterPolicyDecision(
        code=PlayerCharacterPolicyCode.INVALID_TRANSITION,
    )
    object.__setattr__(decision, "code", "IMPOSSIBLE_POLICY_DECISION")
    service = _PlayerCharacterService()
    service.mutation_result = decision

    response = _post(
        _app(service),
        path=_RETIREMENT_PATH,
        json_body=_retirement_body(),
        headers=_valid_headers(),
    )

    _assert_error(response, 500, "INTERNAL_SERVER_ERROR", "Internal server error")
    assert len(service.mutation_calls) == 1
    assert service.calls == []
    assert service.creation_calls == []


def test_retirement_controlled_and_unexpected_failures_are_sanitized_once() -> None:
    for error in (RuntimeError("private failure"), ValueError("private invalid result")):
        service = _PlayerCharacterService()
        service.mutation_error = error
        response = _post(
            _app(service),
            path=_RETIREMENT_PATH,
            json_body=_retirement_body(),
            headers=_valid_headers(),
        )
        _assert_error(response, 500, "INTERNAL_SERVER_ERROR", "Internal server error")
        assert len(service.mutation_calls) == 1


@pytest.mark.asyncio
async def test_retirement_cancellation_propagates_without_a_public_translation() -> None:
    service = _PlayerCharacterService()
    cancellation = asyncio.CancelledError()
    service.mutation_error = cancellation
    with pytest.raises(asyncio.CancelledError) as exc_info:
        await _request_async(
            _app(service),
            "POST",
            _RETIREMENT_PATH,
            json_body=_retirement_body(),
            headers=_valid_headers(),
            raise_app_exceptions=True,
        )
    assert exc_info.value is cancellation
    assert len(service.mutation_calls) == 1


@pytest.mark.asyncio
async def test_retirement_unexpected_service_exception_preserves_identity() -> None:
    error = RuntimeError("retirement service identity")
    service = _PlayerCharacterService()
    service.mutation_error = error

    with pytest.raises(RuntimeError) as exc_info:
        await _request_async(
            _app(service),
            "POST",
            _RETIREMENT_PATH,
            json_body=_retirement_body(),
            headers=_valid_headers(),
            raise_app_exceptions=True,
        )

    assert exc_info.value is error
    assert len(service.mutation_calls) == 1


def test_retirement_openapi_and_route_inventory_are_exact() -> None:
    app = _app(_PlayerCharacterService())
    schema = app.openapi()
    retirement_path = "/v1/player-characters/{player_character_id}/retirement"
    assert set(schema["paths"][retirement_path]) == {"post"}
    operation = schema["paths"][retirement_path]["post"]

    assert set(operation) == {
        "tags",
        "summary",
        "description",
        "operationId",
        "parameters",
        "responses",
        "requestBody",
    }
    assert operation["operationId"] == "retire_player_character"
    assert operation["summary"] == "Retire a Player Character"
    assert operation["tags"] == ["player-characters"]
    assert set(operation["responses"]) == {"200", "404", "409", "422", "500"}
    assert operation["requestBody"] == {
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "$ref": (
                        "#/components/schemas/"
                        "PlayerCharacterRetirementRequest"
                    )
                }
            }
        },
    }
    parameter = operation["parameters"]
    assert parameter == [
        {
            "name": "player_character_id",
            "in": "path",
            "required": True,
            "schema": {"type": "string", "minLength": 1, "maxLength": 128, "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$", "title": "Player Character Id"},
        },
        {
            "name": "Idempotency-Key",
            "in": "header",
            "required": True,
            "schema": {"type": "string", "minLength": 1, "maxLength": 128, "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$", "title": "Idempotency-Key"},
        },
    ]
    retirement_schema = schema["components"]["schemas"]["PlayerCharacterRetirementRequest"]
    assert retirement_schema == {
        "additionalProperties": False,
        "properties": {
            "contract_version": {
                "$ref": "#/components/schemas/PlayerCharacterContractVersion"
            },
            "expected_revision": {
                "$ref": "#/components/schemas/PlayerCharacterRevision"
            },
            "confirm_retirement": {
                "const": True,
                "title": "Confirm Retirement",
                "type": "boolean",
            },
        },
        "required": [
            "contract_version",
            "expected_revision",
            "confirm_retirement",
        ],
        "title": "PlayerCharacterRetirementRequest",
        "type": "object",
    }
    assert schema["components"]["schemas"]["PlayerCharacterContractVersion"] == {
        "enum": ["structured-player-character/v1"],
        "title": "PlayerCharacterContractVersion",
        "type": "string",
    }
    assert schema["components"]["schemas"]["PlayerCharacterRevision"] == {
        "additionalProperties": False,
        "properties": {
            "value": {
                "maximum": 9223372036854775807,
                "minimum": 1,
                "title": "Value",
                "type": "integer",
            }
        },
        "required": ["value"],
        "title": "PlayerCharacterRevision",
        "type": "object",
    }
    assert "security" not in operation
    assert "security" not in schema
    assert operation["responses"]["200"]["description"] == "Player Character retired or exactly replayed."
    assert operation["responses"]["404"]["description"] == "Public resource not found"
    assert operation["responses"]["409"]["description"] == "Request or session state conflict"
    assert operation["responses"]["422"]["description"] == "Request validation failed"
    assert operation["responses"]["500"]["description"] == "Internal server error"
    assert operation["responses"]["200"]["content"] == {
        "application/json": {
            "schema": {
                "$ref": "#/components/schemas/PlayerCharacterSelfProjection"
            }
        }
    }
    for status, description in {
        "404": "Public resource not found",
        "409": "Request or session state conflict",
        "422": "Request validation failed",
        "500": "Internal server error",
    }.items():
        assert operation["responses"][status] == {
            "description": description,
            "content": {
                "application/json": {
                    "schema": {
                        "$ref": "#/components/schemas/ErrorResponse"
                    }
                }
            },
        }
    projection = schema["components"]["schemas"]["PlayerCharacterSelfProjection"]
    assert projection == {
        "properties": {
            "player_character_id": {
                "$ref": "#/components/schemas/PlayerCharacterId"
            },
            "contract_version": {
                "$ref": "#/components/schemas/PlayerCharacterContractVersion"
            },
            "record_revision": {
                "$ref": "#/components/schemas/PlayerCharacterRevision"
            },
            "lifecycle": {
                "$ref": "#/components/schemas/PlayerCharacterLifecycle"
            },
        },
        "additionalProperties": False,
        "type": "object",
        "required": [
            "player_character_id",
            "contract_version",
            "record_revision",
            "lifecycle",
        ],
        "title": "PlayerCharacterSelfProjection",
        "description": (
            "Detached, allowlisted current state for an authorized controller."
        ),
    }
    assert schema["components"]["schemas"]["ErrorResponse"] == {
        "properties": {
            "error": {"$ref": "#/components/schemas/ErrorDetail"}
        },
        "additionalProperties": False,
        "type": "object",
        "required": ["error"],
        "title": "ErrorResponse",
    }
    assert schema["components"]["schemas"]["ErrorDetail"] == {
        "properties": {
            "error_code": {"type": "string", "title": "Error Code"},
            "message": {"type": "string", "title": "Message"},
        },
        "additionalProperties": False,
        "type": "object",
        "required": ["error_code", "message"],
        "title": "ErrorDetail",
    }
    assert all(
        forbidden not in schema["components"]["schemas"]
        for forbidden in (
            "MutationReceipt",
            "OperationEvidence",
            "ControllerBinding",
            "Run",
            "PlayerCharacterRunBinding",
            "Transaction",
            "PolicyDecision",
            "Repository",
            "UnitOfWork",
            "OrmModel",
            "Migration",
            "ReplayMetadata",
            "Administration",
        )
    )
    reachable_components: set[str] = set()
    pending: list[Any] = [operation]
    while pending:
        value = pending.pop()
        if isinstance(value, list):
            pending.extend(value)
        elif isinstance(value, dict):
            reference = value.get("$ref")
            if isinstance(reference, str) and reference.startswith(
                "#/components/schemas/"
            ):
                component = reference.rsplit("/", 1)[1]
                if component not in reachable_components:
                    reachable_components.add(component)
                    pending.append(schema["components"]["schemas"][component])
            pending.extend(
                item for key, item in value.items() if key != "$ref"
            )
    assert reachable_components == {
        "ErrorDetail",
        "ErrorResponse",
        "PlayerCharacterContractVersion",
        "PlayerCharacterId",
        "PlayerCharacterLifecycle",
        "PlayerCharacterRetirementRequest",
        "PlayerCharacterRevision",
        "PlayerCharacterSelfProjection",
    }
    assert "/v1/player-characters//retirement" not in schema["paths"]
    assert not any(path.startswith("/v1/runs") for path in schema["paths"])
    assert sum(
        isinstance(route, APIRoute)
        and route.path == retirement_path
        and route.methods == {"POST"}
        for route in app.routes
    ) == 1
    demo_schema = main.create_app(
        services=ApiServices(
            session_service=object(),  # type: ignore[arg-type]
            turn_orchestrator=object(),  # type: ignore[arg-type]
            player_character_service=None,
        )
    ).openapi()
    assert all("retirement" not in path for path in demo_schema["paths"])
    assert "PlayerCharacterRetirementRequest" not in demo_schema["components"]["schemas"]


def test_retirement_route_uses_raw_request_body_and_exact_signature() -> None:
    route = _retirement_route(_app(_PlayerCharacterService()))
    signature = inspect.signature(route.endpoint)

    assert tuple(signature.parameters) == (
        "http_request",
        "player_character_id",
        "idempotency_key",
        "principal",
        "service",
    )
    assert route.body_field is None
    assert route.dependant.body_params == []
    assert route.dependant.request_param_name == "http_request"
    assert [field.name for field in route.dependant.path_params] == ["player_character_id"]
    assert [field.name for field in route.dependant.header_params] == ["idempotency_key"]
    assert [dependency.call for dependency in route.dependant.dependencies] == [
        get_current_principal,
        get_player_character_service,
    ]
    assert route.openapi_extra == main._PLAYER_CHARACTER_RETIREMENT_OPENAPI_EXTRA


@pytest.mark.asyncio
async def test_retirement_reads_the_raw_body_once_after_dependencies_and_before_mutate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    service = _PlayerCharacterService()
    service.mutation_result = _retirement_success()
    app = _app(service)

    def principal_dependency() -> RequestPrincipal:
        events.append("principal")
        return _PRINCIPAL

    def service_dependency() -> _PlayerCharacterService:
        events.append("service-dependency")
        return service

    app.dependency_overrides[get_current_principal] = principal_dependency
    app.dependency_overrides[get_player_character_service] = service_dependency
    _mark_retirement_route_entry(app, events)
    original_body = Request.body

    async def traced_body(request: Request) -> bytes:
        events.append("body")
        return await original_body(request)

    monkeypatch.setattr(Request, "body", traced_body)
    raw_body = json.dumps(_retirement_body(), separators=(",", ":")).encode()
    response = await _raw_asgi_request(
        app,
        path=_RETIREMENT_PATH,
        headers=[
            (b"content-type", b"application/json"),
            (b"idempotency-key", _VALID_KEY.encode("ascii")),
        ],
        body=raw_body,
        events=events,
    )

    assert response.status_code == 200
    assert events == [
        "principal",
        "service-dependency",
        "route",
        "body",
        "body-receive",
    ]
    assert events.count("body") == events.count("body-receive") == 1
    assert len(service.mutation_calls) == 1


@pytest.mark.asyncio
async def test_retirement_body_and_dependency_failures_do_not_mutate_and_cancellation_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _PlayerCharacterService()
    app = _app(service)
    body_calls = 0

    async def body_must_not_run(_: Request) -> bytes:
        nonlocal body_calls
        body_calls += 1
        raise AssertionError("dependency failure must precede body acquisition")

    monkeypatch.setattr(Request, "body", body_must_not_run)

    def failing_principal() -> RequestPrincipal:
        raise RuntimeError("private dependency failure")

    app.dependency_overrides[get_current_principal] = failing_principal
    dependency_failure = await _request_async(
        app,
        "POST",
        _RETIREMENT_PATH,
        json_body=_retirement_body(),
        headers=_valid_headers(),
    )
    _assert_error(_Response(dependency_failure.status_code, dependency_failure.content, dependency_failure.headers), 500, "INTERNAL_SERVER_ERROR", "Internal server error")
    assert service.mutation_calls == []
    assert body_calls == 0

    app = _app(service)

    async def failing_body(_: Request) -> bytes:
        raise RuntimeError("private body failure")

    monkeypatch.setattr(Request, "body", failing_body)
    body_failure = await _request_async(
        app,
        "POST",
        _RETIREMENT_PATH,
        json_body=_retirement_body(),
        headers=_valid_headers(),
    )
    _assert_error(_Response(body_failure.status_code, body_failure.content, body_failure.headers), 500, "INTERNAL_SERVER_ERROR", "Internal server error")
    assert service.mutation_calls == []

    async def cancelled_body(_: Request) -> bytes:
        raise asyncio.CancelledError()

    monkeypatch.setattr(Request, "body", cancelled_body)
    with pytest.raises(asyncio.CancelledError):
        await _request_async(
            app,
            "POST",
            _RETIREMENT_PATH,
            json_body=_retirement_body(),
            headers=_valid_headers(),
            raise_app_exceptions=True,
        )
    assert service.mutation_calls == []


@pytest.mark.parametrize(
    "outcome",
    ("success", "validation-failure", "service-failure"),
)
@pytest.mark.asyncio
async def test_retirement_reads_request_body_exactly_once_on_every_body_reading_path(
    monkeypatch: pytest.MonkeyPatch,
    outcome: str,
) -> None:
    service = _PlayerCharacterService()
    service.mutation_result = _retirement_success()
    if outcome == "service-failure":
        service.mutation_error = RuntimeError("private service failure")
    body_calls = 0
    original_body = Request.body

    async def counted_body(request: Request) -> bytes:
        nonlocal body_calls
        body_calls += 1
        return await original_body(request)

    monkeypatch.setattr(Request, "body", counted_body)
    content = (
        b'{"confirm_retirement":false}'
        if outcome == "validation-failure"
        else json.dumps(_retirement_body(), separators=(",", ":")).encode()
    )
    response = await _request_async(
        _app(service),
        "POST",
        _RETIREMENT_PATH,
        content=content,
        headers=_valid_headers(),
    )

    assert body_calls == 1
    if outcome == "success":
        assert response.status_code == 200
        assert len(service.mutation_calls) == 1
    elif outcome == "validation-failure":
        assert response.status_code == 422
        assert service.mutation_calls == []
    else:
        assert response.status_code == 500
        assert len(service.mutation_calls) == 1


@pytest.mark.parametrize(
    "error",
    (RuntimeError("retirement body identity"), asyncio.CancelledError()),
    ids=("runtime-error", "cancellation"),
)
@pytest.mark.asyncio
async def test_retirement_body_failure_preserves_original_exception_identity_once(
    monkeypatch: pytest.MonkeyPatch,
    error: BaseException,
) -> None:
    service = _PlayerCharacterService()
    body_calls = 0

    async def failing_body(_: Request) -> bytes:
        nonlocal body_calls
        body_calls += 1
        raise error

    monkeypatch.setattr(Request, "body", failing_body)
    with pytest.raises(type(error)) as exc_info:
        await _request_async(
            _app(service),
            "POST",
            _RETIREMENT_PATH,
            content=json.dumps(_retirement_body()).encode(),
            headers=_valid_headers(),
            raise_app_exceptions=True,
        )

    assert exc_info.value is error
    assert body_calls == 1
    assert service.mutation_calls == []


@pytest.mark.asyncio
async def test_retirement_dependency_failure_preserves_identity_before_body_and_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = RuntimeError("retirement dependency identity")
    service = _PlayerCharacterService()
    app = _app(service)
    body_calls = 0

    async def forbidden_body(_: Request) -> bytes:
        nonlocal body_calls
        body_calls += 1
        raise AssertionError("body parsing must follow dependencies")

    def failing_dependency() -> RequestPrincipal:
        raise error

    monkeypatch.setattr(Request, "body", forbidden_body)
    app.dependency_overrides[get_current_principal] = failing_dependency
    with pytest.raises(RuntimeError) as exc_info:
        await _request_async(
            app,
            "POST",
            _RETIREMENT_PATH,
            content=json.dumps(_retirement_body()).encode(),
            headers=_valid_headers(),
            raise_app_exceptions=True,
        )

    assert exc_info.value is error
    assert body_calls == 0
    assert service.mutation_calls == []


@pytest.mark.asyncio
async def test_retirement_unexpected_validator_failure_preserves_identity_without_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = RuntimeError("retirement validator identity")
    service = _PlayerCharacterService()

    def fail_validation(cls: Any, raw_body: bytes, **kwargs: Any) -> Any:
        del cls, raw_body, kwargs
        raise error

    monkeypatch.setattr(
        main.PlayerCharacterRetirementRequest,
        "model_validate_json",
        classmethod(fail_validation),
    )
    with pytest.raises(RuntimeError) as exc_info:
        await _request_async(
            _app(service),
            "POST",
            _RETIREMENT_PATH,
            content=json.dumps(_retirement_body()).encode(),
            headers=_valid_headers(),
            raise_app_exceptions=True,
        )

    assert exc_info.value is error
    assert service.mutation_calls == []


def test_route_uses_exact_request_signature_without_executable_body_binding() -> None:
    app = _app(_PlayerCharacterService(creation_result=_creation_success()))
    route = _creation_route(app)
    signature = inspect.signature(route.endpoint)

    assert tuple(signature.parameters) == (
        "http_request",
        "idempotency_key",
        "principal",
        "service",
    )
    assert all(
        signature.parameters[name].default is inspect.Parameter.empty
        for name in ("http_request", "idempotency_key")
    )
    assert route.body_field is None
    assert route.dependant.body_params == []
    assert route.dependant.request_param_name == "http_request"
    assert [field.name for field in route.dependant.header_params] == [
        "idempotency_key"
    ]
    assert [dependency.call for dependency in route.dependant.dependencies] == [
        get_current_principal,
        get_player_character_service,
    ]
    assert route.openapi_extra == main._PLAYER_CHARACTER_CREATION_OPENAPI_EXTRA


def test_frozen_json_requires_json_mode_and_reaches_the_exact_strict_command() -> None:
    body = _minimal_creation_body()

    with pytest.raises(ValidationError):
        CharacterCreationCommand.model_validate(body)

    parsed = CharacterCreationCommand.model_validate_json(
        json.dumps(body).encode("utf-8")
    )
    assert type(parsed) is CharacterCreationCommand
    assert type(parsed.contract_version) is PlayerCharacterContractVersion

    service = _PlayerCharacterService(creation_result=_creation_success())
    response = _post(_app(service), json_body=body, headers=_valid_headers())

    assert response.status_code == 200
    assert service.creation_calls[0][2] == parsed
    assert type(service.creation_calls[0][2]) is CharacterCreationCommand


@pytest.mark.asyncio
async def test_creation_stage_trace_reads_body_once_and_preserves_exact_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    service = _PlayerCharacterService(creation_result=_creation_success())
    app = _app(service)

    def principal_dependency() -> RequestPrincipal:
        events.append("principal")
        return _PRINCIPAL

    def service_dependency() -> _PlayerCharacterService:
        events.append("service-dependency")
        return service

    app.dependency_overrides[get_current_principal] = principal_dependency
    app.dependency_overrides[get_player_character_service] = service_dependency
    _mark_creation_route_entry(app, events)

    original_transport = main._validate_player_character_creation_transport

    def traced_transport(
        request: Request,
        idempotency_key: str,
    ) -> PlayerCharacterOperationId:
        events.append("transport")
        return original_transport(request, idempotency_key)

    monkeypatch.setattr(
        main,
        "_validate_player_character_creation_transport",
        traced_transport,
    )
    operation_type = main.PlayerCharacterOperationId

    def traced_operation_id(*, value: str) -> PlayerCharacterOperationId:
        events.append("operation")
        return operation_type(value=value)

    monkeypatch.setattr(main, "PlayerCharacterOperationId", traced_operation_id)
    original_body = Request.body
    returned_body: bytes | None = None

    async def traced_body(request: Request) -> bytes:
        nonlocal returned_body
        events.append("body")
        returned_body = await original_body(request)
        return returned_body

    monkeypatch.setattr(Request, "body", traced_body)
    original_validate_json = CharacterCreationCommand.model_validate_json
    validated_body: bytes | None = None

    def traced_validate_json(cls: Any, raw_body: bytes, **kwargs: Any) -> Any:
        nonlocal validated_body
        del cls
        events.append("json-mode")
        validated_body = raw_body
        return original_validate_json(raw_body, **kwargs)

    monkeypatch.setattr(
        CharacterCreationCommand,
        "model_validate_json",
        classmethod(traced_validate_json),
    )
    original_create = service.create

    async def traced_create(
        principal: RequestPrincipal,
        *,
        operation_id: PlayerCharacterOperationId,
        command: CharacterCreationCommand,
    ) -> Any:
        events.append("service")
        return await original_create(
            principal,
            operation_id=operation_id,
            command=command,
        )

    service.create = traced_create  # type: ignore[method-assign]
    raw_body = json.dumps(_minimal_creation_body(), separators=(",", ":")).encode()

    response = await _raw_asgi_request(
        app,
        headers=[
            (b"content-type", b"application/json"),
            (b"idempotency-key", _VALID_KEY.encode("ascii")),
        ],
        body=raw_body,
        events=events,
    )

    assert response.status_code == 200
    assert events == [
        "principal",
        "service-dependency",
        "route",
        "transport",
        "operation",
        "body",
        "body-receive",
        "json-mode",
        "service",
    ]
    assert returned_body is validated_body
    assert validated_body == raw_body
    assert events.count("operation") == 1
    assert events.count("body") == 1
    assert events.count("body-receive") == 1
    assert events.count("json-mode") == 1
    assert events.count("service") == 1


@pytest.mark.parametrize(
    ("case_id", "raw_headers", "dependency_failure", "expected_events"),
    (
        (
            "dependency",
            [
                (b"content-type", b"application/json"),
                (b"idempotency-key", _VALID_KEY.encode()),
            ],
            True,
            ["principal"],
        ),
        (
            "declarative-header",
            [(b"content-type", b"application/json")],
            False,
            ["principal", "service-dependency"],
        ),
        (
            "raw-content-type",
            [
                (b"content-type", b"text/plain"),
                (b"idempotency-key", _VALID_KEY.encode()),
            ],
            False,
            ["principal", "service-dependency", "route", "transport"],
        ),
        (
            "duplicate-raw-key",
            [
                (b"content-type", b"application/json"),
                (b"idempotency-key", _VALID_KEY.encode()),
                (b"idempotency-key", b"second"),
            ],
            False,
            ["principal", "service-dependency", "route", "transport"],
        ),
        (
            "malformed-json",
            [
                (b"content-type", b"application/json"),
                (b"idempotency-key", _VALID_KEY.encode()),
            ],
            False,
            [
                "principal",
                "service-dependency",
                "route",
                "transport",
                "operation",
                "body",
                "body-receive",
                "parse",
            ],
        ),
    ),
)
@pytest.mark.asyncio
async def test_combined_invalid_inputs_follow_the_authorized_precedence(
    monkeypatch: pytest.MonkeyPatch,
    case_id: str,
    raw_headers: list[tuple[bytes, bytes]],
    dependency_failure: bool,
    expected_events: list[str],
) -> None:
    events: list[str] = []
    service = _PlayerCharacterService(creation_result=_creation_success())
    app = _app(service)

    def principal_dependency() -> RequestPrincipal:
        events.append("principal")
        if dependency_failure:
            raise RequestValidationError([])
        return _PRINCIPAL

    def service_dependency() -> _PlayerCharacterService:
        events.append("service-dependency")
        return service

    app.dependency_overrides[get_current_principal] = principal_dependency
    app.dependency_overrides[get_player_character_service] = service_dependency
    _mark_creation_route_entry(app, events)
    original_transport = main._validate_player_character_creation_transport

    def traced_transport(
        request: Request,
        idempotency_key: str,
    ) -> PlayerCharacterOperationId:
        events.append("transport")
        return original_transport(request, idempotency_key)

    monkeypatch.setattr(
        main,
        "_validate_player_character_creation_transport",
        traced_transport,
    )
    operation_type = main.PlayerCharacterOperationId

    def traced_operation_id(*, value: str) -> PlayerCharacterOperationId:
        events.append("operation")
        return operation_type(value=value)

    monkeypatch.setattr(main, "PlayerCharacterOperationId", traced_operation_id)
    original_body = Request.body

    async def traced_body(request: Request) -> bytes:
        events.append("body")
        return await original_body(request)

    monkeypatch.setattr(Request, "body", traced_body)
    original_parse = main._parse_player_character_creation_command

    def traced_parse(raw_body: bytes) -> CharacterCreationCommand:
        events.append("parse")
        return original_parse(raw_body)

    monkeypatch.setattr(
        main,
        "_parse_player_character_creation_command",
        traced_parse,
    )

    response = await _raw_asgi_request(
        app,
        headers=raw_headers,
        body=b"{",
        events=events,
    )

    _assert_error(
        response,
        422,
        "REQUEST_VALIDATION_FAILED",
        "Request validation failed",
    )
    assert events == expected_events, case_id
    assert service.creation_calls == []


@pytest.mark.parametrize(
    ("case_id", "raw_value"),
    (
        ("missing", None),
        ("empty", b""),
        ("overlength", b"x" * 129),
        ("alphabet", b".leading"),
        ("comma", b"one,two"),
        ("non-ascii", b"\xff"),
    ),
)
@pytest.mark.asyncio
async def test_declarative_header_failures_use_exact_raw_asgi_classification(
    case_id: str,
    raw_value: bytes | None,
) -> None:
    events: list[str] = []
    observed_headers: list[list[tuple[bytes, bytes]]] = []
    service = _PlayerCharacterService(creation_result=_creation_success())
    app = _app(service)

    def principal_dependency() -> RequestPrincipal:
        events.append("principal")
        return _PRINCIPAL

    def service_dependency(request: Request) -> _PlayerCharacterService:
        events.append("service-dependency")
        observed_headers.append(list(request.scope["headers"]))
        if raw_value == b"\xff":
            assert request.headers["Idempotency-Key"] == "ÿ"
        return service

    app.dependency_overrides[get_current_principal] = principal_dependency
    app.dependency_overrides[get_player_character_service] = service_dependency
    _mark_creation_route_entry(app, events)
    headers = [(b"content-type", b"application/json")]
    if raw_value is not None:
        headers.append((b"idempotency-key", raw_value))

    response = await _raw_asgi_request(
        app,
        headers=headers,
        body=json.dumps(_minimal_creation_body()).encode(),
        events=events,
    )

    _assert_error(
        response,
        422,
        "REQUEST_VALIDATION_FAILED",
        "Request validation failed",
    )
    assert observed_headers == [headers]
    assert events == ["principal", "service-dependency"], case_id
    assert service.creation_calls == []


@pytest.mark.parametrize(
    ("decision", "status_code", "code", "message"),
    (
        (
            CharacterOperationProtocolDecision(
                operation_namespace=CharacterOperationNamespace.CREATE_V1,
                code=CharacterOperationProtocolCode.AUTHORIZATION_FAILED,
            ),
            404,
            "PLAYER_CHARACTER_NOT_FOUND",
            "Player character was not found",
        ),
        (
            CharacterOperationProtocolDecision(
                operation_namespace=CharacterOperationNamespace.CREATE_V1,
                code=CharacterOperationProtocolCode.IDEMPOTENCY_CONFLICT,
            ),
            409,
            "IDEMPOTENCY_CONFLICT",
            "Idempotency key was reused",
        ),
    ),
)
def test_creation_decisions_use_exact_non_enumerating_public_errors(
    decision: CharacterOperationProtocolDecision,
    status_code: int,
    code: str,
    message: str,
) -> None:
    service = _PlayerCharacterService(creation_result=decision)

    response = _post(
        _app(service),
        json_body=_minimal_creation_body(),
        headers=_valid_headers(),
    )

    _assert_error(response, status_code, code, message)
    assert len(service.creation_calls) == 1
    for private_detail in (
        _VALID_KEY,
        _PRINCIPAL.player_id,
        "controller",
        "binding",
        "receipt",
        "fingerprint",
    ):
        assert private_detail.casefold() not in response.text.casefold()


@pytest.mark.parametrize(
    "result",
    (
        CharacterOperationProtocolDecision(
            operation_namespace=CharacterOperationNamespace.CREATE_V1,
            code=CharacterOperationProtocolCode.STORED_RECEIPT_INTEGRITY_FAILURE,
        ),
        CharacterOperationProtocolDecision(
            operation_namespace=CharacterOperationNamespace.CREATE_V1,
            code=CharacterOperationProtocolCode.READY_FOR_NEW_OPERATION,
        ),
        CharacterOperationProtocolDecision(
            operation_namespace=CharacterOperationNamespace.MUTATE_V1,
            code=CharacterOperationProtocolCode.AUTHORIZATION_FAILED,
        ),
        object(),
    ),
    ids=("receipt-integrity", "impossible-code", "wrong-namespace", "wrong-type"),
)
def test_corrupt_or_impossible_creation_results_fail_closed(result: Any) -> None:
    service = _PlayerCharacterService(creation_result=result)

    response = _post(
        _app(service),
        json_body=_minimal_creation_body(),
        headers=_valid_headers(),
    )

    _assert_error(
        response,
        500,
        "INTERNAL_SERVER_ERROR",
        "Internal server error",
    )
    assert len(service.creation_calls) == 1
    assert "receipt" not in response.text.casefold()
    assert "namespace" not in response.text.casefold()


@pytest.mark.parametrize(
    "error",
    (
        ValueError("corrupt stored receipt pc.private"),
        RuntimeError("mysql constraint secret"),
    ),
)
def test_unexpected_creation_failures_are_sanitized(error: BaseException) -> None:
    service = _PlayerCharacterService()
    service.creation_error = error

    response = _post(
        _app(service),
        json_body=_minimal_creation_body(),
        headers=_valid_headers(),
    )

    _assert_error(
        response,
        500,
        "INTERNAL_SERVER_ERROR",
        "Internal server error",
    )
    assert str(error) not in response.text


@pytest.mark.asyncio
async def test_creation_preserves_original_exception_identity_internally() -> None:
    error = RuntimeError("internal identity")
    service = _PlayerCharacterService()
    service.creation_error = error

    with pytest.raises(RuntimeError) as exc_info:
        await _request_async(
            _app(service),
            "POST",
            _CREATE_PATH,
            json_body=_minimal_creation_body(),
            headers=_valid_headers(),
            raise_app_exceptions=True,
        )

    assert exc_info.value is error


@pytest.mark.asyncio
async def test_creation_cancellation_propagates_without_translation() -> None:
    cancellation = asyncio.CancelledError()
    service = _PlayerCharacterService()
    service.creation_error = cancellation

    with pytest.raises(asyncio.CancelledError) as exc_info:
        await _request_async(
            _app(service),
            "POST",
            _CREATE_PATH,
            json_body=_minimal_creation_body(),
            headers=_valid_headers(),
            raise_app_exceptions=True,
        )

    assert exc_info.value is cancellation
    assert len(service.creation_calls) == 1


@pytest.mark.parametrize(
    "error",
    (RuntimeError("body read identity"), asyncio.CancelledError()),
    ids=("runtime-error", "cancellation"),
)
@pytest.mark.asyncio
async def test_body_read_failures_preserve_original_base_exception_identity(
    monkeypatch: pytest.MonkeyPatch,
    error: BaseException,
) -> None:
    service = _PlayerCharacterService(creation_result=_creation_success())

    async def failing_body(_: Request) -> bytes:
        raise error

    monkeypatch.setattr(Request, "body", failing_body)

    with pytest.raises(type(error)) as exc_info:
        await _request_async(
            _app(service),
            "POST",
            _CREATE_PATH,
            content=json.dumps(_minimal_creation_body()).encode(),
            headers=_valid_headers(),
            raise_app_exceptions=True,
        )

    assert exc_info.value is error
    assert service.creation_calls == []


@pytest.mark.asyncio
async def test_unexpected_json_validator_failure_preserves_exception_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = RuntimeError("json validator identity")
    service = _PlayerCharacterService(creation_result=_creation_success())

    def fail_validation(cls: Any, raw_body: bytes, **kwargs: Any) -> Any:
        del cls, raw_body, kwargs
        raise error

    monkeypatch.setattr(
        CharacterCreationCommand,
        "model_validate_json",
        classmethod(fail_validation),
    )

    with pytest.raises(RuntimeError) as exc_info:
        await _request_async(
            _app(service),
            "POST",
            _CREATE_PATH,
            content=json.dumps(_minimal_creation_body()).encode(),
            headers=_valid_headers(),
            raise_app_exceptions=True,
        )

    assert exc_info.value is error
    assert service.creation_calls == []


@pytest.mark.parametrize(
    ("headers", "case_id"),
    (
        ([("Content-Type", "application/json")], "missing"),
        (
            [
                (b"Content-Type", b"application/json"),
                (b"Idempotency-Key", b"first"),
                (b"idempotency-key", b"second"),
            ],
            "duplicate",
        ),
        (_valid_headers(b""), "empty"),
        (_valid_headers(b"x" * 129), "overlength"),
        (_valid_headers(b"\xff"), "non-ascii"),
        (_valid_headers(b".leading"), "leading-punctuation"),
        (_valid_headers(b" leading"), "leading-space"),
        (_valid_headers(b"trailing "), "trailing-space"),
        (_valid_headers(b"one,two"), "comma-joined"),
        (_valid_headers(b"percent%20encoded"), "percent-encoded"),
        (_valid_headers(b"has/slash"), "invalid-alphabet"),
    ),
)
def test_invalid_raw_idempotency_key_fails_before_service(
    headers: Any,
    case_id: str,
) -> None:
    service = _PlayerCharacterService(creation_result=_creation_success())

    response = _post(
        _app(service),
        content=json.dumps(_minimal_creation_body()).encode(),
        headers=headers,
    )

    _assert_error(
        response,
        422,
        "REQUEST_VALIDATION_FAILED",
        "Request validation failed",
    )
    assert service.creation_calls == [], case_id
    assert case_id not in response.text


@pytest.mark.parametrize(
    ("key", "content_type"),
    (
        ("a", "application/json"),
        ("A" + "x" * 127, "application/json; charset=utf-8"),
        ("Key.Case", " \tApplication/JSON\t ; charset=utf-8"),
        ("key.case", "application/json; ignored=value"),
    ),
)
def test_valid_key_boundaries_case_and_json_parameters_are_preserved(
    key: str,
    content_type: str,
) -> None:
    service = _PlayerCharacterService(creation_result=_creation_success())

    response = _post(
        _app(service),
        content=json.dumps(_minimal_creation_body()).encode(),
        headers=_valid_headers(key, content_type=content_type),
    )

    assert response.status_code == 200
    assert service.creation_calls[0][1] == PlayerCharacterOperationId(value=key)
    assert service.creation_calls[0][1].value == key


def test_operation_keys_are_case_sensitive_and_never_rewritten() -> None:
    service = _PlayerCharacterService(creation_result=_creation_success())
    app = _app(service)

    for key in ("Key.Case", "key.case"):
        response = _post(
            app,
            json_body=_minimal_creation_body(),
            headers=_valid_headers(key),
        )
        assert response.status_code == 200

    assert [call[1].value for call in service.creation_calls] == [
        "Key.Case",
        "key.case",
    ]


def test_query_body_and_alternate_header_cannot_supply_operation_or_authority() -> None:
    service = _PlayerCharacterService(creation_result=_creation_success())
    app = _app(service)

    without_key = _post(
        app,
        json_body=_minimal_creation_body(),
        headers=[
            ("Content-Type", "application/json"),
            ("X-Idempotency-Key", "alternate"),
            ("X-Controller", "attacker"),
        ],
        path=_CREATE_PATH
        + "?idempotency_key=query-key&controller_binding=attacker",
    )
    body_override = deepcopy(_minimal_creation_body())
    body_override["controller_binding"] = "attacker"
    with_body_override = _post(
        app,
        json_body=body_override,
        headers=_valid_headers(),
    )
    accepted_with_irrelevant_inputs = _post(
        app,
        json_body=_minimal_creation_body(),
        headers=[
            *_valid_headers(),
            ("X-Controller", "attacker"),
        ],
        path=_CREATE_PATH + "?controller_binding=attacker",
    )

    for response in (without_key, with_body_override):
        _assert_error(
            response,
            422,
            "REQUEST_VALIDATION_FAILED",
            "Request validation failed",
        )
    assert accepted_with_irrelevant_inputs.status_code == 200
    assert service.creation_calls == [
        (
            _PRINCIPAL,
            PlayerCharacterOperationId(value=_VALID_KEY),
            CharacterCreationCommand(
                contract_version=PlayerCharacterContractVersion.V1,
                character_core=CharacterCore(),
                narration_preferences=NarrationPreferences(),
            ),
        )
    ]


@pytest.mark.parametrize(
    ("headers", "case_id"),
    (
        ([("Idempotency-Key", _VALID_KEY)], "missing"),
        (_valid_headers(content_type="text/plain"), "wrong"),
        (
            [
                (b"Content-Type", b"application/json"),
                (b"content-type", b"application/json"),
                (b"Idempotency-Key", _VALID_KEY.encode()),
            ],
            "duplicate",
        ),
        (
            _valid_headers(content_type=b"application/\xff"),
            "non-ascii",
        ),
    ),
)
def test_invalid_or_ambiguous_content_type_is_sanitized(
    headers: Any,
    case_id: str,
) -> None:
    service = _PlayerCharacterService(creation_result=_creation_success())

    response = _post(
        _app(service),
        content=json.dumps(_minimal_creation_body()).encode(),
        headers=headers,
    )

    _assert_error(
        response,
        422,
        "REQUEST_VALIDATION_FAILED",
        "Request validation failed",
    )
    assert service.creation_calls == [], case_id


@pytest.mark.parametrize(
    ("content", "headers"),
    (
        (b"{", _valid_headers()),
        (b"", _valid_headers()),
        (b"null", _valid_headers()),
        (b"[]", _valid_headers()),
        (b'"text"', _valid_headers()),
        (b"0", _valid_headers()),
        (b"true", _valid_headers()),
        (b"{}", _valid_headers()),
    ),
    ids=(
        "malformed",
        "empty",
        "null",
        "array",
        "string",
        "number",
        "boolean",
        "wrong-object-shape",
    ),
)
def test_invalid_top_level_json_is_sanitized_before_service(
    content: bytes,
    headers: Any,
) -> None:
    service = _PlayerCharacterService(creation_result=_creation_success())

    response = _post(
        _app(service),
        content=content,
        headers=headers,
    )

    _assert_error(
        response,
        422,
        "REQUEST_VALIDATION_FAILED",
        "Request validation failed",
    )
    assert service.creation_calls == []
    assert "loc" not in response.text
    assert "input" not in response.text


def test_absent_and_explicit_empty_bodies_are_publicly_indistinguishable() -> None:
    absent_service = _PlayerCharacterService(creation_result=_creation_success())
    empty_service = _PlayerCharacterService(creation_result=_creation_success())

    absent = _post(_app(absent_service), headers=_valid_headers())
    empty = _post(_app(empty_service), content=b"", headers=_valid_headers())

    assert absent.status_code == empty.status_code == 422
    assert absent.body == empty.body
    assert absent_service.creation_calls == []
    assert empty_service.creation_calls == []


def _invalid_creation_bodies() -> list[tuple[str, dict[str, Any]]]:
    minimal = _minimal_creation_body()
    missing = deepcopy(minimal)
    missing.pop("character_core")
    unknown_top = deepcopy(minimal)
    unknown_top["unknown"] = True
    unknown_nested = deepcopy(minimal)
    unknown_nested["character_core"]["unknown"] = True
    explicit_null = deepcopy(minimal)
    explicit_null["character_core"] = None
    declared_without_value = deepcopy(minimal)
    declared_without_value["character_core"]["name_or_code_name"] = {
        "state": "declared",
        "value": None,
    }
    omitted_with_value = deepcopy(minimal)
    omitted_with_value["character_core"]["name_or_code_name"] = {
        "state": "omitted",
        "value": {
            "authority": "player-expression",
            "text": "not allowed",
        },
    }
    duplicate_features = deepcopy(minimal)
    feature = {"authority": "player-expression", "text": "same"}
    duplicate_features["character_core"]["distinguishing_features"] = {
        "state": "declared",
        "value": {"features": [feature, feature]},
    }
    duplicate_custom_keys = deepcopy(minimal)
    custom_entry = {
        "key": "same",
        "declaration": {"state": "omitted", "value": None},
    }
    duplicate_custom_keys["character_core"]["custom_values"] = {
        "state": "declared",
        "value": {"entries": [custom_entry, custom_entry]},
    }
    normalized_duplicate_custom_keys = deepcopy(minimal)
    normalized_duplicate_custom_keys["character_core"]["custom_values"] = {
        "state": "declared",
        "value": {
            "entries": [
                {
                    "key": "e\u0301",
                    "declaration": {"state": "omitted", "value": None},
                },
                {
                    "key": "é",
                    "declaration": {"state": "omitted", "value": None},
                },
            ]
        },
    }
    nul_text = deepcopy(minimal)
    nul_text["character_core"]["name_or_code_name"] = {
        "state": "declared",
        "value": {
            "authority": "player-expression",
            "text": "contains\u0000nul",
        },
    }
    non_adult = deepcopy(minimal)
    non_adult["character_core"]["broad_adult_age_presentation"] = {
        "state": "declared",
        "value": {"adult_only": False},
    }
    invalid_enum = deepcopy(minimal)
    invalid_enum["narration_preferences"]["internal_thoughts"] = {
        "state": "declared",
        "value": {
            "authority": "player-expression",
            "value": "provider-decides",
        },
    }
    overflow = deepcopy(minimal)
    overflow["character_core"]["name_or_code_name"] = {
        "state": "declared",
        "value": {
            "authority": "player-expression",
            "text": "x" * 64_821,
        },
    }
    return [
        ("missing-required", missing),
        ("unknown-top", unknown_top),
        ("unknown-nested", unknown_nested),
        ("explicit-null", explicit_null),
        ("declared-without-value", declared_without_value),
        ("omitted-with-value", omitted_with_value),
        ("duplicate-features", duplicate_features),
        ("duplicate-custom-keys", duplicate_custom_keys),
        ("normalized-duplicate-custom-keys", normalized_duplicate_custom_keys),
        ("nul", nul_text),
        ("non-adult", non_adult),
        ("invalid-enum", invalid_enum),
        ("canonical-overflow", overflow),
    ]


@pytest.mark.parametrize(
    ("case_id", "body"),
    _invalid_creation_bodies(),
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_invalid_creation_graph_uses_fixed_422_without_details(
    case_id: str,
    body: dict[str, Any],
) -> None:
    service = _PlayerCharacterService(creation_result=_creation_success())

    response = _post(
        _app(service),
        json_body=body,
        headers=_valid_headers(),
    )

    _assert_error(
        response,
        422,
        "REQUEST_VALIDATION_FAILED",
        "Request validation failed",
    )
    assert service.creation_calls == [], case_id
    assert case_id not in response.text


def test_complete_public_creation_graph_binds_directly_to_command() -> None:
    body = _full_creation_body()
    expected = CharacterCreationCommand.model_validate_json(json.dumps(body))
    service = _PlayerCharacterService(creation_result=_creation_success())

    response = _post(
        _app(service),
        json_body=body,
        headers=_valid_headers(),
    )

    assert response.status_code == 200
    principal, operation_id, command = service.creation_calls[0]
    assert principal is _PRINCIPAL
    assert operation_id == PlayerCharacterOperationId(value=_VALID_KEY)
    assert type(command) is CharacterCreationCommand
    assert command == expected
    dumped = command.model_dump(mode="json")
    for private_field in (
        "controller",
        "owner",
        "receipt",
        "fingerprint",
        "transaction",
        "persistence",
        "schema_version",
        "lifecycle",
    ):
        assert private_field not in json.dumps(dumped).casefold()


@pytest.mark.parametrize(
    ("text", "expected"),
    (
        ("x" * 64_820, "x" * 64_820),
        (("e" + "\u0301") * 8, "\u00e9" * 8),
    ),
    ids=("canonical-65536-boundary", "nfc-equivalent"),
)
def test_boundary_and_nfc_body_values_reach_service_canonically(
    text: str,
    expected: str,
) -> None:
    body = _minimal_creation_body()
    body["character_core"]["name_or_code_name"] = {
        "state": "declared",
        "value": {
            "authority": "player-expression",
            "text": text,
        },
    }
    service = _PlayerCharacterService(creation_result=_creation_success())

    response = _post(
        _app(service),
        json_body=body,
        headers=_valid_headers(),
    )

    assert response.status_code == 200
    declaration = service.creation_calls[0][2].character_core.name_or_code_name
    assert declaration.value is not None
    assert declaration.value.text == expected


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


def test_eligible_discovery_has_exact_safe_collection_contract() -> None:
    service = _PlayerCharacterService()
    service.eligible_result = EligiblePlayerCharacterCollection(
        eligible_player_characters=(_projection(PlayerCharacterLifecycle.ACTIVE),),
        truncated=False,
    )

    response = _get(_app(service), _ELIGIBLE_PATH)

    assert response.status_code == 200
    assert response.json() == {
        "eligible_player_characters": [
            {
                "player_character_id": {"value": "pc.test-owned"},
                "contract_version": "structured-player-character/v1",
                "record_revision": {"value": 1},
                "lifecycle": "active",
            }
        ],
        "truncated": False,
    }
    assert service.eligible_calls == [_PRINCIPAL]
    assert service.calls == []
    assert service.creation_calls == []
    assert service.mutation_calls == []


def test_eligible_discovery_non_enumerates_authority_and_sanitizes_failures() -> None:
    unavailable = _PlayerCharacterService()
    unavailable.eligible_result = None
    failure = _PlayerCharacterService()
    failure.eligible_error = ValueError("corrupt binding evidence")

    assert _get(_app(unavailable), _ELIGIBLE_PATH).json() == {
        "error": {
            "error_code": "PLAYER_CHARACTER_NOT_FOUND",
            "message": "Player character was not found",
        }
    }
    response = _get(_app(failure), _ELIGIBLE_PATH)
    assert response.status_code == 500
    assert response.json()["error"]["error_code"] == "INTERNAL_SERVER_ERROR"
    assert "corrupt" not in response.text


def test_eligible_discovery_openapi_has_no_input_or_duplicate_route() -> None:
    schema = _app(_PlayerCharacterService()).openapi()
    operation = schema["paths"][_ELIGIBLE_PATH]["get"]

    assert operation["operationId"] == "list_eligible_player_characters_for_run_entry"
    assert operation["tags"] == ["player-characters"]
    assert operation["summary"] == "List eligible Player Characters for Run entry"
    assert "parameters" not in operation
    assert "requestBody" not in operation
    assert set(operation["responses"]) == {"200", "404", "422", "500"}
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/EligiblePlayerCharacterCollection"
    }
    assert list(schema["paths"][_ELIGIBLE_PATH]) == ["get"]
    for status_code in ("404", "422", "500"):
        assert operation["responses"][status_code]["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/ErrorResponse"
        }
    component = schema["components"]["schemas"]["EligiblePlayerCharacterCollection"]
    assert component["type"] == "object"
    assert component["additionalProperties"] is False
    assert component["required"] == ["eligible_player_characters", "truncated"]
    assert component["properties"]["eligible_player_characters"] == {
        "items": {"$ref": "#/components/schemas/PlayerCharacterSelfProjection"},
        "type": "array",
        "maxItems": 32,
        "title": "Eligible Player Characters",
    }
    assert component["properties"]["truncated"] == {
        "type": "boolean", "title": "Truncated"
    }


def test_eligible_discovery_exact_empty_and_truncated_serialization_and_query_nonselection() -> None:
    empty_service = _PlayerCharacterService()
    empty = _get(_app(empty_service), _ELIGIBLE_PATH + "?controller=other")
    assert empty.status_code == 200
    assert empty.json() == {"eligible_player_characters": [], "truncated": False}
    assert empty_service.eligible_calls == [_PRINCIPAL]
    truncated_service = _PlayerCharacterService()
    truncated_service.eligible_result = EligiblePlayerCharacterCollection(
        eligible_player_characters=tuple(_projection(PlayerCharacterLifecycle.ACTIVE) for _ in range(32)),
        truncated=True,
    )
    truncated = _get(_app(truncated_service), _ELIGIBLE_PATH)
    assert truncated.status_code == 200
    assert len(truncated.json()["eligible_player_characters"]) == 32
    assert truncated.json()["truncated"] is True


def test_dependency_fails_closed_when_service_is_not_composed() -> None:
    app = _app(None)
    request = Request({"type": "http", "app": app})

    with pytest.raises(RuntimeError, match="not configured"):
        get_player_character_service(request)
    assert "/v1/player-characters" not in app.openapi()["paths"]
    assert "/v1/player-characters/{player_character_id}" not in app.openapi()["paths"]


def test_normal_openapi_preserves_the_safe_owned_read_contract() -> None:
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
    rendered = json.dumps(schema["components"]["schemas"]).casefold()
    for forbidden in (
        "canonicalplayercharacter",
        "controllerbindingref",
        "authorityprovenance",
        "sqlalchemy",
        "storedcreationsuccessreceipt",
        "characteroperationfingerprint",
    ):
        assert forbidden not in rendered


def test_normal_openapi_declares_the_exact_creation_contract() -> None:
    schema = _app(_PlayerCharacterService()).openapi()
    operation = schema["paths"]["/v1/player-characters"]["post"]

    assert operation["operationId"] == "create_player_character"
    assert operation["tags"] == ["player-characters"]
    assert operation["summary"] == "Create or replay a Player Character"
    assert operation["parameters"] == [
        {
            "name": "Idempotency-Key",
            "in": "header",
            "required": True,
            "schema": {
                "type": "string",
                "minLength": 1,
                "maxLength": 128,
                "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$",
                "title": "Idempotency-Key",
            },
        }
    ]
    assert operation["requestBody"] == {
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "$ref": "#/components/schemas/CharacterCreationCommand"
                }
            }
        },
    }
    assert set(operation["responses"]) == {"200", "404", "409", "422", "500"}
    assert operation["responses"]["200"] == {
        "description": "Player Character created or exactly replayed.",
        "content": {
            "application/json": {
                "schema": {
                    "$ref": "#/components/schemas/PlayerCharacterSelfProjection"
                }
            }
        },
    }
    assert all(
        operation["responses"][status_code]["content"]["application/json"][
            "schema"
        ]
        == {"$ref": "#/components/schemas/ErrorResponse"}
        for status_code in ("404", "409", "422", "500")
    )
    for statement in (
        "trusted server-side principal",
        "Idempotency-Key is required and is not authorization",
        "First success and exact replay share HTTP 200",
        "Replay returns the original creation result",
        "owned GET for current state",
        "No controller binding, receipt, fingerprint, provenance, Run, "
        "persistence, transaction, or recovery data is public",
        "fixed development principal is not production authentication",
        "Internet deployment are unsupported",
    ):
        assert statement in operation["description"]
    assert "security" not in operation
    assert "securitySchemes" not in schema["components"]
    rendered_operation = json.dumps(operation).casefold()
    for forbidden in (
        '"201"',
        '"400"',
        '"401"',
        '"403"',
        '"415"',
        "location",
        "replay_discriminator",
    ):
        assert forbidden not in rendered_operation
    rendered_components = json.dumps(schema["components"]["schemas"]).casefold()
    for private_schema in (
        "canonicalplayercharacter",
        "controllerbindingref",
        "creationreceiptkey",
        "storedcreationsuccessreceipt",
        "characteroperationfingerprint",
        "creationsuccessresult",
        "characteroperationprotocoldecision",
        "unitofwork",
        "sqlalchemy",
    ):
        assert private_schema not in rendered_components


def test_creation_openapi_injects_the_exact_validation_schema_inventory() -> None:
    schema = _app(_PlayerCharacterService()).openapi()
    schemas = schema["components"]["schemas"]
    generated = _generated_creation_components()
    expected_generated_names = {
        "CharacterCreationCommand",
        "AdultAgePresentation",
        "CharacterCore",
        "CustomValueEntry",
        "CustomValues",
        "DeclarationState",
        "Declaration_AdultAgePresentation_",
        "Declaration_CustomValues_",
        "Declaration_DistinguishingFeatures_",
        "Declaration_PlayerDeclaredText_",
        "Declaration_PlayerNarrationPreference_",
        "DistinguishingFeatures",
        "NarrationPreference",
        "NarrationPreferences",
        "PlayerCharacterContractVersion",
        "PlayerDeclaredText",
        "PlayerNarrationPreference",
        "PlayerSubjectiveAuthority",
    }

    assert set(generated) == expected_generated_names
    assert len(schemas) == 75
    assert all(schemas[name] == definition for name, definition in generated.items())
    assert "$defs" not in schemas["CharacterCreationCommand"]
    assert schemas["CharacterCreationCommand"]["required"] == [
        "contract_version",
        "character_core",
        "narration_preferences",
    ]
    assert schemas["PlayerCharacterContractVersion"]["enum"] == [
        "structured-player-character/v1"
    ]
    assert schemas["DeclarationState"]["enum"] == [
        "omitted",
        "explicitly-absent",
        "declared",
        "intentionally-undecided",
    ]
    assert schemas["NarrationPreference"]["enum"] == [
        "high-immersion",
        "balanced",
        "high-agency",
    ]
    assert schemas["PlayerSubjectiveAuthority"]["enum"] == [
        "player-expression",
        "player-confirmation",
    ]
    assert all(
        definition["additionalProperties"] is False
        for definition in generated.values()
        if definition.get("type") == "object"
    )
    _assert_all_local_refs_resolve(schema)


def test_creation_openapi_matches_emitted_declaration_and_default_behavior() -> None:
    schemas = _app(_PlayerCharacterService()).openapi()["components"]["schemas"]

    for name in (
        "Declaration_AdultAgePresentation_",
        "Declaration_CustomValues_",
        "Declaration_DistinguishingFeatures_",
        "Declaration_PlayerDeclaredText_",
        "Declaration_PlayerNarrationPreference_",
    ):
        declaration = schemas[name]
        assert declaration["required"] == ["state"]
        assert "value" not in declaration["required"]
        assert declaration["properties"]["value"]["default"] is None
        assert declaration["properties"]["value"]["anyOf"][-1] == {
            "type": "null"
        }

    for group_name in ("CharacterCore", "NarrationPreferences"):
        group = schemas[group_name]
        assert "required" not in group
        assert all(
            "default" not in property_schema
            for property_schema in group["properties"].values()
        )

    rendered = json.dumps(
        {name: schemas[name] for name in _generated_creation_components()},
        sort_keys=True,
    )
    for unsupported in (
        '"if"',
        '"then"',
        '"else"',
        '"oneOf"',
        '"allOf"',
        '"dependentSchemas"',
    ):
        assert unsupported not in rendered


def test_openapi_omits_runtime_only_character_command_invariants() -> None:
    schemas = _app(_PlayerCharacterService()).openapi()["components"]["schemas"]
    generated = {
        name: schemas[name] for name in _generated_creation_components()
    }
    rendered = json.dumps(generated, sort_keys=True).casefold()

    assert "65536" not in rendered
    assert "canonical" not in rendered
    assert "normalization" not in rendered
    assert "\\u0000" not in rendered
    assert "uniqueitems" not in rendered
    assert "duplicate" not in rendered
    assert "state=declared" not in rendered
    assert "only a declared" not in rendered
    assert "a declared slot" not in rendered
    assert "pattern" not in schemas["PlayerDeclaredText"]["properties"]["text"]
    assert "pattern" not in schemas["CustomValueEntry"]["properties"]["key"]
    assert (
        "uniqueItems"
        not in schemas["DistinguishingFeatures"]["properties"]["features"]
    )
    assert "uniqueItems" not in schemas["CustomValues"]["properties"]["entries"]


def test_frozen_creation_operation_has_no_generated_or_parallel_shape() -> None:
    schema = _app(_PlayerCharacterService()).openapi()
    operation = schema["paths"][_CREATE_PATH]["post"]

    assert set(operation) == {
        "tags",
        "summary",
        "description",
        "operationId",
        "parameters",
        "requestBody",
        "responses",
    }
    assert operation["requestBody"] == main._PLAYER_CHARACTER_CREATION_OPENAPI_EXTRA[
        "requestBody"
    ]
    assert operation["requestBody"]["content"] == {
        "application/json": {
            "schema": {"$ref": "#/components/schemas/CharacterCreationCommand"}
        }
    }
    assert "HTTPValidationError" not in json.dumps(operation)
    assert "ValidationError" not in json.dumps(operation)
    assert "security" not in operation
    assert "securitySchemes" not in schema["components"]


@pytest.mark.parametrize("cached", (False, True), ids=("uncached", "cached"))
def test_openapi_wrapper_detaches_preserves_aliases_and_repeats_stably(
    cached: bool,
) -> None:
    generated = _generated_creation_components()
    base_schemas = {
        "Unrelated": {"type": "object", "properties": {"value": {"type": "string"}}},
        "PlayerCharacterContractVersion": deepcopy(
            generated["PlayerCharacterContractVersion"]
        ),
    }
    base_schema: dict[str, Any] = {
        "openapi": "3.1.0",
        "info": {"title": "base", "version": "1"},
        "paths": {
            "/unrelated": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "ok",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/Unrelated"
                                    }
                                }
                            },
                        }
                    }
                }
            }
        },
        "components": {"schemas": base_schemas},
        "x-shared-schemas": base_schemas,
        "x-unrelated": {"kept": True},
    }
    base_snapshot = deepcopy(base_schema)
    app = FastAPI()
    app.openapi_schema = base_schema if cached else None
    default_calls = 0
    in_default = False

    def default_openapi() -> dict[str, Any]:
        nonlocal default_calls, in_default
        assert not in_default
        in_default = True
        try:
            default_calls += 1
            if not cached:
                app.openapi_schema = base_schema
            return base_schema
        finally:
            in_default = False

    app.openapi = default_openapi
    main._install_player_character_openapi_schemas(app)

    first = app.openapi()
    second = app.openapi()

    assert first is second is app.openapi_schema
    assert first is not base_schema
    assert default_calls == 1
    assert base_schema == base_snapshot
    assert base_schema["components"]["schemas"] is base_schema["x-shared-schemas"]
    assert first["components"]["schemas"] is first["x-shared-schemas"]
    assert first["paths"]["/unrelated"] == base_snapshot["paths"]["/unrelated"]
    assert first["x-unrelated"] == {"kept": True}
    assert all(
        first["components"]["schemas"][name] == definition
        for name, definition in generated.items()
    )
    _assert_all_local_refs_resolve(first)


@pytest.mark.parametrize(
    "collision_name",
    ("CharacterCreationCommand", "PlayerSubjectiveAuthority"),
    ids=("early-root", "late-definition"),
)
@pytest.mark.parametrize("cached", (False, True), ids=("uncached", "cached"))
def test_openapi_collision_preflight_is_failure_atomic(
    collision_name: str,
    cached: bool,
) -> None:
    base_schemas = {
        "Unrelated": {"type": "string"},
        collision_name: {"type": "integer", "title": "collision"},
    }
    base_schema: dict[str, Any] = {
        "openapi": "3.1.0",
        "info": {"title": "base", "version": "1"},
        "paths": {},
        "components": {"schemas": base_schemas},
        "x-shared-schemas": base_schemas,
    }
    snapshot = deepcopy(base_schema)
    original_names = tuple(base_schemas)
    app = FastAPI()
    original_cache = base_schema if cached else None
    app.openapi_schema = original_cache

    def default_openapi() -> dict[str, Any]:
        if not cached:
            app.openapi_schema = base_schema
        return base_schema

    app.openapi = default_openapi
    main._install_player_character_openapi_schemas(app)

    with pytest.raises(
        RuntimeError,
        match="Player Character OpenAPI component collision",
    ):
        app.openapi()

    assert app.openapi_schema is original_cache
    assert base_schema == snapshot
    assert tuple(base_schemas) == original_names
    assert base_schema["components"]["schemas"] is base_schema["x-shared-schemas"]


@pytest.mark.parametrize(
    "bad_ref",
    (
        "#/components/schemas/Missing",
        "https://example.invalid/external-schema",
    ),
    ids=("missing-local", "non-local"),
)
@pytest.mark.parametrize("cached", (False, True), ids=("uncached", "cached"))
def test_openapi_reference_failure_is_atomic_and_does_not_poison_cache(
    bad_ref: str,
    cached: bool,
) -> None:
    base_schemas = {"Unrelated": {"type": "string"}}
    base_schema: dict[str, Any] = {
        "openapi": "3.1.0",
        "info": {"title": "base", "version": "1"},
        "paths": {
            "/broken": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "broken",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": bad_ref}
                                }
                            },
                        }
                    }
                }
            }
        },
        "components": {"schemas": base_schemas},
        "x-shared-schemas": base_schemas,
    }
    snapshot = deepcopy(base_schema)
    app = FastAPI()
    original_cache = base_schema if cached else None
    app.openapi_schema = original_cache

    def default_openapi() -> dict[str, Any]:
        if not cached:
            app.openapi_schema = base_schema
        return base_schema

    app.openapi = default_openapi
    main._install_player_character_openapi_schemas(app)

    with pytest.raises(
        RuntimeError,
        match="Player Character OpenAPI reference integrity failure",
    ):
        app.openapi()

    assert app.openapi_schema is original_cache
    assert base_schema == snapshot
    assert base_schema["components"]["schemas"] is base_schema["x-shared-schemas"]


def test_openapi_installer_runs_once_only_for_normal_player_character_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    installations: list[FastAPI] = []
    original_installer = main._install_player_character_openapi_schemas

    def recording_installer(app: FastAPI) -> None:
        installations.append(app)
        original_installer(app)

    monkeypatch.setattr(
        main,
        "_install_player_character_openapi_schemas",
        recording_installer,
    )
    normal = _app(_PlayerCharacterService())
    demo_like = _app(None)

    assert installations == [normal]
    assert _CREATE_PATH in normal.openapi()["paths"]
    assert _CREATE_PATH not in demo_like.openapi()["paths"]
    assert (
        "CharacterCreationCommand"
        not in demo_like.openapi()["components"]["schemas"]
    )


def test_player_character_activation_preserves_exact_route_inventory() -> None:
    app = _app(_PlayerCharacterService())
    public_routes = {
        (route.path, tuple(sorted(route.methods or ())))
        for route in app.routes
        if route.path == "/health" or route.path.startswith("/v1/")
    }

    assert public_routes == {
        ("/health", ("GET",)),
        ("/v1/player-characters", ("POST",)),
        ("/v1/player-characters/eligible-for-run-entry", ("GET",)),
        ("/v1/player-characters/{player_character_id}", ("GET",)),
        (
            "/v1/player-characters/{player_character_id}/retirement",
            ("POST",),
        ),
        ("/v1/scenarios", ("GET",)),
        ("/v1/sessions", ("POST",)),
        ("/v1/sessions/{session_id}", ("GET",)),
        ("/v1/sessions/{session_id}/state", ("GET",)),
        ("/v1/sessions/{session_id}/view", ("GET",)),
        (
            "/v1/sessions/{session_id}/requests/{client_request_id}",
            ("GET",),
        ),
        ("/v1/sessions/{session_id}/actions", ("POST",)),
    }
    assert all(
        (path == _ELIGIBLE_PATH or "run" not in path.casefold())
        and "mutation" not in path.casefold()
        and "bind" not in path.casefold()
        for path, _ in public_routes
    )


def test_demo_composition_exposes_existing_player_character_routes_and_schema() -> None:
    from deviation_protocol.api.demo_composition import build_demo_runtime

    runtime = build_demo_runtime()
    app = main.create_app(services=runtime.services)
    schema = app.openapi()

    assert runtime.services.player_character_service is not None
    expected = {
        "/v1/player-characters/eligible-for-run-entry": {"get"},
        "/v1/player-characters": {"post"},
        "/v1/player-characters/{player_character_id}": {"get"},
        "/v1/player-characters/{player_character_id}/retirement": {"post"},
    }
    assert {
        path: set(schema["paths"][path]) for path in expected
    } == expected
    assert "CharacterCreationCommand" in schema["components"]["schemas"]
