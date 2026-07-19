from __future__ import annotations

from collections.abc import Callable
from dataclasses import FrozenInstanceError
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from deviation_protocol.application.action_gateway import ActionGateway, ActionRoute
from deviation_protocol.domain.actions import ActionContext, ActionSubmission, ActionType
from deviation_protocol.domain.content import ContentCatalog
from deviation_protocol.domain.models import Inventory, NPC, Player
from deviation_protocol.domain.state import (
    AuthoritativeStateView,
    DomainErrorCode,
    DomainRuleViolation,
    GameState,
    PlayerState,
)
from deviation_protocol.infrastructure.content_loader import JsonContentCatalogLoader


CONTENT_PACK = Path(__file__).parents[2] / "config" / "demo_content_pack.json"


@pytest.fixture
def catalog() -> ContentCatalog:
    return JsonContentCatalogLoader(CONTENT_PACK).load()


@pytest.fixture
def state(catalog: ContentCatalog) -> GameState:
    character = catalog.character("character.player.default")
    assert character is not None
    return GameState(
        content_version=catalog.content_version,
        player=PlayerState.from_definition("player-1", character),
    )


def assert_code(exc_info: pytest.ExceptionInfo[DomainRuleViolation], code: DomainErrorCode) -> None:
    assert exc_info.value.code is code


def assert_failure_without_mutation(
    state: GameState,
    code: DomainErrorCode,
    operation: Callable[[], None],
) -> None:
    before = state.to_snapshot()
    with pytest.raises(DomainRuleViolation) as error:
        operation()
    assert_code(error, code)
    assert state.to_snapshot() == before


def test_snapshot_json_round_trip_is_stable(
    catalog: ContentCatalog, state: GameState
) -> None:
    state.credit_currency("credits", 125)
    sword_id = state.grant_item(
        catalog, "item.training_sword", instance_id="item-sword-1"
    )[0]
    state.equip(catalog, sword_id, "hand.main")
    state.learn_skill(catalog, "skill.observation")
    state.spawn_npc(catalog, "npc.demo.guard", "npc-session-guard")

    encoded = json.dumps(state.to_snapshot(), ensure_ascii=False, sort_keys=True)
    restored = GameState.from_snapshot(json.loads(encoded), catalog=catalog)

    assert restored == state
    assert restored.schema_version == 1
    assert restored.to_snapshot() == state.to_snapshot()


@pytest.mark.parametrize("schema_version", [2, True, 1.0])
def test_unknown_or_non_integer_snapshot_schema_is_rejected(
    state: GameState, schema_version: object
) -> None:
    payload = state.to_snapshot()
    payload["schema_version"] = schema_version

    with pytest.raises(ValidationError, match="schema_version"):
        GameState.from_snapshot(payload)


def test_snapshot_content_version_mismatch_is_rejected(
    catalog: ContentCatalog, state: GameState
) -> None:
    payload = state.to_snapshot()
    payload["content_version"] = "demo-2"

    with pytest.raises(DomainRuleViolation) as error:
        GameState.from_snapshot(payload, catalog=catalog)
    assert_code(error, DomainErrorCode.SNAPSHOT_CONTENT_MISMATCH)


def test_equivalent_states_have_deterministic_mysql_json_shape(
    catalog: ContentCatalog,
) -> None:
    character = catalog.character("character.player.default")
    assert character is not None
    first = GameState(
        content_version=catalog.content_version,
        player=PlayerState.from_definition("player-1", character),
    )
    second = GameState(
        content_version=catalog.content_version,
        player=PlayerState.from_definition("player-1", character),
    )
    first.credit_currency("zeta", 1)
    first.credit_currency("alpha", 2)
    second.credit_currency("alpha", 2)
    second.credit_currency("zeta", 1)
    first.spawn_npc(catalog, "npc.demo.guard", "npc-guard")
    second.spawn_npc(catalog, "npc.demo.guard", "npc-guard")
    first.npcs["npc-guard"].runtime_flags = frozenset({"zeta", "alpha"})
    second.npcs["npc-guard"].runtime_flags = frozenset({"alpha", "zeta"})

    first_snapshot = first.to_snapshot()
    second_snapshot = second.to_snapshot()

    assert first_snapshot == second_snapshot
    assert first_snapshot["npcs"]["npc-guard"]["runtime_flags"] == ["alpha", "zeta"]
    encoded = json.dumps(first_snapshot, ensure_ascii=False, allow_nan=False)
    assert json.loads(encoded) == first_snapshot

    def assert_no_float(value: object) -> None:
        assert not isinstance(value, float)
        if isinstance(value, dict):
            for nested in value.values():
                assert_no_float(nested)
        elif isinstance(value, list):
            for nested in value:
                assert_no_float(nested)

    assert_no_float(first_snapshot)


