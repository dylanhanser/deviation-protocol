from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
import re
from typing import Any, Iterable

from deviation_protocol.domain.actions import ActionContext, ActionType


class PolicyOutcome(StrEnum):
    PASS = "PASS"
    REJECT = "REJECT"
    RESOLVE_LOCAL = "RESOLVE_LOCAL"


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    policy: str
    outcome: PolicyOutcome
    reason_code: str
    detail: str


class ActionPolicy(ABC):
    @abstractmethod
    def evaluate(self, context: ActionContext) -> PolicyDecision:
        raise NotImplementedError

    def pass_decision(self) -> PolicyDecision:
        return PolicyDecision(type(self).__name__, PolicyOutcome.PASS, "passed", "policy passed")

    def reject(self, code: str, detail: str) -> PolicyDecision:
        return PolicyDecision(type(self).__name__, PolicyOutcome.REJECT, code, detail)


class TurnStatePolicy(ActionPolicy):
    def evaluate(self, context: ActionContext) -> PolicyDecision:
        if context.session_phase != "AWAITING_ACTION":
            return self.reject("turn_not_accepting_actions", "session is not accepting player actions")
        if context.submission.turn_id != context.current_turn_id:
            return self.reject("stale_turn", "turn_id is not the current turn")
        return self.pass_decision()


class DuplicateRequestPolicy(ActionPolicy):
    def evaluate(self, context: ActionContext) -> PolicyDecision:
        if context.submission.client_request_id in context.processed_client_request_ids:
            return self.reject("duplicate_request", "client_request_id was already processed")
        return self.pass_decision()


class ContinueInputPolicy(ActionPolicy):
    """Keep server-directed auto advancement free of player-authored payloads."""

    def evaluate(self, context: ActionContext) -> PolicyDecision:
        action = context.submission
        if action.action_type is not ActionType.CONTINUE:
            return self.pass_decision()
        if any(
            (
                action.target_ids,
                action.tool_ids,
                action.description is not None,
                action.dialogue is not None,
                action.decision_id is not None,
                action.choice_id is not None,
                action.item_instance_id is not None,
                action.equipment_slot_id is not None,
                action.skill_definition_id is not None,
            )
        ):
            return self.reject(
                "continue_payload_forbidden",
                "CONTINUE accepts no player-authored payload fields",
            )
        return self.pass_decision()


class InputContractPolicy(ActionPolicy):
    def evaluate(self, context: ActionContext) -> PolicyDecision:
        action = context.submission
        if action.action_type is ActionType.CHOOSE:
            if not action.decision_id:
                return self.reject(
                    "missing_required_field", "CHOOSE requires decision_id"
                )
            if not action.choice_id:
                return self.reject(
                    "missing_required_field", "CHOOSE requires choice_id"
                )
            if action.target_ids or action.tool_ids:
                return self.reject(
                    "unexpected_structured_field",
                    "CHOOSE accepts only decision_id and choice_id",
                )
        elif action.decision_id is not None or action.choice_id is not None:
            return self.reject(
                "unexpected_structured_field",
                "decision_id and choice_id are only valid for CHOOSE",
            )
        requirements = {
            ActionType.TALK: ("dialogue", action.dialogue),
            ActionType.CUSTOM: ("description", action.description),
            ActionType.EXPLORE: ("description", action.description),
            ActionType.OBSERVE: ("description", action.description),
            ActionType.MOVE: ("description", action.description),
            ActionType.EQUIP: ("item_instance_id", action.item_instance_id),
            ActionType.UNEQUIP: ("item_instance_id", action.item_instance_id),
            ActionType.USE_ITEM: ("item_instance_id", action.item_instance_id),
            ActionType.LEARN_SKILL: ("skill_definition_id", action.skill_definition_id),
            ActionType.UPGRADE_SKILL: ("skill_definition_id", action.skill_definition_id),
            ActionType.USE_SKILL: ("skill_definition_id", action.skill_definition_id),
        }
        required = requirements.get(action.action_type)
        if required and not required[1]:
            return self.reject("missing_required_field", f"{action.action_type.value} requires {required[0]}")

        populated = sum(
            value is not None and value != ""
            for value in (action.description, action.dialogue, action.choice_id)
        )
        if populated > 1:
            return self.reject(
                "multiple_action_payloads",
                "only the payload matching the primary action type may be submitted",
            )
        if action.action_type is ActionType.EQUIP and not action.equipment_slot_id:
            return self.reject("missing_required_field", "EQUIP requires equipment_slot_id")
        if action.action_type is not ActionType.EQUIP and action.equipment_slot_id is not None:
            return self.reject(
                "unexpected_structured_field",
                "equipment_slot_id is only valid for EQUIP",
            )
        item_actions = {ActionType.EQUIP, ActionType.UNEQUIP, ActionType.USE_ITEM}
        if action.action_type not in item_actions and action.item_instance_id is not None:
            return self.reject(
                "unexpected_structured_field",
                "item_instance_id is only valid for a structured item action",
            )
        skill_actions = {
            ActionType.LEARN_SKILL,
            ActionType.UPGRADE_SKILL,
            ActionType.USE_SKILL,
        }
        if action.action_type not in skill_actions and action.skill_definition_id is not None:
            return self.reject(
                "unexpected_structured_field",
                "skill_definition_id is only valid for a structured skill action",
            )
        return self.pass_decision()


