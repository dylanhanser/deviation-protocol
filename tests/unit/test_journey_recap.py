"""D1 projection + real deterministic Demo HTTP reads, no database/Provider."""
from dataclasses import replace

import httpx
import pytest

from deviation_protocol.api.demo_composition import build_demo_runtime
from deviation_protocol.api.main import create_app
from deviation_protocol.api.journey_recap_schema import JourneyRecapResponse
from deviation_protocol.application.journey_recap import (
    CONTENT_COPY, RecapSource, render_sources, select_text,
)
from deviation_protocol.domain.scenario_runtime import ScenarioRuntimeState
from tests.unit.test_run_completion_api import reach_archive
from tests.unit.test_native_demo import admit
from tests.unit.test_run_exit_api import play_to_ending
from tests.unit.test_run_revisit_api import action, view


@pytest.mark.parametrize("length", [1999, 2000, 2001])
def test_code_point_required_boundary(length):
    # Astral characters occupy two UTF-16 units, one Python/Unicode code point.
    status, text = select_text(["😀" * length], [])
    assert (status, len(text)) == (("complete", length) if length <= 2000 else ("unavailable_overflow", 0))


def test_optional_selection_counts_separators_and_is_stable():
    assert select_text(["a" * 1997], ["b", "c"]) == ("incomplete", "a" * 1997 + "\n\nb")
    assert select_text(["required"], [], optional_missing=True) == ("incomplete", "required")
    assert select_text(["a" * 2001], ["short"]) == ("unavailable_overflow", "")


def source_from_bundle(bundle):
    definition = bundle.scenario_catalog.scenarios[0]
    runtime = ScenarioRuntimeState.from_definition(definition)
    return RecapSource(1, "test-session", 0,
        (bundle.scenario_id, bundle.content_version, bundle.content_sha256), "0" * 64, definition, runtime)


def test_exact_content_missing_optional_and_required(monkeypatch):
    runtime = build_demo_runtime()
    registry = runtime.services.run_revisit_service.registry
    source = source_from_bundle(registry.resolve("receipt_archive", "receipt-archive-1.0.0"))
    status, text = render_sources((source,), "active")
    assert status == "complete" and "送达仍未得到证明" in text
    assert "未解决的待核记录已封存" not in text
    # Version-pinned presentation, never whatever version happens to be latest.
    old_definition = source.definition.model_copy(update={"content_version": "archive-old"})
    old = replace(source, content_identity=("receipt_archive", "archive-old", "1" * 64),
                  definition=old_definition, runtime=ScenarioRuntimeState.from_definition(old_definition))
    with pytest.raises(ValueError): render_sources((old,), "active")
    monkeypatch.setitem(CONTENT_COPY, old.content_identity, CONTENT_COPY[source.content_identity])
    assert render_sources((old,), "active") == (status, text)
    public = source.definition.public_client
    # Synthetic projection-source failures after the source boundary.
    missing_scene = source.definition.model_copy(update={"public_client": public.model_copy(update={"scenes": ()})})
    assert render_sources((replace(source, definition=missing_scene),), "active")[0] == "incomplete"
    with pytest.raises(ValueError):
        render_sources((replace(source, definition=source.definition.model_copy(update={"public_client": None})),), "active")
    bad = source.definition.model_copy(update={"facts": tuple(
        fact.model_copy(update={"value": False}) if fact.fact_id.endswith("delivery_unproven") else fact
        for fact in source.definition.facts)})
    with pytest.raises(ValueError): render_sources((replace(source, definition=bad),), "active")


