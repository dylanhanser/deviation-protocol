from __future__ import annotations

from datetime import UTC, datetime
import inspect
from typing import Any
import uuid

from pydantic import ValidationError
import pytest

from deviation_protocol.api import main
from deviation_protocol.application.run_operations import (
    ReservedBindPlayerCharacterCommand,
    RunReplayDecisionCode,
)
from deviation_protocol.application.run_service import RunService
from deviation_protocol.domain.run import (
    ContinuousStoryLineId,
    RunAuthoritySourceRef,
    RunId,
    RunOperationId,
    RunStateVersion,
)
import deviation_protocol.infrastructure.run_authority as authority_module
from deviation_protocol.infrastructure.player_character_authority import (
    ConfiguredControllerBinding,
)
from deviation_protocol.infrastructure.run_authority import (
    Uuid4ContinuousStoryLineIdIssuer,
    Uuid4RunIdIssuer,
)


_CONTROLLER_BINDING = ConfiguredControllerBinding(
    authentication_scheme="oidc",
    player_id="player.production",
    controller_id="controller.production",
)
_SOURCE = RunAuthoritySourceRef(value="source.production-run")


def _build_run_service(uow_factory) -> RunService:
    resolver = object()
    evidence = object()
    return main.build_run_service(
        uow_factory=uow_factory,
        controller_binding_resolver=resolver,  # type: ignore[arg-type]
        player_character_binding_evidence=evidence,  # type: ignore[arg-type]
    )


