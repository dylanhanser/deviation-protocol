"""No-I/O storage carrier boundary for Run Protocol envelope v1."""

from __future__ import annotations

from dataclasses import dataclass as _dataclass

from deviation_protocol.domain.run_protocol import (
    RUN_PROTOCOL_ENVELOPE_EPOCH as _RUN_PROTOCOL_ENVELOPE_EPOCH,
    RUN_PROTOCOL_ENVELOPE_V1_RECORD_VERSION as _RUN_PROTOCOL_ENVELOPE_V1_RECORD_VERSION,
    RUN_PROTOCOL_ENVELOPE_V1_SCHEMA as _RUN_PROTOCOL_ENVELOPE_V1_SCHEMA,
    RunProtocolEnvelopeV1 as _RunProtocolEnvelopeV1,
    RunProtocolValidationError as _RunProtocolValidationError,
    UnsupportedRunProtocolVersionError as _UnsupportedRunProtocolVersionError,
    decode_run_protocol_envelope as _decode_run_protocol_envelope,
    encode_run_protocol_envelope_v1 as _encode_run_protocol_envelope_v1,
)


class RunProtocolStoredRecordIntegrityError(ValueError):
    """Stored Run Protocol evidence is malformed or contradictory."""


@_dataclass(frozen=True, slots=True)
class StoredRunProtocolEnvelopeRecordV1:
    schema_epoch: str
    record_version: int
    canonical_payload: bytes


def run_protocol_envelope_to_storage(
    value: _RunProtocolEnvelopeV1,
) -> StoredRunProtocolEnvelopeRecordV1:
    """Construct an in-memory stored carrier without performing persistence."""

    try:
        canonical_payload = _encode_run_protocol_envelope_v1(value)
    except (TypeError, _RunProtocolValidationError) as exc:
        raise RunProtocolStoredRecordIntegrityError(
            "Run Protocol envelope cannot be converted to storage"
        ) from exc
    return StoredRunProtocolEnvelopeRecordV1(
        schema_epoch=_RUN_PROTOCOL_ENVELOPE_EPOCH,
        record_version=_RUN_PROTOCOL_ENVELOPE_V1_RECORD_VERSION,
        canonical_payload=canonical_payload,
    )


def run_protocol_envelope_from_storage(
    stored: StoredRunProtocolEnvelopeRecordV1,
) -> _RunProtocolEnvelopeV1:
    """Reconstruct one detached envelope from a complete untrusted record."""

    try:
        if type(stored) is not StoredRunProtocolEnvelopeRecordV1:
            raise TypeError("expected StoredRunProtocolEnvelopeRecordV1")
        if type(stored.schema_epoch) is not str:
            raise TypeError("stored schema_epoch must be an exact string")
        if type(stored.record_version) is not int:
            raise TypeError("stored record_version must be a non-Boolean integer")
        if type(stored.canonical_payload) is not bytes:
            raise TypeError("stored canonical_payload must be exact immutable bytes")
        envelope = _decode_run_protocol_envelope(
            stored.canonical_payload,
            expected_epoch=stored.schema_epoch,
            expected_version=stored.record_version,
        )
        if (
            stored.schema_epoch != _RUN_PROTOCOL_ENVELOPE_EPOCH
            or stored.record_version
            != _RUN_PROTOCOL_ENVELOPE_V1_RECORD_VERSION
            or envelope.schema_version != _RUN_PROTOCOL_ENVELOPE_V1_SCHEMA
        ):
            raise _RunProtocolValidationError(
                "stored record and payload versions are contradictory"
            )
        return envelope
    except (
        AttributeError,
        TypeError,
        _RunProtocolValidationError,
        _UnsupportedRunProtocolVersionError,
    ) as exc:
        raise RunProtocolStoredRecordIntegrityError(
            "stored Run Protocol envelope record is invalid"
        ) from exc