@pytest.mark.parametrize("profile,terminal", [
    ("difficulty.open-expedition", "run-complete"),
    ("difficulty.silent-hunting-ground", "run-exit"),
])
async def test_public_play_cutoff_terminal_and_read_only(profile, terminal, monkeypatch):
    runtime = build_demo_runtime()
    app = create_app(services=runtime.services); app.state.api_services = runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
        history, regional, _, ended = await reach_archive(client, profile)
        paths = [history[0]["session_id"], history[3]["session_id"], regional["session_id"]]
        before = runtime.store.snapshot()
        rows = []
        from deviation_protocol.infrastructure.demo_persistence import DemoUnitOfWork
        async def forbidden(*args, **kwargs):
            raise AssertionError("recap attempted a write or gameplay lock")
        # Direct instrumentation, not an inference from unchanged snapshots.
        monkeypatch.setattr(DemoUnitOfWork, "commit", forbidden)
        monkeypatch.setattr(DemoUnitOfWork, "_acquire_session_lock", forbidden)
        for i, sid in enumerate(paths, 1):
            response = await client.get(f"/v1/sessions/{sid}/run-recap")
            assert response.status_code == 200, response.text
            row = response.json(); JourneyRecapResponse.model_validate(row)
            assert row["status"] == "complete", row
            assert row["context"]["cutoff_visit"] == i
            assert row["context"]["scope"] == ("current" if i == 3 else "historical")
            assert f"第 {i + 1} 次访问" not in row["text"]
            assert (await client.get(f"/v1/sessions/{sid}/run-recap")).json() == row
            assert len(row["text"]) <= 2000
            rows.append(row)
        assert "核验档案室" not in rows[1]["text"]
        assert "送达仍未得到证明" in rows[2]["text"]
        assert "未解决的待核记录已封存" in rows[2]["text"]
        assert ("以失败结果结束" in rows[0]["text"]) == (profile == "difficulty.silent-hunting-ground")
        assert runtime.store.snapshot() == before
        monkeypatch.undo()
        reply = await client.post(f"/v1/sessions/{paths[2]}/{terminal}", headers={"Idempotency-Key": "recap.terminal"},
            json=dict(expected_run_state_version=5, expected_session_state_version=ended["metadata"]["state_version"]))
        assert reply.status_code == 200, reply.text
        terminal_before = runtime.store.snapshot()
        current = (await client.get(f"/v1/sessions/{paths[2]}/run-recap")).json()
        assert ("正常完成，待核事项保留" in current["text"]) == (terminal == "run-complete")
        assert ("已明确终止" in current["text"]) == (terminal == "run-exit")
        historical = (await client.get(f"/v1/sessions/{paths[1]}/run-recap")).json()
        assert historical["text"] == rows[1]["text"]
        assert historical["context"]["lifecycle_at_cutoff"] == "active"
        assert runtime.store.snapshot() == terminal_before
        # Same character, new Run: no old family leaks into its recap.
        reply = await client.post("/v1/runs/native", json=history[1], headers={"Idempotency-Key": "recap.fresh"})
        assert reply.status_code == 200, reply.text
        fresh = reply.json()
        fresh_recap = (await client.get(f"/v1/sessions/{fresh['session_id']}/run-recap")).json()
        assert fresh_recap["context"]["run_id"] != current["context"]["run_id"]
        assert "会签暂缓" not in fresh_recap["text"]
        assert (await client.get(f"/v1/sessions/{paths[2]}/run-recap")).json() == current
        assert not runtime.store.any_session_lock_held


@pytest.mark.parametrize("choice,ending,held", [
    ("hold", "receipt_held", True),
    ("release", "dispatch_closed", False),
])
async def test_http_dispatch_ending_fact_consistency(choice, ending, held, monkeypatch):
    from deviation_protocol.infrastructure.demo_persistence import DemoUnitOfWork

    runtime = build_demo_runtime()
    app = create_app(services=runtime.services)
    app.state.api_services = runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
        entry, _ = await admit(client, "difficulty.silent-hunting-ground")
        first = entry["session_id"]
        ended, _ = await play_to_ending(client, first)
        continued = await client.post(f"/v1/sessions/{first}/run-continuation",
            headers={"Idempotency-Key": "recap.consistency.continue"},
            json=dict(expected_run_state_version=3,
                      expected_session_state_version=ended["metadata"]["state_version"]))
        assert continued.status_code == 200, continued.text
        sid = continued.json()["session_id"]
        await action(client, sid, "recap.observe", action_type="OBSERVE", description="核对收件台")
        await action(client, sid, "recap.talk", action_type="TALK",
                     target_ids=["scenario-npc-1"], dialogue="核对排程")
        current = await view(client, sid)
        await action(client, sid, "recap.choose", action_type="CHOOSE",
                     decision_id=current["narrative_frame"]["decision_id"],
                     choice_id=f"undelivered_receipt.action.{choice}")
        stored = runtime.store._snapshots[sid].state["scenario_runtime"]
        assert stored["ending_id"] == f"undelivered_receipt.ending.{ending}"
        facts = stored["mutable_fact_values"]
        fact_id = "undelivered_receipt.fact.dispatch_held"
        assert facts[fact_id] is held

        async def forbidden(*args, **kwargs):
            raise AssertionError("recap attempted a write or gameplay lock")

        monkeypatch.setattr(DemoUnitOfWork, "commit", forbidden)
        monkeypatch.setattr(DemoUnitOfWork, "_acquire_session_lock", forbidden)
        before = runtime.store.snapshot()
        url = f"/v1/sessions/{sid}/run-recap"
        good = await client.get(url)
        assert good.status_code == 200, good.text
        available = JourneyRecapResponse.model_validate(good.json())
        assert available.status == "complete"
        assert ("会签暂缓已生效" in available.text) is held
        assert ("你选择放行本次发运" in available.text) is not held
        assert runtime.store.snapshot() == before

        # Only this authoritative snapshot field changes; real HTTP ending and
        # all persisted transition/version evidence remain intact.
        with monkeypatch.context() as patch:
            patch.setitem(facts, fact_id, not held)
            conflicting = runtime.store.snapshot()
            bad = await client.get(url)
            assert bad.status_code == 200, bad.text
            unavailable = JourneyRecapResponse.model_validate(bad.json())
            assert unavailable.status == "unavailable_evidence"
            assert unavailable.text == ""
            assert unavailable.context == available.context
            assert runtime.store.snapshot() == conflicting
        assert runtime.store.snapshot() == before
        assert not runtime.store.any_session_lock_held


