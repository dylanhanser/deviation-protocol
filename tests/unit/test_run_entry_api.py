from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute

from deviation_protocol.api import main
from deviation_protocol.api.dependencies import (
    ApiServices,
    get_current_principal,
    get_run_entry_service,
)
from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.player_character_projection import (
    PlayerCharacterSelfProjection,
)
from deviation_protocol.application.run_entry_service import (
    RunEntryCommand,
    RunEntryDecision,
    RunEntryDecisionCode,
    RunEntryIntegrityError,
    RunEntryResult,
)
from deviation_protocol.application.run_operations import (
    RunEntryPublicOperationKey,
)
from deviation_protocol.domain.player_character import (
    PlayerCharacterContractVersion,
    PlayerCharacterId,
    PlayerCharacterLifecycle,
    PlayerCharacterRevision,
)
from deviation_protocol.domain.run import RunId


_PATH = "/v1/runs"
_PRINCIPAL = RequestPrincipal(
    player_id="player.run-entry-test",
    authentication_scheme="test",
)
_VALID_KEY = "Entry.Key:Case-1"
_VALID_BODY = {
    "player_character_id": "pc.test-owned",
    "expected_record_revision": 1,
    "scenario_id": "death_certificate",
}


def _success(
    *,
    scenario_id: str = "death_certificate",
    player_character_id: str = "pc.test-owned",
    revision: int = 1,
    lifecycle: PlayerCharacterLifecycle = PlayerCharacterLifecycle.ACTIVE,
) -> RunEntryResult:
    return RunEntryResult(
        run_id=RunId(value="run.test-entry"),
        session_id="session.test-entry",
        scenario_id=scenario_id,
        player_character=PlayerCharacterSelfProjection(
            player_character_id=PlayerCharacterId(value=player_character_id),
            contract_version=PlayerCharacterContractVersion.V1,
            record_revision=PlayerCharacterRevision(value=revision),
            lifecycle=lifecycle,
        ),
    )


class _EntryService:
    def __init__(self, result: Any | None = None) -> None:
        self.result = _success() if result is None else result
        self.error: BaseException | None = None
        self.calls: list[tuple[RequestPrincipal, RunEntryCommand]] = []

    async def enter(
        self,
        principal: RequestPrincipal,
        *,
        command: RunEntryCommand,
    ) -> Any:
        self.calls.append((principal, command))
        if self.error is not None:
            raise self.error
        return self.result

    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"the API accessed an unauthorized service member: {name}")


def _app(service: _EntryService) -> FastAPI:
    services = ApiServices(
        session_service=object(),  # type: ignore[arg-type]
        turn_orchestrator=object(),  # type: ignore[arg-type]
        run_entry_service=service,  # type: ignore[arg-type]
    )
    app = main.create_app(services=services)
    app.state.api_services = services
    app.dependency_overrides[get_current_principal] = lambda: _PRINCIPAL
    return app


@dataclass(frozen=True, slots=True)
class _Response:
    status_code: int
    body: bytes
    headers: httpx.Headers

    def json(self) -> Any:
        return json.loads(self.body)


async def _request_async(
    app: FastAPI,
    method: str = "POST",
    path: str = _PATH,
    *,
    json_body: Any = _VALID_BODY,
    content: bytes | None = None,
    headers: Any = None,
    raise_app_exceptions: bool = False,
) -> httpx.Response:
    transport = httpx.ASGITransport(
        app=app,
        raise_app_exceptions=raise_app_exceptions,
    )
    options: dict[str, Any] = {"headers": headers}
    if content is None:
        options["json"] = json_body
    else:
        options["content"] = content
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        return await client.request(method, path, **options)


def _post(
    app: FastAPI,
    *,
    json_body: Any = _VALID_BODY,
    content: bytes | None = None,
    headers: Any = None,
) -> _Response:
    response = asyncio.run(
        _request_async(
            app,
            json_body=json_body,
            content=content,
            headers=headers or {"Idempotency-Key": _VALID_KEY},
        )
    )
    return _Response(response.status_code, response.content, response.headers)


