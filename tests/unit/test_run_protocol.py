from __future__ import annotations

import hashlib
import inspect
import json
from enum import IntEnum, StrEnum

from pydantic import BaseModel, ValidationError
import pytest

import deviation_protocol.domain.run_protocol as run_protocol_module
from deviation_protocol.domain.run_protocol import (
    MAX_RUN_PROTOCOL_ENVELOPE_CANONICAL_BYTES,
    MAX_RUN_PROTOCOL_ENVELOPE_RAW_BYTES,
    RUN_PROTOCOL_ENVELOPE_EPOCH,
    RUN_PROTOCOL_ENVELOPE_V1_RECORD_VERSION,
    RUN_PROTOCOL_ENVELOPE_V1_SCHEMA,
    RunProtocolEnvelopeV1,
    RunProtocolProfileId,
    RunProtocolProfileRefV1,
    RunProtocolProfileVersion,
    RunProtocolRealityBoundary,
    RunProtocolRelationshipOverlay,
    RunProtocolValidationError,
    RunProtocolWorldTone,
    UnsupportedRunProtocolVersionError,
    decode_run_protocol_envelope,
    decode_run_protocol_envelope_v1,
    encode_run_protocol_envelope_v1,
    validate_run_protocol_envelope_v1,
)


GOLDEN = (
    b'{"profile_ref":{"profile_id":"profile.example","profile_version":1},'
    b'"reality_boundary":"lawful","relationship_overlay":"off",'
    b'"schema_version":"run-protocol-envelope/v1",'
    b'"world_tone":"balanced"}'
)
GOLDEN_SHA256 = "a7e0149e8241f1b4d1c74487da2b8bcf36c93d05310c76a9b847d4e57c5a3a8a"
MAXIMUM_V1_CANONICAL_BYTES = (
    b'{"profile_ref":{"profile_id":"'
    + (b"A" * 128)
    + b'","profile_version":9223372036854775807},'
    + b'"reality_boundary":"deviant",'
    + b'"relationship_overlay":"charged",'
    + b'"schema_version":"run-protocol-envelope/v1",'
    + b'"world_tone":"balanced"}'
)
MAXIMUM_V1_CANONICAL_SHA256 = (
    "0e0b1f498e1bf51656f1c5e5c742074e864da9678964c048087f52bdf5066e78"
)


class _StringSubclass(str):
    pass


class _IntegerSubclass(int):
    pass


class _ProfileIdStrEnum(StrEnum):
    VALUE = "profile.example"


class _SchemaVersionStrEnum(StrEnum):
    V1 = "run-protocol-envelope/v1"


class _ProfileVersionIntEnum(IntEnum):
    ONE = 1


def envelope(
    *,
    profile_id: str = "profile.example",
    profile_version: int = 1,
    world_tone: RunProtocolWorldTone = RunProtocolWorldTone.BALANCED,
    reality_boundary: RunProtocolRealityBoundary = (
        RunProtocolRealityBoundary.LAWFUL
    ),
    relationship_overlay: RunProtocolRelationshipOverlay = (
        RunProtocolRelationshipOverlay.OFF
    ),
) -> RunProtocolEnvelopeV1:
    return RunProtocolEnvelopeV1(
        schema_version=RUN_PROTOCOL_ENVELOPE_V1_SCHEMA,
        profile_ref=RunProtocolProfileRefV1(
            profile_id=RunProtocolProfileId(value=profile_id),
            profile_version=RunProtocolProfileVersion(
                value=profile_version
            ),
        ),
        world_tone=world_tone,
        reality_boundary=reality_boundary,
        relationship_overlay=relationship_overlay,
    )


