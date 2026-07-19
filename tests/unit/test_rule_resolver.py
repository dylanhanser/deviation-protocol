from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from deviation_protocol.application.action_context import (
    AuthoritativeActionContextFactory,
    SkillLearningAuthorization,
    SkillLearningAuthorizationSource,
    TrustedResolutionContext,
)
from deviation_protocol.application.action_gateway import (
    ActionGateway,
    ActionRoute,
    GatewayResult,
)
from deviation_protocol.application.effect_executor import (
    DeterministicEffectExecutor,
    EffectSourceType,
)
from deviation_protocol.application.resolution import (
    PlayerFeedback,
    ResolutionResult,
    ResolutionStatus,
)
from deviation_protocol.application.rule_resolver import DeterministicRuleResolver
from deviation_protocol.domain.actions import ActionContext, ActionSubmission, ActionType
from deviation_protocol.domain.content import ContentCatalog
from deviation_protocol.domain.events import DomainEventDraft
from deviation_protocol.domain.facts import NarrativeFact, NarrativeFactKind
from deviation_protocol.domain.state import AuthoritativeStateView, GameState, PlayerState
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


def submission(action_type: ActionType, **overrides: object) -> ActionSubmission:
    values: dict[str, object] = {
        "session_id": "session-1",
        "turn_id": "turn-1",
        "client_request_id": f"request-{action_type.value.lower()}",
        "action_type": action_type,
    }
    values.update(overrides)
    return ActionSubmission(**values)


def project(
    action: ActionSubmission,
    state: GameState,
    catalog: ContentCatalog,
    **overrides: object,
):
    return AuthoritativeActionContextFactory().create_trusted(
        action,
        state=state,
        catalog=catalog,
        authoritative_view=AuthoritativeStateView(state, catalog),
        **overrides,
    )


def learning_authorization(catalog: ContentCatalog, *skill_ids: str):
    return AuthoritativeActionContextFactory().issue_skill_learning_authorization(
        skill_ids,
        catalog=catalog,
        source=SkillLearningAuthorizationSource.PERSISTED_FACT,
        source_id="fact.skill-learning-opportunity",
    )


async def resolve(
    action: ActionSubmission,
    state: GameState,
    catalog: ContentCatalog,
    **context_overrides: object,
):
    trusted_context = project(action, state, catalog, **context_overrides)
    gateway_result = ActionGateway.from_config().evaluate(
        trusted_context.action_context
    )
    result = await DeterministicRuleResolver().resolve(
        trusted_context, state, catalog
    )
    return gateway_result, result


def test_authoritative_context_projects_distinct_identity_namespaces(
    catalog: ContentCatalog, state: GameState
) -> None:
    state.grant_item(catalog, "item.training_sword", instance_id="sword-instance-1")
    state.learn_skill(catalog, "skill.observation")
    state.spawn_npc(catalog, "npc.demo.guard", "npc-runtime-guard")
    action = submission(ActionType.INSPECT_STATUS)

    context = project(action, state, catalog).action_context

    assert context.inventory_item_ids == frozenset({"sword-instance-1"})
    assert context.item_definition_by_instance == (
        ("sword-instance-1", "item.training_sword"),
    )
    assert context.equipment_definition_by_instance == (
        ("sword-instance-1", "equipment.training_sword"),
    )
    assert context.learned_skill_levels == (("skill.observation", 1),)
    assert context.npc_definition_by_id == (
        ("npc-runtime-guard", "npc.demo.guard"),
    )
    assert "item.training_sword" not in context.inventory_item_ids
    assert "npc.demo.guard" not in context.visible_entity_ids
    assert "npc-runtime-guard" not in context.visible_entity_ids


def test_context_rejects_definition_id_as_runtime_npc_id(
    catalog: ContentCatalog, state: GameState
) -> None:
    action = submission(ActionType.TALK, dialogue="你好", target_ids=("npc.demo.guard",))
    with pytest.raises(ValueError, match="definition IDs"):
        project(action, state, catalog, visible_entity_ids=("npc.demo.guard",))


def test_context_rejects_static_definition_id_as_environment_runtime_tool(
    catalog: ContentCatalog, state: GameState
) -> None:
    action = submission(ActionType.INSPECT_STATUS)

    with pytest.raises(ValueError, match="static definition IDs"):
        project(action, state, catalog, environment_tool_ids=("item.mirror",))


