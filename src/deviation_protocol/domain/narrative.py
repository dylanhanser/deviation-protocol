from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from deviation_protocol.domain.content import DefinitionId
from deviation_protocol.domain.json_values import freeze_bounded_json_value
from deviation_protocol.domain.scenario import DecisionReason, FrameMode


StrictBool = Annotated[bool, Field(strict=True)]


class NarrativeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RenderableFact(NarrativeModel):
    fact_id: DefinitionId
    value: Any

    @model_validator(mode="after")
    def freeze_value(self) -> RenderableFact:
        object.__setattr__(
            self,
            "value",
            freeze_bounded_json_value(
                self.value, path=f"renderable fact {self.fact_id!r}"
            ),
        )
        return self


class NpcKnowledgeFrame(NarrativeModel):
    npc_id: DefinitionId
    npc_definition_id: DefinitionId
    known_facts: tuple[RenderableFact, ...] = ()


class VerifiedEventFrame(NarrativeModel):
    event_id: DefinitionId
    event_type: DefinitionId


class SuggestedAction(NarrativeModel):
    action_id: DefinitionId
    action_type: DefinitionId
    label_hint: Annotated[str, Field(strict=True, min_length=1, max_length=160)]
    target_ids: tuple[DefinitionId, ...] = ()


class AllowedCustomActionConstraints(NarrativeModel):
    allowed_action_types: tuple[DefinitionId, ...]
    max_description_length: Annotated[int, Field(strict=True, ge=1, le=2000)]
    must_target_visible_entity: StrictBool


class VisibleClock(NarrativeModel):
    clock_id: DefinitionId
    value: Annotated[int, Field(strict=True, ge=0)]
    maximum: Annotated[int, Field(strict=True, ge=1)]

    @model_validator(mode="after")
    def validate_bounds(self) -> VisibleClock:
        if self.value > self.maximum:
            raise ValueError("visible clock value cannot exceed maximum")
        return self


class NarrativeFrame(NarrativeModel):
    frame_id: DefinitionId
    scenario_id: DefinitionId
    phase_id: DefinitionId
    mode: FrameMode
    current_location_id: DefinitionId
    must_render_facts: tuple[RenderableFact, ...] = ()
    may_render_facts: tuple[RenderableFact, ...] = ()
    visible_entities: tuple[DefinitionId, ...] = ()
    visible_clues: tuple[DefinitionId, ...] = ()
    must_render_event_types: tuple[DefinitionId, ...] = ()
    recent_verified_events: tuple[VerifiedEventFrame, ...] = ()
    npc_knowledge: tuple[NpcKnowledgeFrame, ...] = ()
    tone_hints: tuple[str, ...] = ()
    target_length: Annotated[int, Field(strict=True, ge=1)]
    min_length: Annotated[int, Field(strict=True, ge=1)]
    max_length: Annotated[int, Field(strict=True, ge=1)]
    decision_required: StrictBool
    decision_reason: DecisionReason | None = None
    suggested_actions: tuple[SuggestedAction, ...] = ()
    allowed_custom_action_constraints: AllowedCustomActionConstraints | None = None
    stop_condition: Annotated[str, Field(strict=True, pattern="^(CONTINUE|AWAIT_PLAYER|SCENARIO_ENDED)$")]
    player_visible_clocks: tuple[VisibleClock, ...] = ()

    @model_validator(mode="after")
    def validate_decision_shape(self) -> NarrativeFrame:
        bounded_collections = (
            ("must-render facts", self.must_render_facts, 256),
            ("may-render facts", self.may_render_facts, 256),
            ("visible entities", self.visible_entities, 128),
            ("visible clues", self.visible_clues, 512),
            ("required events", self.must_render_event_types, 128),
            ("recent events", self.recent_verified_events, 128),
            ("NPC knowledge", self.npc_knowledge, 128),
            ("tone hints", self.tone_hints, 16),
            ("suggested actions", self.suggested_actions, 32),
            ("visible clocks", self.player_visible_clocks, 32),
        )
        for label, values, maximum in bounded_collections:
            if len(values) > maximum:
                raise ValueError(f"narrative frame {label} exceed the size limit")
        if self.decision_required:
            if self.decision_reason is None or not self.suggested_actions:
                raise ValueError("decision frame requires one reason and suggested actions")
            if self.stop_condition != "AWAIT_PLAYER":
                raise ValueError("decision frame must stop for player input")
        elif any(
            (
                self.decision_reason is not None,
                bool(self.suggested_actions),
                self.allowed_custom_action_constraints is not None,
            )
        ):
            raise ValueError("flow frame cannot contain a decision payload")
        if not self.min_length <= self.target_length <= self.max_length:
            raise ValueError("invalid narrative frame length order")
        fact_ids = tuple(
            item.fact_id for item in (*self.must_render_facts, *self.may_render_facts)
        )
        if len(fact_ids) != len(set(fact_ids)):
            raise ValueError("narrative frame repeats a renderable fact")
        action_ids = tuple(item.action_id for item in self.suggested_actions)
        if len(action_ids) != len(set(action_ids)):
            raise ValueError("narrative frame repeats a suggested action")
        return self
