from __future__ import annotations

import asyncio
from copy import deepcopy
import json
from typing import Any

import pytest

from tests.unit.test_phase_2_4a_playtest import (
    assert_no_internal_fields,
    asgi_request,
    build_playtest,
)


SESSION_PATH = "/v1/sessions/playtest-session"
PUBLIC_VALUE_MARKERS = (
    "rule_id",
    "outcome_token",
    "outcome.",
    "job_id",
    "job.",
    "lease_token",
    "lease.",
    "receipt",
    "provider_name",
    "model_name",
    "security_alert",
    "underground_patient_stability",
)


def _assert_public_payload_values(
    *payloads: dict[str, Any], allow_current_ending: bool = False
) -> None:
    for payload in payloads:
        assert_no_internal_fields(payload)
    serialized = json.dumps(payloads, ensure_ascii=False).casefold()
    for marker in PUBLIC_VALUE_MARKERS:
        assert marker not in serialized
    if not allow_current_ending:
        assert "death_certificate.ending." not in serialized


async def _create_and_open(app: Any, provider: Any, prefix: str) -> dict[str, Any]:
    status, created, _ = await asgi_request(
        app,
        "POST",
        "/v1/sessions",
        {
            "client_request_id": f"{prefix}-create",
            "character_definition_id": "character.death_certificate.investigator",
            "scenario_id": "death_certificate",
        },
    )
    assert status == 201
    opening_task = asyncio.create_task(
        asgi_request(
            app,
            "POST",
            f"{SESSION_PATH}/actions",
            {
                "turn_id": f"{prefix}-opening-turn",
                "client_request_id": f"{prefix}-opening-request",
                "action_type": "CUSTOM",
                "description": "我有规律地移动手指，发出可复核的生命信号",
            },
        )
    )
    await provider.entered.wait()
    provider.release.set()
    opening_status, opening, _ = await opening_task
    assert opening_status == 200
    assert opening["narrative_status"] == "COMMITTED"
    assert opening["narrative_frame"]["phase_id"] == (
        "death_certificate.life_disputed"
    )
    return opening


async def _continue(app: Any, request_id: str) -> dict[str, Any]:
    status, response, _ = await asgi_request(
        app,
        "POST",
        f"{SESSION_PATH}/actions",
        {
            "turn_id": f"turn-{request_id}",
            "client_request_id": request_id,
            "action_type": "CONTINUE",
        },
    )
    assert status == 200, response
    return response


async def _narrative(
    app: Any,
    request_id: str,
    description: str,
    *,
    action_type: str = "EXPLORE",
) -> dict[str, Any]:
    text_field = "dialogue" if action_type == "TALK" else "description"
    status, response, _ = await asgi_request(
        app,
        "POST",
        f"{SESSION_PATH}/actions",
        {
            "turn_id": f"turn-{request_id}",
            "client_request_id": request_id,
            "action_type": action_type,
            text_field: description,
        },
    )
    assert status == 200, response
    assert response["narrative_status"] == "COMMITTED", response
    return response


async def _choose(
    app: Any,
    request_id: str,
    frame: dict[str, Any],
    *,
    choice_index: int = 0,
) -> dict[str, Any]:
    status, response, _ = await asgi_request(
        app,
        "POST",
        f"{SESSION_PATH}/actions",
        {
            "turn_id": f"turn-{request_id}",
            "client_request_id": request_id,
            "action_type": "CHOOSE",
            "decision_id": frame["decision_id"],
            "choice_id": frame["suggested_actions"][choice_index]["action_id"],
        },
    )
    assert status == 200, response
    return response


def _clock(response: dict[str, Any]) -> int:
    return next(
        item["value"]
        for item in response["narrative_frame"]["player_visible_clocks"]
        if item["clock_id"] == "predicted_death_deadline"
    )


