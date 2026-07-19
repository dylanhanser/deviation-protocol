from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from deviation_protocol.domain.actions import ActionType
from deviation_protocol.domain.content import DefinitionId
from deviation_protocol.domain.json_values import freeze_bounded_json_value


class NarrativeOutcomeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class NarrativeOutcomeResult(StrEnum):
    SUCCESS = "SUCCESS"
    AMBIGUOUS = "AMBIGUOUS"
    FAILURE = "FAILURE"
    NO_EFFECT = "NO_EFFECT"


class NarrativeFactRequirement(NarrativeOutcomeModel):
    fact_id: DefinitionId
    value: Any

    @model_validator(mode="after")
    def freeze_value(self) -> NarrativeFactRequirement:
        object.__setattr__(
            self,
            "value",
            freeze_bounded_json_value(self.value, path=f"narrative requirement {self.fact_id!r}"),
        )
        return self


class NarrativeFactEffect(NarrativeOutcomeModel):
    fact_id: DefinitionId
    value: Any

    @model_validator(mode="after")
    def freeze_value(self) -> NarrativeFactEffect:
        object.__setattr__(
            self,
            "value",
            freeze_bounded_json_value(self.value, path=f"narrative effect {self.fact_id!r}"),
        )
        return self


class NarrativeIntentMatcher(NarrativeOutcomeModel):
    action_types: tuple[ActionType, ...]
    required_any_terms: tuple[Annotated[str, Field(strict=True, min_length=1, max_length=80)], ...] = ()
    forbidden_terms: tuple[Annotated[str, Field(strict=True, min_length=1, max_length=80)], ...] = ()
    requires_target: bool = False

    @field_validator("required_any_terms", "forbidden_terms")
    @classmethod
    def normalize_terms(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.casefold().strip() for item in value)
        if len(normalized) != len(set(normalized)):
            raise ValueError("narrative intent terms must be unique")
        return normalized

    @model_validator(mode="after")
    def validate_matcher(self) -> NarrativeIntentMatcher:
        if not self.action_types or len(self.action_types) != len(set(self.action_types)):
            raise ValueError("narrative intent matcher requires unique action types")
        if set(self.required_any_terms) & set(self.forbidden_terms):
            raise ValueError("required and forbidden narrative terms overlap")
        return self


class NarrativeOutcomeEffectTemplate(NarrativeOutcomeModel):
    result: NarrativeOutcomeResult
    event_type: DefinitionId
    action_type: DefinitionId
    discovered_clue_ids: tuple[DefinitionId, ...] = ()
    deferred_bindings: tuple[NarrativeFactEffect, ...] = ()
    mutable_fact_updates: tuple[NarrativeFactEffect, ...] = ()
    resolves_current_decision: bool = False
    expose_in_frame: bool = True
    requires_visible_npc_utterance: bool = False
    required_visible_npc_utterance_any_terms: tuple[
        Annotated[str, Field(strict=True, min_length=1, max_length=80)], ...
    ] = ()
    forbidden_prose_terms: tuple[
        Annotated[str, Field(strict=True, min_length=1, max_length=80)], ...
    ] = ()

    @field_validator(
        "required_visible_npc_utterance_any_terms", "forbidden_prose_terms"
    )
    @classmethod
    def normalize_prose_terms(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.casefold().strip() for item in value)
        if len(normalized) != len(set(normalized)):
            raise ValueError("forbidden prose terms must be unique")
        return normalized

    @model_validator(mode="after")
    def validate_effect(self) -> NarrativeOutcomeEffectTemplate:
        for updates in (self.deferred_bindings, self.mutable_fact_updates):
            ids = tuple(item.fact_id for item in updates)
            if len(ids) != len(set(ids)):
                raise ValueError("narrative outcome repeats a fact update")
        if len(self.discovered_clue_ids) != len(set(self.discovered_clue_ids)):
            raise ValueError("narrative outcome repeats a clue")
        if (
            self.required_visible_npc_utterance_any_terms
            and not self.requires_visible_npc_utterance
        ):
            raise ValueError("required utterance terms require a visible NPC utterance")
        return self


class NarrativeOutcomeRuleDefinition(NarrativeOutcomeModel):
    rule_id: DefinitionId
    rule_version: DefinitionId
    allowed_phase_ids: tuple[DefinitionId, ...]
    intent: NarrativeIntentMatcher
    required_visible_npc_definition_ids: tuple[DefinitionId, ...] = ()
    required_fact_values: tuple[NarrativeFactRequirement, ...] = ()
    required_clue_ids: tuple[DefinitionId, ...] = ()
    required_current_decision_ids: tuple[DefinitionId, ...] = ()
    once: bool = True
    safe_description: Annotated[str, Field(strict=True, min_length=1, max_length=300)]
    effects: tuple[NarrativeOutcomeEffectTemplate, ...]
    priority: Annotated[int, Field(strict=True, ge=0, le=10_000)] = 100
    mutex_group: DefinitionId

    @model_validator(mode="after")
    def validate_rule(self) -> NarrativeOutcomeRuleDefinition:
        if not self.allowed_phase_ids or not self.effects:
            raise ValueError("narrative outcome rule requires phases and effects")
        for values in (
            self.allowed_phase_ids,
            self.required_visible_npc_definition_ids,
            self.required_clue_ids,
            self.required_current_decision_ids,
        ):
            if len(values) != len(set(values)):
                raise ValueError("narrative outcome rule contains duplicate references")
        results = tuple(item.result for item in self.effects)
        if len(results) != len(set(results)):
            raise ValueError("narrative outcome rule repeats a result template")
        fact_ids = tuple(item.fact_id for item in self.required_fact_values)
        if len(fact_ids) != len(set(fact_ids)):
            raise ValueError("narrative outcome rule repeats a fact requirement")
        return self

    def effect(self, result: NarrativeOutcomeResult) -> NarrativeOutcomeEffectTemplate:
        return next(item for item in self.effects if item.result is result)
