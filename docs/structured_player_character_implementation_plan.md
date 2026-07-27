# Structured Player-Character Downstream Implementation Plan

## 1. Status

Status: **Approved and frozen downstream implementation plan — Phase 1 has
passed fresh independent read-only acceptance for the exact nine-path
candidate and is committed and pushed at
`c8808f66e8d97bc4386a481bf21669cfddcd222e`; Phases 2–7 remain unimplemented
and blocked pending separate explicit authorization.**

The concrete Phase 2 persistence design in section 20 is a
technical-prerequisite amendment and **review candidate awaiting fresh
independent acceptance**. It is not yet an accepted or frozen amendment and
does not authorize Phase 2 implementation. Phase 2 remains unimplemented and
blocked pending that review and separate explicit user authorization.

The pre-correction draft received one fresh independent read-only review. That
review identified five accepted findings, `SPCIP-001` through `SPCIP-005`; the
controlled correction closed them. The second fresh independent read-only
review of the complete corrected plan and associated `PLANS.md` diff returned
`APPROVED_STRUCTURED_PLAYER_CHARACTER_IMPLEMENTATION_PLAN_CORRECTED_DRAFT`.
This documentation-only closeout records the resulting approval and freeze; it
does not authorize implementation, staging, commit, or push. Implementation
requires a separately authorized task under this frozen plan and its
phase-specific prerequisites and stop conditions. Any substantive change to
this frozen plan requires a new controlled amendment and review process.

The
[structured player-character contract](structured_player_character_contract.md)
and [final narrative experience](final_narrative_experience.md) remain approved
and frozen product specifications. Only the pure Phase 1 domain and
character-operation protocol foundation is implemented, accepted, committed,
and pushed; the complete product specifications remain only partially
implemented. Phase 3.2b remains closed.

## 2. Purpose

This plan translates the approved structured player-character product
contract into the smallest safe, repository-specific implementation sequence.
Its target is a reviewable vertical slice that can create, read, validate, and
perform narrowly authorized lifecycle mutations on one canonical structured
player-character record while preserving permanent identity, controller
binding, revision, applicable-reference, continuity, Provider, public-client,
memory, and NPC authority boundaries.

The target is not a complete character builder, profile product, progression
system, Run implementation, account system, relationship system, golden-memory
system, or production rollout. Each proposed phase below remains a proposal
requiring separate implementation authority.

## 3. Authority and precedence

The authorities for this plan, in descending order where their scopes
overlap, are:

1. [Structured Player-Character Contract](structured_player_character_contract.md),
   the approved and frozen canonical product authority for player-character
   identity, record, revision, lifecycle, validation, projection, and adjacent
   boundaries.
2. [Final Narrative Experience and Long-Term Systems](final_narrative_experience.md),
   the approved and frozen cross-phase product authority.
3. Existing narrower approved or implemented authorities:
   [Run Protocol](run_protocol.md),
   [Architecture](architecture.md),
   [NPC Relationship and Temporary Residence](npc_relationship_residence.md),
   [Player Memory](player_memory.md),
   [Narrative Provider](narrative_provider.md), and
   [Public Client Contract](public_client_contract.md).
4. Repository engineering constraints in
   [Engineering Guardrails](engineering/guardrails.md) and
   [Codex Workflow](engineering/codex_workflow.md).
5. Project placement and status in [`PLANS.md`](../PLANS.md).

The player-character contract controls its own domain. An existing narrower
contract remains authoritative inside its narrower domain and must not be
silently widened. In particular, Run authority continues to own Run lifecycle,
world and scenario selection, visit identity, transition eligibility, and
applicable world state. The current request, Session, Provider, public-client,
and memory contracts remain intact unless a later separately approved
implementation phase identifies and reviews a narrow incompatibility.

This plan uses the following decision classification:

| Code | Classification |
| --- | --- |
| `A` | Required directly by an approved and frozen product authority |
| `N` | Required by an existing narrower approved or implemented invariant |
| `T` | Repository-specific technical implementation choice proposed for review |
| `U` | Unresolved decision requiring later approval or an owning authority |
| `E` | Explicitly excluded from the first implementation slice |

No `T` proposal in this plan changes a product rule. Any proposal found to
have material product consequences becomes `U` and is a stop condition rather
than an implementation default.

## 4. Implementation status boundary

This approved and frozen document remains the substantive design authority.
The separately authorized Phase 1 implementation added only pure domain models,
independent policies, deterministic character-operation serialization and
receipt semantics, and offline unit/golden-vector tests. It changes no
database, migration, schema, repository, Unit of Work, production service,
API, Provider, client, frontend, Demo, Session request/action, Run/story-line,
or production behavior. It does not reopen Phase 3.2b.

File names, table names, data types, endpoint shapes, and phase boundaries below
are proposed implementation inventory. They are not authority to edit those
surfaces. Exact choices identified as `U` must be resolved before the affected
phase begins.

## 5. Current repository baseline

The controlled planning task began from:

- repository root: `D:\deviation-protocol`;
- branch: `main`;
- `HEAD`: `f988a95baa3ae1b69183c872a5b98cfd96abd88e`;
- local `origin/main`: `f988a95baa3ae1b69183c872a5b98cfd96abd88e`;
- ahead/behind: `0/0`;
- `HEAD` subject:
  `docs(product): freeze structured player-character contract`;
- clean working tree; and
- empty index.

The baseline implements the deterministic Session-based vertical slice through
Phase 3.2b. It does not implement the two frozen product specifications named
above, a Run aggregate, a continuous-story-line aggregate, a stable
player-character identity, controller-binding persistence, player-character
lifecycle, or applicable character version/reference binding.

## 6. Current-state implementation map

### Existing identity and state surfaces

| Area | Current evidence | Current meaning | Planned effect |
| --- | --- | --- | --- |
| Authenticated controller | `RequestPrincipal` in `src/deviation_protocol/application/identity.py`; development composition in `src/deviation_protocol/api/dependencies.py` | Strict request principal whose `player_id` is the current controller/Session-owner subject; normal composition currently uses `demo-player` and `demo-dev-only` | Preserve as controller-domain input only; never use it as `player_character_id` or persist a submitted copy as authority |
| Repository player identity | `PlayerState.player_id` in `src/deviation_protocol/domain/state.py`; `GameSession.player_id` in `src/deviation_protocol/domain/models.py`; ownership checks in `SessionService` | One Session's player and owner, currently equal to `RequestPrincipal.player_id` | Retain narrower meaning; add an explicit, separately typed player-character binding only where authorized |
| Character definition | `CharacterDefinition` in `src/deviation_protocol/domain/content.py`; runtime `PlayerState.character_definition_id` inside `GameState`; application persistence record `PersistedSession.character_definition_id`; ORM `GameSessionRow.character_definition_id`; public `PublicPlayableCharacter`, `SessionMetadata`, and `PlayerVisibleStateProjection` fields | Static, versioned authored content used to seed deterministic state. The domain `GameSession` dataclass does not own `character_definition_id` | Never infer a canonical player character from template reuse, display name, tags, or definition ID |
| Session identity | `GameSession.session_id`, `SessionService`, `game_sessions`, browser Session storage documented by the public-client contract | One public play Session and same-tab recovery target | Keep distinct; loss or reset cannot create or mutate a canonical character |
| Request/action identity | `ActionSubmission.client_request_id`, `turn_id`, `turn_requests`, and request-status routes | Session-scoped idempotency and replay boundary | Reuse semantics, not rows or keys, for a new character-specific operation receipt |
| Provider job identity | `NarrativeJob.job_id` and `narrative_jobs` | Candidate-generation job tied to one Session turn | Never substitute for character identity or mutation authority |
| Runtime NPC identity | `NpcState.npc_id` | Scenario/Session-local instance | Keep separate from player-character and stable logical NPC identities |
| Current logical NPC key | `stable_npc_subject_key(scenario_id, npc_definition_id)` and `NpcMemoryRecord.subject_key` in `src/deviation_protocol/domain/player_memory.py` | Stable only inside the current implemented scenario-memory boundary | Preserve its current authority; do not claim it is the future cross-scenario logical NPC identity |

### Run, world, scenario, and visit

`ScenarioRuntimeState` in
`src/deviation_protocol/domain/scenario_runtime.py` owns scenario-local phase,
location, facts, clues, clocks, decisions, ending, evidence, and visit counters.
`GameSession` carries `scenario_id` and `scenario_version`. The database stores
those values on `game_sessions`; snapshots also carry scenario state.

No current source model or persistence record defines `run_id`,
`continuous_story_line_id`, `world_id`, `visit_id`, or `scenario_run_id`.
`phase_visit_counts` is a counter, not a stable visit identity. Phase 3.3's Run
design is approved but not implemented. Therefore:

- a `GameSession` must not be relabeled as a Run (`A`, `N`);
- a scenario ID or version must not be treated as a world or visit ID (`A`);
- same-story-line and later-world integration must be stop-gated on a real
  Run-owned binding surface (`T`, with the owning shape still `U`), while
  preserving the already-frozen rule that each continuous story line is bound
  to exactly one active player-character identity at a time (`A`); and
- the domain can define the character side of a typed binding before Run
  integration, but cannot invent Run lifecycle or movement mechanics (`E`).

### Request and action lifecycle

`FirstPhaseTurnOrchestrator` in
`src/deviation_protocol/application/turn_orchestrator.py` locks the Session,
validates the request, authoritative snapshot, state version, action
affordances, and replay binding, then commits events, memory, snapshot,
response, and version together through one `UnitOfWork`. Rejections can be
recorded without advancing Session state. Exact replay returns the prior
response; conflicting reuse is rejected.

`DurableNarrativeTurnOrchestrator` in
`src/deviation_protocol/application/narrative_turn_orchestrator.py` prepares a
job transactionally, calls the Provider outside the transaction, then re-locks
and revalidates Session version, fingerprint, scenario, request, and job before
finalizing. The orchestrator and
`SqlAlchemyNarrativeJobRepository` in
`src/deviation_protocol/infrastructure/repositories.py` use compare-and-swap
job transitions. There is no `NarrativeJobService` symbol.

These are evidence for repository transaction, idempotency, and recovery
patterns (`N`). They do not protect a player-character record today. Character
operations need their own aggregate lock, expected revision, operation receipt,
and transaction boundary (`A`, proposed as `T`).

### Canonical state ownership

`GameState` and strict subordinate models in
`src/deviation_protocol/domain/state.py` form the current authoritative
Session snapshot. State transitions are domain-owned and Provider output is
candidate-only. `AuthoritativeStateView` is detached.

A player-character record must not be embedded only inside `GameState`: Session
loss and Run reset must not remove it, and same-character continuity crosses
scenario boundaries. The proposed owner is a new server-side canonical
player-character aggregate in the domain, loaded and committed through a
dedicated application port and MySQL repository (`A`, `T`). Session and future
Run state hold validated references, not the master record.

### Database, migrations, and version mechanisms

`src/deviation_protocol/infrastructure/database.py` configures MySQL 8 through
SQLAlchemy `AsyncSession` and `asyncmy`; there is no SQLite fallback.
`src/deviation_protocol/infrastructure/orm_models.py` defines:

- `game_sessions`;
- `game_snapshots`;
- `domain_events`;
- `turn_requests`; and
- `narrative_jobs`.

`SqlAlchemyUnitOfWork` in
`src/deviation_protocol/infrastructure/unit_of_work.py` owns commit/rollback.
Repositories do not commit independently. Session snapshot saves use an
expected `state_version` compare-and-swap; narrative jobs also use expected
status/version-like predicates. Duplicate-key handling is MySQL-specific.

`src/deviation_protocol/infrastructure/demo_persistence.py` supplies a separate
process-local transactional store and matching repository/UoW behavior for the
deterministic Demo composition. It is not durable production persistence.
Structured-character support must not be added to that fixture automatically:
any Demo adapter needs explicit later scope and must preserve production domain
invariants without turning deterministic Demo identities into production ID
policy.

The directly inspected Alembic chain is linear:
`20260719_0001 -> 20260719_0002 -> 20260719_0003`. Revision
`20260719_0001` has no parent, `20260719_0002` revises
`20260719_0001`, and `20260719_0003` revises `20260719_0002`.
`20260719_0003` is the actual current head. `alembic/env.py` uses the same
metadata and async MySQL URL.
`tests/integration/test_mysql_connection.py` asserts the exact current head,
tables, columns, JSON types, foreign keys, and indexes.

Existing versions have distinct meanings:

| Existing mechanism | Meaning | Not equivalent to |
| --- | --- | --- |
| `GameState.schema_version` | Snapshot schema migration version | Character contract version or record revision |
| `GameSession.state_version` | Session optimistic-concurrency token | Character revision |
| `content_version` / `scenario_version` | Authored content compatibility | Applicable character reference |
| `PlayerMemoryState.memory_model_version` | Memory-model version | Character contract or revision |
| Provider request/proposal schema versions | Candidate protocol compatibility | Canonical character authority |
| Alembic revision | Database schema history | Any domain identity or record revision |

### Provider candidate handling

`NarrativeProvider` is the application `Protocol` owned by
`src/deviation_protocol/application/narrative_models.py`.
`NarrativeRequest`, `UntrustedNarrativeProposal`, and validation in
`src/deviation_protocol/application/narrative_models.py` and
`src/deviation_protocol/application/narrative_validation.py` use strict
schemas. A validated proposal remains a
candidate. `DurableNarrativeTurnOrchestrator` binds it back to trusted Session
state before a commit. No Provider model currently contains player-character
identity, lifecycle, controller binding, applicable reference, or a canonical
character mutation.

The first slice should add no such Provider output fields. If later narration
needs character context, a separately reviewed bounded compiler may provide an
allowlist; it must not expose canonical mutation authority (`MODEL-001`,
`MODEL-002`).

### Public-client projection

`SessionService` in
`src/deviation_protocol/application/session_service.py` constructs strict,
frozen public DTOs field by field, including
`PlayerVisibleStateProjection`, `PublicNpc`, and `PlayerSessionView`.
`PlayerMemoryProjection` is owned by
`src/deviation_protocol/application/player_memory.py` and is embedded in the
player and Session views. `SessionService` validates ownership and
snapshot/session identity before projection. `src/deviation_protocol/api`
returns fixed privacy-safe error envelopes; missing and unauthorized Sessions
share the safe not-found behavior.

The current public player projection exposes the narrower Session
`player_id` and static `character_definition_id`. It is not a structured
player-character projection. The new projection must use a distinct type and
must not silently change the meaning of those existing fields.

### NPC, relationships, memory, and consequences

`NpcState.relationship_bps` is current Session snapshot data; there is no
general persistent relationship aggregate. `PlayerMemoryState` is a bounded
Session snapshot index with scenario memory, significant experiences, event
receipts, and scenario-local NPC subject keys. The application memory projector
uses sealed event provenance and detached bounded projections.

There is no protected golden-memory subsystem, cross-scenario logical NPC
registry, general consequence aggregate, or explicit
`player_character_id` memory/relationship/consequence subject. These remain
outside the first slice. Compatibility hooks must make a future subject
explicit without replacing the current memory authority.

### Tests and verification

The repository uses:

- domain/application unit tests under `tests/unit`;
- real MySQL persistence and API integration tests under `tests/integration`;
- public playthrough and Demo boundary tests under `tests/e2e`;
- Web unit/build/lint checks under `web`; and
- `scripts/verify.ps1` modes for canonical verification.

`tests/integration/conftest.py` requires a `mysql+asyncmy` test URL whose
database is exactly `deviation_protocol_test`. The migration head and exact
schema are asserted. Later implementation work must use
`.\.venv\Scripts\python.exe` explicitly and must keep live Provider tests
disabled unless separately authorized.

## 7. Identity-domain mapping

