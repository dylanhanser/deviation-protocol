"""Pure deterministic Run Protocol profile resolution for resolver v1."""

from __future__ import annotations

from collections.abc import Mapping as _Mapping
from enum import StrEnum as _StrEnum
import hashlib as _hashlib
import json as _json
import re as _re
from typing import Any as _Any, Literal as _Literal

from pydantic import (
    BaseModel as _BaseModel,
    ConfigDict as _ConfigDict,
    field_validator as _field_validator,
    model_validator as _model_validator,
)

from deviation_protocol.domain import run_protocol as _run_protocol


del annotations


RUN_PROTOCOL_RESOLUTION_EPOCH: str = "run-protocol-resolution"
RUN_PROTOCOL_RESOLUTION_V1_VERSION: int = 1
RUN_PROTOCOL_RESOLUTION_V1_SCHEMA: str = "run-protocol-resolution/v1"
MAX_RUN_PROTOCOL_RESOLUTION_INPUT_BYTES: int = 1_024
RUN_PROTOCOL_RESOLUTION_FINGERPRINT_DOMAIN: bytes = (
    b"deviation-protocol:run-protocol-resolution-fingerprint:v1"
)


class RunProtocolResolutionError(ValueError):
    """Base class for classified S2 profile-resolution failures."""


class UnsupportedRunProtocolResolverVersionError(RunProtocolResolutionError):
    """A well-typed trusted resolver selector is unsupported."""


class RunProtocolProfileLookupError(RunProtocolResolutionError):
    """The exact requested profile pair is not in resolver v1."""


class RunProtocolOverrideValidationError(RunProtocolResolutionError):
    """A proposed override set is contradictory or incompatible."""


class RunProtocolResolutionIntegrityError(RunProtocolResolutionError):
    """S2-owned state is malformed, corrupted, or contradictory."""


class _S2StateError(Exception):
    """Private marker for an owner-classified S2 state failure."""


class _StrictFrozenModel(_BaseModel):
    model_config = _ConfigDict(
        extra="forbid",
        strict=True,
        frozen=True,
        revalidate_instances="always",
    )


class ObjectiveParameterName(_StrEnum):
    RESOURCE_PRESSURE = "resource_pressure"
    SOCIAL_TRUST = "social_trust"
    CONSEQUENCE_SEVERITY = "consequence_severity"
    INFORMATION_OPACITY = "information_opacity"
    CONFLICT_INTENSITY = "conflict_intensity"


RUN_PROTOCOL_OBJECTIVE_PARAMETER_ORDER: tuple[ObjectiveParameterName, ...] = (
    ObjectiveParameterName.RESOURCE_PRESSURE,
    ObjectiveParameterName.SOCIAL_TRUST,
    ObjectiveParameterName.CONSEQUENCE_SEVERITY,
    ObjectiveParameterName.INFORMATION_OPACITY,
    ObjectiveParameterName.CONFLICT_INTENSITY,
)


class ObjectiveParameterValue(_StrictFrozenModel):
    value: int

    @_field_validator("value", mode="before")
    @classmethod
    def _require_exact_value(cls, value: _Any) -> int:
        if type(value) is not int or not 0 <= value <= 100 or value % 5 != 0:
            raise ValueError(
                "objective value must be an exact integer from 0 through 100 "
                "in steps of 5"
            )
        return value


class ObjectiveParameterValuesV1(_StrictFrozenModel):
    resource_pressure: ObjectiveParameterValue
    social_trust: ObjectiveParameterValue
    consequence_severity: ObjectiveParameterValue
    information_opacity: ObjectiveParameterValue
    conflict_intensity: ObjectiveParameterValue

    @_field_validator(
        "resource_pressure",
        "social_trust",
        "consequence_severity",
        "information_opacity",
        "conflict_intensity",
        mode="before",
    )
    @classmethod
    def _require_exact_parameter_value(
        cls, value: _Any
    ) -> ObjectiveParameterValue:
        if type(value) is not ObjectiveParameterValue:
            raise ValueError("objective field must be an exact ObjectiveParameterValue")
        return value


class RunProtocolObjectiveOverrideV1(_StrictFrozenModel):
    parameter: ObjectiveParameterName
    value: ObjectiveParameterValue

    @_field_validator("parameter", mode="before")
    @classmethod
    def _require_exact_parameter(cls, value: _Any) -> ObjectiveParameterName:
        if type(value) is not ObjectiveParameterName:
            raise ValueError("override parameter must be an exact ObjectiveParameterName")
        return value

    @_field_validator("value", mode="before")
    @classmethod
    def _require_exact_parameter_value(
        cls, value: _Any
    ) -> ObjectiveParameterValue:
        if type(value) is not ObjectiveParameterValue:
            raise ValueError("override value must be an exact ObjectiveParameterValue")
        return value


class RunProtocolOverrideRuleV1(_StrictFrozenModel):
    parameter: ObjectiveParameterName
    minimum: ObjectiveParameterValue
    maximum: ObjectiveParameterValue
    step: int

    @_field_validator("parameter", mode="before")
    @classmethod
    def _require_exact_parameter(cls, value: _Any) -> ObjectiveParameterName:
        if type(value) is not ObjectiveParameterName:
            raise ValueError("rule parameter must be an exact ObjectiveParameterName")
        return value

    @_field_validator("minimum", "maximum", mode="before")
    @classmethod
    def _require_exact_parameter_value(
        cls, value: _Any
    ) -> ObjectiveParameterValue:
        if type(value) is not ObjectiveParameterValue:
            raise ValueError("rule bound must be an exact ObjectiveParameterValue")
        return value

    @_field_validator("step", mode="before")
    @classmethod
    def _require_exact_step(cls, value: _Any) -> int:
        if type(value) is not int or value != 5:
            raise ValueError("rule step must be the exact integer 5")
        return value

    @_model_validator(mode="after")
    def _require_ordered_bounds(self) -> RunProtocolOverrideRuleV1:
        if self.minimum.value > self.maximum.value:
            raise ValueError("rule minimum must not exceed maximum")
        return self


class RunProtocolOverrideProposalV1(_StrictFrozenModel):
    profile_ref: _run_protocol.RunProtocolProfileRefV1
    entries: tuple[RunProtocolObjectiveOverrideV1, ...]

    @_field_validator("profile_ref", mode="before")
    @classmethod
    def _require_exact_profile_ref(
        cls, value: _Any
    ) -> _run_protocol.RunProtocolProfileRefV1:
        if type(value) is not _run_protocol.RunProtocolProfileRefV1:
            raise ValueError(
                "proposal profile_ref must be an exact RunProtocolProfileRefV1"
            )
        return value

    @_field_validator("entries", mode="before")
    @classmethod
    def _require_exact_entries_tuple(
        cls, value: _Any
    ) -> tuple[RunProtocolObjectiveOverrideV1, ...]:
        if type(value) is not tuple or not 0 <= len(value) <= 5:
            raise ValueError("proposal entries must be an exact tuple of length 0..5")
        if any(type(entry) is not RunProtocolObjectiveOverrideV1 for entry in value):
            raise ValueError(
                "proposal entries must contain exact RunProtocolObjectiveOverrideV1 values"
            )
        return value