class EntityReferencePolicy(ActionPolicy):
    def evaluate(self, context: ActionContext) -> PolicyDecision:
        allowed = context.visible_entity_ids | context.interactable_entity_ids
        inaccessible = sorted(set(context.submission.target_ids) - allowed)
        if inaccessible:
            return self.reject(
                "inaccessible_target", f"targets are not visible or interactable: {', '.join(inaccessible)}"
            )
        return self.pass_decision()


class InventoryOwnershipPolicy(ActionPolicy):
    def evaluate(self, context: ActionContext) -> PolicyDecision:
        allowed_tools = context.inventory_item_ids | context.environment_tool_ids
        unavailable = set(context.submission.tool_ids) - allowed_tools
        item_instance_id = context.submission.item_instance_id
        if (
            item_instance_id is not None
            and item_instance_id not in context.inventory_item_ids
        ):
            unavailable.add(item_instance_id)
        unavailable = sorted(unavailable)
        if unavailable:
            return self.reject(
                "unavailable_tool", f"tools are not owned or present: {', '.join(unavailable)}"
            )
        return self.pass_decision()


class SkillReferencePolicy(ActionPolicy):
    def evaluate(self, context: ActionContext) -> PolicyDecision:
        skill_id = context.submission.skill_definition_id
        if skill_id is not None and skill_id not in context.available_skill_definition_ids:
            return self.reject(
                "unknown_skill_reference",
                f"skill definition is not present in authoritative content: {skill_id}",
            )
        return self.pass_decision()


class FeasibilityPolicy(ActionPolicy):
    """Conservative local screen for explicit nonsense and impossible declarations.

    It intentionally does not attempt open-ended semantic classification. Scenario-
    specific capability checks belong in RuleResolver when richer state exists.
    """

    def __init__(self, invalid_patterns: Iterable[str]) -> None:
        self._patterns = tuple(re.compile(pattern, re.IGNORECASE) for pattern in invalid_patterns)

    def evaluate(self, context: ActionContext) -> PolicyDecision:
        text = " ".join(
            part for part in (context.submission.description, context.submission.dialogue) if part
        )
        if any(pattern.search(text) for pattern in self._patterns):
            return self.reject(
                "invalid_or_impossible_action",
                "action is nonsensical or explicitly exceeds locally allowed capabilities",
            )
        return self.pass_decision()


