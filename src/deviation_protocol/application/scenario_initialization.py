from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import hashlib

from deviation_protocol.application.story_director import (
    DeterministicStoryDirector,
    StoryDirectorResult,
)
from deviation_protocol.domain.content import ContentCatalog
from deviation_protocol.domain.scenario import ScenarioDefinition
from deviation_protocol.domain.state import GameState


_REGIONAL_BASE = object()


@dataclass(frozen=True, slots=True, init=False)
class ValidatedRegionalBase:
    session_id: str
    snapshot: bytes
    _seal: object
    _original: tuple

    def state(self):
        if (getattr(self, "_seal", None) is not _REGIONAL_BASE
                or self._original != (self.session_id, self.snapshot)):
            raise ScenarioInitializationError("untrusted regional base")
        return GameState.model_validate_json(self.snapshot, strict=True)

    def digest(self):
        self.state()
        return hashlib.sha256(self.snapshot).hexdigest()


def _seal_regional_base(*, session_id, state, bundle, events):
    """Verify held-source event provenance before issuing initialization input.

    Callers supply the owned persisted Session's events after full Run validation.
    No player/model transport can provide this sealed value.
    """
    from deviation_protocol.domain.world_continuation import snapshot_canonical_bytes
    from deviation_protocol.domain.world_revisit import HELD_ENDING
    state = bundle.validate_snapshot(state.to_snapshot())
    runtime = state.scenario_runtime
    definition = bundle.scenario_catalog.scenarios[0]
    if ((bundle.scenario_id, bundle.content_version) != ("undelivered_receipt", "undelivered-receipt-1.0.0")
            or runtime.ending_id != HELD_ENDING or runtime.ending_status.value != "RESOLVED"
            or runtime.mutable_fact_values.get("undelivered_receipt.fact.dispatch_held") is not True
            or not any(f.fact_id == "undelivered_receipt.fact.hold_is_not_delivery"
                       and f.value == "暂缓发运不证明此前是否已经送达。" for f in definition.facts)):
        raise ScenarioInitializationError("invalid held-source regional base")
    by_id = {}
    scenario_ids = set()
    held = []
    sequences = set()
    for event in events:
        if (event.session_id != session_id or event.event_id in by_id
                or type(event.sequence_no) is not int or event.sequence_no < 1
                or event.sequence_no in sequences):
            raise ScenarioInitializationError("crossed or duplicate source event")
        by_id[event.event_id] = event
        sequences.add(event.sequence_no)
        if event.payload.get("scenario_event_id"):
            scenario_ids.add(event.payload["scenario_event_id"])
        if (event.event_type == "ScenarioDecisionSelected"
                and event.payload.get("scenario_event_type") == "dispatch.held"
                and event.payload.get("decision_id") == "undelivered_receipt.decision.dispatch"):
            held.append(event)
    records = state.player_memory.scenario_records
    if (len(held) != 1 or not set(runtime.applied_event_ids) <= scenario_ids
            or held[0].payload.get("scenario_event_id") not in runtime.applied_event_ids
            or len(records) != 1 or records[0].status.value != "COMPLETED"
            or records[0].ending_id != HELD_ENDING
            or records[0].last_source_event_id != held[0].event_id
            or records[0].last_source_sequence_no != held[0].sequence_no):
        raise ScenarioInitializationError("held ending lacks committed event/memory provenance")
    value = object.__new__(ValidatedRegionalBase)
    raw = snapshot_canonical_bytes(state.to_snapshot())
    for key, item in (("session_id", session_id), ("snapshot", raw),
                      ("_seal", _REGIONAL_BASE), ("_original", (session_id, raw))):
        object.__setattr__(value, key, item)
    return value


class ScenarioInitializationError(ValueError):
    """Catalog-backed scenario initialization cannot be completed safely."""


def profession_tags_for(
    character_tags: Iterable[str], definition: ScenarioDefinition
) -> frozenset[str]:
    return frozenset(character_tags) & set(definition.available_profession_tags)


def initialize_scenario_state(
    state: GameState,
    catalog: ContentCatalog,
    definition: ScenarioDefinition,
    *,
    character_tags: Iterable[str],
    story_director: DeterministicStoryDirector,
) -> StoryDirectorResult:
    """Spawn declared runtime NPCs and start the authoritative scenario runtime.

    The caller supplies a fresh player state. This function is deterministic and
    performs no file, database, provider, clock, random, or environment access.
    """

    # Initialization is all-or-nothing even for non-transactional callers such as
    # the local workbench.  The successful serialized result remains identical to
    # the former in-place production sequence.
    candidate = state.detached_copy(catalog)

    for index, reference in enumerate(definition.npc_references, start=1):
        npc_definition = catalog.npc(reference.npc_definition_id)
        if npc_definition is None:  # protected by ScenarioCatalog validation
            raise ScenarioInitializationError("scenario NPC definition is unavailable")
        npc_character = catalog.character(npc_definition.character_definition_id)
        if (
            npc_character is None
            or "npc" not in npc_character.tags
            or npc_character.definition_id
            == candidate.player.character_definition_id
        ):
            raise ScenarioInitializationError("scenario NPC character is invalid")
        candidate.spawn_npc(
            catalog,
            reference.npc_definition_id,
            f"scenario-npc-{index}",
        )

    return story_director.start_scenario(
        candidate,
        definition,
        profession_tags=profession_tags_for(character_tags, definition),
    )