class RunProtocolOverrideSetV1(_StrictFrozenModel):
    profile_ref: _run_protocol.RunProtocolProfileRefV1
    entries: tuple[RunProtocolObjectiveOverrideV1, ...]

    @_field_validator("profile_ref", mode="before")
    @classmethod
    def _require_exact_profile_ref(
        cls, value: _Any
    ) -> _run_protocol.RunProtocolProfileRefV1:
        if type(value) is not _run_protocol.RunProtocolProfileRefV1:
            raise ValueError(
                "override-set profile_ref must be an exact RunProtocolProfileRefV1"
            )
        return value

    @_field_validator("entries", mode="before")
    @classmethod
    def _require_exact_entries_tuple(
        cls, value: _Any
    ) -> tuple[RunProtocolObjectiveOverrideV1, ...]:
        if type(value) is not tuple or not 0 <= len(value) <= 5:
            raise ValueError("override-set entries must be an exact tuple of length 0..5")
        if any(type(entry) is not RunProtocolObjectiveOverrideV1 for entry in value):
            raise ValueError(
                "override-set entries must contain exact RunProtocolObjectiveOverrideV1 values"
            )
        return value

    @_model_validator(mode="after")
    def _require_canonical_entries(self) -> RunProtocolOverrideSetV1:
        positions = tuple(
            RUN_PROTOCOL_OBJECTIVE_PARAMETER_ORDER.index(entry.parameter)
            for entry in self.entries
        )
        if positions != tuple(sorted(positions)) or len(set(positions)) != len(
            positions
        ):
            raise ValueError("override-set entries must be unique and canonical")
        return self


class RunProtocolProfileDefinitionV1(_StrictFrozenModel):
    profile_ref: _run_protocol.RunProtocolProfileRefV1
    label: str
    base_values: ObjectiveParameterValuesV1
    override_rules: tuple[RunProtocolOverrideRuleV1, ...]
    server_default_eligible: _Literal[False]

    @_field_validator("profile_ref", mode="before")
    @classmethod
    def _require_exact_profile_ref(
        cls, value: _Any
    ) -> _run_protocol.RunProtocolProfileRefV1:
        if type(value) is not _run_protocol.RunProtocolProfileRefV1:
            raise ValueError(
                "profile definition reference must be an exact RunProtocolProfileRefV1"
            )
        return value

    @_field_validator("label", mode="before")
    @classmethod
    def _require_exact_label(cls, value: _Any) -> str:
        if type(value) is not str:
            raise ValueError("profile label must be an exact string")
        return value

    @_field_validator("base_values", mode="before")
    @classmethod
    def _require_exact_base_values(
        cls, value: _Any
    ) -> ObjectiveParameterValuesV1:
        if type(value) is not ObjectiveParameterValuesV1:
            raise ValueError("base_values must be exact ObjectiveParameterValuesV1")
        return value

    @_field_validator("override_rules", mode="before")
    @classmethod
    def _require_exact_override_rules(
        cls, value: _Any
    ) -> tuple[RunProtocolOverrideRuleV1, ...]:
        if type(value) is not tuple or len(value) != 5:
            raise ValueError("override_rules must be an exact five-entry tuple")
        if any(type(rule) is not RunProtocolOverrideRuleV1 for rule in value):
            raise ValueError(
                "override_rules must contain exact RunProtocolOverrideRuleV1 values"
            )
        return value

    @_field_validator("server_default_eligible", mode="before")
    @classmethod
    def _require_exact_server_default(cls, value: _Any) -> bool:
        if type(value) is not bool or value is not False:
            raise ValueError("server_default_eligible must be exact False")
        return value

    @_model_validator(mode="after")
    def _require_rule_order(self) -> RunProtocolProfileDefinitionV1:
        if tuple(rule.parameter for rule in self.override_rules) != (
            ObjectiveParameterName.RESOURCE_PRESSURE,
            ObjectiveParameterName.SOCIAL_TRUST,
            ObjectiveParameterName.CONSEQUENCE_SEVERITY,
            ObjectiveParameterName.INFORMATION_OPACITY,
            ObjectiveParameterName.CONFLICT_INTENSITY,
        ):
            raise ValueError("profile override rules must use product order")
        return self


class RunProtocolResolutionInputV1(_StrictFrozenModel):
    schema: _Literal["run-protocol-resolution/v1"]
    resolver_version: _Literal[1]
    envelope: _run_protocol.RunProtocolEnvelopeV1
    authorized_profile: RunProtocolProfileDefinitionV1
    authorized_overrides: RunProtocolOverrideSetV1

    @_field_validator("schema", mode="before")
    @classmethod
    def _require_exact_schema(cls, value: _Any) -> str:
        if type(value) is not str:
            raise ValueError("resolution-input schema must be an exact string")
        return value

    @_field_validator("resolver_version", mode="before")
    @classmethod
    def _require_exact_resolver_version(cls, value: _Any) -> int:
        if type(value) is not int:
            raise ValueError("resolver_version must be an exact integer")
        return value

    @_field_validator("envelope", mode="wrap")
    @classmethod
    def _require_exact_envelope(
        cls, value: _Any, handler: _Any
    ) -> _run_protocol.RunProtocolEnvelopeV1:
        if type(value) is not _run_protocol.RunProtocolEnvelopeV1:
            raise ValueError("envelope must be an exact RunProtocolEnvelopeV1")
        validated = _run_protocol.validate_run_protocol_envelope_v1(value)
        _run_protocol.encode_run_protocol_envelope_v1(validated)
        handler(value)
        return validated

    @_field_validator("authorized_profile", mode="wrap")
    @classmethod
    def _require_exact_authorized_profile(
        cls, value: _Any, handler: _Any
    ) -> RunProtocolProfileDefinitionV1:
        if type(value) is not RunProtocolProfileDefinitionV1:
            raise ValueError(
                "authorized_profile must be an exact RunProtocolProfileDefinitionV1"
            )
        try:
            authoritative = _validated_profile_authority(value)
        except _S2StateError as exc:
            raise ValueError(
                "authorized_profile must be the exact authoritative catalogue object"
            ) from exc
        handler(value)
        return authoritative

    @_field_validator("authorized_overrides", mode="wrap")
    @classmethod
    def _require_exact_authorized_overrides(
        cls, value: _Any, handler: _Any
    ) -> RunProtocolOverrideSetV1:
        if type(value) is not RunProtocolOverrideSetV1:
            raise ValueError(
                "authorized_overrides must be an exact RunProtocolOverrideSetV1"
            )
        try:
            _validate_override_set_state(value)
        except _S2StateError as exc:
            raise ValueError("authorized_overrides state is invalid") from exc
        handler(value)
        return value

    @_model_validator(mode="after")
    def _require_matching_profile_refs(self) -> RunProtocolResolutionInputV1:
        try:
            _validated_resolution_context(self)
        except _S2StateError as exc:
            raise ValueError("resolution-input S2 state is invalid") from exc
        return self


