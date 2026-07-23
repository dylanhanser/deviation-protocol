# NPC Relationship and Temporary Residence

Status: **Approved product design — not implemented**

Phase ownership: **Phase 3.4**

## Design purpose

This system is intended to create emotional attachment and a lower-pressure
contrast between dangerous scenario-progression periods.

> Players may return not only because a task remains, but because a meaningful
> NPC and shared place remain emotionally important.

It is not a generic unlimited AI companion chat system. Residence is bounded,
engine-authorized, tied to important NPCs, and temporary.

## Goals

- Make meaningful NPC relationships persist across selected narrative
  consequences without turning conversation volume into progression authority.
- Provide a limited fixed-scene pause between dangerous progression periods.
- Preserve a bounded set of shared memories with future relational or narrative
  value.
- Allow everyday dialogue and presentation variation while keeping permanent
  relationship state and canon engine-owned.
- Give departure and impermanence structural emotional value.

## Non-goals

- Unlimited or consequence-free AI chat.
- Residence for every NPC.
- Relationship farming through repeated messages.
- Model-authored relationship upgrades, permanent promises, major secrets,
  recruitment, betrayal, or canon.
- Choosing a Provider pricing model during Phase 3.4 design.
- Implementing the anticipated state fields in the current schema.

## Core lifecycle

1. The player develops a relationship with an eligible important NPC.
2. Engine-confirmed relationship progress unlocks a temporary residence
   opportunity.
3. The player may choose to pause main progression.
4. The player and NPC remain in a fixed scene for a limited period.
5. Available activities may include:
   - daily conversation;
   - eating together;
   - asking about the past;
   - giving an appropriate gift;
   - dealing with small shared events;
   - reflecting on prior experiences.
6. Residence ends through an engine-confirmed trigger.
7. After departure, the NPC may:
   - continue travelling;
   - remain at a location;
   - become unavailable or lost;
   - return in a later scenario;
   - become relevant to a later hidden setting or major event.

Example residence scenes may include a safe house, camp, clinic, train
carriage, or another authored fixed location. These are examples, not currently
implemented content.

## Eligibility and narrative value

Not every NPC supports residence. Eligibility is limited to important NPCs or
NPCs with meaningful future recovery value, such as:

- important hidden setting or lore;
- major character development;
- future scenario relevance;
- a later reunion or consequence;
- a unique relationship arc.

Ordinary disposable NPCs do not create permanent recovery obligations without
narrative value.

## Authority table

| Engine owns | Model may do |
| --- | --- |
| Relationship stage and flags | Express the NPC's established personality |
| Residence eligibility, activation, and duration | Generate bounded everyday conversation |
| Important events and permanent promises | Vary wording and minor topics |
| Major secrets | Reflect confirmed shared memories |
| Departure triggers | Present approved small events |
| Permanent state changes | — |
| Canon and later NPC recovery | — |

The model must not independently:

- upgrade relationship stages;
- manufacture affection through repeated message volume;
- make binding promises;
- reveal major secrets;
- make an NPC betray or permanently join the player;
- extend residence indefinitely;
- change canon;
- create permanent state transitions.

## Relationship progression

- Ordinary daily chat does not permit unlimited relationship farming.
- Important progression comes from engine-confirmed events and meaningful
  player choices.
- A daily or residence-period relationship-gain cap is anticipated.
- Relationship atmosphere in the Run Protocol changes presentation only.
- Objective relationship progression is a separate engine-owned system.

Exact stages, thresholds, formulas, and caps are Deferred.

## Run Protocol relationship

The future Run Protocol's `off`, `veiled`, or `charged` relationship overlay
may alter tension, restraint, subtext, and expression during eligible dialogue.
It does not change relationship stage, residence eligibility, bond gain,
promises, secrets, departure, or permanent facts. Difficulty/world tone and
relationship atmosphere remain separate authorities.

## Persistence and memory boundaries

The accepted direction is:

- do not preserve the full conversation transcript indefinitely;
- extract bounded structured memory;
- retain only information with future relational or narrative value.

Possible memory categories include:

- shared experiences;
- player promises;
- NPC promises;
- preferred forms of address;
- revealed personal facts;
- unresolved conflict;
- important relationship flags.

The existing [player memory design](player_memory.md) remains the authority for
implemented memory behavior. The detailed integration contract with player
memory will be designed during Phase 3.4. This document does not claim that
relationship conversation memory or residence fields exist today.

## Departure and impermanence

Residence is temporary rather than a permanent consequence-free chat room.
Possible engine-owned departure triggers include:

- resource pressure;
- external threat;
- the NPC's personal objective;
- a new scenario opening;
- a time or event limit;
- an unresolved conflict.

The limited duration is part of the emotional and structural design. Only an
engine-confirmed trigger ends residence or changes the NPC's later
availability.

## Provider cost and abuse boundaries

Daily free-form conversation may become a major source of Provider usage.
Production authentication, quota, metering, rate limiting, and abuse controls
belong to [ADR 0001](decisions/0001-production-provider-distribution.md).
No pricing model is selected here. The deterministic Demo Provider is not
evidence of a commercial dialogue service or fallback.

## Anticipated state

The following are anticipated design fields, not implemented schema:

- `relationship_stage`
- `relationship_flags`
- `residence_scene_id`
- `residence_status`
- `residence_days`
- `shared_memory_summary`
- `daily_bond_gain_cap`
- `npc_personal_goal`
- `departure_trigger`

Phase 3.4 must decide their validated representation, ownership, persistence,
compatibility, and public projection before implementation.

## Implementation acceptance criteria

Phase 3.4 is acceptable only when:

1. Eligibility is explicit in trusted game design or engine state.
2. Relationship progression comes from engine-confirmed events and meaningful
   choices, with enforced anti-farming bounds.
3. Residence activation, duration, activities, and departure are bounded and
   engine-authorized.
4. Model dialogue cannot mutate relationship stage, promises, secrets,
   residence duration, NPC availability, permanent state, or canon.
5. Relationship atmosphere changes presentation only.
6. Structured memory is bounded, validated, and integrated through an explicit
   player-memory contract rather than indefinite transcript retention.
7. Important NPC recovery and later relevance have authored, testable identity
   and persistence rules.
8. Provider usage and abuse boundaries integrate with the future production
   distribution design without exposing credentials.
9. Every state mutation has regression coverage and atomic persistence
   semantics.
10. Documentation and phase status are synchronized before audit or completion.

## Deferred questions

- Residence duration.
- Relationship stages and thresholds.
- Relationship-gain caps.
- Eligible NPC authoring schema.
- Exact fixed-scene interaction set.
- Departure algorithm.
- Structured-memory schema.
- Context-compaction frequency.
- Per-session or per-day dialogue allowance.
- Commercial quota and pricing interaction.
- Whether to design an offline dialogue mode whose availability and design
  remain Deferred. Any such mode would require explicit selection, would not be
  a silent or automatic cross-Provider fallback, and the deterministic Demo
  Provider must not be used or reused by any commercial mode or service,
  whether as a fallback, an explicitly selected offline mode, or otherwise.

## Related documents

- [Project roadmap](../PLANS.md)
- [Run Protocol design](run_protocol.md)
- [Implemented player memory](player_memory.md)
- [Narrative Provider boundary](narrative_provider.md)
- [Production Provider distribution ADR](decisions/0001-production-provider-distribution.md)
