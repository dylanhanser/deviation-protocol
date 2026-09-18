from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from fastapi import Request, Depends
from sqlalchemy.ext.asyncio import AsyncEngine

from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.player_character_service import (
    PlayerCharacterService,
)
from deviation_protocol.application.ports import TurnOrchestrator
from deviation_protocol.application.run_entry_service import RunEntryService
if TYPE_CHECKING:
    from deviation_protocol.application.native_run_admission import NativeRunAdmissionService
from deviation_protocol.application.run_service import RunService
from deviation_protocol.application.session_service import SessionService
from deviation_protocol.application.narrative_models import NarrativeProvider


@dataclass(frozen=True, slots=True)
class ApiServices:
    session_service: SessionService
    turn_orchestrator: TurnOrchestrator
    player_character_service: PlayerCharacterService | None = None
    run_service: RunService | None = None
    run_entry_service: RunEntryService | None = None
    if TYPE_CHECKING:
        native_run_admission_service: NativeRunAdmissionService | None = None
    else:
        # Runtime introspection remains usable without importing S2 into Demo.
        native_run_admission_service: RunEntryService | None = None
    engine: AsyncEngine | None = None
    narrative_provider: NarrativeProvider | None = None
    run_exit_service: object | None = None
    content_registry: object | None = None
    run_continuation_service: object | None = None

    def __post_init__(self):
        if self.native_run_admission_service is not None:
            from deviation_protocol.application.public_run_protocol import project_entry_options
            coordinator = self.session_service.native_view_coordinator
            if (coordinator is None or self.session_service.native_controller_resolver is None
                    or getattr(self.turn_orchestrator, "native_coordinator", None) is not coordinator
                    or self.native_run_admission_service.session_service is not self.session_service
                    or self.native_run_admission_service.controller_binding_resolver is not self.session_service.native_controller_resolver):
                raise ValueError("incomplete native public service graph")
            project_entry_options(self.session_service, coordinator)
            if self.run_exit_service is None:
                from deviation_protocol.application.run_exit_service import RunExitService
                admission = self.native_run_admission_service
                object.__setattr__(self, "run_exit_service", RunExitService(
                    uow_factory=admission.uow_factory, session_service=self.session_service,
                    controller_binding_resolver=admission.controller_binding_resolver,
                    source_reference=admission.source_reference, clock=admission.clock,
                    content_registry=self.content_registry))
            if self.content_registry is not None and self.run_continuation_service is None:
                from deviation_protocol.application.run_continuation_service import RunContinuationService
                object.__setattr__(self,"run_continuation_service",RunContinuationService(self.run_exit_service,self.content_registry))
        elif getattr(self.session_service, "native_view_coordinator", None) is not None:
            raise ValueError("native View without native admission")


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


async def _owned_bundle(request, principal):
    services = get_api_services(request)
    session_id = request.path_params.get("session_id")
    if services.content_registry is None or session_id is None:
        return None
    import re
    if not isinstance(session_id,str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}",session_id):
        return None
    from deviation_protocol.application.errors import SessionNotFoundError,SnapshotInvalidError
    async with services.session_service.uow_factory() as uow:
        persisted = await uow.sessions.get_owned(session_id,principal.player_id)
        if persisted is None:
            raise SessionNotFoundError(session_id)
        try:
            return services.content_registry.for_session(persisted.session)
        except ValueError:
            raise SnapshotInvalidError(session_id) from None


async def get_session_service(request: Request,principal=Depends(get_current_principal)) -> SessionService:
    bundle = await _owned_bundle(request,principal)
    return get_api_services(request).session_service if bundle is None else bundle.session_service


async def get_turn_orchestrator(request: Request,principal=Depends(get_current_principal)) -> TurnOrchestrator:
    bundle = await _owned_bundle(request,principal)
    return get_api_services(request).turn_orchestrator if bundle is None else bundle.turn_orchestrator


def get_player_character_service(request: Request) -> PlayerCharacterService:
    service = get_api_services(request).player_character_service
    if service is None:
        raise RuntimeError("Player Character service is not configured")
    return service


def get_run_entry_service(request: Request) -> RunEntryService:
    service = get_api_services(request).run_entry_service
    if service is None:
        raise RuntimeError("Run entry service is not configured")
    return service
