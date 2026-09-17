import asyncio
from dataclasses import replace, fields
import hashlib
import json

import httpx
import pytest

from deviation_protocol.api.main import create_app
from deviation_protocol.api.demo_composition import build_demo_runtime
from deviation_protocol.domain.run import canonical_run_operation_bytes
from deviation_protocol.domain.run_protocol_binding import NativeRunExitRequestV1, NativeRunExitEvidenceV1, decode_native_run_exit_evidence
from tests.unit.test_native_demo import admit
from tests.unit.test_run_exit_api import play_to_ending
from deviation_protocol.infrastructure.run_persistence import StoredRunMutationReceiptRecord, StoredCurrentRunRecord


REQUEST = b'{"continuous_story_line_id":"line.one","controller_binding":"controller.one","expected_run_state_version":3,"expected_session_state_version":19,"player_id":"player.one","public_operation_key":"exit.one","run_id":"run.one","schema":"run.terminate-native-request/v1","session_id":"session.one","source_reference":"source.one"}'
OPERATION = b'{"controller_binding":"controller.one","public_operation_key":"exit.one","run_id":"run.one","schema":"run.terminate-native-operation/v1"}'
EVIDENCE = b'{"ending_id":"ending.one","ending_status":"RESOLVED","request":' + REQUEST + b',"scenario_content_version":"1","scenario_id":"scenario.one","schema":"run.terminate-native-evidence/v1","session_state_version":19,"snapshot_sha256":"' + b'a' * 64 + b'"}'


def test_e03_independent_literal_canonical_goldens():
    request = NativeRunExitRequestV1.model_validate(json.loads(REQUEST))
    assert canonical_run_operation_bytes(request) == REQUEST
    assert hashlib.sha256(OPERATION).hexdigest() == "0379c671e7d598460fafa28f220fa26de928b611b8c206bc3c3998edc3b1879c"
    assert request.operation_id().value == "0379c671e7d598460fafa28f220fa26de928b611b8c206bc3c3998edc3b1879c"
    assert request.fingerprint() == "8119156e4a05e9344461b7dc7dca0da3c52d76fd3df2977e905b1d07489f9369"
    evidence = decode_native_run_exit_evidence(EVIDENCE)
    assert canonical_run_operation_bytes(evidence) == EVIDENCE
    assert hashlib.sha256(canonical_run_operation_bytes(evidence)).hexdigest() == "e64676f5ca7c284464b155a86de5d7802cb6971de27bf388c7d19255fb233571"
    assert evidence.request == request


def test_e03_internal_alias_and_tampered_instances_do_not_expand_canonical_contract():
    from deviation_protocol.domain.run import revalidate_run_model
    payload = json.loads(REQUEST)
    payload["schema_version"] = payload.pop("schema")
    with pytest.raises(ValueError): NativeRunExitRequestV1.model_validate(payload)
    valid = NativeRunExitRequestV1.model_validate(json.loads(REQUEST))
    for changes in ({"expected_run_state_version":"3"},{"extra":"forged"},{"schema_version":"other"}):
        with pytest.raises(ValueError):
            revalidate_run_model(valid.model_copy(update=changes),NativeRunExitRequestV1)


@pytest.mark.parametrize("mutate", [lambda p: b'\xef\xbb\xbf' + p, lambda p: p + b' ',
    lambda p: p.replace(b'"RESOLVED"', b'"ACTIVE"'), lambda p: p.replace(b'"session_state_version":19', b'"session_state_version":true'),
    lambda p: p.replace(b'"schema":"run.terminate-native-evidence/v1"', b'"extra":1,"schema":"run.terminate-native-evidence/v1"'),
    lambda p: p.replace(b'"expected_run_state_version":3', b'"expected_run_state_version":4'),
    lambda p: p.replace(b'"ending_id":"ending.one"', b'"ending_id":"ending.one","ending_id":"ending.one"'),
    lambda p: p.replace(b'a'*64, b'A'*64), lambda p: b' ' * 4097])
def test_e03_evidence_codec_rejects_noncanonical_or_wrong_family(mutate):
    with pytest.raises(ValueError):
        decode_native_run_exit_evidence(mutate(EVIDENCE))


