"""Parent acceptance gaps: forbidden selection inputs and old/new Run isolation.

These tests use the approved closed catalogues. They do not supply an NPC
identity predicate, expand selection, or manufacture a gameplay ending.
"""
from copy import deepcopy

import httpx
import pytest
from pydantic import ValidationError

from deviation_protocol.api.demo_composition import build_demo_runtime
from deviation_protocol.api.main import create_app
from deviation_protocol.domain.world_continuation import (
    DESTINATION_REGION, DESTINATION_WORLD, SOURCE_REGION, SOURCE_WORLD,
    ContinuationSelectionInputsV1, derive_world_visit_id,
)
from deviation_protocol.domain.world_revisit import (
    ARCHIVE_REGION, RegionalPoolEntryV1, RegionalSelectionInputsV1,
    RegionalSelectionVisitV1,
)
from tests.unit.test_run_completion_api import reach_archive
from tests.unit.test_run_revisit_api import action, view
from tests.unit.test_world_continuation import selection


# The parent S7 verification contract names each prohibited source/relation.
# Neither top-level inputs nor a pool edge may acquire such authority.
FORBIDDEN_INPUTS = (
    "npc_id", "scenario_npc_definition", "name", "appearance", "role",
    "template", "model_output", "semantic_similarity", "counterpart",
    "reincarnation", "copy", "successor", "replacement", "relationship",
    "golden_memory", "cross_scenario_persistence", "phase_6_subject_reference",
    "identity_resolution", "memory_schema", "logical_npc_identity",
    "important_npc_recovery_predicate", "authored_world_recovery_predicate",
)


def regional_selection():
    visits = tuple(
        RegionalSelectionVisitV1(
            visit_id=derive_world_visit_id(
                run_id="run.one", continuous_story_line_id="line.one",
                session_id=sid, joined_state_version=ordinal + 2,
            ).value,
            visit_ordinal=ordinal, world=world, region=region, session_id=sid,
        )
        for ordinal, sid, world, region in (
            (1, "session.one", SOURCE_WORLD, SOURCE_REGION),
            (2, "session.two", DESTINATION_WORLD, DESTINATION_REGION),
        )
    )
    return RegionalSelectionInputsV1(
        selector_version="regional-revisit/v1", run_id="run.one",
        continuous_story_line_id="line.one", source_session_id="session.two",
        source_session_state_version=3, source_snapshot_sha256="b" * 64,
        resolution_fingerprint="c" * 64, visits=visits,
        eligible_pool=(RegionalPoolEntryV1(
            world=DESTINATION_WORLD, region=ARCHIVE_REGION,
            scenario_id="receipt_archive", scenario_content_version="receipt-archive-1.0.0",
            content_sha256="a" * 64, required_priority=0, weight=1,
            cooldown_completed_visits=0,
        ),),
    )


@pytest.mark.parametrize("factory,carrier", [
    (selection, ContinuationSelectionInputsV1),
    (regional_selection, RegionalSelectionInputsV1),
])
@pytest.mark.parametrize("field", FORBIDDEN_INPUTS)
def test_parent_s7_rejects_every_unowned_recovery_input(factory, carrier, field):
    clean = factory()
    original = clean.model_dump()
    seed = clean.seed()
    for location in ("selection", "edge"):
        payload = deepcopy(original)
        target = payload if location == "selection" else payload["eligible_pool"][0]
        target[field] = {"claimed_identity": "scenario-npc-1", "priority": 0}
        with pytest.raises(ValidationError) as rejected:
            carrier.model_validate(payload, strict=True)
        expected = (field,) if location == "selection" else ("eligible_pool", 0, field)
        assert any(e["type"] == "extra_forbidden" and e["loc"] == expected
                   for e in rejected.value.errors())
    assert clean.model_dump() == original
    assert carrier.model_validate(original, strict=True).seed() == seed


@pytest.mark.parametrize("terminal", ["completed", "terminated"])
async def test_parent_s7_old_three_visit_history_after_fresh_run_action(terminal):
    runtime = build_demo_runtime()
    app = create_app(services=runtime.services)
    app.state.api_services = runtime.services
    observed = []

    async def record(request):
        observed.append((request.method, request.url.path))

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test",
        event_hooks={"request": [record]},
    ) as client:
        # With no NPC predicate at all, actual required continuation and regional
        # recovery remain reachable. Every ending comes from ordinary public play.
        history, regional, _, ended = await reach_archive(
            client, "difficulty.silent-hunting-ground",
        )
        sessions = (history[0]["session_id"], history[3]["session_id"], regional["session_id"])
        old_views = [await view(client, sid) for sid in sessions]
        route = "run-complete" if terminal == "completed" else "run-exit"
        reply = await client.post(
            f"/v1/sessions/{sessions[2]}/{route}",
            json=dict(expected_run_state_version=5,
                      expected_session_state_version=ended["metadata"]["state_version"]),
            headers={"Idempotency-Key": "s7.final.terminal"},
        )
        assert reply.status_code == 200, reply.text
        routes = ("view", "run-journey", "run-status", "run-completion")
        old = {}
        for sid in sessions:
            for endpoint in routes:
                response = await client.get(f"/v1/sessions/{sid}/{endpoint}")
                assert response.status_code == 200, response.text
                old[sid, endpoint] = response.json()
        for sid, original_view in zip(sessions, old_views):
            assert old[sid, "view"] == original_view
            assert old[sid, "run-status"]["lifecycle_status"] == terminal
            assert old[sid, "run-status"]["can_exit"] is False
            assert old[sid, "run-journey"]["next_transition"] is None
            assert old[sid, "run-completion"]["can_complete"] is False
            assert (old[sid, "run-completion"]["completion"] is not None) == (terminal == "completed")

        fresh = await client.post(
            "/v1/runs/native", json=history[1],
            headers={"Idempotency-Key": "s7.final.fresh"},
        )
        assert fresh.status_code == 200, fresh.text
        new = fresh.json()
        assert new["run_context"]["run_id"] != regional["run_id"]
        assert new["session_id"] not in sessions
        await action(client, new["session_id"], "s7.final.first",
                     action_type="OBSERVE", description="查看病房")
        assert (await view(client, new["session_id"]))["metadata"]["state_version"] == 1
        settled = runtime.store.snapshot()
        start = len(observed)
        for ordinal in (2, 1, 0, 1, 2):
            sid = sessions[ordinal]
            for endpoint in routes:
                response = await client.get(f"/v1/sessions/{sid}/{endpoint}")
                assert response.status_code == 200, response.text
                assert response.json() == old[sid, endpoint]
        assert len(observed[start:]) == 20
        assert {method for method, _ in observed[start:]} == {"GET"}
        assert runtime.store.snapshot() == settled