async def _trace_step(
    app: Any,
    store: Any,
    provider: Any,
    label: str,
    response: dict[str, Any],
) -> dict[str, Any]:
    view_status, view, _ = await asgi_request(app, "GET", f"{SESSION_PATH}/view")
    assert view_status == 200
    assert view["metadata"]["state_version"] == response["resulting_state_version"]
    _assert_public_payload_values(
        response,
        view,
        allow_current_ending=view["scenario_status"] == "ENDED",
    )
    snapshot = store.snapshots["playtest-session"].state
    runtime = snapshot["scenario_runtime"]
    frame = response["narrative_frame"]
    return {
        "label": label,
        "phase": frame["phase_id"],
        "beat": runtime["phase_beat_index"],
        "stop": frame["stop_condition"],
        "decision": frame["decision_required"],
        "version": response["resulting_state_version"],
        "clock": _clock(response),
        "provider_calls": provider.calls,
        "event_count": len(store.events),
        "clues": tuple(frame["visible_clues"]),
        "visible_npcs": tuple(frame["visible_entities"]),
        "memory": deepcopy(view["player_memory"]),
        "memory_fact_refs": tuple(
            item["fact_ref"]
            for item in view["player_memory"]["known_public_facts"]
        ),
        "prompt_budgets": tuple(provider.prompt_budgets),
        "response": deepcopy(response),
        "view": deepcopy(view),
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "final_choice_index",
        "final_action_id",
        "ending_id",
        "protocol_active",
        "settlement_text",
    ),
    (
        (
            0,
            "death_certificate.action.final_suspend",
            "death_certificate.ending.protocol_broken",
            False,
            "核心处置链被正式暂停",
        ),
        (
            1,
            "death_certificate.action.final_disclose",
            "death_certificate.ending.record_challenged",
            True,
            "核心证据链被正式公开",
        ),
    ),
)
async def test_complete_public_api_happy_path_reaches_resolved_ending(
    final_choice_index: int,
    final_action_id: str,
    ending_id: str,
    protocol_active: bool,
    settlement_text: str,
) -> None:
    app, store, provider = build_playtest()
    steps: list[tuple[str, str, int, str, int]] = []
    trace: list[dict[str, Any]] = []
    opening = await _create_and_open(app, provider, "happy")
    trace.append(await _trace_step(app, store, provider, "opening", opening))
    steps.append(("opening", opening["narrative_frame"]["phase_id"], _clock(opening), opening["narrative_frame"]["stop_condition"], opening["resulting_state_version"]))

    recheck = await _narrative(
        app,
        "happy-clinical-recheck",
        "请协调员复核我的连续回应和生命体征",
        action_type="TALK",
    )
    trace.append(await _trace_step(app, store, provider, "recheck", recheck))
    steps.append(("recheck", recheck["narrative_frame"]["phase_id"], _clock(recheck), recheck["narrative_frame"]["stop_condition"], recheck["resulting_state_version"]))
    assert "分诊协调员完成复核并明确确认：你仍然活着" in recheck["narrative_text"]
    assert "拒绝承认" not in opening["narrative_text"]
    assert "拒绝承认" not in recheck["narrative_text"]
    evidence = store.snapshots["playtest-session"].state["scenario_runtime"][
        "narrative_outcome_evidence"
    ]
    assert any(
        item["player_alive_acknowledgement_npc_definition_ids"]
        == ["npc.death_certificate.triage_coordinator"]
        and item["player_alive_acknowledgement_npc_ids"]
        == ["scenario-npc-1"]
        for item in evidence
    )
    calls_after_recheck = provider.calls
    replay = await _narrative(
        app,
        "happy-clinical-recheck",
        "请协调员复核我的连续回应和生命体征",
        action_type="TALK",
    )
    assert replay == recheck
    assert provider.calls == calls_after_recheck

    before_query = store.snapshots["playtest-session"]
    query_status, query, _ = await asgi_request(
        app,
        "POST",
        f"{SESSION_PATH}/actions",
        {
            "turn_id": "happy-query",
            "client_request_id": "happy-query",
            "action_type": "INSPECT_STATUS",
        },
    )
    assert query_status == 200
    assert query["state_changed"] is False
    assert store.snapshots["playtest-session"] == before_query
    _assert_public_payload_values(query)

    continued = await _continue(app, "happy-life-continue-1")
    trace.append(await _trace_step(app, store, provider, "life-continue-1", continued))
    steps.append(("life-continue-1", continued["narrative_frame"]["phase_id"], _clock(continued), continued["narrative_frame"]["stop_condition"], continued["resulting_state_version"]))
    decision = await _continue(app, "happy-life-continue-2")
    trace.append(await _trace_step(app, store, provider, "life-continue-2", decision))
    steps.append(("life-continue-2", decision["narrative_frame"]["phase_id"], _clock(decision), decision["narrative_frame"]["stop_condition"], decision["resulting_state_version"]))
    assert decision["narrative_frame"]["decision_required"] is True

    stale_token = decision["narrative_frame"]["decision_id"]
    early = await _choose(app, "happy-early-choice", decision["narrative_frame"])
    trace.append(await _trace_step(app, store, provider, "early-choice", early))
    steps.append(("early-choice", early["narrative_frame"]["phase_id"], _clock(early), early["narrative_frame"]["stop_condition"], early["resulting_state_version"]))
    assert early["narrative_frame"]["phase_id"] == "death_certificate.disposal_escape"

    stale_status, stale, _ = await asgi_request(
        app,
        "POST",
        f"{SESSION_PATH}/actions",
        {
            "turn_id": "happy-stale-choice",
            "client_request_id": "happy-stale-choice",
            "action_type": "CHOOSE",
            "decision_id": stale_token,
            "choice_id": "death_certificate.action.prove_vitals",
        },
    )
    assert stale_status == 200
    assert stale["result_code"] == "STALE_DECISION"
    assert stale["state_changed"] is False
    _assert_public_payload_values(stale)

    escape_one = await _continue(app, "happy-escape-continue-1")
    trace.append(await _trace_step(app, store, provider, "escape-continue-1", escape_one))
    escape_two = await _continue(app, "happy-escape-continue-2")
    trace.append(await _trace_step(app, store, provider, "escape-continue-2", escape_two))
    steps.extend(
        (
            ("escape-continue-1", escape_one["narrative_frame"]["phase_id"], _clock(escape_one), escape_one["narrative_frame"]["stop_condition"], escape_one["resulting_state_version"]),
            ("escape-continue-2", escape_two["narrative_frame"]["phase_id"], _clock(escape_two), escape_two["narrative_frame"]["stop_condition"], escape_two["resulting_state_version"]),
        )
    )
    assert escape_two["narrative_frame"]["phase_id"] == "death_certificate.investigation"

    before_guess = deepcopy(store.snapshots["playtest-session"].state)
    guessed = await _narrative(
        app,
        "happy-direct-hidden-guess",
        "请核对死亡记录是否早于诊断，并验证预测会导致结果以及地下患者还活着",
        action_type="CUSTOM",
    )
    trace.append(await _trace_step(app, store, provider, "direct-hidden-guess", guessed))
    guessed_state = store.snapshots["playtest-session"].state
    assert guessed_state["scenario_runtime"]["discovered_clue_ids"] == (
        before_guess["scenario_runtime"]["discovered_clue_ids"]
    )
    assert guessed_state["scenario_runtime"]["opened_location_ids"] == (
        before_guess["scenario_runtime"]["opened_location_ids"]
    )
    assert guessed_state["player_memory"] == before_guess["player_memory"]
    assert all(
        hidden not in guessed["narrative_text"]
        for hidden in ("早于诊断", "预测会导致", "地下患者还活着")
    )
    assert guessed["narrative_frame"]["decision_required"] is True
    route_choice = await _choose(
        app, "happy-investigation-choice", guessed["narrative_frame"]
    )
    trace.append(await _trace_step(app, store, provider, "investigation-choice", route_choice))
    records = await _narrative(
        app,
        "happy-records",
        "逐项查看当前档案室内已经公开的记录",
    )
    trace.append(await _trace_step(app, store, provider, "records", records))
    audit = await _narrative(
        app,
        "happy-audit",
        "核对日志时间顺序以及规程反馈",
    )
    trace.append(await _trace_step(app, store, provider, "audit", audit))
    assert audit["narrative_frame"]["decision_required"] is True
    route_choice_two = await _choose(
        app, "happy-investigation-choice-2", audit["narrative_frame"]
    )
    trace.append(
        await _trace_step(
            app, store, provider, "investigation-choice-2", route_choice_two
        )
    )
    assert store.snapshots["playtest-session"].state["scenario_runtime"][
        "current_location_id"
    ] == "death_certificate.observation_level"
    assert route_choice_two["narrative_frame"]["visible_entities"] == [
        "scenario-npc-3"
    ]
    assert store.snapshots["playtest-session"].state["scenario_runtime"][
        "current_decision_id"
    ] is None
    assert [
        item["outcome_rule_id"]
        for item in store.snapshots["playtest-session"].state["scenario_runtime"][
            "narrative_outcome_evidence"
        ]
    ] == [
        "death_certificate.outcome.investigation_audit_route",
        "death_certificate.outcome.investigation_no_effect",
        "death_certificate.outcome.investigation_records_route",
        "death_certificate.outcome.life_disputed_clinical_recheck",
        "death_certificate.outcome.purposeful_life_signal",
    ]
    patient = await _narrative(
        app,
        "happy-patient",
        "复核地下患者的生命体征与连续监测历史",
        action_type="OBSERVE",
    )
    trace.append(await _trace_step(app, store, provider, "patient", patient))
    assert patient["narrative_text"] == (
        "地下观察对象的即时生命体征与连续监测历史一致，控制室路径已按固定结果开放。"
    )
    assert store.snapshots["playtest-session"].state["scenario_runtime"][
        "completed_clue_group_ids"
    ] == [
        "death_record_predates_diagnosis",
        "player_is_alive",
        "prediction_causes_outcome",
        "underground_patient_alive",
    ]
    assert patient["narrative_frame"]["phase_id"] == (
        "death_certificate.self_fulfilling_truth"
    )
    steps.extend(
        (
            ("investigation-choice", route_choice["narrative_frame"]["phase_id"], _clock(route_choice), route_choice["narrative_frame"]["stop_condition"], route_choice["resulting_state_version"]),
            ("records", records["narrative_frame"]["phase_id"], _clock(records), records["narrative_frame"]["stop_condition"], records["resulting_state_version"]),
            ("audit", audit["narrative_frame"]["phase_id"], _clock(audit), audit["narrative_frame"]["stop_condition"], audit["resulting_state_version"]),
            ("investigation-choice-2", route_choice_two["narrative_frame"]["phase_id"], _clock(route_choice_two), route_choice_two["narrative_frame"]["stop_condition"], route_choice_two["resulting_state_version"]),
            ("patient", patient["narrative_frame"]["phase_id"], _clock(patient), patient["narrative_frame"]["stop_condition"], patient["resulting_state_version"]),
        )
    )

    truth_one = await _continue(app, "happy-truth-continue-1")
    trace.append(await _trace_step(app, store, provider, "truth-continue-1", truth_one))
    core = await _continue(app, "happy-truth-continue-2")
    trace.append(await _trace_step(app, store, provider, "truth-continue-2", core))
    assert truth_one["narrative_frame"]["phase_id"] == "death_certificate.self_fulfilling_truth"
    assert core["narrative_frame"]["phase_id"] == "death_certificate.core_conflict"
    assert core["narrative_frame"]["mode"] == "RAPID_DECISION"

    rapid_decisions = []
    current = core
    calls_before_core = provider.calls
    for index in range(1, 5):
        choice_index = final_choice_index if index == 4 else 0
        rapid_decisions.append(
            current["narrative_frame"]["suggested_actions"][choice_index]["action_id"]
        )
        current = await _choose(
            app,
            f"happy-core-choice-{index}",
            current["narrative_frame"],
            choice_index=choice_index,
        )
        trace.append(await _trace_step(app, store, provider, f"core-choice-{index}", current))
        if index < 4:
            assert current["narrative_frame"]["mode"] == "RAPID_DECISION"
            assert current["narrative_frame"]["decision_required"] is True

    assert [
        (
            item["label"],
            item["phase"].rsplit(".", 1)[-1],
            item["beat"],
            item["stop"],
            item["decision"],
            item["version"],
            item["clock"],
            item["provider_calls"],
            item["event_count"],
        )
        for item in trace
    ] == [
        ("opening", "life_disputed", 0, "CONTINUE", False, 1, 0, 1, 2),
        ("recheck", "life_disputed", 1, "CONTINUE", False, 2, 0, 2, 4),
        ("life-continue-1", "life_disputed", 2, "CONTINUE", False, 3, 1, 2, 5),
        ("life-continue-2", "life_disputed", 3, "AWAIT_PLAYER", True, 4, 2, 2, 7),
        ("early-choice", "disposal_escape", 0, "CONTINUE", False, 5, 2, 2, 8),
        ("escape-continue-1", "disposal_escape", 1, "CONTINUE", False, 6, 3, 2, 9),
        ("escape-continue-2", "investigation", 0, "CONTINUE", False, 7, 4, 2, 10),
        ("direct-hidden-guess", "investigation", 1, "AWAIT_PLAYER", True, 8, 5, 3, 11),
        ("investigation-choice", "investigation", 2, "CONTINUE", False, 9, 6, 3, 12),
        ("records", "investigation", 3, "CONTINUE", False, 10, 7, 4, 13),
        ("audit", "investigation", 4, "AWAIT_PLAYER", True, 11, 8, 5, 18),
        ("investigation-choice-2", "investigation", 5, "CONTINUE", False, 12, 9, 5, 19),
        ("patient", "self_fulfilling_truth", 0, "CONTINUE", False, 13, 10, 6, 22),
        ("truth-continue-1", "self_fulfilling_truth", 1, "CONTINUE", False, 14, 11, 6, 23),
        ("truth-continue-2", "core_conflict", 0, "AWAIT_PLAYER", True, 15, 12, 6, 24),
        ("core-choice-1", "core_conflict", 1, "AWAIT_PLAYER", True, 16, 12, 6, 25),
        ("core-choice-2", "core_conflict", 2, "AWAIT_PLAYER", True, 17, 12, 6, 26),
        ("core-choice-3", "core_conflict", 3, "AWAIT_PLAYER", True, 18, 12, 6, 27),
        ("core-choice-4", "resolution", 0, "SCENARIO_ENDED", False, 19, 12, 6, 28),
    ]
    alive_clue = ("death_certificate.clue.vital_response",)
    alive_clues = (
        "death_certificate.clue.coherent_response",
        "death_certificate.clue.vital_response",
    )
    record_clues = (
        "death_certificate.clue.protocol_feedback",
        "death_certificate.clue.record_timestamp",
    )
    audit_clues = (
        "death_certificate.clue.audit_sequence",
        "death_certificate.clue.comparison_case",
        "death_certificate.clue.protocol_feedback",
        "death_certificate.clue.record_timestamp",
    )
    assert [item["clues"] for item in trace] == [
        alive_clue,
        alive_clues,
        alive_clues,
        alive_clues,
        (),
        (),
        (),
        (),
        (),
        record_clues,
        audit_clues,
        audit_clues,
        (),
        (),
        (),
        (),
        (),
        (),
        (),
    ]
    coordinator = ("scenario-npc-1",)
    custodian = ("scenario-npc-2",)
    patient_npc = ("scenario-npc-3",)
    core_npcs = ("scenario-npc-1", "scenario-npc-2")
    assert [item["visible_npcs"] for item in trace] == [
        *([coordinator] * 8),
        custodian,
        custodian,
        patient_npc,
        patient_npc,
        patient_npc,
        patient_npc,
        core_npcs,
        core_npcs,
        core_npcs,
        core_npcs,
        core_npcs,
    ]
    baseline_memory_facts = (
        "death_certificate.fact.comfort_disposition_imminent",
        "death_certificate.fact.death_certificate_issued",
        "death_certificate.fact.initial_survival_objective",
        "death_certificate.fact.opening_body_bag_state",
        "death_certificate.fact.opening_time_conflict",
        "death_certificate.fact.player_conscious",
        "death_certificate.fact.player_is_alive",
        "death_certificate.fact.record_marks_player_dead",
    )
    investigation_memory_facts = tuple(
        sorted(
            (*baseline_memory_facts,
             "death_certificate.fact.prediction_causes_outcome",
             "death_certificate.fact.record_predates_diagnosis")
        )
    )
    completed_memory_facts = tuple(
        sorted(
            (*investigation_memory_facts,
             "death_certificate.fact.underground_patient_alive")
        )
    )
    assert [item["memory_fact_refs"] for item in trace] == [
        *([baseline_memory_facts] * 10),
        investigation_memory_facts,
        investigation_memory_facts,
        *([completed_memory_facts] * 7),
    ]
    assert [item["memory"]["scenarios"][0]["status"] for item in trace] == [
        *("STARTED" for _ in range(18)),
        "COMPLETED",
    ]

    assert rapid_decisions == [
        "death_certificate.action.pause_protocol",
        "death_certificate.action.ask_coordinator",
        "death_certificate.action.public_override",
        final_action_id,
    ]
    assert current["narrative_frame"]["mode"] == "SETTLEMENT"
    assert current["narrative_frame"]["stop_condition"] == "SCENARIO_ENDED"
    assert settlement_text in current["narrative_text"]
    assert provider.calls == calls_before_core
    assert _clock(current) < 13
    local_jobs = [
        job
        for job in store.jobs.values()
        if job.prompt_schema_version == "local-server-template-v1"
    ]
    assert len(local_jobs) == 1
    assert local_jobs[0].status.value == "COMMITTED"
    assert local_jobs[0].attempt_count == 0
    assert local_jobs[0].accepted_narrative_text == current["narrative_text"]
    assert len(store.jobs) == provider.calls + 1

    view_status, view, _ = await asgi_request(app, "GET", f"{SESSION_PATH}/view")
    assert view_status == 200
    assert view["scenario_status"] == "ENDED"
    assert view["ending_status"] == "RESOLVED"
    assert view["ending_id"] == ending_id
    assert set(view) == {
        "metadata",
        "narrative_frame",
        "player_state",
        "player_memory",
        "presentation",
        "action_affordances",
        "scenario_status",
        "ending_status",
        "public_clocks",
        "recent_narrative_texts",
        "ending_id",
    }
    assert view["action_affordances"] == {
        "mode": "ENDED",
        "actions": [],
        "choices": [],
    }
    expected_ending_titles = {
        "death_certificate.ending.protocol_broken": "规程已中断",
        "death_certificate.ending.record_challenged": "记录已被质疑",
    }
    assert view["presentation"]["ending"]["title"] == expected_ending_titles[
        ending_id
    ]
    scenario_memory = view["player_memory"]["scenarios"][0]
    assert scenario_memory["status"] == "COMPLETED"
    assert scenario_memory["ending_id"] == view["ending_id"]
    known_facts = {
        item["fact_ref"] for item in view["player_memory"]["known_public_facts"]
    }
    assert {
        "death_certificate.fact.player_is_alive",
        "death_certificate.fact.record_predates_diagnosis",
        "death_certificate.fact.prediction_causes_outcome",
        "death_certificate.fact.underground_patient_alive",
    } <= known_facts
    runtime = store.snapshots["playtest-session"].state["scenario_runtime"]
    assert view["ending_status"] == runtime["ending_status"]
    assert runtime["completed_clue_group_ids"] == [
        "death_record_predates_diagnosis",
        "player_is_alive",
        "prediction_causes_outcome",
        "underground_patient_alive",
    ]
    assert runtime["mutable_fact_values"][
        "death_certificate.fact.disposal_protocol_active"
    ] is protocol_active
    assert any(
        event.event_type == "ScenarioDecisionSelected"
        and event.payload["scenario_event_type"] == "core.conflict.resolved"
        for event in store.events
    )

    request_status, recovered_request, _ = await asgi_request(
        app,
        "GET",
        f"{SESSION_PATH}/requests/happy-patient",
    )
    assert request_status == 200
    assert recovered_request["status"] == "COMMITTED"
    assert provider.calls == 6
    assert len(provider.prompt_budgets) == provider.calls
    assert all(chars <= 32_000 and bytes_ <= 64_000 for chars, bytes_ in provider.prompt_budgets)
    assert (
        max(chars for chars, _ in provider.prompt_budgets),
        max(bytes_ for _, bytes_ in provider.prompt_budgets),
    ) == (8_776, 10_614)
    assert [item[3] for item in steps[:7]] == [
        "CONTINUE",
        "CONTINUE",
        "CONTINUE",
        "AWAIT_PLAYER",
        "CONTINUE",
        "CONTINUE",
        "CONTINUE",
    ]
    assert [item["version"] for item in trace] == list(
        range(1, len(trace) + 1)
    )
    assert [item["event_count"] for item in trace] == sorted(
        item["event_count"] for item in trace
    )
    assert all(
        len(item["prompt_budgets"]) == item["provider_calls"] for item in trace
    )
    _assert_public_payload_values(
        opening,
        recheck,
        query,
        decision,
        early,
        stale,
        guessed,
        route_choice,
        records,
        audit,
        route_choice_two,
        patient,
    )
    _assert_public_payload_values(
        current,
        view,
        recovered_request,
        allow_current_ending=True,
    )