def canonical_payload(**changes: object) -> bytes:
    payload: dict[str, object] = {
        "schema_version": RUN_PROTOCOL_ENVELOPE_V1_SCHEMA,
        "profile_ref": {
            "profile_id": "profile.example",
            "profile_version": 1,
        },
        "world_tone": "balanced",
        "reality_boundary": "lawful",
        "relationship_overlay": "off",
    }
    payload.update(changes)
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def test_exact_domain_symbol_contract_and_constants() -> None:
    public_names = {
        name
        for name in vars(run_protocol_module)
        if not name.startswith("_") and name != "annotations"
    }
    assert public_names == {
        "RUN_PROTOCOL_ENVELOPE_EPOCH",
        "RUN_PROTOCOL_ENVELOPE_V1_RECORD_VERSION",
        "RUN_PROTOCOL_ENVELOPE_V1_SCHEMA",
        "MAX_RUN_PROTOCOL_ENVELOPE_RAW_BYTES",
        "MAX_RUN_PROTOCOL_ENVELOPE_CANONICAL_BYTES",
        "RunProtocolValidationError",
        "UnsupportedRunProtocolVersionError",
        "RunProtocolProfileId",
        "RunProtocolProfileVersion",
        "RunProtocolProfileRefV1",
        "RunProtocolWorldTone",
        "RunProtocolRealityBoundary",
        "RunProtocolRelationshipOverlay",
        "RunProtocolEnvelopeV1",
        "validate_run_protocol_envelope_v1",
        "encode_run_protocol_envelope_v1",
        "decode_run_protocol_envelope_v1",
        "decode_run_protocol_envelope",
    }
    assert RUN_PROTOCOL_ENVELOPE_EPOCH == "run-protocol-envelope"
    assert type(RUN_PROTOCOL_ENVELOPE_V1_RECORD_VERSION) is int
    assert RUN_PROTOCOL_ENVELOPE_V1_RECORD_VERSION == 1
    assert RUN_PROTOCOL_ENVELOPE_V1_SCHEMA == "run-protocol-envelope/v1"
    assert MAX_RUN_PROTOCOL_ENVELOPE_RAW_BYTES == 1_024
    assert MAX_RUN_PROTOCOL_ENVELOPE_CANONICAL_BYTES == 1_024
    assert issubclass(RunProtocolValidationError, ValueError)
    assert issubclass(
        UnsupportedRunProtocolVersionError,
        RunProtocolValidationError,
    )
    assert inspect.signature(decode_run_protocol_envelope) == (
        inspect.Signature(
            parameters=(
                inspect.Parameter(
                    "payload",
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation="bytes",
                ),
                inspect.Parameter(
                    "expected_epoch",
                    inspect.Parameter.KEYWORD_ONLY,
                    annotation="str",
                ),
                inspect.Parameter(
                    "expected_version",
                    inspect.Parameter.KEYWORD_ONLY,
                    annotation="int",
                ),
            ),
            return_annotation="RunProtocolEnvelopeV1",
        )
    )


def test_all_models_are_exact_strict_frozen_required_carriers() -> None:
    expected_fields = {
        RunProtocolProfileId: ("value",),
        RunProtocolProfileVersion: ("value",),
        RunProtocolProfileRefV1: ("profile_id", "profile_version"),
        RunProtocolEnvelopeV1: (
            "schema_version",
            "profile_ref",
            "world_tone",
            "reality_boundary",
            "relationship_overlay",
        ),
    }
    for model_type, fields in expected_fields.items():
        assert issubclass(model_type, BaseModel)
        assert tuple(model_type.model_fields) == fields
        assert model_type.model_config["extra"] == "forbid"
        assert model_type.model_config["strict"] is True
        assert model_type.model_config["frozen"] is True
        assert model_type.model_config["revalidate_instances"] == "always"
        assert model_type.model_computed_fields == {}
        assert model_type.__private_attributes__ == {}
        for field in model_type.model_fields.values():
            assert field.is_required()
            assert field.alias is None
            assert field.validation_alias is None
            assert field.serialization_alias is None

    with pytest.raises(TypeError):
        RunProtocolProfileId("profile.example")  # type: ignore[misc]
    with pytest.raises(TypeError):
        RunProtocolProfileVersion(1)  # type: ignore[misc]
    with pytest.raises(TypeError):
        RunProtocolProfileRefV1(  # type: ignore[misc]
            RunProtocolProfileId(value="profile.example"),
            RunProtocolProfileVersion(value=1),
        )


