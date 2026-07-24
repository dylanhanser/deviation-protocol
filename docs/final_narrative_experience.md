# Final Narrative Experience and Long-Term Systems

Status: **Approved and frozen canonical cross-phase product specification —
not implemented; third independent read-only review passed**

Authority scope: **Final player experience, persistent player-character
concept, NPC importance and golden long-term memory, multi-genre scenario
structure, cross-scenario continuity, and generalized narrative conflict**

## Decision language

This document uses the following terms deliberately:

- **Frozen requirement** means a canonical product decision that future design
  and implementation must preserve unless this specification is explicitly
  amended and reviewed.
- **Recommendation** means the preferred starting design, but evidence may
  justify a documented change without reversing a frozen product goal.
- **Provisional heuristic** means a value or weighting intended for
  experimentation. It must not become a permanent hard-coded product constant.
- **Deferred** means the product direction is known but its schema, algorithm,
  thresholds, copy, or implementation phase is not decided here.
- **Non-goal** means this design-freeze task does not implement or fully specify
  the named system.

Every substantive product statement below is a frozen requirement unless it is
explicitly labelled as a recommendation, provisional heuristic, Deferred, a
current implementation fact, or a non-goal.

## Canonical ownership and relationship to existing documents

This is the single product-level authority for the concerns in its authority
scope. It does not replace narrower documents that describe implemented
behavior or an already approved future phase:

| Document | Authority retained |
| --- | --- |
| [`PLANS.md`](../PLANS.md) | Project status, phase placement, and implementation claims |
| [`architecture.md`](architecture.md) | Implemented architecture and composition boundaries |
| [`public_client_contract.md`](public_client_contract.md) | Current implemented public client contract |
| [`narrative_provider.md`](narrative_provider.md) | Current Provider, candidate-output, and commit boundaries |
| [`player_memory.md`](player_memory.md) | Current implemented bounded player-memory behavior |
| [`run_protocol.md`](run_protocol.md) | Phase 3.3 Run Protocol, difficulty, and world-profile detail |
| [`npc_relationship_residence.md`](npc_relationship_residence.md) | Phase 3.4 relationship and temporary-residence detail |
| [`phase_3_2_deterministic_demo_environment.md`](phase_3_2_deterministic_demo_environment.md) | Deterministic Demo specification and evidence |
| [`guardrails.md`](engineering/guardrails.md) | Implemented engineering and safety guardrails, including `MODEL-001` |

Current implemented contracts and engineering guardrails remain authoritative
within their existing scopes. This product specification does not silently
supersede them. That retained narrower authority includes the current
architecture, public client/server contracts, Run Protocol, player-memory
contracts, NPC residence design, deterministic Demo documentation, Provider
and recovery contracts, and other implemented authorities.

Future contracts and phase designs must satisfy this product specification
when they implement its scope. A difference between this final-product
direction and a current Demo or public contract is planned evolution, not a
retroactive claim that the current implementation is defective. Any later
incompatibility requires an explicit versioned contract change, a migration or
compatibility plan, review, and a corresponding update to the authority that
owns the affected contract.

Fixed-semantic system text remains governed by `MODEL-001`. Where candidate
generation is permitted, a model may provide only bounded expression
candidates that preserve the authoritative meaning. Model-generated wording
must not alter fixed semantics, validation rules, state transitions, safety
boundaries, or server authority.

This specification freezes product behavior and authority boundaries. It does
not freeze DTO names, database tables, UI component names, prompt syntax,
numeric thresholds, or phase numbering unless stated otherwise.

## Product experience

The final game is a continuous interactive novel, not a dashboard-driven
workflow tool.

- Most of the player-facing screen must be devoted to readable narrative text.
- The reading area must remain the primary visual surface while model output is
  being produced. Controls should remain compact or be hidden when they are not
  useful.
- Persistent technical panels, debug state, request identifiers, state
  versions, clocks, and similar operational details must not dominate the
  player-facing experience.
- Important immediate conditions may be shown compactly when they affect the
  current situation.
- Full character, inventory, relationship, memory, and history information
  must remain available through secondary drawers, pages, overlays, or
  equivalent non-dominant surfaces.