def test_invalid_snapshot_numbers_and_catalog_limits_are_rejected(
    catalog: ContentCatalog, state: GameState
) -> None:
    payload = state.to_snapshot()
    payload["player"]["wallet"]["balances"]["credits"] = -1
    with pytest.raises(ValidationError, match="greater than or equal to 0"):
        GameState.from_snapshot(payload)

    state.grant_item(catalog, "item.medkit", 1, instance_id="item-medkit")
    payload = state.to_snapshot()
    payload["player"]["inventory"]["items"]["item-medkit"]["quantity"] = 11
    with pytest.raises(DomainRuleViolation) as stack_error:
        GameState.from_snapshot(payload, catalog=catalog)
    assert_code(stack_error, DomainErrorCode.INVALID_SNAPSHOT_REFERENCE)


def test_snapshot_boundary_revalidates_nested_runtime_mutations(
    catalog: ContentCatalog, state: GameState
) -> None:
    state.player.wallet.balances["credits"] = -1
    with pytest.raises(ValidationError, match="greater than or equal to 0"):
        state.to_snapshot()

    character = catalog.character("character.player.default")
    assert character is not None
    duplicate_slot_state = GameState(
        content_version=catalog.content_version,
        player=PlayerState.from_definition("player-2", character),
    )
    first, second = duplicate_slot_state.grant_item(
        catalog, "item.training_sword", 2
    )
    first_equipment = duplicate_slot_state.player.inventory.items[first].equipment
    second_equipment = duplicate_slot_state.player.inventory.items[second].equipment
    assert first_equipment is not None and second_equipment is not None
    first_equipment.equipped_slot = "hand.main"
    second_equipment.equipped_slot = "hand.main"

    with pytest.raises(ValidationError, match="only one item"):
        duplicate_slot_state.to_snapshot()


def test_snapshot_catalog_validation_rejects_non_equipment_invalid_slot_and_skill_level(
    catalog: ContentCatalog, state: GameState
) -> None:
    mirror = state.grant_item(
        catalog, "item.mirror", instance_id="item-mirror"
    )[0]
    payload = state.to_snapshot()
    payload["player"]["inventory"]["items"][mirror]["equipment"] = {
        "enhancement_level": 0,
        "equipped_slot": "hand.main",
    }
    with pytest.raises(DomainRuleViolation) as equipment_error:
        GameState.from_snapshot(payload, catalog=catalog)
    assert_code(equipment_error, DomainErrorCode.INVALID_SNAPSHOT_REFERENCE)

    character = catalog.character("character.player.default")
    assert character is not None
    slot_state = GameState(
        content_version=catalog.content_version,
        player=PlayerState.from_definition("player-slot", character),
    )
    sword = slot_state.grant_item(
        catalog, "item.training_sword", instance_id="item-sword"
    )[0]
    payload = slot_state.to_snapshot()
    payload["player"]["inventory"]["items"][sword]["equipment"][
        "equipped_slot"
    ] = "body.back"
    with pytest.raises(DomainRuleViolation) as slot_error:
        GameState.from_snapshot(payload, catalog=catalog)
    assert_code(slot_error, DomainErrorCode.INVALID_SNAPSHOT_REFERENCE)

    skill_state = GameState(
        content_version=catalog.content_version,
        player=PlayerState.from_definition("player-2", character),
    )
    skill_state.learn_skill(catalog, "skill.observation")
    payload = skill_state.to_snapshot()
    payload["player"]["skills"]["skill.observation"]["level"] = 3
    with pytest.raises(DomainRuleViolation) as skill_error:
        GameState.from_snapshot(payload, catalog=catalog)
    assert_code(skill_error, DomainErrorCode.INVALID_SNAPSHOT_REFERENCE)


