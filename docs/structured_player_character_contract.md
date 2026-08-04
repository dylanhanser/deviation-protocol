# Structured Player-Character Contract

Status: **Approved and frozen structured player-character product
specification — partially implemented through completed Phase 3, Minimum Run
Core, completed internal-only P4-S1 binding, and completed, published Phase 5
through P5-S3 public activation, plus completed and published P8-S3 normal Run
entry, P8-S4 deterministic Demo parity, and P8-S5 minimum Web connection.**

Authority scope: **Normative player-character identity, canonical record,
revision, lifecycle, validation, projection, and adjacent-authority
boundaries**

## 1. Status and authority

This document is the approved and frozen structured player-character product
specification. Its Phase 1 through Phase 3 foundation is implemented,
independently approved, committed, and pushed. Minimum Run Core is also
implemented, independently finally approved, committed, and pushed as
`e821cd922b61868097667b12c2b64cf8089a9681`
(`feat(run): implement minimum run core`). Its null-only seam is historical:
P4-S1a is implemented at `748003319ececa548b68b351746afbb2d54c66bb` and
P4-S1b at `8eabf9d4c3c592ea1de50f443f1816de9a46dc8f`. The Run-owned binding is
implemented internally only. P5-S1 owned read and P5-S2 creation/replay are
published. P5-S3 received `STRUCTURED_PLAYER_CHARACTER_P5_S3_PLAN_APPROVED`.
Its first, first-corrected, and re-corrected local retirement implementation
candidates each received `CHANGES_REQUIRED`. A later evidence candidate's
receipt-add 1062 depended on rolling back the original mutation transaction and
resuming stale in-memory work. The focused investigation returned
`P5_S3_RECEIPT_ADD_RACE_NOT_REACHABLE_UNDER_CURRENT_PRODUCTION_PATH`, so the
accepted implementation proves normal HTTP
serialization at the aggregate lock and labels defensive recovery evidence as
fault injection. Correction validation completed locally (canonical Offline
1,814 passed/124 expected skips, MySQL 136 passed, and Full 1,937 passed/one
  opt-in Provider skip). Its focused final independent review returned
  `STRUCTURED_PLAYER_CHARACTER_P5_S3_FOCUSED_FINAL_REVIEW_APPROVED`, finding no
  material scoped defect. It accepted real-MySQL aggregate-lock serialization,
  exact replay or ordinary idempotency conflict, and one durable mutation; fault
  injection is bounded defensive recovery only, and the unreachable receipt-add
  race is not a requirement. P5-S3 was committed and published as
  `34d063e387cde69500e4dc018ff087e87f3eee74`
  (`feat(player-character): add idempotent retirement endpoint`). Phase 5 is
  complete at P5-S3; no P5-S4 exists and no P5-S3 review remains pending.
  P5-S3 is not a current unstaged candidate, and Phase 8 planning does not
  reopen Phase 5. Deployment, release, broader runtime activation, and Provider
  work remain deferred.
  A standalone public Run-binding command is not implemented; the reserved
public `RunService.bind_player_character(...)` command remains rejected.

The approved and frozen
[Final Narrative Experience and Long-Term Systems](final_narrative_experience.md)
specification governs the cross-phase product requirements translated here.
It remains approved, frozen, and not implemented. Phase 3.2b remains closed.
Existing narrower implemented and approved contracts retain authority over
their current domains, including the
[architecture](architecture.md), [Run Protocol](run_protocol.md),
[public client contract](public_client_contract.md),
[Narrative Provider boundary](narrative_provider.md),
[player-memory contract](player_memory.md), and
[NPC relationship and residence design](npc_relationship_residence.md), plus
the implemented [engineering guardrails](engineering/guardrails.md) and
[Codex workflow](engineering/codex_workflow.md).

This contract MUST NOT silently redefine existing runtime behavior. A material
conflict with an approved product requirement or a retained narrower authority
MUST block the affected later phase and be resolved explicitly. Further
implementation MAY begin only through the approved downstream implementation
plan and a separately authorized task.

## 2. Purpose

This contract translates approved player-character requirements into an
explicit, versionable data and transition boundary. It defines the minimum
logical record, identity references, mutation authority, compatibility rules,
lifecycle transitions, projections, and failure behavior that later design and
implementation must preserve.

Its goal is consistent reasoning across later runtime, persistence, API,
Provider, client, Run, world, memory, and NPC work without selecting those
systems' implementation architecture.

## 3. Scope

This contract covers:

- stable canonical player-character identity;
- separation of controller, character, Run, world, NPC, Provider, transport,
  and request identities;
- the minimum canonical record and its authoritative field groups;
- contract-version and canonical-record-revision semantics;
- canonical creation, validation, mutation, and atomic rejection;
- `active`, `retired`, and `deceased` lifecycle states;
- explicit retirement, reactivation, final death, and authorized continuity
  boundaries;
- player sovereignty over subjective inner states;
- Provider-candidate, client-intent, server-authority, and public-projection
  boundaries;
- conceptual Run, world, memory, NPC relationship, and golden-memory
  references; and
- downstream obligations that must be satisfied before implementation can be
  accepted.

## 4. Explicit non-goals

This contract does not:

- implement runtime code, persistence, database schema, migrations, APIs,
  DTOs, frontend state, tests, or deployment;
- define a complete character-creation user experience;
- add biography, class, origin, body, stats, inventory, progression, combat,
  skills, abilities, possession, inheritance, cloning, merging, deletion,
  transfer, or character-switching systems;
- decide account/controller character limits or how many distinct canonical
  characters one controller may keep active; this does not weaken the frozen
  at-most-one-active-story-line-per-character binding rule;
- define exact movement or transition mechanics, compatibility mechanics,
  arbitrary movement between unrelated Runs, transfer between separate
  continuous story lines or accounts, or cross-Run concurrency beyond the
  frozen at-most-one-active-line-per-character rule;
- decide whether a particular resurrection, rebirth, reincarnation, time
  reversal, or equivalent event preserves identity;
- decide whether time reversal removes already authoritative consequences;
- define memory storage, golden-memory capacity, NPC identity storage, or
  relationship progression;
- change the current Session, request, public-client, Provider, Run, snapshot,
  or player-memory contracts; or
- reopen Phase 3.2b.

## 5. Normative terminology

The keywords **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY**
are normative when capitalized.

| Term | Meaning in this contract |
| --- | --- |
| Canonical | Accepted by a trusted server authority and atomically committed as the current player-character record or an authoritative referenced fact |
| Candidate | Structured or unstructured material that has not acquired mutation authority |
| Controller | The authenticated account, principal, or equivalent trusted subject permitted to submit intent for a character |
| Player-authored declaration | A declaration intentionally submitted or explicitly confirmed by the controller through a trusted player workflow |
| Stable player-character identity | The immutable logical identity of one canonical player character |
| Continuous story line | Run-owned product-level narrative continuity with exactly one active player-character binding once bound; one character may belong to at most one active line |
| Authoritative transition | A validated, authorized, atomic lifecycle mutation issued by trusted server policy |
| Public projection | An explicit allowlist view safe for the intended client audience; never a mutable canonical object |
| Provider candidate | Untrusted model output, including output that is structurally valid |
| Uncommitted narration | Prose not included in the same successful authoritative commit as the facts it is permitted to express |
| Absence | A missing optional value; it is not permission to infer or invent the value |

The current repository field `RequestPrincipal.player_id` identifies the
trusted principal used for Session ownership. In this contract that existing
identity is treated as a controller identity. It MUST NOT be interpreted as
the new stable player-character identity.

## 6. Identity-domain separation