| Domain | Current representation | Planned representation or boundary | Equality rule |
| --- | --- | --- | --- |
| Authenticated controller subject | `RequestPrincipal(authentication_scheme, player_id)` | Input to a trusted `ControllerBindingResolver` port | May authorize a binding; never equals character identity |
| Controller binding | None | Opaque server-issued or server-resolved binding reference, stored privately and required on every canonical record | Distinct from principal fields, Session, Run, request, and character |
| Player character | None | Permanent opaque `PlayerCharacterId` issued only by trusted server code | Equality only by exact canonical ID |
| Static character definition | `DefinitionId`, `character_definition_id` | Retained as content/template reference where separately relevant | Reuse never establishes character equality |
| Session | String-valued `GameSession.session_id` with strict bounded request/DTO fields | Retained narrower identity; optional future reference to an explicit Run participation binding | Never establishes character identity |
| Run | Not implemented | Run-owned aggregate defined by Phase 3.3 implementation | Binds a character and applicable reference; does not equal either |
| Continuous story line | Not implemented | Run/continuity-owned stable reference; exact shape unresolved. Each continuous story line is bound to exactly one active player-character identity at a time | A line cannot simultaneously bind a second or different active character. The inverse number of lines/Runs one character may occupy remains unresolved |
| World / scenario / visit | Scenario only; no world or visit identity | Run-owned references when implemented | Context/provenance only, never character identity |
| Applicable character reference | None | Typed pair/record containing exact `player_character_id`, supported contract version, and applicable `record_revision` | Exact match; distinct from current revision and every other version |
| Stable logical NPC | Scenario-local memory subject key only | Existing key retained; future cross-scenario identity remains deferred | Never runtime NPC ID, definition, name, or player character |
| Runtime NPC | `NpcState.npc_id` | Unchanged | Session/scenario local only |
| Client operation | Session `client_request_id`; turn and job IDs | Dedicated creation operation under a controller-binding scope, or a dedicated mutation operation under a player-character scope | Idempotency only, never subject identity; creation and mutation scopes are not interchangeable |
| Display name / prose | Static content and narration | Data only | Never identity evidence |

All boundary adapters must use different value-object types even when their
storage representations are strings (`A`, `T`). Code must not compare or copy
between domains merely because the underlying values happen to match.

## 8. Scope

The first implementation sequence is limited to:

1. a strict canonical record envelope capable of representing every required
   approved field group, with optional declarations remaining absent;
2. trusted creation with a never-reused identifier, required controller
   binding, `active` lifecycle, supported contract version, initial revision,
   continuity metadata, and provenance;
3. typed lifecycle policy and mutation paths for the admitted transition
   matrix, with `deceased -> active` deterministically unavailable until an
   approved adjudication authority exists;
4. exact expected-revision checking, full-candidate validation, atomic commit,
   operation replay protection, and privacy-safe failures;
5. storage and validation of an applicable character version/reference with no
   general reference-mutation path;
6. a detached, allowlisted self projection;
7. a typed character-subject compatibility boundary for future Run, memory,
   relationship, consequence, and logical-NPC integration; and
8. tests and documentation proving only the behavior actually implemented.

The slice must not be described as complete structured-player-character product
implementation if Run continuity, public exposure, or adjacent subsystem
integration remains stop-gated.

## 9. Explicit exclusions

The first implementation slice explicitly excludes:

- character creation UI or frontend redesign;
- free-form biography systems;
- mandatory biography, body, appearance, class, origin, personality, skills,
  inventory, statistics, combat, or progression fields or systems;
- profile-completion, activation, quick-start-template, vocabulary,
  localization, or default-selection product rules;
- multiple concurrent characters per controller and character limits;
- shared control, multiple controllers, delegation, controller transfer,
  cross-account transfer, account recovery, or unbinding;
- arbitrary cross-Run or cross-story-line movement;
- continuity-line restart/resume, successor/replacement behavior, and the
  inverse number of simultaneous story lines or Runs one character may occupy;
- hard deletion and every delete API or repository method;
- retention, archival, restoration, cloning, merging, or recovery policy;
- resurrection, rebirth, reincarnation, time-reversal, or equivalent identity
  policy;
- consequence inheritance, erasure, or reversal;
- pinned, floating, checkpointed, migrating, automatically following, or any
  other general applicable-reference/revision-following policy;
- full relationship, consequence, or memory redesign;
- protected golden-memory subsystem implementation;
- cross-scenario logical NPC identity design;
- generalized Run, world, visit, transition, or movement implementation;
- unrelated narrative-generation or Provider protocol changes;
- public character-profile editing or a general canonical patch endpoint;
- new production authentication/account authority;
- production rollout, deployment, backfill from prose or existing identities;
  and
- unrelated cleanup.

If any excluded item proves technically unavoidable, the affected phase must
stop and return for product or architecture authority rather than adding it.

## 10. Canonical record implementation design

### Logical aggregate

The domain aggregate must represent the approved logical record, not expose a
database row or accept a wire DTO as canonical. The proposed closed envelope is:

| Logical member | First-slice treatment | Class |
| --- | --- | --- |
| `contract_version` | Required exact supported value `structured-player-character/v1`; unsupported values fail | `A` |
| `player_character_id` | Required immutable opaque value object issued by trusted server code | `A`; representation `T/U` |
| `record_revision` | Required ordered server token; proposed positive integer starting at one and advancing by one per commit | Semantics `A`; numeric form/start `T` |
| `controller_binding` | Required private opaque reference resolved from trusted authentication authority | `A`; resolver/storage `T` |
| `lifecycle` | Required closed enum: `active`, `retired`, `deceased` | `A` |
| `character_core` | Required strict group, capable of approved declarations; every individual field optional and absence preserved | `A` |
| `narration_preferences` | Required strict group; optional internal-thought preference with the three approved values and no silent default | `A` |
| `character_development` | Strict collection, initially empty because no approved mutation issuer is in the slice | `A/E` |
| `continuity_metadata` | Required strict group holding only trusted explicit references/evidence supplied by an owning authority; may contain no current-line reference when none is authorized. A line binding cannot simultaneously name a second or different active player character | Frozen line-to-character invariant `A`; exact storage, inverse cardinality, and post-ending/restart/successor behavior `U` |
| `authority_provenance` | Required mutation fact matching target, prior/result revision, mutation kind, authority class, and trusted source reference | `A`; storage layout `T` |

The supported `character_core` schema must be capable of the exact approved
scope: name/code name, preferred address, adult identity/gender expression,
broad adult age presentation, broad appearance direction plus a small bounded
feature set, outward presentation, inward tendency, reality anchor, and custom
values including intentionally undecided. No field becomes required in the
first slice. Because exact lengths, vocabularies, representation of custom
values, and activation requiredness are deferred, Phase 1 must either:

- implement only lossless optional typed slots whose representations have no
  material product consequence; or
- stop for approval before selecting bounded schemas.

It must not accept unrestricted JSON, silently truncate, invent defaults, or
turn free text into arbitrary canonical fields.

### Frozen optional-declaration and sovereignty rules

The logical domain representation must make declaration state explicit without
prejudging the later wire format. Every supported optional slot must preserve
these distinct states:

| Logical state | Meaning | Validation rule |
| --- | --- | --- |
| Omitted/unset | No value was supplied and no canonical declaration exists | Must remain unset; a reader, migration, server, or Provider cannot fill it |
| Explicitly absent | The player explicitly declared that the slot has no value | Must remain distinguishable from omission and from intentionally undecided |
| Declared value | The player supplied one bounded value accepted by the slot's trusted workflow | Must retain the exact approved meaning after field-specific validation |
| Intentionally undecided | The player explicitly chose not to decide yet where the approved contract permits that state | Must remain distinguishable from omission, explicit absence, and a declared value |

The supported optional slots are exactly the approved scope: name/code name,
preferred form of address, adult identity/gender expression, broad adult age
presentation, broad appearance direction, the bounded distinguishing-feature
collection, outward presentation, inward tendency, reality anchor, custom
values, and internal-thought narration preference. This list adds no
biography, body, origin, class, skill, inventory, statistics, combat, or
progression field.

For internal-thought narration preference, the declaration wrapper may record
omitted/unset, explicitly absent, or intentionally undecided without treating
any of those states as a selected preference. Only a declared preference value
may contain `high-immersion`, `balanced`, or `high-agency`. `balanced` is a
recommendation and must never be written as a silent canonical default.

Every provided broad age presentation must validate as adult. A representation
whose bounded vocabulary or custom-value rules cannot prove that condition is
a Phase 1 stop condition; implementation must not guess an age category or
accept a non-adult presentation.

Player-authored declarations, external server facts, and presentation
preferences require separate subordinate types. Provider prose and observable
external facts cannot settle subjective inner state. `character_development`
remains empty until a trusted event-derived entry type is separately approved.
If a later in-scope subjective entry is admitted, it must carry explicit
player expression or confirmation. Server inference, Provider/narration
inference, NPC output, summaries, events, and external consequences cannot
serve as canonical authority for a player-controlled thought, feeling, motive,
belief, value, intention, or commitment. Conversely, a player-authored
subjective declaration can establish only the character's stated inner state;
it cannot establish an NPC response, world fact, or external consequence.

Traceability for these frozen rules is explicit:

| Authority requirement | Canonical design and validation | Phase and tests | Stop/acceptance trace |
| --- | --- | --- | --- |
| Every approved optional declaration and absence meaning | This section's closed slot list and four-state logical wrapper; strict full-record validation | Phase 1; “Every supported optional declaration slot”, “Omitted versus explicitly absent”, and “Explicitly absent versus intentionally undecided” rows in section 26; persistence round trips in Phase 2 | Phase 1 state-distinction stop conditions; acceptance criterion 13 |
| Adult-only age presentation | Provided age values require a representation that proves adult presentation | Phase 1 domain/service tests; Phase 2 round trip where stored | Phase 1 adult-proof stop condition; acceptance criterion 13 |
| No silent narration default and preserved undecided state | A selected preference is separate from omitted, absent, and intentionally undecided; only three selected values are allowed | Phase 1 unit tests and Phase 2 persistence tests in section 26 | Phase 1 default/state-distinction stop conditions; acceptance criterion 13 |
| Player sovereignty over subjective state | Separate player-expression/confirmation authority type; no server, Provider, narration, NPC, summary, event, memory, or consequence inference path | Phase 1 domain/application tests; later contract/integration tests only where a real boundary exists | Phase 1 subjective-authority stop condition; acceptance criterion 13 |
| Player declarations do not establish external facts | Player-authored subjective type cannot satisfy world/NPC/consequence authority types | Phase 1 domain/application tests and any later real public-boundary contract test | Missing authority separation is a Phase 1 stop; acceptance criterion 13 |

### Ownership and mutation authority

The domain aggregate owns invariants and returns a detached complete candidate.
Independent policy classes authorize creation, retirement, ordinary
reactivation, final death, and the unavailable authorized-continuity-return
route. An application service:

1. authenticates through existing principal context;
2. resolves the trusted controller binding;
3. locks/loads the current aggregate and contextual authority;
4. verifies ID, controller, contract version, expected revision, lifecycle,
   applicable reference, and relevant Run/world/scenario/visit references;
5. invokes exactly one typed policy;
6. validates the complete resulting record;
7. appends trusted provenance;
8. commits allocation/current record/revision history, the matching successful
   creation or mutation receipt, and any in-scope binding effect in one
   transaction; and
9. constructs a detached response after successful commit.

There is no generic dictionary patch, deserialization directly into an ORM
object, client-selected authority class, or Provider-originated mutation.

### Public and private treatment

The canonical aggregate and persistence model are private. Controller binding,
authentication subjects, provenance internals, private declarations, hidden
continuity/adjudication facts, operation receipts, policy traces, Provider
payloads, memory, and generation internals are not public. The projection
allowlist is specified in section 18.

## 11. Permanent ID and non-reuse design

The trusted `PlayerCharacterIdIssuer` must allocate a fresh opaque,
domain-qualified identifier. The caller cannot propose, restore, or select the
ID. Accepted Phase 1 fixes the syntax to its 1–128-character opaque-reference
alphabet, and the section 20 review candidate fixes its database
representation. The production entropy source and random/monotonic issuance
algorithm remain unresolved; they must produce opaque, non-meaningful,
collision-checked values within that accepted envelope.

The proposed persistence invariant (`T`) separates ever-issued identity from
the mutable current record:

- an append-only identity-allocation row records every issued
  `player_character_id`;
- the canonical current-record row references that allocation;
- allocation and initial record insert occur in one transaction;
- the allocation primary/unique key rejects collision;
- no repository port exposes deletion of either row; and
- migration downgrade/recovery must never make a formerly issued ID eligible
  for allocation.

This allocation ledger is required by the section 20 review candidate because
a mutable or archived record alone cannot prove non-reuse after record
absence. A single-table alternative would be a new technical amendment
requiring fresh review; it is not an implementation-session choice. Database
uniqueness is necessary but not sufficient if rows can disappear.

Restoration of the same canonical record, if ever authorized, must locate the
existing allocation and preserve the ID. The first slice implements no
restoration. New creation always allocates a new ID, including successors,
same-name characters, same-controller characters, and records resembling an
existing one. No code may search by display name, controller, Session, Run,
memory, Provider result, definition, or prose to establish identity.

Tests must use a deterministic injected issuer to force collisions and prove
the second allocation fails or retries with a new never-issued value without
partially committing. Production entropy/format remains a review gate, not a
product identity rule.

## 12. Controller-binding design

The repository has no production account/controller aggregate and only a
development principal. The minimum compatible boundary is therefore:

- a `ControllerBindingResolver` application port receives the authenticated
  `RequestPrincipal` from trusted middleware/composition;
- it returns a distinct opaque `ControllerBindingRef`;
- Phase 2's private registry stores only that opaque binding reference; any
  future trusted authentication-scheme/subject mapping belongs to the Phase 3
  resolver design and must not select transfer, shared-control, or account
  semantics silently;
- the canonical record stores only the binding reference, not client-submitted
  authority; and
- authorization re-resolves the current principal and exact-matches the stored
  binding before reading private state or mutating.

The mapping table/adapter is a proposed technical choice (`T`). It does not
create transfer, shared-control, recovery, unbinding, or account-change
semantics. No such mutation method is allowed. Persisting a hash or direct copy
of `RequestPrincipal.player_id` as the binding is rejected because it would
silently conflate domains and make future account changes an identity rule.

Creation fails atomically if the binding cannot be resolved. Every loaded
`active`, `retired`, or `deceased` record must contain it. Every
identity-preserving mutation copies the exact binding into the complete
candidate and validates equality. Missing or altered bindings fail before
commit. Session loss, browser reset, Run reset, transport or Provider failure,
retirement, death, or record projection never calls a binding mutation.

There is no safe production controller source today. Accordingly:

- domain, persistence, and application behavior can be tested with an injected
  trusted resolver;
- a development-only adapter may be used only in explicitly isolated tests or
  Demo composition if separately authorized; and
- a normal public creation/mutation endpoint is blocked until its composition
  has an authoritative non-development resolver or an explicitly accepted
  limited deployment scope.

This is an authority gap and phase stop condition, not permission to treat the
current development principal as a production account model.

## 13. Lifecycle implementation design

Lifecycle is a closed domain enum. Each action is a distinct typed command and
independent policy class, consistent with repository guardrails:

| Transition | Proposed policy | Required evidence | First-slice result |
| --- | --- | --- | --- |
| `active -> retired` | `RetirePlayerCharacterPolicy` | Authenticated matching controller, explicit confirmation bound to ID and expected revision, valid continuity-ending evidence where a current line exists | Same ID/binding/reference; line ends atomically; revision advances once |
| `retired -> active` | `ReactivatePlayerCharacterPolicy` | Authenticated matching controller, explicit confirmation, and separately authorized active-line plus Run/world binding evidence | Same ID/binding/reference; explicit current line established atomically; reject while evidence source is unavailable |
| `active -> deceased` | `FinalDeathPlayerCharacterPolicy` | Trusted server outcome authority and exact identity/revision/context/event evidence | Same ID/binding/reference; current line ends; death provenance persists |
| `retired -> deceased` | `FinalDeathPlayerCharacterPolicy` | Trusted server outcome authority and exact identity/revision/event evidence | Same ID/binding/reference; no line reopened |
| `deceased -> active` | `AuthorizedContinuityReturnPolicy` | Future separately approved adjudication and lifecycle authority | Deterministic `policy unavailable` rejection in the first slice |

All other transitions, including same-state lifecycle commands, ordinary
reactivation of deceased records, client-claimed death, and narration-implied
retirement, are rejected. A rejected transition leaves the record, revision,
binding, continuity, reference, provenance, operation result, relationships,
memories, and consequences unchanged. It receives no durable
character-operation receipt in the first slice. Existing Session
`turn_requests`, when applicable to an existing Session action, retain only
their narrower authority and are not a character receipt.

Confirmation must be structured, explicit, scoped to exact command, character,
expected revision, and operation ID. Ambiguous dialogue, previous behavior,
inactivity, a displayed affordance, or Provider prose is not confirmation.
Exact confirmation token representation is a technical design for Phase 3 and
must not become a reusable capability or a new account-recovery system.

Final-death authority cannot be exposed as a controller/client command. Its
adapter must accept a trusted, verifiable server event reference. Because no
current Run/world outcome emits player-character final death, public
integration remains blocked until an owning narrower rule supplies that event.

## 14. Applicable-version/reference design

The applicable character reference is a distinct immutable value object for
consumer/Run bindings. It contains at least:

- exact `player_character_id`;
- exact supported character `contract_version`; and
- the exact applicable canonical `record_revision`.

It is not the current-record lookup key alone, the structured contract
document version alone, a Session `state_version`, Run Protocol/state version,
snapshot schema version, content/world/scenario version, memory model version,
Alembic revision, or Provider request/proposal version.

The first slice may construct and validate an initial exact reference only for
an explicit authorized consumer. It must not persist an unowned binding merely
because no Run exists. It supplies no general reference-mutation route. That
limited behavior is not approval of a pinned policy. In particular:

- scenario, genre, world, visit, Session, Run reset, browser reset, transport
  recovery, narration, Provider output, and client input cannot change it;
- same-story-line scenario changes and Run-authorized later-world progression
  must carry the exact existing reference;
- an attempted advance, rollback, substitution, same-ID/different-revision
  switch, or contract reinterpretation fails before any canonical or Run-side
  mutation; and
- if the canonical record later advances while a consumer holds an older
  applicable reference, the implementation must not silently decide whether
  that consumer follows it.

Pinned, floating, checkpointed, migrating, automatically following, and every
other revision-following policy remain unselected (`U`). Any need to alter the
reference is an immediate stop condition pending a separately approved policy.

## 15. Revision, concurrency, and atomicity design

### Record revision and optimistic concurrency

The proposed current-record row carries a positive `record_revision`. A write
uses one SQL compare-and-swap predicate over exact
`player_character_id`, current `record_revision`, and immutable
`controller_binding`, after locking or otherwise serializing the aggregate.
Exactly one affected row is required. The same transaction inserts the new
revision/provenance and the successful mutation receipt defined below.

Starting at revision `1` and incrementing by one is a repository-specific
technical proposal (`T`); the product requirement is an ordered server-issued
token with equality and successor checks (`A`). The domain API must still use a
distinct `PlayerCharacterRevision` type, not an integer shared with Session
state.

The Phase 1 implementation uses positive canonical signed 64-bit revisions,
from `1` through `9223372036854775807`. The maximum remains readable as an
existing canonical revision but cannot produce a successor. A transition that
would require `9223372036854775808` rejects before command fingerprint bytes,
receipt lookup, successful policy/result construction, receipt validation, or
stored-success disclosure. A valid `9223372036854775806` to
`9223372036854775807` transition and its exact stored-result replay remain
supported.

Cross-Run concurrency remains deferred. The first slice must nevertheless be
safe for concurrent commands against the one canonical record: only one
matching expected revision may commit; all losers refresh from the last
committed record.

### Complete validation

Every create/read-modify-write path must:

- reject missing, malformed, or unknown fields using strict models;
- reject unsupported contract versions;
- bind exact target identity and expected revision;
- resolve controller authority from trusted context;
- validate exact relevant Run/world/scenario/visit and applicable references
  when supplied by their owning authority;
- apply a typed command to a detached copy;
- validate the complete candidate, not only a patch;
- preserve unknown canonical fields losslessly only under a separately
  supported read-only compatibility rule; and
- prevent older writers from dropping fields.

Phase 1 defensive revalidation inspects the complete actual state of every
already-instantiated strict Pydantic model recursively, including instance
fields and Pydantic extra, private, and fields-set bookkeeping. It rejects
unknown or malformed source state before any model dump and never establishes
validity by dumping and reconstructing a possibly lossy copy.

The first version should fail closed on unknown stored fields rather than claim
additive compatibility not yet implemented. No ORM JSON dictionary is mutated
in place and no partial structured input is salvaged.

### Transaction and operation replay

Receipt persistence is gated on the complete first-slice protocol below being
independently reviewable and accepted before Phase 2 begins. It is a separate
character-aggregate protocol because current `turn_requests` are scoped by
`(session_id, client_request_id)`, bind one `turn_id` and action signature, and
protect only the existing Session action lifecycle. They do not protect a
player-character aggregate. The new protocol must not read, write, reinterpret,
or become a second authority for `turn_requests`, narrative request-status
routes, or the current action/request lifecycle.

#### Operation identity, ownership, and key scope

The first slice uses two non-interchangeable successful-operation receipt
scopes:

| Operation | Server-owned namespace | Receipt owner and unique key | Why |
| --- | --- | --- | --- |
| Canonical creation | `player-character.create/v1` | `(controller_binding, operation_namespace, operation_id)` | No `player_character_id` exists before successful allocation. The trusted controller-binding row is resolved and locked before receipt lookup or identity issuance |
| Canonical mutation | `player-character.mutate/v1` | `(player_character_id, operation_namespace, operation_id)` | The canonical character is the aggregate owner. The current principal must still resolve to the record's exact stored `controller_binding` before receipt data or character existence is disclosed |

`operation_namespace` is selected by server routing, not submitted as authority.
`operation_id` is a strict, bounded, opaque idempotency key and never an
identity, capability, confirmation, or authority token. A creation receipt
stores the allocated `player_character_id` as result data; it is not part of
the creation key. A mutation receipt stores its target character, but no
combined controller-binding-and-character scope exists.

#### Normalized fingerprint and equivalence

The service first validates a typed command, then creates one canonical JSON
fingerprint payload. Common fields are the exact operation namespace, command
kind, and supported contract version. A creation fingerprint additionally
contains every submitted canonical declaration in its validated logical
state, including distinct tags for omitted/unset, explicitly absent,
intentionally undecided, and declared values. It excludes the not-yet-issued
`player_character_id`. A mutation fingerprint additionally contains the exact
target `player_character_id`, expected record revision, typed mutation body,
and the exact confirmation or trusted event/context/reference identifiers
required by that policy.

Canonicalization uses NFC strings, sorted object keys, no floats or non-JSON
values, and the canonical order defined by each typed field. It must not
case-fold, collapse meaningful whitespace, sort an ordered collection, merge
omission with explicit absence, merge absence with intentionally undecided, or
otherwise invent field equivalence. Semantically unordered collections may be
sorted only when their approved domain type declares them unordered. The
fingerprint is SHA-256 over UTF-8 canonical JSON with stable separators. Phase
1 must publish golden fingerprint vectors covering Unicode, ordering, every
declaration-state tag, confirmation/evidence bindings, and every admitted
command kind before Phase 2 creates a receipt schema.

After current controller authorization:

- an existing receipt under the exact scope key with the exact fingerprint,
  command kind, target/result binding, and result-schema version is an exact
  replay;
- exact replay returns the original stored privacy-safe successful result and
  performs no allocation, policy evaluation, canonical mutation, history
  append, or revision advance;
- the replay remains equivalent even when the current canonical record has
  advanced beyond the receipt's resulting revision;
- the same scope key with any different fingerprint, command kind,
  target/result binding, or result-schema version is
  `IDEMPOTENCY_CONFLICT` and changes nothing; and
- a malformed or internally inconsistent stored receipt is an integrity
  failure, never permission to reconstruct a winner heuristically.

The accepted receipt stores a strict, versioned, privacy-safe result envelope
rather than reconstructing success from the later current record. Creation
stores the allocated ID, contract version, initial resulting revision, and
lifecycle. Mutation stores the target ID, contract version, command result,
resulting revision, and resulting lifecycle. It stores no controller subject,
private declarations, provenance detail, confirmation secret, Provider data,
or complete canonical record. Replay validates that envelope and its receipt
bindings before returning it. Revision history remains authority for canonical
history, but it is not used to silently synthesize a different replay result.

#### Rejections and bounded first-slice retention

Only successfully committed creation and mutation operations receive durable
character receipts in the first slice. Validation failures, authority
failures, stale revisions, unavailable policies, lifecycle rejections, and
idempotency conflicts receive no character receipt and are re-evaluated if
resubmitted. Because they make no canonical mutation, this does not permit a
duplicate successful effect. The first slice has no receipt `PENDING` state,
external call, or multi-transaction character operation.

There is no receipt cleanup, deletion, archival, or rejected-operation receipt
path in the first slice. Receipt identifiers, fingerprints, and stored result
envelopes have strict row-size bounds, and the slice remains non-production
and without a public rollout. Retaining successful receipts for this bounded
slice is a technical safety assumption only; it does not select a permanent
retention, deletion, archival, or audit product policy. Any production rollout
or cleanup path is a later stop-gated decision.

### Failure atomicity

Allocation, binding reference, current record, initial/current revision history,
continuity effect, accepted successful-operation receipt, and its stored safe
result commit together where they are part of one character operation.
Creation locks the resolved controller-binding owner and checks its creation
receipt scope before identity allocation. Mutation locks the current character,
authorizes its stored binding, and checks its mutation receipt scope before
expected-revision evaluation. A unique-key race rolls back and re-reads the
winner in a fresh transaction; it never repeats allocation or mutation after a
winner is proven. A persistence exception rolls back the whole transaction. A
response is not reported successful before commit. In-memory candidates are
discarded or restored after rollback, following the current
`SqlAlchemyUnitOfWork` pattern.

Provider work, if ever used, occurs outside the canonical transaction and is
rebound to exact current state before policy evaluation. Provider failure never
opens a fallback mutation path.

## 16. Run and story-line continuity integration

The character side of a future binding is:

```text
Run-owned binding
  -> exact stable player_character_id
  -> exact applicable character contract/revision reference
  -> Run-owned continuous-story-line, world, scenario, and visit references
```

The current repository lacks the Run-owned side. Phase 4 must therefore stop
before persistence or API integration unless the Phase 3.3 implementation
provides an approved aggregate and transaction boundary. The plan must not add
`run_id` columns whose semantics are guessed from `GameSession`.

The missing runtime aggregate does not make all cardinality unresolved. The
frozen line-to-character invariant is already authoritative:

- each continuous story line is bound to exactly one active
  `player_character_id` at a time;
- a line cannot simultaneously acquire a second or different active
  player-character binding; and
- a scenario, world, visit, Run boundary, retry, or concurrency race cannot
  replace that binding as a side effect.

Phase 4 must enforce this invariant at the Run/line service boundary inside the
same transaction strategy that establishes, validates, or authoritatively ends
the owning binding without providing a replacement path. The service must lock
or otherwise serialize the exact line owner, inspect
the existing active binding, and reject a second or conflicting
`player_character_id` before either aggregate changes. The persistence
mechanism must provide a database backstop appropriate to the real Run/line
schema. If that schema does not yet permit a uniqueness/constraint strategy,
Phase 4 records the invariant and stops before persistence rather than
inventing a Run table, lifecycle, or replacement policy.

Once that owner exists, integration must:

1. load the Run-owned binding and canonical character under the transaction
   strategy approved for the owning aggregates;
2. exact-match player-character ID and applicable reference;
3. prove that the continuous story line has exactly one active
   player-character binding and reject a second or conflicting binding;
4. preserve both character ID and applicable reference across same-line
   scenario changes;
5. preserve both across Run-authorized progression into a later world;
6. let Run policy alone select world, scenario, visit, eligibility, and world
   state;
7. reject a boundary that attempts to create, replace, merge, transfer,
   retire, reactivate, kill, delete, or re-version the character; and
8. bind any resulting memory/relationship/consequence provenance to the exact
   logical subjects.

If a cross-aggregate atomic commit is required but the Run and character
records cannot share the existing MySQL `AsyncSession` transaction, integration
stops for an explicit consistency design. An outbox, saga, or eventual
consistency protocol must not be invented in this plan.

Existing Sessions remain legacy narrower records. A future Session
participation field may reference a Run binding only when explicitly created by
trusted Run/Session orchestration. It may be nullable for legacy Sessions and
must never be backfilled from `GameSession.player_id`,
`character_definition_id`, scenario, browser storage, or prose.

Session loss, browser reset, Run reset, and transport failure may invalidate
ephemeral participation/recovery state, but cannot delete or mutate the
canonical character. Exact Run reset and continuity-line restart semantics
remain deferred.

This one-direction invariant does not decide how many simultaneous story lines
or Runs one character may occupy, what binding remains after retirement or
death beyond the already-approved current-line ending effect, whether an
authorized return resumes or starts a line, how restart/resume works, how a
successor or replacement is represented, or whether cross-Run/cross-line
movement is ever allowed.

## 17. Provider, client, and trusted-server boundaries

The trusted server is the only canonical mutation boundary. A client may send
a typed intent, bounded player-authored declaration through a separately
approved profile workflow, expected revision, operation ID, and explicit
confirmation. The server independently resolves identity, controller binding,
authority, lifecycle, and context.

The first slice proposes no changes to `NarrativeProvider`,
`NarrativeRequest`, `UntrustedNarrativeProposal`, prompt schemas, or narrative
validation. Provider output remains candidate-only and contains no canonical
mutation command. Narration cannot create, identify, bind, retire, reactivate,
kill, resurrect, re-version, or otherwise patch a character.

If later Provider context is necessary, the change must be narrow and
independently reviewed. A compiler may include only approved public/bounded
fields plus necessary confirmed lifecycle state. It must exclude controller
binding, private provenance, private memory, hidden facts, capabilities, policy
traces, full canonical JSON, and mutation affordances. The finalize step must
rebind exact character, applicable reference, expected canonical revision, Run
context, Session request, and authoritative state. `MODEL-001` and `MODEL-002`
remain unchanged.

The existing public-client Session recovery contract also remains unchanged.
Character operations need a distinct recovery record; browser storage, pending
Session request identity, and action replay cannot become character identity or
authority.

## 18. Public projection design

The minimum controller-self projection is a new strict, frozen application DTO
built field by field. It must be detached from ORM and domain mutable
containers. The initial allowlist proposed for independent review is:

| Field | Treatment | Reason |
| --- | --- | --- |
| `player_character_id` | Include as opaque controller-safe reference | Required to bind self reads and typed intents |
| `contract_version` | Include only if the public operation needs compatibility negotiation | Never treated as identity/revision |
| `record_revision` | Include as concurrency token | Required for stale-write protection |
| `lifecycle` | Include | Controller-safe current status |
| `applicable_character_reference` | Include only on an authorized Run/consumer projection that must refresh it | Exact-match visibility without mutation authority |
| selected `character_core` declarations | Exclude in the minimum envelope; add only after field-specific privacy classification | Avoid inventing a full profile contract |
| effective narration preference | Exclude until a permitted update/default workflow exists | `balanced` is a recommendation, not a default |
| `controller_binding` | Exclude; at most a server-derived self-owned indication if later necessary | Internal authority reference |
| `continuity_metadata` | Exclude internals; a separately approved safe status may be added later | Contains authority/adjudication context |
| `character_development` | Exclude until entry types and privacy allowlist exist | May contain private or consequence facts |
| `authority_provenance` and operation receipts | Exclude | Internal audit/authority material |

This is a minimal envelope, not a character-profile product. If reviewers
determine that exposing even the opaque ID or revision would conflict with the
current public protocol, Phase 5 stops for a narrow public-client contract
update.

Projection construction must:

- authorize the controller before fetching private state or disclosing
  existence;
- exact-match requested character, stored binding, and any relevant Run
  reference;
- return the same privacy-safe not-found response for missing/unauthorized
  identity where retained `API-001` applies;
- fail safely on unsupported/stale identity/reference state;
- deep-copy or serialize/validate to a detached immutable object;
- ignore no fields: private/unknown fields are explicitly not selected; and
- expose descriptions and affordances only, never a capability to bypass
  server policy.

The current `PlayerVisibleStateProjection.player_id` retains its narrower
Session meaning. It must not be renamed, repurposed, or silently populated
with `player_character_id`.

## 19. NPC, relationship, memory, consequence, and golden-memory integration

The minimum compatibility type is an explicit `PlayerCharacterSubjectRef`
containing the stable `player_character_id` and, where the consumer needs
versioned meaning, the exact applicable reference. Future authoritative
relationship, memory, and consequence ports must require this subject rather
than accept display name, controller identity, Session player ID, or prose.

For an NPC-involving fact, the interface must also require a stable logical NPC
subject. The current `NpcState.npc_id` remains runtime-local. The current
scenario-local `NpcMemoryRecord.subject_key` remains authoritative only within
its existing boundary and is not promoted to a cross-scenario identity.

The first slice should add compatibility tests/value types but not rewrite
`PlayerMemoryState`, `NpcMemoryRecord`, relationship basis points, or event
receipts. Full persistence integration is blocked until:

- a player-character participates through an explicit Run/Session binding;
- the owning memory/relationship/consequence contract specifies its record
  shape and transaction;
- cross-scenario logical NPC identity is approved where needed; and
- migration/compatibility behavior for current Session memories is reviewed.

Identity-preserving retirement, death, reactivation, scenario movement, and
later-world movement must keep subject references attached. New characters
receive no inherited memory, relationship, promise, injury, item, world fact,
golden memory, or consequence merely from shared controller/name/template or
similarity.

Protected golden memory remains a separate, not-implemented subsystem. It must
not be represented by `PlayerMemoryState`, ordinary summaries, prompt context,
Provider output, or continuity notes. The first slice may define only a
prohibition/subject interface; it must not add golden-memory storage.

## 20. Persistence and migration plan

### Proposed ownership and schema sequence

Status of this subsection: **technical-prerequisite review candidate awaiting
fresh independent acceptance; not frozen and not implementation
authorization.**

Once this candidate has been independently accepted and Phase 2 has been
separately authorized, one new linear Alembic revision may directly revise
`20260719_0003`, the current head inspected for this amendment. Phase 2 has
exactly six persisted record families:

| Record family | Proposed table | Logical responsibility |
| --- | --- | --- |
| Controller-binding reference registry | `player_character_controller_bindings` | Record one already trusted opaque `ControllerBindingRef` so character rows and creation receipts can reference it atomically; it is not an authentication-subject mapping or resolver |
| Permanent identity allocations | `player_character_id_allocations` | Append-only ledger of every successfully issued `PlayerCharacterId`, preserving permanent non-reuse independently of the mutable current row |
| Current canonical records | `player_character_current` | One complete validated `CanonicalPlayerCharacter` at its current revision |
| Immutable revision history | `player_character_revisions` | One complete provenance-bearing canonical record for every committed revision |
| Successful creation receipts | `player_character_creation_receipts` | Durable exact replay/conflict result for `player-character.create/v1` under its controller-owned scope |
| Successful mutation receipts | `player_character_mutation_receipts` | Durable exact replay/conflict result for `player-character.mutate/v1` under its character-owned scope |

There is no seventh Phase 2 Run, Session, account, story-line, consumer,
applicable-reference, rejected-operation, pending-operation, archive, or
deletion record. The future Run/consumer character binding remains Phase 4
inventory only. No concrete Run or account parent schema exists, so Phase 2
must not fabricate one or add a foreign key to `game_sessions`. A later
Run-owning migration must choose its table and enforce the frozen
one-active-character-per-story-line direction without changing these six
families or silently selecting a reference-following policy.

Within this boundary, the controller binding owns a creation receipt; the
stable player-character identity is the mutation receipt owner, subject, and
target; namespace plus operation ID supplies command/idempotency identity;
expected/resulting revisions bind the mutation; and provenance supplies its
trusted source reference. The canonical mutation fingerprint additionally
binds the exact `ApplicableCharacterReference` and typed confirmation/evidence
defined by Phase 1. Account and Run identities are not required for these
Phase 1 operations and therefore have no Phase 2 column or fabricated parent.
The natural receipt scope keys are the authoritative private receipt
identities; no public receipt ID or surrogate is introduced.

#### Physical type, serialization, and timestamp conventions

All six tables use InnoDB, table default character set `utf8mb4`, and table
default collation `utf8mb4_bin`. Every opaque external/domain reference
(`player_character_id`, `controller_binding`, `operation_id`, and
`source_reference`) uses `VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin`.
Every one is non-empty, uses the accepted Phase 1
`[A-Za-z0-9][A-Za-z0-9_.:-]*` alphabet, and is at most 128 characters/bytes.
The adapter validates that rule both before writes and after reads. Because the
admitted alphabet is ASCII, this representation is a one-byte-per-character,
byte-stable round trip. MySQL performs no trimming, Unicode normalization,
case folding, semantic parsing, or identifier generation; values that differ
only by ASCII case remain distinct. The syntax and length come from the
accepted Phase 1 value objects and do not select a production issuance
algorithm.

Closed protocol/version/kind tokens use the explicitly sized ASCII
`ascii_bin` columns below. Canonical SHA-256 fingerprints use `BINARY(32)`,
never text or a collation; the adapter converts exactly between those digest
bytes and Phase 1's 64-character lowercase hexadecimal value. Reconstructed
hex must match the canonical lowercase form. Fingerprints are compared only
after scope-key lookup and are not separately indexed.

`record_canonical` is the exact output of
`canonical_character_operation_bytes(CanonicalPlayerCharacter)` and
`receipt_canonical` is the exact output for the corresponding
`StoredCreationSuccessReceipt` or `StoredMutationSuccessReceipt`. They use
`MEDIUMBLOB` (physical maximum 16,777,215 bytes), not MySQL `JSON`, text, or a
collation. Binary storage avoids MySQL JSON normalization or textual
reserialization and preserves exact canonical bytes. The declaration data is
embedded in `record_canonical` as the ordered `character_core` and
`narration_preferences` members. Their four-state tags preserve omitted,
explicitly absent, declared, and intentionally undecided values; ordered
feature/custom-value collections keep their accepted order. Phase 1 defines no
additional per-field text or collection ceiling, so Phase 2 adds none. Before
any write and after every read, the adapter must:

1. strictly parse one UTF-8 JSON object with duplicate keys, floats,
   non-standard constants, invalid Unicode, out-of-range integers, and unknown
   fields rejected;
2. reconstruct and run the reused Phase 1 complete model validation;
3. recompute the canonical bytes and require byte-for-byte equality with the
   stored blob;
4. recompute `canonical_player_declaration_bytes` from the reconstructed
   groups and enforce its aggregate 65,536-byte maximum; and
5. exact-match every duplicated relational identity, version, revision,
   lifecycle, provenance, key, fingerprint, and result column.

The record blob has no new arbitrary whole-record product limit: `MEDIUMBLOB`
is only the physical carrier, while the accepted Phase 1 declaration envelope
and all existing field/type limits remain authoritative. Receipt blobs must
have an `OCTET_LENGTH` from 1 through 65,536, matching
`MAX_STORED_CHARACTER_RECEIPT_CANONICAL_BYTES`. Oversize, non-canonical, or
malformed persisted data is an internal integrity failure and is never
truncated, repaired, defaulted, partially returned, or disclosed as success.

All timestamps are server-supplied UTC `DATETIME(6) NOT NULL` with no database
default and use MySQL's `1000-01-01 00:00:00.000000` through
`9999-12-31 23:59:59.999999` physical range. The adapter restores MySQL's
timezone-naive value as UTC, following the existing repository convention.
Immutable families have only `created_at`; `player_character_current` also has
`updated_at`, changed only with its successful CAS. Timestamps never establish
identity, order, revision, replay equivalence, confirmation, lifecycle, or
continuity.

No table has an auto-increment or opaque surrogate identifier. The authoritative
natural or composite domain identities below already provide stable keys; a
surrogate would add no integrity and must not replace those keys.

#### `player_character_controller_bindings`

| Column | MySQL type | Null/default | Meaning and validation |
| --- | --- | --- | --- |
| `controller_binding` | `VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin` | NOT NULL; no default | Primary key; exact Phase 1 `ControllerBindingRef` |
| `created_at` | `DATETIME(6)` | NOT NULL; no default | Server UTC audit time only |

Primary/candidate key: `PRIMARY KEY (controller_binding)`. There are no other
unique or ordinary indexes and no foreign keys. The named opaque-reference
check applies. The row is immutable after insert; Phase 2 exposes no update,
unbind, rebind, transfer, shared-control, delete, or subject-enumeration
operation.

This table deliberately does not store authentication scheme, account ID, or
principal subject. A one-to-one scheme/subject mapping would prematurely
select controller cardinality, transfer, shared-control, or account-change
behavior. Phase 3's trusted resolver may later resolve a production
authentication context to an already meaningful `ControllerBindingRef`, but
that resolver and the decision to create/invoke a binding are not Phase 2
responsibilities.

#### `player_character_id_allocations`

| Column | MySQL type | Null/default | Meaning and validation |
| --- | --- | --- | --- |
| `player_character_id` | `VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin` | NOT NULL; no default | Primary key; permanently allocated Phase 1 identity |
| `created_at` | `DATETIME(6)` | NOT NULL; no default | Server UTC allocation audit time only |

Primary/candidate key: `PRIMARY KEY (player_character_id)`. There are no other
indexes or foreign keys. The named opaque-reference check applies. The adapter
provides insert/exists only; no delete, release, update, reuse, restoration, or
replacement port exists. A losing transaction rolls its uncommitted allocation
back; every committed allocation remains permanently reserved. Migration
downgrade is safe only while these Phase 2 tables are empty.

#### `player_character_current`

| Column | MySQL type | Null/default | Meaning and validation |
| --- | --- | --- | --- |
| `player_character_id` | `VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin` | NOT NULL; no default | Primary key and immutable aggregate owner |
| `contract_version` | `VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin` | NOT NULL; no default | Exact `structured-player-character/v1` |
| `record_revision` | signed `BIGINT` | NOT NULL; no default | Current Phase 1 revision, 1 through 9223372036854775807 |
| `controller_binding` | `VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin` | NOT NULL; no default | Exact immutable binding copied into every lifecycle state |
| `lifecycle` | `VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin` | NOT NULL; no default | Closed `active`, `retired`, or `deceased` value |
| `record_canonical` | `MEDIUMBLOB` | NOT NULL; no default | Exact full canonical record bytes |
| `created_at` | `DATETIME(6)` | NOT NULL; no default | Initial server UTC commit time |
| `updated_at` | `DATETIME(6)` | NOT NULL; no default | Latest successful CAS server UTC time |

Primary/candidate key: `PRIMARY KEY (player_character_id)`. Exact indexes are
`ix_spc_current_controller_identity (controller_binding,
player_character_id)` for authorized ownership lookup and
`ix_spc_current_identity_revision (player_character_id, record_revision)` for
the history foreign key. No name, declaration, prose, lifecycle-only,
fingerprint, or timestamp index exists. The primary-key lookup already selects
one row for CAS, so a redundant
`(player_character_id, record_revision, controller_binding)` index is not
added.

Checks enforce the supported contract token, positive signed-64-bit revision,
closed lifecycle set, non-empty blob, and opaque-reference rules. Adapter
validation enforces the cross-column/canonical-record equality and the
complete Phase 1 provenance/lifecycle matrix.

#### `player_character_revisions`

| Column | MySQL type | Null/default | Meaning and validation |
| --- | --- | --- | --- |
| `player_character_id` | `VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin` | NOT NULL; no default | Revision owner |
| `record_revision` | signed `BIGINT` | NOT NULL; no default | Committed revision, 1 through 9223372036854775807 |
| `contract_version` | `VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin` | NOT NULL; no default | Exact supported contract |
| `controller_binding` | `VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin` | NOT NULL; no default | Exact binding preserved at this revision |
| `lifecycle` | `VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin` | NOT NULL; no default | Lifecycle at this revision |
| `prior_revision` | signed `BIGINT` | NULL; no default | NULL only for creation; otherwise exact predecessor |
| `mutation_kind` | `VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin` | NOT NULL; no default | Accepted Phase 1 provenance mutation kind |
| `authority_class` | `VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin` | NOT NULL; no default | Exact Phase 1 provenance authority class |
| `source_reference` | `VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin` | NOT NULL; no default | Exact trusted Phase 1 `AuthoritySourceRef` |
| `record_canonical` | `MEDIUMBLOB` | NOT NULL; no default | Exact complete record at this revision |
| `created_at` | `DATETIME(6)` | NOT NULL; no default | Server UTC commit time only |

Primary/candidate key:
`PRIMARY KEY (player_character_id, record_revision)`. The exact ordinary index
is `ix_spc_revisions_controller_binding (controller_binding)` for the
controller-binding foreign key. No other unique or ordinary index is
authorized. Checks enforce the revision range, opaque
references, supported contract, lifecycle set, non-empty blob, and the
accepted Phase 1 matrix: creation is revision 1 with NULL predecessor,
`active`, and `trusted-creation`; retirement and final death have
`prior_revision = record_revision - 1` with their respective admitted
lifecycle/authority pair. No Phase 1-unavailable reactivation or continuity
return may be written as a successful revision.

History rows are insert-only. The complete reconstructed record must validate
before return; history is not a source from which an adapter may synthesize a
different current record or receipt result.

#### `player_character_creation_receipts`

| Column | MySQL type | Null/default | Meaning and validation |
| --- | --- | --- | --- |
| `controller_binding` | `VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin` | NOT NULL; no default | Creation receipt owner |
| `operation_namespace` | `VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin` | NOT NULL; no default | Exact `player-character.create/v1` |
| `operation_id` | `VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin` | NOT NULL; no default | Opaque Phase 1 idempotency key |
| `fingerprint` | `BINARY(32)` | NOT NULL; no default | Raw SHA-256 of the canonical creation command payload |
| `command_kind` | `VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin` | NOT NULL; no default | Exact `CREATE` |
| `result_schema_version` | `VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin` | NOT NULL; no default | Exact `player-character.create-result/v1` |
| `result_player_character_id` | `VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin` | NOT NULL; no default | Allocated identity returned by the stored result |
| `result_contract_version` | `VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin` | NOT NULL; no default | Exact result contract version |
| `resulting_revision` | signed `BIGINT` | NOT NULL; no default | Exact initial revision 1 |
| `resulting_lifecycle` | `VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin` | NOT NULL; no default | Exact initial lifecycle `active` |
| `receipt_canonical` | `MEDIUMBLOB` | NOT NULL; no default | Exact full Phase 1 stored creation receipt bytes |
| `created_at` | `DATETIME(6)` | NOT NULL; no default | Server UTC successful commit time only |