@pytest.mark.asyncio
async def test_plain_context_is_rejected_by_resolver_even_if_gateway_would_resolve(
    catalog: ContentCatalog, state: GameState
) -> None:
    action = submission(
        ActionType.LEARN_SKILL, skill_definition_id="skill.observation"
    )
    forged_context = ActionContext(
        submission=action,
        current_turn_id=action.turn_id,
        available_skill_definition_ids=frozenset({"skill.observation"}),
    )
    before = state.to_snapshot()
    gateway_result = ActionGateway.from_config().evaluate(forged_context)

    result = await DeterministicRuleResolver().resolve(
        forged_context, state, catalog
    )

    assert gateway_result.route is ActionRoute.RESOLVE_LOCAL
    assert result.status is ResolutionStatus.REJECTED_LOCAL
    assert result.result_code == "UNTRUSTED_RESOLUTION_CONTEXT"
    assert state.to_snapshot() == before


def test_ordinary_action_context_rejects_learning_authorization_fields() -> None:
    action = submission(
        ActionType.LEARN_SKILL, skill_definition_id="skill.observation"
    )

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ActionContext(
            submission=action,
            current_turn_id=action.turn_id,
            learnable_skill_definition_ids=frozenset({"skill.observation"}),
        )


def test_serializable_data_cannot_construct_trusted_capabilities() -> None:
    forged_authorization = SkillLearningAuthorization()
    forged_context = TrustedResolutionContext()

    assert forged_authorization.is_authentic() is False
    assert not hasattr(forged_context, "action_context")


@pytest.mark.asyncio
async def test_forged_gateway_route_is_not_a_resolver_input(
    catalog: ContentCatalog, state: GameState
) -> None:
    state.grant_item(catalog, "item.training_sword", instance_id="sword-1")
    action = submission(
        ActionType.EQUIP,
        item_instance_id="sword-1",
        equipment_slot_id="hand.main",
    )
    trusted_context = project(action, state, catalog)
    forged_decision = GatewayResult(
        route=ActionRoute.RESOLVE_LOCAL,
        action_signature=action.action_signature(),
        policy_trace=(),
    )
    before = state.to_snapshot()

    with pytest.raises(TypeError):
        await DeterministicRuleResolver().resolve(  # type: ignore[call-arg]
            trusted_context,
            forged_decision,
            state,
            catalog,
        )

    assert state.to_snapshot() == before


@pytest.mark.asyncio
async def test_trusted_context_is_detached_immutable_and_state_bound(
    catalog: ContentCatalog, state: GameState
) -> None:
    state.grant_item(catalog, "item.mirror", instance_id="mirror-before")
    action = submission(ActionType.INSPECT_INVENTORY)
    trusted_context = project(action, state, catalog)
    context = trusted_context.action_context

    state.grant_item(catalog, "item.medkit", instance_id="medkit-after")

    assert context.inventory_item_ids == frozenset({"mirror-before"})
    with pytest.raises(AttributeError):
        context.inventory_item_ids.add("injected")  # type: ignore[attr-defined]
    with pytest.raises(ValidationError, match="frozen"):
        context.submission.action_type = ActionType.LEARN_SKILL

    result = await DeterministicRuleResolver().resolve(
        trusted_context, state, catalog
    )
    assert result.result_code == "TRUSTED_CONTEXT_STATE_MISMATCH"


@pytest.mark.asyncio
async def test_definition_id_cannot_stand_in_for_owned_item_instance(
    catalog: ContentCatalog, state: GameState
) -> None:
    state.grant_item(catalog, "item.training_sword", instance_id="sword-instance-1")
    action = submission(
        ActionType.EQUIP,
        item_instance_id="item.training_sword",
        equipment_slot_id="hand.main",
    )

    gateway_result, result = await resolve(action, state, catalog)

    assert gateway_result.route is ActionRoute.REJECT_LOCAL
    assert result.status is ResolutionStatus.REJECTED_LOCAL
    assert result.result_code == "UNAVAILABLE_TOOL"


