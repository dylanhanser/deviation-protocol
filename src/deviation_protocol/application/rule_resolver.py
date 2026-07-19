from __future__ import annotations

from collections.abc import Callable
from typing import Any

from deviation_protocol.application.action_context import (
    SkillLearningAuthorizationSource,
    TrustedResolutionContext,
)
from deviation_protocol.application.action_gateway import ActionGateway, ActionRoute
from deviation_protocol.application.effect_executor import (
    DeterministicEffectExecutor,
    EffectSourceType,
)
from deviation_protocol.application.resolution import (
    PlayerFeedback,
    ResolutionResult,
    ResolutionStatus,
)
from deviation_protocol.domain.actions import ActionContext, ActionType
from deviation_protocol.domain.content import ContentCatalog
from deviation_protocol.domain.events import DomainEventDraft
from deviation_protocol.domain.facts import NarrativeFact, NarrativeFactKind
from deviation_protocol.domain.state import DomainRuleViolation, GameState


class DeterministicRuleResolver:
    def __init__(
        self,
        effect_executor: DeterministicEffectExecutor | None = None,
        gateway: ActionGateway | None = None,
    ) -> None:
        self._effect_executor = effect_executor or DeterministicEffectExecutor()
        self._gateway = gateway or ActionGateway.from_config()

    async def resolve(
        self,
        trusted_context: TrustedResolutionContext | object,
        state: GameState,
        catalog: ContentCatalog,
    ) -> ResolutionResult:
        if not isinstance(trusted_context, TrustedResolutionContext):
            return self._rejected("UNTRUSTED_RESOLUTION_CONTEXT")
        try:
            if not trusted_context.is_authentic_for(state, catalog):
                return self._rejected("TRUSTED_CONTEXT_STATE_MISMATCH")
        except (DomainRuleViolation, ValueError, TypeError):
            return self._rejected("INVALID_TRUSTED_RESOLUTION_CONTEXT")

        context = trusted_context.action_context
        gateway_result = self._gateway.evaluate(context)

        if gateway_result.route is ActionRoute.REJECT_LOCAL:
            code = (
                gateway_result.policy_trace[-1].reason_code.upper()
                if gateway_result.policy_trace
                else "GATEWAY_REJECTED"
            )
            return self._rejected(code)
        if gateway_result.route is ActionRoute.NARRATIVE_NORMAL:
            return self._narrative_required(context)
        if gateway_result.route is ActionRoute.NARRATIVE_ANOMALY_CANDIDATE:
            return ResolutionResult(
                status=ResolutionStatus.ANOMALY_EVALUATION_REQUIRED,
                success=False,
                result_code="ANOMALY_EVALUATION_DEFERRED",
                facts=self._intent_facts(context),
                feedback=PlayerFeedback("ANOMALY_EVALUATION_DEFERRED"),
            )

        try:
            state.validate_against(catalog)
        except DomainRuleViolation as exc:
            return self._rejected(exc.code.value.upper())

        action_type = context.submission.action_type
        query_handlers: dict[ActionType, Callable[[GameState], ResolutionResult]] = {
            ActionType.INSPECT_STATUS: self._inspect_status,
            ActionType.INSPECT_INVENTORY: self._inspect_inventory,
            ActionType.INSPECT_EQUIPMENT: self._inspect_equipment,
            ActionType.INSPECT_SKILLS: self._inspect_skills,
            ActionType.INSPECT_RESOURCES: self._inspect_resources,
            ActionType.INSPECT_CURRENCIES: self._inspect_currencies,
            ActionType.INSPECT_QUESTS: self._inspect_quests,
        }
        handler = query_handlers.get(action_type)
        if handler is not None:
            return handler(state)

        if (
            action_type is ActionType.LEARN_SKILL
            and context.submission.skill_definition_id is not None
            and not trusted_context.authorizes_skill_learning(
                context.submission.skill_definition_id
            )
        ):
            return self._rejected("SKILL_LEARNING_NOT_AUTHORIZED")

        skill_learning_authority = (
            trusted_context.skill_learning_authority(
                context.submission.skill_definition_id
            )
            if action_type is ActionType.LEARN_SKILL
            and context.submission.skill_definition_id is not None
            else None
        )
        return self._resolve_mutation(
            context,
            state,
            catalog,
            skill_learning_authority=skill_learning_authority,
        )

    def _resolve_mutation(
        self,
        context: ActionContext,
        state: GameState,
        catalog: ContentCatalog,
        *,
        skill_learning_authority: tuple[SkillLearningAuthorizationSource, str]
        | None = None,
    ) -> ResolutionResult:
        candidate = state.detached_copy(catalog)
        action = context.submission
        events: list[DomainEventDraft] = []
        facts: list[NarrativeFact] = []
        try:
            if action.action_type is ActionType.EQUIP:
                assert action.item_instance_id is not None
                assert action.equipment_slot_id is not None
                candidate.equip(catalog, action.item_instance_id, action.equipment_slot_id)
                events.append(
                    DomainEventDraft(
                        "ItemEquipped",
                        {
                            "item_instance_id": action.item_instance_id,
                            "equipment_slot_id": action.equipment_slot_id,
                        },
                    )
                )
                facts.append(
                    NarrativeFact(
                        f"player.equipment.{action.equipment_slot_id}",
                        action.item_instance_id,
                    )
                )
                code = "ITEM_EQUIPPED"
            elif action.action_type is ActionType.UNEQUIP:
                assert action.item_instance_id is not None
                instance = candidate.player.inventory.items.get(action.item_instance_id)
                previous_slot = (
                    instance.equipment.equipped_slot
                    if instance is not None and instance.equipment is not None
                    else None
                )
                candidate.unequip(action.item_instance_id)
                events.append(
                    DomainEventDraft(
                        "ItemUnequipped",
                        {
                            "item_instance_id": action.item_instance_id,
                            "equipment_slot_id": previous_slot,
                        },
                    )
                )
                facts.append(NarrativeFact(f"player.equipment.{previous_slot}", None))
                code = "ITEM_UNEQUIPPED"
            elif action.action_type is ActionType.USE_ITEM:
                assert action.item_instance_id is not None
                code = self._use_item(candidate, catalog, action.item_instance_id, events, facts)
            elif action.action_type is ActionType.LEARN_SKILL:
                assert action.skill_definition_id is not None
                assert skill_learning_authority is not None
                authorization_source, authorization_source_id = skill_learning_authority
                candidate.learn_skill(catalog, action.skill_definition_id)
                events.append(
                    DomainEventDraft(
                        "SkillLearned",
                        {
                            "skill_definition_id": action.skill_definition_id,
                            "level": 1,
                            "authorization_source": str(authorization_source),
                            "authorization_source_id": authorization_source_id,
                        },
                    )
                )
                facts.append(
                    NarrativeFact(f"player.skill.{action.skill_definition_id}.level", 1)
                )
                code = "SKILL_LEARNED"
            elif action.action_type is ActionType.UPGRADE_SKILL:
                assert action.skill_definition_id is not None
                candidate.upgrade_skill(catalog, action.skill_definition_id)
                level = candidate.player.skills[action.skill_definition_id].level
                events.append(
                    DomainEventDraft(
                        "SkillUpgraded",
                        {"skill_definition_id": action.skill_definition_id, "level": level},
                    )
                )
                facts.append(
                    NarrativeFact(
                        f"player.skill.{action.skill_definition_id}.level", level
                    )
                )
                code = "SKILL_UPGRADED"
            elif action.action_type is ActionType.USE_SKILL:
                return self._use_skill(context, candidate, catalog)
            else:
                return self._rejected("UNSUPPORTED_LOCAL_ACTION")
            candidate.validate_against(catalog)
        except DomainRuleViolation as exc:
            return self._rejected(
                exc.code.value.upper(),
                {"authoritative_rule": exc.code.value},
            )
        except (AssertionError, ValueError):
            return self._rejected("INVALID_LOCAL_ACTION")

        return self._resolved_mutation(code, candidate, events, facts)

    def _use_item(
        self,
        state: GameState,
        catalog: ContentCatalog,
        instance_id: str,
        events: list[DomainEventDraft],
        facts: list[NarrativeFact],
    ) -> str:
        definition_id, remaining_quantity, remaining_charges = state.consume_item(
            catalog, instance_id
        )
        events.append(
            DomainEventDraft(
                "ItemConsumed",
                {
                    "item_instance_id": instance_id,
                    "item_definition_id": definition_id,
                    "remaining_quantity": remaining_quantity,
                    "remaining_charges": remaining_charges,
                },
            )
        )
        facts.extend(
            (
                NarrativeFact(
                    f"player.inventory.{instance_id}.quantity", remaining_quantity
                ),
                NarrativeFact(
                    f"player.inventory.{instance_id}.charges", remaining_charges
                ),
            )
        )
        return "ITEM_CONSUMED"

    def _use_skill(
        self,
        context: ActionContext,
        candidate: GameState,
        catalog: ContentCatalog,
    ) -> ResolutionResult:
        action = context.submission
        assert action.skill_definition_id is not None
        definition = catalog.skill(action.skill_definition_id)
        if definition is None:
            return self._rejected("UNKNOWN_SKILL_DEFINITION")
        skill_state = candidate.player.skills.get(action.skill_definition_id)
        if skill_state is None:
            return self._rejected("SKILL_NOT_LEARNED")
        if skill_state.cooldown_remaining > 0:
            return self._rejected(
                "SKILL_ON_COOLDOWN",
                {"cooldown_remaining": skill_state.cooldown_remaining},
            )
        if action.target_ids:
            return self._rejected("UNSUPPORTED_SKILL_TARGET")

        cost_events: list[DomainEventDraft] = []
        cost_facts: list[NarrativeFact] = []
        try:
            for cost in definition.resource_costs:
                before = candidate.player.resources.get(cost.resource_id)
                before_value = before.current if before is not None else None
                candidate.consume_resource(cost.resource_id, cost.amount)
                after = candidate.player.resources[cost.resource_id].current
                cost_events.append(
                    DomainEventDraft(
                        "SkillResourceSpent",
                        {
                            "skill_definition_id": definition.definition_id,
                            "resource_id": cost.resource_id,
                            "amount": cost.amount,
                            "before": before_value,
                            "after": after,
                        },
                    )
                )
                cost_facts.append(
                    NarrativeFact(f"player.resource.{cost.resource_id}.current", after)
                )
        except DomainRuleViolation as exc:
            return self._rejected(exc.code.value.upper())

        effect_result = self._effect_executor.execute(
            candidate,
            catalog,
            definition.effect_definition_ids,
            source_type=EffectSourceType.SKILL,
            source_id=definition.definition_id,
        )
        if not effect_result.success or effect_result.updated_state is None:
            return self._rejected(effect_result.result_code)

        resolved_state = effect_result.updated_state
        uses = resolved_state.record_skill_use(definition.definition_id)
        resolved_state.validate_against(catalog)
        use_event = DomainEventDraft(
            "SkillUsed",
            {
                "skill_definition_id": definition.definition_id,
                "level": skill_state.level,
                "uses": uses,
            },
        )
        use_fact = NarrativeFact(
            f"player.skill.{definition.definition_id}.uses",
            uses,
        )
        return self._resolved_mutation(
            "SKILL_USED",
            resolved_state,
            [*cost_events, *effect_result.events, use_event],
            [*cost_facts, *effect_result.facts, use_fact],
        )

    @staticmethod
    def _inspect_status(state: GameState) -> ResolutionResult:
        resources = {
            key: {"current": value.current, "maximum": value.maximum}
            for key, value in sorted(state.player.resources.items())
        }
        parameters = {
            "player_id": state.player.player_id,
            "character_definition_id": state.player.character_definition_id,
            "attributes": dict(sorted(state.player.attributes.items())),
            "resources": resources,
        }
        return DeterministicRuleResolver._resolved_query("STATUS_INSPECTED", parameters)

    @staticmethod
    def _inventory_rows(state: GameState) -> list[dict[str, Any]]:
        return [
            {
                "item_instance_id": instance.instance_id,
                "item_definition_id": instance.definition_id,
                "quantity": instance.quantity,
                "durability": instance.durability,
                "charges": instance.charges,
                "equipped_slot": (
                    instance.equipment.equipped_slot
                    if instance.equipment is not None
                    else None
                ),
            }
            for _, instance in sorted(state.player.inventory.items.items())
        ]

    @classmethod
    def _inspect_inventory(cls, state: GameState) -> ResolutionResult:
        return cls._resolved_query(
            "INVENTORY_INSPECTED", {"items": cls._inventory_rows(state)}
        )

    @classmethod
    def _inspect_equipment(cls, state: GameState) -> ResolutionResult:
        items = [
            row
            for row in cls._inventory_rows(state)
            if state.player.inventory.items[row["item_instance_id"]].equipment is not None
        ]
        return cls._resolved_query("EQUIPMENT_INSPECTED", {"equipment": items})

    @staticmethod
    def _inspect_skills(state: GameState) -> ResolutionResult:
        skills = [
            {
                "skill_definition_id": definition_id,
                "level": skill.level,
                "proficiency": skill.proficiency,
                "cooldown_remaining": skill.cooldown_remaining,
                "uses": skill.uses,
            }
            for definition_id, skill in sorted(state.player.skills.items())
        ]
        return DeterministicRuleResolver._resolved_query(
            "SKILLS_INSPECTED", {"skills": skills}
        )

    @staticmethod
    def _inspect_resources(state: GameState) -> ResolutionResult:
        resources = {
            key: {"current": value.current, "maximum": value.maximum}
            for key, value in sorted(state.player.resources.items())
        }
        return DeterministicRuleResolver._resolved_query(
            "RESOURCES_INSPECTED", {"resources": resources}
        )

    @staticmethod
    def _inspect_currencies(state: GameState) -> ResolutionResult:
        return DeterministicRuleResolver._resolved_query(
            "CURRENCIES_INSPECTED",
            {"currencies": dict(sorted(state.player.wallet.balances.items()))},
        )

    @staticmethod
    def _inspect_quests(_: GameState) -> ResolutionResult:
        return DeterministicRuleResolver._resolved_query(
            "QUESTS_INSPECTED", {"quests": []}
        )

    @staticmethod
    def _resolved_query(code: str, parameters: dict[str, Any]) -> ResolutionResult:
        return ResolutionResult(
            status=ResolutionStatus.RESOLVED_LOCAL,
            success=True,
            result_code=code,
            facts=(
                NarrativeFact(
                    f"query.{code.lower()}",
                    parameters,
                    NarrativeFactKind.QUERY_RESULT,
                ),
            ),
            feedback=PlayerFeedback(code, parameters),
        )

    @staticmethod
    def _resolved_mutation(
        code: str,
        state: GameState,
        events: list[DomainEventDraft],
        facts: list[NarrativeFact],
    ) -> ResolutionResult:
        return ResolutionResult(
            status=ResolutionStatus.RESOLVED_LOCAL,
            success=True,
            result_code=code,
            updated_state=state,
            state_changed=True,
            events=tuple(events),
            facts=tuple(facts),
            feedback=PlayerFeedback(code),
        )

    @staticmethod
    def _rejected(
        code: str, parameters: dict[str, Any] | None = None
    ) -> ResolutionResult:
        return ResolutionResult(
            status=ResolutionStatus.REJECTED_LOCAL,
            success=False,
            result_code=code,
            feedback=PlayerFeedback(code, parameters or {}),
        )

    @classmethod
    def _narrative_required(cls, context: ActionContext) -> ResolutionResult:
        return ResolutionResult(
            status=ResolutionStatus.NARRATIVE_REQUIRED,
            success=False,
            result_code="VALIDATED_INTENT_REQUIRES_NARRATIVE",
            facts=cls._intent_facts(context),
            feedback=PlayerFeedback("NARRATIVE_REQUIRED"),
        )

    @staticmethod
    def _intent_facts(context: ActionContext) -> tuple[NarrativeFact, ...]:
        action = context.submission
        item_definitions = dict(context.item_definition_by_instance)
        npc_definitions = dict(context.npc_definition_by_id)
        return (
            NarrativeFact(
                "intent.action_type",
                action.action_type.value,
                NarrativeFactKind.VALIDATED_INTENT,
            ),
            NarrativeFact(
                "intent.target_ids",
                tuple(sorted(action.target_ids)),
                NarrativeFactKind.VALIDATED_INTENT,
            ),
            NarrativeFact(
                "intent.tool_instance_ids",
                tuple(sorted(action.tool_ids)),
                NarrativeFactKind.VALIDATED_INTENT,
            ),
            NarrativeFact(
                "authority.tool_definitions",
                tuple(
                    (instance_id, item_definitions.get(instance_id))
                    for instance_id in sorted(action.tool_ids)
                ),
                NarrativeFactKind.AUTHORITATIVE_CONTEXT,
            ),
            NarrativeFact(
                "authority.target_npc_definitions",
                tuple(
                    (npc_id, npc_definitions[npc_id])
                    for npc_id in sorted(action.target_ids)
                    if npc_id in npc_definitions
                ),
                NarrativeFactKind.AUTHORITATIVE_CONTEXT,
            ),
            NarrativeFact(
                "intent.description",
                action.description,
                NarrativeFactKind.VALIDATED_INTENT,
            ),
            NarrativeFact(
                "intent.dialogue",
                action.dialogue,
                NarrativeFactKind.VALIDATED_INTENT,
            ),
            NarrativeFact(
                "intent.decision_id",
                action.decision_id,
                NarrativeFactKind.VALIDATED_INTENT,
            ),
            NarrativeFact(
                "intent.choice_id",
                action.choice_id,
                NarrativeFactKind.VALIDATED_INTENT,
            ),
        )