Primary/candidate keys are
`PRIMARY KEY (controller_binding, operation_namespace, operation_id)` and
`UNIQUE uq_spc_creation_receipts_result_revision
(result_player_character_id, resulting_revision)`. The latter both prevents
two creation receipts from claiming the same initial revision and supplies the
ordered child index for its history foreign key. There are no other indexes;
in particular, fingerprints are not lookup identities.

Checks enforce the fixed namespace, `CREATE`, result-schema and contract
tokens, revision 1, `active`, opaque-reference rules, and receipt byte length
1–65,536. Only a successfully committed result is representable. No rejection,
pending state, `REVISION_EXHAUSTED`, private declaration, controller subject,
Provider data, or public receipt format is added.

#### `player_character_mutation_receipts`

| Column | MySQL type | Null/default | Meaning and validation |
| --- | --- | --- | --- |
| `player_character_id` | `VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin` | NOT NULL; no default | Character aggregate receipt owner and target |
| `operation_namespace` | `VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin` | NOT NULL; no default | Exact `player-character.mutate/v1` |
| `operation_id` | `VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin` | NOT NULL; no default | Opaque Phase 1 idempotency key |
| `fingerprint` | `BINARY(32)` | NOT NULL; no default | Raw SHA-256 of the canonical mutation command payload |
| `command_kind` | `VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin` | NOT NULL; no default | Admitted successful Phase 1 command kind |
| `result_schema_version` | `VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin` | NOT NULL; no default | Exact `player-character.mutate-result/v1` |
| `expected_revision` | signed `BIGINT` | NOT NULL; no default | Revision bound by the accepted command |
| `result_player_character_id` | `VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin` | NOT NULL; no default | Exact stored-result target; must equal owner |
| `result_contract_version` | `VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin` | NOT NULL; no default | Exact result contract version |
| `result_command_kind` | `VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin` | NOT NULL; no default | Exact command kind in the stored safe result |
| `command_result` | `VARCHAR(32) CHARACTER SET ascii COLLATE ascii_bin` | NOT NULL; no default | `RETIRED` or `DECEASED` for admitted Phase 1 success |
| `resulting_revision` | signed `BIGINT` | NOT NULL; no default | Exact successor revision |
| `resulting_lifecycle` | `VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin` | NOT NULL; no default | Lifecycle in the stored safe result |
| `receipt_canonical` | `MEDIUMBLOB` | NOT NULL; no default | Exact full Phase 1 stored mutation receipt bytes |
| `created_at` | `DATETIME(6)` | NOT NULL; no default | Server UTC successful commit time only |

Primary/candidate keys are
`PRIMARY KEY (player_character_id, operation_namespace, operation_id)` and
`UNIQUE uq_spc_mutation_receipts_result_revision
(player_character_id, resulting_revision)`. The exact ordinary indexes are
`ix_spc_mutation_receipts_expected_revision
(player_character_id, expected_revision)` and
`ix_spc_mutation_receipts_result_revision
(result_player_character_id, resulting_revision)`. The expected-revision index
supports the prior-revision history foreign key. The result-revision composite
index supports both the result-allocation foreign key through its leftmost
`result_player_character_id` prefix and the result-revision history foreign
key through its complete ordered columns. No other unique or ordinary index is
authorized; no fingerprint, controller, lifecycle-only, or timestamp index
exists.

Checks enforce the fixed namespace and result schema, owner/result identity
equality, supported contract, opaque-reference rules,
`1 <= expected_revision <= 9223372036854775806`,
`resulting_revision = expected_revision + 1`, the maximum resulting revision
9223372036854775807, receipt byte length 1–65,536, and the admitted Phase 1
success pairs: `RETIRE`/`RETIRED`/`retired` or
`FINAL_DEATH`/`DECEASED`/`deceased`. Reactivation, continuity return, and
`REVISION_EXHAUSTED` have no successful Phase 1 result and therefore cannot be
stored. The fingerprint still binds the complete typed command, including
controller-authorized target, exact applicable character reference,
confirmation/evidence source, operation kind, and expected revision; the
stored canonical receipt remains the accepted Phase 1 format rather than a new
public format.

`REVISION_EXHAUSTED` remains only an internal failed-operation classification.
It is not a canonical record, history/provenance fact, successful result,
receipt column/value, replay-visible stored result, or public outcome. The
adapter rejects an operation requiring revision 9223372036854775808 before
fingerprint storage, receipt lookup/write, CAS, or result disclosure.

#### Exact keys, indexes, and foreign-key actions

Every foreign key uses `ON DELETE RESTRICT` and `ON UPDATE RESTRICT`. No
`CASCADE`, `SET NULL`, or database-generated update is permitted.

| Child columns | Parent | Constraint |
| --- | --- | --- |
| `player_character_current.player_character_id` | `player_character_id_allocations.player_character_id` | `fk_spc_current_allocation` |
| `player_character_current.controller_binding` | `player_character_controller_bindings.controller_binding` | `fk_spc_current_controller_binding` |
| `player_character_current.(player_character_id, record_revision)` | `player_character_revisions.(player_character_id, record_revision)` | `fk_spc_current_revision` |
| `player_character_revisions.player_character_id` | `player_character_id_allocations.player_character_id` | `fk_spc_revisions_allocation` |
| `player_character_revisions.controller_binding` | `player_character_controller_bindings.controller_binding` | `fk_spc_revisions_controller_binding` |
| `player_character_creation_receipts.controller_binding` | `player_character_controller_bindings.controller_binding` | `fk_spc_creation_receipts_controller_binding` |
| `player_character_creation_receipts.result_player_character_id` | `player_character_id_allocations.player_character_id` | `fk_spc_creation_receipts_allocation` |
| `player_character_creation_receipts.(result_player_character_id, resulting_revision)` | `player_character_revisions.(player_character_id, record_revision)` | `fk_spc_creation_receipts_revision` |
| `player_character_mutation_receipts.player_character_id` | `player_character_id_allocations.player_character_id` | `fk_spc_mutation_receipts_allocation` |
| `player_character_mutation_receipts.result_player_character_id` | `player_character_id_allocations.player_character_id` | `fk_spc_mutation_receipts_result_allocation` |
| `player_character_mutation_receipts.(player_character_id, expected_revision)` | `player_character_revisions.(player_character_id, record_revision)` | `fk_spc_mutation_receipts_prior_revision` |
| `player_character_mutation_receipts.(result_player_character_id, resulting_revision)` | `player_character_revisions.(player_character_id, record_revision)` | `fk_spc_mutation_receipts_result_revision` |

The migration also uses these exact check-constraint names and responsibilities.
Every `*_opaque` check requires the Phase 1 ASCII opaque-reference regular
language and a non-empty value; declared `VARCHAR(128)` width supplies the
maximum. Token checks use exact case-sensitive equality.

| Table | Exact named checks |
| --- | --- |
| `player_character_controller_bindings` | `ck_spc_controller_bindings_opaque` for `controller_binding` |
| `player_character_id_allocations` | `ck_spc_allocations_identity_opaque` for `player_character_id` |
| `player_character_current` | `ck_spc_current_identity_opaque`; `ck_spc_current_binding_opaque`; `ck_spc_current_contract`; `ck_spc_current_revision_range`; `ck_spc_current_lifecycle`; `ck_spc_current_canonical_nonempty` |
| `player_character_revisions` | `ck_spc_revisions_identity_opaque`; `ck_spc_revisions_binding_opaque`; `ck_spc_revisions_source_opaque`; `ck_spc_revisions_contract`; `ck_spc_revisions_revision_range`; `ck_spc_revisions_prior_range`; `ck_spc_revisions_provenance_matrix`; `ck_spc_revisions_canonical_nonempty` |
| `player_character_creation_receipts` | `ck_spc_creation_receipts_binding_opaque`; `ck_spc_creation_receipts_operation_opaque`; `ck_spc_creation_receipts_result_identity_opaque`; `ck_spc_creation_receipts_protocol`; `ck_spc_creation_receipts_result`; `ck_spc_creation_receipts_canonical_size` |
| `player_character_mutation_receipts` | `ck_spc_mutation_receipts_identity_opaque`; `ck_spc_mutation_receipts_operation_opaque`; `ck_spc_mutation_receipts_result_identity_opaque`; `ck_spc_mutation_receipts_protocol`; `ck_spc_mutation_receipts_owner_result`; `ck_spc_mutation_receipts_revision_successor`; `ck_spc_mutation_receipts_result`; `ck_spc_mutation_receipts_canonical_size` |

`ck_spc_revisions_prior_range` permits NULL only where the provenance matrix
permits creation and otherwise requires a positive signed-64-bit value below
the resulting revision. `ck_spc_revisions_provenance_matrix` and both receipt
`*_result` checks enforce the exact admitted combinations described in the
per-table sections. The two `*_canonical_size` receipt checks require 1–65,536
bytes. MySQL check enforcement is a required migration/integration assertion;
the adapter still repeats every check before persistence and after
reconstruction so a disabled, bypassed, or legacy constraint cannot create a
trusted object.

MySQL directly enforces table/key uniqueness, non-nullability, fixed-size
fingerprints, revision ranges/successor arithmetic, closed accepted tokens,
receipt byte bounds, and restrictive relationships. The adapter additionally
enforces opaque-reference syntax, exact canonical bytes, relational/blob
cross-bindings, and complete reconstruction because MySQL cannot validate the
Phase 1 typed value algebra or canonical JSON equality. Reused Phase 1 domain
rules remain the only business/lifecycle validator. Phase 3 later owns trusted
authentication, controller resolution, command sequencing, policy invocation,
and response disclosure. No SQL constraint or adapter branch may duplicate a
Phase 1 mutation policy or infer a repair.

The restrictive graph and absence of delete/update ports preserve allocation,
history, receipts, provenance, controller binding, and current identity without
inventing character deletion, archival, restoration, receipt cleanup,
controller rebinding, Run reassignment, cross-Run movement, reference
migration, or lifecycle recovery. Once any identity has been issued, removing
these tables through downgrade could release an identity and is prohibited;
recovery must be forward-only.

#### Phase 2 persistence ports and trust boundary

Phase 2 may add the following application-layer persistence ports and MySQL
adapters. Inputs are already typed Phase 1 values plus server UTC timestamps;
outputs are either `None` for not found or complete, strictly reconstructed
Phase 1 values. Repository methods flush where needed but never commit.

| Port/capability | Architectural input/output and database behavior | Failure and trust behavior |
| --- | --- | --- |
| Controller-binding registry `get` / `add` / `lock` | Exact `ControllerBindingRef`; load, insert, or `SELECT ... FOR UPDATE` the one registry row | Not found is `None`; duplicate insertion is a concurrency conflict; malformed data is integrity failure; no principal resolution, generation, update, or delete |
| Player-character allocation `exists` / `add` | Exact `PlayerCharacterId`; test existence or insert the allocation ledger row | Collision is a specific allocation conflict; no retry/issuer algorithm in the adapter and no release/delete |
| Current record `get` / `get_for_update` | Exact `PlayerCharacterId`; load unlocked or locked and reconstruct one complete `CanonicalPlayerCharacter` | Not found is `None`; any malformed column/blob/cross-binding fails before an object is returned |
| Initial current/history insert | One complete validated revision-1 record plus canonical bytes and server UTC time | Inserts history before its FK-backed current row; any allocation, binding, history, or validation mismatch fails and rolls back |
| Revision append | One complete validated successor record plus canonical bytes and server UTC time | Insert-only; duplicate or non-successor state is conflict/integrity failure, never history replacement |
| Current-record CAS | Complete validated successor, exact expected revision and controller binding, server UTC update time | Updates by exact identity/current revision/binding and requires one affected row; zero is optimistic-concurrency conflict; it cannot advance from 9223372036854775807 |
| Creation receipt `get` / `add` | Exact `CreationReceiptKey`; reconstruct or insert one validated `StoredCreationSuccessReceipt` and relational bindings | Not found is `None`; malformed receipt/result is integrity failure; duplicate natural key is a unique-race conflict, not heuristic replay |
| Mutation receipt `get` / `add` | Exact `MutationReceiptKey`; reconstruct or insert one validated `StoredMutationSuccessReceipt`, expected revision, and relational bindings | Same behavior as creation; no read occurs until the future trusted caller has authorized the current record's exact stored controller binding |

The UoW port may expose `controller_bindings`, `player_characters`,
`creation_receipts`, and `mutation_receipts` over the same SQLAlchemy
`AsyncSession`, with explicit `commit` and `rollback` matching the current
repository convention. Exiting without a successful commit or with any
exception rolls back. A unique-constraint loser must roll back the entire
transaction, open a fresh UoW, reauthorize through the future trusted caller,
and reread the durable winner; it must not reuse a failed session or repeat
allocation/mutation.

Phase 1 pure validation, fingerprint, receipt, replay/conflict, transaction
order, and mutation-policy operations must be reused. Phase 2 adapters may
persist, lock, CAS, reconstruct, and reject malformed storage; they may not
decide authentication, call a lifecycle policy, generate a production ID,
resolve a production controller, disclose a result, or duplicate business
validation in ORM/SQL logic. Phase 3 owns those trusted application decisions
and production composition. Public API/frontend, Run/story activation,
Provider/model, Demo, and later systems remain outside both the Phase 2 ports
and UoW.

### Transaction boundaries

The following remains the accepted end-to-end order, but Phase 2 implements
only the persistence/UoW primitives and test transaction harness needed to
prove it. Phase 3 later owns production authentication, resolver/issuer calls,
policy orchestration, and result disclosure.

Creation transaction:

1. a future trusted caller supplies an already validated controller binding;
   lock its registry row, inserting it only when that caller has separately
   authorized creation;
2. look up the exact
   `(controller_binding, player-character.create/v1, operation_id)` scope,
   returning its validated stored safe result on exact replay or rejecting a
   conflicting reuse before allocating;
3. obtain an injected ID from the future trusted issuer and insert its
   allocation row;
4. validate the complete Phase 1 initial record and canonical bytes;
5. insert initial revision/provenance history;
6. insert the FK-backed complete current record at initial revision;
7. insert the accepted successful creation receipt with its exact fingerprint
   and privacy-safe result envelope; and
8. commit once.

Mutation transaction:

1. lock and completely reconstruct the current character;
2. a future trusted caller authorizes its exact stored controller binding
   before receipt or character disclosure;
3. validate the complete typed operation and reject an unrepresentable revision
   successor;
4. look up the exact
   `(player_character_id, player-character.mutate/v1, operation_id)` scope and
   handle validated exact replay/conflict before expected-revision evaluation;
5. verify context/reference/expected revision for a new operation;
6. reuse one Phase 1 policy and validate the complete candidate;
7. insert its immutable revision/provenance history;
8. compare-and-swap the FK-backed current record;
9. insert the accepted successful mutation receipt
   with its exact fingerprint and privacy-safe result envelope;
10. apply no Run/story-line continuity effect in Phase 2; and
11. commit once.

Any failure rolls back. Repository methods never commit. The `UnitOfWork` port
exposes exactly the four repository surfaces listed above in MySQL and any
offline test double useful to Phase 2. Deterministic IDs and bindings may be
injected by Phase 2 tests, but that injection is not a production
identity-generation, controller-resolution, or binding-creation policy. Demo
parity is not automatic and remains outside Phase 2.

### Rollback and recovery

Migration upgrade must be additive and make no structured-character rows for
existing data. Downgrade may remove newly created empty schema only before
production use; once an ID is issued, downgrading in a way that permits reuse
conflicts with permanent non-reuse and is a stop condition. Operational schema
rollback after issuance therefore requires a forward-compatible recovery plan,
not an automatic destructive downgrade.

