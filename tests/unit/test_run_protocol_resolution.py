"""P3.3-S2 deterministic profile-resolution contract and direct proof."""

from __future__ import annotations

import ast
from enum import IntEnum, StrEnum
import hashlib
import inspect
import itertools
import json
import locale
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Literal, get_type_hints
import warnings

from pydantic import ValidationError
import pytest

from deviation_protocol.domain import run_protocol as s1
from deviation_protocol.domain import run_protocol_resolution as resolution
from deviation_protocol.infrastructure.run_protocol_persistence import (
    RunProtocolStoredRecordIntegrityError,
    StoredRunProtocolEnvelopeRecordV1,
    run_protocol_envelope_from_storage,
)


ABSENT = object()

PARAMETER_NAMES = (
    "resource_pressure",
    "social_trust",
    "consequence_severity",
    "information_opacity",
    "conflict_intensity",
)

PROFILE_ORACLE = (
    (
        "difficulty.silent-hunting-ground",
        1,
        "Extreme — Silent Hunting Ground",
        (95, 10, 95, 90, 90),
        (
            (80, 85, 90, 95, 100),
            (0, 5, 10, 15, 20, 25),
            (80, 85, 90, 95, 100),
            (75, 80, 85, 90, 95, 100),
            (75, 80, 85, 90, 95, 100),
        ),
        12_348,
        333_396,
        666_792,
    ),
    (
        "difficulty.fragile-alliance",
        1,
        "Standard — Fragile Alliance",
        (60, 45, 65, 60, 60),
        (
            (40, 45, 50, 55, 60, 65, 70, 75),
            (30, 35, 40, 45, 50, 55, 60, 65),
            (45, 50, 55, 60, 65, 70, 75, 80),
            (40, 45, 50, 55, 60, 65, 70, 75),
            (40, 45, 50, 55, 60, 65, 70, 75),
        ),
        59_049,
        1_594_323,
        3_188_646,
    ),
    (
        "difficulty.open-expedition",
        1,
        "Easier — Open Expedition",
        (25, 70, 35, 30, 35),
        (
            (10, 15, 20, 25, 30, 35, 40),
            (55, 60, 65, 70, 75, 80, 85),
            (20, 25, 30, 35, 40, 45, 50),
            (15, 20, 25, 30, 35, 40, 45),
            (20, 25, 30, 35, 40, 45, 50),
        ),
        32_768,
        884_736,
        1_769_472,
    ),
)

WORLD_TONES = ("grim", "balanced", "heroic")
REALITY_BOUNDARIES = ("lawful", "deviant", "chaotic")
RELATIONSHIP_OVERLAYS = ("off", "veiled", "charged")
PRESENTATION_ORACLE = (
    ("grim", "lawful", "off"),
    ("grim", "lawful", "veiled"),
    ("grim", "lawful", "charged"),
    ("grim", "deviant", "off"),
    ("grim", "deviant", "veiled"),
    ("grim", "deviant", "charged"),
    ("grim", "chaotic", "off"),
    ("grim", "chaotic", "veiled"),
    ("grim", "chaotic", "charged"),
    ("balanced", "lawful", "off"),
    ("balanced", "lawful", "veiled"),
    ("balanced", "lawful", "charged"),
    ("balanced", "deviant", "off"),
    ("balanced", "deviant", "veiled"),
    ("balanced", "deviant", "charged"),
    ("balanced", "chaotic", "off"),
    ("balanced", "chaotic", "veiled"),
    ("balanced", "chaotic", "charged"),
    ("heroic", "lawful", "off"),
    ("heroic", "lawful", "veiled"),
    ("heroic", "lawful", "charged"),
    ("heroic", "deviant", "off"),
    ("heroic", "deviant", "veiled"),
    ("heroic", "deviant", "charged"),
    ("heroic", "chaotic", "off"),
    ("heroic", "chaotic", "veiled"),
    ("heroic", "chaotic", "charged"),
)

PUBLIC_NAMES = (
    "RUN_PROTOCOL_RESOLUTION_EPOCH",
    "RUN_PROTOCOL_RESOLUTION_V1_VERSION",
    "RUN_PROTOCOL_RESOLUTION_V1_SCHEMA",
    "MAX_RUN_PROTOCOL_RESOLUTION_INPUT_BYTES",
    "RUN_PROTOCOL_RESOLUTION_FINGERPRINT_DOMAIN",
    "RUN_PROTOCOL_OBJECTIVE_PARAMETER_ORDER",
    "RunProtocolResolutionError",
    "UnsupportedRunProtocolResolverVersionError",
    "RunProtocolProfileLookupError",
    "RunProtocolOverrideValidationError",
    "RunProtocolResolutionIntegrityError",
    "ObjectiveParameterName",
    "ObjectiveParameterValue",
    "ObjectiveParameterValuesV1",
    "RunProtocolObjectiveOverrideV1",
    "RunProtocolOverrideRuleV1",
    "RunProtocolOverrideProposalV1",
    "RunProtocolOverrideSetV1",
    "RunProtocolProfileDefinitionV1",
    "RunProtocolResolutionInputV1",
    "RunProtocolResolutionFingerprint",
    "ResolvedRunProtocolObjectivesV1",
    "RUN_PROTOCOL_PROFILE_CATALOGUE_V1",
    "validate_objective_parameter_values_v1",
    "lookup_run_protocol_profile",
    "validate_run_protocol_overrides",
    "validate_run_protocol_profile_compatibility",
    "construct_run_protocol_resolution_input_v1",
    "validate_run_protocol_resolution_input_v1",
    "encode_run_protocol_resolution_input_v1",
    "fingerprint_run_protocol_resolution_input_v1",
    "resolve_run_protocol_objectives_v1",
    "resolve_run_protocol_objectives",
)

