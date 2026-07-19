from __future__ import annotations

import pytest
from pydantic import ValidationError

from deviation_protocol.application.action_gateway import ActionGateway, ActionRoute
from deviation_protocol.domain.actions import ActionContext, ActionSubmission, ActionType


@pytest.fixture(scope="module")
def gateway() -> ActionGateway:
    return ActionGateway.from_config()


def submission(**overrides: object) -> ActionSubmission:
    values: dict[str, object] = {
        "session_id": "session-1",
        "turn_id": "turn-7",
        "client_request_id": "request-1",
        "action_type": ActionType.CUSTOM,
        "description": "我尝试用镜子反射走廊尽头的微光，观察门缝后是否有动静",
    }
    values.update(overrides)
    return ActionSubmission(**values)


def context(action: ActionSubmission | None = None, **overrides: object) -> ActionContext:
    values: dict[str, object] = {
        "submission": action or submission(),
        "current_turn_id": "turn-7",
        "visible_entity_ids": frozenset({"door", "npc-doctor"}),
        "interactable_entity_ids": frozenset({"switch"}),
        "inventory_item_ids": frozenset({"mirror", "key"}),
        "environment_tool_ids": frozenset({"chair"}),
    }
    values.update(overrides)
    return ActionContext(**values)


def rejection_code(result: object) -> str:
    return result.policy_trace[-1].reason_code  # type: ignore[attr-defined]


def test_legal_creative_action_routes_to_normal_narrative(gateway: ActionGateway) -> None:
    action = submission(target_ids=["door"], tool_ids=["mirror"])
    result = gateway.evaluate(context(action))
    assert result.route is ActionRoute.NARRATIVE_NORMAL
    assert all(trace.outcome.value == "PASS" for trace in result.policy_trace)


def test_nonexistent_inventory_item_is_rejected_locally(gateway: ActionGateway) -> None:
    action = submission(tool_ids=["invented-laser"])
    result = gateway.evaluate(context(action))
    assert result.route is ActionRoute.REJECT_LOCAL
    assert rejection_code(result) == "unavailable_tool"


def test_inaccessible_target_is_rejected_locally(gateway: ActionGateway) -> None:
    action = submission(target_ids=["hidden-basement-npc"])
    result = gateway.evaluate(context(action))
    assert result.route is ActionRoute.REJECT_LOCAL
    assert rejection_code(result) == "inaccessible_target"


def test_player_cannot_decide_npc_outcome(gateway: ActionGateway) -> None:
    action = submission(description="我决定让NPC立刻同意交出钥匙")
    result = gateway.evaluate(context(action))
    assert result.route is ActionRoute.REJECT_LOCAL
    assert rejection_code(result) == "npc_agency_violation"


def test_player_cannot_announce_success(gateway: ActionGateway) -> None:
    action = submission(description="我已经打开了上锁的门")
    result = gateway.evaluate(context(action))
    assert result.route is ActionRoute.REJECT_LOCAL
    assert rejection_code(result) == "declared_success"


def test_multiple_sequential_actions_are_rejected(gateway: ActionGateway) -> None:
    action = submission(description="我尝试撬开门，然后进入房间查看桌上的信")
    result = gateway.evaluate(context(action))
    assert result.route is ActionRoute.REJECT_LOCAL
    assert rejection_code(result) == "multiple_actions"


@pytest.mark.parametrize(
    "description",
    ["啊啊啊啊啊啊啊", "asdfasdf", "我凭空变出一把武器", "我穿墙而过进入密室"],
)
def test_obviously_invalid_actions_are_rejected_not_promoted(
    gateway: ActionGateway, description: str
) -> None:
    result = gateway.evaluate(context(submission(description=description)))
    assert result.route is ActionRoute.REJECT_LOCAL
    assert rejection_code(result) == "invalid_or_impossible_action"


@pytest.mark.parametrize(
    "action_type",
    [ActionType.INSPECT_STATUS, ActionType.INSPECT_INVENTORY, ActionType.INSPECT_QUESTS],
)
def test_state_queries_resolve_locally(
    gateway: ActionGateway, action_type: ActionType
) -> None:
    action = submission(action_type=action_type, description=None)
    result = gateway.evaluate(context(action))
    assert result.route is ActionRoute.RESOLVE_LOCAL
    assert result.policy_trace[-1].reason_code == "local_action"


def test_stale_turn_is_rejected(gateway: ActionGateway) -> None:
    action = submission(turn_id="turn-6")
    result = gateway.evaluate(context(action))
    assert result.route is ActionRoute.REJECT_LOCAL
    assert rejection_code(result) == "stale_turn"


def test_duplicate_request_id_is_rejected(gateway: ActionGateway) -> None:
    action = submission(client_request_id="already-seen")
    result = gateway.evaluate(
        context(action, processed_client_request_ids=frozenset({"already-seen"}))
    )
    assert result.route is ActionRoute.REJECT_LOCAL
    assert rejection_code(result) == "duplicate_request"


def test_action_signature_is_stable_and_request_id_independent() -> None:
    first = submission(
        client_request_id="request-a",
        target_ids=["npc-doctor", "door"],
        tool_ids=["key", "mirror"],
        description="我尝试  打开门",
    )
    second = submission(
        client_request_id="request-b",
        target_ids=["door", "npc-doctor"],
        tool_ids=["mirror", "key"],
        description="我尝试 打开门",
    )
    assert first.action_signature() == second.action_signature()
    assert len(first.action_signature()) == 64


def test_policy_trace_identifies_each_pass_before_rejection(gateway: ActionGateway) -> None:
    result = gateway.evaluate(context(submission(tool_ids=["missing"])))
    assert [item.policy for item in result.policy_trace] == [
        "TurnStatePolicy",
        "DuplicateRequestPolicy",
        "InputContractPolicy",
        "EntityReferencePolicy",
        "InventoryOwnershipPolicy",
    ]


def test_action_specific_contract_is_traced(gateway: ActionGateway) -> None:
    action = submission(action_type=ActionType.TALK, description=None, dialogue=None)
    result = gateway.evaluate(context(action))
    assert result.route is ActionRoute.REJECT_LOCAL
    assert rejection_code(result) == "missing_required_field"


@pytest.mark.parametrize(
    ("field", "value"),
    [("target_ids", "door"), ("tool_ids", [123])],
)
def test_entity_and_tool_ids_require_arrays_of_strings(field: str, value: object) -> None:
    message = "must (?:be submitted as an array|contain only strings)"
    with pytest.raises(ValidationError, match=message):
        submission(**{field: value})