def test_stackable_items_fill_stacks_and_remove_quantities(
    catalog: ContentCatalog, state: GameState
) -> None:
    first_ids = state.grant_item(catalog, "item.medkit", 12)
    assert sorted(
        item.quantity for item in state.player.inventory.items.values()
    ) == [2, 10]

    second_ids = state.grant_item(catalog, "item.medkit", 3)
    assert second_ids == (first_ids[1],)
    assert sorted(
        item.quantity for item in state.player.inventory.items.values()
    ) == [5, 10]

    state.remove_item(first_ids[1], 2)
    assert state.player.inventory.items[first_ids[1]].quantity == 3
    state.remove_item(first_ids[1], 3)
    assert first_ids[1] not in state.player.inventory.items


def test_non_stackable_items_have_unique_instance_ids(
    catalog: ContentCatalog, state: GameState
) -> None:
    instance_ids = state.grant_item(catalog, "item.mirror", 2)

    assert len(instance_ids) == 2
    assert len(set(instance_ids)) == 2
    assert all(
        state.player.inventory.items[instance_id].quantity == 1
        for instance_id in instance_ids
    )


def test_unknown_item_skill_and_npc_definitions_are_rejected(
    catalog: ContentCatalog, state: GameState
) -> None:
    assert_failure_without_mutation(
        state,
        DomainErrorCode.UNKNOWN_ITEM_DEFINITION,
        lambda: state.grant_item(catalog, "item.missing"),
    )
    assert_failure_without_mutation(
        state,
        DomainErrorCode.UNKNOWN_SKILL_DEFINITION,
        lambda: state.learn_skill(catalog, "skill.missing"),
    )
    assert_failure_without_mutation(
        state,
        DomainErrorCode.UNKNOWN_NPC_DEFINITION,
        lambda: state.spawn_npc(catalog, "npc.missing", "npc-1"),
    )


def test_failed_grant_and_remove_operations_are_atomic(
    catalog: ContentCatalog, state: GameState
) -> None:
    medkit = state.grant_item(
        catalog, "item.medkit", 3, instance_id="item-medkit"
    )[0]
    assert_failure_without_mutation(
        state,
        DomainErrorCode.DUPLICATE_ITEM_INSTANCE,
        lambda: state.grant_item(
            catalog, "item.medkit", instance_id="item-medkit"
        ),
    )
    assert_failure_without_mutation(
        state,
        DomainErrorCode.STACK_LIMIT_EXCEEDED,
        lambda: state.grant_item(
            catalog, "item.medkit", 11, instance_id="item-overflow"
        ),
    )
    assert_failure_without_mutation(
        state,
        DomainErrorCode.INVALID_IDENTIFIER,
        lambda: state.grant_item(
            catalog, "item.medkit", instance_id="invalid instance id"
        ),
    )
    assert_failure_without_mutation(
        state,
        DomainErrorCode.INVALID_AMOUNT,
        lambda: state.remove_item(medkit, 4),
    )


def test_equipment_slot_conflict_does_not_change_second_item(
    catalog: ContentCatalog, state: GameState
) -> None:
    first = state.grant_item(
        catalog, "item.training_sword", instance_id="item-sword-1"
    )[0]
    second = state.grant_item(
        catalog, "item.training_sword", instance_id="item-sword-2"
    )[0]
    state.equip(catalog, first, "hand.main")
    assert_failure_without_mutation(
        state,
        DomainErrorCode.SLOT_OCCUPIED,
        lambda: state.equip(catalog, second, "hand.main"),
    )
    assert state.player.inventory.items[first].equipment.equipped_slot == "hand.main"  # type: ignore[union-attr]
    assert state.player.inventory.items[second].equipment.equipped_slot is None  # type: ignore[union-attr]


