"""Bounded authored relationship policy; installed only for the pinned pack.

Decision evidence is the structured shared history. Text and the ordinary
memory index cannot establish relationship or residence eligibility.
"""
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from deviation_protocol.application.errors import SnapshotInvalidError
from deviation_protocol.domain.scenario import EndingStatus

CONTENT_IDENTITY = ("fog_station", "fog-station-1.0.0")
CONTENT_SHA256 = "898b2557f56d6f41263e1f088358df871453d351f2fce79a8e379416d5873a7b"
NPC = "npc.fog_station.cen_zhou"
LOGICAL_NPC = "authored-person.cen-zhou/v1"
FACT = "fog_station.fact.progress"
PREFIX = "fog_station."
ACTIVITIES = {"review": "复盘脱险", "story": "听一段已公开的巡路往事", "records": "一起整理观察记录"}


class PublicStationRelationship(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    presentation_version: Literal[1] = 1
    npc_name: Literal["岑舟"] = "岑舟"
    npc_age: Literal[32] = 32
    scope: Literal["THIS_SESSION"] = "THIS_SESSION"
    stage: Literal["未相识", "相识", "合作", "信任"]
    residence: Literal["未开放", "待决定", "已谢绝", "暂住中", "已离开"]
    activities_used: tuple[Literal["复盘脱险", "听一段已公开的巡路往事", "一起整理观察记录"], ...] = Field(max_length=3)
    remaining_slots: int = Field(ge=0, le=3)
    shared_experiences: tuple[str, ...] = Field(max_length=5)
    reunited: bool


class FogStationPolicy:
    @staticmethod
    def npc_id(session_id):
        return "station-" + sha256((LOGICAL_NPC + "\0" + session_id).encode()).hexdigest()[:48]

    def initialize(self, state, session_id, definition):
        if len(state.npcs) != 1:
            raise SnapshotInvalidError(session_id)
        npc = next(iter(state.npcs.values()))
        npc.npc_id = self.npc_id(session_id)
        state.npcs = {npc.npc_id: npc}
        self.validate(state, session_id, definition)

    def validate(self, state, session_id, definition):
        """Reconstruct the entire finite path, not merely its final fact value."""
        try:
            r = state.scenario_runtime
            if (definition.scenario_id, definition.content_version) != CONTENT_IDENTITY or r is None:
                raise ValueError("content")
            r.validate_against(definition)
            if len(state.npcs) != 1:
                raise ValueError("NPC instance")
            npc = next(iter(state.npcs.values()))
            if (npc.definition_id != NPC or npc.relationship_bps != 0 or npc.runtime_flags
                    or npc.npc_id == state.player.player_id
                    or (session_id is not None and npc.npc_id != self.npc_id(session_id))
                    or state.player.character_definition_id != "character.fog_station.traveler"):
                raise ValueError("NPC binding")
            evidence = {e.decision_id: e for e in r.decision_outcome_evidence}
            if len(evidence) != len(r.decisions_made) or set(evidence) != set(r.decisions_made):
                raise ValueError("decision evidence")
            node, codes, visits, transitions = "arrival", [], {PREFIX + "arrival": 1}, {}
            location = definition.initial_location_id
            for decision_id in r.decisions_made:
                if decision_id != PREFIX + "decision." + node:
                    raise ValueError("chronology")
                decision = next(d for d in definition.decision_windows if d.decision_id == decision_id)
                action = next(a for a in decision.suggested_actions if a.server_event_type == evidence[decision_id].scenario_event_type)
                codes.append(action.action_id.removeprefix(PREFIX + "choice."))
                node = action.mutable_fact_updates[0].value
                location = action.new_location_id
                phase = definition.phase(PREFIX + node)
                visits[phase.phase_id] = visits.get(phase.phase_id, 0) + 1
                transitions[PREFIX + "transition." + codes[-1]] = 1
            phase = definition.phase(PREFIX + node)
            if (r.current_phase_id != phase.phase_id or r.current_location_id != location
                    or r.mutable_fact_values != {FACT: node}
                    or r.current_decision_id != (None if phase.terminal else PREFIX + "decision." + node)
                    or r.ending_status != (EndingStatus.RESOLVED if phase.terminal else EndingStatus.ACTIVE)
                    or r.ending_id != (PREFIX + "ending." + node if phase.terminal else None)
                    or r.phase_visit_counts != visits or r.transition_use_counts != transitions
                    or len(r.applied_event_ids) != len(codes) or len(set(r.applied_event_ids)) != len(codes)
                    or r.phase_beat_index != 0 or r.dynamic_facts or r.threat_clocks
                    or r.narrative_outcome_evidence or r.discovered_clue_ids or r.completed_clue_group_ids
                    or r.bound_deferred_facts or r.opened_location_ids != {PREFIX + "interior", PREFIX + "platform"}
                    or NPC not in next(p for p in definition.locations if p.location_id == location).visible_entity_ids):
                raise ValueError("path state")
            return tuple(codes)
        except (ValueError, TypeError, AttributeError, StopIteration, KeyError, IndexError):
            raise SnapshotInvalidError(session_id or "invalid station snapshot") from None

    def project(self, state, session_id, definition):
        codes = self.validate(state, session_id, definition)
        used = tuple(ACTIVITIES[c.split("_")[0]] for c in codes if c.split("_")[0] in ACTIVITIES)
        departed = any(c.startswith("depart_") for c in codes)
        entered = "enter" in codes
        stage = "信任" if "finish_work" in codes else "合作" if "cooperate" in codes else "相识" if "meet" in codes else "未相识"
        residence = "已离开" if departed else "暂住中" if entered else "已谢绝" if "decline" in codes else "待决定" if "finish_work" in codes else "未开放"
        shared = []
        if "cooperate" in codes:
            shared.append("共同固定挡板，安全结束了这次险情。")
        if "finish_work" in codes:
            shared.append("自愿暂缓离开，并一起完成观察记录的收尾。")
        if entered:
            shared.append("曾在哨站短暂停留；" + ("已共同进行：" + "、".join(used) + "。" if used else "没有进行暂住活动。"))
        if departed:
            shared.append("已明确离开暂住处，本次不能再次入住。")
        if "farewell" in codes:
            shared.append("在观察台确认灯光消失后，回门口道别。")
        return PublicStationRelationship(stage=stage, residence=residence,
            activities_used=used, remaining_slots=3-len(used) if entered and not departed else 0,
            shared_experiences=tuple(shared), reunited="farewell" in codes)