S1_001 = (
    b'{"profile_ref":{"profile_id":"difficulty.fragile-alliance",'
    b'"profile_version":1},"reality_boundary":"lawful",'
    b'"relationship_overlay":"off",'
    b'"schema_version":"run-protocol-envelope/v1",'
    b'"world_tone":"balanced"}'
)
RESOLUTION_001 = (
    b'{"authorized_overrides":[],"authorized_profile_id":'
    b'"difficulty.fragile-alliance","authorized_profile_version":1,'
    b'"canonical_envelope_hex":"7b2270726f66696c655f726566223a7b2270726f'
    b'66696c655f6964223a22646966666963756c74792e66726167696c652d616c6c6961'
    b'6e6365222c2270726f66696c655f76657273696f6e223a317d2c227265616c697479'
    b'5f626f756e64617279223a226c617766756c222c2272656c6174696f6e736869705f'
    b'6f7665726c6179223a226f6666222c22736368656d615f76657273696f6e223a2272'
    b'756e2d70726f746f636f6c2d656e76656c6f70652f7631222c22776f726c645f74'
    b'6f6e65223a2262616c616e636564227d","resolver_version":1,'
    b'"schema":"run-protocol-resolution/v1"}'
)
S1_002 = (
    b'{"profile_ref":{"profile_id":"difficulty.silent-hunting-ground",'
    b'"profile_version":1},"reality_boundary":"deviant",'
    b'"relationship_overlay":"charged",'
    b'"schema_version":"run-protocol-envelope/v1","world_tone":"grim"}'
)
RESOLUTION_002 = (
    b'{"authorized_overrides":[{"parameter":"resource_pressure","value":85},'
    b'{"parameter":"social_trust","value":20}],"authorized_profile_id":'
    b'"difficulty.silent-hunting-ground","authorized_profile_version":1,'
    b'"canonical_envelope_hex":"7b2270726f66696c655f726566223a7b2270726f'
    b'66696c655f6964223a22646966666963756c74792e73696c656e742d68756e74696e'
    b'672d67726f756e64222c2270726f66696c655f76657273696f6e223a317d2c227265'
    b'616c6974795f626f756e64617279223a2264657669616e74222c2272656c6174696f'
    b'6e736869705f6f7665726c6179223a2263686172676564222c22736368656d615f76'
    b'657273696f6e223a2272756e2d70726f746f636f6c2d656e76656c6f70652f7631'
    b'222c22776f726c645f746f6e65223a226772696d227d","resolver_version":1,'
    b'"schema":"run-protocol-resolution/v1"}'
)
S1_003 = (
    b'{"profile_ref":{"profile_id":"difficulty.fragile-alliance",'
    b'"profile_version":1},"reality_boundary":"chaotic",'
    b'"relationship_overlay":"charged",'
    b'"schema_version":"run-protocol-envelope/v1","world_tone":"heroic"}'
)
RESOLUTION_003 = (
    b'{"authorized_overrides":[],"authorized_profile_id":'
    b'"difficulty.fragile-alliance","authorized_profile_version":1,'
    b'"canonical_envelope_hex":"7b2270726f66696c655f726566223a7b2270726f'
    b'66696c655f6964223a22646966666963756c74792e66726167696c652d616c6c6961'
    b'6e6365222c2270726f66696c655f76657273696f6e223a317d2c227265616c697479'
    b'5f626f756e64617279223a226368616f746963222c2272656c6174696f6e73686970'
    b'5f6f7665726c6179223a2263686172676564222c22736368656d615f76657273696f'
    b'6e223a2272756e2d70726f746f636f6c2d656e76656c6f70652f7631222c22776f'
    b'726c645f746f6e65223a226865726f6963227d","resolver_version":1,'
    b'"schema":"run-protocol-resolution/v1"}'
)
RESOLUTION_004 = (
    b'{"authorized_overrides":[{"parameter":"conflict_intensity","value":65}],'
    b'"authorized_profile_id":"difficulty.fragile-alliance",'
    b'"authorized_profile_version":1,"canonical_envelope_hex":'
    b'"7b2270726f66696c655f726566223a7b2270726f66696c655f6964223a2264696666'
    b'6963756c74792e66726167696c652d616c6c69616e6365222c2270726f66696c655f'
    b'76657273696f6e223a317d2c227265616c6974795f626f756e64617279223a226c61'
    b'7766756c222c2272656c6174696f6e736869705f6f7665726c6179223a226f666622'
    b'2c22736368656d615f76657273696f6e223a2272756e2d70726f746f636f6c2d656e'
    b'76656c6f70652f7631222c22776f726c645f746f6e65223a2262616c616e63656422'
    b'7d","resolver_version":1,"schema":"run-protocol-resolution/v1"}'
)

GOLDEN_ORACLE = (
    (
        "difficulty.fragile-alliance",
        ("balanced", "lawful", "off"),
        (),
        S1_001,
        "a8fb2964e1c50a1428b33277426098cec69b0c19a33673abf0617d39d00ca2ab",
        RESOLUTION_001,
        671,
        "2cca2a7d1bc1308ca6c0cb93b440eb0f5152ecbcda313162b7c9e6ab49f795ac",
        (60, 45, 65, 60, 60),
    ),
    (
        "difficulty.silent-hunting-ground",
        ("grim", "deviant", "charged"),
        (("social_trust", 20), ("resource_pressure", 85)),
        S1_002,
        "f35b6a40b591af8dfc203f66df98b55bcf1bcf5b7ac5cdc0a9318b5959be88fc",
        RESOLUTION_002,
        772,
        "e1caa4cabad5bd0c4df75140482d42852351f062ee837911bfc2bbcf48ddd2aa",
        (85, 20, 95, 90, 90),
    ),
    (
        "difficulty.fragile-alliance",
        ("heroic", "chaotic", "charged"),
        (),
        S1_003,
        "f4556a2b47ad4b976770c8a57d32601c149ad59356c85da26e18d617e42605eb",
        RESOLUTION_003,
        677,
        "c4019fecafeeb1e23d9eb13663baf21653f04ee9fe70b3fbb7e4f2714c3218ed",
        (60, 45, 65, 60, 60),
    ),
    (
        "difficulty.fragile-alliance",
        ("balanced", "lawful", "off"),
        (("conflict_intensity", 65),),
        S1_001,
        "a8fb2964e1c50a1428b33277426098cec69b0c19a33673abf0617d39d00ca2ab",
        RESOLUTION_004,
        716,
        "ae94567793fb992eeaccfe7cadf3c5f10df3c1366224d6b0b98fbfbc8c3243ff",
        (60, 45, 65, 60, 65),
    ),
)


def _make_ref(profile_id: str, version: int = 1) -> s1.RunProtocolProfileRefV1:
    return s1.RunProtocolProfileRefV1(
        profile_id=s1.RunProtocolProfileId(value=profile_id),
        profile_version=s1.RunProtocolProfileVersion(value=version),
    )


def _make_envelope(
    profile_id: str,
    presentation: tuple[str, str, str] = ("balanced", "lawful", "off"),
    *,
    version: int = 1,
) -> s1.RunProtocolEnvelopeV1:
    tone, boundary, overlay = presentation
    return s1.RunProtocolEnvelopeV1(
        schema_version="run-protocol-envelope/v1",
        profile_ref=_make_ref(profile_id, version),
        world_tone=s1.RunProtocolWorldTone(tone),
        reality_boundary=s1.RunProtocolRealityBoundary(boundary),
        relationship_overlay=s1.RunProtocolRelationshipOverlay(overlay),
    )


def _entry(parameter: str, value: int) -> resolution.RunProtocolObjectiveOverrideV1:
    return resolution.RunProtocolObjectiveOverrideV1(
        parameter=resolution.ObjectiveParameterName(parameter),
        value=resolution.ObjectiveParameterValue(value=value),
    )


def _make_proposal(
    profile_ref: s1.RunProtocolProfileRefV1,
    items: tuple[tuple[str, int], ...],
) -> resolution.RunProtocolOverrideProposalV1:
    return resolution.RunProtocolOverrideProposalV1(
        profile_ref=profile_ref,
        entries=tuple(_entry(parameter, value) for parameter, value in items),
    )


def _resolve(
    envelope: s1.RunProtocolEnvelopeV1,
    proposal: resolution.RunProtocolOverrideProposalV1,
) -> resolution.ResolvedRunProtocolObjectivesV1:
    return resolution.resolve_run_protocol_objectives(
        envelope,
        proposal,
        expected_epoch="run-protocol-resolution",
        expected_version=1,
    )


def _objective_tuple(
    values: resolution.ObjectiveParameterValuesV1,
) -> tuple[int, int, int, int, int]:
    return (
        values.resource_pressure.value,
        values.social_trust.value,
        values.consequence_severity.value,
        values.information_opacity.value,
        values.conflict_intensity.value,
    )


def _golden_input(
    vector: tuple[Any, ...],
) -> tuple[s1.RunProtocolEnvelopeV1, resolution.RunProtocolOverrideProposalV1]:
    profile_id, presentation, items = vector[0], vector[1], vector[2]
    envelope = _make_envelope(profile_id, presentation)
    return envelope, _make_proposal(envelope.profile_ref, items)


