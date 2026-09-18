"""Independent operation vectors and closed continuation authority boundaries."""
from copy import deepcopy
import hashlib
import json

import pytest

from deviation_protocol.domain.run import canonical_run_operation_bytes, revalidate_run_model
from deviation_protocol.domain.world_continuation import (
    WorldId, RegionId, WorldVisitId, WorldVersion, RegionVersion,
    NativeRunContinuationRequestV1, ContinuationPoolEntryV1,
    ContinuationSelectionInputsV1, SOURCE_WORLD, derive_world_visit_id,
    snapshot_canonical_bytes,
)


REQUEST = (b'{"continuous_story_line_id":"line.one","controller_binding":"controller.one",'
    b'"expected_run_state_version":3,"expected_session_state_version":19,"player_id":"player.one",'
    b'"public_operation_key":"continue.one","run_id":"run.one","schema":"run.continue-native-request/v1",'
    b'"source_reference":"source.one","source_session_id":"session.one"}')
OPERATION = (b'{"controller_binding":"controller.one","public_operation_key":"continue.one",'
             b'"run_id":"run.one","schema":"run.continue-native-operation/v1"}')
CREATION = (b'{"controller_binding":"controller.one","public_operation_key":"continue.one",'
            b'"run_id":"run.one","schema":"run.continuation-session-create/v1"}')
VISIT = (b'{"continuous_story_line_id":"line.one","joined_state_version":4,"run_id":"run.one",'
         b'"schema":"run.world-visit-id/v1","session_id":"session.two"}')


def request():
    return NativeRunContinuationRequestV1.model_validate(json.loads(REQUEST), strict=True)


def pool_entry():
    return ContinuationPoolEntryV1(world_id="world.undelivered_receipt", world_version=1,
        region_id="region.undelivered_receipt.dispatch_hall", region_version=1,
        scenario_id="undelivered_receipt", scenario_content_version="undelivered-receipt-1.0.0",
        content_sha256="a" * 64, required_priority=0, weight=1)


def selection():
    return ContinuationSelectionInputsV1(selector_version="same-line-continuation/v1",
        run_id="run.one", continuous_story_line_id="line.one", source_session_id="session.one",
        source_session_state_version=19, source_snapshot_sha256="b" * 64,
        source_world=SOURCE_WORLD, source_ending_id="death_certificate.ending.protocol_broken",
        source_ending_status="RESOLVED", resolution_fingerprint="c" * 64,
        visited_worlds=(SOURCE_WORLD,), eligible_pool=(pool_entry(),))


def test_c10_independent_request_operation_creation_and_visit_bytes():
    value = request()
    assert canonical_run_operation_bytes(value) == REQUEST
    assert value.operation_id().value == hashlib.sha256(OPERATION).hexdigest()
    assert value.creation_request_id() == hashlib.sha256(CREATION).hexdigest()
    assert value.fingerprint() == hashlib.sha256(REQUEST).hexdigest()
    assert derive_world_visit_id(run_id="run.one", continuous_story_line_id="line.one",
        session_id="session.two", joined_state_version=4).value == hashlib.sha256(VISIT).hexdigest()
    permuted = dict(reversed(list(json.loads(REQUEST).items())))
    assert canonical_run_operation_bytes(NativeRunContinuationRequestV1(**permuted)) == REQUEST


@pytest.mark.parametrize("field,value", [
    ("expected_run_state_version", True), ("expected_run_state_version", 3.0),
    ("expected_run_state_version", "3"), ("expected_session_state_version", -1),
    ("source_session_id", "x" * 65), ("source_session_id", "无效"),
    ("schema", "run.continue-native-request/v2"), ("run_id", None),
    ("expected_session_state_version", 2**63), ("destination", "world.arbitrary"),
])
def test_c10_request_rejects_noncanonical_original_scalars(field, value):
    obj = json.loads(REQUEST)
    obj[field] = value
    with pytest.raises((TypeError, ValueError)):
        NativeRunContinuationRequestV1.model_validate(obj, strict=True)