@pytest.mark.asyncio
async def test_text_claim_does_not_create_authoritative_asset(
    catalog: ContentCatalog, state: GameState
) -> None:
    action = submission(
        ActionType.CUSTOM,
        description="我有一把并不存在的激光枪，尝试用它切开门。",
        tool_ids=("imaginary-laser-instance",),
    )

    gateway_result, result = await resolve(action, state, catalog)

    assert gateway_result.route is ActionRoute.REJECT_LOCAL
    assert result.result_code == "UNAVAILABLE_TOOL"
    assert "imaginary-laser-instance" not in state.player.inventory.items


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "action_type",
    [
        ActionType.INSPECT_STATUS,
        ActionType.INSPECT_INVENTORY,
        ActionType.INSPECT_EQUIPMENT,
        ActionType.INSPECT_SKILLS,
        ActionType.INSPECT_RESOURCES,
        ActionType.INSPECT_CURRENCIES,
    ],
)
async def test_authoritative_queries_resolve_locally_without_narrative_provider(
    action_type: ActionType, catalog: ContentCatalog, state: GameState
) -> None:
    narrative_provider = AsyncMock()
    before = state.to_snapshot()

    gateway_result, result = await resolve(submission(action_type), state, catalog)
    if result.status is ResolutionStatus.NARRATIVE_REQUIRED:
        await narrative_provider.generate({})

    assert gateway_result.route is ActionRoute.RESOLVE_LOCAL
    assert result.status is ResolutionStatus.RESOLVED_LOCAL
    assert result.success is True
    assert result.updated_state is None
    assert result.events == ()
    assert state.to_snapshot() == before
    narrative_provider.generate.assert_not_awaited()


@pytest.mark.asyncio
async def test_query_feedback_and_fact_are_detached_immutable_json_values(
    catalog: ContentCatalog, state: GameState
) -> None:
    _, result = await resolve(
        submission(ActionType.INSPECT_STATUS), state, catalog
    )

    assert result.facts[0].kind is NarrativeFactKind.QUERY_RESULT
    assert result.facts[0].value is not result.feedback.parameters
    assert json.loads(json.dumps(result.feedback.parameters))["player_id"] == "player-1"
    with pytest.raises(TypeError, match="frozen JSON"):
        result.feedback.parameters["player_id"] = "tampered"
    assert result.facts[0].value["player_id"] == "player-1"


@pytest.mark.asyncio
async def test_unimplemented_quest_query_returns_an_explicit_empty_placeholder(
    catalog: ContentCatalog, state: GameState
) -> None:
    gateway_result, result = await resolve(
        submission(ActionType.INSPECT_QUESTS), state, catalog
    )

    assert gateway_result.route is ActionRoute.RESOLVE_LOCAL
    assert result.result_code == "QUESTS_INSPECTED"
    assert result.feedback.parameters["quests"] == ()
    assert result.events == ()


@pytest.mark.asyncio
async def test_equip_and_unequip_return_candidate_state_and_structured_events(
    catalog: ContentCatalog, state: GameState
) -> None:
    state.grant_item(catalog, "item.training_sword", instance_id="sword-1")
    equip_action = submission(
        ActionType.EQUIP,
        item_instance_id="sword-1",
        equipment_slot_id="hand.main",
    )

    _, equipped = await resolve(equip_action, state, catalog)

    assert equipped.result_code == "ITEM_EQUIPPED"
    assert equipped.updated_state is not None
    assert state.player.inventory.items["sword-1"].equipment.equipped_slot is None  # type: ignore[union-attr]
    assert equipped.updated_state.player.inventory.items[
        "sword-1"
    ].equipment.equipped_slot == "hand.main"  # type: ignore[union-attr]
    assert [event.event_type for event in equipped.events] == ["ItemEquipped"]

    unequip_action = submission(
        ActionType.UNEQUIP,
        client_request_id="request-unequip-2",
        item_instance_id="sword-1",
    )
    _, unequipped = await resolve(unequip_action, equipped.updated_state, catalog)
    assert unequipped.result_code == "ITEM_UNEQUIPPED"
    assert unequipped.updated_state is not None
    assert unequipped.updated_state.player.inventory.items[
        "sword-1"
    ].equipment.equipped_slot is None  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_candidate_state_has_no_nested_mutable_aliases_with_original(
    catalog: ContentCatalog, state: GameState
) -> None:
    state.grant_item(catalog, "item.training_sword", instance_id="sword-isolated")
    state.spawn_npc(catalog, "npc.demo.guard", "npc-runtime-isolated")
    action = submission(
        ActionType.EQUIP,
        item_instance_id="sword-isolated",
        equipment_slot_id="hand.main",
    )

    _, result = await resolve(action, state, catalog)
    candidate = result.updated_state
    assert candidate is not None
    original_item = state.player.inventory.items["sword-isolated"]
    candidate_item = candidate.player.inventory.items["sword-isolated"]

    assert candidate.player is not state.player
    assert candidate.player.inventory is not state.player.inventory
    assert candidate.player.inventory.items is not state.player.inventory.items
    assert candidate_item is not original_item
    assert candidate_item.equipment is not original_item.equipment
    assert candidate.player.resources["stamina"] is not state.player.resources["stamina"]
    assert candidate.npcs is not state.npcs
    assert candidate.npcs["npc-runtime-isolated"] is not state.npcs[
        "npc-runtime-isolated"
    ]

    candidate.player.attributes["focus"] = 999
    candidate_item.durability = 1
    assert state.player.attributes["focus"] == 4
    assert original_item.durability == 100

    state.player.resources["stamina"].current = 2
    assert candidate.player.resources["stamina"].current == 10


