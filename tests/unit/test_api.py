from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest
from fastapi import FastAPI

from deviation_protocol.api import main
from deviation_protocol.api.dependencies import ApiServices, get_current_principal
from deviation_protocol.application.errors import (
    IdempotencyConflictError,
    SessionNotFoundError,
    SnapshotContentVersionMismatchError,
)
from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.resolution import ResolutionStatus
from deviation_protocol.application.session_service import (
    PlayerVisibleStateProjection,
    PublicResource,
    SessionCreationResult,
    SessionMetadata,
)
from deviation_protocol.application.turn_response import TurnResponse
from deviation_protocol.domain.actions import ActionSubmission, ActionType
from deviation_protocol.domain.narrative import NarrativeFrame
from deviation_protocol.domain.scenario import FrameMode
from deviation_protocol.domain.state import DomainErrorCode, DomainRuleViolation
from deviation_protocol.infrastructure.errors import OptimisticLockError


NOW = datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc)


@dataclass(frozen=True)
class AsgiResponse:
    status_code: int
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body)

    @property
    def text(self) -> str:
        return self.body.decode("utf-8")


class AsgiClient:
    """Minimal in-process HTTP driver; avoids Starlette's optional httpx2 package."""

    def __init__(self, app: FastAPI, *, raise_server_exceptions: bool = True) -> None:
        self.app = app
        self.raise_server_exceptions = raise_server_exceptions

    def __enter__(self) -> AsgiClient:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def get(self, path: str) -> AsgiResponse:
        return asyncio.run(self._request("GET", path, None))

    def post(
        self,
        path: str,
        *,
        json: dict[str, Any],
        query_string: bytes = b"",
        headers: tuple[tuple[bytes, bytes], ...] = (),
    ) -> AsgiResponse:
        return asyncio.run(
            self._request(
                "POST",
                path,
                json,
                query_string=query_string,
                headers=headers,
            )
        )

    async def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None,
        *,
        query_string: bytes = b"",
        headers: tuple[tuple[bytes, bytes], ...] = (),
    ) -> AsgiResponse:
        body = json.dumps(payload).encode("utf-8") if payload is not None else b""
        sent_request = False
        response_status = 500
        response_parts: list[bytes] = []

        async def receive() -> dict[str, Any]:
            nonlocal sent_request
            if not sent_request:
                sent_request = True
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.disconnect"}

        async def send(message: dict[str, Any]) -> None:
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message["status"]
            elif message["type"] == "http.response.body":
                response_parts.append(message.get("body", b""))

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": query_string,
            "root_path": "",
            "headers": [(b"content-type", b"application/json"), *headers],
            "client": ("127.0.0.1", 1),
            "server": ("testserver", 80),
        }
        try:
            await self.app(scope, receive, send)
        except Exception:
            if self.raise_server_exceptions:
                raise
        return AsgiResponse(response_status, b"".join(response_parts))


def metadata(session_id: str = "session-1") -> SessionMetadata:
    return SessionMetadata(
        session_id=session_id,
        phase="AWAITING_ACTION",
        state_version=0,
        content_version="demo-1",
        created_at=NOW,
        updated_at=NOW,
        character_definition_id="character.player.default",
        character_display_name="测试调查员",
    )


def creation_result(session_id: str = "session-1") -> SessionCreationResult:
    return SessionCreationResult(
        **metadata(session_id).model_dump(),
        scenario_id="scenario.test",
        narrative_frame=NarrativeFrame(
            frame_id="frame.test",
            scenario_id="scenario.test",
            phase_id="phase.test",
            mode=FrameMode.FLOW,
            current_location_id="location.test",
            target_length=100,
            min_length=50,
            max_length=150,
            decision_required=False,
            stop_condition="CONTINUE",
        ),
    )