Identity equality is domain-specific. Equality in one row below MUST NOT imply
equality in another.

| Identity domain | Meaning and current/future authority | Required separation |
| --- | --- | --- |
| Account or authenticated controller | Trusted subject allowed to submit intent; the current implementation uses `RequestPrincipal.player_id` and a development-only principal | MUST NOT be the player-character ID; shared control or account equality MUST NOT merge characters |
| Repository “player” identity | Current Session ownership and `PlayerState.player_id` binding; no separate production account model exists today | MUST be treated as a retained narrower identity, not proof of persistent character identity |
| Stable player-character | One canonical persistent character, identified here as `player_character_id` | MUST be distinct from every other domain in this table |
| Character definition or template | Versioned content definition currently named `character_definition_id` | Reuse of a definition, display name, or description MUST NOT merge player characters |
| Run | One upper-level play continuity governed by Run authority | MUST bind, but MUST NOT equal, a player-character identity |
| Continuous story line | Narrative continuity bound to one active player character at a time | MUST NOT be inferred from a Session, browser tab, or prose resemblance |
| World | Persistent authored-world identity, distinct from a visit, region, or scenario content identity | MUST NOT equal a character or Run identity |
| Scenario and scenario visit | Versioned scenario content and any future visit/run-local occurrence | MUST remain under scenario and Run authorities; current `scenario_id` is not a character ID |
| Stable logical NPC | Long-term NPC subject distinct from runtime NPC and content definition identities | MUST NOT collide with or be substituted for a player-character identity |
| Runtime NPC | Session/scenario-local NPC instance currently represented by `npc_id` | MUST NOT be treated as stable player-character or stable logical-NPC identity |
| Provider/model | Supplier, selected model channel, Provider job, or Provider request metadata | MUST NOT own or establish character identity |
| Browser/tab/session/transport | Browser storage record, Session, connection, device, cookie, or transport occurrence | Loss, reset, or duplication MUST NOT create, replace, retire, reactivate, or delete a character |
| Client request/turn/job | Idempotency key, turn, narrative job, lease, or Provider request | MUST bind operations without becoming character identity |

Repeated names, descriptions, templates, memories, controllers, or prose
similarity MUST NOT establish identity continuity. Identity continuity MUST be
an explicit trusted fact bound to `player_character_id`.

One account or controller MAY be associated with multiple distinct canonical
player characters. This contract does not select an account-level upper bound
or decide how many distinct character records that controller may keep active.
Independently, one canonical player character may belong to at most one active
continuous story line.

## 7. Canonical player-character record

The canonical record is a logical contract, not a database row or wire DTO.
The minimum field groups are:

| Logical field or group | Presence | Conceptual type/domain | Meaning and absence behavior |
| --- | --- | --- | --- |
| `contract_version` | Required | Supported structured-contract version identifier | Selects the rules used to validate the whole record; absence is invalid |
| `player_character_id` | Required | Non-empty, opaque, domain-qualified stable identifier | Immutable, permanently non-reusable identity of this character; absence or malformed form is invalid |
| `record_revision` | Required | Server-issued ordered revision token supporting equality and successor checks | Identifies one committed canonical revision; absence is invalid |
| `controller_binding` | Required | Trusted reference to an authenticated controller domain | Established at canonical creation and preserved in every current lifecycle state; absence is invalid |
| `lifecycle` | Required | Closed value: `active`, `retired`, or `deceased` | Current canonical lifecycle state; absence or unknown value is invalid |
| `character_core` | Required group; individual supported declarations may be absent until a separately approved profile rule requires them | Bounded player-authored declaration slots | Persistent self-description and identity presentation; absence means unset, not inferred |
| `narration_preferences` | Required group; individual preference may be absent | Bounded player-selected presentation controls | Affects presentation only; absence does not authorize a Provider or server to choose subjective facts |
| `character_development` | Optional entries | Bounded, typed, trusted-event-derived facts with provenance | Long-term consequences accepted by server rules; absence means no accepted entry of that type |
| `continuity_metadata` | Required group; current-line reference or references conditional on lifecycle and transition context | Trusted references and explicit adjudication records | Binds current or ended continuity without deriving identity from prose; one line has one active binding once bound and one character has at most one active line |
| `authority_provenance` | Required for each canonical mutation | Trusted mutation kind, actor/authority class, and source reference | Supports validation and audit; public absence is expected because it is not generally projected |

The first contract version is referred to in this document as
`structured-player-character/v1`. That name is a contract identifier, not a
choice of JSON shape, endpoint, programming language, or storage layout.

### Supported `character_core` declarations

The canonical group MUST be capable of representing the approved formal
character scope:

- name or code name;
- preferred form of address;
- adult identity and gender expression, including ambiguous or custom
  expression;
- broad adult age presentation;
- broad appearance direction and a small bounded set of distinguishing
  features;
- outward presentation and inward tendency;
- reality anchor; and
- custom values, including an explicit intentionally-undecided declaration.

This contract does not make every supported declaration mandatory at base-record
creation. A later approved profile or activation workflow MAY define
conditional requiredness, bounded vocabularies, and lengths. Until then,
absence MUST remain distinguishable from an explicit value and from
intentionally undecided. Every supported age presentation MUST represent an
adult.

No biography, origin, class, stat, ability, skill, inventory, body, or
appearance detail beyond the approved scope becomes mandatory through this
contract.

### Supported `narration_preferences`

The internal-thought narration preference, when present, MUST use one of:

| Value | Presentation effect |
| --- | --- |
| `high-immersion` | Permits more immediate sensations, involuntary reactions, and bounded associations grounded in confirmed context |
| `balanced` | Permits a measured mix of external action, sensation, and tentative internal response |
| `high-agency` | Minimizes inferred interiority and leaves intentional judgment primarily to the player |

`balanced` remains the approved recommendation, not a silent canonical player
selection. Exact defaulting and preference-change workflow remain deferred.

## 8. Field authority, mutability, and visibility rules

| Field/group | Canonical authority/source | Mutability | Projection class |
| --- | --- | --- | --- |
| `contract_version` | Trusted contract loader and migration policy | Only through an approved, atomic compatibility transition | Controller-safe when needed; Provider receives only a bounded compiler version if required |
| `player_character_id` | Trusted server identity issuer | Immutable and permanently non-reusable | Controller-safe opaque reference; MUST NOT expose internal generation data |
| `record_revision` | Trusted canonical mutation boundary | Advances only after a successful canonical mutation | MAY be controller-safe as a concurrency token under a future public contract |
| `controller_binding` | Authentication/ownership authority | Preserved; no current mutation path exists. Only a separately approved ownership contract may define transfer, shared control, recovery, or unbinding | Internal only except for a safe self/ownership indication |
| `lifecycle` | Trusted lifecycle policy | Only through the transition matrix | Controller-safe; Provider may receive only necessary confirmed state |
| `character_core` | Player-authored or player-confirmed trusted workflow | Only explicit permitted field updates | Controller-safe subject to privacy rules; bounded Provider context may include only necessary approved fields |
| `narration_preferences` | Player-selected trusted workflow | Explicit preference update only | Controller-safe; bounded Provider context MAY include the effective presentation preference |
| `character_development` | Trusted server rules from authoritative events; subjective entries additionally require player expression/confirmation | Only typed authoritative mutation; no prose patching | Explicit allowlist only; private or internal entries remain excluded |
| `continuity_metadata` | Trusted lifecycle/continuity adjudication | Only atomically with the corresponding authoritative transition | Safe status MAY be projected; adjudication internals and non-public consequences MUST NOT be exposed |
| `authority_provenance` | Trusted server mutation boundary | Append/replace only as part of the new revision's audit facts | Internal; never Provider-authored and not public by default |