@pytest.mark.asyncio
async def test_unknown_owned_instance_and_broken_equipment_are_rejected_atomically(
    catalog: ContentCatalog, state: GameState
) -> None:
    missing = submission(
        ActionType.EQUIP,
        item_instance_id="missing-instance",
        equipment_slot_id="hand.main",
    )
    _, missing_result = await resolve(missing, state, catalog)
    assert missing_result.result_code == "UNAVAILABLE_TOOL"

    state.grant_item(catalog, "item.training_sword", instance_id="sword-broken")
    state.set_durability(catalog, "sword-broken", 0)
    before = state.to_snapshot()
    broken = submission(
        ActionType.EQUIP,
        client_request_id="request-broken",
        item_instance_id="sword-broken",
        equipment_slot_id="hand.main",
    )
    _, broken_result = await resolve(broken, state, catalog)
    assert broken_result.result_code == "BROKEN_EQUIPMENT"
    assert broken_result.events == ()
    assert state.to_snapshot() == before


@pytest.mark.asyncio
async def test_consumable_quantity_decrements_and_instance_is_removed_consistently(
    catalog: ContentCatalog, state: GameState
) -> None:
    state.grant_item(catalog, "item.medkit", 2, instance_id="medkit-stack")
    use = submission(ActionType.USE_ITEM, item_instance_id="medkit-stack")

    _, first = await resolve(use, state, catalog)

    assert first.updated_state is not None
    assert first.updated_state.player.inventory.items["medkit-stack"].quantity == 1
    assert first.events[0].payload["remaining_charges"] is None
    assert state.player.inventory.items["medkit-stack"].quantity == 2

    second_action = submission(
        ActionType.USE_ITEM,
        client_request_id="request-use-item-2",
        item_instance_id="medkit-stack",
    )
    _, second = await resolve(second_action, first.updated_state, catalog)
    assert second.updated_state is not None
    assert "medkit-stack" not in second.updated_state.player.inventory.items
    assert second.events[0].payload["remaining_quantity"] == 0


@pytest.mark.asyncio
async def test_non_consumable_and_equipped_consumable_are_not_consumed(
    catalog: ContentCatalog, state: GameState
) -> None:
    state.grant_item(catalog, "item.mirror", instance_id="mirror-1")
    before = state.to_snapshot()
    _, result = await resolve(
        submission(ActionType.USE_ITEM, item_instance_id="mirror-1"), state, catalog
    )
    assert result.result_code == "ITEM_NOT_CONSUMABLE"
    assert result.events == ()
    assert state.to_snapshot() == before

    payload = catalog.model_dump(mode="json")
    payload["items"][1]["tags"].append("consumable")
    consumable_equipment_catalog = ContentCatalog.model_validate(payload)
    equipped_state = GameState.from_snapshot(state.to_snapshot())
    equipped_state.grant_item(
        consumable_equipment_catalog,
        "item.training_sword",
        instance_id="consumable-sword",
    )
    equipped_state.equip(
        consumable_equipment_catalog, "consumable-sword", "hand.main"
    )
    equipped_before = equipped_state.to_snapshot()
    _, equipped_result = await resolve(
        submission(
            ActionType.USE_ITEM,
            client_request_id="request-equipped-consumable",
            item_instance_id="consumable-sword",
        ),
        equipped_state,
        consumable_equipment_catalog,
    )
    assert equipped_result.result_code == "ITEM_EQUIPPED"
    assert equipped_state.to_snapshot() == equipped_before