def test_equipment_requirements_equip_and_unequip(
    catalog: ContentCatalog, state: GameState
) -> None:
    sword = state.grant_item(
        catalog, "item.training_sword", instance_id="item-sword"
    )[0]
    state.player.attributes["strength"] = 2
    assert_failure_without_mutation(
        state,
        DomainErrorCode.EQUIPMENT_REQUIREMENT_NOT_MET,
        lambda: state.equip(catalog, sword, "hand.main"),
    )
    assert state.player.inventory.items[sword].equipment.equipped_slot is None  # type: ignore[union-attr]

    state.player.attributes["strength"] = 3
    state.equip(catalog, sword, "hand.main")
    assert state.player.inventory.items[sword].equipment.equipped_slot == "hand.main"  # type: ignore[union-attr]
    state.unequip(sword)
    assert state.player.inventory.items[sword].equipment.equipped_slot is None  # type: ignore[union-attr]


def test_equipment_membership_slot_and_broken_item_rejections_are_atomic(
    catalog: ContentCatalog, state: GameState
) -> None:
    sword = state.grant_item(
        catalog, "item.training_sword", instance_id="item-sword"
    )[0]
    mirror = state.grant_item(catalog, "item.mirror", instance_id="item-mirror")[0]

    assert_failure_without_mutation(
        state,
        DomainErrorCode.UNKNOWN_ITEM_INSTANCE,
        lambda: state.equip(catalog, "item-not-owned", "hand.main"),
    )
    assert_failure_without_mutation(
        state,
        DomainErrorCode.NOT_EQUIPMENT,
        lambda: state.equip(catalog, mirror, "hand.main"),
    )
    assert_failure_without_mutation(
        state,
        DomainErrorCode.SLOT_NOT_ALLOWED,
        lambda: state.equip(catalog, sword, "body.back"),
    )
    assert_failure_without_mutation(
        state,
        DomainErrorCode.NOT_EQUIPPED,
        lambda: state.unequip(sword),
    )
    assert_failure_without_mutation(
        state,
        DomainErrorCode.UNKNOWN_ITEM_INSTANCE,
        lambda: state.unequip("item-not-owned"),
    )

    state.set_durability(catalog, sword, 0)
    assert_failure_without_mutation(
        state,
        DomainErrorCode.BROKEN_EQUIPMENT,
        lambda: state.equip(catalog, sword, "hand.main"),
    )


def test_equipment_that_reaches_zero_durability_remains_equipped_until_unequipped(
    catalog: ContentCatalog, state: GameState
) -> None:
    sword = state.grant_item(
        catalog, "item.training_sword", instance_id="item-sword"
    )[0]
    state.equip(catalog, sword, "hand.main")
    state.damage_item(catalog, sword, 100)

    equipment = state.player.inventory.items[sword].equipment
    assert equipment is not None
    assert equipment.equipped_slot == "hand.main"
    assert state.player.inventory.items[sword].durability == 0
    state.unequip(sword)
    assert_failure_without_mutation(
        state,
        DomainErrorCode.BROKEN_EQUIPMENT,
        lambda: state.equip(catalog, sword, "hand.main"),
    )


def test_equipment_slot_must_exist_on_player_character(
    catalog: ContentCatalog, state: GameState
) -> None:
    payload = catalog.model_dump(mode="json")
    payload["equipment"][0]["allowed_slots"] = ["body.back"]
    catalog_with_foreign_slot = ContentCatalog.model_validate(payload)
    sword = state.grant_item(
        catalog_with_foreign_slot,
        "item.training_sword",
        instance_id="item-sword",
    )[0]

    assert_failure_without_mutation(
        state,
        DomainErrorCode.SLOT_NOT_ALLOWED,
        lambda: state.equip(
            catalog_with_foreign_slot, sword, "body.back"
        ),
    )


def test_same_equipment_instance_moves_between_slots_without_duplicate_occupancy(
    catalog: ContentCatalog, state: GameState
) -> None:
    sword = state.grant_item(
        catalog, "item.training_sword", instance_id="item-sword"
    )[0]
    state.equip(catalog, sword, "hand.main")
    state.equip(catalog, sword, "hand.off")

    equipment = state.player.inventory.items[sword].equipment
    assert equipment is not None
    assert equipment.equipped_slot == "hand.off"