Application rollback begins from a fresh read of the last committed record and
the appropriately scoped successful receipt. A rejection has no first-slice
character receipt. No failure may leave an allocated ID without the atomic
initial record unless a reviewed recovery design explicitly treats the
permanent allocation as a failed-but-never-reusable reservation. The preferred
transaction prevents that state.

## 21. Compatibility and existing-data handling

The migration assumes no existing structured player-character data. It does
not assume there are no Sessions.

Existing `game_sessions`, snapshots, events, turn requests, jobs, and public
Session APIs continue under their current contract. No backfill may derive
`player_character_id`, controller binding, lifecycle, story line, applicable
reference, memory subject, or provenance from:

- `GameSession.player_id` or `PlayerState.player_id`;
- `RequestPrincipal.player_id`;
- Session ID, browser state, action/turn/job IDs;
- `character_definition_id`, display name, tags, or scenario;
- current memory facts, NPC keys, relationships, summaries, or events; or
- Provider output or narrative prose.

A later explicit structured participation workflow may bind a newly created
canonical character to a new Run/Session using trusted authority. Legacy
Sessions remain unbound and cannot invoke structured-character mutations. If a
schema column is later added to `game_sessions`, it must be nullable for legacy
rows and set only by trusted binding creation; absence means legacy/unbound,
not an invitation to infer identity.

Unsupported record versions fail read-only or require an approved migration.
An older writer encountering unknown canonical fields must not rewrite the
record. No compatibility path may remap IDs, clear bindings, silently default
preferences, reinterpret absence, or select an applicable-reference policy.

## 22. Security and privacy

The implementation must preserve `AUTH-001`, `AUTH-002`, `API-001`,
`STATE-001`, `MODEL-001`, and `MODEL-002`.

Required controls include:

- authenticate before resolving controller binding;
- authorize exact binding before returning existence or private state;
- never trust a submitted binding or authority class;
- use opaque bounded IDs as data, not paths, SQL fragments, or log templates;
- do not expose generation internals, authentication subjects, binding
  registry data, provenance, private declarations, hidden continuity facts,
  policy traces, capabilities, or Provider payloads;
- use parameterized SQLAlchemy queries and bounded strict DTOs;
- avoid logging complete canonical records or private structured fields;
- return fixed privacy-safe error codes/messages without distinguishing absent
  from unauthorized records;
- keep projection detached and allowlisted;
- reject identity/reference mismatch before disclosing authority-bearing
  fields; and
- keep live Provider calls and credentials outside normal verification.

ID opacity is not authorization. Revision and operation IDs are concurrency
data, not capabilities. Rate limits, enumeration protection beyond current
authority, audit retention, and production account security are not selected
by this plan and may block public rollout.

## 23. Failure and recovery behavior

| Failure | Required safe result |
| --- | --- |
| Missing/malformed identity or required group | Reject complete input; no allocation or mutation |
| Duplicate/colliding issued ID | Never attach it to a new character; retry only with a fresh server-issued ID inside reviewed bounds or fail |
| Unsupported contract/record version | Fail closed; no rewrite or revision advance |
| Unknown submitted/stored field | Reject write; older writer does not drop it |
| Stale expected revision | Conflict; current record/revision unchanged |
| Controller mismatch or unresolved binding | Privacy-safe missing/unauthorized result; no mutation or existence disclosure |
| Missing/altered stored binding | Integrity/authority failure; no repair from request, Session, Run, narration, or Provider |
| Invalid lifecycle/confirmation/authority | Reject; preserve all state and reference bindings |
| `deceased -> active` without approved adjudication | Deterministic unavailable-policy rejection |
| Character or applicable-reference mismatch | Reject without retarget, redirect, merge, advance, or rollback |
| Run/world/scenario/visit mismatch | Reject or require owning authority to refresh; never transfer or re-version |
| Duplicate exact successful creation operation | Authorize the controller-binding scope and return the stored original safe creation result; no second allocation |
| Duplicate exact successful mutation operation | Authorize the character's stored binding and return the stored original safe mutation result even after later revisions; no second mutation |
| Conflicting operation replay | Same exact scope key with any non-equivalent fingerprint, owner or target binding, or result schema conflicts; no allocation or mutation |
| Rejected operation repeated | Re-evaluate because the first slice stores no rejection receipt; no mutation or receipt is created by the rejection |
| Provider timeout/invalid/stale output | Preserve last committed canonical record and existing Provider recovery behavior |
| Persistence/CAS/commit failure | Roll back entire character operation; report no success |
| Response delivery failure after commit | Recover the original successful result through the exact scoped durable receipt; use a separate fresh authoritative projection only when the caller explicitly requests current state; do not reapply |
| Session/browser/transport loss | Canonical record, binding, lifecycle, identity, and applicable reference remain unchanged |
| Run reset | Canonical character remains unchanged; exact Run-side reset semantics remain deferred |
| Projection identity/staleness mismatch | Fail safely and require fresh authorized read |

Public errors must not include raw IDs supplied by another controller, binding
values, private fields, SQL/Provider exceptions, or policy evidence. Successful
operation recovery starts from the exact authorized receipt and its stored
safe result; new work starts from the last committed current record and owning
contextual state. Rejections have no first-slice character receipt.

## 24. Implementation phases

Phase 1 was separately authorized and has passed fresh independent read-only
acceptance for the exact nine-path candidate. Every later phase remains
proposed, incomplete, and unauthorized for implementation. A later phase may
begin only after its prerequisites, the gate in section 31, and a separate
scoped implementation task.

### Phase 1 — Domain envelope, identity types, and policies

Status: **Implemented and independently accepted for the exact
nine-path candidate, then committed and pushed at
`c8808f66e8d97bc4386a481bf21669cfddcd222e`. This acceptance does not authorize
Phase 2 or a public activation.**

Scope:

- add distinct player-character ID, revision, contract-version,
  controller-binding, applicable-reference, lifecycle, record-group,
  provenance, and subject-reference domain types;
- add complete-record validation;
- add explicit optional-declaration state types for every approved slot,
  adult-only age validation, and separate player-subjective versus external
  authority types;
- add pure character-operation namespace, fingerprint, equivalence, conflict,
  and stored-safe-result validation types matching section 15;
- add independent creation, retirement, reactivation, final-death, and
  unavailable-continuity-return policies; and
- add pure unit tests for all invariants and transitions.

Prerequisites: approval of exact optional structured field representations or a
reviewed bounded envelope that preserves absence without inventing defaults.

Exclusions: persistence, API, Provider, Session/Run binding, UI, full profile
mutation.

Completion criteria: pure domain/application tests prove strict validation,
every approved optional slot and declaration state, adult-only presentation,
no narration-preference default, player-sovereignty separation, identity
separation, binding preservation, transition matrix, full-candidate mutation,
applicable-reference preservation, deterministic unavailable death return,
and golden character-operation fingerprint/equivalence vectors.

Stop conditions: a field representation selects a deferred vocabulary/default;
omission, explicit absence, or intentionally undecided cannot remain distinct;
adult-only presentation cannot be proved; a subjective field can be populated
without player expression/confirmation; a story-line representation permits a
second or conflicting active character at the same time; receipt fingerprint
equivalence depends on an unresolved field meaning; or independent policies
require a missing product rule.

### Phase 2 — MySQL persistence and migration

Status: **Technical prerequisites drafted as an unaccepted review candidate;
not implemented and blocked pending fresh independent acceptance plus separate
explicit user authorization.**

Scope:

- once separately authorized, add only the six reviewed section 20 record
  families through SQLAlchemy models/mappings and one linear Alembic revision;
- extend repository and Unit of Work ports/implementations with the exact
  section 20 persistence capabilities;
- implement allocation, binding-registry storage, current record,
  revision/provenance, successful creation and mutation receipts, CAS, locking,
  reconstruction validation, concurrency translation, and rollback behavior;
- add real MySQL migration/repository integration tests and narrow offline test
  doubles where useful; and
- make only minimal truthful status-documentation updates required by that
  later authorized implementation.

Prerequisites: Phase 1 accepted; this exact two-path technical-prerequisite
candidate independently reviewed and accepted; permanent non-reuse and the six
section 20 physical schemas accepted as technical design; the complete section
15 receipt ownership, key, fingerprint, equivalence, result, transaction,
rejection, and bounded-retention semantics retained; and separate explicit
user authorization. The migration must directly revise actual head
`20260719_0003`.

Exclusions: trusted business/application orchestration; production
controller resolution; production controller-ID or player-character-ID
generation (including generation of a `ControllerBindingRef`); deciding when a
controller binding is created or invoked;
backfill; deletion; archive/restore; public routes or response projections;
frontend flows; Run/story-line binding or activation; Provider/model
integration; Demo activation; production/network composition; and every Phase
3 or later behavior.

Completion criteria: migration reaches one head; empty upgrade changes no
legacy records; allocation/non-reuse, constraints, exact creation/mutation
receipt scopes, stored-result replay after later revisions, conflict handling,
absence/undecided and deterministic canonical-byte round trips, fixed
65-feature persistence, aggregate 65,536-byte declaration boundary,
case-sensitive maximum-length opaque references, malformed reconstruction and
stored-result rejection before disclosure, CAS, concurrent writers,
binding-insert conflict, state-plus-receipt atomicity, failure rollback,
signed-64-bit maximum/overflow prevention, restrictive foreign keys, durable
reload across a new session/process to the extent the persistence layer owns
it, and no-cascade behavior pass real MySQL tests.

Stop conditions: downgrade can release issued IDs; MySQL constraints require
inventing product semantics; a receipt schema would be created before its
section 15 semantics and Phase 1 fingerprint vectors are accepted; multiple
transaction owners prevent atomicity; or legacy data would need inferred
identity.

### Phase 3 — Trusted canonical application service

Scope:

- add controller-binding resolver and canonical character repositories to the
  application boundary;
- implement create, owned read, typed lifecycle commands, exact replay,
  privacy-safe errors, and detached internal/self projection;
- use a trusted test resolver; and
- add application and persistence-backed service tests.

Prerequisites: Phases 1–2 accepted; controller-binding adapter scope reviewed;
the exact section 15 operation protocol present in the accepted Phase 2 schema.

Exclusions: production account system, public production endpoint, Run
integration, death-event adapter without an owning source, Provider changes.

Completion criteria: canonical create/read and every admitted policy are
testable through trusted application ports; inaccessible authorities reject
deterministically; exact successful creation and mutation replays return their
stored safe original results; rejections create no character receipt; no path
accepts submitted canonical authority.

Stop conditions: normal composition would rely on the development principal as
production authority; confirmation becomes a reusable capability; or final
death requires unapproved Run/world rules.

### Phase 4 — Run and continuous-story-line binding

Scope:

- connect the character-side typed binding to the separately implemented
  Run-owned aggregate;
- enforce that each continuous story line has exactly one active
  player-character binding and reject a second or conflicting binding;
- add a separately reviewed Run/line persistence migration only if the real
  owner requires one, following the then-current Alembic head;
- validate and preserve exact character ID and applicable reference across
  scenario and authorized later-world changes;
- bind Session participation only through trusted Run orchestration; and
- add integration tests for boundaries and mismatch rejection.

Prerequisites: approved Run aggregate, continuous-line reference, world/visit
identity, transition authority, and compatible transaction ownership.

Exclusions: implementing Phase 3.3 itself, arbitrary movement, reset semantics,
reference-following policy, cross-Run concurrency.

Completion criteria: same-line scenario and authorized later-world transitions
preserve exact ID/reference; attempts, including concurrent attempts, to give
one story line a second or different active character fail atomically; every
boundary-driven switch fails atomically; Run retains all of its current
authority.

Stop conditions: the prerequisite Run surfaces do not exist; `GameSession`
would need to masquerade as Run; cross-aggregate atomicity is unresolved;
line-owner serialization and a persistence backstop cannot enforce the frozen
one-active-character-per-story-line invariant; a reference change is
requested; or implementation would have to select inverse cardinality,
restart/resume, successor/replacement, or post-return binding behavior.

### Phase 5 — Public projection and narrow boundary integration

Scope:

- expose the minimum reviewed detached self projection and typed intents only
  where an authoritative controller resolver is composed;
- preserve current Session request recovery and error envelopes; and
- add public contract/API tests without a character-profile UI.

Prerequisites: Phase 3 accepted; Phase 4 if public operation requires Run
binding; public allowlist and authentication scope independently reviewed.

Exclusions: profile UI, general patch endpoint, Provider protocol, frontend
redesign, production rollout.

Completion criteria: public allowlist/privacy, non-enumeration, stale/replay,
identity/reference mismatch, detachment, Session/browser recovery separation,
and no client mutation authority are tested.

Stop conditions: no non-development controller authority; existing
`PlayerVisibleStateProjection.player_id` would change meaning; safe recovery
requires redesign of the current client contract; or private fields become
necessary.

### Phase 6 — Subject-reference compatibility hooks

Scope:

- require explicit player-character subject references at any new
  memory/relationship/consequence boundary touched by the structured slice;
- preserve runtime/logical NPC separation; and
- add compatibility tests without replacing current memory storage.

Prerequisites: explicit Run/Session participation and owning adjacent-system
contracts.

Exclusions: full relationship, consequence, memory, golden-memory, and
cross-scenario NPC systems.

Completion criteria: every new authoritative adjacent fact is bound to correct
logical subjects; transitions do not transfer/erase it; current
`PlayerMemoryState` invariants remain intact.

Stop conditions: a cross-scenario logical NPC ID, golden-memory schema,
consequence transfer rule, or current-memory backfill would have to be invented.

### Phase 7 — Regression, documentation, and closeout

Scope:

- run focused, Offline, Full, and MySQL verification appropriate to all
  implemented surfaces;
- run Alembic checks and inspect migration/state documentation;
- complete the canonical documentation-synchronization checklist;
- update owning architecture/public/memory/roadmap documents truthfully; and
- obtain independent audit before any completion or commit request.

Prerequisites: all in-scope implementation phases accepted and present.

Exclusions: production deployment, staging, push, or claims for deferred
systems.

Completion criteria: all evidence is recorded, status matches the code, every
mutation has regression coverage, guardrail impact is assessed, and no deferred
product decision was selected.

Stop conditions: verification failure, documentation drift, unexpected changed
paths, migration mismatch, live Provider dependency, or missing independent
audit.

## 25. Proposed file-level change inventory

This inventory is proposed implementation scope only. It authorizes no edit.
Exact placement should be confirmed at each phase.

### Proposed additions