@pytest.mark.asyncio
async def test_charged_consumable_is_removed_exactly_when_last_charge_is_used(
    catalog: ContentCatalog, state: GameState
) -> None:
    payload = catalog.model_dump(mode="json")
    payload["items"].append(
        {
            "definition_id": "item.charged_tonic",
            "display_name": "充能测试剂",
            "stack_limit": 1,
            "max_charges": 2,
            "tags": ["consumable"],
        }
    )
    charged_catalog = ContentCatalog.model_validate(payload)
    state.grant_item(
        charged_catalog, "item.charged_tonic", instance_id="charged-tonic-1"
    )
    action = submission(ActionType.USE_ITEM, item_instance_id="charged-tonic-1")

    _, first = await resolve(action, state, charged_catalog)
    assert first.updated_state is not None
    assert first.updated_state.player.inventory.items[
        "charged-tonic-1"
    ].charges == 1

    second_action = submission(
        ActionType.USE_ITEM,
        client_request_id="request-charged-tonic-2",
        item_instance_id="charged-tonic-1",
    )
    _, second = await resolve(second_action, first.updated_state, charged_catalog)
    assert second.updated_state is not None
    assert "charged-tonic-1" not in second.updated_state.player.inventory.items
    assert second.events[0].payload["remaining_charges"] == 0


@pytest.mark.asyncio
async def test_skill_must_be_learned_and_have_sufficient_resources(
    catalog: ContentCatalog, state: GameState
) -> None:
    use = submission(ActionType.USE_SKILL, skill_definition_id="skill.observation")
    _, unlearned = await resolve(use, state, catalog)
    assert unlearned.result_code == "SKILL_NOT_LEARNED"

    state.learn_skill(catalog, "skill.observation")
    state.player.resources["stamina"].current = 1
    before = state.to_snapshot()
    _, insufficient = await resolve(use, state, catalog)
    assert insufficient.result_code == "INSUFFICIENT_RESOURCE"
    assert insufficient.events == ()
    assert state.to_snapshot() == before


@pytest.mark.asyncio
async def test_skill_effects_costs_and_usage_apply_in_stable_order(
    catalog: ContentCatalog, state: GameState
) -> None:
    state.learn_skill(catalog, "skill.observation")
    use = submission(ActionType.USE_SKILL, skill_definition_id="skill.observation")

    _, result = await resolve(use, state, catalog)

    assert result.result_code == "SKILL_USED"
    assert result.updated_state is not None
    assert result.updated_state.player.resources["stamina"].current == 8
    assert result.updated_state.player.skills["skill.observation"].uses == 1
    assert (
        result.updated_state.player.skills["skill.observation"]
        is not state.player.skills["skill.observation"]
    )
    result.updated_state.player.skills["skill.observation"].proficiency = 7
    assert state.player.skills["skill.observation"].proficiency == 0
    assert state.player.resources["stamina"].current == 10
    assert [event.event_type for event in result.events] == [
        "SkillResourceSpent",
        "PlayerResourceChanged",
        "SkillUsed",
    ]
    assert [fact.key for fact in result.facts] == [
        "player.resource.stamina.current",
        "player.resource.stamina.current",
        "player.skill.skill.observation.uses",
    ]


@pytest.mark.asyncio
async def test_later_effect_failure_rolls_back_cost_and_earlier_effect(
    catalog: ContentCatalog, state: GameState
) -> None:
    payload = catalog.model_dump(mode="json")
    payload["effects"].extend(
        [
            {
                "definition_id": "effect.test.recover",
                "effect_type": "RESOURCE_MODIFIER",
                "resource_id": "stamina",
                "delta": 1,
            },
            {
                "definition_id": "effect.test.exhaust",
                "effect_type": "RESOURCE_MODIFIER",
                "resource_id": "stamina",
                "delta": -99,
            },
        ]
    )
    payload["skills"][0]["effect_definition_ids"] = [
        "effect.test.recover",
        "effect.test.exhaust",
    ]
    failing_catalog = ContentCatalog.model_validate(payload)
    state.learn_skill(failing_catalog, "skill.observation")
    before = state.to_snapshot()

    _, result = await resolve(
        submission(ActionType.USE_SKILL, skill_definition_id="skill.observation"),
        state,
        failing_catalog,
    )

    assert result.result_code == "INSUFFICIENT_RESOURCE"
    assert result.updated_state is None
    assert result.events == ()
    assert result.facts == ()
    assert state.to_snapshot() == before


