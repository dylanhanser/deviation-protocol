# Run Protocol, Difficulty, and World Profiles

Status: **Approved product design — not implemented**

Phase ownership: **Phase 3.3**

P4-G0 status: **minimum Run-core documentation authority approved and closed;
its independent read-only review returned
`STRUCTURED_PLAYER_CHARACTER_P4_G0_REVIEW_APPROVED`. The resulting
documentation milestone is local until the user manually pushes it. The minimum
Run core and Structured Player Character Phase 4 remain unimplemented.**

## Goals

- Give players bounded pre-game control over world pressure and narrative
  presentation.
- Keep objective mechanics, character definition, presentation, and
  relationship atmosphere under separate authorities.
- Resolve all permitted choices before play, then freeze a versioned protocol
  for deterministic use throughout the run.
- Let a narrative model render confirmed state and results without giving it
  authority to invent mechanics, permanent state, or canon.

## Non-goals

- Implementing Phase 3.3 in the current codebase.
- Letting prose or model preference change resources, success, betrayal, death,
  relationship progression, or permanent facts.
- Replacing scenario-authored facts, character definitions, or engine rules.
- Defining NPC residence progression or production Provider pricing.
- Letting a player freely select an arbitrary world or directly select every
  later world.

## Minimum Run-core prerequisite for player-character Phase 4

The complete Run Protocol remains approved product design and is not
implemented. Before Structured Player Character P4-S1, only the smaller
prerequisite specified by the
[Minimum Run Core Implementation Plan](minimum_run_core_implementation_plan.md)
must be implemented and independently reviewed.

That prerequisite freezes:

- distinct strict opaque `RunId` and `ContinuousStoryLineId` carriers;
- one Run permanently owning exactly one continuous story line, rather than a
  generalized container for unrelated lines;
- a canonical current Run record, immutable Run revisions, and a positive
  monotonic `RunStateVersion` with compare-and-swap persistence;
- the closed minimum lifecycle values `pre_first_turn`, `active`, `completed`,
  and `terminated`;
- a separate immutable Run-owned Session participation record, with no Run,
  line, or character-binding column added to `game_sessions`;
- a Run application service as the one transaction owner for minimum Run
  mutations and the future character binding; and
- an all-null authoritative storage seam for the future exact
  player-character and applicable contract/revision reference.

`pre_first_turn` and `active` are active continuous-story-line states for
binding exclusivity. `completed` and `terminated` are non-active historical
states. The minimum core creates only `pre_first_turn`; it does not implement
the transition to any other lifecycle value. When a later authorized terminal
transition has a character binding, Run authority must make the binding
historical in the same atomic change.

The minimum aggregate is allocated before the first turn and therefore does
not pretend that a resolved protocol, entry world, current visit, or scenario
already exists. The existing lifecycle below remains authoritative: before
the first turn can begin, the resolved protocol plus
`entry_world_id`/`entry_world_version` must receive their Run binding and be
frozen. Full Phase 3.3 implementation continues to own that transition,
world/visit identity, later-world selection, revisits, and world-line rules.

Session participation is created only through trusted Run orchestration.
Caller-supplied Session data cannot select or replace a Run; participation
does not grant character ownership or controller authority. Multiple distinct
trusted Sessions may participate in the same Run, while one Session cannot
participate in conflicting Runs. This record does not activate public resume,
reconnect, cross-tab, browser-restart, or multi-device behavior.

The minimum Run core and its production composition remain unimplemented at
P4-G0. The reserved character-binding seam is populated only by separately
authorized P4-S1 work.

## Responsibility separation

The pre-game UI may expose these choices together, but their internal authority
remains separate:

| Concern | Authority | Effect |
| --- | --- | --- |
| Difficulty/world rules | Engine-owned world profile | Objective resources, trust environment, failure consequences, information opacity, and conflict incentives |
| Character definition | Versioned character definition | Abilities, knowledge boundaries, personality, and viewpoint |
| Run Protocol | Frozen structured presentation contract | How confirmed state and results are narrated |
| Relationship atmosphere | Presentation overlay | Tension and expression only; never objective relationship progression |

Difficulty may recommend presentation defaults, and a character may recommend
viewpoint-compatible defaults. Neither merges its authority into the Run
Protocol. Relationship atmosphere is not world tone.

## World selection and ordering

Status: **Approved product design — not implemented**

- At the beginning of a run, the player may select the entry world only from a
  small, explicitly authored set of eligible initial worlds.
- The player cannot freely select an arbitrary world.
- Once selected and the run begins, `entry_world_id` and
  `entry_world_version` are frozen for that run and cannot be changed.
- The player does not select later worlds directly.
- Later worlds are selected dynamically by the engine from the currently
  eligible world pool.
- Dynamic selection is deterministic and reproducible from engine-owned state
  and seed. It does not rely on uncontrolled model randomness.