- Operational diagnostics may exist in development or support tooling, but
  their availability does not make them part of the primary reading
  experience.

Exact typography, navigation, responsive breakpoints, accessibility behavior,
streaming presentation, and overlay layout are Deferred to the reading-first
interface design.

## Player actions

### Final interaction model

For a normal player-initiated narrative decision turn, the final interaction
model must present exactly three contextual natural-language action
suggestions for the current situation and must also provide a free-action path.

- The three generated actions must describe meaningful intentions in language
  appropriate to the current scene.
- The generated actions are suggestions, not restrictions or capabilities.
- The player must be able to ignore all three and submit a free action.
- Selecting a suggestion submits player intent; it does not guarantee that the
  suggested result will occur.
- Every submitted suggestion or free action must pass server-authoritative
  validation and state-transition resolution before any outcome is committed.
- Permanent fixed action-category buttons such as `move`, `observe`,
  `interact`, `explore`, or equivalent categories are not the final
  player-facing interaction model.
- A player choice should represent a meaningful, situation-changing narrative
  segment rather than one trivial mechanical button press.

The normal three-options-plus-free-action presentation is not required for:

- automatic narrative continuation that does not request a player decision;
- clarification or disambiguation;
- recoverable error handling;
- safety or invalid-intent responses;
- terminal or post-terminal presentation; or
- another non-decision system state explicitly defined by a narrower contract.

These exclusions must not be used to avoid offering choices during a genuine
player decision. Their exact public representation is Deferred to the future
output and recovery contracts.

### Agency and normalization

The player owns the intention of a submitted free action.

- A free action must not be silently rewritten into a materially different
  intention.
- The server must validate identity, current-state eligibility, size, safety,
  and structured input requirements.
- The server may perform meaning-preserving normalization, such as whitespace,
  encoding, or an unambiguous protocol projection.
- When an action cannot be accepted as intended, the system must reject it,
  request clarification, or state the applicable constraint. It must not
  pretend that the player chose a safer, easier, or more convenient action.
- The model may help classify or propose an interpretation, but that proposal
  is not the submitted action and cannot acquire mutation authority.

The server remains authoritative over whether an intended action is possible
and what outcome follows. That authority constrains outcomes, not the player's
right to state an intention.

## Persistent player-character creation

### Identity, account, and Run binding

- One account may create multiple player characters.
- Each continuous story line is bound to exactly one active player-character
  identity at a time.
- A Run must bind one stable player-character ID and the applicable character
  version.
- A Run must not silently replace, merge, reinterpret, or switch its bound
  player character.
- A character change requires an explicit, authoritative transition.

These are product identity invariants, not a choice of database schema,
endpoint shape, storage engine, or migration implementation.

### Formal character scope

The formal game must not restrict players to the five fixed character
presentations in the current deterministic Demo.

The existing five characters remain deterministic Demo validation fixtures.
They may later be adapted into editable quick-start templates, but they are not
the complete formal character system.

A formal player-character creation contract must support:

- a name or code name;
- a preferred form of address;
- an adult identity and gender expression, including ambiguous or custom
  expression;
- a broad adult age presentation;
- a broad appearance direction plus a small number of distinguishing features;
- an outward presentation plus an inward tendency;
- a reality anchor;
- a preference for narration of internal thoughts; and
- custom values or values intentionally left undecided.

The exact input controls, allowed lengths, localization rules, validation
vocabulary, and quick-start catalogue are Deferred. Every supported age
presentation represents an adult.

Within a continuous story line, the bound player character persists across
scenarios. Starting a new scenario must not silently recreate, replace,
reinterpret, merge, or switch that identity or its applicable version.

### Trait influence and limits

Character traits may guide:

- narration and point of view;
- immediate, bounded sensations or involuntary physical responses;
- NPC first impressions; and
- the content and phrasing of the three candidate actions.

Character traits must never:

- execute an action for the player;
- lock a choice merely because it contrasts with a trait;
- declare a contrasting action invalid;
- settle an intentional belief, relationship, or moral conclusion; or
- become hidden permission to mutate authoritative state.

Contradicting an initial trait is valid player behavior. The system may later
record an engine-validated development observation, but it must not erase the
fact that the player chose the action.