@pytest.mark.asyncio
async def test_complete_public_api_deadline_path_reaches_failed_ending() -> None:
    app, store, provider = build_playtest()
    trace: list[dict[str, Any]] = []
    opening = await _create_and_open(app, provider, "deadline")
    trace.append(await _trace_step(app, store, provider, "opening", opening))
    current = None
    for index in range(1, 4):
        current = await _continue(app, f"deadline-life-continue-{index}")
        trace.append(await _trace_step(app, store, provider, f"life-continue-{index}", current))
    assert current is not None
    current = await _choose(app, "deadline-early-choice", current["narrative_frame"])
    trace.append(await _trace_step(app, store, provider, "early-choice", current))
    current = await _continue(app, "deadline-escape-continue-1")
    trace.append(await _trace_step(app, store, provider, "escape-continue-1", current))
    current = await _continue(app, "deadline-escape-continue-2")
    trace.append(await _trace_step(app, store, provider, "escape-continue-2", current))
    assert _clock(current) == 5

    no_effect_index = 0
    while _clock(current) < 13:
        if current["narrative_frame"]["decision_required"]:
            current = await _choose(
                app,
                f"deadline-choice-{no_effect_index}",
                current["narrative_frame"],
            )
            trace.append(
                await _trace_step(app, store, provider, f"choice-{no_effect_index}", current)
            )
            continue
        no_effect_index += 1
        current = await _narrative(
            app,
            f"deadline-no-effect-{no_effect_index}",
            "等待并重复与线索无关的动作",
            action_type="CUSTOM",
        )
        trace.append(
            await _trace_step(app, store, provider, f"no-effect-{no_effect_index}", current)
        )
        if no_effect_index == 1:
            calls = provider.calls
            replay = await _narrative(
                app,
                "deadline-no-effect-1",
                "等待并重复与线索无关的动作",
                action_type="CUSTOM",
            )
            assert replay == current
            assert provider.calls == calls
            _assert_public_payload_values(replay)

    assert _clock(current) == 13
    assert [
        (
            item["label"],
            item["phase"].rsplit(".", 1)[-1],
            item["beat"],
            item["stop"],
            item["decision"],
            item["version"],
            item["clock"],
            item["provider_calls"],
            item["event_count"],
        )
        for item in trace
    ] == [
        ("opening", "life_disputed", 0, "CONTINUE", False, 1, 0, 1, 2),
        ("life-continue-1", "life_disputed", 1, "CONTINUE", False, 2, 1, 1, 3),
        ("life-continue-2", "life_disputed", 2, "CONTINUE", False, 3, 2, 1, 4),
        ("life-continue-3", "life_disputed", 3, "AWAIT_PLAYER", True, 4, 3, 1, 6),
        ("early-choice", "disposal_escape", 0, "CONTINUE", False, 5, 3, 1, 7),
        ("escape-continue-1", "disposal_escape", 1, "CONTINUE", False, 6, 4, 1, 8),
        ("escape-continue-2", "investigation", 0, "CONTINUE", False, 7, 5, 1, 9),
        ("no-effect-1", "investigation", 1, "AWAIT_PLAYER", True, 8, 6, 2, 10),
        ("choice-1", "investigation", 2, "CONTINUE", False, 9, 7, 2, 11),
        ("no-effect-2", "investigation", 3, "CONTINUE", False, 10, 8, 3, 13),
        ("no-effect-3", "investigation", 4, "AWAIT_PLAYER", True, 11, 9, 4, 15),
        ("choice-3", "investigation", 5, "CONTINUE", False, 12, 10, 4, 16),
        ("no-effect-4", "investigation", 6, "CONTINUE", False, 13, 11, 5, 18),
        ("no-effect-5", "investigation", 7, "CONTINUE", False, 14, 12, 6, 19),
        ("no-effect-6", "investigation", 8, "SCENARIO_ENDED", False, 15, 13, 7, 21),
    ]
    alive_clue = ("death_certificate.clue.vital_response",)
    assert [item["clues"] for item in trace] == [alive_clue] * 4 + [()] * 11
    coordinator = ("scenario-npc-1",)
    custodian = ("scenario-npc-2",)
    assert [item["visible_npcs"] for item in trace] == [
        *([coordinator] * 8),
        *([custodian] * 7),
    ]
    baseline_memory_facts = (
        "death_certificate.fact.comfort_disposition_imminent",
        "death_certificate.fact.death_certificate_issued",
        "death_certificate.fact.initial_survival_objective",
        "death_certificate.fact.opening_body_bag_state",
        "death_certificate.fact.opening_time_conflict",
        "death_certificate.fact.player_conscious",
        "death_certificate.fact.player_is_alive",
        "death_certificate.fact.record_marks_player_dead",
    )
    assert [item["memory_fact_refs"] for item in trace] == [
        baseline_memory_facts
    ] * 15
    assert [item["memory"]["scenarios"][0]["status"] for item in trace] == [
        *("STARTED" for _ in range(14)),
        "COMPLETED",
    ]
    assert current["narrative_frame"]["mode"] == "SETTLEMENT"
    assert current["narrative_frame"]["stop_condition"] == "SCENARIO_ENDED"
    snapshot = store.snapshots["playtest-session"]
    assert snapshot.state["scenario_runtime"]["ending_id"] == (
        "death_certificate.ending.deadline_reached"
    )

    version = current["resulting_state_version"]
    for action_index, payload in enumerate(
        (
            {"action_type": "CONTINUE"},
            {
                "action_type": "CHOOSE",
                "decision_id": "decision.stale",
                "choice_id": "death_certificate.action.inspect_archive",
            },
            {"action_type": "CUSTOM", "description": "继续行动"},
        ),
        start=1,
    ):
        status, rejected, _ = await asgi_request(
            app,
            "POST",
            f"{SESSION_PATH}/actions",
            {
                "turn_id": f"deadline-ended-{action_index}",
                "client_request_id": f"deadline-ended-{action_index}",
                **payload,
            },
        )
        assert status == 200
        assert rejected["result_code"] == "SCENARIO_ENDED"
        assert rejected["state_changed"] is False
        assert rejected["resulting_state_version"] == version
        _assert_public_payload_values(rejected, allow_current_ending=True)

    view_status, view, _ = await asgi_request(app, "GET", f"{SESSION_PATH}/view")
    assert view_status == 200
    assert view["scenario_status"] == "ENDED"
    assert view["ending_status"] == "FAILED"
    assert view["ending_id"] == "death_certificate.ending.deadline_reached"
    assert view["presentation"]["ending"] == {
        "title": "记录成为现实",
        "summary": "截止时刻到达，处置规程完成了记录所预告的结果。",
    }
    assert view["action_affordances"] == {
        "mode": "ENDED",
        "actions": [],
        "choices": [],
    }
    assert view["player_memory"]["scenarios"][0]["status"] == "COMPLETED"
    assert view["player_memory"]["scenarios"][0]["ending_id"] == view["ending_id"]
    assert view["ending_status"] == store.snapshots["playtest-session"].state[
        "scenario_runtime"
    ]["ending_status"]
    assert provider.calls == 7
    assert all(chars <= 32_000 and bytes_ <= 64_000 for chars, bytes_ in provider.prompt_budgets)
    assert (
        max(chars for chars, _ in provider.prompt_budgets),
        max(bytes_ for _, bytes_ in provider.prompt_budgets),
    ) == (7_851, 9_659)
    assert sum(
        event.event_type == "NarrativeOutcomeAccepted" for event in store.events
    ) == provider.calls
    assert [item["version"] for item in trace] == list(
        range(1, len(trace) + 1)
    )
    assert [item["clock"] for item in trace] == sorted(
        item["clock"] for item in trace
    )
    assert trace[-1]["beat"] >= 0
    assert all(
        len(item["prompt_budgets"]) == item["provider_calls"] for item in trace
    )
    _assert_public_payload_values(view, allow_current_ending=True)
