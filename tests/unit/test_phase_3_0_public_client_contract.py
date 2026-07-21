from __future__ import annotations

import asyncio
from copy import deepcopy
import json
from pathlib import Path
from typing import Any

import pytest

from deviation_protocol.application.action_gateway import ActionGateway, ActionRoute
from deviation_protocol.application.narrative_outcome_policy import (
    allowed_narrative_outcomes,
    available_narrative_actions,
)
from deviation_protocol.domain.actions import ActionContext, ActionSubmission, ActionType
from deviation_protocol.domain.policies import InputContractPolicy
from deviation_protocol.domain.scenario import ScenarioCatalog
from deviation_protocol.domain.state import GameState
from tests.unit.test_phase_2_4a_playtest import (
    asgi_request,
    build_playtest,
)


SESSION_PATH = "/v1/sessions/playtest-session"


async def _create(app: Any, request_id: str = "public-contract-create") -> None:
    status, _, _ = await asgi_request(
        app,
        "POST",
        "/v1/sessions",
        {
            "client_request_id": request_id,
            "character_definition_id": "character.death_certificate.investigator",
            "scenario_id": "death_certificate",
        },
    )
    assert status == 201


async def _create_and_commit_opening(app: Any, provider: Any) -> dict[str, Any]:
    await _create(app)
    task = asyncio.create_task(
        asgi_request(
            app,
            "POST",
            f"{SESSION_PATH}/actions",
            {
                "turn_id": "public-contract-opening-turn",
                "client_request_id": "public-contract-opening",
                "action_type": "CUSTOM",
                "description": "我有规律地移动手指，发出可复核的生命信号",
            },
        )
    )
    await provider.entered.wait()
    provider.release.set()
    status, response, _ = await task
    assert status == 200
    return response


def _require_target_for_every_talk_outcome(app: Any) -> ScenarioCatalog:
    service = app.state.api_services.session_service
    original = service.scenario_catalog
    assert original is not None
    definition = original.scenario("death_certificate")
    assert definition is not None
    rules = tuple(
        rule.model_copy(
            update={
                "intent": rule.intent.model_copy(update={"requires_target": True})
            }
        )
        if ActionType.TALK in rule.intent.action_types
        else rule
        for rule in definition.narrative_outcome_rules
    )
    modified_definition = definition.model_copy(
        update={"narrative_outcome_rules": rules}
    )
    modified = ScenarioCatalog.model_validate(
        original.model_copy(
            update={
                "scenarios": tuple(
                    modified_definition
                    if item.scenario_id == definition.scenario_id
                    else item
                    for item in original.scenarios
                )
            }
        ).model_dump(mode="python")
    )
    assert all(
        rule.intent.requires_target
        for rule in modified_definition.narrative_outcome_rules
        if ActionType.TALK in rule.intent.action_types
    )
    service.scenario_catalog = modified
    app.state.api_services.turn_orchestrator.scenario_catalog = modified
    return modified


@pytest.mark.asyncio
async def test_public_scenario_catalog_is_an_exact_bounded_allowlist() -> None:
    app, _, _ = build_playtest()
    status, payload, _ = await asgi_request(app, "GET", "/v1/scenarios")

    assert status == 200
    assert set(payload) == {"scenarios"}
    assert len(payload["scenarios"]) == 1
    scenario = payload["scenarios"][0]
    assert set(scenario) == {
        "scenario_id",
        "content_version",
        "title",
        "hook",
        "playable_characters",
        "default_character_definition_id",
    }
    assert scenario["scenario_id"] == "death_certificate"
    assert scenario["content_version"] == "death-certificate-1.1.0"
    assert scenario["default_character_definition_id"] == (
        "character.death_certificate.investigator"
    )
    assert len(scenario["playable_characters"]) == 5
    assert all(
        set(item) == {"character_definition_id", "display_name", "description"}
        for item in scenario["playable_characters"]
    )
    serialized = json.dumps(payload, ensure_ascii=False)
    for forbidden in (
        "fact.",
        "clue.",
        "ending.",
        "arrival_locked",
        "life_disputed",
        "narrative_outcome_rules",
        "memory_rules",
        "persona_summary",
        "npc.death_certificate",
        "security_alert",
    ):
        assert forbidden not in serialized