class FakeSessionService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []
        self.error: Exception | None = None

    async def create(
        self,
        principal: RequestPrincipal,
        *,
        client_request_id: str,
        character_definition_id: str,
        scenario_id: str,
    ) -> SessionCreationResult:
        self.calls.append(
            (
                "create",
                (principal, client_request_id, character_definition_id, scenario_id),
            )
        )
        if self.error:
            raise self.error
        return creation_result()

    async def get_metadata(
        self, principal: RequestPrincipal, session_id: str
    ) -> SessionMetadata:
        self.calls.append(("metadata", (principal, session_id)))
        if self.error:
            raise self.error
        if principal.player_id != "player-1":
            raise SessionNotFoundError(session_id)
        return metadata(session_id)

    async def get_visible_state(
        self, principal: RequestPrincipal, session_id: str
    ) -> PlayerVisibleStateProjection:
        self.calls.append(("state", (principal, session_id)))
        if self.error:
            raise self.error
        if principal.player_id != "player-1":
            raise SessionNotFoundError(session_id)
        return PlayerVisibleStateProjection(
            session_id=session_id,
            phase="AWAITING_ACTION",
            state_version=0,
            content_version="demo-1",
            player_id="player-1",
            character_definition_id="character.player.default",
            attributes=(("focus", 4), ("strength", 5)),
            resources=(PublicResource(resource_id="stamina", current=10, maximum=10),),
            wallet=(),
            inventory=(),
            equipped_items=(),
            skills=(),
            visible_npcs=(),
            quests=(),
        )

    async def require_owner(
        self, principal: RequestPrincipal, session_id: str
    ) -> None:
        self.calls.append(("owner", (principal, session_id)))
        if self.error:
            raise self.error
        if principal.player_id != "player-1":
            raise SessionNotFoundError(session_id)


class FakeOrchestrator:
    def __init__(self) -> None:
        self.submissions: list[ActionSubmission] = []
        self.error: Exception | None = None
        self.responses: dict[tuple[str, str], TurnResponse] = {}

    async def handle(self, submission: ActionSubmission) -> TurnResponse:
        self.submissions.append(submission)
        if self.error:
            raise self.error
        key = (submission.session_id, submission.client_request_id)
        existing = self.responses.get(key)
        if existing is not None:
            if existing.action_signature != submission.action_signature():
                raise IdempotencyConflictError(submission.session_id)
            return existing
        narrative = submission.action_type in {ActionType.EXPLORE, ActionType.CHOOSE}
        mutation = submission.action_type in {
            ActionType.EQUIP,
            ActionType.USE_ITEM,
            ActionType.USE_SKILL,
        }
        rejected = submission.action_type is ActionType.LEARN_SKILL
        query = submission.action_type is ActionType.INSPECT_STATUS
        kind = (
            ResolutionStatus.NARRATIVE_REQUIRED
            if narrative
            else (
                ResolutionStatus.REJECTED_LOCAL
                if rejected
                else ResolutionStatus.RESOLVED_LOCAL
            )
        )
        query_result = {"attributes": {"strength": 5}} if query else None
        response = TurnResponse(
            session_id=submission.session_id,
            client_request_id=submission.client_request_id,
            action_signature=submission.action_signature(),
            resolution_kind=kind,
            result_code=(
                "VALIDATED_INTENT_REQUIRES_NARRATIVE"
                if narrative
                else (
                    "SKILL_LEARNING_NOT_AUTHORIZED"
                    if rejected
                    else "LOCAL_ACTION_COMPLETED"
                )
            ),
            feedback_code=(
                "NARRATIVE_REQUIRED"
                if narrative
                else (
                    "SKILL_LEARNING_NOT_AUTHORIZED"
                    if rejected
                    else "LOCAL_ACTION_COMPLETED"
                )
            ),
            feedback_parameters=query_result or {},
            resulting_state_version=1 if mutation else 0,
            state_changed=mutation,
            narrative_required=narrative,
            narrative_pending=narrative,
            local_query_result=query_result,
        )
        self.responses[key] = response
        return response


@pytest.fixture
def api() -> tuple[AsgiClient, FakeSessionService, FakeOrchestrator]:
    service = FakeSessionService()
    orchestrator = FakeOrchestrator()
    services = ApiServices(
        session_service=service,  # type: ignore[arg-type]
        turn_orchestrator=orchestrator,
    )
    app = main.create_app(services=services)
    app.state.api_services = services
    app.dependency_overrides[get_current_principal] = lambda: RequestPrincipal(
        player_id="player-1", authentication_scheme="test"
    )
    return AsgiClient(app), service, orchestrator


def test_create_app_does_not_build_or_connect_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        main,
        "build_default_services",
        lambda: (_ for _ in ()).throw(AssertionError("must stay lazy")),
    )
    created = main.create_app()
    assert created.title == "Deviation Protocol"