@pytest.mark.parametrize("stage", ["revision", "cas", "receipt", "commit"])
@pytest.mark.parametrize("cancel", [False, True])
async def test_e06_demo_failure_publishes_nothing(monkeypatch, stage, cancel):
    from deviation_protocol.infrastructure.demo_persistence import DemoRunRepository, DemoRunMutationReceiptRepository, DemoUnitOfWork
    runtime = build_demo_runtime()
    app = create_app(services=runtime.services)
    app.state.api_services = runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app, raise_app_exceptions=False), base_url="http://test") as client:
        admitted, _ = await admit(client)
        sid = admitted["session_id"]
        ended, _ = await play_to_ending(client, sid)
        before = runtime.store.snapshot()
        owner, method = {"revision":(DemoRunRepository,"append_revision"), "cas":(DemoRunRepository,"compare_and_swap_current"),
            "receipt":(DemoRunMutationReceiptRepository,"add"), "commit":(DemoUnitOfWork,"commit")}[stage]
        original = getattr(owner, method)
        async def fail(*args, **kwargs):
            if stage != "commit":
                await original(*args, **kwargs)
            raise asyncio.CancelledError() if cancel else RuntimeError("exit fault")
        with monkeypatch.context() as patch:
            patch.setattr(owner, method, fail)
            call = client.post(f"/v1/sessions/{sid}/run-exit", headers={"Idempotency-Key":"exit.fault"},
                json={"expected_run_state_version":3,"expected_session_state_version":ended["metadata"]["state_version"]})
            if cancel:
                with pytest.raises(asyncio.CancelledError): await call
            else:
                assert (await call).status_code == (503 if stage == "commit" else 500)
        assert runtime.store.snapshot() == before
        assert runtime.store.active_uows == 0 and not runtime.store.any_session_lock_held


@pytest.mark.parametrize("field", ["active_player_character_id", "inactivated_at", "operation_id", "binding_operation_id",
    "binding_record_revision", "creation_source_reference", "receipt", "snapshot", "protocol", "world", "missing_revision", "missing_receipt"]
    + ["receipt." + f.name for f in fields(StoredRunMutationReceiptRecord)]
    + ["current." + f.name for f in fields(StoredCurrentRunRecord)]
    + ["evidence." + name for name in ("ending_id","ending_status","session_state_version","snapshot_sha256","scenario_id","scenario_content_version")])
async def test_e03_terminal_corruption_rejected_without_writes(field):
    from deviation_protocol.domain.run import RunOperationId, RunAuthoritySourceRef
    runtime = build_demo_runtime()
    app = create_app(services=runtime.services)
    app.state.api_services = runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app, raise_app_exceptions=False), base_url="http://test") as client:
        admitted, _ = await admit(client, "difficulty.silent-hunting-ground")
        sid, rid = admitted["session_id"], admitted["run_context"]["run_id"]
        ended, _ = await play_to_ending(client, sid)
        response = await client.post(f"/v1/sessions/{sid}/run-exit", headers={"Idempotency-Key":"exit.corrupt"},
            json={"expected_run_state_version":3,"expected_session_state_version":ended["metadata"]["state_version"]})
        assert response.status_code == 200, response.text
        store = runtime.store
        current = store._run_current[rid]
        changes = {"active_player_character_id":current.binding_player_character_id, "inactivated_at":None,
            "operation_id":RunOperationId(value="other"), "binding_operation_id":"other", "binding_record_revision":99,
            "creation_source_reference":RunAuthoritySourceRef(value="other")}
        if field in changes: store._run_current[rid] = replace(current, **{field:changes[field]})
        elif field == "missing_revision": del store._run_revisions[(rid, 4)]
        elif field == "missing_receipt":
            key = next(k for k,v in store._run_mutation_receipts.items() if v.resulting_state_version == 4)
            del store._run_mutation_receipts[key]
        elif field == "receipt":
            key = next(k for k,v in store._run_mutation_receipts.items() if v.resulting_state_version == 4)
            value = store._run_mutation_receipts[key]
            store._run_mutation_receipts[key] = replace(value, operation_evidence_canonical=value.operation_evidence_canonical.replace(b'"snapshot_sha256":"', b'"snapshot_sha256":"0'))
        elif field == "snapshot": del store._snapshots[sid]
        elif field == "protocol": store._run_protocol_bindings.clear()
        elif field == "world": store._run_entry_world_bindings.clear()
        elif field.startswith("current."):
            name = field.split(".")[1]
            store._run_current[rid] = replace(current, **{name:"unexpected" if getattr(current,name) is None else None})
        elif field.startswith(("receipt.","evidence.")):
            key = next(k for k,v in store._run_mutation_receipts.items() if v.resulting_state_version == 4)
            value = store._run_mutation_receipts[key]
            name = field.split(".")[1]
            if field.startswith("receipt."):
                changed = "unexpected" if getattr(value,name) is None else None
                store._run_mutation_receipts[key] = replace(value, **{name:changed})
            else:
                data = json.loads(value.operation_evidence_canonical)
                data[name] = {"ending_id":"other.ending","ending_status":"RESOLVED","session_state_version":999,
                    "snapshot_sha256":"a"*64,"scenario_id":"other.scenario","scenario_content_version":"other.version"}[name]
                store._run_mutation_receipts[key] = replace(value,operation_evidence_canonical=json.dumps(data,sort_keys=True,separators=(",",":")).encode())
        corrupted = store.snapshot()
        for path in ("run-status", "view"):
            response = await client.get(f"/v1/sessions/{sid}/{path}")
            assert response.status_code == 409 and response.json()["error"]["error_code"] == "SNAPSHOT_INVALID", response.text
        assert store.snapshot() == corrupted
