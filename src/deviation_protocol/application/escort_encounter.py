"""The bounded wind-gate encounter policy and its explicit safe projection.

This is not a general conflict or status engine. Composition installs it only
for the pinned standalone content package; generic scenario code has no ID switch.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_serializer, model_validator

from deviation_protocol.application.errors import SnapshotInvalidError
from deviation_protocol.domain.scenario import EndingStatus


CONTENT_IDENTITY = ("wind_gate", "wind-gate-1.0.0")
CONTENT_SHA256 = "c3c6673df9615a9d749dc4db2cc905b6541c113b6e639adc8bd3428fd8f0d961"
FACT = "wind_gate.fact.encounter"
COMPANION = "npc.wind_gate.companion"
PLAYER = "character.wind_gate.traveler"


class PublicEscortEncounter(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    presentation_version: Literal[1] = 1
    objective: str
    danger: str
    companion: str
    player_position: str
    companion_position: str
    condition: Literal["慌乱", "扶稳", "失衡"] | None
    outcome: Literal["ACTIVE", "SUCCESS", "SAFE_WITHDRAWAL"]

    @model_validator(mode="after")
    def validate_condition_lifetime(self):
        if (self.outcome == "ACTIVE") != (self.condition is not None):
            raise ValueError("encounter condition must match its lifetime")
        return self

    @model_serializer(mode="wrap")
    def serialize(self, handler):
        data = handler(self)
        data["condition"] = self.condition
        return data


class EscortEncounterPolicy:
    # condition, phase, location, histories (ordered accepted decisions)
    _states = {
        "initial": ("慌乱", "reception", "platform", ((),)),
        "steady": ("扶稳", "transfer", "platform", (("initial",),)),
        "unsteady": ("失衡", "transfer", "midpoint", (("initial",),)),
        "door": ("扶稳", "exit", "door", (("initial", "steady"), ("initial", "unsteady"))),
        "success": (None, "resolution", "waiting", (("initial", "steady", "door"), ("initial", "unsteady", "door"))),
        "withdrawn": (None, "resolution", "refuge", (("initial",), ("initial", "steady"), ("initial", "unsteady"), ("initial", "steady", "door"), ("initial", "unsteady", "door"))),
    }
    _positions = {"platform": "入口平台", "midpoint": "通道中段", "door": "内门前", "waiting": "候船室", "refuge": "避风间"}

    @staticmethod
    def companion_id(session_id: str) -> str:
        return "companion-" + sha256(session_id.encode("utf-8")).hexdigest()[:48]

    def initialize(self, state, session_id, definition):
        # Creation-only binding, before the initial snapshot or any response.
        if len(state.npcs) != 1:
            raise SnapshotInvalidError(session_id)
        npc = next(iter(state.npcs.values()))
        npc.npc_id = self.companion_id(session_id)
        state.npcs = {npc.npc_id: npc}
        self.validate(state, session_id, definition)

    def validate(self, state, session_id, definition):
        runtime = state.scenario_runtime
        if (definition is None or (definition.scenario_id, definition.content_version) != CONTENT_IDENTITY
                or runtime is None or (runtime.scenario_id, runtime.scenario_content_version) != CONTENT_IDENTITY
                or state.player.character_definition_id != PLAYER):
            raise SnapshotInvalidError(session_id)
        value = runtime.mutable_fact_values.get(FACT)
        if not isinstance(value, str) or value not in self._states:
            raise SnapshotInvalidError(session_id)
        _, phase, location, histories = self._states[value]
        terminal = value in ("success", "withdrawn")
        expected_status = (EndingStatus.RESOLVED if value == "success" else EndingStatus.FAILED) if terminal else EndingStatus.ACTIVE
        npc_id = self.companion_id(session_id)
        npc = state.npcs.get(npc_id)
        if (set(state.npcs) != {npc_id} or npc is None or npc.npc_id != npc_id
                or npc.definition_id != COMPANION or npc_id == state.player.player_id
                or runtime.current_phase_id != f"wind_gate.{phase}"
                or runtime.current_location_id != f"wind_gate.{location}"
                or runtime.ending_status is not expected_status
                or runtime.ending_id != (f"wind_gate.ending.{value}" if terminal else None)
                or runtime.current_decision_id != (None if terminal else f"wind_gate.decision.{value}")
                or runtime.decisions_made not in tuple(tuple(f"wind_gate.decision.{v}" for v in history) for history in histories)
                or len(runtime.applied_event_ids) != len(runtime.decisions_made)
                or set(runtime.mutable_fact_values) != {FACT}
                or runtime.dynamic_facts or runtime.threat_clocks):
            raise SnapshotInvalidError(session_id)
        place = next((item for item in definition.locations if item.location_id == runtime.current_location_id), None)
        if place is None or COMPANION not in place.visible_entity_ids:
            raise SnapshotInvalidError(session_id)

    def project(self, state, session_id, definition) -> PublicEscortEncounter:
        self.validate(state, session_id, definition)
        value = state.scenario_runtime.mutable_fact_values[FACT]
        condition, _, location, _ = self._states[value]
        return PublicEscortEncounter(
            objective="护送同行者进入候船室，或一起撤入避风间。",
            danger="阵风穿过通道，外侧风闸正在关闭。阅读和等待不会推进危险。",
            companion="成年同行者",
            player_position=self._positions[location],
            companion_position=self._positions[location],
            condition=condition,
            outcome={"success": "SUCCESS", "withdrawn": "SAFE_WITHDRAWAL"}.get(value, "ACTIVE"),
        )