def test_removing_equipped_item_is_explicitly_rejected_without_mutation(
    catalog: ContentCatalog, state: GameState
) -> None:
    sword = state.grant_item(
        catalog, "item.training_sword", instance_id="item-sword"
    )[0]
    state.equip(catalog, sword, "hand.main")

    assert_failure_without_mutation(
        state,
        DomainErrorCode.ITEM_EQUIPPED,
        lambda: state.remove_item(sword),
    )


def test_durability_stays_within_integer_boundaries(
    catalog: ContentCatalog, state: GameState
) -> None:
    sword = state.grant_item(
        catalog, "item.training_sword", instance_id="item-sword"
    )[0]
    state.damage_item(catalog, sword, 250)
    assert state.player.inventory.items[sword].durability == 0
    state.repair_item(catalog, sword, 250)
    assert state.player.inventory.items[sword].durability == 100

    assert_failure_without_mutation(
        state,
        DomainErrorCode.DURABILITY_OUT_OF_RANGE,
        lambda: state.set_durability(catalog, sword, -1),
    )
    assert_failure_without_mutation(
        state,
        DomainErrorCode.DURABILITY_OUT_OF_RANGE,
        lambda: state.set_durability(catalog, sword, 101),
    )
    assert state.player.inventory.items[sword].durability == 100


def test_skill_learning_upgrade_prerequisites_and_max_level(
    catalog: ContentCatalog, state: GameState
) -> None:
    assert_failure_without_mutation(
        state,
        DomainErrorCode.SKILL_NOT_LEARNED,
        lambda: state.upgrade_skill(catalog, "skill.observation"),
    )
    state.learn_skill(catalog, "skill.observation")
    state.credit_currency("credits", 10)
    assert_failure_without_mutation(
        state,
        DomainErrorCode.SKILL_ALREADY_LEARNED,
        lambda: state.learn_skill(catalog, "skill.observation"),
    )
    assert_failure_without_mutation(
        state,
        DomainErrorCode.SKILL_PREREQUISITE_NOT_MET,
        lambda: state.learn_skill(catalog, "skill.precision"),
    )
    assert "skill.precision" not in state.player.skills

    state.upgrade_skill(catalog, "skill.observation")
    state.learn_skill(catalog, "skill.precision")
    assert state.player.skills["skill.precision"].level == 1

    assert_failure_without_mutation(
        state,
        DomainErrorCode.SKILL_MAX_LEVEL,
        lambda: state.upgrade_skill(catalog, "skill.observation"),
    )
    assert state.player.skills["skill.observation"].level == 2


def test_insufficient_balance_and_resource_leave_state_unchanged(
    state: GameState,
) -> None:
    state.credit_currency("credits", 5)
    before = state.to_snapshot()

    with pytest.raises(DomainRuleViolation) as balance_error:
        state.debit_currency("credits", 6)
    assert_code(balance_error, DomainErrorCode.INSUFFICIENT_FUNDS)
    with pytest.raises(DomainRuleViolation) as resource_error:
        state.consume_resource("stamina", 11)
    assert_code(resource_error, DomainErrorCode.INSUFFICIENT_RESOURCE)

    assert state.to_snapshot() == before


def test_invalid_runtime_identifiers_are_rejected_without_mutation(
    catalog: ContentCatalog, state: GameState
) -> None:
    assert_failure_without_mutation(
        state,
        DomainErrorCode.INVALID_IDENTIFIER,
        lambda: state.credit_currency("invalid currency", 1),
    )
    assert_failure_without_mutation(
        state,
        DomainErrorCode.INVALID_IDENTIFIER,
        lambda: state.spawn_npc(
            catalog, "npc.demo.guard", "invalid npc id"
        ),
    )


