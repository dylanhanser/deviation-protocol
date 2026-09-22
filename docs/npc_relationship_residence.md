# NPC Relationship and Temporary Residence

Status: **First bounded slice implemented as an uncommitted candidate; broader Phase 3.4 remains incomplete.**

Phase ownership: **Phase 3.4**

## First bounded slice: 雾哨站

The owner authorized this slice against published baseline
`96200883dd00d8639c91579b9518175e197ce856`. It is not an independent approval,
browser acceptance, local commit or claim of full Phase 3.4 completion.
The following exact rules supersede the deferred questions below only for
this authored encounter. The broader product direction remains unchanged.

### Content, entry and cost

`config/scenarios/fog_station_v1.json` is original content, pinned as
`fog_station / fog-station-1.0.0`, raw UTF-8 SHA-256
`898b2557f56d6f41263e1f088358df871453d351f2fce79a8e379416d5873a7b`.
Adult patrol officer 岑舟 is 32. The station interior and outside observation
platform form one bounded location. Strange lights and an unstable shutter
provide exploration and environmental conflict; there is no puzzle chain.

`world.fog_station / 1` is the second formal native starting world. Existing
owned-character selection, three difficulty profiles, frozen opening preparation,
two-of-five CURRENT talent confirmation and atomic native admission are reused.
Per-world Session services resolve exact content for initialization and successful
confirmation replay. Normal application and deterministic Demo install the same
content, policy and local authored-text turn orchestrator; no Provider is invoked.
It is not a standalone Session launcher or a continuation destination. Frozen packs
and all published continuation/revisit edges remain unchanged.

Every accepted gameplay submission is a bound `CHOOSE`. The pack explicitly maps
`choose` to an empty clock-advance list and declares no threat clocks or auto-beat
clock advances. Thus encounter, cooperation, delay, work, acceptance/decline, each
activity, departure, outside observation and farewell each commit one Session
version, but **advance no action clock and deduct no resource**. Rejected actions,
GET/refresh and exact replay advance neither. The delay cost is closing the
immediate-departure branch and requiring one additional explicit authored action.
There is no injury, hidden penalty, danger clock, reward, growth or gift economy.
Published talents still affect only additional costs of their four published
action types; they do not affect CHOOSE, manufacture a missing clock, or change
residence slots. All 100 entries, 12 CURRENT effects and 88 FUTURE exclusions remain
unchanged. Difficulty and relationship overlay do not change this finite lifecycle.

### Authorized transitions

| Before / condition | Explicit accepted choice | After / player impact |
| --- | --- | --- |
| Native participation, actual visible NPC instance | Approach and meet 岑舟 | 相识; no shared achievement yet |
| 相识 | Cooperate to secure the shutter | 合作; first unique advancement |
| 合作, danger resolved | Leave immediately | Authored ending, no residence |
| 合作 | Delay departure to help | Immediate departure closes; one work action required |
| Work pending | Complete observation-record work | 信任; second and last advancement; invitation opens |
| Invitation | Decline | Authored ending; cooperation/work history retained |
| Invitation | Accept residence | One residence entry; three activity slots |
| Residing | 复盘脱险 / 听一段已公开的巡路往事 / 一起整理观察记录 | Each once, any order; each consumes one slot; no stage gain |
| Residing, including zero remaining slots | Explicit departure | Permanently closes residence for this encounter; no slot cost |
| Departed | Check the light along the outside platform railing | One optional farewell becomes available |
| Outside observation complete | Return to the doorway, or finish without return | Authored ending; return references only actual shared activities; no gain/reward/re-entry |
| Authored ending | Existing explicit native Run exit | Run terminates and releases the existing character binding |

Three used slots leave departure as the only residence action. Entry and departure
are distinct submissions. Reading, repetition under another request key, stale
choices, retries and ordinary chat cannot farm progress. The ordinary action
pipeline retains ownership, native participation, lifecycle, version, lock,
receipt, atomic commit and exact-response replay boundaries.

### Identity, persistence and shared experience

`FogStationPolicy` validates the complete finite decision path against the pinned
content: ordered decisions and exact outcome evidence must agree with phase,
location, progress fact, transition/visit counts and ending. Runtime NPC identity
is bound to Session ID and the explicit authored logical reference
`authored-person.cen-zhou/v1`, mapped to this exact pack's `npc.fog_station.cen_zhou`.
Catalog presence alone creates neither encounter nor trust. Existing
`NpcState.relationship_bps` remains zero and is not a competing stage authority.

The bounded relationship state is a deterministic interpretation of the existing
typed `ScenarioRuntimeState` progress fact and decision outcome evidence. These
are already stored in `game_snapshots.state_json` with `domain_events`, response
receipts and local narrative jobs in the same transaction. No extra mutable
relationship copy, table, schema migration, old-snapshot rewrite or old-Run backfill
is introduced. A failed commit preserves the prior relationship and all slots.

The read-only `PlayerSessionView.relationship` projection retains at most five
structured-experience presentations: cooperation, completed work, one residence
record (at most three actual activity codes), departure and optional farewell.
They remain readable after departure and Run exit. No transcript or model summary
is retained as relationship memory. `PlayerMemoryState` continues its existing
trusted scenario-start/completion indexing; the bounded relationship projection
is **not** an NPC-index update or a claim that its memory index contains these
experiences. See [player_memory.md](player_memory.md) for this explicit boundary.

The first slice verifies only a reunion in the **same Session**. Later-Session
recovery within the same Run and cross-Run inheritance are not implemented. A
local NPC definition/subject key, repeated name or logical reference does not
authorize transferring trust, residence, promises or memories into another Run.
Fresh admission starts unacquainted. Golden-memory retention, cross-Session NPC
participation, universal relationship mechanics and Provider dialogue are later
work; this slice does not complete their Phase 3.4 acceptance criteria.

### Verification boundary

`tests/unit/test_fog_station.py` drives the public deterministic native admission
and all residence activity orders, early departures, decline/immediate endings,
replay, concurrent duplicate submissions, rollback, forged/stale choices,
ownership and corrupted snapshots. It checks zero clock/resource cost, actual-only
farewell text, journey recovery, recap and explicit Run exit. Web tests exercise
second-world preparation, bounded display, historical read-only rendering and
identity/schema rejection. Automated rendering is not browser acceptance.

`tests/integration/test_mysql_fog_station.py` provides the corresponding real
production-service/Repository test on the configured dedicated MySQL test database
at actual head `20260921_0012`, without DDL. It scopes cleanup to generated test
rows. The final dedicated-MySQL run passed all three selected routes, including
concurrent confirmations/submissions, rollback, fresh-service recovery and exit.
Its wrapper recorded the initial empty test database at `20260916_0007`, deployed
the actual head, then restored the exact schema, data and constraints. The initial
cleanup-order failure and its scoped repair remain recorded separately; that
failed run is not a pass. No application migration or user-data change was needed.
Browser acceptance and independent review are still pending; no full Phase 3.4
or limited-trial readiness is claimed by this implementation candidate.

Final scoped Offline verification passed 227 tests, compileall, dependency checks,
Alembic metadata and Git diff checks. The complete Web run passed 528 tests with
one existing skip; typecheck, lint and build passed. These are separate selections,
not additive totals. Earlier interrupted runs, temporary-path failures and the
corrected non-hospital composition fixture remain historical evidence, not passes.

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