Validation and compatibility apply per field group:

| Field/group | Validation requirements | Compatibility behavior |
| --- | --- | --- |
| `contract_version` | Present, exact, supported, and consistent with the complete record | Unsupported versions fail; version change requires an explicit compatibility transition |
| `player_character_id` | Present, well formed for its domain, never previously assigned to a different canonical player character at creation, exact-match on update, and permanently non-reusable | Preserved byte-for-byte or by equivalent canonical value; never synthesized, merged, remapped, released, or made reusable |
| `record_revision` | Present, current, server-issued, and exact-match for mutation | Preserved on read; advances only through one successful canonical commit |
| `controller_binding` | Present and issued or resolved by trusted authentication/ownership authority; submitted copies have no authority; absence or unauthorized alteration is a validation or authority failure | Preserved in `active`, `retired`, and `deceased` records and through every identity-preserving continuity transition unless a separately approved ownership contract explicitly changes the rule; older readers MUST NOT drop it |
| `lifecycle` | Present closed value and reachable only through an allowed transition | Unknown values fail; migration MUST preserve lifecycle meaning and history |
| `character_core` | Complete group validates all provided bounded declarations, adult-presentation rule, provenance, and absence/undecided distinction | Missing optional declarations remain missing; migration MUST NOT invent defaults or reinterpret player meaning |
| `narration_preferences` | Provided values use the closed approved preference set and come from a trusted player workflow | Absence and explicit selection remain distinct; unknown values fail rather than silently default |
| `character_development` | Each entry is bounded, typed, provenance-bearing, and issued by an authorized server rule; subjective entries also prove player expression/confirmation | Unknown entry types fail or remain read-only under an explicitly compatible additive version; no silent loss or prose conversion |
| `continuity_metadata` | References exact logical identities and authoritative transition/adjudication evidence; no inference from narration | Identity and consequence meaning MUST be preserved; unsupported adjudication types fail |
| `authority_provenance` | Matches the exact mutation, actor/authority class, target identity, prior revision, and resulting revision | Retained for required audit/validation; MUST NOT be replaced with Provider or client assertions |

Until a separately approved ownership, transfer, shared-control, recovery, or
unbinding contract explicitly changes this rule, `controller_binding` MUST
remain present and preserved on every canonical record in every existing
lifecycle state: `active`, `retired`, and `deceased`. It MUST remain preserved
through ordinary retirement, ordinary reactivation, authoritative death, and
every authorized continuity transition that preserves the same canonical
player-character identity. A lifecycle or continuity transition alone MUST NOT
clear, replace, infer, or transfer the binding.

Provider output, narration, client projection, Session loss, Run reset, browser
reset, transport failure, inactivity, retirement, or death MUST NOT remove or
replace `controller_binding`. Until a separately approved ownership contract
defines an explicit mutation, no transfer, shared-control, recovery, or
unbinding path exists under this contract. This rule does not decide how many
controllers may exist or whether any future ownership mutation will be
supported.

Player-authored input is a proposal until trusted validation and commit
succeed. Provider-generated candidates, client objects, memory summaries, and
uncommitted narration MUST NOT be copied into canonical fields merely because
they are well formed.

## 9. Contract version and record revision semantics

The following concepts are distinct:

| Concept | Purpose | MUST NOT be confused with |
| --- | --- | --- |
| Contract version | Selects the canonical record's structural and semantic validation rules | Character identity, record revision, Run version, snapshot schema, memory model, content version |
| Record revision | Orders committed mutations of one `player_character_id` and provides stale-write protection | Contract version, Session `state_version`, Run state version, event sequence |
| Applicable character version reference | The pair of stable character identity plus the contract/revision information a Run or consumer is authorized to use | A new identity or permission to transfer between Runs/worlds |
| Existing narrower versions | Snapshot schema, content/scenario version, memory model, prompt/proposal schema, Run Protocol version, and Session state version | Any player-character version above |

For every proposed canonical mutation:

1. The complete record MUST declare a supported `contract_version`.
2. The caller or trusted workflow MUST bind the exact
   `player_character_id` and expected `record_revision`.
3. Validation and authorization MUST occur against one current canonical
   revision.
4. A successful mutation MUST commit the complete resulting record and advance
   its revision exactly once.
5. A rejected, stale, unsupported, malformed, or rolled-back mutation MUST
   leave the revision and canonical record unchanged.

A Run state version MUST NOT be used as player-character identity, contract
version, or record revision. A Run binding MUST record the stable character
identity and the applicable character version reference required by Run
authority.

## 10. Creation and initial validation

Canonical creation MUST:

1. authenticate and authorize the controller;
2. allocate a never-before-assigned `player_character_id` in the
   player-character identity domain;
3. reject any attempted caller-supplied reuse or collision, including reuse of
   an identifier whose former record is retired, deceased, archived, absent, or
   otherwise unavailable;
4. validate the complete record under one supported contract version;
5. validate every provided player declaration without inferring absent values;
6. establish the initial lifecycle and continuity facts through trusted
   policy;
7. bind the controller without treating controller identity as character
   identity; and
8. commit the record atomically with its initial revision.

This contract defines `active` as the normal initial lifecycle for a newly
accepted playable canonical character. It does not decide how many draft
profiles a controller may hold, how many characters may be active
concurrently, or whether a future creation UI has a pre-canonical draft state.

Creation MUST NOT inherit an identity, lifecycle, memory, relationship,
consequence, Run binding, or world binding from another character merely
because the controller, display name, description, template, or input text
matches.

## 11. Update and mutation rules

An update MUST identify:

- the target `player_character_id`;
- the expected `record_revision`;
- the supported contract version;
- the authenticated actor and its authority class;
- the requested typed mutation; and
- any confirmation or authoritative evidence required by that mutation.

The server MUST re-resolve controller authority, current revision, lifecycle,
and relevant Run/world bindings before accepting the mutation. It MUST
validate the complete candidate record, not only the supplied patch.

Character-core and narration-preference changes require an explicit permitted
player/profile workflow. Character-development changes require a trusted
server rule and authoritative provenance. A player declaration cannot create
an external consequence merely by asserting it, and an external consequence
cannot settle a subjective inner state without player expression or
confirmation.

Free text MUST NOT be interpreted as a generic canonical patch. Duplicate or
replayed requests remain governed by the existing narrower idempotency and
request-lifecycle authorities and MUST NOT apply a mutation twice.

## 12. Lifecycle state model

| State | Meaning | Continuous-story-line rule |
| --- | --- | --- |
| `active` | Living canonical player character eligible for an explicitly authorized active continuity binding | Every line using the character MUST bind it explicitly; one line has exactly one active binding once bound and the character belongs to at most one active line |
| `retired` | Living canonical player character whose current continuous story line ended through explicit retirement | MUST have no silently active current line; consequences remain attached |
| `deceased` | Canonical player character whose final death was authoritatively established | Current continuous story line is ended; ordinary reactivation is forbidden |

Lifecycle is canonical state. Absence, inactivity, browser loss, Session loss,
withdrawal, exhaustion, ambiguous dialogue, reduced participation, or model
wording MUST NOT change it.

Every `active`, `retired`, and `deceased` canonical record MUST retain its
`controller_binding`. No lifecycle transition in this contract clears,
replaces, infers, or transfers that binding.

## 13. Authoritative lifecycle transition matrix

Only the following lifecycle-changing paths are admitted by this contract:

| Source | Requested transition | Required actor/authority | Player confirmation | Preconditions | Result | Stable-identity effect | Continuous-story-line effect | Consequences retained | Prohibited alternatives |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `active` | `RETIRE` | Authenticated controller request plus trusted lifecycle policy | Required: explicit choice or explicit confirmation | Character is living; exact revision and identity match; no conflicting transition | `retired` | Same `player_character_id` | Current line ends atomically | All established memories, relationships, promises, injuries, world facts, and consequences remain attached | No inference from absence, behavior, dialogue, exhaustion, or Provider prose |
| `retired` | `REACTIVATE` | Authenticated controller request plus trusted lifecycle policy | Required: explicit player confirmation | Exact retired identity and revision; separately authorized active-line and Run/world bindings | `active` | Same `player_character_id` | An explicit current-line binding is established atomically; whether it is a new line or an authorized continuation remains delegated | All established consequences remain attached | No silent reactivation; no identity replacement; no ordinary path from `deceased` |
| `active` | `FINAL_DEATH` | Trusted server outcome/lifecycle authority | Not required by this contract; a narrower approved rule MAY impose interaction requirements | Final death is established by authoritative event or validated transition; exact identity/revision/bindings match | `deceased` | Same `player_character_id`, now deceased | Current line ends atomically | Death and all prior consequences remain attached | Must not produce `retired`; uncommitted narration cannot establish death |
| `retired` | `FINAL_DEATH` | Trusted server outcome/lifecycle authority | Not required by this contract | Character is still living; final death is authoritatively established; exact identity/revision match | `deceased` | Same `player_character_id`, now deceased | No current line is reopened; prior ended line remains ended | Retirement history, death, and all prior consequences remain attached | Must not silently reactivate before death or reinterpret death as retirement |
| `deceased` | `AUTHORIZED_CONTINUITY_RETURN` | Explicit trusted continuity adjudication plus lifecycle authority | Determined by a future approved continuity rule; this contract does not select it | Authorized resurrection, rebirth, reincarnation, time reversal, or equivalent event; adjudication explicitly says this same identity continues; exact revision/bindings match | `active` | Same ID only when explicitly adjudicated; otherwise this row does not apply | An explicit current-line binding is established atomically; erased/reversed-consequence semantics remain unselected | All consequences remain unless the same approved adjudication explicitly and lawfully changes specified consequences | No ordinary `REACTIVATE`; no inference from prose, resemblance, controller, or memory; no implicit consequence erasure |

Every other lifecycle state change is prohibited unless this contract and its
product authority are explicitly amended and approved. A transition that
adjudicates a new identity is canonical creation of a distinct character, not
a mutation of the deceased record into that new identity.

## 14. Retirement and reactivation

Retirement applies only to a living `active` player character. It MUST be an
explicit, player-chosen or player-confirmed authoritative transition.
Temporary absence, reduced participation, withdrawal from an organization,
exhaustion, travel, silence, ambiguous dialogue, or narrative behavior MUST
NOT be treated as retirement.

Reactivation applies only to the same `retired` identity. It MUST require
explicit player confirmation and a trusted transition. The server MUST
validate any required current-line, Run, and world bindings before atomically
returning the record to `active`.

Retirement and reactivation MUST NOT erase, transfer, clone, or silently
rewrite established consequences.

## 15. Death and authorised continuity

Final death MUST result in `deceased`, never `retired`. It MUST end an active
character's current continuous story line and remain attached to the same
stable identity.

A `deceased` character MUST NOT use `REACTIVATE`. Return from death requires a
separately authorized continuity event and explicit continuity adjudication.
The adjudication MUST state whether the existing `player_character_id`
continues. If it does not, the deceased record remains deceased and any new
character receives a new identity.

This contract intentionally does not decide:

- which resurrection, rebirth, reincarnation, time-reversal, or equivalent
  forms are available;
- which forms preserve identity;
- whether a returned character resumes an earlier line or starts a new one;
  or
- whether an authorized time reversal changes any prior consequence.

No consequence may be removed merely to make a return coherent. Any permitted
change MUST be explicitly authorized, identity-bound, provenance-bearing, and
atomic with the continuity transition.

## 16. New-character identity separation

Every newly created player character MUST receive a never-before-assigned
`player_character_id`. A new character MUST NOT inherit or reuse the identifier
of an active, retired, deceased, deleted-if-ever-supported, archived,
restored, absent, or otherwise known canonical player character. Retirement,
death, deletion if ever supported, archival, restoration, account changes,
display-name reuse, or record absence MUST NOT release an identifier or make it
eligible for reuse.

Restoration or continuity of the same canonical player character preserves the
same identifier and is not identifier reuse. A distinct successor or any other
new player character requires a new identifier.

Shared account/controller, name, code name, address, appearance, template,
description, memory resemblance, Provider output, or narrative role MUST NOT
merge identities. Memory, relationship, promise, item, injury, world,
golden-memory, or consequence transfer to a new identity requires a separately
approved explicit relationship and MUST NOT be inferred.

This contract selects no inheritance, successor, counterpart, cloning, merging,
deletion, archival, restoration, retention, or recovery mechanics. Those
unselected mechanics remain subordinate to permanent `player_character_id`
non-reuse.

## 17. Player-sovereignty boundary

The player remains the authority over the character's subjective inner state.
The following MUST NOT become canonical without explicit player expression or
confirmation:

- private thoughts;
- feelings and emotional commitments;
- motives and intentions;
- beliefs and values;
- love, hatred, trust, forgiveness, fear, guilt, or regret;
- moral conclusions;
- consent; and
- voluntary promises or commitments.

Player-authored declarations MUST be stored separately from externally
observable or server-adjudicated facts. A player declaration MAY establish the
character's own stated belief, feeling, intention, or commitment after
validation; it MUST NOT by itself establish another actor's response or an
external outcome.

The server MAY authoritatively establish permitted external facts, including
world state, NPC actions and attitudes, damage, injuries, survival, death,
resource effects, and other valid consequences. An NPC's attitude toward the
player character MUST NOT be treated as proof of reciprocal feeling.

## 18. Provider and uncommitted-narration boundary

Provider output is candidate material only. Structural validation does not
make it canonical.

A Provider MUST NOT create, delete, merge, clone, rename, transfer, retire,
reactivate, kill, resurrect, replace, or otherwise mutate a canonical
player-character record by narration or proposed structure alone. It MUST NOT
choose the target identity from display-name or prose similarity.

Provider failure, timeout, invalid output, unavailable output, stale output,
or uncertain delivery MUST leave the last committed record and revision
unchanged. Uncommitted narration MUST NOT establish permanent lifecycle,
memory, relationship, identity, or continuity facts.

Any bounded Provider candidate considered by a trusted policy MUST still be
rebound to the exact character, controller/session as relevant, expected
revision, Run/world/scenario context, request, and authoritative state before a
server decision. This contract preserves `MODEL-001`: valid model output is
still not a world fact, and model prose never rewrites fixed facts.

## 19. Client, server, and public-projection boundary

The client submits intent, typed permitted input, or player-authored
declarations. It does not submit canonical authority. The server decides
whether a mutation or lifecycle transition is valid and commits the complete
result atomically.

Public affordances and projections are descriptions, not capabilities. A
client MUST refresh and obey the latest authoritative projection, but a
displayed affordance does not guarantee that a later stale or conflicting
submission succeeds.

A future player-character public projection MUST:

- be built field by field from an explicit allowlist;
- identify the intended audience and controller authorization;
- return detached, immutable data;
- exclude controller credentials, internal provenance, private memory,
  hidden facts, capabilities, policy traces, Provider payloads, and
  adjudication internals;
- avoid deriving identity or lifecycle from display prose; and
- remain subordinate to server validation.

