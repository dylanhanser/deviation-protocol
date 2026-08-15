from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, replace
import inspect
from pathlib import Path

from pydantic import ValidationError
import pytest

import deviation_protocol.infrastructure.run_protocol_persistence as persistence_module
from deviation_protocol.domain.run_protocol import (
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
    encode_run_protocol_envelope_v1,
)
from deviation_protocol.infrastructure.run_protocol_persistence import (
    RunProtocolStoredRecordIntegrityError,
    StoredRunProtocolEnvelopeRecordV1,
    run_protocol_envelope_from_storage,
    run_protocol_envelope_to_storage,
)


GOLDEN = (
    b'{"profile_ref":{"profile_id":"profile.example","profile_version":1},'
    b'"reality_boundary":"lawful","relationship_overlay":"off",'
    b'"schema_version":"run-protocol-envelope/v1",'
    b'"world_tone":"balanced"}'
)


def envelope() -> RunProtocolEnvelopeV1:
    return RunProtocolEnvelopeV1(
        schema_version=RUN_PROTOCOL_ENVELOPE_V1_SCHEMA,
        profile_ref=RunProtocolProfileRefV1(
            profile_id=RunProtocolProfileId(value="profile.example"),
            profile_version=RunProtocolProfileVersion(value=1),
        ),
        world_tone=RunProtocolWorldTone.BALANCED,
        reality_boundary=RunProtocolRealityBoundary.LAWFUL,
        relationship_overlay=RunProtocolRelationshipOverlay.OFF,
    )


def record() -> StoredRunProtocolEnvelopeRecordV1:
    return StoredRunProtocolEnvelopeRecordV1(
        schema_epoch=RUN_PROTOCOL_ENVELOPE_EPOCH,
        record_version=RUN_PROTOCOL_ENVELOPE_V1_RECORD_VERSION,
        canonical_payload=GOLDEN,
    )


def test_exact_infrastructure_symbol_and_signature_contract() -> None:
    public_names = {
        name
        for name in vars(persistence_module)
        if not name.startswith("_") and name != "annotations"
    }
    assert public_names == {
        "RunProtocolStoredRecordIntegrityError",
        "StoredRunProtocolEnvelopeRecordV1",
        "run_protocol_envelope_to_storage",
        "run_protocol_envelope_from_storage",
    }
    assert issubclass(RunProtocolStoredRecordIntegrityError, ValueError)
    assert not issubclass(
        RunProtocolStoredRecordIntegrityError,
        RunProtocolValidationError,
    )
    assert tuple(inspect.signature(StoredRunProtocolEnvelopeRecordV1).parameters) == (
        "schema_epoch",
        "record_version",
        "canonical_payload",
    )
    assert not inspect.iscoroutinefunction(run_protocol_envelope_to_storage)
    assert not inspect.iscoroutinefunction(run_protocol_envelope_from_storage)


def test_stored_carrier_is_frozen_slotted_and_deliberately_unvalidated() -> None:
    stored = StoredRunProtocolEnvelopeRecordV1(
        schema_epoch=object(),  # type: ignore[arg-type]
        record_version=True,
        canonical_payload=bytearray(GOLDEN),  # type: ignore[arg-type]
    )
    assert not hasattr(stored, "__dict__")
    assert type(stored.schema_epoch) is object
    assert stored.record_version is True
    assert type(stored.canonical_payload) is bytearray
    with pytest.raises(FrozenInstanceError):
        stored.record_version = 1  # type: ignore[misc]
    with pytest.raises(TypeError):
        StoredRunProtocolEnvelopeRecordV1()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        StoredRunProtocolEnvelopeRecordV1(
            schema_epoch="x",
            record_version=1,
            canonical_payload=b"x",
            unknown="x",  # type: ignore[call-arg]
        )


def test_storage_conversion_writes_only_exact_v1_discriminators_and_payload() -> None:
    value = envelope()
    before = value.model_dump(mode="python")
    first = run_protocol_envelope_to_storage(value)
    second = run_protocol_envelope_to_storage(value)

    assert first == second == record()
    assert first.schema_epoch == "run-protocol-envelope"
    assert type(first.record_version) is int
    assert first.record_version == 1
    assert first.canonical_payload == GOLDEN
    assert first.canonical_payload == encode_run_protocol_envelope_v1(value)
    assert value.model_dump(mode="python") == before


def test_storage_reconstruction_returns_detached_revalidated_domain_state() -> None:
    original = envelope()
    stored = run_protocol_envelope_to_storage(original)
    reconstructed = run_protocol_envelope_from_storage(stored)

    assert reconstructed == original
    assert reconstructed is not original
    assert reconstructed.profile_ref is not original.profile_ref
    assert reconstructed.profile_ref.profile_id is not original.profile_ref.profile_id
    assert run_protocol_envelope_to_storage(reconstructed) == stored


@pytest.mark.parametrize(
    "invalid",
    (
        object(),
        None,
        {"schema_epoch": "run-protocol-envelope"},
    ),
)
def test_wrong_complete_record_type_is_stored_integrity_failure(
    invalid: object,
) -> None:
    with pytest.raises(RunProtocolStoredRecordIntegrityError) as error:
        run_protocol_envelope_from_storage(invalid)  # type: ignore[arg-type]
    assert isinstance(error.value.__cause__, TypeError)