- Selection may consider prerequisites, completed worlds, current run state,
  difficulty/world profile, major hidden-setting requirements, and
  important-NPC recovery requirements.
- Pure randomness must not prevent required narrative progression or recovery
  of a major hidden setting or important NPC.

`death_certificate_v1` is the current canonical Demo and vertical-slice
scenario. It is not permanently designated as the production entry world.

The exact eligible initial-world catalogue, weighting algorithm, anti-repeat
rules, progression constraints, and priority-injection rules remain Deferred.

### Important-world revisits

Status: **Approved product design — not implemented**

- An explicitly authored important world may remain eligible for later engine
  selection after the player has already visited it.
- The player cannot directly choose or request a later-world revisit and cannot
  approve, veto, or otherwise authorize an engine-proposed revisit. The
  complete revisit decision is engine-owned.
- Revisiting a world is not automatically a scenario restart or state reset.
- Confirmed world state, important NPC state, player-caused consequences,
  discovered facts, and unresolved events persist unless an engine-authorized
  world-line transition explicitly changes them.
- A world's first accessible region does not define the power level, scale, or
  narrative depth of the entire world.
- An initial world may appear beginner-oriented only because the player begins
  in a remote, protected, or peripheral region.
- Later visits may reveal previously inaccessible regions, major factions,
  powerful inhabitants, hidden history, and higher-level conflicts within the
  same persistent world.
- Re-entry must provide meaningful progression, revelation, or consequence
  rather than unrestricted repetition, duplicated rewards, or resource
  farming.
- The engine may prioritize an important-world revisit when required for:
  - a major hidden-setting revelation;
  - an important NPC's recovery or later arc;
  - unresolved world consequences;
  - access to a newly eligible region;
  - a major scenario or world-line event.
- Ordinary worlds do not require later recovery merely because they were
  previously visited.
- Anti-repeat rules and random weighting must not permanently exclude an
  important world whose authored recovery conditions have become true.
- Re-entry eligibility, persistent world state, region unlocking, and recovery
  priority are engine-owned.
- The model must not independently return the player to a world, reset world
  state, unlock a region, or invent a required recovery event.

The design distinguishes three conceptual identities without defining current
schema fields:

1. the persistent identity of an authored world;
2. an individual visit or run-local entry identity; and
3. the region or scenario content accessible during that visit.

These identities prevent a revisit from being treated as a fresh copy of the
world while allowing each visit to expose different authored content.

## Main pre-game dimensions

### World tone

- `Grim`
- `Balanced`
- `Heroic`

### Resource pressure

- `Scarce`
- `Fluid`
- `Generous`

Resource pressure becomes an engine-owned world/difficulty input. A model may
narrate its confirmed effects but cannot directly add, remove, restore, spoil,
or otherwise modify resources.

### Reality boundary

- `Lawful`
- `Deviant`
- `Chaotic`

### Relationship atmosphere overlay

- `off`
- `veiled`
- `charged`

This overlay changes presentation only. It cannot create affection, change a
relationship stage, satisfy a relationship flag, or unlock residence.

## Difficulty/world parameters

The engine owns these parameters:

- `resource_pressure`
- `social_trust`
- `consequence_severity`
- `information_opacity`
- `conflict_intensity`

Profiles provide defaults. Permitted player overrides occur only before the run
starts.

### Extreme — Silent Hunting Ground

- Extreme scarcity.
- Severe consequences.
- Opaque information.
- Very low default social trust.
- High cooperation cost.
- High betrayal incentives.
- Dark-forest-like conflict.

### Standard — Fragile Alliance

- Local scarcity.
- Trust must be earned.
- Cooperation and betrayal are both meaningful.
- Betrayal is possible but not universal.

### Easier — Open Expedition

- Sufficient resources.
- Trade, rescue, and cooperation are more common.
- Betrayal incentives are lower.
- Conflict intensity is reduced, but narrative conflict still exists.

## Determinism and authority

- Difficulty controls objective mechanics and world conditions.
- Character definition controls abilities, knowledge, personality, and
  viewpoint.
- Protocol presets control presentation.
- Difficulty and character may supply recommended defaults.
- Player-approved overrides are resolved before the first turn.
- The resolved protocol is versioned and frozen when the first turn begins.
- Fluid behavior is resolved deterministically by the engine using state and
  seed.
- The model does not perform its own uncontrolled random selection.
- The model does not invent resource loss, betrayal, death, permanent state
  changes, or major canon facts.
- `Grim` may intensify language, but cannot make a valid potion expired or an
  on-time rescue late unless the engine established that fact.
- `Heroic` may emphasize opportunity and reversal, but cannot manufacture
  success.
- `Chaotic` may add dreamlike, surreal, or limited meta presentation.
- Permanent canon arising from `Chaotic` presentation requires engine
  authorization and world-line consistency validation.