class RunProtocolResolutionFingerprint(_StrictFrozenModel):
    value: str

    @_field_validator("value", mode="before")
    @classmethod
    def _require_exact_fingerprint(cls, value: _Any) -> str:
        if type(value) is not str or _FINGERPRINT.fullmatch(value) is None:
            raise ValueError("fingerprint must be 64 lowercase hexadecimal characters")
        return value


class ResolvedRunProtocolObjectivesV1(_StrictFrozenModel):
    resolution_input: RunProtocolResolutionInputV1
    final_values: ObjectiveParameterValuesV1
    fingerprint: RunProtocolResolutionFingerprint

    @_field_validator("resolution_input", mode="wrap")
    @classmethod
    def _require_exact_resolution_input(
        cls, value: _Any, handler: _Any
    ) -> RunProtocolResolutionInputV1:
        if type(value) is not RunProtocolResolutionInputV1:
            raise ValueError(
                "resolution_input must be an exact RunProtocolResolutionInputV1"
            )
        validated = validate_run_protocol_resolution_input_v1(value)
        handler(value)
        return validated

    @_field_validator("final_values", mode="wrap")
    @classmethod
    def _require_exact_final_values(
        cls, value: _Any, handler: _Any
    ) -> ObjectiveParameterValuesV1:
        if type(value) is not ObjectiveParameterValuesV1:
            raise ValueError("final_values must be exact ObjectiveParameterValuesV1")
        validated = validate_objective_parameter_values_v1(value)
        handler(value)
        return validated

    @_field_validator("fingerprint", mode="wrap")
    @classmethod
    def _require_exact_fingerprint_carrier(
        cls, value: _Any, handler: _Any
    ) -> RunProtocolResolutionFingerprint:
        if type(value) is not RunProtocolResolutionFingerprint:
            raise ValueError(
                "fingerprint must be an exact RunProtocolResolutionFingerprint"
            )
        try:
            validated = _validate_fingerprint_state(
                value, path="ResolvedRunProtocolObjectivesV1.fingerprint"
            )
        except _S2StateError as exc:
            raise ValueError("fingerprint state is invalid") from exc
        handler(value)
        return validated

    @_model_validator(mode="after")
    def _require_derived_state(self) -> ResolvedRunProtocolObjectivesV1:
        expected_values = _build_final_values(self.resolution_input)
        if self.final_values != expected_values:
            raise ValueError("resolved final values contradict the resolution input")
        expected_fingerprint = _fingerprint_from_bytes(
            _encode_resolution_input_without_validation(self.resolution_input)
        )
        if self.fingerprint.value != expected_fingerprint:
            raise ValueError("resolved fingerprint contradicts the resolution input")
        return self


_FINGERPRINT = _re.compile(r"^[0-9a-f]{64}$")
_OBJECTIVE_FIELDS = (
    "resource_pressure",
    "social_trust",
    "consequence_severity",
    "information_opacity",
    "conflict_intensity",
)
_AUTHORITATIVE_PARAMETER_ORDER = RUN_PROTOCOL_OBJECTIVE_PARAMETER_ORDER
_MODEL_FIELDS = {
    ObjectiveParameterValue: ("value",),
    ObjectiveParameterValuesV1: _OBJECTIVE_FIELDS,
    RunProtocolObjectiveOverrideV1: ("parameter", "value"),
    RunProtocolOverrideRuleV1: ("parameter", "minimum", "maximum", "step"),
    RunProtocolOverrideProposalV1: ("profile_ref", "entries"),
    RunProtocolOverrideSetV1: ("profile_ref", "entries"),
    RunProtocolProfileDefinitionV1: (
        "profile_ref",
        "label",
        "base_values",
        "override_rules",
        "server_default_eligible",
    ),
    RunProtocolResolutionInputV1: (
        "schema",
        "resolver_version",
        "envelope",
        "authorized_profile",
        "authorized_overrides",
    ),
    RunProtocolResolutionFingerprint: ("value",),
    ResolvedRunProtocolObjectivesV1: (
        "resolution_input",
        "final_values",
        "fingerprint",
    ),
}
_MODULE_GLOBALS = globals()


def _objective_values(
    resource_pressure: int,
    social_trust: int,
    consequence_severity: int,
    information_opacity: int,
    conflict_intensity: int,
) -> ObjectiveParameterValuesV1:
    return ObjectiveParameterValuesV1(
        resource_pressure=ObjectiveParameterValue(value=resource_pressure),
        social_trust=ObjectiveParameterValue(value=social_trust),
        consequence_severity=ObjectiveParameterValue(value=consequence_severity),
        information_opacity=ObjectiveParameterValue(value=information_opacity),
        conflict_intensity=ObjectiveParameterValue(value=conflict_intensity),
    )


def _rule(
    parameter: ObjectiveParameterName, minimum: int, maximum: int
) -> RunProtocolOverrideRuleV1:
    return RunProtocolOverrideRuleV1(
        parameter=parameter,
        minimum=ObjectiveParameterValue(value=minimum),
        maximum=ObjectiveParameterValue(value=maximum),
        step=5,
    )


def _profile_ref(
    profile_id: str,
) -> _run_protocol.RunProtocolProfileRefV1:
    return _run_protocol.RunProtocolProfileRefV1(
        profile_id=_run_protocol.RunProtocolProfileId(value=profile_id),
        profile_version=_run_protocol.RunProtocolProfileVersion(value=1),
    )


def _profile(
    profile_id: str,
    label: str,
    defaults: tuple[int, int, int, int, int],
    ranges: tuple[
        tuple[int, int],
        tuple[int, int],
        tuple[int, int],
        tuple[int, int],
        tuple[int, int],
    ],
) -> RunProtocolProfileDefinitionV1:
    return RunProtocolProfileDefinitionV1(
        profile_ref=_profile_ref(profile_id),
        label=label,
        base_values=_objective_values(*defaults),
        override_rules=tuple(
            _rule(parameter, bounds[0], bounds[1])
            for parameter, bounds in zip(
                _AUTHORITATIVE_PARAMETER_ORDER, ranges, strict=True
            )
        ),
        server_default_eligible=False,
    )


