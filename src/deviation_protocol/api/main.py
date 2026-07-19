from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path as FilePath
from typing import Annotated

from fastapi import Depends, FastAPI, Path, status

from deviation_protocol.api.dependencies import (
    ApiServices,
    get_current_principal,
    get_session_service,
    get_turn_orchestrator,
)
from deviation_protocol.api.errors import install_exception_handlers
from deviation_protocol.api.schemas import (
    ActionRequest,
    ActionResponse,
    CreateSessionRequest,
)
from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.ports import TurnOrchestrator
from deviation_protocol.application.rule_resolver import DeterministicRuleResolver
from deviation_protocol.application.session_service import (
    PlayerVisibleStateProjection,
    SessionCreationResult,
    SessionMetadata,
    SessionService,
)
from deviation_protocol.application.turn_orchestrator import FirstPhaseTurnOrchestrator
from deviation_protocol.infrastructure.database import create_engine, create_session_factory
from deviation_protocol.infrastructure.scenario_loader import JsonScenarioCatalogLoader
from deviation_protocol.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


SCENARIO_PACK = (
    FilePath(__file__).parents[3]
    / "config"
    / "scenarios"
    / "death_certificate_v1.json"
)
SessionPathId = Annotated[
    str,
    Path(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$",
    ),
]


def build_default_services() -> ApiServices:
    """Build runtime dependencies without opening a connection or running migrations."""
    scenario_catalog = JsonScenarioCatalogLoader(SCENARIO_PACK).load()
    catalog = scenario_catalog.content_catalog
    engine = create_engine()
    session_factory = create_session_factory(engine)
    uow_factory = lambda: SqlAlchemyUnitOfWork(session_factory)
    orchestrator = FirstPhaseTurnOrchestrator(
        resolver=DeterministicRuleResolver(),
        uow_factory=uow_factory,
        catalog=catalog,
        scenario_catalog=scenario_catalog,
    )
    return ApiServices(
        session_service=SessionService(
            uow_factory=uow_factory,
            catalog=catalog,
            scenario_catalog=scenario_catalog,
        ),
        turn_orchestrator=orchestrator,
        engine=engine,
    )


def create_app(*, services: ApiServices | None = None) -> FastAPI:
    owns_services = services is None

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        runtime = services or build_default_services()
        app.state.api_services = runtime
        try:
            yield
        finally:
            if owns_services and runtime.engine is not None:
                await runtime.engine.dispose()

    app = FastAPI(
        title="Deviation Protocol",
        version="0.2.2a",
        lifespan=lifespan,
    )
    install_exception_handlers(app)

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "phase": "2.2a"}

    @app.post(
        "/v1/sessions",
        response_model=SessionCreationResult,
        status_code=status.HTTP_201_CREATED,
        tags=["sessions"],
    )
    async def create_session(
        request: CreateSessionRequest,
        principal: RequestPrincipal = Depends(get_current_principal),
        service: SessionService = Depends(get_session_service),
    ) -> SessionCreationResult:
        result = await service.create(
            principal,
            client_request_id=request.client_request_id,
            character_definition_id=request.character_definition_id,
            scenario_id=request.scenario_id,
        )
        if not isinstance(result, SessionCreationResult):  # pragma: no cover
            raise RuntimeError("scenario creation did not return its initial frame")
        return result

    @app.get(
        "/v1/sessions/{session_id}",
        response_model=SessionMetadata,
        tags=["sessions"],
    )
    async def get_session(
        session_id: SessionPathId,
        principal: RequestPrincipal = Depends(get_current_principal),
        service: SessionService = Depends(get_session_service),
    ) -> SessionMetadata:
        return await service.get_metadata(principal, session_id)

    @app.get(
        "/v1/sessions/{session_id}/state",
        response_model=PlayerVisibleStateProjection,
        tags=["sessions"],
    )
    async def get_session_state(
        session_id: SessionPathId,
        principal: RequestPrincipal = Depends(get_current_principal),
        service: SessionService = Depends(get_session_service),
    ) -> PlayerVisibleStateProjection:
        return await service.get_visible_state(principal, session_id)

    @app.post(
        "/v1/sessions/{session_id}/actions",
        response_model=ActionResponse,
        tags=["actions"],
    )
    async def submit_action(
        session_id: SessionPathId,
        request: ActionRequest,
        principal: RequestPrincipal = Depends(get_current_principal),
        service: SessionService = Depends(get_session_service),
        orchestrator: TurnOrchestrator = Depends(get_turn_orchestrator),
    ) -> ActionResponse:
        await service.require_owner(principal, session_id)
        response = await orchestrator.handle(request.to_submission(session_id))
        return ActionResponse.from_turn_response(response)

    return app


app = create_app()