## Structured character authority

The authoritative server stores structured character state. The conceptual
separation is:

| Area | Purpose | Authority boundary |
| --- | --- | --- |
| `character_core` | Player-authored persistent identity, address, adult presentation, appearance direction, distinguishing features, outward presentation, inward tendency, reality anchor, and intentionally stated or undecided values | Changes require an explicit trusted player/profile workflow; model prose cannot rewrite it |
| `character_development` | Engine-validated long-term consequences and development accumulated through play | Only trusted server rules may accept and persist mutations |
| `narration_preferences` | Player-selected presentation controls, including internal-thought narration | Changes presentation only; it cannot alter objective mechanics, facts, relationships, or player intent |

These are conceptual authorities, not a claim that fields or storage with these
exact names exist today.

A versioned prompt compiler may derive stable, bounded model context from the
structured authoritative state. The compiler must preserve the separation
between identity, development, and narration preference. Model output must not
directly mutate authoritative long-term character state.

`character_development` may eventually include:

- injuries and scars;
- abilities and restrictions;
- externally grounded relationship facts;
- player-expressed or player-confirmed beliefs;
- promises and debts;
- player-expressed or player-confirmed regrets;
- important items; and
- behavior-derived observations that do not settle subjective inner states.

The list establishes the required breadth of the long-term system, not an
implemented schema or permission for prose to create those facts. In
particular, an engine-validated observation does not authorize the system to
infer a settled subjective inner state.

Initial self-description and behavior-derived personality may coexist. An
apparent conflict between them may be an intentional contradiction,
role-playing choice, or development arc; the system must not automatically
rewrite one to make the character artificially consistent.

## Player-character continuity, death, retirement, and replacement

- Final death places the affected player character in the `deceased` state and
  ends that character's current continuous story line.
- `deceased` and `retired` are separate lifecycle states. Final death does not
  place a character in the `retired` state.
- A deceased player character may return only through an authoritatively
  established resurrection, rebirth, reincarnation, time reversal, or
  equivalent narrative continuation. A deceased character must not use an
  ordinary retirement-reactivation path.
- Retirement is a distinct explicit authoritative transition for a living
  player character. It changes the character from active to `retired` and ends
  that character's current continuous story line.
- Player-character retirement requires either an explicit player choice or the
  player's explicit confirmation of a proposed retirement transition.
- Player-character retirement must not be inferred silently from narrative
  behavior, temporary absence, exhaustion, withdrawal from an organization,
  ambiguous dialogue, or reduced participation.
- A retired player character must not be reactivated silently. Reactivation
  requires an explicit player-confirmed authoritative transition and continues
  the same stable player-character identity.
- The later structured player-character contract must determine the applicable
  versioning, compatibility, validation, and data representation for retirement
  and reactivation.
- A newly created player character remains a distinct identity. It does not
  inherit the identity of a character in the `deceased` or `retired` state
  merely because the same account controls both.
- Any continuity of memories, relationships, consequences, or identity claims
  between a new character and a character in the `deceased` or `retired` state
  requires an explicitly authorized narrative relationship. The system must
  not infer or transfer that continuity silently.

These are product-level lifecycle and identity invariants. They do not select
one metaphysical explanation or prescribe a DTO, database schema, endpoint,
migration, or storage representation.

## Internal narration and player agency

### Narration preferences

The formal character contract must support three narration preferences:

| Preference | Presentation direction |
| --- | --- |
| `high-immersion` | More immediate sensations, involuntary reactions, and bounded associations grounded in confirmed context |
| `balanced` | A measured mix of external action, sensation, and tentative internal response |
| `high-agency` | Minimal inferred interiority, leaving interpretation and intentional judgment primarily to the player |

`balanced` is the recommended default.

All three preferences preserve the same authority boundary:

- The model may describe immediate sensations, involuntary reactions, and
  bounded associations to the degree permitted by the selected preference.
- Even in `high-immersion`, narration must not decide whom the player loves,
  trusts, forgives, or fears, or what final moral position the player holds.
- Narration must not convert a momentary sensation or association into a
  settled belief.
- The player remains final authority over intentional beliefs and actions.