def test_currency_and_resource_mutations_obey_boundaries(state: GameState) -> None:
    state.credit_currency("credits", 10)
    state.debit_currency("credits", 4)
    state.consume_resource("stamina", 3)
    state.restore_resource("stamina", 100)

    assert state.player.wallet.balances["credits"] == 6
    assert state.player.resources["stamina"].current == 10


def test_authoritative_view_queries_real_state(
    catalog: ContentCatalog, state: GameState
) -> None:
    sword = state.grant_item(
        catalog, "item.training_sword", instance_id="item-sword"
    )[0]
    state.equip(catalog, sword, "hand.main")
    state.learn_skill(catalog, "skill.observation")
    state.spawn_npc(catalog, "npc.demo.guard", "npc-session-guard")
    view = AuthoritativeStateView(state, catalog)

    assert view.has_item_instance(sword)
    assert view.owns_equipment(sword)
    assert view.is_equipped(sword)
    assert view.has_skill("skill.observation")
    assert view.npc_exists("npc-session-guard")
    assert not view.npc_exists("npc-invented")
    assert view.has_resource("stamina", 10)
    assert not view.has_resource("stamina", 11)
    assert not view.has_item_instance("item.training_sword")
    assert not view.owns_equipment("item.training_sword")
    assert not view.has_skill("skill.missing")
    assert not view.has_currency("credits", 0)


def test_authoritative_view_is_a_detached_immutable_projection(
    catalog: ContentCatalog, state: GameState
) -> None:
    view = AuthoritativeStateView(state, catalog)

    assert not hasattr(view, "state")
    assert not hasattr(view, "catalog")
    assert isinstance(view.inventory_item_instance_ids, frozenset)
    with pytest.raises(FrozenInstanceError):
        view._npc_ids = frozenset({"npc-injected"})  # type: ignore[misc]

    state.grant_item(catalog, "item.mirror", instance_id="item-after-view")
    assert not view.has_item_instance("item-after-view")
    assert AuthoritativeStateView(state, catalog).has_item_instance("item-after-view")


def test_text_claim_does_not_grant_an_item(
    catalog: ContentCatalog, state: GameState
) -> None:
    submission = ActionSubmission(
        session_id="session-1",
        turn_id="turn-1",
        client_request_id="request-1",
        action_type=ActionType.CUSTOM,
        tool_ids=("item-imaginary-laser",),
        description="我有一把激光枪，我尝试用它切开门。",
    )
    view = AuthoritativeStateView(state, catalog)
    context = ActionContext(
        submission=submission,
        current_turn_id="turn-1",
        inventory_item_ids=view.inventory_item_instance_ids,
    )

    result = ActionGateway.from_config().evaluate(context)

    assert result.route is ActionRoute.REJECT_LOCAL
    assert result.policy_trace[-1].reason_code == "unavailable_tool"
    assert not view.has_item_instance("item-imaginary-laser")


def test_action_context_projection_uses_instance_ids_not_definition_ids(
    catalog: ContentCatalog, state: GameState
) -> None:
    state.grant_item(catalog, "item.mirror", instance_id="item-mirror-instance")
    submission = ActionSubmission(
        session_id="session-1",
        turn_id="turn-1",
        client_request_id="request-definition-id",
        action_type=ActionType.CUSTOM,
        tool_ids=("item.mirror",),
        description="我尝试使用镜子观察门后。",
    )
    view = AuthoritativeStateView(state, catalog)
    result = ActionGateway.from_config().evaluate(
        ActionContext(
            submission=submission,
            current_turn_id="turn-1",
            inventory_item_ids=view.inventory_item_instance_ids,
        )
    )

    assert result.route is ActionRoute.REJECT_LOCAL
    assert result.policy_trace[-1].reason_code == "unavailable_tool"


def test_legacy_model_imports_keep_their_original_constructor_semantics() -> None:
    player = Player("legacy-player", {"strength": 1})
    npc = NPC("legacy-npc", "旧 NPC", {"alert": True})
    inventory = Inventory("legacy-player", {"legacy-item"})

    assert player.attributes == {"strength": 1}
    assert npc.name == "旧 NPC"
    assert npc.state == {"alert": True}
    assert inventory.item_ids == {"legacy-item"}
