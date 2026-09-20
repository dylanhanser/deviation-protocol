"""Independent literal completion identities and strict carrier boundaries."""
import hashlib
import json

import pytest

from deviation_protocol.domain.run import canonical_run_operation_bytes
from deviation_protocol.domain.run_completion import (
    NativeRunCompletionRequestV1, decode_native_run_completion_request,
    CompletionPreservedFactsV1, CanonTransitionV1,
)

REQUEST = (b'{"continuous_story_line_id":"line.one","controller_binding":"controller.one",'
    b'"expected_run_state_version":5,"expected_session_state_version":2,"player_id":"player.one",'
    b'"public_operation_key":"complete.one","run_id":"run.one","schema":"run.complete-revisited-native-request/v1",'
    b'"source_reference":"source.one","source_session_id":"session.three"}')
OPERATION = (b'{"controller_binding":"controller.one","public_operation_key":"complete.one",'
    b'"run_id":"run.one","schema":"run.complete-revisited-native-operation/v1"}')


def test_a03_literal_request_operation_and_completion_identity():
    request = decode_native_run_completion_request(REQUEST)
    assert canonical_run_operation_bytes(request) == REQUEST
    assert request.fingerprint() == hashlib.sha256(REQUEST).hexdigest()
    operation = hashlib.sha256(OPERATION).hexdigest()
    assert request.operation_id().value == operation
    identity = (b'{"continuous_story_line_id":"line.one","operation_id":"' + operation.encode()
                + b'","run_id":"run.one","schema":"run.completion-id/v1"}')
    assert request.completion_id() == hashlib.sha256(identity).hexdigest()
    assert NativeRunCompletionRequestV1(**dict(reversed(list(json.loads(REQUEST).items())))) == request
    for version in (1, 4, 6, 2**63-1):
        changed = NativeRunCompletionRequestV1(**{**json.loads(REQUEST), "expected_run_state_version": version})
        assert changed.operation_id() == request.operation_id()
        assert changed.fingerprint() != request.fingerprint()


@pytest.mark.parametrize("field,value", [
    ("expected_run_state_version", True), ("expected_run_state_version", 5.0),
    ("expected_run_state_version", "5"), ("expected_run_state_version", 0),
    ("expected_session_state_version", -1), ("expected_session_state_version", 2**63),
    ("source_session_id", "x"*65), ("run_id", "x"*129), ("run_id", "中文"),
    ("run_id", None), ("rule_version", "receipt-archive-closure/v1"),
    ("schema", "run.complete-revisited-native-request/v2"),
])
def test_a03_closed_request_carriers(field, value):
    with pytest.raises(ValueError):
        NativeRunCompletionRequestV1(**{**json.loads(REQUEST), field: value})


@pytest.mark.parametrize("payload", [b"\xef\xbb\xbf"+REQUEST, REQUEST+b" ", b"\xff", b"null", b"[]",
    REQUEST.replace(b'"run_id":"run.one"', b'"run_id":"run.one","run_id":"run.one"'),
    REQUEST.replace(b'"schema":', b'"schema_version":'), b" "*16385])
def test_a03_canonical_decoder_rejects_alternate_bytes(payload):
    with pytest.raises(ValueError):
        decode_native_run_completion_request(payload)


@pytest.mark.parametrize("value", [1, "true", 1.0, False, None])
def test_a03_facts_require_actual_true(value):
    with pytest.raises(ValueError):
        CompletionPreservedFactsV1(dispatch_held=value, delivery_unproven=True, unresolved_sealed=True)


def test_a03_transition_cannot_resolve_delivery_or_change_world():
    fields = dict(schema="run.canon-transition/v1", kind="close_unresolved_verification/v1",
        world=dict(world_id="world.undelivered_receipt", world_version=1), from_disposition="open_unresolved",
        to_disposition="closed_unresolved", preserved_facts=dict(dispatch_held=True, delivery_unproven=True, unresolved_sealed=True))
    assert CanonTransitionV1(**fields).to_disposition == "closed_unresolved"
    for field, value in (("to_disposition", "resolved"), ("world", dict(world_id="world.death_certificate", world_version=1)),
                         ("kind", "close_unresolved_verification/v2")):
        with pytest.raises(ValueError):
            CanonTransitionV1(**{**fields, field:value})
