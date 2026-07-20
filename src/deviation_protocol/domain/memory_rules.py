from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from deviation_protocol.domain.content import DefinitionId
from deviation_protocol.domain.player_memory import (
    NpcInteractionMilestone,
    SignificantExperienceCategory,
    SignificantExperienceSummary,
    significant_experience_summary,
)
from deviation_protocol.domain.narrative_outcome import NarrativeOutcomeResult


class _MemoryRuleModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class MemoryRuleSourceEventType(StrEnum):
    SCENARIO_STARTED = "ScenarioStarted"
    SCENARIO_DECISION_SELECTED = "ScenarioDecisionSelected"
    NARRATIVE_OUTCOME_ACCEPTED = "NarrativeOutcomeAccepted"
    SCENARIO_RUNTIME_EVENT_GENERATED = "ScenarioRuntimeEventGenerated"


class MemoryRuleOperation(StrEnum):
    START_SCENARIO = "START_SCENARIO"
    COMPLETE_SCENARIO = "COMPLETE_SCENARIO"
    RECORD_NPC_ENCOUNTER = "RECORD_NPC_ENCOUNTER"
    UPDATE_NPC_MILESTONE = "UPDATE_NPC_MILESTONE"
    REMEMBER_PUBLIC_FACT = "REMEMBER_PUBLIC_FACT"
    RECORD_SIGNIFICANT_EXPERIENCE = "RECORD_SIGNIFICANT_EXPERIENCE"