Replayed, duplicated, stale, identity-mismatched, or controller-mismatched
requests MUST fail safely under this contract and the existing narrower
request/idempotency authorities. This contract does not redesign the current
public client or request lifecycle.

## 20. Run and world relationship

Player-character, Run, continuous-story-line, world, scenario, visit, region,
and Session identities remain distinct.

The canonical relationship required by the approved product authority is:

```text
RunId
  -> permanently owns one ContinuousStoryLineId
  -> stores one explicit active player-character binding once bound
       -> exact stable player_character_id
       -> exact ApplicableCharacterReference
  -> uses Run-owned world and scenario bindings
```

The Run authority owns Run creation, frozen protocol, entry-world identity and
version, later-world selection, visit identity, and world-line rules. This
character contract owns only the character identity/revision side of that
binding and the rule that a binding MUST be explicit and validated. The
[Minimum Run Core Implementation Plan](minimum_run_core_implementation_plan.md)
froze the prerequisite persistence and transaction seam. That core is now
implemented at `e821cd922b61868097667b12c2b64cf8089a9681`; that null-only seam
was activated internally by P4-S1a
(`748003319ececa548b68b351746afbb2d54c66bb`) and P4-S1b
(`8eabf9d4c3c592ea1de50f443f1816de9a46dc8f`).

Active binding cardinality is no longer unresolved:

- once a continuous story line is bound, it has exactly one active canonical
  player-character binding while active;
- one canonical player character belongs to at most one active continuous
  story line;
- a second or conflicting active binding fails atomically without changing
  either canonical subject;
- a completed, terminated, or otherwise non-active historical line may retain
  its immutable exact character/reference history without counting as a
  second active binding; and
- ending a bound Run/line MUST make the binding historical in the same
  Run-owned canonical transaction.

No cloning, transfer, replacement, automatic rebinding, or ownership inference
is authorized by these rules. A Run or line identity, Session, controller,
account, character definition, world, scenario, visit, browser record, or
piece of prose cannot substitute for the bound `player_character_id`.

Within the same continuous story line, every scenario change MUST preserve the
same bound `player_character_id`. Run-authorized progression into a later world
within that continuous story line MUST also preserve the same bound
`player_character_id`. Run authority continues to govern world and scenario
selection, Run lifecycle, visit identity, transition eligibility, and
applicable world state; none of those identities becomes the player-character
identity.

Within those same boundaries, every scenario change and Run-authorized
progression into a later world MUST also preserve the bound applicable
character version reference unless and until a separately approved
authoritative policy governing revision following, checkpointing, or equivalent
behavior explicitly authorizes a reference change. A scenario boundary, genre
change, world change, visit change, or Run-authorized later-world selection is
not by itself authority to select a different applicable character version
reference, advance or roll back that reference, reinterpret the character
through a different revision, substitute another revision while retaining the
same `player_character_id`, or infer consent to a reference change. Such a
boundary MUST NOT silently or independently switch that reference or imply an
automatic boundary-driven version change. Any future reference change MUST
follow that separately approved explicit policy; this contract does not state
that the reference can never change and does not select pinned, floating,
checkpointed, or any other revision-following behavior.

A scenario boundary, genre change, or Run-authorized later-world selection MUST
NOT by itself create a replacement player character, issue a new
player-character identity, merge or transfer identities, retire or reactivate
the character, mark the character deceased, or erase attached relationships,
memories, or consequences. Such authorized same-line progression is identity
continuity, not identity transfer.

A Run MUST NOT silently replace, merge, reinterpret, or switch its bound player
character. A character MUST NOT be arbitrarily transferred between unrelated
Runs, separate continuous story lines, or accounts. Run reset, browser reset,
Session loss, transport failure, or Provider failure MUST NOT create, delete,
retire, reactivate, or replace a player character.

The implemented P4-S1 binding is a Run-owned mutation. The Run application service
MUST resolve trusted controller authority, obtain the canonical owned
character and exact applicable reference through the narrow Phase 3-owned
internal read seam defined by the minimum Run-core plan, and commit the
complete Run binding revision and receipt inside the already-owned Run
UnitOfWork. That seam MUST preserve existing Phase 3 authorization,
non-enumeration, validation, and public `get_owned` behavior without opening a
nested UnitOfWork. The binding operation MUST NOT trust submitted ownership,
update the player-character aggregate, coordinate independent service commits,
copy that aggregate into Session state, or treat a detached owned/public
projection as writable persistence state.

Session participation is a separate Run-owned persistence record. It MUST NOT
add Run, line, or character-binding columns to `game_sessions`; MUST be created
only by trusted Run orchestration; MUST NOT grant character ownership or
controller authority; and MUST reject conflicting participation. Multiple
distinct trusted Sessions MAY participate in the same Run without activating
public resume, reconnect, cross-tab, browser-restart, or multi-device behavior.

The following remain unresolved and MUST NOT be inferred by implementation:

- exact same-line movement, transition, and compatibility mechanics, without
  making the binding's identity continuity optional;
- arbitrary movement between unrelated Runs, transfer between separate
  continuous story lines, cross-account transfer, and ownership transfer;
- whether a Run binding follows later character revisions, checkpoints a
  specific revision, or otherwise follows revisions, including when a future
  approved policy may change the applicable character version reference; this
  deferral is not current authority for a scenario or later-world boundary to
  change that reference;
- restart/resume, Session reassignment, successor/replacement, and
  post-retirement/death/return behavior; and
- exact cross-Run behavior beyond the frozen active-binding exclusivity,
  revisit and world-line compatibility, plus policy for any world movement not
  already authorized by Run authority and the frozen product specification.

## 21. NPC, relationship, memory, and golden-memory references

Any future authoritative memory, relationship, or consequence attached to a
player character MUST carry or be unambiguously bound through trusted state to
the correct `player_character_id`. When an NPC is involved, it MUST also bind
the correct stable logical NPC identity and MUST NOT substitute a runtime NPC
ID, content definition, name, role, or template for that logical identity.

Identity-bearing provenance SHOULD include the relevant trusted Run, world,
scenario/visit, and event references when those domains are material. These
references describe provenance; they do not merge their subjects.

Protected golden memory remains distinct from:

- the current implemented `PlayerMemoryState` bounded index;
- ordinary bounded summaries;
- replaceable prompt or recent-context material;
- Provider candidates and continuity notes; and
- uncommitted narration.

This contract does not modify the existing memory architecture. Current memory
rules, stable local NPC subject keys, scenario participation evidence,
capacity behavior, event receipts, atomicity, and projections retain their
narrow authority until an approved integration explicitly adds stable
player-character and cross-scenario logical-NPC references.

Death, survival, retirement, reactivation, promises, relationships, protected
golden memory, and world consequences MUST remain attached to their correct
logical subjects. They MUST NOT transfer because two characters share a
controller, name, description, template, or Provider-generated resemblance.
Retirement, death, reactivation, or authorized continuity MUST NOT silently
erase them.

## 22. Validation, rejection, and recovery behavior

Validation MUST operate on a detached complete candidate and commit all
accepted effects atomically. Rejection MUST leave the canonical record,
revision, lifecycle, bindings, memory references, relationships, and
consequences unchanged.

