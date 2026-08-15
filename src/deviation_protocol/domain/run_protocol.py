"""Strict, versioned Run Protocol representation and canonical v1 codec."""

from __future__ import annotations

from collections.abc import Mapping as _Mapping
from enum import StrEnum as _StrEnum
import json as _json
import re as _re
from typing import Any as _Any, Literal as _Literal, TypeVar as _TypeVar
import unicodedata as _unicodedata

from pydantic import (
    BaseModel as _BaseModel,
    ConfigDict as _ConfigDict,
    Field as _Field,
    field_validator as _field_validator,
)


RUN_PROTOCOL_ENVELOPE_EPOCH: str = "run-protocol-envelope"
RUN_PROTOCOL_ENVELOPE_V1_RECORD_VERSION: int = 1
RUN_PROTOCOL_ENVELOPE_V1_SCHEMA: str = "run-protocol-envelope/v1"
MAX_RUN_PROTOCOL_ENVELOPE_RAW_BYTES: int = 1_024
MAX_RUN_PROTOCOL_ENVELOPE_CANONICAL_BYTES: int = 1_024

_MAX_SIGNED_POSITIVE_64_BIT = 2**63 - 1
_PROFILE_ID = _re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
_ModelT = _TypeVar("_ModelT", bound=_BaseModel)


class RunProtocolValidationError(ValueError):
    """A Run Protocol carrier or byte representation is malformed."""


class UnsupportedRunProtocolVersionError(RunProtocolValidationError):
    """A well-typed trusted envelope epoch/version pair is unsupported."""


class _StrictFrozenModel(_BaseModel):
    model_config = _ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )


class RunProtocolProfileId(_StrictFrozenModel):
    value: str = _Field(strict=True, min_length=1, max_length=128)

    @_field_validator("value", mode="before")
    @classmethod
    def _validate_value(cls, value: _Any) -> str:
        if (
            type(value) is not str
            or not _PROFILE_ID.fullmatch(value)
            or len(value.encode("utf-8")) > 128
        ):
            raise ValueError("profile ID must be a bounded ASCII opaque identifier")
        return value


class RunProtocolProfileVersion(_StrictFrozenModel):
    value: int = _Field(
        strict=True,
        ge=1,
        le=_MAX_SIGNED_POSITIVE_64_BIT,
    )

    @_field_validator("value", mode="before")
    @classmethod
    def _require_exact_value(cls, value: _Any) -> int:
        if type(value) is not int:
            raise ValueError("profile version must be an exact integer")
        return value


class RunProtocolProfileRefV1(_StrictFrozenModel):
    profile_id: RunProtocolProfileId
    profile_version: RunProtocolProfileVersion

    @_field_validator("profile_id", mode="before")
    @classmethod
    def _require_profile_id(
        cls, value: _Any
    ) -> RunProtocolProfileId:
        if type(value) is not RunProtocolProfileId:
            raise ValueError("profile_id must be an exact RunProtocolProfileId")
        return value

    @_field_validator("profile_version", mode="before")
    @classmethod
    def _require_profile_version(
        cls, value: _Any
    ) -> RunProtocolProfileVersion:
        if type(value) is not RunProtocolProfileVersion:
            raise ValueError(
                "profile_version must be an exact RunProtocolProfileVersion"
            )
        return value


class RunProtocolWorldTone(_StrEnum):
    GRIM = "grim"
    BALANCED = "balanced"
    HEROIC = "heroic"


class RunProtocolRealityBoundary(_StrEnum):
    LAWFUL = "lawful"
    DEVIANT = "deviant"
    CHAOTIC = "chaotic"


class RunProtocolRelationshipOverlay(_StrEnum):
    OFF = "off"
    VEILED = "veiled"
    CHARGED = "charged"


class RunProtocolEnvelopeV1(_StrictFrozenModel):
    schema_version: _Literal["run-protocol-envelope/v1"]
    profile_ref: RunProtocolProfileRefV1
    world_tone: RunProtocolWorldTone
    reality_boundary: RunProtocolRealityBoundary
    relationship_overlay: RunProtocolRelationshipOverlay

    @_field_validator("schema_version", mode="before")
    @classmethod
    def _require_schema_version(cls, value: _Any) -> str:
        if type(value) is not str:
            raise ValueError("schema_version must be an exact string")
        return value

    @_field_validator("profile_ref", mode="before")
    @classmethod
    def _require_profile_ref(
        cls, value: _Any
    ) -> RunProtocolProfileRefV1:
        if type(value) is not RunProtocolProfileRefV1:
            raise ValueError("profile_ref must be an exact RunProtocolProfileRefV1")
        return value

    @_field_validator("world_tone", mode="before")
    @classmethod
    def _require_world_tone(cls, value: _Any) -> RunProtocolWorldTone:
        if type(value) is not RunProtocolWorldTone:
            raise ValueError("world_tone must be an exact RunProtocolWorldTone")
        return value

    @_field_validator("reality_boundary", mode="before")
    @classmethod
    def _require_reality_boundary(
        cls, value: _Any
    ) -> RunProtocolRealityBoundary:
        if type(value) is not RunProtocolRealityBoundary:
            raise ValueError(
                "reality_boundary must be an exact RunProtocolRealityBoundary"
            )
        return value

    @_field_validator("relationship_overlay", mode="before")
    @classmethod
    def _require_relationship_overlay(
        cls, value: _Any
    ) -> RunProtocolRelationshipOverlay:
        if type(value) is not RunProtocolRelationshipOverlay:
            raise ValueError(
                "relationship_overlay must be an exact "
                "RunProtocolRelationshipOverlay"
            )
        return value