@pytest.mark.parametrize(
    "value",
    (
        "",
        ".profile",
        "profile with space",
        "profile/example",
        "é",
        "A" * 129,
        1,
        True,
        None,
    ),
)
def test_profile_id_rejects_every_non_exact_identifier(value: object) -> None:
    with pytest.raises(ValidationError):
        RunProtocolProfileId(value=value)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "value",
    (
        _StringSubclass("profile.example"),
        _ProfileIdStrEnum.VALUE,
    ),
)
def test_profile_id_rejects_equal_string_subtypes_before_normalization(
    value: object,
) -> None:
    with pytest.raises(ValidationError) as error:
        RunProtocolProfileId(value=value)  # type: ignore[arg-type]
    assert type(error.value) is ValidationError


@pytest.mark.parametrize(
    "value",
    (0, -1, 2**63, True, False, 1.0, "1", None),
)
def test_profile_version_rejects_boolean_coercion_float_and_bounds(
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        RunProtocolProfileVersion(value=value)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "value",
    (
        _IntegerSubclass(1),
        _ProfileVersionIntEnum.ONE,
        True,
    ),
)
def test_profile_version_rejects_equal_integer_subtypes_before_normalization(
    value: object,
) -> None:
    with pytest.raises(ValidationError) as error:
        RunProtocolProfileVersion(value=value)  # type: ignore[arg-type]
    assert type(error.value) is ValidationError


@pytest.mark.parametrize(
    "value",
    (
        _StringSubclass(RUN_PROTOCOL_ENVELOPE_V1_SCHEMA),
        _SchemaVersionStrEnum.V1,
    ),
)
def test_schema_version_rejects_equal_string_subtypes_before_normalization(
    value: object,
) -> None:
    with pytest.raises(ValidationError) as error:
        RunProtocolEnvelopeV1(
            schema_version=value,  # type: ignore[arg-type]
            profile_ref=envelope().profile_ref,
            world_tone=RunProtocolWorldTone.BALANCED,
            reality_boundary=RunProtocolRealityBoundary.LAWFUL,
            relationship_overlay=RunProtocolRelationshipOverlay.OFF,
        )
    assert type(error.value) is ValidationError


def test_profile_reference_and_envelope_require_exact_nested_types() -> None:
    profile_id = RunProtocolProfileId(value="profile.example")
    profile_version = RunProtocolProfileVersion(value=2**63 - 1)
    profile_ref = RunProtocolProfileRefV1(
        profile_id=profile_id,
        profile_version=profile_version,
    )
    assert type(profile_ref.profile_id) is RunProtocolProfileId
    assert type(profile_ref.profile_version) is RunProtocolProfileVersion
    assert profile_ref.profile_id == profile_id
    assert profile_ref.profile_version == profile_version

    invalid_refs = (
        {"profile_id": {"value": "profile.example"}, "profile_version": profile_version},
        {"profile_id": profile_id, "profile_version": {"value": 1}},
        {"profile_id": profile_id},
        {
            "profile_id": profile_id,
            "profile_version": profile_version,
            "unknown": "x",
        },
    )
    for invalid in invalid_refs:
        with pytest.raises(ValidationError):
            RunProtocolProfileRefV1.model_validate(invalid)

    valid = envelope()
    source = valid.model_dump(mode="python")
    invalid_envelopes = (
        {**source, "profile_ref": source["profile_ref"]},
        {**source, "world_tone": "balanced"},
        {**source, "reality_boundary": "lawful"},
        {**source, "relationship_overlay": "off"},
        {key: value for key, value in source.items() if key != "world_tone"},
        {**source, "unknown": "x"},
    )
    for invalid in invalid_envelopes:
        with pytest.raises(ValidationError):
            RunProtocolEnvelopeV1.model_validate(invalid)