| Failure | Required behavior |
| --- | --- |
| Missing required identity | Reject before mutation; do not infer from controller, Session, Run, name, or prose |
| Malformed identity | Reject with a stable safe classification; do not normalize into another identity |
| Duplicate identity attempt | Reject creation or return the already committed idempotent winner only when the existing request contract proves it is the same operation |
| Unsupported contract version | Fail explicitly; do not apply current defaults or reinterpret under another version |
| Stale record revision | Reject and require a fresh canonical read; do not merge or partially apply |
| Invalid lifecycle transition | Reject; preserve state and revision |
| Missing required player confirmation | Reject; ambiguous text or prior behavior is not confirmation |
| Authority mismatch | Reject before reading or applying authority-bearing fields |
| Controller mismatch | Return only the safe response permitted by the retained ownership authority; do not expose existence or private data |
| Missing or altered `controller_binding` | Reject as a validation or authority failure; no lifecycle state, continuity transition, Provider output, client projection, Session loss, Run reset, or transport failure may supply, remove, or replace it |
| Provider-only proposed mutation | Reject as non-authoritative candidate material |
| Ambiguous narration | Treat as narration only; establish no lifecycle, identity, memory, or relationship fact |
| Partial or malformed structured input | Reject the complete proposed mutation; do not salvage a subset |
| Unknown submitted field | Reject at a canonical write boundary; do not treat it as prose or silently persist it |
| Cross-character identity mismatch | Reject; do not copy, merge, redirect, or retarget the mutation |
| Run/world/scenario mismatch | Reject or require the owning authority to refresh/rebind explicitly; do not transfer the character |
| Applicable character version reference change lacking separately approved policy authority | Reject before use or mutation and preserve the current binding and canonical record; a scenario, genre, world, visit, or Run-authorized later-world boundary supplies no reference-change authority and cannot infer consent |
| Provider failure or uncertain result | Preserve the last committed record and revision; follow the retained Provider recovery boundary |
| Persistence or commit failure | Roll back the entire proposed mutation and expose no success projection |

After failure, recovery begins from a fresh read of the last committed
canonical record and relevant retained authoritative state. A failed proposed
transition MUST NOT leave a reservation, partial lifecycle state, partial
confirmation, synthetic narration fact, or advanced revision unless a future
approved protocol explicitly defines a separate non-canonical operation
record.

## 23. Compatibility and evolution rules

| Situation | Required compatibility behavior |
| --- | --- |
| Supported exact contract version | Validate the complete record under that version |
| Older supported version | Read or migrate only through an explicit pure, deterministic, reviewed compatibility rule; preserve identity and authoritative meaning |
| Newer unsupported version | Fail explicitly; do not downgrade, guess, or write |
| Unknown external mutation field | Reject the mutation |
| Unknown canonical field under a declared compatible additive version | An older reader MAY read only if it can preserve the field losslessly and remains read-only; otherwise it MUST fail |
| Older writer facing unknown canonical fields | MUST NOT rewrite or drop them; fail or use an approved migration |
| Removed or changed meaning | Requires a new contract version and explicit compatibility/adjudication rule |
| Migration or validation failure | Leaves the original canonical record unchanged |

Compatibility logic MUST preserve `player_character_id` and its permanent
non-reuse, `controller_binding`, player-authored meaning, lifecycle history,
controller separation, consequence provenance, and player sovereignty. It MUST
NOT manufacture missing declarations, reinterpret absence as consent, merge
identities, or convert Provider prose into facts.

Unknown fields MUST never be silently dropped on a read-modify-write path.
Contract evolution MUST remain distinct from Run version, Session
`state_version`, snapshot schema, content version, memory model version, and
Provider prompt/proposal versions.

## 24. Security and privacy boundary

Canonical and projected data MUST follow least disclosure. Public or
Provider-facing projections MUST NOT expose:

- secrets, credentials, authentication tokens, cookies, or internal account
  identifiers not required by the audience;
- private player declarations not explicitly intended for that projection;
- private memory, hidden world facts, NPC secrets, or non-public adjudication
  data;
- capabilities, seals, receipts, policy traces, internal rule IDs, raw
  Provider payloads, database details, or stack traces; or
- identity-generation internals that make identifiers predictable or
  forgeable.

Controller authorization MUST be checked from trusted authentication context,
not from a submitted `controller_binding`. Character identifiers SHOULD be
opaque in public surfaces and MUST be validated as data, never executed or
used as unbounded path material.

## 25. Downstream implementation obligations

### P5-S1 implementation-candidate status

The P5-S1 scope represented by the exact candidate or commit identified by
applicable exact-candidate review evidence and Git history activates only the
controller-owned detached read at
`GET /v1/player-characters/{player_character_id}`. It does not
alter this contract's identity, lifecycle, canonical validation, privacy,
Run-binding, or mutation rules. Acceptance must be established by the
applicable exact-candidate review record, and repository integration and
publication state must be established from Git history. It must not be
represented as a completed Phase 5 or production-authentication milestone.

### P5-S2 implementation status

The frozen P5-S2 public creation/replay contract was independently approved,
committed, and published at
`4ba66d8f277988325795c905fdf6fd9e416d7457`
(`feat(player-character): add creation API`). It adds only the normal
application's authenticated
`POST /v1/player-characters` boundary, preserving the existing P5-S1 owned
read and delegating controller ownership, operation identity, durable replay,
creation persistence, and race recovery to the existing application and
persistence authorities. This status does not amend this product contract or
promote any deferred lifecycle, mutation, Run, or gameplay behavior.

P5-S2 is not deployed or a production-authentication milestone. Demo and
frontend creation remain inactive: Demo has no Player Character service and no
Player Character route or OpenAPI path.

### P5-S3 implementation status

The dedicated
[P5-S3 retirement activation plan](structured_player_character_p5_s3_implementation_plan.md)
and its narrow amendment to the
[Public Client Contract](public_client_contract.md) received
`STRUCTURED_PLAYER_CHARACTER_P5_S3_PLAN_APPROVED`. The first, first-corrected,
and re-corrected local implementation candidates each received
`CHANGES_REQUIRED`; the third review found no production-code defect and
requested corrected evidence only. The later evidence candidate was followed
by a focused receipt-add reachability investigation whose verdict was
`P5_S3_RECEIPT_ADD_RACE_NOT_REACHABLE_UNDER_CURRENT_PRODUCTION_PATH`. The
accepted implementation selects only explicit
controller-requested retirement of an
owned, active, unbound canonical character. Its final independent review passed
and it was committed and published as
`34d063e387cde69500e4dc018ff087e87f3eee74`. It is not deployed, released, or
production-authentication activated. It does not change
the frozen lifecycle matrix: identity and controller binding remain preserved,
revision advances once only on committed success, and an active Run binding
continues to require the existing atomic lifecycle-transition rejection until
later Run-owned line ending and binding historicalization exist.

Current mandatory concurrency evidence uses normal HTTP requests, distinct
real MySQL connections/UoWs, and the existing aggregate `FOR UPDATE` boundary.
It must prove one durable mutation/receipt/revision advance followed by exact
replay for an identical fingerprint or ordinary idempotency conflict for a
different fingerprint, with no duplicate policy mutation, recovery, or 1062.
The existing receipt-add recovery branch remains bounded defensive behavior and
is covered through explicitly labelled narrow service fault injection; direct
repository uniqueness evidence is synthetic out-of-topology translation. A
real receipt-add 1062 becomes mandatory only if a future composed runtime writer
or changed transaction topology can legitimately reach that unique boundary
without first serializing on the aggregate lock. No such topology is approved
or required by this contract.

### Phase 8 Run-entry and minimum playable-loop status