@pytest.mark.asyncio
async def test_active_view_projects_current_public_scene_and_is_read_only() -> None:
    app, store, _ = build_playtest()
    await _create(app)
    before = deepcopy(
        (
            store.sessions,
            store.snapshots,
            store.events,
            store.turn_requests,
            store.jobs,
        )
    )

    status, view, _ = await asgi_request(app, "GET", f"{SESSION_PATH}/view")

    assert status == 200
    assert set(view) == {
        "metadata",
        "narrative_frame",
        "player_state",
        "player_memory",
        "presentation",
        "action_affordances",
        "scenario_status",
        "public_clocks",
        "recent_narrative_texts",
    }
    assert view["presentation"] == {
        "title": "死亡证明已签发",
        "scene_title": "封闭抵达",
        "scene_summary": "在封闭接收室中回应迫近的处置程序。",
    }
    assert "ending" not in view["presentation"]
    assert "ending_id" not in view
    assert view["action_affordances"]["mode"] == "DECISION"
    assert view["action_affordances"]["actions"] == []
    assert view["action_affordances"]["decision_id"] == (
        view["narrative_frame"]["decision_id"]
    )
    assert all(
        item["action_type"] == "CHOOSE"
        for item in view["action_affordances"]["choices"]
    )
    assert before == (
        store.sessions,
        store.snapshots,
        store.events,
        store.turn_requests,
        store.jobs,
    )


@pytest.mark.asyncio
async def test_free_action_affordances_share_gateway_contract_and_safe_targets() -> None:
    app, store, provider = build_playtest()
    await _create_and_commit_opening(app, provider)
    status, view, _ = await asgi_request(app, "GET", f"{SESSION_PATH}/view")
    assert status == 200

    affordances = view["action_affordances"]
    assert affordances["mode"] == "FREE_ACTIONS"
    by_type = {item["action_type"]: item for item in affordances["actions"]}
    assert "CONTINUE" in by_type
    assert by_type["CONTINUE"] == {
        "action_type": "CONTINUE",
        "label": "继续",
        "input_kind": "NONE",
        "target_required": False,
        "targets": [],
    }
    assert by_type["TALK"]["input_kind"] == "DIALOGUE"
    assert by_type["TALK"]["max_input_length"] == 200
    assert by_type["TALK"]["target_required"] is False
    visible_ids = {item["npc_id"] for item in view["player_state"]["visible_npcs"]}
    assert {
        target["target_id"] for target in by_type["TALK"]["targets"]
    } == visible_ids

    catalog = app.state.api_services.session_service.scenario_catalog
    assert catalog is not None
    state = GameState.from_snapshot(
        store.snapshots["playtest-session"].state,
        catalog=catalog.content_catalog,
        scenario_catalog=catalog,
    )
    definition = catalog.scenario("death_certificate")
    assert definition is not None
    frame = app.state.api_services.session_service.story_director.plan_frame(
        state,
        definition,
        profession_tags=(),
    )
    authoritative = {
        item.action_type: item
        for item in available_narrative_actions(
            state=state,
            definition=definition,
            frame=frame,
        )
    }
    assert set(authoritative) == set(by_type) - {"CONTINUE"}
    gateway = ActionGateway.from_config()
    for action_type_value, affordance in by_type.items():
        action_type = ActionType(action_type_value)
        contract = InputContractPolicy.contract_for(action_type)
        assert contract is not None
        assert contract.input_kind.value == affordance["input_kind"]
        assert contract.max_length == affordance.get("max_input_length")
        assert contract.target_required is affordance["target_required"]
        submission_kwargs: dict[str, Any] = {}
        if contract.input_kind.value == "DESCRIPTION":
            submission_kwargs["description"] = "我尝试观察并核对现场"
        elif contract.input_kind.value == "DIALOGUE":
            submission_kwargs["dialogue"] = "请复核当前情况"
        result = gateway.evaluate(
            ActionContext(
                submission=ActionSubmission(
                    session_id="playtest-session",
                    turn_id="gateway-consistency",
                    client_request_id=f"gateway-{action_type.value.lower()}",
                    action_type=action_type,
                    **submission_kwargs,
                ),
                current_turn_id="gateway-consistency",
                visible_entity_ids=frozenset(visible_ids),
                interactable_entity_ids=frozenset(visible_ids),
            )
        )
        assert result.route is not ActionRoute.REJECT_LOCAL