async def _raw_request(
    app: FastAPI,
    *,
    headers: list[tuple[bytes, bytes]],
    body: bytes,
) -> _Response:
    request_sent = False
    response_start: dict[str, Any] | None = None
    response_body = bytearray()

    async def receive() -> dict[str, Any]:
        nonlocal request_sent
        if request_sent:
            return {"type": "http.disconnect"}
        request_sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        nonlocal response_start
        if message["type"] == "http.response.start":
            response_start = message
        elif message["type"] == "http.response.body":
            response_body.extend(message.get("body", b""))

    await app(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": _PATH,
            "raw_path": _PATH.encode("ascii"),
            "query_string": b"",
            "headers": headers,
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
            "root_path": "",
        },
        receive,
        send,
    )
    assert response_start is not None
    return _Response(
        response_start["status"],
        bytes(response_body),
        httpx.Headers(response_start["headers"]),
    )


def _validation_error() -> dict[str, Any]:
    return {
        "error": {
            "error_code": "REQUEST_VALIDATION_FAILED",
            "message": "Request validation failed",
        }
    }


def _internal_error() -> dict[str, Any]:
    return {
        "error": {
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "Internal server error",
        }
    }


def test_success_forwards_exact_trusted_command_once_and_allowlists_response() -> None:
    service = _EntryService()
    app = _app(service)

    response = _post(
        app,
        headers={
            "Idempotency-Key": _VALID_KEY,
            "X-Player-Id": "attacker",
            "X-Controller-Id": "attacker-controller",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "run_id": "run.test-entry",
        "session_id": "session.test-entry",
        "scenario_id": "death_certificate",
        "player_character": {
            "player_character_id": {"value": "pc.test-owned"},
            "contract_version": "structured-player-character/v1",
            "record_revision": {"value": 1},
            "lifecycle": "active",
        },
    }
    assert len(service.calls) == 1
    principal, command = service.calls[0]
    assert principal is _PRINCIPAL
    assert type(command) is RunEntryCommand
    assert command.public_operation_key.value == _VALID_KEY
    assert command.player_character_id == PlayerCharacterId(value="pc.test-owned")
    assert command.expected_record_revision == PlayerCharacterRevision(value=1)
    assert command.scenario_id == "death_certificate"
    serialized = response.body.decode("utf-8")
    for forbidden in (
        "attacker",
        "controller",
        "continuous_story_line",
        "source.production",
        "operation_id",
        "receipt",
        "fingerprint",
        "transaction",
        "state_version",
        "provider",
    ):
        assert forbidden not in serialized.casefold()


def test_projection_constructs_a_new_detached_nested_allowlist() -> None:
    result = _success()
    command = RunEntryCommand(
        public_operation_key=RunEntryPublicOperationKey(value=_VALID_KEY),
        player_character_id=PlayerCharacterId(value="pc.test-owned"),
        expected_record_revision=PlayerCharacterRevision(value=1),
        scenario_id="death_certificate",
    )

    projected = main._project_run_entry_success(result, command=command)

    assert projected.player_character is not result.player_character
    assert (
        projected.player_character.player_character_id
        is not result.player_character.player_character_id
    )
    assert (
        projected.player_character.record_revision
        is not result.player_character.record_revision
    )
    assert set(projected.model_dump()) == {
        "run_id",
        "session_id",
        "scenario_id",
        "player_character",
    }
    assert set(projected.player_character.model_dump()) == {
        "player_character_id",
        "contract_version",
        "record_revision",
        "lifecycle",
    }


def test_exact_replay_is_stable_and_each_request_calls_the_service_once() -> None:
    service = _EntryService()
    app = _app(service)

    first = _post(app)
    replay = _post(app)

    assert first.status_code == replay.status_code == 200
    assert first.body == replay.body
    assert len(service.calls) == 2
    assert service.calls[0][1] == service.calls[1][1]


@pytest.mark.asyncio
async def test_raw_header_and_media_type_rejections_precede_service() -> None:
    body = json.dumps(_VALID_BODY, separators=(",", ":")).encode()
    valid_type = (b"content-type", b"application/json")
    valid_key = (b"idempotency-key", _VALID_KEY.encode("ascii"))
    cases = {
        "missing-content-type": [valid_key],
        "duplicate-content-type": [valid_type, valid_type, valid_key],
        "conflicting-content-type": [
            valid_type,
            (b"content-type", b"text/plain"),
            valid_key,
        ],
        "combined-content-type": [
            (b"content-type", b"application/json,application/json"),
            valid_key,
        ],
        "non-json-content-type": [(b"content-type", b"text/plain"), valid_key],
        "non-ascii-content-type": [(b"content-type", b"\xff"), valid_key],
        "non-ascii-content-parameter": [
            (b"content-type", b"application/json; charset=\xff"),
            valid_key,
        ],
        "missing-key": [valid_type],
        "duplicate-key": [valid_type, valid_key, valid_key],
        "comma-folded-key": [
            valid_type,
            (b"idempotency-key", b"Entry.One,Entry.Two"),
        ],
        "empty-key": [valid_type, (b"idempotency-key", b"")],
        "whitespace-key": [valid_type, (b"idempotency-key", b" Entry.Key")],
        "bad-first-character": [valid_type, (b"idempotency-key", b".Entry")],
        "bad-punctuation": [valid_type, (b"idempotency-key", b"Entry/Key")],
        "control-key": [valid_type, (b"idempotency-key", b"Entry\x1fKey")],
        "non-ascii-key": [valid_type, (b"idempotency-key", b"Entry\xff")],
        "over-bound-key": [valid_type, (b"idempotency-key", b"A" * 129)],
    }
    for case_id, headers in cases.items():
        service = _EntryService()
        response = await _raw_request(_app(service), headers=headers, body=body)
        assert response.status_code == 422, case_id
        assert response.json() == _validation_error(), case_id
        assert service.calls == [], case_id


@pytest.mark.asyncio
async def test_valid_raw_headers_preserve_exact_key_case_and_boundaries() -> None:
    body = json.dumps(_VALID_BODY, separators=(",", ":")).encode()
    cases = (
        (b"APPLICATION/JSON", b"A"),
        (b" \tapplication/json \t; charset=utf-8", b"A" * 128),
        (b"application/json; ; opaque", b"Case.Sensitive:Key-1"),
    )
    for content_type, key in cases:
        service = _EntryService()
        response = await _raw_request(
            _app(service),
            headers=[
                (b"content-type", content_type),
                (b"idempotency-key", key),
            ],
            body=body,
        )
        assert response.status_code == 200
        assert len(service.calls) == 1
        assert service.calls[0][1].public_operation_key.value == key.decode("ascii")


@pytest.mark.parametrize(
    "body",
    (
        {},
        {"expected_record_revision": 1, "scenario_id": "death_certificate"},
        {"player_character_id": "pc.test-owned", "scenario_id": "death_certificate"},
        {"player_character_id": "pc.test-owned", "expected_record_revision": 1},
        {**_VALID_BODY, "expected_record_revision": None},
        {**_VALID_BODY, "expected_record_revision": True},
        {**_VALID_BODY, "expected_record_revision": 1.0},
        {**_VALID_BODY, "expected_record_revision": "1"},
        {**_VALID_BODY, "expected_record_revision": 0},
        {**_VALID_BODY, "expected_record_revision": 2**63},
        {**_VALID_BODY, "player_character_id": " pc.test-owned"},
        {**_VALID_BODY, "player_character_id": "pc/test"},
        {**_VALID_BODY, "player_character_id": "A" * 129},
        {**_VALID_BODY, "scenario_id": "death certificate"},
        {**_VALID_BODY, "scenario_id": "death_certificate\u0000"},
        {**_VALID_BODY, "controller_id": "controller.attacker"},
        {**_VALID_BODY, "player_id": "player.attacker"},
        {**_VALID_BODY, "run_id": "run.attacker"},
        [],
        "not-an-object",
        None,
        True,
    ),
)
def test_strict_request_body_rejects_wrong_shapes_types_bounds_and_authority(
    body: Any,
) -> None:
    service = _EntryService()

    response = _post(_app(service), json_body=body)

    assert response.status_code == 422
    assert response.json() == _validation_error()
    assert service.calls == []


@pytest.mark.parametrize(
    "content",
    (
        b"{",
        b"",
        b"not-json",
        b'[^]',
    ),
)
def test_malformed_json_fails_with_fixed_envelope_before_service(content: bytes) -> None:
    service = _EntryService()

    response = _post(
        _app(service),
        content=content,
        headers={
            "Content-Type": "application/json",
            "Idempotency-Key": _VALID_KEY,
        },
    )

    assert response.status_code == 422
    assert response.json() == _validation_error()
    assert service.calls == []


@pytest.mark.asyncio
async def test_raw_duplicate_request_member_is_rejected_before_service() -> None:
    service = _EntryService()
    body = (
        b'{"player_character_id":"pc.test-owned",'
        b'"expected_record_revision":1,'
        b'"expected_record_revision":2,'
        b'"scenario_id":"death_certificate"}'
    )

    response = await _raw_request(
        _app(service),
        headers=[
            (b"content-type", b"application/json"),
            (b"idempotency-key", _VALID_KEY.encode("ascii")),
        ],
        body=body,
    )

    assert response.status_code == 422
    assert response.json() == _validation_error()
    assert service.calls == []
    rendered = response.body.decode("utf-8").casefold()
    for forbidden in (
        "duplicate json member",
        "jsondecodeerror",
        "expected_record_revision",
        "pc.test-owned",
        "death_certificate",
        "traceback",
        "fastapi",
        "pydantic",
    ):
        assert forbidden not in rendered


@pytest.mark.parametrize(
    ("code", "status_code", "error_code", "message"),
    (
        (
            RunEntryDecisionCode.AUTHORIZATION_FAILED,
            404,
            "PLAYER_CHARACTER_NOT_FOUND",
            "Player character was not found",
        ),
        (
            RunEntryDecisionCode.IDEMPOTENCY_CONFLICT,
            409,
            "IDEMPOTENCY_CONFLICT",
            "Idempotency key was reused",
        ),
        (
            RunEntryDecisionCode.PLAYER_CHARACTER_STALE,
            409,
            "PLAYER_CHARACTER_STALE",
            "Player character revision is stale",
        ),
        (
            RunEntryDecisionCode.PLAYER_CHARACTER_NOT_ELIGIBLE,
            409,
            "PLAYER_CHARACTER_NOT_ELIGIBLE",
            "Player character is not eligible for Run entry",
        ),
        (
            RunEntryDecisionCode.INVALID_SCENARIO_DEFINITION,
            422,
            "INVALID_SCENARIO_DEFINITION",
            "Scenario definition is not available",
        ),
        (
            RunEntryDecisionCode.RUN_ENTRY_CONFLICT,
            409,
            "RUN_ENTRY_CONFLICT",
            "Run entry conflicts with current state",
        ),
    ),
)
def test_decisions_preserve_service_precedence_and_use_fixed_private_safe_errors(
    code: RunEntryDecisionCode,
    status_code: int,
    error_code: str,
    message: str,
) -> None:
    service = _EntryService(RunEntryDecision(code=code))

    response = _post(_app(service))

    assert response.status_code == status_code
    assert response.json() == {
        "error": {"error_code": error_code, "message": message}
    }
    assert len(service.calls) == 1
    serialized = response.body.decode("utf-8").casefold()
    for private in (
        "pc.test-owned",
        "player.run-entry-test",
        "controller",
        "binding",
        "mysql",
        "constraint",
    ):
        assert private not in serialized


@pytest.mark.parametrize(
    "result",
    (
        _success(scenario_id="other-scenario"),
        _success(player_character_id="pc.other"),
        _success(revision=2),
        _success(lifecycle=PlayerCharacterLifecycle.RETIRED),
        object(),
    ),
)
def test_cross_bound_or_unexpected_success_fails_closed_without_retry(result: Any) -> None:
    service = _EntryService(result)

    response = _post(_app(service))

    assert response.status_code == 500
    assert response.json() == _internal_error()
    assert len(service.calls) == 1


def test_actual_state_mutation_of_success_or_decision_fails_closed() -> None:
    mutated_success = _success()
    mutated_success.__dict__["private_sql"] = "mysql://private/constraint"
    success_service = _EntryService(mutated_success)
    success_response = _post(_app(success_service))
    assert success_response.status_code == 500
    assert success_response.json() == _internal_error()
    assert len(success_service.calls) == 1
    assert "mysql" not in success_response.body.decode("utf-8").casefold()

    mutated_decision = RunEntryDecision(code=RunEntryDecisionCode.RUN_ENTRY_CONFLICT)
    object.__setattr__(mutated_decision, "code", "PRIVATE_CONSTRAINT")
    decision_service = _EntryService(mutated_decision)
    decision_response = _post(_app(decision_service))
    assert decision_response.status_code == 500
    assert decision_response.json() == _internal_error()
    assert len(decision_service.calls) == 1
    assert "private" not in decision_response.body.decode("utf-8").casefold()


@pytest.mark.parametrize(
    "error",
    (
        RunEntryIntegrityError("mysql://secret SQL uq_private pc.secret"),
        RuntimeError("C:\\private\\repository.py constraint private_id"),
        ValueError("integrity diagnostic transaction.secret"),
    ),
)
def test_service_and_integrity_failures_are_sanitized_once(error: BaseException) -> None:
    service = _EntryService()
    service.error = error

    response = _post(_app(service))

    assert response.status_code == 500
    assert response.json() == _internal_error()
    assert len(service.calls) == 1
    rendered = response.body.decode("utf-8").casefold()
    for forbidden in (
        "mysql",
        "secret",
        "sql",
        "constraint",
        "repository",
        "private_id",
        "diagnostic",
    ):
        assert forbidden not in rendered


@pytest.mark.asyncio
async def test_service_cancellation_propagates_same_identity_without_retry() -> None:
    cancellation = asyncio.CancelledError()
    service = _EntryService()
    service.error = cancellation

    with pytest.raises(asyncio.CancelledError) as exc_info:
        await _request_async(
            _app(service),
            headers={"Idempotency-Key": _VALID_KEY},
            raise_app_exceptions=True,
        )

    assert exc_info.value is cancellation
    assert len(service.calls) == 1


def test_dependency_failures_call_no_service_and_use_existing_envelopes() -> None:
    service = _EntryService()
    app = _app(service)

    def missing_principal() -> RequestPrincipal:
        raise RequestValidationError([])

    app.dependency_overrides[get_current_principal] = missing_principal
    missing = _post(app)
    assert missing.status_code == 422
    assert missing.json() == _validation_error()
    assert service.calls == []

    app = _app(service)

    def broken_service_dependency() -> Any:
        raise RuntimeError("private dependency configuration")

    app.dependency_overrides[get_run_entry_service] = broken_service_dependency
    broken = _post(app)
    assert broken.status_code == 500
    assert broken.json() == _internal_error()
    assert service.calls == []
    assert "private" not in broken.body.decode("utf-8").casefold()


def test_route_registration_is_exact_conditional_and_preserves_unrelated_behavior() -> None:
    service = _EntryService()
    app = _app(service)
    run_routes = [
        route
        for route in app.routes
        if isinstance(route, APIRoute) and route.path == _PATH
    ]
    assert len(run_routes) == 1
    assert run_routes[0].methods == {"POST"}
    assert run_routes[0].operation_id == "enter_run"
    assert run_routes[0].summary == "Enter a Run"

    get_response = asyncio.run(_request_async(app, "GET", _PATH))
    health_response = asyncio.run(_request_async(app, "GET", "/health"))
    assert get_response.status_code == 405
    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok", "phase": "3.0"}

    absent_services = ApiServices(
        session_service=object(),  # type: ignore[arg-type]
        turn_orchestrator=object(),  # type: ignore[arg-type]
    )
    absent_app = main.create_app(services=absent_services)
    assert _PATH not in {route.path for route in absent_app.routes}
    schemas = absent_app.openapi().get("components", {}).get("schemas", {})
    assert "RunEntryRequest" not in schemas
    assert "RunEntryResponse" not in schemas