def test_three_presentation_enums_are_exact_and_closed() -> None:
    assert tuple(RunProtocolWorldTone) == (
        RunProtocolWorldTone.GRIM,
        RunProtocolWorldTone.BALANCED,
        RunProtocolWorldTone.HEROIC,
    )
    assert tuple(RunProtocolRealityBoundary) == (
        RunProtocolRealityBoundary.LAWFUL,
        RunProtocolRealityBoundary.DEVIANT,
        RunProtocolRealityBoundary.CHAOTIC,
    )
    assert tuple(RunProtocolRelationshipOverlay) == (
        RunProtocolRelationshipOverlay.OFF,
        RunProtocolRelationshipOverlay.VEILED,
        RunProtocolRelationshipOverlay.CHARGED,
    )
    for enum_type in (
        RunProtocolWorldTone,
        RunProtocolRealityBoundary,
        RunProtocolRelationshipOverlay,
    ):
        with pytest.raises(ValueError):
            enum_type("unknown")
        with pytest.raises(ValueError):
            enum_type(enum_type.__members__[next(iter(enum_type.__members__))].value.upper())


def test_golden_vector_bytes_length_hash_and_round_trip_are_exact() -> None:
    value = envelope()
    encoded = encode_run_protocol_envelope_v1(value)
    assert encoded == GOLDEN
    assert len(encoded) == 193
    assert hashlib.sha256(encoded).hexdigest() == GOLDEN_SHA256
    decoded = decode_run_protocol_envelope(
        encoded,
        expected_epoch=RUN_PROTOCOL_ENVELOPE_EPOCH,
        expected_version=RUN_PROTOCOL_ENVELOPE_V1_RECORD_VERSION,
    )
    assert decoded == value
    assert decoded is not value
    assert decoded.profile_ref is not value.profile_ref
    assert encode_run_protocol_envelope_v1(decoded) == GOLDEN


def test_real_maximum_legal_v1_envelope_has_independent_exact_identity() -> None:
    value = envelope(
        profile_id="A" * 128,
        profile_version=2**63 - 1,
        world_tone=RunProtocolWorldTone.BALANCED,
        reality_boundary=RunProtocolRealityBoundary.DEVIANT,
        relationship_overlay=RunProtocolRelationshipOverlay.CHARGED,
    )

    encoded = encode_run_protocol_envelope_v1(value)

    assert encoded == MAXIMUM_V1_CANONICAL_BYTES
    assert len(encoded) == 329
    assert hashlib.sha256(encoded).hexdigest() == MAXIMUM_V1_CANONICAL_SHA256
    assert len(encoded) < MAX_RUN_PROTOCOL_ENVELOPE_CANONICAL_BYTES


