from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
import os
from types import MappingProxyType
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from deviation_protocol.application.identity import RequestPrincipal
from deviation_protocol.domain.player_character import (
    ControllerBindingRef,
    PlayerCharacterId,
)


PLAYER_CHARACTER_CONTROLLER_BINDINGS_ENV = (
    "PLAYER_CHARACTER_CONTROLLER_BINDINGS"
)


class ConfiguredControllerBinding(BaseModel):
    """One explicit trusted-principal to controller-binding assignment."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )

    authentication_scheme: str
    player_id: str
    controller_id: str

    @model_validator(mode="after")
    def validate_authority_types(self) -> ConfiguredControllerBinding:
        try:
            principal = RequestPrincipal(
                authentication_scheme=self.authentication_scheme,
                player_id=self.player_id,
            )
            ControllerBindingRef(value=self.controller_id)
        except (TypeError, ValueError):
            raise ValueError(
                "configured controller binding is invalid"
            ) from None
        if (
            principal.authentication_scheme != self.authentication_scheme
            or principal.player_id != self.player_id
        ):
            raise ValueError(
                "configured principal identity must already be canonical"
            )
        return self


def _unique_json_object(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(
                "controller-binding configuration contains a duplicate key"
            )
        value[key] = item
    return value


def _validated_principal_key(
    principal: RequestPrincipal,
) -> tuple[str, str] | None:
    if type(principal) is not RequestPrincipal:
        return None
    try:
        validated = RequestPrincipal.model_validate(
            {
                "authentication_scheme": principal.authentication_scheme,
                "player_id": principal.player_id,
            },
            strict=True,
        )
    except (AttributeError, TypeError, ValidationError, ValueError):
        return None
    if validated != principal:
        return None
    return (
        validated.authentication_scheme,
        validated.player_id,
    )


class ConfiguredControllerBindingResolver:
    """Exact, immutable production allowlist for trusted principals."""

    def __init__(
        self,
        bindings: Sequence[ConfiguredControllerBinding],
    ) -> None:
        entries = tuple(bindings)
        if not entries:
            raise ValueError(
                "at least one player-character controller binding is required"
            )

        resolved: dict[tuple[str, str], ControllerBindingRef] = {}
        assigned_controller_ids: set[str] = set()
        for source_entry in entries:
            if type(source_entry) is not ConfiguredControllerBinding:
                raise TypeError(
                    "controller bindings must use ConfiguredControllerBinding"
                )
            try:
                entry = ConfiguredControllerBinding.model_validate(
                    source_entry,
                    strict=True,
                )
            except (TypeError, ValidationError, ValueError):
                raise ValueError(
                    "configured controller binding is invalid"
                ) from None
            key = (entry.authentication_scheme, entry.player_id)
            if key in resolved:
                raise ValueError(
                    "controller-binding configuration contains a duplicate "
                    "principal"
                )
            if entry.controller_id in assigned_controller_ids:
                raise ValueError(
                    "controller-binding configuration assigns one controller "
                    "to multiple principals"
                )
            resolved[key] = ControllerBindingRef(
                value=entry.controller_id
            )
            assigned_controller_ids.add(entry.controller_id)

        self._bindings: Mapping[
            tuple[str, str],
            ControllerBindingRef,
        ] = MappingProxyType(resolved)

    @classmethod
    def from_environment(
        cls,
        environ: Mapping[str, str] | None = None,
    ) -> ConfiguredControllerBindingResolver:
        source = os.environ if environ is None else environ
        raw = source.get(PLAYER_CHARACTER_CONTROLLER_BINDINGS_ENV)
        if raw is None or not raw.strip():
            raise ValueError(
                f"{PLAYER_CHARACTER_CONTROLLER_BINDINGS_ENV} is not configured"
            )
        try:
            decoded = json.loads(
                raw,
                object_pairs_hook=_unique_json_object,
            )
        except (TypeError, ValueError):
            raise ValueError(
                f"{PLAYER_CHARACTER_CONTROLLER_BINDINGS_ENV} is invalid"
            ) from None
        if type(decoded) is not list:
            raise ValueError(
                f"{PLAYER_CHARACTER_CONTROLLER_BINDINGS_ENV} must be a JSON "
                "array"
            )
        try:
            entries = tuple(
                ConfiguredControllerBinding.model_validate(
                    item,
                    strict=True,
                )
                for item in decoded
            )
        except (TypeError, ValidationError, ValueError):
            raise ValueError(
                f"{PLAYER_CHARACTER_CONTROLLER_BINDINGS_ENV} is invalid"
            ) from None
        return cls(entries)

    async def resolve(
        self,
        principal: RequestPrincipal,
        /,
    ) -> ControllerBindingRef | None:
        key = _validated_principal_key(principal)
        if key is None:
            return None
        binding = self._bindings.get(key)
        if binding is None:
            return None
        return ControllerBindingRef(value=binding.value)


class Uuid4PlayerCharacterIdIssuer:
    """Issue opaque, domain-qualified identities from OS-random UUIDv4."""

    __slots__ = ()

    def issue(self) -> PlayerCharacterId:
        generated = uuid.uuid4()
        if type(generated) is not uuid.UUID or generated.version != 4:
            raise ValueError("uuid.uuid4() returned an invalid UUIDv4")
        return PlayerCharacterId(value=f"pc.{generated.hex}")