Phase 5 ended with published P5-S3. No P5-S4 exists. The separately allocated
Phase 8 approved and published planning authority is the
[Structured Player Character Run Entry and Minimum Playable Loop plan](structured_player_character_run_playable_loop_plan.md).
Its original seven-document planning candidate received
`STRUCTURED_PLAYER_CHARACTER_RUN_PLAYABLE_LOOP_PLAN_REVIEW_APPROVED` and was
committed and published at `de4d8c0e35c7864948306d751a00aaf295ff77ff`.
It does not implement behavior. Later modifications to its canonical planning
bytes require fresh exact-byte independent review before a separately authorized
documentation commit; that commit precedes user publication and clean
published-baseline confirmation. P8-G0 is complete and published. P8-S1
eligible-character discovery is implemented, accepted, committed, and
published. P8-S2 atomic internal Run entry is implemented, accepted, committed,
and published at `70815b181624e5475d2d978bef0db1ed3b22324e`; its implementation
and F1/F2/F3 evidence are closed and are not reopened. The
[P8-S3 implementation plan](structured_player_character_p8_s3_implementation_plan.md)
was independently approved and committed/published at
`e17172ad0a9febe4ec9e3a96e7be8204c9722d29`. Its implementation contains normal
public Run entry that reuses the exact
trusted Player Character ownership/eligibility evidence, returns only the
detached four-field character projection, and leaves the active revision-one
character unchanged through the terminal Session journey. Independent
technical evidence did not constitute approval: the implementation candidate's
first independent review returned
`CHANGES_REQUIRED` with five bounded findings, and all five corrections are
complete. The subsequent independent read-only re-review found no remaining
actionable technical defect but formally returned `CHANGES_REQUIRED` solely for
one Medium documentation-synchronization finding. The complete 15-path candidate
then received focused independent read-only approval and was committed and
published at `ac07a5fe267adfb0281ec2658b2fcbd0085f6eb1`. P8-S3 is complete.
The dedicated
[P8-S4 implementation plan](structured_player_character_p8_s4_implementation_plan.md)
was independently approved and committed/published at
`375a2a7ae018c9c9c79272e5de7da703818d1f20`. Its implementation received
`STRUCTURED_PLAYER_CHARACTER_P8_S4_IMPLEMENTATION_CORRECTION_INDEPENDENT_REVIEW_APPROVED`,
was committed as `187d41ba3035c8d717c2fb2578a805402255d979`, and was
manually published by the user. P8-S4 is complete: the fixed Demo controller
can create, read, retire, and discover only its owned Player Characters through
the existing service and public projections, and can use the same ownership,
revision, lifecycle, compatibility, binding, replay, and non-enumeration rules
for Run entry. The dedicated
[P8-S5 implementation plan](structured_player_character_p8_s5_implementation_plan.md)
was independently approved and committed/published at
`dceecaf0d7a33ccde07f519f83997489acd5fc86`, remained frozen during
implementation, and its corrected implementation received
`STRUCTURED_PLAYER_CHARACTER_P8_S5_CORRECTED_IMPLEMENTATION_REVIEW_APPROVED`.
The exact eight-path Web implementation was committed and published at
`2ce56a757beed8a3989d38453da3b6d80342ca05`. P8-S5 is complete: the primary
Web journey consumes the existing detached eligible projection and submits its
exact Player Character identity and revision to existing Run-entry authority.
It adds no character lifecycle, binding, ownership, DTO, or persistence
authority. P8-S6 cross-surface evidence/final status closure has not started.
Phase 8 and the overall project remain incomplete.

The implemented Phase 8 character-side boundary remains narrow and unchanged
by P8-S5:

- a bounded discovery query returns only detached projections of records owned
  by the resolved controller, currently `active`, and without an active Run
  binding;
- one Run-entry-owned transaction locks and validates the exact selected
  character and expected revision through the existing P4-S1 same-UoW seam;
- the Run receives the existing complete active binding envelope with the exact
  `PlayerCharacterId` and `ApplicableCharacterReference`;
- one server-created Session receives separate Run participation and the Run
  changes to `active` without copying the character aggregate into Session
  state; and
- no Phase 8 operation can replace, switch, follow, clear, historicalize, or
  transfer the binding.

The current scenario's static `character_definition_id` remains a separate
server-selected Session-initialization fixture. It is not the Structured Player
Character and cannot establish identity. Scenario settlement does not end the
Run or release the active binding. Run completion/termination, binding
historicalization, later Session/scenario movement, character-to-mechanics or
Provider context, and post-ending reuse remain later authority.

Phase 6 subject-reference compatibility hooks and Phase 7 closeout retain their
existing allocations and remain unimplemented. Neither is a Phase 8
prerequisite because Phase 8 creates no new memory/relationship/consequence
fact and owns only its own bounded evidence/status closure. Phase 8 authorizes
no schema or migration.

Before any runtime implementation is accepted, the owning implementation
specification MUST define and verify:

| Obligation | Required evidence |
| --- | --- |
| Identity issuer and collision handling | Stable domain-qualified IDs, uniqueness, permanent non-reuse across every lifecycle or record-availability condition, and cross-domain mismatch tests |
| Canonical validator | Complete-record validation, unknown-field policy, adult-presentation constraints, and absence semantics |
| Revision/CAS boundary | Stale-write, duplicate, concurrency, rollback, and exactly-one-revision-advance tests |
| Controller authorization | Required binding preservation across every lifecycle state and identity-preserving continuity transition, ownership mismatch, and non-enumeration behavior without conflating controller and character |
| Lifecycle policy classes | Independent policies for retirement, reactivation, final death, and authorized continuity |
| Confirmation protocol | Explicit, identity/revision-bound retirement/reactivation confirmation with replay and ambiguity tests |
| Atomic persistence | Character, lifecycle, bindings, provenance, consequences, and response commit or roll back together |
| Run/world binding integration | Run-owned exact `RunId`/`ContinuousStoryLineId`, stable character ID plus applicable character reference, one-active-line-per-character and one-binding-per-line database/service backstops, atomic conflict tests, stable-ID and no-silent-reference-switch tests across scenario, genre, world, visit, and Run-authorized later-world boundaries, separate trusted Session participation, and no silent transfer or Session-derived replacement |
| Memory/NPC integration | Correct stable player-character and logical-NPC subject binding without weakening current memory authority |
| Provider boundary | Candidate-only behavior, failure preservation, no direct mutation path, and `MODEL-001` coverage |
| Public projection | Explicit allowlists, privacy scans, immutable copies, and no authority-bearing internals |
| Compatibility | Supported/unsupported version, lossless additive read, unknown-field, and migration rollback tests |
| Documentation synchronization | Updated owning authorities, migration review if applicable, acceptance evidence, and accurate `PLANS.md` status |

Every implemented state mutation MUST have regression coverage. Persistence or
model changes MUST follow the repository architecture, MySQL, `AsyncSession`,
Provider, atomicity, and Alembic guardrails applicable at that later time.

## 26. Acceptance criteria

The second fresh independent read-only review confirmed that the following
approval criteria were satisfied:

1. every canonical character has one stable, permanently non-reusable identity
   separate from all listed identity domains;
2. controller or display-name equality cannot merge characters;
3. the minimum record states field presence, type/domain, authority,
   mutability, projection, validation, compatibility, and absence behavior;
4. contract version and record revision are distinct and stale writes fail
   atomically;
5. creation and every lifecycle transition are explicit, validated, fail-safe,
   and preserve the required `controller_binding`;
6. retirement requires explicit player choice or confirmation;
7. reactivation preserves the same retired identity and cannot apply to a
   deceased character;
8. final death produces `deceased` and ends an active current line;
9. return from death requires explicit continuity adjudication without this
   contract deciding its identity outcome;
10. subjective inner states remain player-sovereign;
11. Provider, narration, client, projection, Run, world, NPC, and memory
    boundaries retain their narrower authority;
12. protected golden memory is not collapsed into ordinary context or the
    current memory index;
