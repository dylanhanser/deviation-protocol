from __future__ import annotations

import inspect
import json
from typing import Any
import uuid

import pytest
from pydantic import ValidationError

from deviation_protocol.api import main
from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.application.player_character_service import (
    PlayerCharacterService,
)
from deviation_protocol.domain.player_character import (
    ControllerBindingRef,
    PlayerCharacterId,
)
from deviation_protocol.domain.player_character_policies import (
    CreatePlayerCharacterPolicy,
)
import deviation_protocol.infrastructure.player_character_authority as authority_module
from deviation_protocol.infrastructure.player_character_authority import (
    PLAYER_CHARACTER_CONTROLLER_BINDINGS_ENV,
    ConfiguredControllerBinding,
    ConfiguredControllerBindingResolver,
    Uuid4PlayerCharacterIdIssuer,
)


_ENTRY = ConfiguredControllerBinding(
    authentication_scheme="oidc",
    player_id="player.production",
    controller_id="controller.production",
)
_PRINCIPAL = RequestPrincipal(
    authentication_scheme="oidc",
    player_id="player.production",
)


async def test_configured_resolver_exactly_matches_complete_principal() -> None:
    resolver = ConfiguredControllerBindingResolver((_ENTRY,))

    assert await resolver.resolve(_PRINCIPAL) == ControllerBindingRef(
        value="controller.production"
    )
    assert (
        await resolver.resolve(
            RequestPrincipal(
                authentication_scheme="oidc",
                player_id="player.unknown",
            )
        )
        is None
    )
    assert (
        await resolver.resolve(
            RequestPrincipal(
                authentication_scheme="saml",
                player_id="player.production",
            )
        )
        is None
    )
    assert (
        await resolver.resolve(
            RequestPrincipal.model_construct(
                authentication_scheme="oidc",
                player_id="invalid player",
            )
        )
        is None
    )


async def test_configured_resolver_defensively_copies_configuration() -> None:
    caller_entries = [_ENTRY]
    resolver = ConfiguredControllerBindingResolver(caller_entries)
    caller_entries.clear()

    with pytest.raises(ValidationError):
        _ENTRY.controller_id = "controller.changed"
    first = await resolver.resolve(_PRINCIPAL)
    second = await resolver.resolve(_PRINCIPAL)

    assert first == ControllerBindingRef(
        value="controller.production"
    )
    assert second == first
    assert first is not second


@pytest.mark.parametrize(
    "payload",
    [
        {
            "authentication_scheme": "oidc",
            "player_id": "player.production",
        },
        {
            "authentication_scheme": "oidc",
            "player_id": "invalid player",
            "controller_id": "controller.production",
        },
        {
            "authentication_scheme": "oidc",
            "player_id": "player.production",
            "controller_id": "invalid controller",
        },
        {
            "authentication_scheme": "oidc",
            "player_id": "player.production",
            "controller_id": "controller.production",
            "unexpected": "field",
        },
    ],
)
def test_configured_binding_rejects_incomplete_or_invalid_entries(
    payload: dict[str, str],
) -> None:
    with pytest.raises(ValidationError):
        ConfiguredControllerBinding.model_validate(
            payload,
            strict=True,
        )


def test_configured_resolver_rejects_duplicate_or_conflicting_entries() -> None:
    duplicate_principal = ConfiguredControllerBinding(
        authentication_scheme="oidc",
        player_id="player.production",
        controller_id="controller.other",
    )
    with pytest.raises(ValueError, match="duplicate principal"):
        ConfiguredControllerBindingResolver(
            (_ENTRY, duplicate_principal)
        )

    shared_controller = ConfiguredControllerBinding(
        authentication_scheme="oidc",
        player_id="player.other",
        controller_id="controller.production",
    )
    with pytest.raises(ValueError, match="multiple principals"):
        ConfiguredControllerBindingResolver(
            (_ENTRY, shared_controller)
        )

    with pytest.raises(ValueError, match="at least one"):
        ConfiguredControllerBindingResolver(())


def test_environment_binding_configuration_is_required_and_strict() -> None:
    with pytest.raises(ValueError, match="is not configured"):
        ConfiguredControllerBindingResolver.from_environment({})
    with pytest.raises(ValueError, match="must be a JSON array"):
        ConfiguredControllerBindingResolver.from_environment(
            {PLAYER_CHARACTER_CONTROLLER_BINDINGS_ENV: "{}"}
        )
    with pytest.raises(ValueError, match="is invalid"):
        ConfiguredControllerBindingResolver.from_environment(
            {
                PLAYER_CHARACTER_CONTROLLER_BINDINGS_ENV: (
                    '[{"player_id":"one","player_id":"two"}]'
                )
            }
        )

    resolver = ConfiguredControllerBindingResolver.from_environment(
        {
            PLAYER_CHARACTER_CONTROLLER_BINDINGS_ENV: json.dumps(
                [_ENTRY.model_dump(mode="json")]
            )
        }
    )
    assert isinstance(resolver, ConfiguredControllerBindingResolver)


