"""Independent regional identity vectors and closed carrier boundaries."""
from datetime import datetime, timezone
import hashlib
import json

import pytest

from deviation_protocol.domain.run import canonical_run_operation_bytes
from deviation_protocol.domain.world_continuation import WorldVisitV1, derive_world_visit_id
from deviation_protocol.domain.world_revisit import (
    NativeRunRegionalRevisitRequestV1, WorldVisitV2, derive_regional_visit_id,
    RegionalSourceEndingV1, RegionalPoolEntryV1,
)

REQUEST = (b'{"continuous_story_line_id":"line.one","controller_binding":"controller.one",'
    b'"expected_run_state_version":4,"expected_session_state_version":3,"player_id":"player.one",'
    b'"public_operation_key":"revisit.one","run_id":"run.one","schema":"run.revisit-native-region-request/v1",'
    b'"source_reference":"source.one","source_session_id":"session.two"}')
OPERATION = (b'{"controller_binding":"controller.one","public_operation_key":"revisit.one",'
    b'"run_id":"run.one","schema":"run.revisit-native-region-operation/v1"}')
CREATION = (b'{"controller_binding":"controller.one","public_operation_key":"revisit.one",'
    b'"run_id":"run.one","schema":"run.regional-session-create/v1"}')
VISIT = (b'{"continuous_story_line_id":"line.one","joined_state_version":5,"run_id":"run.one",'
    b'"schema":"run.world-visit-id/v2","session_id":"session.three"}')


def test_r04_independent_regional_request_and_identity_vectors():
    request = NativeRunRegionalRevisitRequestV1.model_validate(json.loads(REQUEST), strict=True)
    assert canonical_run_operation_bytes(request) == REQUEST
    assert request.fingerprint() == hashlib.sha256(REQUEST).hexdigest()
    assert request.operation_id().value == hashlib.sha256(OPERATION).hexdigest()
    assert request.creation_request_id() == hashlib.sha256(CREATION).hexdigest()
    assert derive_regional_visit_id(run_id="run.one", continuous_story_line_id="line.one",
        session_id="session.three", joined_state_version=5).value == hashlib.sha256(VISIT).hexdigest()
    changed = json.loads(REQUEST)
    changed["expected_run_state_version"] = 6
    other = NativeRunRegionalRevisitRequestV1(**changed)
    assert other.fingerprint() != request.fingerprint()
    assert other.operation_id() == request.operation_id()


@pytest.mark.parametrize("field,value", [
    ("expected_run_state_version", True), ("expected_run_state_version", 4.0),
    ("expected_run_state_version", "4"), ("expected_run_state_version", 0),
    ("expected_session_state_version", 2**63), ("source_session_id", "x" * 65),
    ("run_id", None), ("destination", "receipt_archive"),
    ("schema", "run.continue-native-request/v1"),
])
def test_r04_request_preserves_original_types_and_closed_fields(field, value):
    obj = json.loads(REQUEST)
    obj[field] = value
    with pytest.raises(ValueError):
        NativeRunRegionalRevisitRequestV1(**obj)


@pytest.mark.parametrize("value", [True, 5.0, "5", 3, 4, 6])
def test_r04_v2_visit_identity_only_accepts_exact_join_five(value):
    with pytest.raises(ValueError):
        derive_regional_visit_id(run_id="run.one", continuous_story_line_id="line.one",
            session_id="session.three", joined_state_version=value)
    with pytest.raises(ValueError):
        derive_world_visit_id(run_id="run.one", continuous_story_line_id="line.one",
            session_id="session.three", joined_state_version=5)


def test_r04_old_visit_parser_does_not_accept_regional_visit():
    time = datetime(2026, 9, 19, tzinfo=timezone.utc)
    values = dict(run_id="run.one", continuous_story_line_id="line.one",
        visit_id=hashlib.sha256(VISIT).hexdigest(), session_id="session.three",
        visit_ordinal=3, world_id="world.undelivered_receipt", world_version=1,
        region_id="region.undelivered_receipt.verification_archive", region_version=1,
        joined_state_version=5, materialized_state_version=5, operation_id="operation.one",
        source_reference="source.one", entered_at=time, created_at=time)
    assert WorldVisitV2(**values).visit_ordinal == 3
    with pytest.raises(ValueError):
        WorldVisitV1(**values)
    for field, value in (("visit_ordinal", 2), ("materialized_state_version", 4),
                         ("region_id", "region.undelivered_receipt.dispatch_hall")):
        with pytest.raises(ValueError):
            WorldVisitV2(**{**values, field: value})


@pytest.mark.parametrize("ending,status", [
    ("dispatch_closed", "FAILED"), ("deadline_reached", "FAILED"),
    ("receipt_held", "FAILED"), ("dispatch_closed", "RESOLVED"),
])
def test_r03_only_the_authored_hold_ending_can_supply_revisit_evidence(ending, status):
    with pytest.raises(ValueError):
        RegionalSourceEndingV1(scenario_id="undelivered_receipt",
            scenario_content_version="undelivered-receipt-1.0.0",
            ending_id="undelivered_receipt.ending." + ending, ending_status=status,
            session_state_version=3, snapshot_sha256="a" * 64)


@pytest.mark.parametrize("field,value", [("weight", 2), ("weight", True),
    ("required_priority", 1), ("cooldown_completed_visits", 1),
    ("scenario_content_version", "receipt-archive-2.0.0")])
def test_r03_pool_has_one_exact_authored_policy(field, value):
    obj = dict(world=dict(world_id="world.undelivered_receipt", world_version=1),
        region=dict(region_id="region.undelivered_receipt.verification_archive", region_version=1),
        scenario_id="receipt_archive", scenario_content_version="receipt-archive-1.0.0",
        content_sha256="a" * 64, required_priority=0, weight=1, cooldown_completed_visits=0)
    assert RegionalPoolEntryV1(**obj).weight == 1
    with pytest.raises(ValueError):
        RegionalPoolEntryV1(**{**obj, field: value})