The exact prompt representation, examples, sensitivity controls, and preference
change workflow are Deferred.

### Sovereignty over subjective inner states

The following player-character states may become authoritative only through
explicit player expression or confirmation:

- beliefs;
- values;
- love or hatred;
- trust or forgiveness;
- fear;
- guilt;
- regret;
- moral conclusions;
- emotional commitments; and
- equivalent subjective internal conclusions.

The system may describe observable player actions, record objective
consequences, present justified sensations or involuntary physical responses,
and offer possibilities, questions, or non-binding interpretations. It must
not convert inferred player psychology into settled canonical fact.

When later continuity depends materially on a subjective internal state, the
player must have explicitly expressed or confirmed that state.

### Objective relationships and player attitudes

These domains remain separate:

- Server-authoritative relationship facts may include shared events, promises,
  obligations, reputation, NPC attitudes toward the player, and other
  observable or externally grounded relationship consequences.
- The player character's feelings toward an NPC remain under player
  sovereignty unless the player explicitly expresses or confirms them.
- An NPC's opinion of the player must not be presented as proof of the
  player's reciprocal feelings.

## NPC hierarchy and golden long-term memory

### Conceptual NPC groups

The long-term system distinguishes three conceptual groups:

| Group | Meaning | Retention direction |
| --- | --- | --- |
| System-core NPCs | NPCs with major hidden setting information, world structure, irreplaceable narrative functions, or required future callbacks | Protected from automatic eviction |
| Player-shaped important NPCs | NPCs whose importance is established primarily through actual player attention and investment, with secondary future narrative potential | Eligible for protected golden-memory retention and later callbacks |
| Temporary NPCs | Local or functional NPCs without current long-term importance | May remain bounded, compacted, forgotten, or promoted when validated evidence changes |

These groups describe long-term narrative treatment, not physical power,
morality, relationship polarity, or current schema types. A temporary NPC may
become important; a player-shaped important NPC may gradually lose importance.
System-core protection is an authored engine property and must not be inferred
by the model.

### Logical identity and counterparts

- An important NPC has a stable logical identity independent of a particular
  Run instance, scene instance, or reusable content definition.
- Reusing a template, role, name, appearance, or archetype does not establish
  identity continuity.
- Parallel-world counterparts, reincarnations, replacements, copies,
  disguises, and alternate versions are distinct identities by default.
- Such an NPC becomes continuous with an earlier identity only when
  authoritative narrative state explicitly establishes the relationship and
  the consequences that relationship permits.
- Death, survival, relationship consequences, and golden memory must attach to
  the correct logical identity.
- Identity relationships such as counterpart, reincarnation, copy, or
  successor must not silently collapse distinct NPCs into the same identity.

These rules are genre-general. They do not impose one metaphysical explanation
on every scenario, and they do not prescribe an identity schema.

### NPC lifecycle authority

The player-choice and player-confirmation requirements for retirement and
reactivation apply only to player characters. They do not prevent NPC death,
retirement, disappearance, sacrifice, permanent departure, or other lasting
consequences. NPC lifecycle changes do not require player consent.

An NPC lifecycle change may be established by:

- an explicit server-authoritative narrative event;
- a validated player action and resulting state transition; or
- an authoritative scenario or system adjudication.

The following authority and identity limits also apply:

- No permanent lifecycle state for any character may be inferred solely from
  ambiguous narration, temporary absence, suggestive dialogue, or uncommitted
  model output.
- An NPC's death, retirement, or permanent departure must be established
  through an explicit authoritative event or validated state transition.
- Important-NPC consequences must bind to the correct stable logical identity.
  Death, survival, relationships, protected golden memory, and world
  consequences must remain attached to that identity.

This boundary does not prevent an NPC from being killed or written out of the
story; it requires only that the lasting consequence be authoritatively
established and identity-bound.

### Importance model

Ordinary NPC importance must be driven primarily by actual player attention and
investment, with secondary consideration for future narrative potential.

The initial design recommendation is the following provisional heuristic:

- approximately 70% player attention and actual investment;
- approximately 30% future narrative potential.

This ratio is for calibration and evaluation. It must not be treated as a
permanent hard-coded product constant.