async def test_unknown_configured_principal_opens_no_uow() -> None:
    calls = 0

    def forbidden_uow() -> Any:
        nonlocal calls
        calls += 1
        raise AssertionError("unauthorized resolution must not open a UoW")

    service = main.build_player_character_service(
        uow_factory=forbidden_uow,
        controller_binding_resolver=(
            ConfiguredControllerBindingResolver((_ENTRY,))
        ),
    )

    result = await service.get_owned(
        RequestPrincipal(
            authentication_scheme="oidc",
            player_id="player.unknown",
        ),
        player_character_id=PlayerCharacterId(value="pc.unknown"),
    )

    assert result is None
    assert calls == 0


def test_uuid4_issuer_uses_standard_source_and_domain_representation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generated = uuid.UUID("12345678-1234-4abc-9234-1234567890ab")
    calls = 0

    def controlled_uuid4() -> uuid.UUID:
        nonlocal calls
        calls += 1
        return generated

    monkeypatch.setattr(
        authority_module.uuid,
        "uuid4",
        controlled_uuid4,
    )

    result = Uuid4PlayerCharacterIdIssuer().issue()

    assert result == PlayerCharacterId(
        value=f"pc.{generated.hex}"
    )
    assert uuid.UUID(hex=result.value.removeprefix("pc.")).version == 4
    assert calls == 1
    assert tuple(
        inspect.signature(
            Uuid4PlayerCharacterIdIssuer.issue
        ).parameters
    ) == ("self",)


def test_uuid4_issuer_does_not_reuse_successive_normal_issuances() -> None:
    issuer = Uuid4PlayerCharacterIdIssuer()

    first = issuer.issue()
    second = issuer.issue()

    assert first != second
    for issued in (first, second):
        assert issued.value.startswith("pc.")
        uuid_value = uuid.UUID(hex=issued.value.removeprefix("pc."))
        assert uuid_value.version == 4
        assert uuid_value.hex == issued.value.removeprefix("pc.")


def test_player_character_service_composition_is_lazy_and_complete(
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

    monkeypatch.setattr(
        authority_module.uuid,
        "uuid4",
        forbidden_uuid4,
    )
    resolver = ConfiguredControllerBindingResolver((_ENTRY,))

    service = main.build_player_character_service(
        uow_factory=forbidden_uow,
        controller_binding_resolver=resolver,
    )

    assert isinstance(service, PlayerCharacterService)
    assert service.uow_factory is forbidden_uow
    assert service.controller_binding_resolver is resolver
    assert isinstance(
        service.player_character_id_issuer,
        Uuid4PlayerCharacterIdIssuer,
    )
    assert isinstance(service.create_policy, CreatePlayerCharacterPolicy)
    assert callable(service.create)
    assert callable(service.mutate)
    assert callable(service.get_owned)
    assert uow_calls == 0
    assert uuid_calls == 0


def test_default_composition_reuses_one_lazy_mysql_uow_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = object()
    session_factory = object()
    uow_calls = 0

    def create_engine() -> object:
        return engine

    def create_session_factory(observed_engine: object) -> object:
        assert observed_engine is engine
        return session_factory

    def forbidden_uow(observed_factory: object) -> Any:
        nonlocal uow_calls
        uow_calls += 1
        raise AssertionError("composition must not construct a UoW")

    def no_provider(_: type[Any]) -> Any:
        raise ValueError("not configured")

    monkeypatch.setattr(main, "create_engine", create_engine)
    monkeypatch.setattr(
        main,
        "create_session_factory",
        create_session_factory,
    )
    monkeypatch.setattr(main, "SqlAlchemyUnitOfWork", forbidden_uow)
    monkeypatch.setattr(
        main.DeepSeekSettings,
        "from_environment",
        classmethod(no_provider),
    )

    services = main.build_default_services(
        player_character_controller_bindings=(_ENTRY,)
    )

    player_character_service = services.player_character_service
    assert isinstance(player_character_service, PlayerCharacterService)
    assert isinstance(
        player_character_service.controller_binding_resolver,
        ConfiguredControllerBindingResolver,
    )
    assert isinstance(
        player_character_service.player_character_id_issuer,
        Uuid4PlayerCharacterIdIssuer,
    )
    assert (
        player_character_service.uow_factory
        is services.session_service.uow_factory
    )
    assert (
        player_character_service.uow_factory
        is services.turn_orchestrator.uow_factory
    )
    assert services.engine is engine
    assert services.narrative_provider is None
    assert uow_calls == 0


def test_default_composition_rejects_missing_authority_before_resources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(
        PLAYER_CHARACTER_CONTROLLER_BINDINGS_ENV,
        raising=False,
    )

    def forbidden(*args: object, **kwargs: object) -> Any:
        del args, kwargs
        raise AssertionError(
            "invalid authority must fail before runtime resources"
        )

    monkeypatch.setattr(main, "JsonScenarioCatalogLoader", forbidden)
    monkeypatch.setattr(main, "create_engine", forbidden)

    with pytest.raises(
        ValueError,
        match=f"{PLAYER_CHARACTER_CONTROLLER_BINDINGS_ENV} is not configured",
    ):
        main.build_default_services()

    with pytest.raises(ValueError, match="at least one"):
        main.build_default_services(
            player_character_controller_bindings=()
        )