def test_validation_and_encoding_return_or_read_without_mutating_input() -> None:
    value = envelope(
        profile_version=2**63 - 1,
        world_tone=RunProtocolWorldTone.HEROIC,
        reality_boundary=RunProtocolRealityBoundary.CHAOTIC,
        relationship_overlay=RunProtocolRelationshipOverlay.CHARGED,
    )
    before = value.model_dump(mode="python")
    state_ids = (id(value), id(value.profile_ref), id(value.profile_ref.profile_id))
    assert validate_run_protocol_envelope_v1(value) is value
    assert encode_run_protocol_envelope_v1(value) == encode_run_protocol_envelope_v1(value)
    assert value.model_dump(mode="python") == before
    assert state_ids == (
        id(value),
        id(value.profile_ref),
        id(value.profile_ref.profile_id),
    )
    with pytest.raises(TypeError):
        validate_run_protocol_envelope_v1(object())  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        encode_run_protocol_envelope_v1(object())  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "corruption",
    (
        "unknown-field",
        "missing-field",
        "fields-set-missing",
        "fields-set-extra",
        "malformed-fields-set",
        "extra-state",
        "private-state",
        "nested-unknown",
        "nested-missing-fields-set",
        "wrong-nested-type",
        "wrong-enum-type",
        "wrong-version-literal",
    ),
)
def test_original_actual_instance_state_is_revalidated_before_encoding(
    corruption: str,
) -> None:
    value = envelope()
    if corruption == "unknown-field":
        value.__dict__["hidden"] = "x"
    elif corruption == "missing-field":
        value.__dict__.pop("world_tone")
    elif corruption == "fields-set-missing":
        value.__pydantic_fields_set__.remove("world_tone")
    elif corruption == "fields-set-extra":
        value.__pydantic_fields_set__.add("hidden")
    elif corruption == "malformed-fields-set":
        object.__setattr__(
            value,
            "__pydantic_fields_set__",
            frozenset(type(value).model_fields),
        )
    elif corruption == "extra-state":
        object.__setattr__(value, "__pydantic_extra__", {"hidden": "x"})
    elif corruption == "private-state":
        object.__setattr__(value, "__pydantic_private__", {"hidden": "x"})
    elif corruption == "nested-unknown":
        value.profile_ref.profile_id.__dict__["hidden"] = "x"
    elif corruption == "nested-missing-fields-set":
        value.profile_ref.profile_version.__pydantic_fields_set__.clear()
    elif corruption == "wrong-nested-type":
        object.__setattr__(value.profile_ref, "profile_id", {"value": "profile.example"})
    elif corruption == "wrong-enum-type":
        object.__setattr__(value, "world_tone", "balanced")
    else:
        object.__setattr__(value, "schema_version", "run-protocol-envelope/v2")

    with pytest.raises(RunProtocolValidationError):
        validate_run_protocol_envelope_v1(value)
    with pytest.raises(RunProtocolValidationError):
        encode_run_protocol_envelope_v1(value)


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    (
        ("profile_id", _StringSubclass("profile.example")),
        ("profile_id", _ProfileIdStrEnum.VALUE),
        ("profile_version", _IntegerSubclass(1)),
        ("profile_version", _ProfileVersionIntEnum.ONE),
        ("profile_version", True),
        ("schema_version", _StringSubclass(RUN_PROTOCOL_ENVELOPE_V1_SCHEMA)),
        ("schema_version", _SchemaVersionStrEnum.V1),
    ),
)
def test_original_equal_scalar_subtypes_are_rejected_after_instance_corruption(
    field: str,
    invalid_value: object,
) -> None:
    value = envelope()
    if field == "profile_id":
        object.__setattr__(value.profile_ref.profile_id, "value", invalid_value)
    elif field == "profile_version":
        object.__setattr__(
            value.profile_ref.profile_version,
            "value",
            invalid_value,
        )
    else:
        object.__setattr__(value, "schema_version", invalid_value)

    with pytest.raises(RunProtocolValidationError) as validation_error:
        validate_run_protocol_envelope_v1(value)
    assert type(validation_error.value) is RunProtocolValidationError
    with pytest.raises(RunProtocolValidationError) as encoding_error:
        encode_run_protocol_envelope_v1(value)
    assert type(encoding_error.value) is RunProtocolValidationError


