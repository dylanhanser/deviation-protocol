from __future__ import annotations

from collections.abc import Iterable

from deviation_protocol.application.story_director import (
    DeterministicStoryDirector,
    StoryDirectorResult,
)
from deviation_protocol.domain.content import ContentCatalog
from deviation_protocol.domain.scenario import ScenarioDefinition
from deviation_protocol.domain.state import GameState


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