_EXTREME_PROFILE = _profile(
    "difficulty.silent-hunting-ground",
    "Extreme — Silent Hunting Ground",
    (95, 10, 95, 90, 90),
    ((80, 100), (0, 25), (80, 100), (75, 100), (75, 100)),
)
_STANDARD_PROFILE = _profile(
    "difficulty.fragile-alliance",
    "Standard — Fragile Alliance",
    (60, 45, 65, 60, 60),
    ((40, 75), (30, 65), (45, 80), (40, 75), (40, 75)),
)
_EASIER_PROFILE = _profile(
    "difficulty.open-expedition",
    "Easier — Open Expedition",
    (25, 70, 35, 30, 35),
    ((10, 40), (55, 85), (20, 50), (15, 45), (20, 50)),
)
_AUTHORITATIVE_CATALOGUE_V1 = (
    _EXTREME_PROFILE,
    _STANDARD_PROFILE,
    _EASIER_PROFILE,
)
RUN_PROTOCOL_PROFILE_CATALOGUE_V1: tuple[
    RunProtocolProfileDefinitionV1,
    RunProtocolProfileDefinitionV1,
    RunProtocolProfileDefinitionV1,
] = _AUTHORITATIVE_CATALOGUE_V1


def _catalogue_snapshot(
    entry: RunProtocolProfileDefinitionV1,
) -> tuple[_Any, ...]:
    base = entry.base_values
    rules = entry.override_rules
    return (
        entry.profile_ref,
        entry.label,
        base,
        tuple(
            (getattr(base, field), getattr(base, field).value)
            for field in _OBJECTIVE_FIELDS
        ),
        rules,
        tuple(
            (
                rule,
                rule.parameter,
                rule.minimum,
                rule.minimum.value,
                rule.maximum,
                rule.maximum.value,
                rule.step,
            )
            for rule in rules
        ),
        entry.server_default_eligible,
    )


_CATALOGUE_SNAPSHOTS = tuple(
    _catalogue_snapshot(entry) for entry in _AUTHORITATIVE_CATALOGUE_V1
)


def _profile_pair(
    profile_ref: _run_protocol.RunProtocolProfileRefV1,
) -> tuple[str, int]:
    return (
        profile_ref.profile_id.value,
        profile_ref.profile_version.value,
    )


def _validate_s1_profile_ref(
    profile_ref: _run_protocol.RunProtocolProfileRefV1,
) -> None:
    scaffold = _run_protocol.RunProtocolEnvelopeV1.model_construct(
        _fields_set={
            "schema_version",
            "profile_ref",
            "world_tone",
            "reality_boundary",
            "relationship_overlay",
        },
        schema_version=_run_protocol.RUN_PROTOCOL_ENVELOPE_V1_SCHEMA,
        profile_ref=profile_ref,
        world_tone=_run_protocol.RunProtocolWorldTone.BALANCED,
        reality_boundary=_run_protocol.RunProtocolRealityBoundary.LAWFUL,
        relationship_overlay=_run_protocol.RunProtocolRelationshipOverlay.OFF,
    )
    _run_protocol.validate_run_protocol_envelope_v1(scaffold)


def _model_state(
    value: _Any,
    expected_type: type[_BaseModel],
    *,
    path: str,
) -> dict[str, _Any]:
    if type(value) is not expected_type:
        raise _S2StateError(f"{path} has the wrong exact type")
    try:
        state = object.__getattribute__(value, "__dict__")
        fields_set = object.__getattribute__(value, "__pydantic_fields_set__")
        extra = object.__getattribute__(value, "__pydantic_extra__")
        private = object.__getattribute__(value, "__pydantic_private__")
    except (AttributeError, TypeError) as exc:
        raise _S2StateError(f"{path} lacks original Pydantic state") from exc
    expected_fields = _MODEL_FIELDS[expected_type]
    if type(state) is not dict or tuple(state) != expected_fields:
        raise _S2StateError(f"{path} has non-canonical instance fields")
    if type(fields_set) is not set or fields_set != set(expected_fields):
        raise _S2StateError(f"{path} has contradictory fields-set state")
    if extra is not None and (
        not isinstance(extra, _Mapping) or bool(extra)
    ):
        raise _S2StateError(f"{path} has unauthorized extra state")
    if private is not None and (
        not isinstance(private, _Mapping) or bool(private)
    ):
        raise _S2StateError(f"{path} has unauthorized private state")
    return state


def _locate_s2_field(
    value: _Any,
    expected_type: type[_BaseModel],
    field: str,
    *,
    path: str,
) -> _Any:
    if type(value) is not expected_type:
        raise TypeError(f"expected {expected_type.__name__}")
    try:
        state = object.__getattribute__(value, "__dict__")
    except (AttributeError, TypeError) as exc:
        raise _S2StateError(f"{path} lacks instance state") from exc
    if type(state) is not dict or field not in state:
        raise _S2StateError(f"{path} lacks required {field}")
    return state[field]


def _validate_parameter_value_state(
    value: _Any, *, path: str
) -> ObjectiveParameterValue:
    state = _model_state(value, ObjectiveParameterValue, path=path)
    scalar = state["value"]
    if type(scalar) is not int or not 0 <= scalar <= 100 or scalar % 5 != 0:
        raise _S2StateError(f"{path}.value is outside the exact numeric domain")
    return value


def _validate_objective_values_state(
    value: _Any, *, path: str
) -> ObjectiveParameterValuesV1:
    state = _model_state(value, ObjectiveParameterValuesV1, path=path)
    for field in _OBJECTIVE_FIELDS:
        _validate_parameter_value_state(state[field], path=f"{path}.{field}")
    return value


def _validate_override_entry_state(
    value: _Any, *, path: str
) -> RunProtocolObjectiveOverrideV1:
    state = _model_state(value, RunProtocolObjectiveOverrideV1, path=path)
    parameter = state["parameter"]
    if type(parameter) is not ObjectiveParameterName or parameter not in (
        ObjectiveParameterName.RESOURCE_PRESSURE,
        ObjectiveParameterName.SOCIAL_TRUST,
        ObjectiveParameterName.CONSEQUENCE_SEVERITY,
        ObjectiveParameterName.INFORMATION_OPACITY,
        ObjectiveParameterName.CONFLICT_INTENSITY,
    ):
        raise _S2StateError(f"{path}.parameter is not an exact product member")
    _validate_parameter_value_state(state["value"], path=f"{path}.value")
    return value


def _validate_rule_state(
    value: _Any,
    *,
    path: str,
    expected_parameter: ObjectiveParameterName | None = None,
) -> RunProtocolOverrideRuleV1:
    state = _model_state(value, RunProtocolOverrideRuleV1, path=path)
    parameter = state["parameter"]
    if (
        type(parameter) is not ObjectiveParameterName
        or parameter not in _AUTHORITATIVE_PARAMETER_ORDER
        or (expected_parameter is not None and parameter is not expected_parameter)
    ):
        raise _S2StateError(f"{path}.parameter is invalid")
    minimum = _validate_parameter_value_state(
        state["minimum"], path=f"{path}.minimum"
    )
    maximum = _validate_parameter_value_state(
        state["maximum"], path=f"{path}.maximum"
    )
    if minimum.value > maximum.value:
        raise _S2StateError(f"{path} has reversed bounds")
    if type(state["step"]) is not int or state["step"] != 5:
        raise _S2StateError(f"{path}.step is not exact integer 5")
    return value