| Proposed path | Layer and purpose | Obligation | Protecting tests |
| --- | --- | --- | --- |
| `src/deviation_protocol/domain/player_character.py` | Domain aggregate, distinct value objects, strict field groups, lifecycle, reference, provenance | Complete canonical record, identity separation, versions, lifecycle | New domain unit tests |
| `src/deviation_protocol/domain/player_character_policies.py` | Independent pure policies for creation and each lifecycle route | Guardrail policy separation; transition/authority matrix | Policy matrix unit tests |
| `src/deviation_protocol/application/player_character_service.py` | Trusted orchestration for create/read/mutate/project | Controller resolution, complete validation, atomic/replay boundary | Application unit and MySQL service tests |
| `src/deviation_protocol/application/player_character_operations.py` | Server-owned operation namespaces, canonical fingerprints, replay equivalence, and strict safe-result envelopes | Independently reviewable successful-receipt protocol before persistence | Golden-vector and replay/conflict unit tests |
| `src/deviation_protocol/application/player_character_projection.py` | Detached allowlisted self projection | Privacy and non-authoritative public data | Projection/privacy unit and contract tests |
| `src/deviation_protocol/application/player_character_identity.py` or the existing identity module, Phase 3 only | Ports/value adapters for production controller resolution and ID issuance | Domain separation and trusted issuer/resolver | Identity-boundary unit tests |
| one Phase 2 Alembic revision whose parent is actual head `20260719_0003` | Add exactly the six section 20 tables only after this amendment is independently accepted and Phase 2 separately authorized | Exact columns/types/collations, uniqueness, non-reuse, binding, revision, provenance, and distinct successful creation/mutation receipts | Migration-head/schema/upgrade tests |
| future Phase 4 Alembic revision, only if required by the real Run/line owner | Add the approved binding schema after the then-current head without inventing a path now | One active player-character binding per story line at a time; exact character/reference preservation | Run binding migration/concurrency tests |
| `tests/unit/test_player_character.py` | Domain record and validation matrix | Strict complete record | Unit matrix |
| `tests/unit/test_player_character_policies.py` | Lifecycle/confirmation/authority matrix | Every state mutation | Unit matrix |
| `tests/unit/test_player_character_operations.py` | Canonical fingerprint vectors, exact replay equivalence, conflicts, and safe-result validation | Receipt protocol before schema | Application boundary tests |
| `tests/unit/test_player_character_service.py` | Service, replay, privacy, rollback with fakes | Trusted boundary | Application tests |
| `tests/integration/test_mysql_player_character.py` | Real MySQL repositories, transactions, CAS, constraints | Persistence/atomicity | Integration tests |

The exact split among the proposed application/domain files is `T`.
Repository convention supports domain, application, infrastructure, and test
separation, but avoiding circular dependencies and keeping policy classes
independent is more important than these filenames.

### Proposed modifications

| Existing path | Purpose | Obligation | Protecting tests |
| --- | --- | --- | --- |
| `src/deviation_protocol/application/ports.py` | Add canonical repository, separate successful creation/mutation receipt, issuer/resolver, and UoW ports | Domain-directed dependencies and exact receipt ownership | Port/service type and fake tests |
| `src/deviation_protocol/infrastructure/orm_models.py` | Add private normalized persistence models | MySQL canonical ownership/constraints | Schema and repository tests |
| `src/deviation_protocol/infrastructure/repositories.py` | Add lock/read/allocation/CAS/history and exact-scoped successful-receipt operations without commits | Atomic canonical mutations and replay | MySQL repository tests |
| `src/deviation_protocol/infrastructure/unit_of_work.py` | Expose new repositories in one `AsyncSession` transaction | Commit/rollback ownership | UoW rollback tests |
| `tests/unit/test_repository_and_uow.py` | Cover new repository/UoW wiring and failure restoration | Existing persistence convention | Focused unit tests |
| `tests/integration/test_mysql_connection.py` | Advance expected Alembic head and assert exact new schema | Migration verification | Real MySQL schema test |
| `src/deviation_protocol/api/schemas.py`, `src/deviation_protocol/api/main.py`, `src/deviation_protocol/api/dependencies.py`, and `src/deviation_protocol/api/errors.py` | Phase 5 only: narrow typed public boundary, resolver composition, safe errors | Public allowlist/authority | API unit/integration contract tests |
| `tests/unit/test_session_service.py` and relevant API integration tests | Prove existing Session identity/projection is unchanged | Compatibility | Regression tests |
| future Run-owned module/directory, not nameable today | Phase 4 only: bind exact ID/reference in the real Run aggregate and reject second/conflicting active character bindings on one line | Same-line/later-world continuity and frozen line cardinality | Run service/integration/contract tests |
| future adjacent-system owning modules, not nameable today | Phase 6 only: accept explicit logical subject refs | Memory/NPC/consequence correctness | Compatibility/integration tests |

No Run-owned source path can be named reliably because no Run implementation
exists. Inventing one here would prejudge Phase 3.3 architecture.

### Deliberately untouched unless a later phase proves a narrow need

| Path/surface | Reason |
| --- | --- |
| `src/deviation_protocol/application/narrative_models.py` (owner of `NarrativeProvider`), `src/deviation_protocol/application/narrative_validation.py`, `src/deviation_protocol/application/narrative_turn_orchestrator.py`, and Provider adapters | Candidate-only boundary already fits; no character mutation field is needed |
| `src/deviation_protocol/domain/player_memory.py` and `src/deviation_protocol/application/player_memory.py` | Current bounded memory authority remains intact; full integration deferred |
| scenario content, static character definitions, and `config` | Templates/content must not become canonical identity |
| `web` | No creation UI or frontend redesign in the first slice |
| existing frozen product specifications | Implementation may not change approved product rules |
| Phase 3.2 Demo launcher/smoke/provider | Phase 3.2b remains closed; Demo parity needs separate explicit scope |

During an authorized implementation closeout, documentation likely requiring
truthful synchronization includes `PLANS.md`, `docs/architecture.md`, this
plan, and any owning public-client/memory/Run authority actually changed.
`docs/engineering/guardrails.md` changes only if a confirmed defect creates or
changes a reusable rule.

## 26. Test and verification matrix

### Required behavior matrix

| Case | Primary level | Required assertion |
| --- | --- | --- |
| Canonical creation | Domain + persistence/integration | Complete v1 record, active lifecycle, binding, initial revision, provenance commit atomically |
| Every supported optional declaration slot | Domain unit | Parameterized coverage for name/code name, preferred address, adult identity/gender expression, broad adult age presentation, broad appearance direction, bounded distinguishing features, outward presentation, inward tendency, reality anchor, custom values, and internal-thought narration preference; no unapproved field is accepted |
| More than 64 distinguishing features within the declaration envelope | Domain + application unit | A fixed 65-feature declaration remains below 65,536 canonical UTF-8 bytes and passes direct declaration, complete-record, creation-command, fingerprint, receipt-protocol, and creation-policy validation without a replacement item-count ceiling |
| Omitted versus explicitly absent | Domain unit + persistence/integration | Every supported optional slot preserves unset/omitted separately from an explicitly absent declaration through validation, snapshot/row serialization, and reload |
| Explicitly absent versus intentionally undecided | Domain unit + persistence/integration | The two states remain unequal and round-trip without defaulting or reinterpretation wherever intentionally undecided is permitted |
| Adult-only age presentation | Domain unit + application/service | Every admitted age representation proves adult presentation; every non-adult or unprovable representation rejects before allocation or mutation |
| No narration-preference default | Domain unit + persistence/integration | Omitted/absent preference remains without a selected value; `balanced` is never silently written |
| Intentionally undecided narration preference | Domain unit + persistence/integration | An explicit undecided selection state survives commit/reload without becoming omitted, absent, `balanced`, or another selected preference |
| Player-confirmed subjective state | Domain unit + application/service | A bounded subjective declaration or admitted development entry can become canonical only from exact player expression/confirmation bound to character and revision |
| Server inference of subjective state | Domain unit + application/service | Server observations or behavior-derived inference cannot populate player-controlled thought, feeling, motive, belief, value, intention, or commitment |
| Provider/narration inference of subjective state | Application/service + contract | Provider candidates and narration have no canonical subjective-state command or authority path; a real public/narrative boundary receives end-to-end coverage only if Phase 5 actually adds one |
| NPC/summary/event/consequence authority over inner state | Application/service + compatibility/integration | NPC output, summaries, events, memories, and external consequences cannot settle player-controlled inner state without exact player expression/confirmation |
| Player declaration over external facts | Domain unit + application/service + contract | A player declaration may record the character's stated inner state but cannot establish NPC response, world fact, relationship outcome, or external consequence |
| Unique ID allocation | Persistence/integration | Distinct creates get distinct server IDs |
| Duplicate/collision ID | Persistence/integration | Existing allocation cannot attach to a new record; no partial row |
| Permanent non-reuse | Migration + persistence | Retired/deceased/known absent identity is never allocatable; no delete path |
| Missing/malformed ID | Domain + API contract | Strict reject; no enumeration or mutation |
| Required controller binding | Domain + persistence | Missing/null binding cannot create or load as valid |
| Altered binding | Domain + service/integration | Mutation rejects; no revision/state change |
| `active -> retired` | Policy + service | Explicit bound confirmation; exact preservation/end-line effect |
| `retired -> active` | Policy + service | Explicit confirmation plus authorized binding evidence |
| `active/retired -> deceased` | Policy + service | Trusted event authority only; final death provenance |
| Forbidden transitions | Policy unit | Every unlisted edge rejects |
| Deceased ordinary reactivation | Policy + API contract | Deterministic rejection |
| Deceased authorized return unavailable | Policy + service | No approved adjudication adapter, no mutation |
| Missing/ambiguous confirmation | Policy + contract | Reject retirement/reactivation |
| Authority mismatch | Service + API contract | Privacy-safe reject before authority fields |
| Stale revision | Persistence/integration | CAS loser does not advance or append accepted history |
| Unsupported version | Domain + persistence | Safe read/write failure; no rewrite |
| Unknown fields | Domain + contract | Submitted unknown rejected; older writer cannot drop stored unknown |
| Malformed structured input | Domain + API contract | Whole command rejected, no salvage |
| Provider-only mutation attempt | Application/service + contract | Proposal cannot reach character command/policy |
| Narration-only mutation attempt | Application/service + contract | Text establishes no identity/lifecycle/reference or subjective canonical fact; end-to-end coverage is added only when a real integrated boundary exists |
| Controller mismatch | Service + API integration | Same safe missing/unauthorized result, no disclosure |
| Character identity mismatch | Service + integration | No retarget/merge/redirect |
| Run/world/scenario/visit mismatch | Run integration | Owning context rejects atomically |
| Applicable-reference mismatch | Domain + Run integration | No use or mutation |
| Second active character on one story line | Run application/service + persistence/integration | An existing line binding rejects a second or different active `player_character_id` with neither aggregate changed |
| Concurrent conflicting line bindings | Run persistence/integration | Competing transactions for one story line produce exactly one committed active character binding; the loser rejects and no split binding state remains |
| Scenario continuity | Run integration/end-to-end | Exact ID and reference preserved |
| Later-world continuity | Run integration/end-to-end | Run selects world; exact ID/reference preserved |
| Unauthorized reference advance | Domain + Run integration | Rejected before boundary mutation |
| Unauthorized reference rollback/substitution | Domain + Run integration | Rejected even with same character ID |
| Creation receipt scope before ID | Application unit + persistence/integration | Receipt key is exact controller binding + `player-character.create/v1` + operation ID; replay occurs before allocation and returns the originally stored safe result |
| Mutation receipt scope | Application unit + persistence/integration | Receipt key is exact character ID + `player-character.mutate/v1` + operation ID; current controller binding is authorized before disclosure |
| Fingerprint canonicalization | Application unit golden vectors | Exact namespace/command/contract/declaration or target/revision/body/evidence fields use stable UTF-8 canonical JSON while preserving omission, absence, undecided, ordered data, and meaningful text |
| Duplicate exact creation operation | Service + persistence | Original safe result returned; one identity allocation/current record/history/receipt |
| Duplicate exact mutation operation after later revisions | Service + persistence | Original stored safe result returned without reconstructing from current state; no second revision/history entry |
| Conflicting replay | Service + persistence | Same exact scope key with different fingerprint, command, target/result binding, or result-schema version conflicts; no allocation or mutation |
| Rejected operation receipt absence | Service + persistence | Rejections create no first-slice character receipt and may be re-evaluated without ever duplicating a successful effect |
| Current Session replay separation | Application/contract + persistence | Character operations neither reuse nor mutate `turn_requests`; Session action/request status authority remains unchanged |
| Provider failure | Application regression | Last canonical record/revision unchanged |
| Canonical commit failure | UoW + MySQL | Complete rollback and no success response |
| No revision after rejection | Policy/service/persistence | All negative cases preserve revision |
| No partial mutation | UoW + MySQL | Record/binding/history/continuity/successful receipt/safe result remain mutually consistent |
| Privacy-safe public errors | API contract/integration | No existence/private/authority leak |
| Detached allowlisted projection | Unit + API contract | Immutable copy; private fields absent; mutation of response cannot affect state |
| Session loss/browser reset | API/end-to-end boundary | Canonical identity/binding/lifecycle/reference unchanged |
| Run reset | Run contract | Canonical record unchanged; no invented restart behavior |
| Transport delivery failure/recovery | Service/integration | Exact scoped receipt returns the original committed safe result without reapply; current state is fetched only through a separate authorized read |
| Logical/runtime NPC distinction | Domain compatibility | Runtime ID cannot satisfy logical subject type |
| Memory subject correctness | Compatibility/integration | Exact player-character subject, current memory rules preserved |
| Relationship/consequence subject correctness | Compatibility/integration | No transfer by controller/name/template |
| Golden-memory protection | Boundary/contract | Current memory/summary/Provider data cannot masquerade as protected golden memory |
| Migration parent and head | Migration/integration | Baseline chain is exactly `20260719_0001 -> 20260719_0002 -> 20260719_0003`; the proposed revision directly revises `20260719_0003` and produces one head |
| Migration empty upgrade | Migration/integration | New schema only; no inferred structured records |
| Exact Phase 2 schema | Migration/integration | All six and only the six section 20 tables have the candidate's exact columns, types, nullability, keys, indexes, checks, `ascii_bin` identity columns, restrictive FKs, and timestamp behavior; the inspected exact index inventory includes `ix_spc_revisions_controller_binding (controller_binding)` and `ix_spc_mutation_receipts_result_revision (result_player_character_id, resulting_revision)`, with the latter satisfying both mutation-receipt result-side child FKs; no undeclared MySQL-generated child-side index exists |
| Every Phase 2 record family round trip | Persistence/integration | Binding, allocation, current, history, creation receipt, and mutation receipt survive commit and strict reload without byte or meaning changes |
| Case-sensitive maximum opaque identities | Persistence/integration | Distinct case variants coexist; every applicable 128-character value round-trips exactly; 129-character, malformed, trimmed, folded, normalized, or reinterpreted input rejects |
| Aggregate declaration byte boundary | Domain + persistence/integration | Exact canonical UTF-8 declaration envelopes at 65,536 bytes commit/reload; 65,537 bytes reject before any insert despite MySQL character counts |
| Fixed 65-feature persistence | Persistence/integration | The accepted fixed 65-feature declaration commits and reloads with order, content, authority, and count unchanged and no item-count ceiling |
| Malformed current/history record | Persistence/integration | Invalid JSON/canonical bytes, cross-column mismatch, unknown field, invalid declaration envelope, or impossible provenance fails closed before any domain object or private data is returned |
| Malformed receipt/stored result | Persistence/integration | Invalid canonical receipt, key/fingerprint/result mismatch, impossible semantic result, or oversize blob is an integrity failure before stored-success disclosure |
| Deterministic fingerprint storage | Application + persistence/integration | `BINARY(32)` round-trips to the exact Phase 1 lowercase digest and produces exact replay only for the canonical matching command |
| Atomic initial state plus receipt | UoW + MySQL | Binding/allocation/revision/current/creation receipt all commit once or all roll back |
| Atomic successor state plus receipt | UoW + MySQL | New history/current CAS/mutation receipt all commit once or all roll back |
| Controller-binding insertion conflict | Persistence/integration | Concurrent insertion of one exact binding has at most one winner; loser rolls back and no binding mutation/rebinding policy appears |
| Concurrent character writers | Persistence/integration | Locked/CAS writers against one expected revision yield one committed successor/receipt and clean loser rollback |
| Signed-64-bit revision maximum | Domain + persistence/integration | Revision 9223372036854775807 reloads; 9223372036854775806 may commit its final successor; no update/receipt can require or store 9223372036854775808 |
| Restrictive foreign keys | Migration + persistence/integration | Parent update/delete and Session cleanup cannot cascade, null, migrate, or erase character allocation, binding, current, history, provenance, or receipts |
| Durable persistence reload | Persistence/integration | A newly opened `AsyncSession`, and a process restart only where the Phase 2 fixture supports it, reconstructs the same complete records and receipts without Provider, API, frontend, or Run composition |
| Legacy Session compatibility | API/integration/end-to-end | Existing Sessions remain valid and unbound |
| Migration failure/rollback | Migration/integration | Original schema/data unchanged where supported; no issued-ID release |