def test_defensive_canonical_encoder_guard_branch_isolated_at_1024_and_1025(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Isolate the unreachable guard; injected bytes are not valid envelopes."""

    monkeypatch.setattr(
        run_protocol_module,
        "_canonical_json_bytes",
        lambda _value: b"x" * 1_024,
    )
    assert len(encode_run_protocol_envelope_v1(envelope())) == 1_024
    monkeypatch.setattr(
        run_protocol_module,
        "_canonical_json_bytes",
        lambda _value: b"x" * 1_025,
    )
    with pytest.raises(RunProtocolValidationError, match="canonical payload"):
        encode_run_protocol_envelope_v1(envelope())


@pytest.mark.parametrize(
    "payload",
    (
        b"",
        b"\xff",
        b"\xef\xbb\xbf" + GOLDEN,
        b"[]",
        b"null",
        b"true",
        b"{}",
        b"{" + b'"profile_ref":{}' * 20 + b"}",
        GOLDEN + b" trailing",
        b"/*comment*/" + GOLDEN,
        b"{" + b'"x":{' * 20 + b"0" + b"}" * 20 + b"}",
    ),
)
def test_decoder_rejects_empty_utf8_bom_trailing_array_and_depth(
    payload: bytes,
) -> None:
    with pytest.raises(RunProtocolValidationError):
        decode_run_protocol_envelope_v1(payload)


def test_public_decoder_raw_ceiling_reaches_parsing_at_1024_and_rejects_1025() -> None:
    at_limit = b" " * (1_024 - len(GOLDEN)) + GOLDEN
    assert len(at_limit) == 1_024
    with pytest.raises(RunProtocolValidationError, match="byte-identical canonical"):
        decode_run_protocol_envelope_v1(at_limit)
    with pytest.raises(RunProtocolValidationError, match="raw payload"):
        decode_run_protocol_envelope_v1(at_limit + b" ")
    for wrong_type in (GOLDEN.decode(), bytearray(GOLDEN), memoryview(GOLDEN)):
        with pytest.raises(RunProtocolValidationError, match="immutable bytes"):
            decode_run_protocol_envelope_v1(wrong_type)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "payload",
    (
        GOLDEN.replace(
            b'"profile_id":"profile.example"',
            b'"profile_id":"profile.example","profile_id":"other"',
        ),
        GOLDEN.replace(
            b'"profile_version":1',
            b'"profile_version":1,"profile_version":2',
        ),
        GOLDEN.replace(
            b'"profile_ref":{',
            b'"profile_ref":{"profile_id":"other"},"profile_ref":{',
        ),
    ),
)
def test_duplicate_members_are_rejected_at_every_object_depth(
    payload: bytes,
) -> None:
    with pytest.raises(RunProtocolValidationError, match="duplicate"):
        decode_run_protocol_envelope_v1(payload)


@pytest.mark.parametrize(
    "payload",
    (
        b" " + GOLDEN,
        GOLDEN + b" ",
        GOLDEN.replace(
            b'"profile_ref":{"profile_id":"profile.example","profile_version":1}',
            b'"profile_ref":{"profile_version":1,"profile_id":"profile.example"}',
        ),
        GOLDEN.replace(b"profile.example", b"profile\\u002eexample"),
        GOLDEN.replace(b"envelope/v1", b"envelope\\/v1"),
        GOLDEN.replace(b'"profile_version":1', b'"profile_version":1e0'),
    ),
)
def test_semantically_equivalent_noncanonical_bytes_are_rejected(
    payload: bytes,
) -> None:
    with pytest.raises(RunProtocolValidationError):
        decode_run_protocol_envelope_v1(payload)


@pytest.mark.parametrize(
    "payload",
    (
        canonical_payload(profile_ref={"profile_id": "profile.example"}),
        canonical_payload(
            profile_ref={
                "profile_id": "profile.example",
                "profile_version": 1,
                "extra": "x",
            }
        ),
        canonical_payload(profileId="profile.example"),
        canonical_payload(world_tone="unknown"),
        canonical_payload(reality_boundary="unknown"),
        canonical_payload(relationship_overlay="unknown"),
        canonical_payload(schema_version="run-protocol-envelope/v2"),
        canonical_payload(profile_ref=[]),
        canonical_payload(profile_ref=None),
        canonical_payload(
            profile_ref={"profile_id": "profile.example", "profile_version": True}
        ),
        canonical_payload(
            profile_ref={"profile_id": "profile.example", "profile_version": "1"}
        ),
        canonical_payload(
            profile_ref={"profile_id": "profile.example", "profile_version": 0}
        ),
        canonical_payload(
            profile_ref={"profile_id": "profile.example", "profile_version": -1}
        ),
        canonical_payload(
            profile_ref={"profile_id": "profile.example", "profile_version": 2**63}
        ),
        canonical_payload(
            profile_ref={"profile_id": "profile.example", "profile_version": 1.5}
        ),
    ),
)
def test_missing_extra_alias_default_enum_and_numeric_coercion_are_rejected(
    payload: bytes,
) -> None:
    with pytest.raises(RunProtocolValidationError):
        decode_run_protocol_envelope_v1(payload)


@pytest.mark.parametrize(
    "payload",
    (
        GOLDEN.replace(b'"profile_version":1', b'"profile_version":NaN'),
        GOLDEN.replace(b'"profile_version":1', b'"profile_version":Infinity'),
        GOLDEN.replace(b'"profile_version":1', b'"profile_version":-Infinity'),
        GOLDEN.replace(b'"profile_version":1', b'"profile_version":01'),
        GOLDEN.replace(b'"profile_version":1', b'"profile_version":+1'),
        GOLDEN.replace(b'"profile_version":1', b'"profile_version":1.0'),
        GOLDEN.replace(b'"profile_version":1', b'"profile_version":1e0'),
    ),
)
def test_nonfinite_float_and_alternate_integer_tokens_are_rejected(
    payload: bytes,
) -> None:
    with pytest.raises(RunProtocolValidationError):
        decode_run_protocol_envelope_v1(payload)


def test_non_nfc_strings_and_unpaired_surrogates_are_rejected() -> None:
    decomposed = canonical_payload(
        profile_ref={"profile_id": "e\u0301", "profile_version": 1}
    )
    with pytest.raises(RunProtocolValidationError, match="non-NFC"):
        decode_run_protocol_envelope_v1(decomposed)
    unpaired_surrogate = GOLDEN.replace(
        b"profile.example",
        b"profile.\\ud800",
    )
    with pytest.raises(RunProtocolValidationError):
        decode_run_protocol_envelope_v1(unpaired_surrogate)


@pytest.mark.parametrize(
    ("epoch", "version"),
    (
        ("run-protocol-envelope/v1", 1),
        ("run-protocol-envelope", 0),
        ("run-protocol-envelope", 2),
        ("", 1),
        ("future", -1),
    ),
)
def test_well_typed_unsupported_trusted_selectors_never_fall_back(
    epoch: str,
    version: int,
) -> None:
    with pytest.raises(UnsupportedRunProtocolVersionError):
        decode_run_protocol_envelope(
            GOLDEN,
            expected_epoch=epoch,
            expected_version=version,
        )


@pytest.mark.parametrize(
    ("epoch", "version"),
    (
        (1, 1),
        (None, 1),
        ("run-protocol-envelope", True),
        ("run-protocol-envelope", 1.0),
        ("run-protocol-envelope", "1"),
    ),
)
def test_malformed_trusted_selectors_are_validation_errors_not_unsupported(
    epoch: object,
    version: object,
) -> None:
    with pytest.raises(RunProtocolValidationError) as error:
        decode_run_protocol_envelope(
            GOLDEN,
            expected_epoch=epoch,  # type: ignore[arg-type]
            expected_version=version,  # type: ignore[arg-type]
        )
    assert type(error.value) is RunProtocolValidationError


def test_trusted_version_dispatch_precedes_payload_and_payload_cannot_select() -> None:
    with pytest.raises(UnsupportedRunProtocolVersionError):
        decode_run_protocol_envelope(
            b"not-json",
            expected_epoch=RUN_PROTOCOL_ENVELOPE_EPOCH,
            expected_version=2,
        )
    contradictory_payload = canonical_payload(
        schema_version="run-protocol-envelope/v2"
    )
    with pytest.raises(RunProtocolValidationError) as error:
        decode_run_protocol_envelope(
            contradictory_payload,
            expected_epoch=RUN_PROTOCOL_ENVELOPE_EPOCH,
            expected_version=1,
        )
    assert type(error.value) is RunProtocolValidationError