def _validate_catalogue_state() -> None:
    catalogue = _MODULE_GLOBALS.get("RUN_PROTOCOL_PROFILE_CATALOGUE_V1")
    if type(catalogue) is not tuple:
        raise _S2StateError("catalogue binding is not an exact tuple")
    if catalogue is not _AUTHORITATIVE_CATALOGUE_V1:
        raise _S2StateError("catalogue binding does not name the authoritative tuple")
    if len(catalogue) != 3:
        raise _S2StateError("catalogue cardinality is not three")
    for index, expected_entry in enumerate(_AUTHORITATIVE_CATALOGUE_V1):
        if catalogue[index] is not expected_entry:
            raise _S2StateError("catalogue entry identity or order is corrupted")
    order = _MODULE_GLOBALS.get("RUN_PROTOCOL_OBJECTIVE_PARAMETER_ORDER")
    if type(order) is not tuple:
        raise _S2StateError("objective parameter order is not an exact tuple")
    if order is not _AUTHORITATIVE_PARAMETER_ORDER:
        raise _S2StateError("objective parameter order binding is corrupted")
    if len(order) != 5 or order != (
        ObjectiveParameterName.RESOURCE_PRESSURE,
        ObjectiveParameterName.SOCIAL_TRUST,
        ObjectiveParameterName.CONSEQUENCE_SEVERITY,
        ObjectiveParameterName.INFORMATION_OPACITY,
        ObjectiveParameterName.CONFLICT_INTENSITY,
    ):
        raise _S2StateError("objective parameter order contents are corrupted")

    for index, entry in enumerate(_AUTHORITATIVE_CATALOGUE_V1):
        snapshot = _CATALOGUE_SNAPSHOTS[index]
        if type(entry) is not RunProtocolProfileDefinitionV1:
            raise _S2StateError("catalogue entry has the wrong exact type")
        if catalogue[index] is not entry:
            raise _S2StateError("catalogue entry association is corrupted")
        state = _model_state(
            entry,
            RunProtocolProfileDefinitionV1,
            path=f"catalogue[{index}]",
        )
        if type(state["label"]) is not str or state["label"] != snapshot[1]:
            raise _S2StateError(f"catalogue[{index}].label is corrupted")

        base = state["base_values"]
        if base is not snapshot[2]:
            raise _S2StateError(f"catalogue[{index}].base_values association changed")
        base_state = _model_state(
            base,
            ObjectiveParameterValuesV1,
            path=f"catalogue[{index}].base_values",
        )
        for field_index, field in enumerate(_OBJECTIVE_FIELDS):
            nested, expected_scalar = snapshot[3][field_index]
            if base_state[field] is not nested:
                raise _S2StateError(
                    f"catalogue[{index}].base_values.{field} association changed"
                )
            actual = _validate_parameter_value_state(
                base_state[field], path=f"catalogue[{index}].base_values.{field}"
            )
            if actual.value != expected_scalar:
                raise _S2StateError(
                    f"catalogue[{index}].base_values.{field} value changed"
                )

        rules = state["override_rules"]
        if type(rules) is not tuple or rules is not snapshot[4] or len(rules) != 5:
            raise _S2StateError(f"catalogue[{index}].override_rules changed")
        for rule_index, expected_parameter in enumerate(
            _AUTHORITATIVE_PARAMETER_ORDER
        ):
            rule_snapshot = snapshot[5][rule_index]
            rule = rules[rule_index]
            if rule is not rule_snapshot[0]:
                raise _S2StateError(
                    f"catalogue[{index}].override_rules[{rule_index}] association changed"
                )
            rule_state = _model_state(
                rule,
                RunProtocolOverrideRuleV1,
                path=f"catalogue[{index}].override_rules[{rule_index}]",
            )
            if (
                rule_state["parameter"] is not expected_parameter
                or rule_state["parameter"] is not rule_snapshot[1]
            ):
                raise _S2StateError("catalogue rule parameter changed")
            if rule_state["minimum"] is not rule_snapshot[2]:
                raise _S2StateError("catalogue rule minimum association changed")
            minimum = _validate_parameter_value_state(
                rule_state["minimum"],
                path=f"catalogue[{index}].override_rules[{rule_index}].minimum",
            )
            if minimum.value != rule_snapshot[3]:
                raise _S2StateError("catalogue rule minimum changed")
            if rule_state["maximum"] is not rule_snapshot[4]:
                raise _S2StateError("catalogue rule maximum association changed")
            maximum = _validate_parameter_value_state(
                rule_state["maximum"],
                path=f"catalogue[{index}].override_rules[{rule_index}].maximum",
            )
            if maximum.value != rule_snapshot[5]:
                raise _S2StateError("catalogue rule maximum changed")
            if type(rule_state["step"]) is not int or rule_state["step"] != rule_snapshot[6]:
                raise _S2StateError("catalogue rule step changed")

        if (
            type(state["server_default_eligible"]) is not bool
            or state["server_default_eligible"] is not False
            or state["server_default_eligible"] is not snapshot[6]
        ):
            raise _S2StateError(
                f"catalogue[{index}].server_default_eligible changed"
            )
        if state["profile_ref"] is not snapshot[0]:
            raise _S2StateError(f"catalogue[{index}].profile_ref association changed")
        _validate_s1_profile_ref(state["profile_ref"])


def _validated_profile_authority(
    profile: _Any,
) -> RunProtocolProfileDefinitionV1:
    profile_ref = _locate_s2_field(
        profile,
        RunProtocolProfileDefinitionV1,
        "profile_ref",
        path="RunProtocolProfileDefinitionV1",
    )
    authoritative = lookup_run_protocol_profile(profile_ref)
    if profile is not authoritative:
        raise _S2StateError("profile is not the authoritative catalogue object")
    return authoritative


def _validate_proposal_state(
    proposal: _Any,
) -> tuple[
    _run_protocol.RunProtocolProfileRefV1,
    tuple[RunProtocolObjectiveOverrideV1, ...],
]:
    profile_ref = _locate_s2_field(
        proposal,
        RunProtocolOverrideProposalV1,
        "profile_ref",
        path="RunProtocolOverrideProposalV1",
    )
    if type(profile_ref) is not _run_protocol.RunProtocolProfileRefV1:
        raise _S2StateError("proposal profile_ref has the wrong exact type")
    _validate_s1_profile_ref(profile_ref)
    state = _model_state(
        proposal,
        RunProtocolOverrideProposalV1,
        path="RunProtocolOverrideProposalV1",
    )
    entries = state["entries"]
    if type(entries) is not tuple or not 0 <= len(entries) <= 5:
        raise _S2StateError("proposal entries are not an exact tuple of length 0..5")
    for index, entry in enumerate(entries):
        _validate_override_entry_state(entry, path=f"proposal.entries[{index}]")
    return profile_ref, entries


