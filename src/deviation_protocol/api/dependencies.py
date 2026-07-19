from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine

from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.ports import TurnOrchestrator
from deviation_protocol.application.session_service import SessionService


@dataclass(frozen=True, slots=True)
class ApiServices:
    session_service: SessionService
    turn_orchestrator: TurnOrchestrator
    engine: AsyncEngine | None = None


def get_demo_dev_principal() -> RequestPrincipal:
    """Development-only fixed identity; replace/override before production use."""
    return RequestPrincipal(
        player_id="demo-player",
        authentication_scheme="demo-dev-only",
    )


def get_current_principal() -> RequestPrincipal:
    return get_demo_dev_principal()


def get_api_services(request: Request) -> ApiServices:
    return cast(ApiServices, request.app.state.api_services)


def get_session_service(request: Request) -> SessionService:
    return get_api_services(request).session_service


def get_turn_orchestrator(request: Request) -> TurnOrchestrator:
    return get_api_services(request).turn_orchestrator