Every state mutation receives a regression test. Phase-specific tests should
follow current repository conventions: pure policies and validation in unit
tests; SQL constraints, concurrency, transactions, and migrations against real
MySQL; public request/projection behavior in API contract/integration tests;
and only cross-boundary continuity/recovery cases in end-to-end tests.
Phase 2 tests may inject deterministic player-character IDs and controller
bindings. They must not require or establish production issuance/resolution
policy and require no Provider, model, public API, frontend, production
resource, or network-service test.

### Intended later implementation commands

These commands are listed for later authorized implementation tasks and are not
run by this documentation-only planning task:

```powershell
.\.venv\Scripts\python.exe -m pytest <focused test paths>
.\.venv\Scripts\python.exe -m compileall -q src tests alembic
.\scripts\verify.ps1 -Mode Offline
.\scripts\verify.ps1 -Mode Full
.\scripts\verify.ps1 -Mode MySQL
.\.venv\Scripts\python.exe -m alembic heads
.\.venv\Scripts\python.exe -m alembic history
git diff --check
```

Offline verification must use the canonical Offline mode and keep
`RUN_LIVE_DEEPSEEK_TEST` disabled. MySQL verification must use the approved
test database only. Web commands are required only if an authorized later task
actually changes Web files; this plan excludes those changes.

## 27. Documentation synchronization

Before an independent audit, phase-completion claim, or commit-authorization
request, the implementing task must complete the canonical checklist in
[Codex Workflow](engineering/codex_workflow.md#canonical-documentation-synchronization-checklist).
At minimum it must:

- map implemented behavior to the approved product contract without changing
  that contract's rules;
- update [Architecture](architecture.md) for actual aggregate, transaction,
  persistence, identity, and composition boundaries;
- update [Public Client Contract](public_client_contract.md) only if a public
  route/projection is actually added;
- update [Player Memory](player_memory.md), [Run Protocol](run_protocol.md), or
  [NPC Relationship and Temporary Residence](npc_relationship_residence.md)
  only where their owning implemented scope truly changes;
- update `PLANS.md` and this plan with evidence-based status, never marking
  deferred phases implemented;
- review the matching Alembic migration whenever models change;
- add a regression test for every confirmed defect and mutation;
- update engineering guardrails only when a confirmed defect creates or
  changes a reusable rule; and
- record verification, independent audit, changed paths, and Git handoff
  truthfully.

Documentation sync cannot approve a product policy, close a phase without
evidence, or make the frozen product contract appear implemented ahead of
runtime behavior.

## 28. Risks and stop conditions

| Risk | Mitigation / stop condition |
| --- | --- |
| Current `player_id` is mistaken for canonical character ID | Distinct types, resolver boundary, negative type/integration tests; stop any mapping/backfill |
| Development principal is treated as production controller authority | Keep public composition blocked until trusted authority exists |
| `GameSession` is promoted to Run | Stop Phase 4 until a real Run aggregate exists |
| Applicable reference silently follows current revision | No mutation route; exact-match preservation; stop for any change request |
| Identifier becomes reusable after deletion/downgrade | Append-only allocation/no delete; stop destructive downgrade after issuance |
| JSON groups permit unbounded or unknown canonical fields | Strict bounded domain schema; stop where exact representation requires product choice |
| Optional declaration states collapse or preference defaults silently | Closed state wrapper, exhaustive unit/persistence tests, and a Phase 1 stop if omission, explicit absence, intentionally undecided, or selected preference cannot remain distinct |
| External or inferred material settles player-controlled inner state | Separate authority types and negative domain/service/contract tests; stop any server, Provider, narration, NPC, summary, event, memory, or consequence inference path |
| Player declaration is accepted as an external fact | Subjective declaration types cannot satisfy world/NPC/consequence authority; reject before canonical commit |
| Story-line integration permits two active characters on one line | Enforce the frozen one-active-character-per-story-line invariant in the owning service transaction and persistence backstop; stop if the real Run/line schema cannot enforce it |
| Inverse line cardinality or post-ending behavior is inferred | Preserve only the frozen line-to-character direction and approved lifecycle effects; stop rather than select how many lines one character occupies, restart/resume, successor/replacement, or return behavior |
| Controller-binding registry implies transfer/recovery behavior | No binding mutation API; classify new behavior as product decision |
| Character transaction is split across aggregate owners | Shared MySQL transaction or stop for approved consistency design |
| Receipt schema precedes exact first-slice semantics | Phase 2 is gated on section 15 review and Phase 1 golden vectors; use distinct creation/mutation scopes and accepted-result receipts only |
| Existing idempotency rows are reused outside Session scope | Keep character receipts separate from Session `turn_requests` and their lifecycle |
| Public projection leaks controller/provenance/private facts | Minimal allowlist, detached DTO, privacy/non-enumeration tests |
| Provider candidate acquires mutation authority | No candidate fields/path; preserve MODEL invariants |
| Current memory key is claimed cross-scenario | Keep narrow authority and stop for logical-NPC design |
| Legacy Sessions are backfilled heuristically | Leave explicitly unbound; no inference |
| A migration assumes SQLite or live services | MySQL/AsyncSession only; Offline/MySQL verification |
| Plan phase is treated as implementation authorization | Approval gate below; every phase needs separate scoped authority |

Any material conflict between this plan and an approved authority, need to
select a deferred product policy, need to edit an excluded surface, or failure
of required verification is a stop condition.

## 29. Deferred decisions

The following remain unresolved and this plan deliberately does not select
them:

- production player-character ID issuance algorithm and entropy source; the
  accepted Phase 1 opaque syntax/128-character bound and this candidate's
  `ascii_bin` storage representation remain fixed for review;
- any post-first-slice history compaction or physical-schema evolution; the
  exact six-table Phase 2 candidate in section 20 selects neither;
- exact structured field lengths, vocabularies, localization, custom-value
  representation, and profile/activation requiredness;
- defaulting and update workflows for narration preferences;
- character/profile creation drafts and UI;
- account/controller character limits and concurrent active-character rules;
- controller transfer, shared control, delegation, recovery, unbinding, and
  account-change behavior;
- exact continuous-story-line identity and the inverse number of simultaneous
  active story lines or Runs one character may occupy;
- restart/resume, successor/replacement, post-retirement/death/return binding,
  cross-Run concurrency, and arbitrary movement between unrelated Runs/story
  lines/accounts;
- pinned, floating, checkpointed, migrating, automatically following, or any
  other applicable-reference/revision-following behavior;
- when or how an applicable reference may be changed by future approved
  authority;
- resurrection, rebirth, reincarnation, time reversal, equivalent continuity,
  and consequence reversal/inheritance;
- deletion, archival, restoration, cloning, merging, and recovery;
- post-first-slice receipt cleanup/deletion/archival, rejected-operation
  receipt behavior, and permanent retention/audit policy;
- full relationship, consequence, memory, protected golden-memory, and
  cross-scenario logical NPC schemas;
- production controller/account composition, enumeration controls, quotas, and
  rollout; and
- exact public endpoint and profile projection beyond the minimal allowlist.

None of these deferrals authorizes a boundary-driven default. In particular,
the absence of a general reference policy does not authorize pinned, floating,
checkpointed, migrating, revision-following, automatic, scenario-driven, or
later-world-driven switching.

## 30. Acceptance criteria

The completed independent read-only review confirmed that this implementation
plan:

1. remains downstream from, and does not weaken or expand, the frozen product
   contract;
2. maps current repository surfaces accurately and does not claim related
   infrastructure already implements the contract;
3. keeps controller, existing player, player character, template, Run, story
   line, world, scenario, visit, Session, browser, request, Provider, NPC, and
   display identities distinct;
4. provides a credible permanent non-reuse mechanism with no hard-delete path;
5. requires and preserves controller binding in every lifecycle state;
6. supports only admitted lifecycle policies and rejects unapproved return from
   death;
7. distinguishes contract version, record revision, applicable reference, and
   all existing narrower versions;
8. preserves exact player-character ID and applicable reference across
   same-story-line scenario and Run-authorized later-world boundaries;
9. preserves the frozen rule that each continuous story line has
   exactly one active player-character binding, rejects second/conflicting
   bindings atomically, and does not select inverse cardinality or replacement
   behavior;
10. selects no general applicable-reference policy;
11. uses complete strict validation, expected revision, exact authority/context
    matching, and one atomic commit;
12. defines distinct creation and mutation receipt ownership/key scopes,
    canonical fingerprints, exact replay/conflict and stored-original-result
    behavior, accepted-operation-only persistence, transaction ordering, and
    the bounded no-cleanup first-slice assumption before Phase 2 schema work;
13. preserves every approved optional declaration state, enforces adult-only
    age presentation, selects no narration-preference default, and preserves
    player sovereignty against server, Provider, narration, NPC, summary,
    event, consequence, and external-fact authority confusion;
14. preserves Provider-candidate and public-client authority boundaries;
15. defines a detached minimal public allowlist without a profile UI;
16. supplies subject-reference hooks without redesigning memory, relationships,
    consequences, logical NPCs, or golden memory;
17. proposes MySQL/AsyncSession/Alembic persistence after the actual current
    head `20260719_0003` without backfilling canonical identity from legacy
    data;
18. contains an actionable phase, file, test, verification, risk, stop, and
    documentation plan;
19. classifies product decisions, technical choices, deferrals, and exclusions
    truthfully; and
20. was unimplemented, unstaged, uncommitted, and unpushed when the plan was
    approved and frozen.

Runtime acceptance for later implementation is phase-specific and cannot be
earned by approval of this document alone.

## 31. Approval and implementation gate

The plan-level independent-review and correction gate is closed. The separately
authorized Phase 1 implementation passed fresh independent read-only
acceptance for the exact nine-path candidate after the third correction round.

Phase 2 remains blocked pending fresh independent read-only acceptance of the
exact section 20 technical-prerequisite amendment and separate explicit user
authorization. The amendment is a review candidate, not an approved or frozen
change. Phase 1 acceptance does not authorize persistence, public activation,
or any Phase 2 work.

No phase is approved, frozen, started, or completed by being listed here.
Approval of the frozen product contract is not implementation authorization.
Approval and freeze of this plan do not authorize staging, committing, pushing,
deployment, or work outside a separately authorized phase.

## 32. Review history

- 2026-07-24: Initial downstream implementation-plan draft prepared from the
  approved and frozen structured player-character contract and current
  repository evidence. This was a controlled documentation-planning task, not
  an independent review, approval, freeze, implementation, staging, commit, or
  push.
- 2026-07-24: A fresh independent read-only review of the initial draft
  identified `SPCIP-001` (HIGH), `SPCIP-002` (MEDIUM), `SPCIP-003` (MEDIUM),
  `SPCIP-004` (MEDIUM), and `SPCIP-005` (LOW). Its report was historical
  guidance; each finding was re-verified against repository authority and
  current source before correction.
- 2026-07-24: This controlled documentation-only correction addressed all five
  accepted findings. It was not an independent review, approval, freeze,
  implementation, closeout, staging, commit, or push, and it made no new
  product decision.

- 2026-07-24: The second fresh independent read-only review of the complete
  corrected plan and complete current `PLANS.md` diff returned
  `APPROVED_STRUCTURED_PLAYER_CHARACTER_IMPLEMENTATION_PLAN_CORRECTED_DRAFT`.
  This controlled documentation-only closeout recorded the plan as approved,
  frozen, and unimplemented; it closed the plan-level independent-review gate,
  selected no deferred product decision, and did not begin implementation,
  stage, commit, or push.
- 2026-07-24: A separately authorized controlled task implemented only Phase 1
  locally: the pure canonical record envelope and identity types, independent
  lifecycle policies, distinct successful creation/mutation receipt
  namespaces and keys, deterministic canonical JSON/SHA-256 protocol,
  privacy-safe result envelopes, authorization/replay/conflict decisions,
  later-persistence ordering/atomicity requirements, bounded retention
  boundary, and fixed offline golden vectors. Phase 1 remains unaccepted and
  unclosed pending a fresh independent read-only review. Phase 2 and every
  later phase remain blocked and unimplemented. No migration, database receipt
  schema/repository, production service/transaction wiring, public route,
  Provider integration, frontend flow, Demo change, Run/story-line activation,
  staging, commit, or push occurred.
- 2026-07-24: A narrowly scoped correction locally addressed the fresh
  independent review's applicable-reference fingerprint, complete-record
  provenance/lifecycle/authority validation, and declaration-envelope findings.
  It refreshed the affected fixed mutation vectors and reran offline
  verification. Phase 1 remains unaccepted pending a new independent read-only
  review; Phase 2 and later phases remain blocked. No persistence, migration,
  public route, Provider, Run activation, or frontend behavior was added.
- 2026-07-27: A second narrowly scoped correction locally addressed all four
  blocking scenarios from the next independent review: bypass-corrupted
  applicable references, forged success replay for unavailable operations,
  bypass-corrupted nested/current records at public Phase 1 boundaries, and
  declaration-envelope limit ownership at the exact 65,536-byte boundary.
  Focused Phase 1 tests, the affected Session/orchestrator selection,
  `compileall`, the complete isolated Offline verifier, and `git diff --check`
  were rerun successfully.
  Phase 1 remains unaccepted and unclosed pending a fresh independent read-only
  acceptance review. The complete plan remains partially implemented; Phase 2
  and later phases remain blocked. No persistence, migration, public route,
  Provider, Run/story-line activation, frontend behavior, staging, commit, or
  push was added or performed.
- 2026-07-27: This third narrow correction locally addressed the next
  independent review's three blocking findings: lossy dump/reconstruction of
  bypass-injected unknown Pydantic state, revision-successor overflow beyond
  the canonical signed 64-bit domain, and missing fixed regression proof for a
  valid 65-feature creation. Focused and repository Offline verification were
  rerun. At that point Phase 1 remained unaccepted pending a fresh independent
  read-only acceptance review; the complete plan remained partially
  implemented, and Phase 2 and later phases remained blocked. No persistence,
  migration, public route, Provider, Run/story-line activation, frontend
  behavior, staging, commit, or push was added or performed.
- 2026-07-27: A fresh independent read-only review returned
  `APPROVED_STRUCTURED_PLAYER_CHARACTER_PHASE_1` for the exact nine-path Phase
  1 candidate. The review confirmed closure of all prior findings, including
  complete actual-state validation, signed-64-bit revision handling, and the
  fixed 65-feature proof. It accepted only the pure Phase 1 foundation; the
  complete plan remains partially implemented, and Phase 2 and later phases
  remain blocked pending separate explicit authorization. No persistence,
  public API, frontend, Run activation, Provider integration, or public
  activation was accepted or introduced. This acceptance does not authorize a
  push, which remains user-controlled.
- 2026-07-27: This controlled documentation-only technical-prerequisite task
  began after accepted Phase 1 had been committed and pushed at
  `c8808f66e8d97bc4386a481bf21669cfddcd222e`. It drafted the exact six-family
  MySQL schema, opaque-reference/collation,
  canonical-binary storage, key/index/foreign-key, persistence-port/UoW,
  concurrency, rollback, and integration-test boundary for Phase 2. The
  amendment is an unaccepted review candidate. Phase 2 remains unimplemented
  and blocked pending fresh independent read-only acceptance of this exact
  two-path candidate and separate user authorization. No source, test,
  migration, database, Provider, production, network-service, staging, commit,
  amend, or push action occurred.