Positive and negative relationships can both make an NPC important. Relevant
evidence may include:

- repeated voluntary contact;
- cross-scene attention;
- protection or sacrifice;
- pursuit or investigation;
- explicit player expressions of fear, trust, hatred, guilt, or suspicion; and
- giving up a meaningful advantage.

Lower-weight evidence includes:

- forced dialogue;
- task-required questioning;
- NPC monologues; and
- purely functional information gathering.

Importance must rise and fall gradually. One line of dialogue, one model
assertion, or one required interaction must not normally cause immediate
promotion, demotion, or eviction. Exact signals, decay, hysteresis, thresholds,
caps, and tie-breaking are Deferred.

The model may emit candidate attention or externally grounded relationship
signals. Before any importance, relationship, or golden-memory change, the
server must validate the candidate against the actual player action,
authoritative context, and trusted event history. A candidate signal cannot
establish the player character's subjective attitude.

### Golden long-term memory

Golden memory is a protected, bounded tier of validated narrative records and
callback anchors. It is not an indefinite raw transcript.

This specification distinguishes:

| Memory class | Product meaning |
| --- | --- |
| Protected golden memory | Validated, identity-bound facts and callback anchors protected by the rules below |
| Ordinary bounded summaries or replaceable context | Non-golden context governed by its narrower bounded-retention contract |
| Candidate information | Untrusted or not-yet-promoted information with no authoritative memory status |

- System-core NPC records are protected from automatic eviction.
- Player-shaped important NPCs may enter or leave golden protection only
  through gradual, server-owned evaluation.
- Golden records may preserve validated shared experiences, relationship
  facts, promises, debts, explicitly player-expressed or confirmed regrets,
  unresolved conflict, important facts, and callback value.
- A protected record preserves narrative continuity; it does not force an NPC
  to appear in every scenario.
- Golden-memory protection does not give an NPC physical plot armour. An NPC
  may be injured, changed, lost, or killed when an authoritative outcome
  permits it, while the consequential record and callback value remain.
- Compaction must preserve authoritative meaning and provenance boundaries.
  Accepted prose may inform a candidate, but model text alone is not a
  long-term fact.

When protected golden memory approaches or reaches its bounded capacity:

1. First apply safe compression that preserves protected facts, their meaning,
   provenance, logical-identity binding, and relevant uncertainty.
2. Compression must not silently alter, merge, weaken, or invent protected
   facts.
3. If safe compression is insufficient, do not silently overwrite or evict
   existing protected memory.
4. Refuse the new promotion to protected golden memory, or reject content
   admission that would require an additional system-core NPC beyond the
   supported bound.
5. Surface the refusal as an explicit authoritative outcome suitable for later
   recovery or adjudication.

Capacity pressure alone must not cause a protected record's demotion or
eviction.

Exact numerical capacity, promotion and demotion events, safe-compression
algorithm, public projection, logical-identity representation, compatibility
schema, and persistence schema are Deferred.

## Multi-genre infinite-flow structure

### Genre breadth

The product is not limited to urban anomaly, rules horror, or modern
supernatural fiction.

The same long-term player character may enter original scenarios involving,
among others:

- urban anomaly;
- xuanhuan;
- xianxia;
- Western fantasy;
- science fiction;
- wasteland or apocalypse;
- historical fantasy;
- mystery;
- comedy and absurdism;
- anime-inspired presentation; and
- mixed genres.

This list demonstrates breadth and is not a closed genre enum.
Anime-inspired design is primarily a presentation and narrative-language
dimension, not one fixed world category.

### Scenario dimensions

Scenario definition must conceptually separate dimensions such as:

| Dimension | Examples of what it controls |
| --- | --- |
| World genre | Metaphysical and social genre foundation |
| Narrative mode | Investigation, survival, journey, intrigue, comedy, or another dramatic structure |
| Emotional tone | Dread, wonder, warmth, melancholy, absurdity, or a deliberate mixture |
| Local world rules | Scenario-specific metaphysics, constraints, institutions, and causal rules |
| Main objective | The central situation the player may need to change, survive, understand, protect, or resolve |
| Presentation style | Linguistic, visual, pacing, or anime-inspired expression |