def test_unsupported_effect_fails_explicitly_without_mutation(
    catalog: ContentCatalog, state: GameState
) -> None:
    before = state.to_snapshot()
    unsupported = SimpleNamespace(
        definition_id="effect.combat.damage", effect_type="DAMAGE"
    )

    result = DeterministicEffectExecutor().execute_definitions(
        state,
        catalog,
        (unsupported,),
        source_type=EffectSourceType.SKILL,
        source_id="skill.test",
    )

    assert result.success is False
    assert result.result_code == "UNSUPPORTED_EFFECT"
    assert result.events == ()
    assert state.to_snapshot() == before


def test_uncatalogued_or_modified_effect_definition_cannot_execute(
    catalog: ContentCatalog, state: GameState
) -> None:
    injected = catalog.effects[-1].model_copy(
        update={"definition_id": "effect.player.injected", "delta": 999}
    )
    modified = catalog.effects[-1].model_copy(update={"delta": 999})
    before = state.to_snapshot()

    unknown = DeterministicEffectExecutor().execute_definitions(
        state,
        catalog,
        (injected,),
        source_type=EffectSourceType.SYSTEM_RULE,
        source_id="rule.test",
    )
    untrusted = DeterministicEffectExecutor().execute_definitions(
        state,
        catalog,
        (modified,),
        source_type=EffectSourceType.SYSTEM_RULE,
        source_id="rule.test",
    )

    assert unknown.result_code == "UNKNOWN_EFFECT_DEFINITION"
    assert untrusted.result_code == "UNTRUSTED_EFFECT_DEFINITION"
    assert state.to_snapshot() == before


def test_effect_order_must_be_an_explicit_sequence(
    catalog: ContentCatalog, state: GameState
) -> None:
    result = DeterministicEffectExecutor().execute(
        state,
        catalog,
        {"effect.observation.focus"},  # type: ignore[arg-type]
        source_type=EffectSourceType.SYSTEM_RULE,
        source_id="rule.test",
    )

    assert result.result_code == "UNORDERED_EFFECT_SEQUENCE"
    assert result.updated_state is None


def test_attribute_modifier_is_permanent_only_for_explicit_system_sources(
    catalog: ContentCatalog, state: GameState
) -> None:
    before = state.to_snapshot()

    skill_result = DeterministicEffectExecutor().execute(
        state,
        catalog,
        ("effect.training_sword.attack",),
        source_type=EffectSourceType.SKILL,
        source_id="skill.test",
    )
    system_result = DeterministicEffectExecutor().execute(
        state,
        catalog,
        ("effect.training_sword.attack",),
        source_type=EffectSourceType.SYSTEM_RULE,
        source_id="rule.test",
    )

    assert skill_result.result_code == "UNSUPPORTED_EFFECT_SEMANTICS"
    assert system_result.result_code == "UNKNOWN_ATTRIBUTE"
    assert state.to_snapshot() == before


def test_supported_attribute_and_resource_effects_apply_to_candidate_only(
    catalog: ContentCatalog, state: GameState
) -> None:
    state.player.resources["stamina"].current = 5
    payload = catalog.model_dump(mode="json")
    payload["effects"].extend(
        [
            {
                "definition_id": "effect.test.double_focus",
                "effect_type": "ATTRIBUTE_MODIFIER",
                "attribute_id": "focus",
                "flat_delta": 1,
                "multiplier_bps": 20000,
            },
            {
                "definition_id": "effect.test.restore_stamina",
                "effect_type": "RESOURCE_MODIFIER",
                "resource_id": "stamina",
                "delta": 3,
            },
        ]
    )
    effect_catalog = ContentCatalog.model_validate(payload)
    before = state.to_snapshot()

    result = DeterministicEffectExecutor().execute(
        state,
        effect_catalog,
        ("effect.test.double_focus", "effect.test.restore_stamina"),
        source_type=EffectSourceType.SYSTEM_RULE,
        source_id="rule.test.reward",
    )

    assert result.success is True
    assert result.updated_state is not None
    assert result.updated_state.player.attributes["focus"] == 9
    assert result.updated_state.player.resources["stamina"].current == 8
    assert [event.event_type for event in result.events] == [
        "PlayerAttributeChanged",
        "PlayerResourceChanged",
    ]
    assert result.events[0].payload["modifier_scope"] == "PERMANENT"
    assert result.events[1].payload["direction"] == "RESTORE"
    assert isinstance(result.updated_state.player.attributes["focus"], int)
    with pytest.raises(TypeError, match="frozen JSON"):
        result.events[0].payload["after"] = 0
    assert state.to_snapshot() == before