13. rejected input cannot partially mutate canonical state;
14. deferred material product choices remain explicit;
15. same-story-line scenario changes and Run-authorized later-world progression
    preserve the same bound `player_character_id`;
16. those boundaries do not silently or independently switch the applicable
    character version reference, and any future reference change requires a
    separately approved explicit revision-following, checkpointing, or
    equivalent policy;
17. `controller_binding` remains required in every existing lifecycle state and
    identity-preserving continuity transition unless a separately approved
    ownership contract explicitly changes the rule; and
18. the document makes no runtime, database, migration, API, DTO, Provider,
    public-client, test, or frontend implementation claim.

Approval of this document approves only the specification. It does not
implement it or authorize runtime implementation. Implementation requires a
separately approved downstream implementation plan and task.

## 27. Deferred questions and explicitly unselected designs

The following are deliberately unselected by this product contract. A
narrower downstream authority may already select a bounded representation for
an implemented or planned slice; that does not promote the choice into this
product contract or authorize adjacent work:

- exact wire, DTO, API, persistence, table, column, snapshot, migration, and
  public-projection shapes;
- exact ID syntax/generation, field lengths, localization, vocabularies, and
  quick-start templates;
- activation/profile-completion requiredness for supported `character_core`
  declarations;
- account/controller character limits and how many distinct canonical
  character records one controller may keep active; active line occupancy is
  already frozen separately;
- ownership transfer, shared control, delegation, unbinding, account recovery,
  deletion, archival, retention, restoration, cloning, and merging mechanics,
  all subordinate to permanent `player_character_id` non-reuse;
- exact same-line movement and compatibility mechanics, arbitrary movement
  between unrelated Runs, transfer between separate continuous story lines or
  accounts, cross-Run behavior beyond the frozen active-binding exclusivity,
  and any world movement not already authorized by Run authority and the
  frozen product specification;
- whether Run bindings float with later character revisions, checkpoint a
  specific revision, or otherwise follow revisions, including when a future
  approved policy may change the applicable character version reference; this
  deferral supplies no current boundary-driven reference-change authority;
- restart/resume, Session reassignment, and public reconnect semantics; the
  minimum canonical `ContinuousStoryLineId` carrier and one-Run/one-line
  ownership are frozen by P4-G0;
- availability and identity outcome of resurrection, rebirth, reincarnation,
  time reversal, or equivalent continuity;
- time-reversal effect on authoritative consequences;
- inheritance, successor, counterpart, memory transfer, relationship transfer,
  item transfer, or consequence transfer;
- progression, inventory, combat, class, skill, ability, body, possession, and
  switching systems;
- exact character-development event schemas and prompt-compiler compatibility;
- stable cross-scenario logical-NPC representation and golden-memory schema;
  and
- rollout, migration, deployment, phase numbering, and implementation plan.

Identifier non-reuse is already binding and is not a deferred product choice.
Restoration or continuity of the same canonical character preserves that
character's identifier; a distinct successor or new character receives a new
identifier.

No downstream implementation may silently select one of these designs.

## 28. Authority precedence and conflict handling

Precedence is:

1. The approved final narrative experience specification governs its frozen
   cross-phase product requirements.
2. Existing narrower implemented or approved contracts retain authority over
   their current Run, public-client, persistence, snapshot, memory, NPC,
   Provider, request-lifecycle, recovery, and security domains.
3. This approved contract governs the structured player-character domain only
   where it does not silently redefine those retained domains.

An apparent difference between this contract and current Demo behavior
is planned evolution, not a current defect. Any material conflict MUST block
approval and be resolved through explicit amendments, compatibility/migration
planning, and review of every affected authority.

This contract does not weaken `AUTH-001`, `STATE-001`, `API-001`, `MODEL-001`, or
`MODEL-002`. It adds no authority to players, clients, Providers, narration,
memory summaries, or public projections.

## 29. Review and implementation status

The first independent read-only review of the then-complete draft found one
HIGH issue concerning stable same-story-line identity continuity, one MEDIUM
issue concerning permanent `player_character_id` non-reuse, and one MEDIUM
issue concerning `controller_binding` lifecycle presence. The first controlled
correction addressed those three issues locally.

The first independent re-review confirmed that all three original findings were
closed but found one new MEDIUM omission concerning silent applicable-version
switching at scenario and Run-authorized later-world boundaries. The second
controlled correction addressed that omission locally without selecting
pinned, floating, checkpointed, or other revision-following behavior. Neither
controlled correction was an independent review or an approval.

The second fresh independent read-only review confirmed that all four
historical findings were closed, found no new HIGH, MEDIUM, or LOW issue
requiring correction, and returned
`APPROVED_STRUCTURED_PLAYER_CHARACTER_CONTRACT`.

This separate controlled documentation closeout then recorded the earned
approval and frozen status in this contract and `PLANS.md` and created exactly
one local documentation commit. It was not an independent review, changed no
runtime behavior, made no additional product decision, and did not push. Codex
does not push.

The structured player-character contract is approved and frozen and partially
implemented through completed, independently approved, committed, and pushed
Phase 3 plus the completed Minimum Run Core at
`e821cd922b61868097667b12c2b64cf8089a9681`. P4-S1a
(`748003319ececa548b68b351746afbb2d54c66bb`) and P4-S1b
(`8eabf9d4c3c592ea1de50f443f1816de9a46dc8f`) complete the internal Run-owned
continuous-story-line binding. P5-S1, P5-S2, and P5-S3 are published. The first,
first-corrected, and re-corrected P5-S3 candidates each received
`CHANGES_REQUIRED`; the third review found no production-code defect and
requested corrected evidence only. The later evidence candidate and focused
`P5_S3_RECEIPT_ADD_RACE_NOT_REACHABLE_UNDER_CURRENT_PRODUCTION_PATH` verdict
preceded the accepted correction. Correction validation passed with the
canonical counts above, final independent review passed, and the result was
committed and published as `34d063e387cde69500e4dc018ff087e87f3eee74`.
Phase 5 is complete at P5-S3, no P5-S4 exists, and P5-S3 remains closed. Demo,
public Run, frontend, Web, and administration were not activated by Phase 5.
Phase 8 now has the approved and published planning authority described above.
P8-G0 and P8-S1 are complete and published. P8-S2 atomic internal Run entry is
implemented, accepted, committed, and published at
`70815b181624e5475d2d978bef0db1ed3b22324e`; it remains closed. The P8-S3
normal API/composition implementation linked above contains the completed five
bounded corrections. Its subsequent independent re-review returned
`CHANGES_REQUIRED` solely for the Medium documentation-synchronization finding.
The complete 15-path candidate later received focused independent read-only
approval and was committed and published at
`ac07a5fe267adfb0281ec2658b2fcbd0085f6eb1`. P8-S3 is complete. P8-S4 then
completed under its independently approved and published plan. The
implementation received
`STRUCTURED_PLAYER_CHARACTER_P8_S4_IMPLEMENTATION_CORRECTION_INDEPENDENT_REVIEW_APPROVED`,
was committed as `187d41ba3035c8d717c2fb2578a805402255d979`, and was
manually published by the user. P8-S4 deterministic Demo parity is complete.
The frozen P8-S5 plan was independently approved and published at
`dceecaf0d7a33ccde07f519f83997489acd5fc86`; its corrected implementation was
independently approved, committed, and published at
`2ce56a757beed8a3989d38453da3b6d80342ca05`. P8-S5 is complete. P8-S6
cross-surface evidence/final status closure has not started, and Phase 8 and the
overall project remain incomplete. Phase 6 and Phase 7 remain allocated and
unimplemented. The approved final
narrative experience specification remains approved, frozen, and not
implemented. Phase 3.2b remains closed.