@pytest.mark.asyncio
async def test_talk_input_contract_is_independent_of_targeted_outcome_rules() -> None:
    app, store, provider = build_playtest()
    catalog = _require_target_for_every_talk_outcome(app)
    await _create_and_commit_opening(app, provider)

    status, view, _ = await asgi_request(app, "GET", f"{SESSION_PATH}/view")
    assert status == 200
    by_type = {
        item["action_type"]: item
        for item in view["action_affordances"]["actions"]
    }
    talk = by_type["TALK"]
    assert talk["input_kind"] == "DIALOGUE"
    assert talk["target_required"] is False
    visible_ids = {
        item["npc_id"] for item in view["player_state"]["visible_npcs"]
    }
    assert visible_ids
    assert {item["target_id"] for item in talk["targets"]} == visible_ids

    state = GameState.from_snapshot(
        store.snapshots["playtest-session"].state,
        catalog=catalog.content_catalog,
        scenario_catalog=catalog,
    )
    definition = catalog.scenario("death_certificate")
    assert definition is not None
    frame = app.state.api_services.session_service.story_director.plan_frame(
        state,
        definition,
        profession_tags=(),
    )
    contract = InputContractPolicy.contract_for(ActionType.TALK)
    assert contract is not None
    assert contract.input_kind.value == "DIALOGUE"
    assert contract.target_supported is True
    assert contract.target_required is False

    no_target = ActionSubmission(
        session_id="playtest-session",
        turn_id="talk-without-target",
        client_request_id="talk-without-target",
        action_type=ActionType.TALK,
        dialogue="请复核当前情况",
    )
    gateway = ActionGateway.from_config()
    no_target_gateway = gateway.evaluate(
        ActionContext(
            submission=no_target,
            current_turn_id=no_target.turn_id,
            visible_entity_ids=frozenset(visible_ids),
            interactable_entity_ids=frozenset(visible_ids),
        )
    )
    assert no_target_gateway.route is ActionRoute.NARRATIVE_NORMAL
    without_target_outcomes = allowed_narrative_outcomes(
        submission=no_target,
        state=state,
        state_version=store.sessions["playtest-session"].session.state_version,
        definition=definition,
        frame=frame,
    )
    assert without_target_outcomes == ()

    visible_target = next(iter(sorted(visible_ids)))
    with_target = no_target.model_copy(
        update={
            "client_request_id": "talk-with-visible-target",
            "target_ids": (visible_target,),
        }
    )
    with_target_outcomes = allowed_narrative_outcomes(
        submission=with_target,
        state=state,
        state_version=store.sessions["playtest-session"].session.state_version,
        definition=definition,
        frame=frame,
    )
    assert with_target_outcomes
    assert all(item.rule.intent.requires_target for item in with_target_outcomes)

    service = app.state.api_services.session_service
    service.session_id_generator = lambda: "other-session"
    service.seed_generator = lambda: 43
    await _create(app, "other-session-create")
    other_snapshot = store.snapshots["other-session"]
    other_state = GameState.from_snapshot(
        other_snapshot.state,
        catalog=catalog.content_catalog,
        scenario_catalog=catalog,
    )
    original_other_target = next(iter(sorted(other_state.npcs)))
    other_target = "other-session-visible-npc"
    other_npc = other_state.npcs.pop(original_other_target)
    other_state.npcs[other_target] = other_npc.model_copy(
        update={"npc_id": other_target}
    )
    other_state.validate_against(catalog.content_catalog)
    store.snapshots["other-session"] = type(other_snapshot)(
        state_version=other_snapshot.state_version,
        state=other_state.to_snapshot(),
    )
    other_status, other_view, _ = await asgi_request(
        app,
        "GET",
        "/v1/sessions/other-session/view",
    )
    assert other_status == 200
    assert other_target in {
        item["npc_id"] for item in other_view["player_state"]["visible_npcs"]
    }
    assert other_target not in state.npcs

    hidden_targets = set(state.npcs) - visible_ids
    assert hidden_targets
    definition_target = state.npcs[visible_target].definition_id
    rejected_targets = {
        "hidden": next(iter(sorted(hidden_targets))),
        "other-session": other_target,
        "nonexistent": "npc.runtime.does-not-exist",
        "definition-id": definition_target,
    }
    version_before_rejections = store.sessions["playtest-session"].session.state_version
    calls_before_rejections = provider.calls
    for label, target_id in rejected_targets.items():
        rejected_status, rejected, _ = await asgi_request(
            app,
            "POST",
            f"{SESSION_PATH}/actions",
            {
                "turn_id": f"talk-rejected-{label}",
                "client_request_id": f"talk-rejected-{label}",
                "action_type": "TALK",
                "target_ids": [target_id],
                "dialogue": "请复核当前情况",
            },
        )
        assert rejected_status == 200
        assert rejected["resolution_kind"] == "REJECTED_LOCAL"
        assert rejected["result_code"] == "INACCESSIBLE_TARGET"
    assert store.sessions["playtest-session"].session.state_version == (
        version_before_rejections
    )
    assert provider.calls == calls_before_rejections

    accepted_status, accepted, _ = await asgi_request(
        app,
        "POST",
        f"{SESSION_PATH}/actions",
        {
            "turn_id": with_target.turn_id,
            "client_request_id": with_target.client_request_id,
            "action_type": "TALK",
            "target_ids": [visible_target],
            "dialogue": with_target.dialogue,
        },
    )
    assert accepted_status == 200
    assert accepted["resolution_kind"] == "NARRATIVE_COMMITTED"
    assert accepted["narrative_status"] == "COMMITTED"