def _validate_override_set_state(
    overrides: _Any,
) -> tuple[
    _run_protocol.RunProtocolProfileRefV1,
    tuple[RunProtocolObjectiveOverrideV1, ...],
]:
    profile_ref = _locate_s2_field(
        overrides,
        RunProtocolOverrideSetV1,
        "profile_ref",
        path="RunProtocolOverrideSetV1",
    )
    if type(profile_ref) is not _run_protocol.RunProtocolProfileRefV1:
        raise _S2StateError("override-set profile_ref has the wrong exact type")
    _validate_s1_profile_ref(profile_ref)
    state = _model_state(
        overrides,
        RunProtocolOverrideSetV1,
        path="RunProtocolOverrideSetV1",
    )
    entries = state["entries"]
    if type(entries) is not tuple or not 0 <= len(entries) <= 5:
        raise _S2StateError(
            "override-set entries are not an exact tuple of length 0..5"
        )
    previous_position = -1
    seen: set[ObjectiveParameterName] = set()
    for index, entry in enumerate(entries):
        _validate_override_entry_state(entry, path=f"overrides.entries[{index}]")
        position = _AUTHORITATIVE_PARAMETER_ORDER.index(entry.parameter)
        if entry.parameter in seen or position <= previous_position:
            raise _S2StateError("override-set entries are not unique and canonical")
        seen.add(entry.parameter)
        previous_position = position
    return profile_ref, entries


def _validate_compatibility_without_lookup(
    profile: RunProtocolProfileDefinitionV1,
    profile_ref: _run_protocol.RunProtocolProfileRefV1,
    entries: tuple[RunProtocolObjectiveOverrideV1, ...],
) -> None:
    if _profile_pair(profile_ref) != _profile_pair(profile.profile_ref):
        raise RunProtocolOverrideValidationError(
            "override-set profile reference contradicts the selected profile"
        )
    rule_index = 0
    for entry in entries:
        while profile.override_rules[rule_index].parameter is not entry.parameter:
            rule_index += 1
        rule = profile.override_rules[rule_index]
        scalar = entry.value.value
        if not rule.minimum.value <= scalar <= rule.maximum.value:
            raise RunProtocolOverrideValidationError(
                f"{entry.parameter.value} is outside the selected profile range"
            )


def _construct_override_set(
    profile_ref: _run_protocol.RunProtocolProfileRefV1,
    entries: tuple[RunProtocolObjectiveOverrideV1, ...],
) -> RunProtocolOverrideSetV1:
    return RunProtocolOverrideSetV1.model_construct(
        _fields_set={"profile_ref", "entries"},
        profile_ref=profile_ref,
        entries=entries,
    )


def _canonicalize_proposal_without_lookup(
    profile: RunProtocolProfileDefinitionV1,
    proposal: RunProtocolOverrideProposalV1,
) -> RunProtocolOverrideSetV1:
    profile_ref, entries = _validate_proposal_state(proposal)
    if _profile_pair(profile_ref) != _profile_pair(profile.profile_ref):
        raise RunProtocolOverrideValidationError(
            "proposal profile reference contradicts the selected profile"
        )
    seen: set[ObjectiveParameterName] = set()
    for entry in entries:
        if entry.parameter in seen:
            raise RunProtocolOverrideValidationError(
                f"duplicate override for {entry.parameter.value}"
            )
        seen.add(entry.parameter)
    canonical_entries = tuple(
        entry
        for parameter in _AUTHORITATIVE_PARAMETER_ORDER
        for entry in entries
        if entry.parameter is parameter
    )
    return _construct_override_set(profile_ref, canonical_entries)


def _build_objective_values_from_scalars(
    scalars: tuple[int, int, int, int, int],
) -> ObjectiveParameterValuesV1:
    return ObjectiveParameterValuesV1.model_construct(
        _fields_set=set(_OBJECTIVE_FIELDS),
        resource_pressure=ObjectiveParameterValue.model_construct(
            _fields_set={"value"}, value=scalars[0]
        ),
        social_trust=ObjectiveParameterValue.model_construct(
            _fields_set={"value"}, value=scalars[1]
        ),
        consequence_severity=ObjectiveParameterValue.model_construct(
            _fields_set={"value"}, value=scalars[2]
        ),
        information_opacity=ObjectiveParameterValue.model_construct(
            _fields_set={"value"}, value=scalars[3]
        ),
        conflict_intensity=ObjectiveParameterValue.model_construct(
            _fields_set={"value"}, value=scalars[4]
        ),
    )


def _build_final_values_from_parts(
    profile: RunProtocolProfileDefinitionV1,
    entries: tuple[RunProtocolObjectiveOverrideV1, ...],
) -> ObjectiveParameterValuesV1:
    base = profile.base_values
    scalars = [
        base.resource_pressure.value,
        base.social_trust.value,
        base.consequence_severity.value,
        base.information_opacity.value,
        base.conflict_intensity.value,
    ]
    for entry in entries:
        if entry.parameter is ObjectiveParameterName.RESOURCE_PRESSURE:
            scalars[0] = entry.value.value
        elif entry.parameter is ObjectiveParameterName.SOCIAL_TRUST:
            scalars[1] = entry.value.value
        elif entry.parameter is ObjectiveParameterName.CONSEQUENCE_SEVERITY:
            scalars[2] = entry.value.value
        elif entry.parameter is ObjectiveParameterName.INFORMATION_OPACITY:
            scalars[3] = entry.value.value
        elif entry.parameter is ObjectiveParameterName.CONFLICT_INTENSITY:
            scalars[4] = entry.value.value
    return _build_objective_values_from_scalars(
        (scalars[0], scalars[1], scalars[2], scalars[3], scalars[4])
    )


def _build_final_values(
    value: RunProtocolResolutionInputV1,
) -> ObjectiveParameterValuesV1:
    return _build_final_values_from_parts(
        value.authorized_profile, value.authorized_overrides.entries
    )


def _validated_resolution_context(
    value: _Any,
) -> tuple[
    RunProtocolResolutionInputV1,
    bytes,
    RunProtocolProfileDefinitionV1,
    tuple[RunProtocolObjectiveOverrideV1, ...],
]:
    envelope = _locate_s2_field(
        value,
        RunProtocolResolutionInputV1,
        "envelope",
        path="RunProtocolResolutionInputV1",
    )
    envelope = _run_protocol.validate_run_protocol_envelope_v1(envelope)
    envelope_bytes = _run_protocol.encode_run_protocol_envelope_v1(envelope)
    profile = lookup_run_protocol_profile(envelope.profile_ref)
    state = _model_state(
        value,
        RunProtocolResolutionInputV1,
        path="RunProtocolResolutionInputV1",
    )
    if type(state["authorized_profile"]) is not RunProtocolProfileDefinitionV1:
        raise _S2StateError("authorized_profile has the wrong exact type")
    if state["authorized_profile"] is not profile:
        raise _S2StateError("authorized_profile is not the catalogue object")
    override_ref, entries = _validate_override_set_state(
        state["authorized_overrides"]
    )
    _validate_compatibility_without_lookup(profile, override_ref, entries)
    if _profile_pair(override_ref) != _profile_pair(envelope.profile_ref):
        raise _S2StateError("authorized overrides contradict the envelope profile")
    if type(state["schema"]) is not str or state["schema"] != RUN_PROTOCOL_RESOLUTION_V1_SCHEMA:
        raise _S2StateError("resolution-input schema is corrupted")
    if type(state["resolver_version"]) is not int or state["resolver_version"] != 1:
        raise _S2StateError("resolution-input resolver version is corrupted")
    return value, envelope_bytes, profile, entries