def test_exact_public_surface_constants_signatures_and_inheritance() -> None:
    actual_names = tuple(
        name for name in vars(resolution) if not name.startswith("_")
    )
    assert len(PUBLIC_NAMES) == 33
    assert set(actual_names) == set(PUBLIC_NAMES)
    assert len(actual_names) == 33
    assert resolution.RUN_PROTOCOL_RESOLUTION_EPOCH == "run-protocol-resolution"
    assert type(resolution.RUN_PROTOCOL_RESOLUTION_EPOCH) is str
    assert resolution.RUN_PROTOCOL_RESOLUTION_V1_VERSION == 1
    assert type(resolution.RUN_PROTOCOL_RESOLUTION_V1_VERSION) is int
    assert resolution.RUN_PROTOCOL_RESOLUTION_V1_SCHEMA == (
        "run-protocol-resolution/v1"
    )
    assert resolution.MAX_RUN_PROTOCOL_RESOLUTION_INPUT_BYTES == 1_024
    assert resolution.RUN_PROTOCOL_RESOLUTION_FINGERPRINT_DOMAIN == (
        b"deviation-protocol:run-protocol-resolution-fingerprint:v1"
    )
    assert len(resolution.RUN_PROTOCOL_RESOLUTION_FINGERPRINT_DOMAIN) == 57
    assert tuple(item.value for item in resolution.RUN_PROTOCOL_OBJECTIVE_PARAMETER_ORDER) == PARAMETER_NAMES

    for exception in (
        resolution.UnsupportedRunProtocolResolverVersionError,
        resolution.RunProtocolProfileLookupError,
        resolution.RunProtocolOverrideValidationError,
        resolution.RunProtocolResolutionIntegrityError,
    ):
        assert exception.__bases__ == (resolution.RunProtocolResolutionError,)
    assert resolution.RunProtocolResolutionError.__bases__ == (ValueError,)

    expected_signatures = {
        "validate_objective_parameter_values_v1": "(value: 'ObjectiveParameterValuesV1') -> 'ObjectiveParameterValuesV1'",
        "lookup_run_protocol_profile": "(profile_ref: '_run_protocol.RunProtocolProfileRefV1') -> 'RunProtocolProfileDefinitionV1'",
        "validate_run_protocol_overrides": "(profile: 'RunProtocolProfileDefinitionV1', proposal: 'RunProtocolOverrideProposalV1') -> 'RunProtocolOverrideSetV1'",
        "validate_run_protocol_profile_compatibility": "(profile: 'RunProtocolProfileDefinitionV1', overrides: 'RunProtocolOverrideSetV1') -> 'RunProtocolOverrideSetV1'",
        "construct_run_protocol_resolution_input_v1": "(envelope: '_run_protocol.RunProtocolEnvelopeV1', *, authorized_profile: 'RunProtocolProfileDefinitionV1', authorized_overrides: 'RunProtocolOverrideSetV1') -> 'RunProtocolResolutionInputV1'",
        "validate_run_protocol_resolution_input_v1": "(value: 'RunProtocolResolutionInputV1') -> 'RunProtocolResolutionInputV1'",
        "encode_run_protocol_resolution_input_v1": "(value: 'RunProtocolResolutionInputV1') -> 'bytes'",
        "fingerprint_run_protocol_resolution_input_v1": "(value: 'RunProtocolResolutionInputV1') -> 'RunProtocolResolutionFingerprint'",
        "resolve_run_protocol_objectives_v1": "(value: 'RunProtocolResolutionInputV1') -> 'ResolvedRunProtocolObjectivesV1'",
        "resolve_run_protocol_objectives": "(envelope: '_run_protocol.RunProtocolEnvelopeV1', approved_overrides: 'RunProtocolOverrideProposalV1', *, expected_epoch: 'str', expected_version: 'int') -> 'ResolvedRunProtocolObjectivesV1'",
    }
    for name, expected in expected_signatures.items():
        assert str(inspect.signature(getattr(resolution, name))) == expected

    input_signature = inspect.signature(resolution.RunProtocolResolutionInputV1)
    assert tuple(input_signature.parameters) == (
        "schema",
        "resolver_version",
        "envelope",
        "authorized_profile",
        "authorized_overrides",
    )
    input_hints = get_type_hints(
        resolution.RunProtocolResolutionInputV1, include_extras=True
    )
    assert input_hints == {
        "schema": Literal["run-protocol-resolution/v1"],
        "resolver_version": Literal[1],
        "envelope": s1.RunProtocolEnvelopeV1,
        "authorized_profile": resolution.RunProtocolProfileDefinitionV1,
        "authorized_overrides": resolution.RunProtocolOverrideSetV1,
    }
    assert (
        input_signature.parameters["authorized_profile"].annotation
        is resolution.RunProtocolProfileDefinitionV1
    )
    assert (
        resolution.RunProtocolResolutionInputV1.model_fields[
            "authorized_profile"
        ].annotation
        is resolution.RunProtocolProfileDefinitionV1
    )
    assert "SkipValidation" not in repr(input_hints)
    assert "SkipValidation" not in str(input_signature)

    output_signature = inspect.signature(resolution.ResolvedRunProtocolObjectivesV1)
    assert tuple(output_signature.parameters) == (
        "resolution_input",
        "final_values",
        "fingerprint",
    )
    assert get_type_hints(
        resolution.ResolvedRunProtocolObjectivesV1, include_extras=True
    ) == {
        "resolution_input": resolution.RunProtocolResolutionInputV1,
        "final_values": resolution.ObjectiveParameterValuesV1,
        "fingerprint": resolution.RunProtocolResolutionFingerprint,
    }


def test_all_s2_carriers_are_strict_frozen_and_revalidate() -> None:
    carriers = (
        resolution.ObjectiveParameterValue,
        resolution.ObjectiveParameterValuesV1,
        resolution.RunProtocolObjectiveOverrideV1,
        resolution.RunProtocolOverrideRuleV1,
        resolution.RunProtocolOverrideProposalV1,
        resolution.RunProtocolOverrideSetV1,
        resolution.RunProtocolProfileDefinitionV1,
        resolution.RunProtocolResolutionInputV1,
        resolution.RunProtocolResolutionFingerprint,
        resolution.ResolvedRunProtocolObjectivesV1,
    )
    for carrier in carriers:
        config = carrier.model_config
        assert config["extra"] == "forbid"
        assert config["strict"] is True
        assert config["frozen"] is True
        assert config["revalidate_instances"] == "always"


def test_trusted_public_constructors_enforce_catalogue_identity_and_revalidation() -> None:
    envelope = _make_envelope("difficulty.fragile-alliance")
    profile = resolution.lookup_run_protocol_profile(envelope.profile_ref)
    proposal = _make_proposal(envelope.profile_ref, ())
    overrides = resolution.validate_run_protocol_overrides(profile, proposal)

    valid_input = resolution.RunProtocolResolutionInputV1(
        schema="run-protocol-resolution/v1",
        resolver_version=1,
        envelope=envelope,
        authorized_profile=profile,
        authorized_overrides=overrides,
    )
    assert valid_input.authorized_profile is profile
    valid_fingerprint = resolution.fingerprint_run_protocol_resolution_input_v1(
        valid_input
    )
    valid_output = resolution.ResolvedRunProtocolObjectivesV1(
        resolution_input=valid_input,
        final_values=profile.base_values,
        fingerprint=valid_fingerprint,
    )
    assert valid_output.resolution_input is valid_input
    assert valid_output.resolution_input.authorized_profile is profile

    fresh_equal = resolution.RunProtocolProfileDefinitionV1(
        profile_ref=profile.profile_ref,
        label=profile.label,
        base_values=profile.base_values,
        override_rules=profile.override_rules,
        server_default_eligible=False,
    )
    hostile_label = resolution.RunProtocolProfileDefinitionV1.model_construct(
        _fields_set={
            "profile_ref",
            "label",
            "base_values",
            "override_rules",
            "server_default_eligible",
        },
        profile_ref=profile.profile_ref,
        label=123,
        base_values=profile.base_values,
        override_rules=profile.override_rules,
        server_default_eligible=False,
    )

    for hostile_profile in (fresh_equal, hostile_label):
        with pytest.raises(ValidationError):
            resolution.RunProtocolResolutionInputV1(
                schema="run-protocol-resolution/v1",
                resolver_version=1,
                envelope=envelope,
                authorized_profile=hostile_profile,
                authorized_overrides=overrides,
            )

        hostile_input = resolution.RunProtocolResolutionInputV1.model_construct(
            _fields_set={
                "schema",
                "resolver_version",
                "envelope",
                "authorized_profile",
                "authorized_overrides",
            },
            schema="run-protocol-resolution/v1",
            resolver_version=1,
            envelope=envelope,
            authorized_profile=hostile_profile,
            authorized_overrides=overrides,
        )
        with pytest.raises(ValidationError):
            resolution.ResolvedRunProtocolObjectivesV1(
                resolution_input=hostile_input,
                final_values=profile.base_values,
                fingerprint=valid_fingerprint,
            )

    assert hostile_label.label == 123
    assert valid_input.authorized_profile is profile
    assert valid_output.resolution_input.authorized_profile is profile


