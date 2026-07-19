from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
import re
from typing import Any

from deviation_protocol.domain.content import (
    AttributeModifierEffectDefinition,
    ContentCatalog,
    ResourceModifierEffectDefinition,
)
from deviation_protocol.domain.events import DomainEventDraft
from deviation_protocol.domain.facts import NarrativeFact
from deviation_protocol.domain.state import (
    DomainErrorCode,
    DomainRuleViolation,
    GameState,
)


@dataclass(frozen=True, slots=True)
class EffectExecutionResult:
    success: bool
    result_code: str
    updated_state: GameState | None = None
    events: tuple[DomainEventDraft, ...] = ()
    facts: tuple[NarrativeFact, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "events", tuple(self.events))
        object.__setattr__(self, "facts", tuple(self.facts))
        if self.success != (self.updated_state is not None):
            raise ValueError("effect success must match the presence of updated_state")
        if not self.success and (self.events or self.facts):
            raise ValueError("failed effects cannot contain event drafts or facts")


class EffectSourceType(StrEnum):
    SKILL = "SKILL"
    CONSUMABLE = "CONSUMABLE"
    REWARD_SETTLEMENT = "REWARD_SETTLEMENT"
    SYSTEM_RULE = "SYSTEM_RULE"


_PERMANENT_ATTRIBUTE_SOURCES = frozenset(
    {EffectSourceType.REWARD_SETTLEMENT, EffectSourceType.SYSTEM_RULE}
)
_SOURCE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


class DeterministicEffectExecutor:
    """Applies the explicitly modeled effect union to a detached candidate state."""

    def execute(
        self,
        state: GameState,
        catalog: ContentCatalog,
        effect_definition_ids: Sequence[str],
        *,
        source_type: EffectSourceType,
        source_id: str,
    ) -> EffectExecutionResult:
        invalid_source = self._validate_source(source_type, source_id)
        if invalid_source is not None:
            return invalid_source
        if isinstance(effect_definition_ids, (str, bytes)) or not isinstance(
            effect_definition_ids, Sequence
        ):
            return EffectExecutionResult(False, "UNORDERED_EFFECT_SEQUENCE")
        effects: list[object] = []
        for definition_id in effect_definition_ids:
            effect = catalog.effect(definition_id)
            if effect is None:
                return EffectExecutionResult(False, "UNKNOWN_EFFECT_DEFINITION")
            effects.append(effect)
        return self.execute_definitions(
            state,
            catalog,
            effects,
            source_type=source_type,
            source_id=source_id,
        )

    def execute_definitions(
        self,
        state: GameState,
        catalog: ContentCatalog,
        effects: Sequence[object],
        *,
        source_type: EffectSourceType,
        source_id: str,
    ) -> EffectExecutionResult:
        invalid_source = self._validate_source(source_type, source_id)
        if invalid_source is not None:
            return invalid_source
        if isinstance(effects, (str, bytes)) or not isinstance(effects, Sequence):
            return EffectExecutionResult(False, "UNORDERED_EFFECT_SEQUENCE")
        try:
            candidate = state.detached_copy(catalog)
        except DomainRuleViolation as exc:
            return EffectExecutionResult(False, exc.code.value.upper())
        except ValueError:
            return EffectExecutionResult(False, "INVALID_EFFECT_RESULT")
        events: list[DomainEventDraft] = []
        facts: list[NarrativeFact] = []
        try:
            for effect in effects:
                if not isinstance(
                    effect,
                    (
                        AttributeModifierEffectDefinition,
                        ResourceModifierEffectDefinition,
                    ),
                ):
                    return EffectExecutionResult(False, "UNSUPPORTED_EFFECT")
                catalog_effect = catalog.effect(effect.definition_id)
                if catalog_effect is None:
                    return EffectExecutionResult(False, "UNKNOWN_EFFECT_DEFINITION")
                if catalog_effect != effect:
                    return EffectExecutionResult(False, "UNTRUSTED_EFFECT_DEFINITION")
                if isinstance(effect, AttributeModifierEffectDefinition):
                    if source_type not in _PERMANENT_ATTRIBUTE_SOURCES:
                        return EffectExecutionResult(
                            False, "UNSUPPORTED_EFFECT_SEMANTICS"
                        )
                    self._apply_attribute(
                        candidate, effect, source_type, source_id, events, facts
                    )
                else:
                    self._apply_resource(
                        candidate, effect, source_type, source_id, events, facts
                    )
            candidate.validate_against(catalog)
        except DomainRuleViolation as exc:
            return EffectExecutionResult(False, exc.code.value.upper())
        except ValueError:
            return EffectExecutionResult(False, "INVALID_EFFECT_RESULT")

        return EffectExecutionResult(
            True,
            "EFFECTS_APPLIED",
            updated_state=candidate,
            events=tuple(events),
            facts=tuple(facts),
        )

    @staticmethod
    def _validate_source(
        source_type: EffectSourceType, source_id: str
    ) -> EffectExecutionResult | None:
        if not isinstance(source_type, EffectSourceType):
            return EffectExecutionResult(False, "INVALID_EFFECT_SOURCE")
        if not _SOURCE_ID_PATTERN.fullmatch(source_id):
            return EffectExecutionResult(False, "INVALID_EFFECT_SOURCE")
        return None

    @staticmethod
    def _source_payload(
        source_type: EffectSourceType, source_id: str
    ) -> dict[str, str]:
        return {"source_type": source_type.value, "source_id": source_id}

    def _apply_attribute(
        self,
        state: GameState,
        effect: AttributeModifierEffectDefinition,
        source_type: EffectSourceType,
        source_id: str,
        events: list[DomainEventDraft],
        facts: list[NarrativeFact],
    ) -> None:
        before, after = state.apply_attribute_modifier(
            effect.attribute_id,
            flat_delta=effect.flat_delta,
            multiplier_bps=effect.multiplier_bps,
        )
        payload: dict[str, Any] = {
            **self._source_payload(source_type, source_id),
            "effect_definition_id": effect.definition_id,
            "attribute_id": effect.attribute_id,
            "before": before,
            "after": after,
            "modifier_scope": "PERMANENT",
        }
        events.append(DomainEventDraft("PlayerAttributeChanged", payload))
        facts.append(NarrativeFact(f"player.attribute.{effect.attribute_id}", after))

    def _apply_resource(
        self,
        state: GameState,
        effect: ResourceModifierEffectDefinition,
        source_type: EffectSourceType,
        source_id: str,
        events: list[DomainEventDraft],
        facts: list[NarrativeFact],
    ) -> None:
        resource = state.player.resources.get(effect.resource_id)
        if resource is None:
            raise DomainRuleViolation(
                DomainErrorCode.UNKNOWN_RESOURCE,
                f"unknown player resource {effect.resource_id!r}",
            )
        before = resource.current
        if effect.delta < 0:
            state.consume_resource(effect.resource_id, -effect.delta)
        elif effect.delta > 0:
            state.restore_resource(effect.resource_id, effect.delta)
        after = resource.current
        payload: dict[str, Any] = {
            **self._source_payload(source_type, source_id),
            "effect_definition_id": effect.definition_id,
            "resource_id": effect.resource_id,
            "delta": effect.delta,
            "direction": "CONSUME" if effect.delta < 0 else "RESTORE",
            "before": before,
            "after": after,
        }
        events.append(DomainEventDraft("PlayerResourceChanged", payload))
        facts.append(NarrativeFact(f"player.resource.{effect.resource_id}.current", after))