@pytest.mark.parametrize("slot", ["extra", "private", "scalar", "fields"])
def test_c04_request_rejects_mutated_actual_model_state(slot):
    value = request()
    if slot == "extra": value.__dict__["destination"] = "world.arbitrary"
    elif slot == "private": object.__setattr__(value, "__pydantic_private__", {"authority": True})
    elif slot == "scalar": value.__dict__["expected_run_state_version"] = True
    else: object.__setattr__(value, "__pydantic_fields_set__", {"unknown"})
    with pytest.raises((TypeError, ValueError)):
        value.fingerprint()


@pytest.mark.parametrize("carrier", [WorldId, RegionId, WorldVisitId])
@pytest.mark.parametrize("value", [None, True, "", "a b", "中文", "x" * 129])
def test_c10_identity_domains_reject_invalid_scalars(carrier, value):
    with pytest.raises((TypeError, ValueError)):
        carrier(value=value)


@pytest.mark.parametrize("carrier", [WorldVersion, RegionVersion])
@pytest.mark.parametrize("value", [None, True, 1.0, "1", 0, -1, 2**63])
def test_c10_version_domains_are_positive_exact_int64(carrier, value):
    with pytest.raises((TypeError, ValueError)):
        carrier(value=value)


def test_c10_snapshot_encoding_preserves_decomposed_unicode():
    value = {"fact": "e\u0301", "number": 1}
    literal = b'{"fact":"e\xcc\x81","number":1}'
    assert snapshot_canonical_bytes(value) == literal
    assert canonical_run_operation_bytes(value) != literal
    assert snapshot_canonical_bytes(dict(reversed(list(value.items())))) == literal


@pytest.mark.parametrize("changes", [
    {"weight": 0}, {"weight": True}, {"weight": 1.0}, {"weight": 2},
    {"required_priority": 1}, {"world_id": "world.third"},
    {"world_version": 2}, {"region_id": "region.crossed"},
    {"scenario_content_version": "death-certificate-1.1.0"},
])
def test_c10_single_required_edge_is_closed(changes):
    obj = pool_entry().model_dump()
    obj.update(changes)
    with pytest.raises(ValueError):
        ContinuationPoolEntryV1(**obj)