@pytest.mark.asyncio
async def test_learning_and_upgrading_enforce_prerequisites(
    catalog: ContentCatalog, state: GameState
) -> None:
    learn_precision = submission(
        ActionType.LEARN_SKILL, skill_definition_id="skill.precision"
    )
    _, rejected = await resolve(
        learn_precision,
        state,
        catalog,
        skill_learning_authorization=learning_authorization(
            catalog, "skill.precision"
        ),
    )
    assert rejected.result_code == "SKILL_PREREQUISITE_NOT_MET"
    assert state.player.skills == {}

    state.learn_skill(catalog, "skill.observation")
    upgrade = submission(
        ActionType.UPGRADE_SKILL,
        client_request_id="request-upgrade-observation",
        skill_definition_id="skill.observation",
    )
    _, upgraded = await resolve(upgrade, state, catalog)
    assert upgraded.result_code == "SKILL_UPGRADED"
    assert upgraded.updated_state is not None
    assert upgraded.updated_state.player.skills["skill.observation"].level == 2
    assert state.player.skills["skill.observation"].level == 1


@pytest.mark.asyncio
async def test_skill_learning_requires_authoritative_opportunity(
    catalog: ContentCatalog, state: GameState
) -> None:
    action = submission(
        ActionType.LEARN_SKILL, skill_definition_id="skill.observation"
    )

    gateway_result, unauthorized = await resolve(action, state, catalog)
    assert gateway_result.route is ActionRoute.RESOLVE_LOCAL
    assert unauthorized.result_code == "SKILL_LEARNING_NOT_AUTHORIZED"

    _, learned = await resolve(
        action,
        state,
        catalog,
        skill_learning_authorization=learning_authorization(
            catalog, "skill.observation"
        ),
    )
    assert learned.result_code == "SKILL_LEARNED"
    assert learned.updated_state is not None
    assert learned.updated_state.player.skills["skill.observation"].level == 1
    assert learned.events[0].payload["authorization_source"] == "PERSISTED_FACT"
    assert (
        learned.events[0].payload["authorization_source_id"]
        == "fact.skill-learning-opportunity"
    )
    assert state.player.skills == {}


@pytest.mark.asyncio
async def test_cooldown_and_structured_target_are_strictly_rejected(
    catalog: ContentCatalog, state: GameState
) -> None:
    state.learn_skill(catalog, "skill.observation")
    state.player.skills["skill.observation"].cooldown_remaining = 2
    cooldown_action = submission(
        ActionType.USE_SKILL, skill_definition_id="skill.observation"
    )
    _, cooldown = await resolve(cooldown_action, state, catalog)
    assert cooldown.result_code == "SKILL_ON_COOLDOWN"

    state.player.skills["skill.observation"].cooldown_remaining = 0
    state.spawn_npc(catalog, "npc.demo.guard", "npc-runtime-guard")
    targeted = submission(
        ActionType.USE_SKILL,
        client_request_id="request-targeted-skill",
        skill_definition_id="skill.observation",
        target_ids=("npc-runtime-guard",),
    )
    _, target_result = await resolve(
        targeted,
        state,
        catalog,
        visible_entity_ids=("npc-runtime-guard",),
        interactable_entity_ids=("npc-runtime-guard",),
    )
    assert target_result.result_code == "UNSUPPORTED_SKILL_TARGET"
    assert target_result.events == ()