def test_exact_em_dash_labels_and_catalogue_literal_oracle() -> None:
    assert len(resolution.RUN_PROTOCOL_PROFILE_CATALOGUE_V1) == 3
    for entry_value, oracle in zip(
        resolution.RUN_PROTOCOL_PROFILE_CATALOGUE_V1,
        PROFILE_ORACLE,
        strict=True,
    ):
        profile_id, version, label, defaults, permitted, _, _, _ = oracle
        assert entry_value.label == label
        dash = entry_value.label[entry_value.label.index("—")]
        assert ord(dash) == 0x2014
        assert dash.encode("utf-8") == b"\xe2\x80\x94"
        assert " — ".encode("utf-8") == b"\x20\xe2\x80\x94\x20"
        assert entry_value.profile_ref.profile_id.value == profile_id
        assert entry_value.profile_ref.profile_version.value == version
        assert _objective_tuple(entry_value.base_values) == defaults
        assert entry_value.server_default_eligible is False
        assert type(entry_value.server_default_eligible) is bool
        assert tuple(rule.parameter.value for rule in entry_value.override_rules) == PARAMETER_NAMES
        assert tuple(
            tuple(range(rule.minimum.value, rule.maximum.value + 1, rule.step))
            for rule in entry_value.override_rules
        ) == permitted
        detached_ref = _make_ref(profile_id, version)
        assert resolution.lookup_run_protocol_profile(detached_ref) is entry_value


@pytest.mark.parametrize(
    "bad_value",
    [True, 1.0, "5", -5, 42, 105],
)
def test_numeric_domain_rejects_non_exact_global_values(bad_value: object) -> None:
    with pytest.raises(ValidationError):
        resolution.ObjectiveParameterValue(value=bad_value)  # type: ignore[arg-type]


def test_numeric_domain_rejects_intenum_and_integer_subclass() -> None:
    class NumberEnum(IntEnum):
        FIVE = 5

    class IntegerSubclass(int):
        pass

    for value in (NumberEnum.FIVE, IntegerSubclass(5)):
        with pytest.raises(ValidationError):
            resolution.ObjectiveParameterValue(value=value)
    assert tuple(
        resolution.ObjectiveParameterValue(value=value).value
        for value in (
            0,
            5,
            10,
            15,
            20,
            25,
            30,
            35,
            40,
            45,
            50,
            55,
            60,
            65,
            70,
            75,
            80,
            85,
            90,
            95,
            100,
        )
    ) == tuple(range(0, 101, 5))


def test_direct_carrier_invalidity_remains_pydantic_validation_error() -> None:
    ref = _make_ref("difficulty.fragile-alliance")
    valid_entry = _entry("resource_pressure", 60)
    invalid_constructors = (
        lambda: resolution.RunProtocolObjectiveOverrideV1(
            parameter="resource_pressure", value=valid_entry.value
        ),
        lambda: resolution.RunProtocolObjectiveOverrideV1(
            parameter=valid_entry.parameter, value=60
        ),
        lambda: resolution.RunProtocolOverrideProposalV1(
            profile_ref=ref, entries=[valid_entry]
        ),
        lambda: resolution.RunProtocolOverrideProposalV1(profile_ref=ref),
        lambda: resolution.RunProtocolOverrideProposalV1(
            profile_ref=ref, entries=(valid_entry,) * 6
        ),
        lambda: resolution.RunProtocolResolutionFingerprint(value="A" * 64),
        lambda: resolution.RunProtocolResolutionFingerprint(value="0x" + "a" * 64),
    )
    for constructor in invalid_constructors:
        with pytest.raises(ValidationError):
            constructor()


def test_four_independent_published_golden_vectors() -> None:
    results: list[resolution.ResolvedRunProtocolObjectivesV1] = []
    for vector in GOLDEN_ORACLE:
        envelope, proposal = _golden_input(vector)
        result = _resolve(envelope, proposal)
        encoded_envelope = s1.encode_run_protocol_envelope_v1(envelope)
        encoded_resolution = resolution.encode_run_protocol_resolution_input_v1(
            result.resolution_input
        )
        assert encoded_envelope == vector[3]
        assert len(encoded_envelope) == len(vector[3])
        assert hashlib.sha256(encoded_envelope).hexdigest() == vector[4]
        assert encoded_resolution == vector[5]
        assert len(encoded_resolution) == len(vector[5])
        assert 57 + 1 + 4 + len(encoded_resolution) == vector[6]
        assert result.fingerprint.value == vector[7]
        assert _objective_tuple(result.final_values) == vector[8]
        assert result.fingerprint == resolution.fingerprint_run_protocol_resolution_input_v1(
            result.resolution_input
        )
        results.append(result)
    assert len(S1_001) == 205
    assert len(S1_002) == 211
    assert len(S1_003) == 208
    assert tuple(map(len, (RESOLUTION_001, RESOLUTION_002, RESOLUTION_003, RESOLUTION_004))) == (
        609,
        710,
        615,
        654,
    )
    assert results[0].final_values == results[2].final_values
    assert results[0].fingerprint != results[2].fingerprint
    assert results[0].fingerprint != results[3].fingerprint
    assert results[0].resolution_input.authorized_overrides.entries == ()
    assert tuple(
        (entry.parameter.value, entry.value.value)
        for entry in results[3].resolution_input.authorized_overrides.entries
    ) == (("conflict_intensity", 65),)


def test_reachable_maximum_is_exactly_863_and_defensive_bound_is_exact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    envelope = _make_envelope(
        "difficulty.silent-hunting-ground",
        ("balanced", "deviant", "charged"),
    )
    proposal = _make_proposal(
        envelope.profile_ref,
        (
            ("resource_pressure", 100),
            ("social_trust", 25),
            ("consequence_severity", 100),
            ("information_opacity", 100),
            ("conflict_intensity", 100),
        ),
    )
    result = _resolve(envelope, proposal)
    assert len(resolution.encode_run_protocol_resolution_input_v1(result.resolution_input)) == 863
    original_encoder = resolution._canonical_resolution_json_bytes
    monkeypatch.setattr(
        resolution, "_canonical_resolution_json_bytes", lambda _payload: b"x" * 1_024
    )
    assert len(resolution.encode_run_protocol_resolution_input_v1(result.resolution_input)) == 1_024
    monkeypatch.setattr(
        resolution, "_canonical_resolution_json_bytes", lambda _payload: b"x" * 1_025
    )
    with pytest.raises(resolution.RunProtocolResolutionIntegrityError):
        resolution.encode_run_protocol_resolution_input_v1(result.resolution_input)
    monkeypatch.setattr(resolution, "_canonical_resolution_json_bytes", original_encoder)


def test_override_boundaries_wrong_steps_and_profile_ranges() -> None:
    for oracle in PROFILE_ORACLE:
        profile_id, version, _, _, permitted, _, _, _ = oracle
        ref = _make_ref(profile_id, version)
        profile = resolution.lookup_run_protocol_profile(ref)
        for parameter, permitted_values in zip(PARAMETER_NAMES, permitted, strict=True):
            for value in (permitted_values[0], permitted_values[-1]):
                proposal = _make_proposal(ref, ((parameter, value),))
                override_set = resolution.validate_run_protocol_overrides(
                    profile, proposal
                )
                assert resolution.validate_run_protocol_profile_compatibility(
                    profile, override_set
                ) is override_set
            for value in range(0, 101, 5):
                proposal = _make_proposal(ref, ((parameter, value),))
                override_set = resolution.validate_run_protocol_overrides(
                    profile, proposal
                )
                if value in permitted_values:
                    assert resolution.validate_run_protocol_profile_compatibility(
                        profile, override_set
                    ) is override_set
                else:
                    with pytest.raises(
                        resolution.RunProtocolOverrideValidationError
                    ):
                        resolution.validate_run_protocol_profile_compatibility(
                            profile, override_set
                        )
    for wrong_step in tuple(value for value in range(0, 101) if value % 5):
        with pytest.raises(ValidationError):
            resolution.ObjectiveParameterValue(value=wrong_step)


