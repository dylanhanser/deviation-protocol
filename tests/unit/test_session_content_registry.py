from pathlib import Path
from types import SimpleNamespace
import hashlib
import pytest

from deviation_protocol.application.session_content_registry import SessionContentBundle,SessionContentRegistry

ROOT=Path(__file__).parents[2]/"config/scenarios"


def test_exact_preloaded_bundles_never_merge_or_fallback(monkeypatch):
    old=(ROOT/"death_certificate_v1.json").read_bytes()
    new=(ROOT/"undelivered_receipt_v1.json").read_bytes()
    a,b=SessionContentBundle.from_bytes(old),SessionContentBundle.from_bytes(new)
    c=SessionContentBundle.from_bytes((ROOT/"receipt_archive_v1.json").read_bytes())
    registry=SessionContentRegistry((a,b,c))
    assert SessionContentRegistry((c,b,a)).continuation_pool()==registry.continuation_pool()
    assert a.content_sha256==hashlib.sha256(old).hexdigest()
    assert b.content_sha256==hashlib.sha256(new).hexdigest()
    monkeypatch.setattr(Path,"read_bytes",lambda *args:pytest.fail("lookup performed filesystem access"))
    for bundle in (a,b,c):
        assert registry.for_session(SimpleNamespace(scenario_id=bundle.scenario_id,scenario_version=bundle.content_version)) is bundle
        assert len(bundle.scenario_catalog.scenarios)==1
    for identity in ((a.scenario_id,b.content_version),(b.scenario_id,a.content_version),(b.scenario_id,"undelivered-receipt-1.0.1")):
        with pytest.raises(ValueError):registry.resolve(*identity)
    with pytest.raises(ValueError):SessionContentRegistry((a,a))
    with pytest.raises(ValueError,match="required destination content missing"):SessionContentRegistry((a,))
    with pytest.raises(ValueError):SessionContentBundle.from_bytes(b'{"content_version":"a","content_version":"b"}')
    assert [item.world_id for item in registry.continuation_pool()]==["world.undelivered_receipt"]


def test_independent_approved_pack_pin_and_declared_values():
    import json
    import subprocess
    from deviation_protocol.application.session_content_registry import DESTINATION_CONTENT_SHA256
    raw=(ROOT/"undelivered_receipt_v1.json").read_bytes()
    assert raw.count(b'\r\n')==raw.count(b'\n')
    assert hashlib.sha256(raw).hexdigest()==DESTINATION_CONTENT_SHA256=="74af55faf2eca0dd826be1f025272d070c23a2000383183e886ec823f495582c"
    path="config/scenarios/undelivered_receipt_v1.json"
    # The independently pinned deployment bytes must survive Git's clean filter.
    assert subprocess.check_output(["git","hash-object","--no-filters",path],cwd=ROOT.parents[1])==subprocess.check_output(
        ["git","hash-object",f"--path={path}",path],cwd=ROOT.parents[1])
    bundle=SessionContentBundle.from_bytes(raw)
    assert SessionContentRegistry((bundle,SessionContentBundle.from_bytes((ROOT/"receipt_archive_v1.json").read_bytes()))).continuation_pool()[0].content_sha256==DESTINATION_CONTENT_SHA256
    definition=json.loads(raw)["scenarios"][0]
    assert definition["threat_clocks"][0]["maximum"]==40
    assert [(e["ending_id"],e["priority"]) for e in definition["endings"]]==[
        ("undelivered_receipt.ending.deadline_reached",10),("undelivered_receipt.ending.receipt_held",20),
        ("undelivered_receipt.ending.dispatch_closed",30)]


@pytest.mark.parametrize("mutation",["ceiling","version","scenario","whitespace","crlf","digest","services"])
def test_required_destination_configuration_rejects_substitution(mutation):
    import json
    from dataclasses import replace
    raw=(ROOT/"undelivered_receipt_v1.json").read_bytes()
    bundle=SessionContentBundle.from_bytes(raw)
    with pytest.raises(ValueError):
        if mutation=="digest":replace(bundle,content_sha256="0"*64)
        elif mutation=="services":replace(bundle,session_service=SimpleNamespace(catalog=None,scenario_catalog=None))
        else:
            changed=json.loads(raw)
            if mutation=="ceiling":changed["scenarios"][0]["threat_clocks"][0]["maximum"]=41
            if mutation=="version":
                changed["content_version"]=changed["content_catalog"]["content_version"]=changed["scenarios"][0]["content_version"]="undelivered-receipt-1.0.1"
            if mutation=="scenario":changed["scenarios"][0]["scenario_id"]="substituted"
            payload=raw+b" " if mutation=="whitespace" else raw.replace(b"\r\n",b"\n") if mutation=="crlf" else json.dumps(changed,ensure_ascii=False).encode()
            SessionContentRegistry((SessionContentBundle.from_bytes(payload),))