def test_c10_seed_has_only_the_frozen_reproducibility_inputs():
    value = selection()
    expected = {"selector_version": "same-line-continuation/v1", "run_id": "run.one",
        "continuous_story_line_id": "line.one", "source_session_id": "session.one",
        "source_session_state_version": 19, "source_snapshot_sha256": "b" * 64,
        "source_world": {"world_id": "world.death_certificate", "world_version": 1},
        "source_ending_id": "death_certificate.ending.protocol_broken", "source_ending_status": "RESOLVED",
        "resolution_fingerprint": "c" * 64,
        "visited_worlds": [{"world_id": "world.death_certificate", "world_version": 1}],
        "eligible_pool": [{"world_id": "world.undelivered_receipt", "world_version": 1,
            "region_id": "region.undelivered_receipt.dispatch_hall", "region_version": 1,
            "scenario_id": "undelivered_receipt", "scenario_content_version": "undelivered-receipt-1.0.0",
            "content_sha256": "a" * 64, "required_priority": 0, "weight": 1}]}
    literal = json.dumps(expected, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    assert canonical_run_operation_bytes(value) == literal
    assert value.seed() == hashlib.sha256(b"deviation-protocol:world-continuation-selection:v1\0" + literal).hexdigest()
    with pytest.raises(ValueError):
        revalidate_run_model(value.model_copy(update={"eligible_pool": (pool_entry(), pool_entry())}), type(value))
    with pytest.raises(ValueError):
        revalidate_run_model(value.model_copy(update={"source_ending_status": "FAILED"}), type(value))
    assert selection().seed() == value.seed()
    empty=value.model_copy(update={"eligible_pool":()})
    assert revalidate_run_model(empty,type(value)).eligible_pool==()
    from deviation_protocol.domain.world_continuation import DESTINATION_WORLD
    for visited in ((),(SOURCE_WORLD,DESTINATION_WORLD),(DESTINATION_WORLD,)):
        with pytest.raises(ValueError):
            revalidate_run_model(value.model_copy(update={"visited_worlds":visited}),type(value))


def test_c10_independent_complete_root_and_receipt_vectors():
    from deviation_protocol.domain.world_continuation import WorldStateRootV1,decode_world_state_root,NativeRunContinuationEvidenceV1,decode_native_run_continuation_evidence
    encode=lambda obj:json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    snapshot={"schema_version":3,"content_version":"undelivered-receipt-1.0.0",
        "player":{"player_id":"player.one","character_definition_id":"character.one","attributes":{},"resources":{},
            "inventory":{"items":{}},"wallet":{"balances":{}},"skills":{}},"npcs":{},"scenario_runtime":None,
        "player_memory":{"memory_model_version":2,"sync_status":"CURRENT","last_applied_source_sequence_no":0,
            "last_applied_source_event_id":None,"first_deferred_source_sequence_no":None,"last_deferred_source_sequence_no":None,
            "deferred_event_count":0,"scenario_records":[],"npc_records":[],"significant_experiences":[],"known_public_facts":[]}}
    obj={"schema":"run-world-state/v1","run_id":"run.one","continuous_story_line_id":"line.one",
        "world":{"world_id":"world.undelivered_receipt","world_version":1},
        "region":{"region_id":"region.undelivered_receipt.dispatch_hall","region_version":1},
        "first_visit_id":hashlib.sha256(VISIT).hexdigest(),"session_id":"session.two","scenario_id":"undelivered_receipt",
        "scenario_content_version":"undelivered-receipt-1.0.0","content_sha256":"a"*64,"basis":"session_initialization",
        "snapshot_state_version":0,"snapshot":snapshot,"snapshot_sha256":hashlib.sha256(encode(snapshot)).hexdigest()}
    literal=encode(obj)
    root=decode_world_state_root(literal)
    assert root.canonical_bytes()==literal and root.digest()==hashlib.sha256(literal).hexdigest()
    assert WorldStateRootV1.model_validate(dict(reversed(list(obj.items())))).canonical_bytes()==literal
    incomplete=deepcopy(obj);incomplete["snapshot"].pop("npcs")
    incomplete["snapshot_sha256"]=hashlib.sha256(encode(incomplete["snapshot"])).hexdigest()
    with pytest.raises(ValueError):decode_world_state_root(encode(incomplete))
    source_visit=hashlib.sha256(VISIT.replace(b'"joined_state_version":4',b'"joined_state_version":3').replace(b'session.two',b'session.one')).hexdigest()
    inputs=json.loads(canonical_run_operation_bytes(selection()))
    evidence={"schema":"run.continue-native-evidence/v1","request":json.loads(REQUEST),
        "source_ending":{"scenario_id":"death_certificate","scenario_content_version":"death-certificate-1.1.0",
            "ending_id":"death_certificate.ending.protocol_broken","ending_status":"RESOLVED","session_state_version":19,"snapshot_sha256":"b"*64},
        "selection_inputs":inputs,"selection_seed":hashlib.sha256(b"deviation-protocol:world-continuation-selection:v1\0"+encode(inputs)).hexdigest(),
        "source_visit_id":source_visit,"destination_visit_id":hashlib.sha256(VISIT).hexdigest(),"destination_session_id":"session.two",
        "destination_creation_request_id":hashlib.sha256(CREATION).hexdigest(),"destination_initial_event_id":"event.two","destination_random_seed":42,
        "source_world_state_sha256":"d"*64,"destination_world_state_sha256":hashlib.sha256(literal).hexdigest(),
        "carryover_rule":"carry-player-state/v1","entry_variant":"resolved","occurred_at":"2026-09-18T00:00:00.000000Z"}
    receipt=encode(evidence)
    assert canonical_run_operation_bytes(decode_native_run_continuation_evidence(receipt))==receipt
    for field,value in (("destination_random_seed",True),("schema","run.continue-native-evidence/v2"),("occurred_at","2026-09-18T00:00:00.000001Z")):
        with pytest.raises(ValueError):decode_native_run_continuation_evidence(encode({**evidence,field:value}))