def test_dispatcher_precedence_and_s1_exception_ownership() -> None:
    with pytest.raises(resolution.UnsupportedRunProtocolResolverVersionError):
        resolution.resolve_run_protocol_objectives(
            object(),
            object(),
            expected_epoch="run-protocol-resolution",
            expected_version=2,
        )
    for epoch, version in (
        (1, 1),
        ("run-protocol-resolution", True),
        (StrEnum("Epoch", {"VALUE": "run-protocol-resolution"}).VALUE, 1),
    ):
        with pytest.raises(resolution.RunProtocolResolutionIntegrityError):
            resolution.resolve_run_protocol_objectives(
                object(),
                object(),
                expected_epoch=epoch,  # type: ignore[arg-type]
                expected_version=version,
            )
    with pytest.raises(TypeError):
        resolution.resolve_run_protocol_objectives(
            object(),
            object(),
            expected_epoch="run-protocol-resolution",
            expected_version=1,
        )

    envelope = _make_envelope("difficulty.fragile-alliance")
    proposal = _make_proposal(envelope.profile_ref, ())
    original = envelope.profile_ref.profile_version.value
    object.__setattr__(envelope.profile_ref.profile_version, "value", True)
    try:
        with pytest.raises(s1.RunProtocolValidationError) as error:
            _resolve(envelope, proposal)
        assert type(error.value.__cause__) is ValidationError
    finally:
        object.__setattr__(envelope.profile_ref.profile_version, "value", original)

    payload = s1.encode_run_protocol_envelope_v1(
        _make_envelope("difficulty.fragile-alliance")
    )
    with pytest.raises(s1.UnsupportedRunProtocolVersionError):
        s1.decode_run_protocol_envelope(
            payload,
            expected_epoch="run-protocol-envelope",
            expected_version=2,
        )
    with pytest.raises(RunProtocolStoredRecordIntegrityError):
        run_protocol_envelope_from_storage(
            StoredRunProtocolEnvelopeRecordV1(
                schema_epoch="run-protocol-envelope",
                record_version=2,
                canonical_payload=payload,
            )
        )


def _replace_hostile_attribute(target: Any, name: str, hostile: Any) -> Any:
    original = object.__getattribute__(target, name)
    object.__setattr__(target, name, hostile)

    def restore() -> None:
        object.__setattr__(target, name, original)

    return restore


def _add_hostile_dict_field(target: Any) -> Any:
    state = object.__getattribute__(target, "__dict__")
    assert "hostile" not in state
    state["hostile"] = True

    def restore() -> None:
        del state["hostile"]

    return restore


def _remove_hostile_fields_set_member(target: Any, field: str) -> Any:
    fields_set = object.__getattribute__(target, "__pydantic_fields_set__")
    original = set(fields_set)
    fields_set.remove(field)

    def restore() -> None:
        fields_set.clear()
        fields_set.update(original)

    return restore


def _assert_public_integrity_after_mutation(
    mutate: Any,
    operation: Any,
) -> None:
    restore = mutate()
    output = None
    fingerprint = None
    try:
        with pytest.raises(resolution.RunProtocolResolutionIntegrityError):
            output = operation()
            if isinstance(output, resolution.ResolvedRunProtocolObjectivesV1):
                fingerprint = output.fingerprint
    finally:
        restore()
    assert output is None
    assert fingerprint is None


def _assert_mutated_override_scalar_rejected(
    envelope: s1.RunProtocolEnvelopeV1,
    hostile: Any,
) -> None:
    valid_entry = _entry("resource_pressure", 60)
    valid_proposal = resolution.RunProtocolOverrideProposalV1(
        profile_ref=envelope.profile_ref,
        entries=(valid_entry,),
    )
    stored_value = valid_proposal.entries[0].value
    original = stored_value.value
    object.__setattr__(stored_value, "value", hostile)
    output = None
    fingerprint = None
    try:
        with pytest.raises(resolution.RunProtocolResolutionIntegrityError):
            output = _resolve(envelope, valid_proposal)
            fingerprint = output.fingerprint
    finally:
        object.__setattr__(stored_value, "value", original)
    assert output is None
    assert fingerprint is None
    assert stored_value.value == 60


def _exercise_n16_public_corruption_matrix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    envelope = _make_envelope("difficulty.fragile-alliance")
    proposal = _make_proposal(
        envelope.profile_ref, (("resource_pressure", 60),)
    )
    resolved = _resolve(envelope, proposal)
    resolution_input = resolved.resolution_input
    profile = resolution.lookup_run_protocol_profile(envelope.profile_ref)
    overrides = resolution_input.authorized_overrides
    override_entry = overrides.entries[0]

    override_operation = lambda: resolution.validate_run_protocol_profile_compatibility(
        profile, overrides
    )
    _assert_public_integrity_after_mutation(
        lambda: _replace_hostile_attribute(override_entry.value, "value", 42),
        override_operation,
    )
    _assert_public_integrity_after_mutation(
        lambda: _replace_hostile_attribute(overrides, "entries", [override_entry]),
        override_operation,
    )
    _assert_public_integrity_after_mutation(
        lambda: _add_hostile_dict_field(overrides),
        override_operation,
    )
    _assert_public_integrity_after_mutation(
        lambda: _remove_hostile_fields_set_member(overrides, "entries"),
        override_operation,
    )
    _assert_public_integrity_after_mutation(
        lambda: _replace_hostile_attribute(
            overrides, "__pydantic_extra__", {"hostile": True}
        ),
        override_operation,
    )
    _assert_public_integrity_after_mutation(
        lambda: _replace_hostile_attribute(
            overrides, "__pydantic_private__", {"hostile": True}
        ),
        override_operation,
    )

    input_operation = lambda: resolution.resolve_run_protocol_objectives_v1(
        resolution_input
    )
    _assert_public_integrity_after_mutation(
        lambda: _replace_hostile_attribute(
            resolution_input, "schema", "run-protocol-resolution/hostile"
        ),
        input_operation,
    )
    _assert_public_integrity_after_mutation(
        lambda: _replace_hostile_attribute(
            resolution_input, "resolver_version", True
        ),
        input_operation,
    )
    _assert_public_integrity_after_mutation(
        lambda: _add_hostile_dict_field(resolution_input),
        input_operation,
    )
    _assert_public_integrity_after_mutation(
        lambda: _remove_hostile_fields_set_member(resolution_input, "schema"),
        input_operation,
    )
    _assert_public_integrity_after_mutation(
        lambda: _replace_hostile_attribute(
            resolution_input, "__pydantic_extra__", {"hostile": True}
        ),
        input_operation,
    )
    _assert_public_integrity_after_mutation(
        lambda: _replace_hostile_attribute(
            resolution_input, "__pydantic_private__", {"hostile": True}
        ),
        input_operation,
    )

    original_builder = resolution._construct_resolved_output

    def assert_injected_output_mutation(mutator: Any) -> None:
        restorers: list[Any] = []

        def hostile_builder(*args: Any, **kwargs: Any) -> Any:
            result = original_builder(*args, **kwargs)
            restorers.append(mutator(result))
            return result

        monkeypatch.setattr(resolution, "_construct_resolved_output", hostile_builder)
        output = None
        fingerprint = None
        try:
            with pytest.raises(resolution.RunProtocolResolutionIntegrityError):
                output = resolution.resolve_run_protocol_objectives_v1(
                    resolution_input
                )
                fingerprint = output.fingerprint
        finally:
            monkeypatch.setattr(
                resolution, "_construct_resolved_output", original_builder
            )
            for restore in reversed(restorers):
                restore()
        assert output is None
        assert fingerprint is None

    for mutator in (
        lambda value: _replace_hostile_attribute(
            value.final_values.resource_pressure, "value", 65
        ),
        lambda value: _add_hostile_dict_field(value),
        lambda value: _remove_hostile_fields_set_member(value, "fingerprint"),
        lambda value: _replace_hostile_attribute(
            value, "__pydantic_extra__", {"hostile": True}
        ),
        lambda value: _replace_hostile_attribute(
            value, "__pydantic_private__", {"hostile": True}
        ),
        lambda value: _replace_hostile_attribute(
            value.fingerprint, "value", "A" * 64
        ),
        lambda value: _add_hostile_dict_field(value.fingerprint),
        lambda value: _remove_hostile_fields_set_member(
            value.fingerprint, "value"
        ),
        lambda value: _replace_hostile_attribute(
            value.fingerprint, "__pydantic_extra__", {"hostile": True}
        ),
        lambda value: _replace_hostile_attribute(
            value.fingerprint, "__pydantic_private__", {"hostile": True}
        ),
    ):
        assert_injected_output_mutation(mutator)

    repeated = resolution.resolve_run_protocol_objectives_v1(resolution_input)
    assert repeated == resolved
    assert repeated.fingerprint == resolved.fingerprint


