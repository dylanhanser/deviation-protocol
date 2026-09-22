"""Exact patrol path validation and bounded previous-visit author text."""
from hashlib import sha256
from deviation_protocol.application.errors import SnapshotInvalidError
from deviation_protocol.domain.scenario import EndingStatus
from deviation_protocol.domain.fog_patrol import DESTINATION as CONTENT_IDENTITY, DESTINATION_NPC as NPC, LOGICAL_NPC
CONTENT_SHA256 = "fdb955dd20693607f7a7a5fffd43811bcb32c933bf28e7588dacc5ffe0344c61"
PREFIX = "fog_patrol."
FACT = PREFIX + "fact.progress"

class FogPatrolPolicy:
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
                    or r.bound_deferred_facts or r.opened_location_ids != {PREFIX + "path"}
                    or NPC not in next(p for p in definition.locations if p.location_id == location).visible_entity_ids):
                raise ValueError("path state")
            return tuple(codes)
        except (ValueError, TypeError, AttributeError, StopIteration, KeyError, IndexError):
            raise SnapshotInvalidError(session_id or "invalid station snapshot") from None

    def project(self, state, session_id, definition):
        self.validate(state, session_id, definition)
        # Previous-visit recollections are presented in authored narrative. They
        # are not a THIS_SESSION relationship or transferable eligibility.
        return None