class SystemAuthorityPolicy(ActionPolicy):
    """Rejects player text that tries to invoke system-only mutation commands."""

    def __init__(self, forbidden_patterns: Iterable[str]) -> None:
        self._patterns = tuple(
            re.compile(pattern, re.IGNORECASE) for pattern in forbidden_patterns
        )

    def evaluate(self, context: ActionContext) -> PolicyDecision:
        text = " ".join(
            part
            for part in (context.submission.description, context.submission.dialogue)
            if part
        )
        if any(pattern.search(text) for pattern in self._patterns):
            return self.reject(
                "unauthorized_system_mutation",
                "player input cannot execute system rewards or authoritative state edits",
            )
        return self.pass_decision()


class PlayerAgencyPolicy(ActionPolicy):
    def __init__(self, success_patterns: Iterable[str], npc_control_patterns: Iterable[str]) -> None:
        self._success = tuple(re.compile(pattern, re.IGNORECASE) for pattern in success_patterns)
        self._npc_control = tuple(re.compile(pattern, re.IGNORECASE) for pattern in npc_control_patterns)

    def evaluate(self, context: ActionContext) -> PolicyDecision:
        text = " ".join(
            part for part in (context.submission.description, context.submission.dialogue) if part
        )
        if any(pattern.search(text) for pattern in self._success):
            return self.reject(
                "declared_success", "players may describe an attempt, not declare its outcome"
            )
        if any(pattern.search(text) for pattern in self._npc_control):
            return self.reject(
                "npc_agency_violation", "players cannot decide an NPC's reaction or outcome"
            )
        return self.pass_decision()


class MultipleActionPolicy(ActionPolicy):
    def __init__(self, sequence_patterns: Iterable[str]) -> None:
        self._patterns = tuple(re.compile(pattern, re.IGNORECASE | re.DOTALL) for pattern in sequence_patterns)

    def evaluate(self, context: ActionContext) -> PolicyDecision:
        text = " ".join(
            part for part in (context.submission.description, context.submission.dialogue) if part
        )
        if any(pattern.search(text) for pattern in self._patterns):
            return self.reject("multiple_actions", "submit only one primary action per request")
        return self.pass_decision()


class LocalActionPolicy(ActionPolicy):
    def __init__(self, local_action_types: Iterable[str]) -> None:
        self._local_types = frozenset(ActionType(value) for value in local_action_types)

    def evaluate(self, context: ActionContext) -> PolicyDecision:
        if context.submission.action_type in self._local_types:
            return PolicyDecision(
                type(self).__name__,
                PolicyOutcome.RESOLVE_LOCAL,
                "local_action",
                "action is resolved from authoritative local state",
            )
        return self.pass_decision()


POLICY_TYPES: dict[str, type[ActionPolicy]] = {
    policy.__name__: policy
    for policy in (
        TurnStatePolicy,
        DuplicateRequestPolicy,
        ContinueInputPolicy,
        InputContractPolicy,
        EntityReferencePolicy,
        InventoryOwnershipPolicy,
        SkillReferencePolicy,
        FeasibilityPolicy,
        SystemAuthorityPolicy,
        PlayerAgencyPolicy,
        MultipleActionPolicy,
        LocalActionPolicy,
    )
}


def build_policy_chain(config: dict[str, Any]) -> list[ActionPolicy]:
    """Construct policies in configured order without introducing a rule-language DSL."""
    enabled = config.get("enabled", {})
    result: list[ActionPolicy] = []
    for name in config["policy_order"]:
        if not enabled.get(name, True):
            continue
        if name not in POLICY_TYPES:
            raise ValueError(f"unknown action policy: {name}")
        if name == "PlayerAgencyPolicy":
            result.append(PlayerAgencyPolicy(**config["player_agency"]))
        elif name == "FeasibilityPolicy":
            result.append(FeasibilityPolicy(**config["feasibility"]))
        elif name == "SystemAuthorityPolicy":
            result.append(SystemAuthorityPolicy(**config["system_authority"]))
        elif name == "MultipleActionPolicy":
            result.append(MultipleActionPolicy(**config["multiple_action"]))
        elif name == "LocalActionPolicy":
            result.append(LocalActionPolicy(config["local_action_types"]))
        else:
            result.append(POLICY_TYPES[name]())
    return result