def test_uuid4_issuers_use_separate_standard_calls_and_identity_domains(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generated = iter(
        (
            uuid.UUID("12345678-1234-4abc-9234-1234567890ab"),
            uuid.UUID("abcdef01-2345-4abc-9234-1234567890ab"),
        )
    )
    calls = 0

    def controlled_uuid4() -> uuid.UUID:
        nonlocal calls
        calls += 1
        return next(generated)

    monkeypatch.setattr(authority_module.uuid, "uuid4", controlled_uuid4)

    run_id = Uuid4RunIdIssuer().issue()
    line_id = Uuid4ContinuousStoryLineIdIssuer().issue()

    assert type(run_id) is RunId
    assert type(line_id) is ContinuousStoryLineId
    assert run_id.value == "run.1234567812344abc92341234567890ab"
    assert line_id.value == "csl.abcdef0123454abc92341234567890ab"
    assert uuid.UUID(hex=run_id.value.removeprefix("run.")).version == 4
    assert uuid.UUID(hex=line_id.value.removeprefix("csl.")).version == 4
    assert calls == 2
    assert tuple(inspect.signature(Uuid4RunIdIssuer.issue).parameters) == (
        "self",
    )
    assert tuple(
        inspect.signature(
            Uuid4ContinuousStoryLineIdIssuer.issue
        ).parameters
    ) == ("self",)


@pytest.mark.parametrize(
    "generated",
    (
        object(),
        uuid.UUID("12345678-1234-1abc-9234-1234567890ab"),
    ),
)
def test_uuid4_issuers_reject_invalid_standard_source_results(
    monkeypatch: pytest.MonkeyPatch,
    generated: object,
) -> None:
    monkeypatch.setattr(authority_module.uuid, "uuid4", lambda: generated)

    with pytest.raises(ValueError, match="invalid UUIDv4"):
        Uuid4RunIdIssuer().issue()
    with pytest.raises(ValueError, match="invalid UUIDv4"):
        Uuid4ContinuousStoryLineIdIssuer().issue()


def test_uuid4_issuers_do_not_reuse_successive_normal_identities() -> None:
    issued = (
        Uuid4RunIdIssuer().issue(),
        Uuid4RunIdIssuer().issue(),
        Uuid4ContinuousStoryLineIdIssuer().issue(),
        Uuid4ContinuousStoryLineIdIssuer().issue(),
    )

    assert issued[0] != issued[1]
    assert issued[2] != issued[3]
    assert all(
        uuid.UUID(hex=value.value.split(".", 1)[1]).version == 4
        for value in issued
    )


def test_run_service_composition_is_lazy_complete_and_trusted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    uow_calls = 0
    uuid_calls = 0

    def forbidden_uow() -> Any:
        nonlocal uow_calls
        uow_calls += 1
        raise AssertionError("composition must not construct a UoW")

    def forbidden_uuid4() -> uuid.UUID:
        nonlocal uuid_calls
        uuid_calls += 1
        raise AssertionError("composition must not issue an identity")

    monkeypatch.setattr(authority_module.uuid, "uuid4", forbidden_uuid4)

    resolver = object()
    evidence = object()
    service = main.build_run_service(
        uow_factory=forbidden_uow,
        controller_binding_resolver=resolver,  # type: ignore[arg-type]
        player_character_binding_evidence=evidence,  # type: ignore[arg-type]
    )

    assert type(service) is RunService
    assert service.uow_factory is forbidden_uow
    assert type(service.run_id_issuer) is Uuid4RunIdIssuer
    assert (
        type(service.continuous_story_line_id_issuer)
        is Uuid4ContinuousStoryLineIdIssuer
    )
    assert service.source_reference == _SOURCE
    assert service.clock().tzinfo is UTC
    assert callable(service.create_run)
    assert callable(service.get_run)
    assert callable(service.attach_session)
    assert callable(service.bind_player_character)
    assert callable(service.bind_player_character_internal)
    assert service.controller_binding_resolver is resolver
    assert service.player_character_binding_evidence is evidence
    assert uow_calls == 0
    assert uuid_calls == 0


def test_run_service_keeps_deterministic_issuers_injectable_for_tests() -> None:
    class DeterministicIssuer:
        def __init__(self, value: RunId | ContinuousStoryLineId) -> None:
            self.value = value

        def issue(self) -> RunId | ContinuousStoryLineId:
            return self.value

    run_issuer = DeterministicIssuer(RunId(value="run.test-injected"))
    line_issuer = DeterministicIssuer(
        ContinuousStoryLineId(value="csl.test-injected")
    )
    service = RunService(
        uow_factory=lambda: None,  # type: ignore[arg-type,return-value]
        run_id_issuer=run_issuer,  # type: ignore[arg-type]
        continuous_story_line_id_issuer=line_issuer,  # type: ignore[arg-type]
        source_reference=RunAuthoritySourceRef(value="source.test"),
        clock=lambda: datetime(2026, 7, 29, tzinfo=UTC),
        controller_binding_resolver=object(),  # type: ignore[arg-type]
        player_character_binding_evidence=object(),  # type: ignore[arg-type]
    )

    assert service.run_id_issuer is run_issuer
    assert service.continuous_story_line_id_issuer is line_issuer


def test_default_composition_reuses_one_lazy_mysql_uow_graph(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = object()
    session_factory = object()
    constructed_with: list[object] = []
    uow = object()

    def create_engine() -> object:
        return engine

    def create_session_factory(observed_engine: object) -> object:
        assert observed_engine is engine
        return session_factory

    def construct_uow(observed_factory: object) -> object:
        constructed_with.append(observed_factory)
        return uow

    def no_provider(_: type[Any]) -> Any:
        raise ValueError("not configured")

    monkeypatch.setattr(main, "create_engine", create_engine)
    monkeypatch.setattr(
        main,
        "create_session_factory",
        create_session_factory,
    )
    monkeypatch.setattr(main, "SqlAlchemyUnitOfWork", construct_uow)
    monkeypatch.setattr(
        main.DeepSeekSettings,
        "from_environment",
        classmethod(no_provider),
    )

    services = main.build_default_services(
        player_character_controller_bindings=(_CONTROLLER_BINDING,)
    )

    service = services.run_service
    assert type(service) is RunService
    assert service is services.run_service
    assert (
        service.uow_factory
        is services.player_character_service.uow_factory
        is services.session_service.uow_factory
        is services.turn_orchestrator.uow_factory
    )
    assert (
        service.player_character_binding_evidence
        is services.player_character_service
    )
    assert (
        service.controller_binding_resolver
        is services.player_character_service.controller_binding_resolver
    )
    assert services.player_character_service.binding_integrity_guard_enabled
    assert services.engine is engine
    assert services.narrative_provider is None
    assert constructed_with == []
    assert service.uow_factory() is uow
    assert constructed_with == [session_factory]


def test_default_database_configuration_is_lazy_and_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    app = main.create_app()
    assert app.title == "Deviation Protocol"
    service = _build_run_service(
        lambda: None  # type: ignore[arg-type,return-value]
    )
    assert type(service) is RunService

    with pytest.raises(ValidationError, match="database_url"):
        main.build_default_services(
            player_character_controller_bindings=(_CONTROLLER_BINDING,)
        )

    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///unsafe.db")
    with pytest.raises(ValueError, match="must use mysql\\+asyncmy"):
        main.build_default_services(
            player_character_controller_bindings=(_CONTROLLER_BINDING,)
        )


def test_composed_binding_namespace_stays_reserved_without_uow_entry() -> None:
    uow_calls = 0

    def forbidden_uow() -> Any:
        nonlocal uow_calls
        uow_calls += 1
        raise AssertionError("reserved binding must not enter a UoW")

    service = _build_run_service(forbidden_uow)
    decision = service.bind_player_character(
        operation_id=RunOperationId(value="operation.reserved-binding"),
        command=ReservedBindPlayerCharacterCommand(
            run_id=RunId(value="run.reserved-binding"),
            continuous_story_line_id=ContinuousStoryLineId(
                value="csl.reserved-binding"
            ),
            expected_state_version=RunStateVersion(value=1),
            source_reference=_SOURCE,
        ),
    )

    assert decision.code is RunReplayDecisionCode.RESERVED_OPERATION_REJECTED
    assert uow_calls == 0


def test_run_composition_activates_only_authorized_player_character_routes() -> None:
    app = main.create_app()
    public_routes = {
        (route.path, frozenset(route.methods))
        for route in app.routes
        if route.path == "/health" or route.path.startswith("/v1/")
    }

    assert public_routes == {
        ("/health", frozenset({"GET"})),
        (
            "/v1/player-characters/{player_character_id}",
            frozenset({"GET"}),
        ),
        ("/v1/player-characters", frozenset({"POST"})),
        ("/v1/scenarios", frozenset({"GET"})),
        ("/v1/sessions", frozenset({"POST"})),
        ("/v1/sessions/{session_id}", frozenset({"GET"})),
        ("/v1/sessions/{session_id}/state", frozenset({"GET"})),
        ("/v1/sessions/{session_id}/view", frozenset({"GET"})),
        (
            "/v1/sessions/{session_id}/requests/{client_request_id}",
            frozenset({"GET"}),
        ),
        ("/v1/sessions/{session_id}/actions", frozenset({"POST"})),
    }