def validate_run_protocol_envelope_v1(
    value: RunProtocolEnvelopeV1,
) -> RunProtocolEnvelopeV1:
    """Revalidate the complete original instance without copying or repair."""

    if type(value) is not RunProtocolEnvelopeV1:
        raise TypeError("expected RunProtocolEnvelopeV1")
    try:
        _validate_actual_model_state(
            value,
            path="RunProtocolEnvelopeV1",
            visited=set(),
        )
        validated = RunProtocolEnvelopeV1.model_validate(value, strict=True)
        if validated != value:
            raise ValueError("envelope state is not already canonical")
    except RunProtocolValidationError:
        raise
    except (AttributeError, TypeError, ValueError) as exc:
        raise RunProtocolValidationError(
            "Run Protocol v1 envelope state is invalid"
        ) from exc
    return value


def encode_run_protocol_envelope_v1(value: RunProtocolEnvelopeV1) -> bytes:
    """Encode one validated v1 envelope as canonical UTF-8 JSON bytes."""

    value = validate_run_protocol_envelope_v1(value)
    payload = {
        "schema_version": value.schema_version,
        "profile_ref": {
            "profile_id": value.profile_ref.profile_id.value,
            "profile_version": value.profile_ref.profile_version.value,
        },
        "world_tone": value.world_tone.value,
        "reality_boundary": value.reality_boundary.value,
        "relationship_overlay": value.relationship_overlay.value,
    }
    try:
        encoded = _canonical_json_bytes(payload)
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise RunProtocolValidationError(
            "Run Protocol v1 envelope cannot be encoded canonically"
        ) from exc
    if not 1 <= len(encoded) <= MAX_RUN_PROTOCOL_ENVELOPE_CANONICAL_BYTES:
        raise RunProtocolValidationError(
            "Run Protocol v1 canonical payload is outside its byte bound"
        )
    return encoded


def decode_run_protocol_envelope_v1(payload: bytes) -> RunProtocolEnvelopeV1:
    """Decode only byte-identical canonical v1 payload bytes."""

    if type(payload) is not bytes:
        raise RunProtocolValidationError(
            "Run Protocol v1 payload must be exact immutable bytes"
        )
    if not 1 <= len(payload) <= MAX_RUN_PROTOCOL_ENVELOPE_RAW_BYTES:
        raise RunProtocolValidationError(
            "Run Protocol v1 raw payload is outside its byte bound"
        )
    if payload.startswith(b"\xef\xbb\xbf"):
        raise RunProtocolValidationError("Run Protocol v1 payload contains a BOM")
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise RunProtocolValidationError(
            "Run Protocol v1 payload is not strict UTF-8"
        ) from exc
    try:
        decoded = _json.loads(
            text,
            object_pairs_hook=_unique_json_object,
            parse_float=_reject_json_float,
            parse_constant=_reject_json_constant,
        )
    except RunProtocolValidationError:
        raise
    except (_json.JSONDecodeError, TypeError, ValueError) as exc:
        raise RunProtocolValidationError(
            "Run Protocol v1 payload is not strict JSON"
        ) from exc
    try:
        _validate_decoded_shape(decoded)
        envelope = RunProtocolEnvelopeV1(
            schema_version=decoded["schema_version"],
            profile_ref=RunProtocolProfileRefV1(
                profile_id=RunProtocolProfileId(
                    value=decoded["profile_ref"]["profile_id"]
                ),
                profile_version=RunProtocolProfileVersion(
                    value=decoded["profile_ref"]["profile_version"]
                ),
            ),
            world_tone=RunProtocolWorldTone(decoded["world_tone"]),
            reality_boundary=RunProtocolRealityBoundary(
                decoded["reality_boundary"]
            ),
            relationship_overlay=RunProtocolRelationshipOverlay(
                decoded["relationship_overlay"]
            ),
        )
        envelope = validate_run_protocol_envelope_v1(envelope)
    except RunProtocolValidationError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise RunProtocolValidationError(
            "Run Protocol v1 payload does not match the exact carrier"
        ) from exc
    if encode_run_protocol_envelope_v1(envelope) != payload:
        raise RunProtocolValidationError(
            "Run Protocol v1 payload is not byte-identical canonical JSON"
        )
    return envelope