def test_importing_api_module_does_not_read_json_or_create_engine() -> None:
    repository_root = Path(__file__).parents[2]
    script = """
from pathlib import Path
import sqlalchemy.ext.asyncio

original_open = Path.open
def guarded_open(path, *args, **kwargs):
    if path.suffix.lower() == '.json':
        raise AssertionError('API import read a JSON content file')
    return original_open(path, *args, **kwargs)

Path.open = guarded_open
sqlalchemy.ext.asyncio.create_async_engine = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('API import created an engine'))
import deviation_protocol.api.main
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repository_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_health_response_does_not_expose_runtime_configuration(
    api: tuple[AsgiClient, FakeSessionService, FakeOrchestrator],
) -> None:
    client, _, _ = api
    with client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "phase": "2.2a"}


def test_default_lifespan_disposes_its_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    service = FakeSessionService()
    orchestrator = FakeOrchestrator()

    class Engine:
        def __init__(self) -> None:
            self.dispose_calls = 0

        async def dispose(self) -> None:
            self.dispose_calls += 1

    engine = Engine()
    services = ApiServices(
        session_service=service,  # type: ignore[arg-type]
        turn_orchestrator=orchestrator,
        engine=engine,  # type: ignore[arg-type]
    )
    monkeypatch.setattr(main, "build_default_services", lambda: services)
    app = main.create_app()

    async def drive_lifespan() -> None:
        async with app.router.lifespan_context(app):
            assert app.state.api_services is services
            assert engine.dispose_calls == 0

    asyncio.run(drive_lifespan())
    assert engine.dispose_calls == 1


def test_create_app_supports_dependency_override(
    api: tuple[AsgiClient, FakeSessionService, FakeOrchestrator],
) -> None:
    client, service, _ = api
    with client:
        response = client.post(
            "/v1/sessions",
            json={
                "client_request_id": "create-1",
                "character_definition_id": "character.player.default",
                "scenario_id": "scenario.test",
            },
        )
    assert response.status_code == 201
    used_principal = service.calls[0][1][0]
    assert used_principal.player_id == "player-1"
    assert response.json()["scenario_id"] == "scenario.test"
    assert response.json()["narrative_frame"]["frame_id"] == "frame.test"


@pytest.mark.parametrize(
    "forged_field",
    [
        "scenario_content_version",
        "initial_phase",
        "facts",
        "clues",
        "clock",
        "scenario_runtime",
        "narrative_frame",
        "verified_scenario_event",
        "trusted_authority",
    ],
)
def test_create_body_rejects_all_internal_scenario_state(
    api: tuple[AsgiClient, FakeSessionService, FakeOrchestrator],
    forged_field: str,
) -> None:
    client, service, _ = api
    with client:
        response = client.post(
            "/v1/sessions",
            json={
                "client_request_id": "create-forged-scenario",
                "character_definition_id": "character.player.default",
                "scenario_id": "scenario.test",
                forged_field: "forged",
            },
        )
    assert response.status_code == 422
    assert service.calls == []


def test_create_requires_explicit_scenario_id(
    api: tuple[AsgiClient, FakeSessionService, FakeOrchestrator],
) -> None:
    client, service, _ = api
    with client:
        response = client.post(
            "/v1/sessions",
            json={
                "client_request_id": "create-without-scenario",
                "character_definition_id": "character.player.default",
            },
        )
    assert response.status_code == 422
    assert service.calls == []


def test_query_and_headers_cannot_override_principal(
    api: tuple[AsgiClient, FakeSessionService, FakeOrchestrator],
) -> None:
    client, service, _ = api
    with client:
        response = client.post(
            "/v1/sessions",
            json={
                "client_request_id": "create-context",
                "character_definition_id": "character.player.default",
                "scenario_id": "scenario.test",
            },
            query_string=b"player_id=other-player",
            headers=(
                (b"x-player-id", b"other-player"),
                (b"authorization", b"Bearer forged-player"),
            ),
        )
    assert response.status_code == 201
    assert service.calls[0][1][0].player_id == "player-1"


@pytest.mark.parametrize(
    "forged_field",
    [
        "player_id",
        "session_id",
        "route",
        "authorization",
        "catalog",
        "facts",
        "trusted_resolution_context",
        "gateway_decision",
        "narrative_frame",
        "suggested_actions",
        "allowed_choices",
        "scenario_version",
    ],
)
def test_action_body_rejects_identity_and_internal_injection(
    api: tuple[AsgiClient, FakeSessionService, FakeOrchestrator], forged_field: str
) -> None:
    client, _, orchestrator = api
    body = {
        "turn_id": "turn-1",
        "client_request_id": "action-1",
        "action_type": "INSPECT_STATUS",
        forged_field: "forged",
    }
    with client:
        response = client.post("/v1/sessions/session-1/actions", json=body)
    assert response.status_code == 422
    assert response.json()["error"]["error_code"] == "REQUEST_VALIDATION_FAILED"
    assert orchestrator.submissions == []


@pytest.mark.parametrize(
    "invalid_fields",
    [
        {"description": "x" * 151},
        {"dialogue": "unsafe\u202etext"},
        {"target_ids": [f"target-{index}" for index in range(17)]},
    ],
)
def test_action_body_rejects_oversized_or_controlled_input(
    api: tuple[AsgiClient, FakeSessionService, FakeOrchestrator],
    invalid_fields: dict[str, Any],
) -> None:
    client, _, orchestrator = api
    with client:
        response = client.post(
            "/v1/sessions/session-1/actions",
            json={
                "turn_id": "turn-1",
                "client_request_id": "invalid-action",
                "action_type": "EXPLORE",
                **invalid_fields,
            },
        )
    assert response.status_code == 422
    assert response.json()["error"] == {
        "error_code": "REQUEST_VALIDATION_FAILED",
        "message": "Request validation failed",
    }
    assert "unsafe" not in response.text
    assert orchestrator.submissions == []


def test_create_body_cannot_choose_player_id(
    api: tuple[AsgiClient, FakeSessionService, FakeOrchestrator],
) -> None:
    client, service, _ = api
    with client:
        response = client.post(
            "/v1/sessions",
            json={
                "client_request_id": "create-1",
                "character_definition_id": "character.player.default",
                "scenario_id": "scenario.test",
                "player_id": "other-player",
            },
        )
    assert response.status_code == 422
    assert service.calls == []


def test_session_metadata_and_visible_state_are_safe(
    api: tuple[AsgiClient, FakeSessionService, FakeOrchestrator],
) -> None:
    client, _, _ = api
    with client:
        metadata_response = client.get("/v1/sessions/session-1")
        state_response = client.get("/v1/sessions/session-1/state")
    assert metadata_response.status_code == state_response.status_code == 200
    metadata_payload = metadata_response.json()
    state_payload = state_response.json()
    assert not ({"snapshot", "random_seed", "npcs", "database_url"} & metadata_payload.keys())
    assert state_payload["visible_npcs"] == []
    assert "npcs" not in state_payload


def test_openapi_excludes_trusted_and_persistence_only_fields(
    api: tuple[AsgiClient, FakeSessionService, FakeOrchestrator],
) -> None:
    client, _, _ = api
    with client:
        response = client.get("/openapi.json")
    assert response.status_code == 200
    rendered = json.dumps(response.json(), ensure_ascii=False).lower()
    for forbidden in (
        "requestprincipal",
        "trustedresolutioncontext",
        "gatewaydecision",
        "narrativefact",
        "action_signature",
        "anomaly_evaluation_required",
        "verifiedscenarioevent",
        "trustedscenarioeventsource",
        "scenariodecisionselected",
        "player.decision.selected",
    ):
        assert forbidden not in rendered


def test_other_player_cannot_read_or_submit_actions(
    api: tuple[AsgiClient, FakeSessionService, FakeOrchestrator],
) -> None:
    client, _, orchestrator = api
    client.app.dependency_overrides[get_current_principal] = lambda: RequestPrincipal(
        player_id="other-player", authentication_scheme="test"
    )
    with client:
        read = client.get("/v1/sessions/session-1")
        state = client.get("/v1/sessions/session-1/state")
        action = client.post(
            "/v1/sessions/session-1/actions",
            json={
                "turn_id": "turn-1",
                "client_request_id": "action-1",
                "action_type": "INSPECT_STATUS",
            },
        )
    assert read.status_code == state.status_code == action.status_code == 404
    assert orchestrator.submissions == []


@pytest.mark.parametrize(
    ("action_type", "extra", "expected_kind", "state_changed"),
    [
        ("INSPECT_STATUS", {}, "RESOLVED_LOCAL", False),
        ("EQUIP", {"item_instance_id": "item-1", "equipment_slot_id": "hand.main"}, "RESOLVED_LOCAL", True),
        ("USE_ITEM", {"item_instance_id": "item-1"}, "RESOLVED_LOCAL", True),
        ("USE_SKILL", {"skill_definition_id": "skill.observation"}, "RESOLVED_LOCAL", True),
        (
            "LEARN_SKILL",
            {"skill_definition_id": "skill.observation"},
            "REJECTED_LOCAL",
            False,
        ),
        ("EXPLORE", {"description": "Inspect the corridor"}, "NARRATIVE_REQUIRED", False),
    ],
)
def test_action_api_exposes_local_and_pending_results(
    api: tuple[AsgiClient, FakeSessionService, FakeOrchestrator],
    action_type: str,
    extra: dict[str, Any],
    expected_kind: str,
    state_changed: bool,
) -> None:
    client, _, _ = api
    body = {
        "turn_id": "turn-1",
        "client_request_id": f"request-{action_type.lower()}",
        "action_type": action_type,
        **extra,
    }
    with client:
        response = client.post("/v1/sessions/session-1/actions", json=body)
    assert response.status_code == 200
    payload = response.json()
    assert "action_signature" not in payload
    assert payload["resolution_kind"] == expected_kind
    assert payload["state_changed"] is state_changed
    if expected_kind == "NARRATIVE_REQUIRED":
        assert payload["narrative_required"] is True
        assert payload["narrative_pending"] is True
        assert "narrative" not in payload


def test_action_api_accepts_only_public_decision_and_choice_fields(
    api: tuple[AsgiClient, FakeSessionService, FakeOrchestrator],
) -> None:
    client, _, orchestrator = api
    with client:
        response = client.post(
            "/v1/sessions/session-1/actions",
            json={
                "turn_id": "turn-1",
                "client_request_id": "decision-request",
                "action_type": "CHOOSE",
                "decision_id": "decision.public-token",
                "choice_id": "choice.public-option",
            },
        )
    assert response.status_code == 200
    assert len(orchestrator.submissions) == 1
    assert orchestrator.submissions[0].decision_id == "decision.public-token"
    assert orchestrator.submissions[0].choice_id == "choice.public-option"


def test_action_idempotent_replay_and_conflict_are_mapped(
    api: tuple[AsgiClient, FakeSessionService, FakeOrchestrator],
) -> None:
    client, _, orchestrator = api
    first_body = {
        "turn_id": "turn-1",
        "client_request_id": "same-key",
        "action_type": "INSPECT_STATUS",
    }
    with client:
        first = client.post("/v1/sessions/session-1/actions", json=first_body)
        replay = client.post("/v1/sessions/session-1/actions", json=first_body)
        conflict = client.post(
            "/v1/sessions/session-1/actions",
            json={**first_body, "action_type": "INSPECT_RESOURCES"},
        )
    assert first.json() == replay.json()
    assert conflict.status_code == 409
    assert conflict.json()["error"]["error_code"] == "IDEMPOTENCY_CONFLICT"
    assert len(orchestrator.responses) == 1


@pytest.mark.parametrize(
    ("error", "status_code", "error_code"),
    [
        (
            DomainRuleViolation(DomainErrorCode.UNKNOWN_RESOURCE, "internal detail"),
            400,
            "UNKNOWN_RESOURCE",
        ),
        (OptimisticLockError("secret SQL"), 409, "OPTIMISTIC_LOCK_CONFLICT"),
        (
            SnapshotContentVersionMismatchError("session-1"),
            409,
            "SNAPSHOT_CONTENT_VERSION_MISMATCH",
        ),
    ],
)
def test_central_error_mapping_does_not_leak_internal_details(
    api: tuple[AsgiClient, FakeSessionService, FakeOrchestrator],
    error: Exception,
    status_code: int,
    error_code: str,
) -> None:
    client, service, _ = api
    service.error = error
    with client:
        response = client.get("/v1/sessions/session-1")
    assert response.status_code == status_code
    assert response.json()["error"]["error_code"] == error_code
    rendered = response.text.lower()
    assert "secret sql" not in rendered
    assert "database_url" not in rendered
    assert "traceback" not in rendered


def test_unknown_error_is_sanitized(
    api: tuple[AsgiClient, FakeSessionService, FakeOrchestrator],
) -> None:
    original_client, service, orchestrator = api
    service.error = RuntimeError("mysql://secret@host/db at C:\\private\\file.py")
    safe_client = AsgiClient(original_client.app, raise_server_exceptions=False)
    with safe_client:
        response = safe_client.get("/v1/sessions/session-1")
    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "Internal server error",
        }
    }
    assert orchestrator.submissions == []


@pytest.mark.parametrize(
    "bad_value",
    ["", "   ", "x" * 65, "request\u0000id", "request\u202eid"],
)
def test_external_identifiers_are_bounded_and_reject_controls(
    api: tuple[AsgiClient, FakeSessionService, FakeOrchestrator], bad_value: str
) -> None:
    client, _, _ = api
    with client:
        response = client.post(
            "/v1/sessions",
            json={
                "client_request_id": bad_value,
                "character_definition_id": "character.player.default",
                "scenario_id": "scenario.test",
            },
        )
    assert response.status_code == 422