def test_negative_vectors_n01_through_n22_in_exact_sequence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[str] = []
    standard = _make_envelope("difficulty.fragile-alliance")
    empty = _make_proposal(standard.profile_ref, ())

    with pytest.raises(resolution.UnsupportedRunProtocolResolverVersionError):
        resolution.resolve_run_protocol_objectives(
            object(), object(), expected_epoch="run-protocol-resolution", expected_version=2
        )
    observed.append("N01")
    with pytest.raises(resolution.RunProtocolResolutionIntegrityError):
        resolution.resolve_run_protocol_objectives(
            standard, empty, expected_epoch="run-protocol-resolution", expected_version=True
        )
    observed.append("N02")
    with pytest.raises(ValidationError):
        s1.RunProtocolEnvelopeV1(
            schema_version="run-protocol-envelope/v1",
            world_tone=s1.RunProtocolWorldTone.BALANCED,
            reality_boundary=s1.RunProtocolRealityBoundary.LAWFUL,
            relationship_overlay=s1.RunProtocolRelationshipOverlay.OFF,
        )
    observed.append("N03")
    for profile_id, version, vector_id in (
        ("difficulty.fragile-alliance", 2, "N04"),
        ("difficulty.unknown", 1, "N05"),
    ):
        envelope = _make_envelope(profile_id, version=version)
        proposal = _make_proposal(envelope.profile_ref, ())
        with pytest.raises(resolution.RunProtocolProfileLookupError):
            _resolve(envelope, proposal)
        observed.append(vector_id)
    contradictory = _make_proposal(_make_ref("difficulty.open-expedition"), ())
    with pytest.raises(resolution.RunProtocolOverrideValidationError):
        _resolve(standard, contradictory)
    observed.append("N06")
    duplicate = _make_proposal(
        standard.profile_ref,
        (("resource_pressure", 60), ("resource_pressure", 60)),
    )
    with pytest.raises(resolution.RunProtocolOverrideValidationError):
        _resolve(standard, duplicate)
    observed.append("N07")
    with pytest.raises(ValidationError):
        resolution.RunProtocolObjectiveOverrideV1(
            parameter="resource_pressure_extra",
            value=resolution.ObjectiveParameterValue(value=60),
        )
    valid_entry = _entry("resource_pressure", 60)
    original_parameter = valid_entry.parameter
    object.__setattr__(valid_entry, "parameter", "resource_pressure_extra")
    mutated_proposal = resolution.RunProtocolOverrideProposalV1.model_construct(
        _fields_set={"profile_ref", "entries"},
        profile_ref=standard.profile_ref,
        entries=(valid_entry,),
    )
    try:
        with pytest.raises(resolution.RunProtocolResolutionIntegrityError):
            _resolve(standard, mutated_proposal)
    finally:
        object.__setattr__(valid_entry, "parameter", original_parameter)
    observed.append("N08")
    with pytest.raises(ValidationError):
        resolution.RunProtocolObjectiveOverrideV1(
            parameter=resolution.ObjectiveParameterName.RESOURCE_PRESSURE
        )
    value_carrier = valid_entry.value
    del valid_entry.__dict__["value"]
    try:
        with pytest.raises(resolution.RunProtocolResolutionIntegrityError):
            _resolve(standard, mutated_proposal)
    finally:
        valid_entry.__dict__["value"] = value_carrier
    observed.append("N09")
    class NumberEnum(IntEnum):
        ONE = 1
    class IntegerSubclass(int):
        pass
    for value in (True, NumberEnum.ONE, IntegerSubclass(60), 60.0, "60"):
        with pytest.raises(ValidationError):
            resolution.ObjectiveParameterValue(value=value)
        _assert_mutated_override_scalar_rejected(standard, value)
    observed.append("N10")
    for value in (-5, 42, 105):
        with pytest.raises(ValidationError):
            resolution.ObjectiveParameterValue(value=value)
        _assert_mutated_override_scalar_rejected(standard, value)
    observed.append("N11")
    extreme = _make_envelope("difficulty.silent-hunting-ground")
    with pytest.raises(resolution.RunProtocolOverrideValidationError):
        _resolve(extreme, _make_proposal(extreme.profile_ref, (("resource_pressure", 75),)))
    observed.append("N12")
    easier = _make_envelope("difficulty.open-expedition")
    with pytest.raises(resolution.RunProtocolOverrideValidationError):
        _resolve(easier, _make_proposal(easier.profile_ref, (("conflict_intensity", 0),)))
    observed.append("N13")
    for extra_name in (
        "recommendation",
        "scenario_id",
        "content_version",
        "server_id",
        "seed",
        "entropy",
        "resource_pressure",
    ):
        with pytest.raises(TypeError):
            resolution.resolve_run_protocol_objectives(
                standard,
                empty,
                expected_epoch="run-protocol-resolution",
                expected_version=1,
                **{extra_name: "Scarce"},
            )
    for label in ("Scarce", "Fluid", "Generous"):
        with pytest.raises(ValidationError):
            resolution.ObjectiveParameterValue(value=label)
    observed.append("N14")
    assert not hasattr(resolution, "decode_run_protocol_resolution_input_v1")
    observed.append("N15")
    _exercise_n16_public_corruption_matrix(monkeypatch)
    observed.append("N16")
    profile = resolution.lookup_run_protocol_profile(standard.profile_ref)
    fresh_equal = resolution.RunProtocolProfileDefinitionV1(
        profile_ref=profile.profile_ref,
        label=profile.label,
        base_values=profile.base_values,
        override_rules=profile.override_rules,
        server_default_eligible=False,
    )
    overrides = resolution.validate_run_protocol_overrides(profile, empty)
    with pytest.raises(resolution.RunProtocolResolutionIntegrityError):
        resolution.construct_run_protocol_resolution_input_v1(
            standard,
            authorized_profile=fresh_equal,
            authorized_overrides=overrides,
        )
    observed.append("N17")
    reverse = {"social_trust": 20, "resource_pressure": 85}
    forward = {"resource_pressure": 85, "social_trust": 20}
    reverse_result = _resolve(
        extreme,
        _make_proposal(extreme.profile_ref, tuple(reverse.items())),
    )
    forward_result = _resolve(
        extreme,
        _make_proposal(extreme.profile_ref, tuple(forward.items())),
    )
    assert reverse_result.final_values == forward_result.final_values
    assert reverse_result.fingerprint == forward_result.fingerprint
    assert resolution.encode_run_protocol_resolution_input_v1(
        reverse_result.resolution_input
    ) == resolution.encode_run_protocol_resolution_input_v1(
        forward_result.resolution_input
    )
    observed.append("N18")
    explicit = _resolve(
        standard,
        _make_proposal(standard.profile_ref, (("resource_pressure", 60),)),
    )
    absent = _resolve(standard, empty)
    assert explicit.final_values == absent.final_values
    assert explicit.fingerprint != absent.fingerprint
    assert len(explicit.resolution_input.authorized_overrides.entries) == 1
    observed.append("N19")
    standard_profile = resolution.RUN_PROTOCOL_PROFILE_CATALOGUE_V1[1]
    standard_scalar = standard_profile.base_values.resource_pressure
    original_default = standard_scalar.value
    object.__setattr__(standard_scalar, "value", 65)
    try:
        with pytest.raises(resolution.RunProtocolResolutionIntegrityError):
            resolution.lookup_run_protocol_profile(_make_ref("difficulty.fragile-alliance"))
    finally:
        object.__setattr__(standard_scalar, "value", original_default)
    observed.append("N20")
    corrupted = _make_envelope("difficulty.fragile-alliance")
    original_version = corrupted.profile_ref.profile_version.value
    object.__setattr__(corrupted.profile_ref.profile_version, "value", True)
    try:
        with pytest.raises(s1.RunProtocolValidationError) as error:
            _resolve(corrupted, _make_proposal(_make_ref("difficulty.fragile-alliance"), ()))
        assert type(error.value.__cause__) is ValidationError
    finally:
        object.__setattr__(corrupted.profile_ref.profile_version, "value", original_version)
    observed.append("N21")
    associated_ref = standard_profile.profile_ref
    associated_version = associated_ref.profile_version
    original_version = associated_version.value
    object.__setattr__(associated_version, "value", True)
    try:
        with pytest.raises(s1.RunProtocolValidationError) as error:
            resolution.lookup_run_protocol_profile(_make_ref("difficulty.fragile-alliance"))
        assert type(error.value.__cause__) is ValidationError
        assert not isinstance(error.value, resolution.RunProtocolResolutionError)
    finally:
        object.__setattr__(associated_version, "value", original_version)
    observed.append("N22")

    assert tuple(observed) == tuple(f"N{index:02d}" for index in range(1, 23))