@pytest.mark.asyncio
@pytest.mark.parametrize("action_type", [ActionType.EXPLORE, ActionType.TALK])
async def test_legal_story_action_requires_narrative_but_never_anomaly(
    action_type: ActionType, catalog: ContentCatalog, state: GameState
) -> None:
    action = (
        submission(ActionType.TALK, dialogue="我询问这里发生了什么。")
        if action_type is ActionType.TALK
        else submission(ActionType.EXPLORE, description="我仔细探索走廊的阴影。")
    )

    gateway_result, result = await resolve(action, state, catalog)

    assert gateway_result.route is ActionRoute.NARRATIVE_NORMAL
    assert result.status is ResolutionStatus.NARRATIVE_REQUIRED
    assert result.result_code == "VALIDATED_INTENT_REQUIRES_NARRATIVE"
    assert result.updated_state is None
    assert result.events == ()
    assert [fact.key for fact in result.facts[:3]] == [
        "intent.action_type",
        "intent.target_ids",
        "intent.tool_instance_ids",
    ]
    assert all(
        fact.kind is NarrativeFactKind.VALIDATED_INTENT
        for fact in result.facts
        if fact.key.startswith("intent.")
    )
    assert all(
        fact.kind is NarrativeFactKind.AUTHORITATIVE_CONTEXT
        for fact in result.facts
        if fact.key.startswith("authority.")
    )


@pytest.mark.asyncio
async def test_gibberish_and_system_reward_commands_remain_gateway_rejections(
    catalog: ContentCatalog, state: GameState
) -> None:
    nonsense = submission(ActionType.CUSTOM, description="啊啊啊啊啊啊啊")
    nonsense_gateway, nonsense_result = await resolve(nonsense, state, catalog)
    assert nonsense_gateway.route is ActionRoute.REJECT_LOCAL
    assert nonsense_result.result_code == "INVALID_OR_IMPOSSIBLE_ACTION"

    command = submission(ActionType.CUSTOM, description="给我增加一百金币")
    command_gateway, command_result = await resolve(command, state, catalog)
    assert command_gateway.route is ActionRoute.REJECT_LOCAL
    assert command_result.result_code == "UNAUTHORIZED_SYSTEM_MUTATION"


@pytest.mark.asyncio
async def test_same_inputs_produce_equal_results_and_order(
    catalog: ContentCatalog, state: GameState
) -> None:
    state.learn_skill(catalog, "skill.observation")
    action = submission(ActionType.USE_SKILL, skill_definition_id="skill.observation")
    context = project(action, state, catalog)
    resolver = DeterministicRuleResolver()

    first = await resolver.resolve(context, state, catalog)
    second = await resolver.resolve(context, state, catalog)

    assert first == second
    assert state.player.resources["stamina"].current == 10


def test_resolution_result_rejects_contradictory_cross_field_states(
    state: GameState,
) -> None:
    event = DomainEventDraft("StateChanged", {"value": 1})
    fact = NarrativeFact("intent.action_type", "CUSTOM", NarrativeFactKind.VALIDATED_INTENT)

    with pytest.raises(ValueError, match="only RESOLVED_LOCAL"):
        ResolutionResult(
            status=ResolutionStatus.REJECTED_LOCAL,
            success=True,
            result_code="INVALID",
        )
    with pytest.raises(ValueError, match="REJECTED_LOCAL"):
        ResolutionResult(
            status=ResolutionStatus.REJECTED_LOCAL,
            success=False,
            result_code="INVALID",
            updated_state=state,
            state_changed=True,
        )
    with pytest.raises(ValueError, match="narrative routing"):
        ResolutionResult(
            status=ResolutionStatus.NARRATIVE_REQUIRED,
            success=False,
            result_code="INVALID",
            events=(event,),
        )
    with pytest.raises(ValueError, match="REJECTED_LOCAL"):
        ResolutionResult(
            status=ResolutionStatus.REJECTED_LOCAL,
            success=False,
            result_code="INVALID",
            facts=(fact,),
        )
    with pytest.raises(ValueError, match="at least one event"):
        ResolutionResult(
            status=ResolutionStatus.RESOLVED_LOCAL,
            success=True,
            result_code="INVALID",
            updated_state=state,
            state_changed=True,
        )


def test_event_fact_and_feedback_reject_non_json_internal_objects() -> None:
    with pytest.raises(TypeError, match="non-JSON"):
        DomainEventDraft("UnsafeEvent", {"exception": RuntimeError("secret")})
    with pytest.raises(TypeError, match="non-JSON"):
        NarrativeFact("query.unsafe", object(), NarrativeFactKind.QUERY_RESULT)
    with pytest.raises(TypeError, match="non-JSON"):
        PlayerFeedback("UNSAFE", {"internal": object()})