def _encode_resolution_parts(
    envelope_bytes: bytes,
    profile: RunProtocolProfileDefinitionV1,
    entries: tuple[RunProtocolObjectiveOverrideV1, ...],
) -> bytes:
    payload = {
        "authorized_overrides": [
            {"parameter": entry.parameter.value, "value": entry.value.value}
            for entry in entries
        ],
        "authorized_profile_id": profile.profile_ref.profile_id.value,
        "authorized_profile_version": profile.profile_ref.profile_version.value,
        "canonical_envelope_hex": envelope_bytes.hex(),
        "resolver_version": 1,
        "schema": RUN_PROTOCOL_RESOLUTION_V1_SCHEMA,
    }
    try:
        encoded = _canonical_resolution_json_bytes(payload)
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise RunProtocolResolutionIntegrityError(
            "resolution input cannot be encoded canonically"
        ) from exc
    return _enforce_canonical_input_bound(encoded)


def _canonical_resolution_json_bytes(payload: dict[str, _Any]) -> bytes:
    return _json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _enforce_canonical_input_bound(encoded: bytes) -> bytes:
    if type(encoded) is not bytes or not 1 <= len(encoded) <= 1_024:
        raise RunProtocolResolutionIntegrityError(
            "canonical resolution input is outside its 1..1,024 byte bound"
        )
    return encoded


def _encode_resolution_input_without_validation(
    value: RunProtocolResolutionInputV1,
) -> bytes:
    return _encode_resolution_parts(
        _run_protocol.encode_run_protocol_envelope_v1(value.envelope),
        value.authorized_profile,
        value.authorized_overrides.entries,
    )


def _fingerprint_from_bytes(encoded: bytes) -> str:
    preimage = (
        RUN_PROTOCOL_RESOLUTION_FINGERPRINT_DOMAIN
        + b"\x00"
        + len(encoded).to_bytes(4, byteorder="big", signed=False)
        + encoded
    )
    return _hashlib.sha256(preimage).hexdigest()


def _construct_resolution_input(
    envelope: _run_protocol.RunProtocolEnvelopeV1,
    profile: RunProtocolProfileDefinitionV1,
    overrides: RunProtocolOverrideSetV1,
) -> RunProtocolResolutionInputV1:
    return RunProtocolResolutionInputV1.model_construct(
        _fields_set={
            "schema",
            "resolver_version",
            "envelope",
            "authorized_profile",
            "authorized_overrides",
        },
        schema=RUN_PROTOCOL_RESOLUTION_V1_SCHEMA,
        resolver_version=1,
        envelope=envelope,
        authorized_profile=profile,
        authorized_overrides=overrides,
    )


def _construct_resolved_output(
    resolution_input: RunProtocolResolutionInputV1,
    final_values: ObjectiveParameterValuesV1,
    fingerprint_value: str,
) -> ResolvedRunProtocolObjectivesV1:
    fingerprint = RunProtocolResolutionFingerprint.model_construct(
        _fields_set={"value"}, value=fingerprint_value
    )
    return ResolvedRunProtocolObjectivesV1.model_construct(
        _fields_set={"resolution_input", "final_values", "fingerprint"},
        resolution_input=resolution_input,
        final_values=final_values,
        fingerprint=fingerprint,
    )


def validate_objective_parameter_values_v1(
    value: ObjectiveParameterValuesV1,
) -> ObjectiveParameterValuesV1:
    """Validate complete S2 objective-value state and return the same instance."""

    if type(value) is not ObjectiveParameterValuesV1:
        raise TypeError("expected ObjectiveParameterValuesV1")
    try:
        return _validate_objective_values_state(
            value, path="ObjectiveParameterValuesV1"
        )
    except _S2StateError as exc:
        raise RunProtocolResolutionIntegrityError(
            "objective parameter values state is invalid"
        ) from exc


def lookup_run_protocol_profile(
    profile_ref: _run_protocol.RunProtocolProfileRefV1,
) -> RunProtocolProfileDefinitionV1:
    """Return the exact authoritative v1 profile after ordered validation."""

    if type(profile_ref) is not _run_protocol.RunProtocolProfileRefV1:
        raise TypeError("expected RunProtocolProfileRefV1")
    _validate_s1_profile_ref(profile_ref)
    try:
        _validate_catalogue_state()
    except _S2StateError as exc:
        raise RunProtocolResolutionIntegrityError(
            "Run Protocol resolver-v1 catalogue state is invalid"
        ) from exc
    requested_pair = _profile_pair(profile_ref)
    for entry in _AUTHORITATIVE_CATALOGUE_V1:
        if _profile_pair(entry.profile_ref) == requested_pair:
            return entry
    raise RunProtocolProfileLookupError(
        f"Run Protocol profile {requested_pair[0]!r}/{requested_pair[1]!r} is unsupported"
    )


def validate_run_protocol_overrides(
    profile: RunProtocolProfileDefinitionV1,
    proposal: RunProtocolOverrideProposalV1,
) -> RunProtocolOverrideSetV1:
    """Validate and canonicalize one explicit override proposal."""

    try:
        authoritative = _validated_profile_authority(profile)
        return _canonicalize_proposal_without_lookup(authoritative, proposal)
    except _S2StateError as exc:
        raise RunProtocolResolutionIntegrityError(
            "override proposal or profile state is invalid"
        ) from exc


def validate_run_protocol_profile_compatibility(
    profile: RunProtocolProfileDefinitionV1,
    overrides: RunProtocolOverrideSetV1,
) -> RunProtocolOverrideSetV1:
    """Validate the complete canonical override set against one exact profile."""

    try:
        authoritative = _validated_profile_authority(profile)
        profile_ref, entries = _validate_override_set_state(overrides)
        _validate_compatibility_without_lookup(authoritative, profile_ref, entries)
    except _S2StateError as exc:
        raise RunProtocolResolutionIntegrityError(
            "override set or profile state is invalid"
        ) from exc
    return overrides