def test_s2_corruption_metadata_and_owner_specific_catalogue_association() -> None:
    values = resolution.ObjectiveParameterValuesV1(
        resource_pressure=resolution.ObjectiveParameterValue(value=60),
        social_trust=resolution.ObjectiveParameterValue(value=45),
        consequence_severity=resolution.ObjectiveParameterValue(value=65),
        information_opacity=resolution.ObjectiveParameterValue(value=60),
        conflict_intensity=resolution.ObjectiveParameterValue(value=60),
    )
    assert resolution.validate_objective_parameter_values_v1(values) is values
    fields_set = values.__pydantic_fields_set__
    fields_set.remove("resource_pressure")
    try:
        with pytest.raises(resolution.RunProtocolResolutionIntegrityError):
            resolution.validate_objective_parameter_values_v1(values)
    finally:
        fields_set.add("resource_pressure")
    original_extra = values.__pydantic_extra__
    object.__setattr__(values, "__pydantic_extra__", {"hostile": True})
    try:
        with pytest.raises(resolution.RunProtocolResolutionIntegrityError):
            resolution.validate_objective_parameter_values_v1(values)
    finally:
        object.__setattr__(values, "__pydantic_extra__", original_extra)
    original_private = values.__pydantic_private__
    object.__setattr__(values, "__pydantic_private__", {"hostile": True})
    try:
        with pytest.raises(resolution.RunProtocolResolutionIntegrityError):
            resolution.validate_objective_parameter_values_v1(values)
    finally:
        object.__setattr__(values, "__pydantic_private__", original_private)

    profile = resolution.RUN_PROTOCOL_PROFILE_CATALOGUE_V1[1]
    original_ref = profile.profile_ref
    object.__setattr__(profile, "profile_ref", _make_ref("difficulty.fragile-alliance"))
    try:
        with pytest.raises(resolution.RunProtocolResolutionIntegrityError):
            resolution.lookup_run_protocol_profile(_make_ref("difficulty.fragile-alliance"))
    finally:
        object.__setattr__(profile, "profile_ref", original_ref)


def test_detached_reconstruction_requires_authoritative_relookup() -> None:
    envelope, proposal = _golden_input(GOLDEN_ORACLE[1])
    original = _resolve(envelope, proposal)
    detached_envelope = s1.decode_run_protocol_envelope_v1(
        s1.encode_run_protocol_envelope_v1(envelope)
    )
    authoritative_profile = resolution.lookup_run_protocol_profile(
        detached_envelope.profile_ref
    )
    detached_proposal = _make_proposal(
        detached_envelope.profile_ref,
        (("social_trust", 20), ("resource_pressure", 85)),
    )
    detached_overrides = resolution.validate_run_protocol_overrides(
        authoritative_profile, detached_proposal
    )
    assert resolution.validate_run_protocol_profile_compatibility(
        authoritative_profile, detached_overrides
    ) is detached_overrides
    detached_input = resolution.RunProtocolResolutionInputV1(
        schema="run-protocol-resolution/v1",
        resolver_version=1,
        envelope=detached_envelope,
        authorized_profile=authoritative_profile,
        authorized_overrides=detached_overrides,
    )
    detached = resolution.resolve_run_protocol_objectives_v1(detached_input)
    assert detached_input.authorized_profile is authoritative_profile
    assert detached.final_values == original.final_values
    assert detached.fingerprint == original.fingerprint
    assert resolution.encode_run_protocol_resolution_input_v1(
        detached.resolution_input
    ) == resolution.encode_run_protocol_resolution_input_v1(
        original.resolution_input
    )


def test_each_golden_repeats_one_hundred_times() -> None:
    for vector in GOLDEN_ORACLE:
        envelope, proposal = _golden_input(vector)
        for _ in range(100):
            result = _resolve(envelope, proposal)
            assert _objective_tuple(result.final_values) == vector[8]
            assert resolution.encode_run_protocol_resolution_input_v1(
                result.resolution_input
            ) == vector[5]
            assert result.fingerprint.value == vector[7]


def _worker_source() -> str:
    return r'''
import json
import locale
import os
from deviation_protocol.domain import run_protocol as s
from deviation_protocol.domain import run_protocol_resolution as r
requested = os.environ.get("RPRES_LOCALE")
if requested:
    try:
        locale.setlocale(locale.LC_ALL, requested)
    except locale.Error:
        print("UNSUPPORTED:" + requested)
        raise SystemExit(0)
vectors = (
 ("difficulty.fragile-alliance",("balanced","lawful","off"),()),
 ("difficulty.silent-hunting-ground",("grim","deviant","charged"),(("social_trust",20),("resource_pressure",85))),
 ("difficulty.fragile-alliance",("heroic","chaotic","charged"),()),
 ("difficulty.fragile-alliance",("balanced","lawful","off"),(("conflict_intensity",65),)),
)
rows=[]
for profile_id,presentation,items in vectors:
 ref=s.RunProtocolProfileRefV1(profile_id=s.RunProtocolProfileId(value=profile_id),profile_version=s.RunProtocolProfileVersion(value=1))
 env=s.RunProtocolEnvelopeV1(schema_version="run-protocol-envelope/v1",profile_ref=ref,world_tone=s.RunProtocolWorldTone(presentation[0]),reality_boundary=s.RunProtocolRealityBoundary(presentation[1]),relationship_overlay=s.RunProtocolRelationshipOverlay(presentation[2]))
 proposal=r.RunProtocolOverrideProposalV1(profile_ref=ref,entries=tuple(r.RunProtocolObjectiveOverrideV1(parameter=r.ObjectiveParameterName(k),value=r.ObjectiveParameterValue(value=v)) for k,v in items))
 out=r.resolve_run_protocol_objectives(env,proposal,expected_epoch="run-protocol-resolution",expected_version=1)
 values=tuple(getattr(out.final_values,name).value for name in ("resource_pressure","social_trust","consequence_severity","information_opacity","conflict_intensity"))
 rows.append((values,r.encode_run_protocol_resolution_input_v1(out.resolution_input).decode("ascii"),out.fingerprint.value))
print(json.dumps(rows,separators=(",",":")))
'''