def decode_run_protocol_envelope(
    payload: bytes,
    *,
    expected_epoch: str,
    expected_version: int,
) -> RunProtocolEnvelopeV1:
    """Dispatch only from the separately trusted stored epoch and version."""

    if type(expected_epoch) is not str or type(expected_version) is not int:
        raise RunProtocolValidationError(
            "trusted Run Protocol envelope selectors have invalid types"
        )
    if (
        expected_epoch != RUN_PROTOCOL_ENVELOPE_EPOCH
        or expected_version != RUN_PROTOCOL_ENVELOPE_V1_RECORD_VERSION
    ):
        raise UnsupportedRunProtocolVersionError(
            "trusted Run Protocol envelope version is unsupported"
        )
    envelope = decode_run_protocol_envelope_v1(payload)
    if envelope.schema_version != RUN_PROTOCOL_ENVELOPE_V1_SCHEMA:
        raise RunProtocolValidationError(
            "trusted record version contradicts the payload schema"
        )
    return envelope


def _validate_actual_model_state(
    value: _BaseModel,
    *,
    path: str,
    visited: set[int],
) -> None:
    identity = id(value)
    if identity in visited:
        return
    visited.add(identity)
    model_type = type(value)
    fields = set(model_type.model_fields)
    state = value.__dict__
    if type(state) is not dict or set(state) != fields:
        raise ValueError(f"{path} has non-canonical instance fields")
    extra = getattr(value, "__pydantic_extra__", None)
    if extra is not None and (
        not isinstance(extra, _Mapping) or bool(extra)
    ):
        raise ValueError(f"{path} has unauthorized Pydantic extra state")
    private = getattr(value, "__pydantic_private__", None)
    if private is not None and (
        not isinstance(private, _Mapping) or bool(private)
    ):
        raise ValueError(f"{path} has unauthorized Pydantic private state")
    fields_set = getattr(value, "__pydantic_fields_set__", None)
    if type(fields_set) is not set or fields_set != fields:
        raise ValueError(f"{path} has contradictory Pydantic fields-set state")
    for field_name in fields:
        nested = state[field_name]
        if isinstance(nested, _BaseModel):
            _validate_actual_model_state(
                nested,
                path=f"{path}.{field_name}",
                visited=visited,
            )


def _canonical_json_bytes(value: _Any) -> bytes:
    normalized = _normalize_canonical_value(value)
    return _json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _normalize_canonical_value(value: _Any) -> _Any:
    if type(value) is int:
        if not 1 <= value <= _MAX_SIGNED_POSITIVE_64_BIT:
            raise ValueError("canonical profile version is outside its domain")
        return value
    if type(value) is str:
        normalized = _unicodedata.normalize("NFC", value)
        normalized.encode("utf-8")
        return normalized
    if type(value) is dict:
        normalized: dict[str, _Any] = {}
        for key, nested in value.items():
            if type(key) is not str:
                raise TypeError("canonical object keys must be exact strings")
            normalized_key = _unicodedata.normalize("NFC", key)
            normalized_key.encode("utf-8")
            if normalized_key in normalized:
                raise ValueError("canonical object keys collide after NFC")
            normalized[normalized_key] = _normalize_canonical_value(nested)
        return normalized
    raise TypeError(f"unsupported canonical value {type(value).__name__}")


def _unique_json_object(pairs: list[tuple[str, _Any]]) -> dict[str, _Any]:
    result: dict[str, _Any] = {}
    for key, value in pairs:
        if key in result:
            raise RunProtocolValidationError(
                "Run Protocol v1 payload contains duplicate object members"
            )
        result[key] = value
    return result


def _reject_json_float(_value: str) -> _Any:
    raise RunProtocolValidationError(
        "Run Protocol v1 payload does not admit JSON floats"
    )


def _reject_json_constant(_value: str) -> _Any:
    raise RunProtocolValidationError(
        "Run Protocol v1 payload does not admit non-finite numbers"
    )


def _validate_decoded_shape(value: _Any) -> None:
    if type(value) is not dict:
        raise RunProtocolValidationError(
            "Run Protocol v1 payload must contain exactly one object"
        )
    expected_root = {
        "schema_version",
        "profile_ref",
        "world_tone",
        "reality_boundary",
        "relationship_overlay",
    }
    if set(value) != expected_root:
        raise RunProtocolValidationError(
            "Run Protocol v1 payload has missing or unknown envelope fields"
        )
    profile_ref = value["profile_ref"]
    if type(profile_ref) is not dict or set(profile_ref) != {
        "profile_id",
        "profile_version",
    }:
        raise RunProtocolValidationError(
            "Run Protocol v1 payload has an invalid profile_ref object"
        )
    scalar_types = (
        (value["schema_version"], str),
        (profile_ref["profile_id"], str),
        (profile_ref["profile_version"], int),
        (value["world_tone"], str),
        (value["reality_boundary"], str),
        (value["relationship_overlay"], str),
    )
    if any(type(item) is not expected for item, expected in scalar_types):
        raise RunProtocolValidationError(
            "Run Protocol v1 payload has an invalid scalar type"
        )
    for item in (
        *value.keys(),
        *profile_ref.keys(),
        value["schema_version"],
        profile_ref["profile_id"],
        value["world_tone"],
        value["reality_boundary"],
        value["relationship_overlay"],
    ):
        if _unicodedata.normalize("NFC", item) != item:
            raise RunProtocolValidationError(
                "Run Protocol v1 payload contains a non-NFC string"
            )
