from __future__ import annotations

from collections.abc import Mapping
from unittest.mock import AsyncMock, Mock

import pytest

from deviation_protocol.application.action_gateway import ActionGateway
from deviation_protocol.application.turn_orchestrator import FirstPhaseTurnOrchestrator
from deviation_protocol.domain.actions import ActionContext, ActionSubmission, ActionType


def submission() -> ActionSubmission:
    return ActionSubmission(
        session_id="session-1",
        turn_id="turn-1",
        client_request_id="request-1",
        action_type=ActionType.CUSTOM,
        description="我尝试观察门锁",
    )


class FakeSessionRepository:
    def __init__(self, calls: list[str], exists: bool = True) -> None:
        self._calls = calls
        self._exists = exists

    async def lock_for_turn(self, session_id: str) -> bool:
        self._calls.append(f"lock:{session_id}")
        return self._exists


class FakeTurnRequestRepository:
    def __init__(
        self, calls: list[str], existing: Mapping[str, object] | None = None
    ) -> None:
        self._calls = calls
        self._existing = existing
        self.add = AsyncMock(side_effect=self._add)

    async def _add(self, *args: object, **kwargs: object) -> None:
        self._calls.append("add")

    async def get_by_client_request_id(
        self, session_id: str, client_request_id: str
    ) -> Mapping[str, object] | None:
        self._calls.append(f"get:{session_id}:{client_request_id}")
        return self._existing


class FakeUnitOfWork:
    def __init__(
        self, calls: list[str], existing: Mapping[str, object] | None = None
    ) -> None:
        self.sessions = FakeSessionRepository(calls)
        self.turn_requests = FakeTurnRequestRepository(calls, existing)
        self.commit = AsyncMock(side_effect=lambda: calls.append("commit"))

    async def __aenter__(self) -> "FakeUnitOfWork":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


@pytest.mark.asyncio
async def test_duplicate_request_returns_stored_response_before_business_processing() -> None:
    calls: list[str] = []
    stored = {"route": "REJECT_LOCAL", "action_signature": "stored"}
    uow = FakeUnitOfWork(calls, stored)
    context_loader = AsyncMock()
    gateway = Mock(spec=ActionGateway)
    orchestrator = FirstPhaseTurnOrchestrator(gateway, lambda: uow, context_loader)

    result = await orchestrator.handle(submission())

    assert result is stored
    assert calls == ["lock:session-1", "get:session-1:request-1"]
    context_loader.assert_not_awaited()
    gateway.evaluate.assert_not_called()
    uow.turn_requests.add.assert_not_awaited()
    uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_new_request_is_locked_before_gateway_and_persisted_once() -> None:
    calls: list[str] = []
    uow = FakeUnitOfWork(calls)
    action = submission()
    context = ActionContext(submission=action, current_turn_id=action.turn_id)

    async def load_context(_: ActionSubmission) -> ActionContext:
        calls.append("context")
        return context

    gateway = ActionGateway.from_config()
    orchestrator = FirstPhaseTurnOrchestrator(gateway, lambda: uow, load_context)

    result = await orchestrator.handle(action)

    assert result["route"] == "NARRATIVE_NORMAL"
    assert calls == [
        "lock:session-1",
        "get:session-1:request-1",
        "context",
        "add",
        "commit",
    ]
    uow.turn_requests.add.assert_awaited_once()
    uow.commit.assert_awaited_once()