def _run_worker(*, seed: str, locale_name: str, timezone: str) -> str:
    environment = os.environ.copy()
    environment["PYTHONHASHSEED"] = seed
    environment["RPRES_LOCALE"] = locale_name
    environment["TZ"] = timezone
    completed = subprocess.run(
        [sys.executable, "-c", _worker_source()],
        cwd=Path(__file__).resolve().parents[2],
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def test_hash_seed_process_locale_and_timezone_independence() -> None:
    expected_rows = [
        [list(vector[8]), vector[5].decode("ascii"), vector[7]]
        for vector in GOLDEN_ORACLE
    ]
    for seed in ("0", "1", "42", "random"):
        output = _run_worker(seed=seed, locale_name="C", timezone=f"UTC+{seed if seed != 'random' else '9'}")
        assert json.loads(output) == expected_rows

    unavailable: list[str] = []
    for index, locale_name in enumerate(
        (
            "English_United Kingdom.1252",
            "German_Germany.1252",
            "Turkish_Turkey.1254",
        )
    ):
        output = _run_worker(
            seed="42", locale_name=locale_name, timezone=("UTC", "UTC-7", "UTC+11")[index]
        )
        if output == "UNSUPPORTED:" + locale_name:
            unavailable.append(locale_name)
        else:
            assert json.loads(output) == expected_rows
    for locale_name in unavailable:
        warnings.warn(f"named locale unavailable and not substituted: {locale_name}")
    assert set(unavailable).issubset(
        {
            "English_United Kingdom.1252",
            "German_Germany.1252",
            "Turkish_Turkey.1254",
        }
    )


def test_no_prohibited_dependencies_io_or_categorical_projection() -> None:
    source_path = Path(resolution.__file__).resolve()
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    allowed_import_roots = {
        "__future__",
        "collections",
        "enum",
        "hashlib",
        "json",
        "re",
        "typing",
        "pydantic",
        "deviation_protocol",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(alias.name.split(".")[0] in allowed_import_roots for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] in allowed_import_roots
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"open", "hash", "print", "input", "exec", "eval"}
    assert "deviation_protocol.application" not in source
    assert "deviation_protocol.infrastructure" not in source
    assert "SkipValidation" not in source
    assert "_run_protocol.RunProtocolEnvelopeV1.model_construct(" in source
    for prohibited in (
        "Scarce",
        "Fluid",
        "Generous",
        "random",
        "uuid",
        "logging",
        "locale",
        "timezone",
        "environ",
        "filesystem",
        "database",
        "provider",
        "socket",
        "requests",
    ):
        assert prohibited not in source
    assert '.encode("utf-8")' in source
    assert 'byteorder="big"' in source
    assert "_hashlib.sha256" in source
    assert "_json.dumps" in source
    assert "os.linesep" not in source
    assert "\\r\\n" not in source


def _materialize_override_maps(
    valid_values: tuple[tuple[int, ...], ...],
) -> list[dict[str, int]]:
    dimensions = tuple((ABSENT, *values) for values in valid_values)
    maps: list[dict[str, int]] = []
    for product in itertools.product(*dimensions):
        override_map: dict[str, int] = {}
        for parameter, value in zip(PARAMETER_NAMES, product, strict=True):
            if value is not ABSENT:
                override_map[parameter] = value
        maps.append(override_map)
    return maps


def test_complete_direct_exhaustive_public_resolution_domain() -> None:
    generated_presentations = tuple(
        (tone, boundary, overlay)
        for tone in WORLD_TONES
        for boundary in REALITY_BOUNDARIES
        for overlay in RELATIONSHIP_OVERLAYS
    )
    assert generated_presentations == PRESENTATION_ORACLE
    assert len(PRESENTATION_ORACLE) == 3 * 3 * 3 == 27

    materialized = tuple(
        _materialize_override_maps(oracle[4]) for oracle in PROFILE_ORACLE
    )
    assert tuple(map(len, materialized)) == (12_348, 59_049, 32_768)
    assert sum(map(len, materialized)) == 104_165

    primary_per_profile = [0, 0, 0]
    repeat_per_profile = [0, 0, 0]
    distinct_inputs_per_profile = [0, 0, 0]
    combined_per_profile = [0, 0, 0]

    for profile_index, (oracle, override_maps) in enumerate(
        zip(PROFILE_ORACLE, materialized, strict=True)
    ):
        profile_id, version, _, defaults, _, map_count, expected_calls, expected_combined = oracle
        assert len(override_maps) == map_count
        for override_map in override_maps:
            expected_values = list(defaults)
            for parameter_index, parameter in enumerate(PARAMETER_NAMES):
                if parameter in override_map:
                    expected_values[parameter_index] = override_map[parameter]
            expected_tuple = tuple(expected_values)
            expected_items = tuple(override_map.items())
            first_primary_values: tuple[int, int, int, int, int] | None = None
            for presentation in PRESENTATION_ORACLE:
                envelope = _make_envelope(profile_id, presentation, version=version)
                proposal = _make_proposal(envelope.profile_ref, expected_items)

                primary = resolution.resolve_run_protocol_objectives(
                    envelope,
                    proposal,
                    expected_epoch="run-protocol-resolution",
                    expected_version=1,
                )
                primary_values = _objective_tuple(primary.final_values)
                primary_entries = tuple(
                    (entry.parameter.value, entry.value.value)
                    for entry in primary.resolution_input.authorized_overrides.entries
                )
                primary_bytes = resolution.encode_run_protocol_resolution_input_v1(
                    primary.resolution_input
                )
                assert primary_values == expected_tuple
                if first_primary_values is None:
                    first_primary_values = primary_values
                assert primary_values == first_primary_values
                assert primary.resolution_input.authorized_profile.profile_ref.profile_id.value == profile_id
                assert primary.resolution_input.authorized_profile.profile_ref.profile_version.value == version
                assert primary_entries == expected_items
                assert tuple(parameter for parameter, _ in primary_entries) == tuple(
                    parameter for parameter in PARAMETER_NAMES if parameter in override_map
                )
                assert not (
                    {"world_tone", "reality_boundary", "relationship_overlay"}
                    & set(type(primary.final_values).model_fields)
                )
                primary_per_profile[profile_index] += 1

                repeat = resolution.resolve_run_protocol_objectives(
                    envelope,
                    proposal,
                    expected_epoch="run-protocol-resolution",
                    expected_version=1,
                )
                repeat_bytes = resolution.encode_run_protocol_resolution_input_v1(
                    repeat.resolution_input
                )
                assert _objective_tuple(repeat.final_values) == expected_tuple
                assert repeat.final_values == primary.final_values
                assert repeat_bytes == primary_bytes
                assert repeat.fingerprint == primary.fingerprint
                repeat_per_profile[profile_index] += 1
                distinct_inputs_per_profile[profile_index] += 1
                combined_per_profile[profile_index] += 2

        assert primary_per_profile[profile_index] == expected_calls
        assert repeat_per_profile[profile_index] == expected_calls
        assert distinct_inputs_per_profile[profile_index] == expected_calls
        assert combined_per_profile[profile_index] == expected_combined

    assert tuple(primary_per_profile) == (333_396, 1_594_323, 884_736)
    assert tuple(repeat_per_profile) == (333_396, 1_594_323, 884_736)
    assert tuple(distinct_inputs_per_profile) == (333_396, 1_594_323, 884_736)
    assert tuple(combined_per_profile) == (666_792, 3_188_646, 1_769_472)
    assert sum(primary_per_profile) == 2_812_455
    assert sum(repeat_per_profile) == 2_812_455
    assert sum(distinct_inputs_per_profile) == 2_812_455
    assert sum(combined_per_profile) == 5_624_910