class MemoryRuleDefinition(_MemoryRuleModel):
    """Closed, data-only mapping from a flushed server event to one memory operation."""

    rule_id: DefinitionId
    rule_version: Annotated[
        str,
        Field(
            strict=True,
            min_length=1,
            max_length=32,
            pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$",
        ),
    ]
    source_event_type: MemoryRuleSourceEventType
    operation: MemoryRuleOperation
    required_narrative_outcome_rule_ids: tuple[DefinitionId, ...] = ()
    required_scenario_event_types: tuple[DefinitionId, ...] = ()
    required_outcome_results: tuple[NarrativeOutcomeResult, ...] = ()
    requires_scenario_completed: Annotated[bool, Field(strict=True)] = False
    npc_definition_id: DefinitionId | None = None
    npc_milestone: NpcInteractionMilestone | None = None
    public_fact_id: DefinitionId | None = None
    allowed_ending_ids: tuple[DefinitionId, ...] = ()
    significant_experience_category: SignificantExperienceCategory | None = None
    significant_experience_summary: SignificantExperienceSummary | None = None
    important_experience: Annotated[bool, Field(strict=True)] = False

    @model_validator(mode="after")
    def validate_closed_shape(self) -> MemoryRuleDefinition:
        for label, values in (
            ("outcome rule", self.required_narrative_outcome_rule_ids),
            ("scenario event", self.required_scenario_event_types),
            ("outcome result", self.required_outcome_results),
            ("ending", self.allowed_ending_ids),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"memory rule repeats a {label} reference")
        narrative_conditions = (
            self.required_narrative_outcome_rule_ids
            or self.required_outcome_results
        )
        if narrative_conditions and (
            self.source_event_type
            is not MemoryRuleSourceEventType.NARRATIVE_OUTCOME_ACCEPTED
        ):
            raise ValueError("narrative memory conditions require a narrative outcome event")
        if self.required_scenario_event_types and self.source_event_type not in {
            MemoryRuleSourceEventType.NARRATIVE_OUTCOME_ACCEPTED,
            MemoryRuleSourceEventType.SCENARIO_RUNTIME_EVENT_GENERATED,
        }:
            raise ValueError("scenario-event conditions require a trusted world event")

        permitted_operations = {
            MemoryRuleSourceEventType.SCENARIO_STARTED: {
                MemoryRuleOperation.START_SCENARIO,
                MemoryRuleOperation.REMEMBER_PUBLIC_FACT,
                MemoryRuleOperation.RECORD_SIGNIFICANT_EXPERIENCE,
            },
            MemoryRuleSourceEventType.SCENARIO_DECISION_SELECTED: {
                MemoryRuleOperation.COMPLETE_SCENARIO,
            },
            MemoryRuleSourceEventType.NARRATIVE_OUTCOME_ACCEPTED: {
                MemoryRuleOperation.COMPLETE_SCENARIO,
                MemoryRuleOperation.RECORD_NPC_ENCOUNTER,
                MemoryRuleOperation.UPDATE_NPC_MILESTONE,
                MemoryRuleOperation.REMEMBER_PUBLIC_FACT,
                MemoryRuleOperation.RECORD_SIGNIFICANT_EXPERIENCE,
            },
            MemoryRuleSourceEventType.SCENARIO_RUNTIME_EVENT_GENERATED: {
                MemoryRuleOperation.COMPLETE_SCENARIO,
                MemoryRuleOperation.REMEMBER_PUBLIC_FACT,
                MemoryRuleOperation.RECORD_SIGNIFICANT_EXPERIENCE,
            },
        }
        if self.operation not in permitted_operations[self.source_event_type]:
            raise ValueError("memory operation is incompatible with its source event")
        if self.operation in {
            MemoryRuleOperation.RECORD_NPC_ENCOUNTER,
            MemoryRuleOperation.UPDATE_NPC_MILESTONE,
        } and self.source_event_type is not MemoryRuleSourceEventType.NARRATIVE_OUTCOME_ACCEPTED:
            raise ValueError("NPC memory requires a trusted narrative world outcome")

        required_fields: dict[MemoryRuleOperation, frozenset[str]] = {
            MemoryRuleOperation.START_SCENARIO: frozenset(),
            MemoryRuleOperation.COMPLETE_SCENARIO: frozenset({"allowed_ending_ids"}),
            MemoryRuleOperation.RECORD_NPC_ENCOUNTER: frozenset({"npc_definition_id"}),
            MemoryRuleOperation.UPDATE_NPC_MILESTONE: frozenset(
                {"npc_definition_id", "npc_milestone"}
            ),
            MemoryRuleOperation.REMEMBER_PUBLIC_FACT: frozenset({"public_fact_id"}),
            MemoryRuleOperation.RECORD_SIGNIFICANT_EXPERIENCE: frozenset(
                {
                    "significant_experience_category",
                    "significant_experience_summary",
                }
            ),
        }
        present = {
            name
            for name in (
                "npc_definition_id",
                "npc_milestone",
                "public_fact_id",
                "allowed_ending_ids",
                "significant_experience_category",
                "significant_experience_summary",
            )
            if getattr(self, name)
        }
        required = required_fields[self.operation]
        if self.operation is MemoryRuleOperation.RECORD_SIGNIFICANT_EXPERIENCE:
            if self.significant_experience_category in {
                SignificantExperienceCategory.IMPORTANT_NPC_ENCOUNTER,
                SignificantExperienceCategory.NPC_RELATIONSHIP_MILESTONE,
            }:
                required = required | {"npc_definition_id"}
            elif (
                self.significant_experience_category
                is SignificantExperienceCategory.IMPORTANT_PUBLIC_DISCOVERY
            ):
                required = required | {"public_fact_id"}
        if present != required:
            raise ValueError("memory rule fields do not match its closed operation")
        if self.operation is MemoryRuleOperation.COMPLETE_SCENARIO and not (
            self.requires_scenario_completed and self.allowed_ending_ids
        ):
            raise ValueError("scenario completion memory requires a completed ending")
        if self.operation is MemoryRuleOperation.RECORD_SIGNIFICANT_EXPERIENCE:
            category = self.significant_experience_category
            assert category is not None
            allowed_categories = {
                MemoryRuleSourceEventType.SCENARIO_STARTED: {
                    SignificantExperienceCategory.SCENARIO_BEGIN,
                },
                MemoryRuleSourceEventType.SCENARIO_DECISION_SELECTED: set(),
                MemoryRuleSourceEventType.NARRATIVE_OUTCOME_ACCEPTED: {
                    SignificantExperienceCategory.SCENARIO_COMPLETION,
                    SignificantExperienceCategory.IMPORTANT_NPC_ENCOUNTER,
                    SignificantExperienceCategory.NPC_RELATIONSHIP_MILESTONE,
                    SignificantExperienceCategory.IMPORTANT_PUBLIC_DISCOVERY,
                },
                MemoryRuleSourceEventType.SCENARIO_RUNTIME_EVENT_GENERATED: {
                    SignificantExperienceCategory.SCENARIO_COMPLETION,
                    SignificantExperienceCategory.IMPORTANT_PUBLIC_DISCOVERY,
                },
            }
            if category not in allowed_categories[self.source_event_type]:
                raise ValueError(
                    "significant experience is incompatible with its source event"
                )
            if (
                category is SignificantExperienceCategory.SCENARIO_COMPLETION
                and not self.requires_scenario_completed
            ):
                raise ValueError(
                    "scenario-completion experience requires a completed scenario"
                )
            if (
                self.significant_experience_summary
                is not significant_experience_summary(category)
                or not self.important_experience
            ):
                raise ValueError("significant experience summary/importance is incompatible")
        elif self.important_experience:
            raise ValueError("only a significant-experience operation may be important")
        return self