These names are conceptual and do not freeze one schema.

Scenarios must not merely reskin the same urban-anomaly structure. Individual
scenarios may have substantially different metaphysics, social structures,
conflict forms, humor, pacing, and rules.

All commercial-facing scenarios and characters must remain original. They must
not directly reproduce copyrighted fictional worlds or characters. Genre
influence and presentation vocabulary do not authorize copying plot, names,
prose, equipment, skills, characters, or distinctive setting elements from
reference fiction.

## Cross-scenario continuity

The shared foundation across genres is the persistent player and the
upper-level infinite-flow structure, not identical surface rules.

Cross-scenario continuity may preserve:

- character identity and appearance;
- important injuries and scars;
- abilities and restrictions;
- important items;
- explicitly player-expressed or confirmed psychological and belief changes;
- golden-memory NPCs;
- externally grounded promises and debts, plus explicitly player-expressed or
  confirmed regrets;
- recovered hidden-setting information;
- behavior-derived observations that do not settle subjective inner states; and
- death and rebirth consequences.

Local scenario rules remain scenario-specific. A carried ability, item,
condition, or relationship must not silently bypass the rules of a destination
scenario. Eligibility, translation, suppression, cost, and compatibility are
engine-owned and Deferred to structured contracts.

The upper-level system must preserve validated consequences without requiring
every world to share the same metaphysics, power scale, resource vocabulary, or
conflict mechanics.

## Generalized narrative conflict and combat

### Conflict scope

Combat is one form of narrative conflict, not a mandatory independent mode.
Conflict remains inside the continuous novel flow.

The system must support conflicts expressed through:

- physical combat;
- magic;
- cultivation systems;
- formations and artifacts;
- technology and machinery;
- individual anime-style abilities;
- negotiation;
- deception;
- pursuit;
- protection;
- escape;
- environmental manipulation; and
- intentionally absurd but locally consistent rules.

The engine must not be designed around modern weapons, urban rooms,
conventional HP bars, or a fixed `attack`/`defend`/`skill`/`flee` menu.

### Authoritative reasoning concepts

A generalized authoritative conflict model must be able to reason about:

- actor capabilities;
- local world rules;
- position and relative advantage;
- environmental opportunities;
- equipment or ability media;
- resources or energy;
- activation conditions;
- costs and backlash;
- actor intentions;
- conflict objective;
- injuries or impairments;
- danger clocks; and
- deterministic server-owned randomness.

These are required conceptual capabilities, not a frozen class model or
database schema.

### Flow and outcomes

- A player choice represents a meaningful situation-changing segment, not one
  trivial exchange of attacks.
- Failure should move the situation forward through cost, consequence, lost
  position, new danger, revelation, or another changed circumstance.
- Conflict goals may include survival, escape, protection, delay,
  investigation, negotiation, seizure, interruption, restraint, or killing
  when appropriate.
- The authoritative server owns outcome resolution, randomness, injuries,
  impairments, resource changes, deaths, and other state mutation.
- The model expresses an already-authorized result as narrative prose. It does
  not decide the authoritative outcome after the fact.

Death and rebirth belong to the upper-level long-term system and must carry
consequences under the player-character continuity rules above. Death must not
become a cost-free brute-force answer mechanism. Exact resolution rules,
randomness primitives, conflict clocks, injury representation, rebirth
availability, and consequence schedules are Deferred.

## Model and server authority boundary

The central rule is:

> The model generates candidate narrative content; the local authoritative
> server owns persistent state and final mutation decisions.

The model may generate candidates for:

- narrative prose;
- exactly three contextual action suggestions for a normal player-initiated
  narrative decision turn;
- NPC-attention signals;
- externally grounded relationship facts or NPC attitudes;
- character-development observations;
- potentially valuable long-term memories; and
- conflict narration.

The server must authoritatively decide:

- the action actually submitted by the player, preserving its intention through
  any normalization;
- whether and how state changes;
- character-profile updates;
- NPC promotion or demotion;
- golden-memory writes;
- cross-scenario facts;
- injuries, resources, abilities, deaths, and endings; and
- validation and safety acceptance of model output.