async def test_http_ownership_missing_conflict_and_closed_transport(monkeypatch):
    from deviation_protocol.api.dependencies import get_current_principal
    from deviation_protocol.application.identity import RequestPrincipal
    runtime = build_demo_runtime()
    app = create_app(services=runtime.services); app.state.api_services = runtime.services
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
        entry, _ = await admit(client)
        sid = entry["session_id"]; url = f"/v1/sessions/{sid}/run-recap"
        before = runtime.store.snapshot()
        good = await client.get(url)
        assert good.status_code == 200 and good.json()["status"] == "complete", good.text
        assert (await client.get(url + "?other_run=wrong")).status_code == 422
        assert (await client.request("GET", url, content=b"{}")).status_code == 422
        assert (await client.get("/v1/sessions/unknown/run-recap")).status_code == 404
        app.dependency_overrides[get_current_principal] = lambda: RequestPrincipal(player_id="other", authentication_scheme="demo")
        assert (await client.get(url)).status_code == 404
        app.dependency_overrides.clear()
        assert runtime.store.snapshot() == before
        participation = runtime.store._run_participations.pop(sid)
        try:
            unbound = await client.get(url)
            assert unbound.status_code == 200 and unbound.json()["status"] == "unavailable_evidence"
            assert unbound.json()["context"] is None and unbound.json()["text"] == ""
        finally: runtime.store._run_participations[sid] = participation
        original = runtime.store._snapshots[sid]
        try:
            for snapshot in (None, replace(original, state_version=original.state_version + 1)):
                if snapshot is None: del runtime.store._snapshots[sid]
                else: runtime.store._snapshots[sid] = snapshot
                corrupt = runtime.store.snapshot()
                response = await client.get(url)
                assert response.status_code == 200, response.text
                assert response.json()["status"] == "unavailable_evidence"
                assert response.json()["text"] == "" and response.json()["context"] is None
                assert runtime.store.snapshot() == corrupt
        finally: runtime.store._snapshots[sid] = original
        assert runtime.store.snapshot() == before
        # Missing registered copy and required overflow traverse the real HTTP contract.
        import deviation_protocol.application.journey_recap as recap
        identity = next(key for key in CONTENT_COPY if key[0] == "death_certificate")
        with monkeypatch.context() as patch:
            patch.delitem(CONTENT_COPY, identity)
            unavailable = (await client.get(url)).json()
            assert unavailable["status"] == "unavailable_evidence" and unavailable["text"] == ""
        with monkeypatch.context() as patch:
            original_render = recap.render_sources
            def overflow(sources, lifecycle):
                original_render(sources, lifecycle)
                return select_text(["😀" * 2001], [])
            patch.setattr(recap, "render_sources", overflow)
            result = (await client.get(url)).json()
            assert result["status"] == "unavailable_overflow" and result["text"] == ""
        assert runtime.store.snapshot() == before
        schema = app.openapi()
        route = schema["paths"]["/v1/sessions/{session_id}/run-recap"]
        assert set(route) == {"get"}
        assert set(route["get"]["responses"]) == {"200", "404", "409", "422", "500", "503"}