@pytest.mark.parametrize(
    "invalid",
    (
        replace(record(), schema_epoch=1),
        replace(record(), schema_epoch=None),
        replace(record(), record_version=True),
        replace(record(), record_version=1.0),
        replace(record(), record_version="1"),
        replace(record(), canonical_payload=bytearray(GOLDEN)),
        replace(record(), canonical_payload=memoryview(GOLDEN)),
        replace(record(), canonical_payload=GOLDEN.decode()),
    ),
)
def test_stored_field_types_are_exact_and_boolean_is_not_an_integer(
    invalid: StoredRunProtocolEnvelopeRecordV1,
) -> None:
    with pytest.raises(RunProtocolStoredRecordIntegrityError) as error:
        run_protocol_envelope_from_storage(invalid)
    assert isinstance(error.value.__cause__, TypeError)


@pytest.mark.parametrize(
    ("epoch", "version"),
    (
        ("run-protocol-envelope", 0),
        ("run-protocol-envelope", 2),
        ("run-protocol-envelope/v1", 1),
        ("future", -1),
    ),
)
def test_unsupported_trusted_record_versions_are_distinct_caused_failures(
    epoch: str,
    version: int,
) -> None:
    with pytest.raises(RunProtocolStoredRecordIntegrityError) as error:
        run_protocol_envelope_from_storage(
            replace(record(), schema_epoch=epoch, record_version=version)
        )
    assert type(error.value.__cause__) is UnsupportedRunProtocolVersionError


@pytest.mark.parametrize(
    "payload",
    (
        b"",
        b"not-json",
        b"\xff",
        b"\xef\xbb\xbf" + GOLDEN,
        b" " + GOLDEN,
        GOLDEN + b" ",
        GOLDEN.replace(
            b'"profile_version":1',
            b'"profile_version":1,"profile_version":2',
        ),
        GOLDEN.replace(
            b'"profile_ref":{"profile_id":"profile.example","profile_version":1}',
            b'"profile_ref":{"profile_version":1,"profile_id":"profile.example"}',
        ),
        GOLDEN + b"x" * (1_025 - len(GOLDEN)),
    ),
)
def test_malformed_or_noncanonical_payload_is_stored_corruption(
    payload: bytes,
) -> None:
    with pytest.raises(RunProtocolStoredRecordIntegrityError) as error:
        run_protocol_envelope_from_storage(
            replace(record(), canonical_payload=payload)
        )
    assert isinstance(error.value.__cause__, RunProtocolValidationError)
    assert not isinstance(
        error.value.__cause__, UnsupportedRunProtocolVersionError
    )


def test_payload_version_contradiction_never_upgrades_downgrades_or_falls_back() -> None:
    contradictory = GOLDEN.replace(
        b"run-protocol-envelope/v1",
        b"run-protocol-envelope/v2",
    )
    with pytest.raises(RunProtocolStoredRecordIntegrityError) as error:
        run_protocol_envelope_from_storage(
            replace(record(), canonical_payload=contradictory)
        )
    assert type(error.value.__cause__) is RunProtocolValidationError

    with pytest.raises(RunProtocolStoredRecordIntegrityError) as unsupported:
        run_protocol_envelope_from_storage(
            replace(
                record(),
                record_version=2,
                canonical_payload=contradictory,
            )
        )
    assert type(unsupported.value.__cause__) is (
        UnsupportedRunProtocolVersionError
    )


@pytest.mark.parametrize(
    "corruption",
    (
        "unknown",
        "missing",
        "fields-set",
        "nested",
    ),
)
def test_domain_conversion_failure_is_translated_with_exact_cause(
    corruption: str,
) -> None:
    value = envelope()
    if corruption == "unknown":
        value.__dict__["hidden"] = "x"
    elif corruption == "missing":
        value.__dict__.pop("world_tone")
    elif corruption == "fields-set":
        value.__pydantic_fields_set__.remove("world_tone")
    else:
        value.profile_ref.profile_id.__dict__["hidden"] = "x"

    with pytest.raises(RunProtocolStoredRecordIntegrityError) as error:
        run_protocol_envelope_to_storage(value)
    assert type(error.value.__cause__) is RunProtocolValidationError


def test_wrong_domain_type_is_integrity_failure_and_direct_model_error_stays_distinct() -> None:
    with pytest.raises(RunProtocolStoredRecordIntegrityError) as error:
        run_protocol_envelope_to_storage(object())  # type: ignore[arg-type]
    assert isinstance(error.value.__cause__, TypeError)

    with pytest.raises(ValidationError):
        RunProtocolProfileVersion(value=True)
    with pytest.raises(RunProtocolValidationError):
        encode_run_protocol_envelope_v1(
            envelope().model_copy(update={"world_tone": "balanced"})
        )


def test_module_has_no_io_database_transaction_repository_or_runtime_dependency() -> None:
    source_path = Path(persistence_module.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(
                alias.name.split(".", 1)[0] for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_roots.add(node.module.split(".", 1)[0])
    assert imported_roots <= {
        "__future__",
        "dataclasses",
        "deviation_protocol",
    }
    forbidden_names = {
        "open",
        "connect",
        "commit",
        "rollback",
        "flush",
        "execute",
        "query",
        "add",
        "write",
        "read",
    }
    called_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert not (called_names & forbidden_names)