Candidate output must be bounded, validated, and rejected safely when it
conflicts with authoritative state or policy. Validation does not itself turn a
candidate into canon; a trusted server decision and atomic persistence boundary
are still required.

### Provider failure and recovery

- Provider failure must not advance authoritative game state.
- Provider failure must not silently switch to another Provider.
- The system must enter an explicit recoverable error condition.
- Recovery must preserve the last committed authoritative state.
- After recovery, suggestions or candidates may be regenerated and therefore
  need not be textually identical.
- No regenerated model output becomes authoritative until it passes the normal
  validation and commit boundary.

This invariant does not introduce a new Provider architecture, change current
Provider-selection or retry configuration authority, or make the deterministic
Demo Provider a fallback. Exact error projection and recovery interaction are
Deferred to later versioned contracts.

## Current deterministic Demo boundary

The current deterministic Demo remains useful for regression tests, scenario
validation, and fixed input/output evidence.

- Its current panel-heavy UI is not the final player-facing visual foundation.
- Its five fixed character presentations are not the only formal-game
  characters.
- Urban anomaly and procedural-record themes are one validated vertical slice,
  not the whole product identity.
- Its fixed action affordances validate the current public contract; they are
  not the final three-option-plus-free-action presentation.
- This specification does not retroactively invalidate or require unnecessary
  rewriting of completed Phase 3.2b Demo implementation work.

The authoritative review and closure status of Phase 3.2b remains governed by
`PLANS.md` and the Demo phase document. This specification neither closes nor
reopens that phase and does not change its history.

## Bounded future implementation sequence

The following order is planned future work. Except for creating and freezing
this specification, it does not claim that any step is implemented:

The third independent read-only review approved this specification with no
HIGH, MEDIUM, or LOW findings. This closeout does not implement any requirement
or begin the structured player-character contract. That contract is the next
planned specification task and may begin only after this approved closeout has
been committed and pushed.

1. Complete the separate approved-specification closeout and confirm the
   approved version is committed and pushed.
2. Define the structured player-character contract.
3. Define NPC importance, relationship, and golden-memory candidate events.
4. Define the three-option-plus-free-action output contract.
5. Design a low-fidelity reading-first interface.
6. Build one final-UX vertical slice using an existing deterministic scenario.
7. Validate reading rhythm, prose length, option quality, player agency, and
   NPC-attention recognition.
8. Define and test one generalized short conflict slice.
9. Expand into broader scenario genres only after the shared contracts are
   validated.

Each later step must update `PLANS.md` with accurate phase placement before
implementation. No step may be described as implemented or complete solely
because this specification exists.

## Deferred design work

The following remain Deferred while the product decisions above stay frozen:

- exact player-character DTOs, validation vocabularies, persistence, editing,
  authoritative identity transition, migration, and public projection;
- exact death, retirement, continuity, resurrection, and replacement
  representation;
- prompt-compiler schema and compatibility policy;
- internal-narration prompt representation and sensitivity controls;
- exact NPC signals, scoring, decay, hysteresis, thresholds, numerical
  capacity, safe-compression algorithm, logical-identity representation, and
  compatibility schema;
- exact option-generation, exceptional-turn, free-action, and clarification
  contracts;
- exact Provider-failure error projection and recovery interaction;
- final interface layout, accessibility, streaming, and navigation behavior;
- scenario-dimension schema, genre catalogues, eligibility, ordering, and
  compatibility rules;
- cross-scenario ability, item, injury, and restriction translation;
- generalized conflict state, resolution, deterministic-randomness, injury,
  death, and rebirth contracts; and
- phase numbers, migrations, test matrices, and rollout plans for these
  systems.

## Non-goals of this design freeze

This task does not implement:

- the final UI or character-creation flow;
- NPC importance, relationship, residence, or golden-memory runtime behavior;
- generalized conflict or combat resolution;
- model transport or prompt compilation;
- a production Provider or Production Distribution Gateway;
- database, API, snapshot, or migration changes;
- new scenarios or commercial content;
- secrets, network calls, external dependencies, or production readiness.

Every future state mutation introduced under this specification requires the
repository's normal authority, atomicity, regression-test, migration, and
documentation review.