def construct_run_protocol_resolution_input_v1(
    envelope: _run_protocol.RunProtocolEnvelopeV1,
    *,
    authorized_profile: RunProtocolProfileDefinitionV1,
    authorized_overrides: RunProtocolOverrideSetV1,
) -> RunProtocolResolutionInputV1:
    """Construct one complete validated value-authoritative resolution input."""

    envelope = _run_protocol.validate_run_protocol_envelope_v1(envelope)
    _run_protocol.encode_run_protocol_envelope_v1(envelope)
    profile = lookup_run_protocol_profile(envelope.profile_ref)
    try:
        if type(authorized_profile) is not RunProtocolProfileDefinitionV1:
            raise _S2StateError("authorized_profile has the wrong exact type")
        if authorized_profile is not profile:
            raise _S2StateError("authorized_profile is not the catalogue object")
        override_ref, entries = _validate_override_set_state(authorized_overrides)
        _validate_compatibility_without_lookup(profile, override_ref, entries)
        if _profile_pair(override_ref) != _profile_pair(envelope.profile_ref):
            raise _S2StateError("authorized overrides contradict the envelope")
        return _construct_resolution_input(
            envelope, profile, authorized_overrides
        )
    except _S2StateError as exc:
        raise RunProtocolResolutionIntegrityError(
            "resolution input construction received invalid S2 state"
        ) from exc


def validate_run_protocol_resolution_input_v1(
    value: RunProtocolResolutionInputV1,
) -> RunProtocolResolutionInputV1:
    """Revalidate the complete owner-specific resolution-input state."""

    if type(value) is not RunProtocolResolutionInputV1:
        raise TypeError("expected RunProtocolResolutionInputV1")
    try:
        validated, _, _, _ = _validated_resolution_context(value)
        return validated
    except _S2StateError as exc:
        raise RunProtocolResolutionIntegrityError(
            "Run Protocol resolution-input state is invalid"
        ) from exc


def encode_run_protocol_resolution_input_v1(
    value: RunProtocolResolutionInputV1,
) -> bytes:
    """Encode one validated resolution input as exact compact UTF-8 JSON."""

    if type(value) is not RunProtocolResolutionInputV1:
        raise TypeError("expected RunProtocolResolutionInputV1")
    try:
        _, envelope_bytes, profile, entries = _validated_resolution_context(value)
    except _S2StateError as exc:
        raise RunProtocolResolutionIntegrityError(
            "Run Protocol resolution-input state is invalid"
        ) from exc
    return _encode_resolution_parts(envelope_bytes, profile, entries)


def fingerprint_run_protocol_resolution_input_v1(
    value: RunProtocolResolutionInputV1,
) -> RunProtocolResolutionFingerprint:
    """Fingerprint one exact canonical resolution input using v1 framing."""

    encoded = encode_run_protocol_resolution_input_v1(value)
    return RunProtocolResolutionFingerprint(value=_fingerprint_from_bytes(encoded))


def resolve_run_protocol_objectives_v1(
    value: RunProtocolResolutionInputV1,
) -> ResolvedRunProtocolObjectivesV1:
    """Resolve one validated resolver-v1 input without presentation mechanics."""

    if type(value) is not RunProtocolResolutionInputV1:
        raise TypeError("expected RunProtocolResolutionInputV1")
    try:
        validated, envelope_bytes, profile, entries = _validated_resolution_context(
            value
        )
        final_values = _build_final_values_from_parts(profile, entries)
        encoded = _encode_resolution_parts(envelope_bytes, profile, entries)
        fingerprint_value = _fingerprint_from_bytes(encoded)
        result = _construct_resolved_output(
            validated, final_values, fingerprint_value
        )
        _validate_resolved_output_state(result)
        return result
    except _S2StateError as exc:
        raise RunProtocolResolutionIntegrityError(
            "Run Protocol resolved-output state is invalid"
        ) from exc


def resolve_run_protocol_objectives(
    envelope: _run_protocol.RunProtocolEnvelopeV1,
    approved_overrides: RunProtocolOverrideProposalV1,
    *,
    expected_epoch: str,
    expected_version: int,
) -> ResolvedRunProtocolObjectivesV1:
    """Dispatch the sole deterministic S2 profile-resolution facade."""

    if type(expected_epoch) is not str or type(expected_version) is not int:
        raise RunProtocolResolutionIntegrityError(
            "trusted Run Protocol resolver selectors have invalid types"
        )
    if (
        expected_epoch != RUN_PROTOCOL_RESOLUTION_EPOCH
        or expected_version != RUN_PROTOCOL_RESOLUTION_V1_VERSION
    ):
        raise UnsupportedRunProtocolResolverVersionError(
            "trusted Run Protocol resolver version is unsupported"
        )

    envelope = _run_protocol.validate_run_protocol_envelope_v1(envelope)
    envelope_bytes = _run_protocol.encode_run_protocol_envelope_v1(envelope)
    profile = lookup_run_protocol_profile(envelope.profile_ref)
    try:
        overrides = _canonicalize_proposal_without_lookup(
            profile, approved_overrides
        )
        override_ref, entries = _validate_override_set_state(overrides)
        _validate_compatibility_without_lookup(profile, override_ref, entries)
        final_values = _build_final_values_from_parts(profile, entries)
        resolution_input = _construct_resolution_input(
            envelope, profile, overrides
        )
        encoded = _encode_resolution_parts(envelope_bytes, profile, entries)
        fingerprint_value = _fingerprint_from_bytes(encoded)
        result = _construct_resolved_output(
            resolution_input, final_values, fingerprint_value
        )
        _validate_resolved_output_state(result)
        return result
    except _S2StateError as exc:
        raise RunProtocolResolutionIntegrityError(
            "Run Protocol resolver-v1 S2 state is invalid"
        ) from exc


def _validate_fingerprint_state(
    value: _Any, *, path: str
) -> RunProtocolResolutionFingerprint:
    state = _model_state(value, RunProtocolResolutionFingerprint, path=path)
    fingerprint = state["value"]
    if type(fingerprint) is not str or _FINGERPRINT.fullmatch(fingerprint) is None:
        raise _S2StateError(f"{path}.value is not exact lowercase SHA-256 hex")
    return value


def _validate_resolved_output_state(
    value: _Any,
) -> ResolvedRunProtocolObjectivesV1:
    state = _model_state(
        value,
        ResolvedRunProtocolObjectivesV1,
        path="ResolvedRunProtocolObjectivesV1",
    )
    resolution_input = state["resolution_input"]
    validated, envelope_bytes, profile, entries = _validated_resolution_context(
        resolution_input
    )
    final_values = _validate_objective_values_state(
        state["final_values"], path="ResolvedRunProtocolObjectivesV1.final_values"
    )
    expected_values = _build_final_values_from_parts(profile, entries)
    if final_values != expected_values:
        raise _S2StateError("resolved final values contradict the resolution input")
    fingerprint = _validate_fingerprint_state(
        state["fingerprint"], path="ResolvedRunProtocolObjectivesV1.fingerprint"
    )
    expected_fingerprint = _fingerprint_from_bytes(
        _encode_resolution_parts(envelope_bytes, profile, entries)
    )
    if fingerprint.value != expected_fingerprint:
        raise _S2StateError("resolved fingerprint contradicts the resolution input")
    if validated is not resolution_input:
        raise _S2StateError("resolved resolution input identity changed")
    return value