@pytest.mark.asyncio
async def test_decision_affordance_exposes_choices_and_no_free_actions() -> None:
    app, _, provider = build_playtest()
    response = await _create_and_commit_opening(app, provider)
    for index in range(1, 5):
        status, response, _ = await asgi_request(
            app,
            "POST",
            f"{SESSION_PATH}/actions",
            {
                "turn_id": f"public-contract-continue-{index}",
                "client_request_id": f"public-contract-continue-{index}",
                "action_type": "CONTINUE",
            },
        )
        assert status == 200
        if response["narrative_frame"]["decision_required"]:
            break
    assert response["narrative_frame"]["decision_required"] is True

    status, view, _ = await asgi_request(app, "GET", f"{SESSION_PATH}/view")
    assert status == 200
    affordances = view["action_affordances"]
    assert set(affordances) == {"mode", "actions", "decision_id", "choices"}
    assert affordances["mode"] == "DECISION"
    assert affordances["actions"] == []
    assert affordances["decision_id"] == view["narrative_frame"]["decision_id"]
    assert "allowed_custom_action_constraints" not in view["narrative_frame"]
    assert all(
        item["action_type"] == "choice" and item["target_ids"] == []
        for item in view["narrative_frame"]["suggested_actions"]
    )
    assert [item["choice_id"] for item in affordances["choices"]] == [
        item["action_id"] for item in view["narrative_frame"]["suggested_actions"]
    ]
    assert all(
        set(item) == {"action_type", "choice_id", "label", "target_ids"}
        and item["action_type"] == "CHOOSE"
        for item in affordances["choices"]
    )


def test_openapi_exposes_public_contract_without_internal_models() -> None:
    app, _, _ = build_playtest()
    schema = app.openapi()
    scenarios = schema["paths"]["/v1/scenarios"]["get"]
    assert scenarios["responses"]["200"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/PublicScenarioCatalog"}
    model_names = set(schema["components"]["schemas"])
    assert {
        "ScenarioDefinition",
        "ScenarioRuntimeState",
        "NarrativeJob",
        "NarrativeRequest",
        "NarrativeProposalPayload",
        "NarrativeProviderMetadata",
        "PersistedEventReceipt",
        "MemoryRuleDefinition",
    }.isdisjoint(model_names)


def test_production_python_has_no_scenario_id_specific_branch() -> None:
    root = Path(__file__).parents[2] / "src" / "deviation_protocol"
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*.py"))
    )
    for branch in (
        'scenario_id == "death_certificate"',
        "scenario_id == 'death_certificate'",
        'runtime.scenario_id == "death_certificate"',
        "runtime.scenario_id == 'death_certificate'",
    ):
        assert branch not in source