- Relationship atmosphere affects tension and expression, not objective
  relationship state.

These rules preserve the existing authority principle: the model narrates
confirmed state and results; the engine owns objective mechanics and permanent
state.

## Structured prompt input

The accepted direction is:

```text
difficulty + character + permitted pre-game overrides
  -> resolved, versioned Run Protocol
  -> fixed structured prompt prefix
```

A proposed representation is:

```text
[RUN_PROTOCOL v1]
difficulty_profile=<resolved profile>
character_id=<resolved character>
world_tone=<grim|balanced|heroic>
resource_pressure=<scarce|fluid|generous>
social_trust=<resolved value>
consequence_severity=<resolved value>
information_opacity=<resolved value>
conflict_intensity=<resolved value>
reality_boundary=<lawful|deviant|chaotic>
relationship_overlay=<off|veiled|charged>
preset_version=1
[/RUN_PROTOCOL]
```

The structured, versioned boundary is accepted. Exact serialization and
validation details will be finalized during Phase 3.3 implementation. No
`RUN_PROTOCOL` block exists in the implemented prompt today.

## Lifecycle

1. The game offers engine-approved profile, character, and eligible
   initial-world choices.
2. Difficulty and character definitions supply defaults or recommendations.
3. The player selects one eligible entry world and applies only permitted
   pre-game overrides.
4. The engine validates and resolves the complete profile.
5. The resolved protocol, `entry_world_id`, and `entry_world_version` receive
   their run binding and are frozen at the first turn.
6. Each turn uses the frozen protocol with current engine-confirmed state.
7. The engine resolves any fluid behavior deterministically from state and
   seed; the Provider only renders the permitted presentation.
8. When a later world is required, the engine deterministically selects it from
   the eligible pool while preserving required progression and recovery.
9. Replay uses the same frozen protocol, authoritative state, and deterministic
   inputs.

## Deterministic requirements

- Resolution order, defaults, override precedence, and validation are stable.
- No setting depends on unordered collection iteration, wall-clock time, or a
  Provider-selected random value.
- Entry-world identity remains frozen, and later-world selection is
  reproducible from engine-owned state and seed.
- Required progression and engine-confirmed major-setting or important-NPC
  recovery constraints take priority over pure random weighting.
- The stored/frozen representation is sufficient to reproduce presentation
  inputs for a run.
- Objective results are reproducible independently of prose variation.
- A missing, unknown, incompatible, or mutated protocol fails explicitly; it
  does not silently select new defaults mid-run.

## Implementation acceptance criteria

Phase 3.3 is acceptable only when:

1. The engine has a validated, versioned world/difficulty profile and frozen
   Run Protocol boundary.
2. Profile defaults and permitted overrides are resolved before the first turn.
3. Objective parameter effects are implemented and tested independently from
   presentation settings.
4. Character authority remains separate from difficulty and presentation.
5. Relationship atmosphere cannot mutate objective relationship state.
6. Identical state, seed, character, and resolved settings produce identical
   engine-owned outcomes.
7. Prompt construction uses only the validated frozen representation and does
   not grant model authority over resources, betrayal, death, or canon.
8. `Grim`, `Heroic`, and `Chaotic` authority limits have regression coverage.
9. Current scenarios retain their fixed facts unless a trusted engine event
   changes a mutable fact.
10. Entry-world selection is limited to an authored eligible set, freezes the
    selected ID/version, and later-world selection is deterministic,
    reproducible, and cannot strand required progression or recovery.
11. Important-world revisits preserve confirmed state and consequences, expose
    only engine-authorized regions/content, resist reward farming, and cannot
    be permanently excluded after authored recovery conditions become true.
12. Documentation and phase status are synchronized before audit or completion.

## Deferred questions

- Exact serialization and schema-validation form.
- Exact numeric/value ranges for the five engine-owned parameters.
- Profile-to-parameter default values.
- Which overrides are offered for each game mode or character.
- Compatibility and migration policy for future protocol versions.
- World/profile discovery and unlock policy.
- Exact eligible initial-world catalogue.
- Later-world weighting algorithm and general anti-repeat rules.
- Progression constraints and priority-injection rules for required story
  progression, major hidden settings, and important-NPC recovery.
- Important-world designation schema.
- Revisit limits and cooldowns.
- Region-unlock rules.
- Reward anti-farming rules.
- Recovery-priority weighting.
- World-line transition representation.
- How world-line consistency validation represents permanent canon approved
  after `Chaotic` presentation.

## Related documents

- [Project roadmap](../PLANS.md)
- [Minimum Run Core Implementation Plan](minimum_run_core_implementation_plan.md)
- [Narrative Provider boundary](narrative_provider.md)
- [NPC Relationship and Temporary Residence](npc_relationship_residence.md)
- [Current scenario specification](scenarios/death_certificate_v1.md)
