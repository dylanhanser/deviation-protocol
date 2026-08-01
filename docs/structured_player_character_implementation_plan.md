# Structured Player-Character Downstream Implementation Plan

## 1. Status

Status: **The downstream implementation plan, technical prerequisites, and
ordered Phase 2 slice amendment are approved, frozen, committed, and pushed.
Phase 1 has passed fresh independent read-only acceptance for the exact
nine-path candidate. Its original implementation commit is
`c8808f66e8d97bc4386a481bf21669cfddcd222e`; the current completed and pushed
Phase 1 implementation baseline is
`4acb8b993f15a1fdee20edc3140324730447fc9f`
(`fix(domain): preserve exact opaque identifiers`). Phase 2 Slice 1 is
implemented, independently accepted, committed, and pushed at
`3ad39c7bb7a2c7cc6b2571f6dcb69685b7234101`. Phase 2 Slice 2 is implemented,
verified, independently reviewed with no remaining substantive issue,
committed, and pushed at
`a2802799b3d3a5497f4fc097b0cc05d573d8e0ca`. Phase 2 Slice 3 is implemented
and independently approved. Slice 4 is implemented, verified locally, and
received new-session independent implementation approval with verdict
`PHASE_2_SLICE_4_IMPLEMENTATION_INDEPENDENTLY_APPROVED`; no blocking findings
remained. Phase 2 is independently accepted and complete. P3-S1 canonical
creation orchestration completed its bounded correction and final independent
implementation review, was committed as
`7606e51523338247ea33ed9329346fdba046d29b`
(`feat(player-character): add race-safe creation recovery`), and was pushed to
`main`. Its three-document closure status synchronization was subsequently
committed and pushed at
`150074d58cdbf3aee08bea9c1084325b2b0f0a3f`
(`docs(player-character): close phase 3 slice 1 status sync`). P3-S1 is
implemented, independently approved, committed, pushed, complete, and closed.
P3-S2 mutation orchestration, P3-S3 owned read and detached projection, and
P3-S4 normal production composition are implemented. P3-S1 through P3-S4 are
complete, and the complete Phase 3 code candidate received independent
read-only approval with no implementation finding remaining open. Phase 3 is
complete, committed, and pushed at
`cafb12272e703e8751c78bb6852cec90d7d7ec8d`
(`feat(player-character): complete canonical application service`). Minimum
Run Core is implemented, independently finally approved, committed, and pushed
at `e821cd922b61868097667b12c2b64cf8089a9681`
(`feat(run): implement minimum run core`). Its null-only seam is historical:
P4-S1a is implemented at `748003319ececa548b68b351746afbb2d54c66bb` and
P4-S1b at `8eabf9d4c3c592ea1de50f443f1816de9a46dc8f`. P4-S1 is complete,
internal-only, and publicly inactive. No P4-S2 objective is defined by
repository authority. P5-S1 owned-read activation is completed and published
at `5955c47eac07429107b93ef85da6a055bd2044ef`
(`feat(player-character): activate owned-read API`); it activates only the
approved single-resource read. The P5-S2 public
creation/replay contract is frozen and published at
`245caff3903666fcd2dd9a318785f323117deb24`
(`docs(player-character): define P5-S2 public contract`). P5-S2's bounded
normal POST implementation was independently approved, committed, and
published at `4ba66d8f277988325795c905fdf6fd9e416d7457`
(`feat(player-character): add creation API`). The dedicated
[P5-S3 retirement plan](structured_player_character_p5_s3_implementation_plan.md)
received `STRUCTURED_PLAYER_CHARACTER_P5_S3_PLAN_APPROVED`. Its first,
first-corrected, and re-corrected local implementation candidates each
received `CHANGES_REQUIRED`; the third review found no production-code defect
and requested corrected evidence only. A later evidence candidate's receipt-add
1062 depended on a mid-operation rollback-and-resume topology. The focused
investigation returned
`P5_S3_RECEIPT_ADD_RACE_NOT_REACHABLE_UNDER_CURRENT_PRODUCTION_PATH`. The
accepted and published P5-S3 result uses normal HTTP serialization evidence
plus explicitly labelled defensive fault injection. Correction validation
completed locally (canonical Offline 1,814
passed/124 expected skips, MySQL 136 passed, and Full 1,937 passed/one opt-in
  Provider skip); its focused final independent review returned
  `STRUCTURED_PLAYER_CHARACTER_P5_S3_FOCUSED_FINAL_REVIEW_APPROVED`, finding no
  material scoped defect. It accepted real-MySQL aggregate-lock serialization,
  exact replay or ordinary idempotency conflict, and one durable mutation; fault
  injection is bounded defensive recovery only, and the unreachable receipt-add
  race is not a requirement. P5-S3 was committed and published at
  `34d063e387cde69500e4dc018ff087e87f3eee74`
  (`feat(player-character): add idempotent retirement endpoint`). P5-S3 is not
  a current unstaged candidate. Phase 5 ended with P5-S3; no P5-S4 exists or has
  begun, and Phase 8 planning does not reopen Phase 5. Phase 6 and Phase 7
  retain their allocations and remain unimplemented. Phase 8 — Structured
  Player Character Run Entry and Minimum Playable Loop — is the selected
  planning priority under its dedicated approved and published planning
  authority at `de4d8c0e35c7864948306d751a00aaf295ff77ff`. Phase 8 is not
  implemented; P8-S1 through P8-S6 remain unimplemented and unauthorized.
  Planning publication does not authorize implementation, and P8-S1 requires a
  separate explicit implementation task. Push by Codex, deployment, release,
  runtime activation, and Provider work remain deferred.**

Phase 2 is committed, pushed, and closed at
`ac5263fd5ca652665d23a082a19b3d66f8a047d1`
(`feat(player-character): wire repositories into unit of work`). The Phase 3–5
roadmap remains written. The revised section 24 P3-S1 authority amendment was
independently approved, committed, and pushed at
`c6d0220a2442887e89717b5b6facb14af4604236`. Its first implementation attempt
had exposed a typed-conflict ownership contradiction, and the first
authority-amendment design was rejected because the existing infrastructure
conflict is shared across unrelated Repository operations. The later separately
authorized P3-S1 implementation and its bounded correction completed final
independent implementation approval, then were committed and pushed at
`7606e51523338247ea33ed9329346fdba046d29b`. The later P3-S1 status
synchronization was the then-current pushed baseline
`150074d58cdbf3aee08bea9c1084325b2b0f0a3f`. The complete Phase 3 candidate
subsequently implemented P3-S2 through P3-S4, received independent read-only
approval, and was committed and pushed at
`cafb12272e703e8751c78bb6852cec90d7d7ec8d`. P4-G0 documentation authority
is approved and closed; it freezes the minimum Run-core prerequisite without
beginning that prerequisite or Phase 4.

The concrete Phase 2 persistence design in section 20 is a
technical-prerequisite amendment that received the independent verdict
`STRUCTURED_PLAYER_CHARACTER_PHASE_2_TECHNICAL_FREEZE_APPROVED`. The exact
approved candidate was committed and pushed unchanged as
`1fd29798fe256593e56029baca743484cc221ae4`
(`docs(domain): freeze structured player-character phase 2 prerequisites`).
It remains the historical technical-freeze commit. The later ordered-slice
amendment was approved, committed, and pushed at
`afa9f9c21900eebd4e08d65071a26903e83d4a65`. Slice 2 now adds only the exact
six-family SQLAlchemy metadata, one linear Alembic migration, and bounded
schema/migration verification. It adds no repository adapter, live-row
reconstruction, transaction or replay orchestration, production composition,
public route, frontend behavior, Provider integration, Demo behavior, or
story/Run activation. Phase 2 Slice 3 now adds only the four existing-port
MySQL Repository adapters with strict codec/identity reconstruction, immutable
history, current-row locking and CAS, allocation/binding/current/revision and
receipt operations, caller-owned sessions, and `flush()` without transaction
ownership. Its two narrow infrastructure errors classify repository operation
and known immutable/unique conflicts. Phase 2 Slice 4 now wires those four
adapters into one entered `SqlAlchemyUnitOfWork` session and supplies bounded
test-only cross-repository transaction evidence. Its production change is
limited to imports and `SqlAlchemyUnitOfWork.__aenter__`; it adds no production
orchestration. P3-S1 through P3-S4 are implemented, complete, committed, and
pushed. P4-G0 documentation authority is approved and closed. Its minimum Run
core prerequisite is implemented, independently finally approved, committed,
and pushed at `e821cd922b61868097667b12c2b64cf8089a9681`; its null-only
binding seam was the historical pre-P4-S1 baseline. P4-S1a
  (`748003319ececa548b68b351746afbb2d54c66bb`) and P4-S1b
  (`8eabf9d4c3c592ea1de50f443f1816de9a46dc8f`) are complete; later units retain
  their own accepted plan boundary, predecessor approval, and explicit
  authorization.

The ordered Phase 2 implementation slices introduced in section 24 were a
separate amendment from the prior technical-freeze verdict. The section 31
self-executing gate has been satisfied. Each numbered slice still requires its
own authorization and independent review, and a later slice may not be folded
into an earlier one.

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
and frozen product specifications. The pure Phase 1 domain and
character-operation protocol foundation is implemented, accepted, committed,
and pushed. Phase 2 Slice 1 is also implemented, accepted, committed, and
pushed. Phase 2 Slice 2 is implemented, verified, independently reviewed,
committed, and pushed. Phase 2 Slices 3 and 4 are implemented and independently
approved; Phase 2 is accepted and complete, while the complete product
specifications remain only partially implemented. Phase 3.2b remains closed.

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

For Phase 4, the
[Minimum Run Core Implementation Plan](minimum_run_core_implementation_plan.md)
owns only the prerequisite Run-core implementation sequence, persistence,
transaction order, and acceptance evidence. This plan owns P4-G0/P4-S1 gating
and the character-binding boundary. The Run Protocol owns the Run and line
lifecycle; this plan cannot use a broad roadmap sentence to override either
that authority or the player-character contract.

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

The historical technical-freeze portions of this document remain design
evidence. The section 31 ordering-amendment gate is operative, but every
numbered implementation slice retains its separate authorization and
independent-review requirement.
The separately authorized Phase 1 implementation added only pure domain models,
independent policies, deterministic character-operation serialization and
receipt semantics, and offline unit/golden-vector tests. It changes no
database, migration, schema, repository, Unit of Work, production service,
API, Provider, client, frontend, Demo, Session request/action, Run/story-line,
or production behavior. It does not reopen Phase 3.2b.
The separately authorized Phase 2 Slice 1 adds only the approved application
ports, six non-authoritative stored carriers, canonical and fingerprint codecs,
aggregate integrity validation, and offline tests. It is implemented,
independently accepted, committed, and pushed at
`3ad39c7bb7a2c7cc6b2571f6dcb69685b7234101`.

The separately authorized Phase 2 Slice 2 implementation added exactly six
SQLAlchemy mappings and migration `20260728_0004` directly after
`20260719_0003`. It is implemented and verified, received independent review
with no remaining substantive issue, was committed as
`a2802799b3d3a5497f4fc097b0cc05d573d8e0ca`, and was pushed to `origin/main`.
Relevant real-MySQL verification passed with 64 tests, and all 284 relevant
Slice 1 regression tests passed. The completed schema includes the corrected
`ck_spc_revisions_provenance_matrix`, with explicit non-NULL `prior_revision`
requirements for both `RETIRE` and `FINAL_DEATH`. Phase 2 Slice 3 then added
only the four existing-port MySQL Repository adapters, strict reconstruction,
immutable revisions, receipts, locking/CAS, and narrow error translation. It
uses caller-owned sessions and `flush()` without commit, rollback, retry, or
application orchestration. No Unit of Work, service, runtime, public, Provider,
Demo, or Run/story behavior was added.

The separately authorized Phase 2 Slice 4 implementation changes
only the UoW imports and `SqlAlchemyUnitOfWork.__aenter__` in production. It
constructs all four structured player-character Repository adapters over the
same active `AsyncSession`, preserves lazy autobegin and every existing
commit/rollback/close method, and keeps creation/mutation orchestration private
to `tests/unit/test_repository_and_uow.py` and
`tests/integration/test_mysql_player_character.py`. It is verified locally and
independently approved. Phase 2 is accepted and complete.

The exact amended P3-S1 and P3-S2 symbols, signatures, path budgets, and
acceptance boundaries in section 24 are satisfied historical authority.
P3-S3 and P3-S4 are implemented as described there. All other file names,
table names, data types,
endpoint shapes, and phase boundaries below remain prospective inventory and
are not authority to edit those surfaces. Exact choices identified as `U` must
be resolved before the affected phase begins.

P4-G0 documentation authority is approved and closed. Its three accepted
decisions are current authority rather than unresolved inventory: the minimum
Run core comes first; one character may occupy at most one active line while
one line has one active character binding once bound; and Session participation
uses a separate Run-owned record. The minimum Run core is implemented at
`e821cd922b61868097667b12c2b64cf8089a9681`; its historical seam was activated
internally by completed P4-S1a and P4-S1b.

## 5. Historical baselines and pre-closure Phase 3 baseline

The revised P3-S1 authority-amendment candidate was written against this
historical pre-implementation baseline:

- repository root: `D:\deviation-protocol`;
- branch: `main`;
- `HEAD`: `323069ff63a71adad3b7896e1a233b3d21ba8da2`;
- local `origin/main`: `323069ff63a71adad3b7896e1a233b3d21ba8da2`;
- ahead/behind: `0/0`;
- `HEAD` subject:
  `docs(player-character): approve phase 3 implementation plan`;
- then-clean working tree; and
- empty index.

That historical baseline implemented the deterministic Session-based vertical
slice through Phase 3.2b plus the accepted structured player-character Phase 1
pure domain/protocol foundation and Phase 2 persistence boundary. It does not
implement a structured player-character application service, normal production
composition, public character route, Run aggregate, continuous-story-line
aggregate, frontend, Demo parity, Provider integration, narrative integration,
or gameplay activation.

Commit `7606e51523338247ea33ed9329346fdba046d29b`
(`feat(player-character): add race-safe creation recovery`) subsequently
implemented and superseded that P3-S1 baseline, contains the structured
player-character creation service, and closed P3-S1 after final independent
approval. The three-document closure status synchronization was subsequently
committed and pushed at the pre-closure `HEAD`/local-`origin/main` baseline
`150074d58cdbf3aee08bea9c1084325b2b0f0a3f`
(`docs(player-character): close phase 3 slice 1 status sync`). The current
completed Phase 3 baseline is the independently approved, committed, and
pushed
`cafb12272e703e8751c78bb6852cec90d7d7ec8d`
(`feat(player-character): complete canonical application service`). This
section retains `150074d...` only as the historical pre-closure baseline. No
future session may use either historical baseline above to implement P3-S1 or
another Phase 3 slice again.

The current completed Phase 1 implementation baseline is
`4acb8b993f15a1fdee20edc3140324730447fc9f`
(`fix(domain): preserve exact opaque identifiers`); it follows the original
Phase 1 implementation commit
`c8808f66e8d97bc4386a481bf21669cfddcd222e` and preserves opaque identifiers
exactly. The current committed and pushed Phase 2 closure baseline is
`ac5263fd5ca652665d23a082a19b3d66f8a047d1`
(`feat(player-character): wire repositories into unit of work`). Phase 2 is
independently accepted and complete.

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

Minimum Run Core now defines and persists distinct `RunId` and
`ContinuousStoryLineId` values through `CanonicalRun`, `RunService`, five
Run-owned ORM/persistence families, migration `20260729_0005`, and normal
production composition. Completed P4-S1a/P4-S1b activate the exact internal
Run-owned character/reference binding seam in that composition. No current
source model or persistence record defines `world_id`, `visit_id`, or
`scenario_run_id`; `phase_visit_counts` is a counter, not a stable visit
identity. The broader Phase 3.3 Run Protocol remains approved but not
implemented. Therefore:

- a `GameSession` must not be relabeled as a Run (`A`, `N`);
- a scenario ID or version must not be treated as a world or visit ID (`A`);
- same-story-line binding now uses the internal
  `RunService.bind_player_character_internal` surface; scenario, world, and
  later-world integration remains stop-gated on its owning future surfaces
  (`T`);
- that prerequisite uses distinct `RunId` and `ContinuousStoryLineId`
  carriers, with one Run permanently owning exactly one line (`A/T`);
- each line has exactly one active character binding once bound, and one
  canonical character belongs to at most one active line (`A`);
- trusted Session participation must use a separate Run-owned record and must
  not add Run/binding columns to `game_sessions` (`A/T`); and
- the implemented character side of the typed internal binding cannot invent
  later Run lifecycle or movement mechanics (`E`).

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

These Session and narrative orchestrators remain pattern evidence (`N`).
Structured player-character Phase 1 owns its typed operation/replay protocol,
Phase 2 owns the dedicated aggregate lock, revision history/current state,
operation receipts, Repositories, and same-session UoW wiring, and completed
Phase 3 supplies the trusted `PlayerCharacterService` plus normal production
composition for create, mutate, and `get_owned`. Minimum Run Core supplies its
Run models, persistence, service, and composition; completed P4-S1 activates
the separately named internal binding seam. P5-S1's owned GET, P5-S2's bounded
normal POST creation/replay route, P5-S3's normal POST retirement route, the
configured service dependency getter, public exposure of the existing
`PlayerCharacterSelfProjection` DTO, and their corresponding OpenAPI operations
are implemented and published. All other Player Character public routes,
including Run binding, general mutation, listing, search, and administration
surfaces; frontend and Demo behavior; scenario/world execution; and the Run
transition to `active` remain absent.

The accepted P5-S3 retirement implementation was locally validated after the
  focused `P5_S3_RECEIPT_ADD_RACE_NOT_REACHABLE_UNDER_CURRENT_PRODUCTION_PATH`
  verdict.
  Its focused final independent review returned
  `STRUCTURED_PLAYER_CHARACTER_P5_S3_FOCUSED_FINAL_REVIEW_APPROVED` with no
  material scoped defect. The accepted real-MySQL evidence proves aggregate-lock
  serialization, replay/conflict, and one durable mutation; fault injection is
  bounded defensive recovery only, and the unreachable receipt-add race is not a
  requirement. P5-S3 was committed and published at
  `34d063e387cde69500e4dc018ff087e87f3eee74`. Phase 5 is complete at P5-S3;
  no P5-S4 exists or has begun. Phase 8 planning does not imply deployment,
  release, runtime activation, or Provider work.

For this slice, mandatory real-MySQL evidence is normal HTTP concurrency through
distinct connections/UoWs: the second retirement waits at the Player Character
`FOR UPDATE` lock, then exact-replays an identical fingerprint or returns the
ordinary idempotency conflict for a different fingerprint after exactly one
durable revision advance and mutation receipt. Fresh independent reads prove no
duplicate policy mutation, recovery UoW, receipt-add conflict, or 1062. The
existing bounded recovery branch is defensive and remains covered by explicitly
labelled narrow service fault injection with no mutation retry, third UoW,
recovery write/commit, generic retry, or uncertain-commit recovery. Real
receipt-add 1062 evidence becomes mandatory only if a future composed runtime
writer or changed transaction topology can legitimately reach receipt
uniqueness without first serializing on the aggregate lock; this plan does not
approve or require such a topology.

### Canonical state ownership

`GameState` and strict subordinate models in
`src/deviation_protocol/domain/state.py` form the current authoritative
Session snapshot. State transitions are domain-owned and Provider output is
candidate-only. `AuthoritativeStateView` is detached.

A player-character record is not embedded inside `GameState`: Session loss and
Run reset must not remove it, and same-character continuity crosses scenario
boundaries. `CanonicalPlayerCharacter` is the server-side domain aggregate;
the accepted Phase 2 ports and MySQL Repository load and commit its current and
immutable revision forms. Session and future Run state may hold only validated
references, not the master record.

### Database, migrations, and version mechanisms

`src/deviation_protocol/infrastructure/database.py` configures MySQL 8 through
SQLAlchemy `AsyncSession` and `asyncmy`; there is no SQLite fallback.
`src/deviation_protocol/infrastructure/orm_models.py` defines:

- `game_sessions`;
- `game_snapshots`;
- `domain_events`;
- `turn_requests`;
- `narrative_jobs`;
- `PlayerCharacterControllerBindingRow`
  (`player_character_controller_bindings`);
- `PlayerCharacterIdAllocationRow` (`player_character_id_allocations`);
- `PlayerCharacterRevisionRow` (`player_character_revisions`);
- `PlayerCharacterCurrentRow` (`player_character_current`);
- `PlayerCharacterCreationReceiptRow` (`player_character_creation_receipts`);
- `PlayerCharacterMutationReceiptRow` (`player_character_mutation_receipts`);
- `RunRevisionRow` (`run_revisions`);
- `RunCurrentRow` (`run_current`);
- `RunSessionParticipationRow` (`run_session_participations`);
- `RunCreationReceiptRow` (`run_creation_receipts`); and
- `RunMutationReceiptRow` (`run_mutation_receipts`).

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

The directly inspected current Alembic chain is linear:
`20260719_0001 -> 20260719_0002 -> 20260719_0003 -> 20260728_0004 ->
20260729_0005`. Revision `20260719_0001` has no parent; each later revision
directly revises its predecessor, including `20260729_0005` directly revising
`20260728_0004`. Revision `20260729_0005` is the actual current linear head.
It adds the five Run-owned families and already supplies the P4-S1 persistence
representation: the nullable binding envelope on `run_revisions` and
`run_current`, the unique non-NULL `run_current.active_player_character_id`
backstop, the binding result/evidence form in `run_mutation_receipts`, and
restrictive character-revision references from both Run state families and the
mutation receipt. P4-S1b introduced no ORM or Alembic change.
`alembic/env.py` uses the same metadata and async MySQL URL.
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
| Controller binding | `ControllerBindingRef`; private registry Repository/table and required canonical-record field | The trusted resolver uses the exact configured production allowlist | Distinct from principal fields, Session, Run, request, and character |
| Player character | `PlayerCharacterId`; permanent allocation ledger, current record, and immutable revisions | The production issuer supplies a validated canonical UUIDv4-based ID | Equality only by exact canonical ID |
| Static character definition | `DefinitionId`, `character_definition_id` | Retained as content/template reference where separately relevant | Reuse never establishes character equality |
| Session | String-valued `GameSession.session_id` with strict bounded request/DTO fields | Retained narrower identity plus a separate immutable Run-owned participation record | Never establishes character identity, Run selection, or controller authority |
| Run | Implemented by Minimum Run Core and P4-S1 | A distinct strict opaque `RunId` and one Run-owned canonical aggregate are implemented at `e821cd922b61868097667b12c2b64cf8089a9681`; P4-S1a/P4-S1b activate its internal binding carrier | Owns one line and its binding transaction; never equals Session, line, character, controller, world, or operation identity |
| Continuous story line | Implemented by Minimum Run Core and P4-S1 | A distinct strict opaque `ContinuousStoryLineId` is permanently owned one-to-one by its Run; P4-S1 binding is internal-only | Once bound, one active character per line; one character belongs to at most one active line; historical non-active references do not count |
| World / scenario / visit | Scenario only; no world or visit identity | Run-owned references when implemented | Context/provenance only, never character identity |
| Applicable character reference | `ApplicableCharacterReference` in the accepted Phase 1 domain | Completed P4-S1 stores the exact typed reference through `RunService.bind_player_character_internal`; the binding remains internal-only and `RunService.bind_player_character(...)` remains rejected | Exact match; distinct from current revision and every other version |
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
- account/controller limits and how many distinct canonical character records
  one controller may keep active; active line occupancy is frozen separately;
- shared control, multiple controllers, delegation, controller transfer,
  cross-account transfer, account recovery, or unbinding;
- arbitrary cross-Run or cross-story-line movement;
- continuity-line restart/resume and successor/replacement behavior; active
  binding cardinality is frozen separately and is not excluded or unresolved;
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
| `continuity_metadata` | Required strict group holding only trusted explicit references/evidence supplied by an owning authority; may contain no current-line reference when none is authorized. A line binding cannot simultaneously name a second or different active player character, and a character cannot occupy a second active line | Both active-binding cardinality directions `A`; post-ending restart/successor behavior `U` |
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

The trusted `PlayerCharacterIdIssuer` allocates a fresh opaque,
domain-qualified identifier. The caller cannot propose, restore, or select the
ID. Accepted Phase 1 fixes the syntax to its 1–128-character opaque-reference
alphabet, and the frozen section 20 technical prerequisite fixes its database
representation. Production directly uses Python standard-library
`uuid.uuid4()`, with UUID entropy supplied by operating-system randomness, and
formats the result as `pc.<32 lowercase UUIDv4 hexadecimal digits>` before
validating it through `PlayerCharacterId`. The ID contains no principal,
controller, timestamp, sequence, or other user information. Production exposes
no injection seam that can replace UUIDv4 generation.

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

This allocation ledger is required by frozen section 20 because
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

Tests may use the application service's deterministic injected issuer to force
collisions and prove the second allocation fails without partially committing.
Production persistence uniqueness failures fail closed, and no generalized
creation retry was introduced.

## 12. Controller-binding design

Production controller authority is deliberately narrower than an
account/controller aggregate:

- a `ControllerBindingResolver` application port receives the authenticated
  `RequestPrincipal` from trusted middleware/composition;
- it returns a distinct opaque `ControllerBindingRef`;
- Phase 2's private registry stores only that opaque binding reference;
- the canonical record stores only the binding reference, not client-submitted
  authority; and
- authorization re-resolves the current principal and exact-matches the stored
  binding before reading private state or mutating.

The production resolver uses an explicit configured allowlist. Matching uses
the complete exact `(authentication_scheme, player_id)` `RequestPrincipal`
identity and returns only the explicitly configured `controller_id`. Unknown
or invalid principals receive no authority. Configuration is immutable or
defensively copied, strict, duplicate-safe, and value-free in errors.
Resolution performs no database or UnitOfWork work and does not automatically
register, fall back to a development principal, partially match, or derive
ownership. The resolver is not an account-registration, Steam,
authorization-administration, or database-backed identity system.

Creation fails atomically if the binding cannot be resolved. Every loaded
`active`, `retired`, or `deceased` record must contain it. Every
identity-preserving mutation copies the exact binding into the complete
candidate and validates equality. Missing or altered bindings fail before
commit. Session loss, browser reset, Run reset, transport or Provider failure,
retirement, death, or record projection never calls a binding mutation.

When typed bindings are not supplied directly, required runtime JSON is read
from `PLAYER_CHARACTER_CONTROLLER_BINDINGS`. Missing, empty, malformed,
incomplete, non-canonical, duplicate-principal, or shared-controller
configuration fails closed before catalog, engine, database, or UnitOfWork
construction. No public creation or mutation route is activated by this
composition.

## 13. Lifecycle implementation design

Lifecycle is a closed domain enum. Each action is a distinct typed command and
independent policy class, consistent with repository guardrails:

| Transition | Proposed policy | Required evidence | First-slice result |
| --- | --- | --- | --- |
| `active -> retired` | `RetirePlayerCharacterPolicy` | Authenticated matching controller, explicit confirmation bound to ID and expected revision, valid continuity-ending evidence where a current line exists | While unbound, revision advances once; while P4-S1 has a current active binding, reject with `ACTIVE_BINDING_ATOMIC_LIFECYCLE_TRANSITION_REQUIRED` until a later atomic line-ending transaction exists |
| `retired -> active` | `ReactivatePlayerCharacterPolicy` | Authenticated matching controller, explicit confirmation, and separately authorized active-line plus Run/world binding evidence | Same ID/binding/reference; explicit current line established atomically; reject while evidence source is unavailable |
| `active -> deceased` | `FinalDeathPlayerCharacterPolicy` | Trusted server outcome authority and exact identity/revision/context/event evidence | While unbound, death provenance persists; while P4-S1 has a current active binding, reject with `ACTIVE_BINDING_ATOMIC_LIFECYCLE_TRANSITION_REQUIRED` until a later atomic line-ending transaction exists |
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

Cross-Run concurrency behavior beyond the frozen rule that one canonical player character belongs to at most one active continuous story line remains deferred. The first slice must nevertheless be
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

After current controller authorization and all operation-specific
pre-fingerprint gates have succeeded, including the mutation
successor-capacity gate described above:

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
RunId
  -> owns exactly one ContinuousStoryLineId
  -> Run-owned binding
  -> exact stable player_character_id
  -> exact applicable character contract/revision reference
  -> Run-owned continuous-story-line, world, scenario, and visit references
```

The completed Minimum Run Core now supplies the Run-owned prerequisite defined
by P4-G0 in the
[Minimum Run Core Implementation Plan](minimum_run_core_implementation_plan.md):
distinct `RunId` and `ContinuousStoryLineId` carriers; one Run permanently
owning one line; current state and immutable revisions with monotonic CAS;
separate trusted Session participation; a Run application transaction owner;
and an all-null future character-binding envelope. It was implemented,
independently finally approved, committed, and pushed at
`e821cd922b61868097667b12c2b64cf8089a9681`; its all-null envelope is the
historical baseline before P4-S1a/P4-S1b activated the internal binding.
`GameSession` must not masquerade as Run, and no Run or binding column may be
added to `game_sessions`.

Both active-binding directions are current authority:

- a continuous story line has exactly one active canonical
  player-character binding once bound;
- one canonical player character belongs to at most one active continuous
  story line;
- a completed, terminated, or otherwise non-active historical line retains
  its immutable exact reference without counting as active; and
- retry, concurrency, scenario, world, visit, Run, Session, browser, or
  Provider behavior cannot replace or clone that binding.

P4-S1 must enforce both directions at the Run service boundary and database
backstop. It locks or otherwise serializes the exact Run/line, exact-matches
the `ApplicableCharacterReference`, and rejects a second/conflicting line or
character before any canonical change. The Run service owns the binding mutation
UnitOfWork and one commit. Once binding is activated, the Player Character
mutation path uses the same evidence seam to fail closed for `RETIRE` and
`FINAL_DEATH`; it must not independently make a currently bound character
inactive.

P4-S1 must:

1. resolve trusted controller authority;
2. use the P4-S1-only narrow Phase 3-owned internal read seam specified by the
   minimum Run-core plan to lock and obtain the owned canonical exact
   reference and lifecycle evidence inside the already-owned Run UnitOfWork,
   without trusting submitted ownership or opening a nested UnitOfWork;
3. leave PlayerCharacterService create and public `get_owned` semantics
   unchanged; add only the internal binding-aware `RETIRE`/`FINAL_DEATH` guard
   to mutate, and never treat detached owned/public data as writable canonical
   state;
4. evaluate the binding receipt before stale Run-state rejection;
5. require an active character and active Run/line for a new binding after
   receipt evaluation;
6. write the complete Run/line/character/reference/provenance envelope, Run
   revision, current-state CAS, and receipt atomically;
7. reject conflicting active bindings with no Run or character mutation;
8. preserve ID/reference through same-line scenarios and Run-authorized
   later-world progression;
9. let Run policy alone select world, scenario, visit, eligibility, and world
   state; and
10. add no independent character commit, Session copy of the character
   aggregate, replacement, transfer, or reference-following policy.

The minimum Run core stores Session participation in its own immutable
Run-owned record. Participation is created only by trusted Run orchestration,
does not grant ownership/controller authority, supports multiple distinct
Sessions on one continuing Run, and prevents one Session from conflicting Run
routing. It does not change legacy Session rows or activate public resume,
reconnect, cross-tab, browser-restart, or multi-device behavior. The narrow
Phase 3-owned read seam preserves the approved authorization, non-enumeration,
canonical validation, and projection boundaries; it performs no character
mutation or commit. P4-S1 may not invent an outbox, saga, distributed
transaction, or eventual-consistency protocol.

Restart/resume, Session reassignment, successor/replacement, the complete
post-retirement/death/return binding transaction, arbitrary transfer, and
cross-Run/cross-line movement remain deferred. P4-S1 nevertheless rejects
`RETIRE` and `FINAL_DEATH` while a current active binding exists; this temporary
gate remains until a separately reviewed atomic transaction ends the line,
historicalizes the binding, clears current active binding, preserves immutable
history/receipts, and commits all effects together. These deferrals do not
weaken the frozen active cardinality or same-line exact-reference preservation.

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

- a player character has an explicit Run-owned line binding and the Session
  has a separate trusted Run participation record;
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

Status of this subsection: **historical technical prerequisite accepted under
`STRUCTURED_PLAYER_CHARACTER_PHASE_2_TECHNICAL_FREEZE_APPROVED`, committed
and pushed unchanged as
`1fd29798fe256593e56029baca743484cc221ae4`. It predates the current Phase 1
opaque-identifier correction and does not approve this current locked
candidate; it is not implementation authorization.**

Once the section 31 slice-order gate is satisfied and the affected slice has
been separately authorized, one new linear Alembic revision may directly revise
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
Run-owning migration, now planned by the minimum Run-core authority, must use
separate Run-owned record families and enforce both active binding cardinality
directions without changing these six families, adding Run columns to
`game_sessions`, or silently selecting a reference-following policy.

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
`ascii_bin` columns below. Phase 1 command `CharacterOperationFingerprint`
and internal `CanonicalStateRecordFingerprint` values use `BINARY(32)`, never
text or a collation. The adapter converts the former exactly between digest
bytes and Phase 1's 64-character lowercase hexadecimal value; reconstructed
hex must match the canonical lowercase form. The latter remains raw internal
digest bytes. Neither is separately indexed, and only the Phase 1 command
fingerprint participates in post-scope-key replay equivalence.

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
additional per-field text or collection ceiling, so Phase 2 adds none.

Each of the two existing successful-receipt families also retains one internal
canonical operation-evidence blob: the complete lossless Phase 1 command input
used to compute its existing operation fingerprint. It is persistence
integrity material, not a public receipt contract, a domain authority, or a
seventh family. Strict decoding and byte-identical re-encoding are required;
the existing Phase 1 fingerprint is recomputed from that evidence. Exact
opaque identifiers retain their exact bytes and are never trimmed, normalized,
case-folded, or reinterpreted. Before
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

##### Canonical state-record fingerprint and receipt binding

For each persisted authoritative `PlayerCharacter` revision, the persistence
canonical state-record representation is the exact `record_canonical` byte
sequence produced by the existing Phase 1
`canonical_character_operation_bytes(CanonicalPlayerCharacter)` helper after
the frozen player-character contract and the persistence schema have completed
their required validation and normalization. Its internal
`CanonicalStateRecordFingerprint` is the raw 32-byte SHA-256 digest of those
exact bytes. It identifies the canonical persisted content of one authoritative
revision record; it is not a product identity, an event, a seventh family, or a
separate event-sourcing subsystem.

The existing helper and canonical schema control deterministic serialization:
NFC UTF-8 JSON, stable separators and sorted normalized object keys; exact
typed field inclusion; explicit optional/null/state representation; preserved
meaningful text and ordered collections; and sorting only where an approved
type declares a collection unordered. Floats, non-JSON values, duplicate or
NFC-colliding keys, unknown fields, and lossy equivalences are rejected. Thus
logically identical validated authoritative revision records produce identical
bytes, while every field needed to reconstruct that exact revision is covered.
Database row/column layout, transport formatting, incidental timestamps or
metadata, and storage-engine representation are not inputs unless they are
themselves members of this canonical persisted state schema.

`CanonicalStateRecordFingerprint` is distinct from Phase 1
`CharacterOperationFingerprint`. The latter retains its existing public
operation-command/replay meaning and its existing receipt construction and
types remain unchanged. The former is persistence-layer integrity metadata
derived only while mapping validated Phase 1 results into the six-family Phase
2 record set. No caller or receipt-supplied fingerprint text is authoritative
for calculating it, and conversion preserves all Phase 1 receipt data while
adding only the internal metadata below.

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
| `result_record_fingerprint` | `BINARY(32)` | NOT NULL; no default | Internal `CanonicalStateRecordFingerprint` of the exact resulting revision-1 state record |
| `receipt_canonical` | `MEDIUMBLOB` | NOT NULL; no default | Exact full Phase 1 stored creation receipt bytes |
| `operation_evidence_canonical` | `MEDIUMBLOB` | NOT NULL; no default | Exact Phase 1 creation-command evidence used to recompute `fingerprint` |
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
| `before_record_fingerprint` | `BINARY(32)` | NOT NULL; no default | Internal `CanonicalStateRecordFingerprint` of the exact expected/before revision record |
| `after_record_fingerprint` | `BINARY(32)` | NOT NULL; no default | Internal `CanonicalStateRecordFingerprint` of the exact resulting/after revision record |
| `receipt_canonical` | `MEDIUMBLOB` | NOT NULL; no default | Exact full Phase 1 stored mutation receipt bytes |
| `operation_evidence_canonical` | `MEDIUMBLOB` | NOT NULL; no default | Exact Phase 1 mutation-command evidence used to recompute `fingerprint` |
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

Cross-record integrity is required at repository write and reconstruction/read
boundaries. A creation receipt must bind to the same allocated character,
controller binding, revision-1 canonical state, declarations, provenance, and
canonical-record fingerprint as its referenced history row. A mutation receipt
must bind to the same character and controller binding, exact prior/resulting
revisions, lifecycle transition, mutation kind, authority class, source
reference, and canonical state-record fingerprints as its referenced history rows.
The repository must reject an incomplete or inconsistent record set, including
missing history, broken revision continuity, substituted character/controller,
provenance mismatch, or fingerprint mismatch. These checks validate the
existing Phase 1 receipt contracts and stored result envelopes; they do not
redefine them or introduce a new receipt/history product subsystem.

One coherent cross-record validator receives the persisted creation receipt,
all persisted mutation receipts relevant to the reconstructed character
history, the complete ordered authoritative revision-record set for that
character, its current record, the controller-binding and allocation companion records, and the
declarations/provenance, lifecycle, and mutation metadata carried by those
existing records. It independently reconstructs, validates, and canonicalizes
every authoritative revision record; recomputes each
`CanonicalStateRecordFingerprint`; and compares it to
`result_record_fingerprint` for creation and to `before_record_fingerprint` and
`after_record_fingerprint` for each mutation. It binds creation to the exact
character, controller, revision 1, declarations, provenance, and result
fingerprint; binds each mutation to that exact character/controller and its
before/after revisions; verifies uninterrupted revision continuity and every
applicable lifecycle transition, mutation kind, authority class, and source
reference; and rejects cross-character or cross-controller substitution,
missing, extra where prohibited, contradictory, or incomplete history,
provenance mismatch, fingerprint mismatch, and internally inconsistent record
sets. Independently valid rows are insufficient. This validator fails closed as
an integrity failure at repository write boundaries before durable success and
at reconstruction/read boundaries before an authoritative
`PlayerCharacter` aggregate or stored success result is returned.

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
| Initial current/history insert | One complete validated revision-1 record plus canonical bytes, derived `CanonicalStateRecordFingerprint`, and server UTC time | Inserts history before its FK-backed current row; any allocation, binding, history, fingerprint, or validation mismatch fails and rolls back |
| Revision append | One complete validated successor record plus canonical bytes, derived `CanonicalStateRecordFingerprint`, and server UTC time | Insert-only; duplicate or non-successor state is conflict/integrity failure, never history replacement |
| Current-record CAS | Complete validated successor, exact expected revision and controller binding, server UTC update time | Updates by exact identity/current revision/binding and requires one affected row; zero is optimistic-concurrency conflict; it cannot advance from 9223372036854775807 |
| Creation receipt `get` / `add` | Exact `CreationReceiptKey`; reconstruct or insert one validated `StoredCreationSuccessReceipt`, relational bindings, and the repository-derived revision-1 `result_record_fingerprint` | Not found is `None`; malformed receipt/result/fingerprint binding is integrity failure; duplicate natural key is a unique-race conflict, not heuristic replay |
| Mutation receipt `get` / `add` | Exact `MutationReceiptKey`; reconstruct or insert one validated `StoredMutationSuccessReceipt`, expected revision, relational bindings, and repository-derived before/after fingerprints | Same behavior as creation; no read occurs until the future trusted caller has authorized the current record's exact stored controller binding |

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
7. canonicalize the exact revision-1 state record in the persistence mapping,
   calculate its `CanonicalStateRecordFingerprint`, and insert the accepted
   successful creation receipt with the derived `result_record_fingerprint`,
   its existing exact operation fingerprint, and privacy-safe result envelope; and
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
9. canonicalize the exact before and after revision records in the persistence
   mapping, calculate their `CanonicalStateRecordFingerprint` values, and
   insert the accepted successful mutation receipt with derived
   `before_record_fingerprint` and `after_record_fingerprint`, its existing
   exact operation fingerprint, and privacy-safe result envelope;
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

A later trusted Run workflow stores Session participation only in the separate
Run-owned `run_session_participations` family frozen by P4-G0. It adds no Run,
line, or character-binding column to `game_sessions`, and participation does
not bind or authorize a character. Legacy Sessions remain unbound and cannot
invoke structured-character mutations merely because they exist; absence of a
participation record is not an invitation to infer identity or routing.

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

Phase 1 and Phase 2 Slice 1 were separately authorized, independently accepted,
committed, and pushed. Phase 2 Slice 2 was separately authorized, implemented,
verified, independently reviewed with no remaining substantive issue, committed
as `a2802799b3d3a5497f4fc097b0cc05d573d8e0ca`, and pushed to `origin/main`.
Phase 2 Slice 3 is implemented and independently approved: its four existing-
port MySQL Repository adapters provide strict reconstruction, allocation,
binding/current/revision and receipt persistence, locking, CAS, and narrow
error translation over caller-owned sessions. Slice 4 UoW wiring and bounded
test-only cross-repository transaction evidence are implemented, verified
locally, and independently approved. Phase 2 is accepted and complete. Every
later phase remains proposed, incomplete, and unauthorized for implementation.

### Phase 1 — Domain envelope, identity types, and policies

Status: **Implemented and independently accepted for the exact
nine-path candidate. The original implementation commit is
`c8808f66e8d97bc4386a481bf21669cfddcd222e`; the current completed and pushed
implementation baseline is
`4acb8b993f15a1fdee20edc3140324730447fc9f`
(`fix(domain): preserve exact opaque identifiers`). This acceptance does not
authorize Phase 2 or a public activation.**

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

Status: **Historical technical prerequisites were accepted and frozen at
`1fd29798fe256593e56029baca743484cc221ae4`. Phase 2 Slice 1 is implemented,
independently accepted, committed, and pushed. Slice 2 schema metadata and its
single migration are implemented, verified, independently reviewed, committed
as `a2802799b3d3a5497f4fc097b0cc05d573d8e0ca`, and pushed to `origin/main`.
Slice 3 repositories are implemented and independently approved. Slice 4 Unit
of Work integration and atomicity evidence are implemented, verified locally,
and independently approved. Phase 2 is accepted and complete, while production
runtime activation remains unimplemented.**

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

Prerequisites: Phase 1 accepted at the current completed implementation
baseline; the current locked candidate independently reviewed under the section
31 gate, with `1fd29798fe256593e56029baca743484cc221ae4` retained only as the
historical technical-freeze commit; permanent non-reuse and the six section 20
physical schemas retained; the complete section 15 receipt ownership, key,
fingerprint, equivalence, result, transaction, rejection, and bounded-retention
semantics retained; and separate explicit authorization for the exact slice.
The migration slice must directly revise actual head `20260719_0003`.

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

#### Deterministic Phase 2 implementation slices

The following order is mandatory once the section 31 amendment gate becomes
operative. Each slice requires its own explicit implementation authorization
and independent review. A later slice may not be folded into an earlier one
for convenience. The order follows the actual dependency direction: typed
ports and byte-exact reconstruction define what persistence may accept and
return; mappings and DDL then fix the physical carrier; repositories then
implement those contracts against that carrier; and the Unit of Work can
finally compose the repositories and prove cross-family transaction behavior.

Earlier references in this plan to the original “first slice” or “first-slice
protocol” describe the already frozen bounded product/protocol semantics,
including successful-receipt retention. They do not expand **Phase 2 Slice 1**
below; this section's numbered names control Phase 2 implementation ordering.

##### Phase 2 Slice 1 — Offline persistence contracts and canonical stored-record codec

Why this occurs first: every mapped column, repository query, reconstruction
path, and transaction test must depend on one previously reviewed typed
contract for accepted input, returned values, canonical bytes, and integrity
failure. No later Phase 2 slice can define that contract without reversing the
domain-directed dependency.

Architectural purpose: define the domain-directed Phase 2 persistence
interfaces and the one fail-closed, database-independent conversion boundary
between the frozen Phase 1 values and the six section 20 stored record shapes.
Every later slice depends on this contract, while this slice depends on no ORM,
migration, database, Provider, production composition, or Phase 3 service.

Prerequisite slices: none. The section 31 amendment gate must be operative and
this exact slice must receive separate explicit implementation authorization.

In scope: only the exact application ports, six non-authoritative stored
carriers, canonical/fingerprint codecs, integrity failure, and exhaustive
offline tests specified below.

Expected production paths, exact for this slice:

- modify `src/deviation_protocol/application/ports.py`;
- create
  `src/deviation_protocol/infrastructure/player_character_persistence.py`.

Expected test paths, exact for this slice:

- create `tests/unit/test_player_character_persistence.py`;
- do not modify the existing Phase 1 player-character test files unless a
  separately confirmed Phase 1 regression requires it.

The application port surface introduced in
`src/deviation_protocol/application/ports.py` is exactly:

- `ControllerBindingRegistryRepository` with `get`, `add`, and `lock`;
- `PlayerCharacterRepository` with `allocation_exists`, `add_allocation`,
  `get`, `get_for_update`, `add_initial`, `append_revision`, and
  `compare_and_swap_current`;
- `PlayerCharacterCreationReceiptRepository` with `get` and `add`;
- `PlayerCharacterMutationReceiptRepository` with `get` and `add`; and
- the existing `UnitOfWork` type annotations
  `controller_bindings`, `player_characters`, `creation_receipts`, and
  `mutation_receipts`.

Those ports accept already validated Phase 1 identifiers, records, receipt
keys/results, fingerprints, and server UTC timestamps. They return `None` for
not found or complete validated Phase 1 values. They expose no commit,
authentication, controller resolution, ID generation, retry, delete, release,
repair, projection, policy invocation, or response-disclosure behavior.

The infrastructure codec module introduces exactly these persistence-facing
records, one for each and only each frozen family:

- `StoredControllerBindingRecord`;
- `StoredPlayerCharacterIdAllocationRecord`;
- `StoredCurrentPlayerCharacterRecord`;
- `StoredPlayerCharacterRevisionRecord`;
- `StoredCreationReceiptRecord`; and
- `StoredMutationReceiptRecord`.

These are typed scalar/byte carriers matching the exact section 20 columns;
they are not domain authority, ORM mappings, a seventh family, or public DTOs.
The module also introduces
`PlayerCharacterStoredRecordIntegrityError`,
`canonical_record_to_storage_bytes`,
`canonical_record_from_current_storage`,
`canonical_record_from_revision_storage`,
`creation_receipt_to_storage_bytes`,
`creation_receipt_from_storage`,
`mutation_receipt_to_storage_bytes`,
`mutation_receipt_from_storage`,
`fingerprint_to_storage_bytes`, and
`fingerprint_from_storage_bytes`.

The codec must reuse, without replacing, the Phase 1
`CanonicalPlayerCharacter`, `StoredCreationSuccessReceipt`,
`StoredMutationSuccessReceipt`, strict validators,
`canonical_character_operation_bytes`,
`canonical_player_declaration_bytes`, and fingerprint types. Encoding validates
the complete original Phase 1 object before emitting bytes. Reconstruction
strictly parses exactly one UTF-8 JSON object, constructs the existing Phase 1
type, revalidates the complete actual state, recomputes canonical bytes, and
requires byte-for-byte equality before returning any object or stored result.
The current-record decoder cross-checks every duplicated current column; the
history decoder additionally cross-checks prior revision, mutation kind,
authority class, and source reference. Receipt decoders cross-check every
scope-key, fingerprint, command, schema, owner/target, expected/result
revision, lifecycle, result, and internal state-record-fingerprint column.
They must also provide one aggregate cross-record validation input comprising
the creation receipt, relevant mutation receipts, complete ordered revision
history, current record, controller-binding/allocation companion records, and their existing
declarations, provenance, lifecycle, and mutation metadata; per-row decoding
alone is insufficient.

The codec must reject, before returning a trusted value or disclosing stored
success:

- non-object, empty, invalid UTF-8, invalid Unicode, duplicate-key, float,
  non-standard constant, out-of-signed-64-bit, unknown-field, missing-field,
  non-canonical, or trailing-content JSON;
- a canonical blob whose relational identity, contract, revision, binding,
  lifecycle, or provenance columns differ from the reconstructed value;
- a creation or mutation receipt whose referenced history is missing,
  discontinuous, cross-character or cross-controller substituted, or differs
  in provenance or canonical-record fingerprint; and
- an empty or over-65,536-byte receipt blob, any receipt/key/result mismatch,
  any impossible or Phase 1-unavailable success, and any receipt that would
  represent `REVISION_EXHAUSTED`;
- any declaration envelope above 65,536 canonical UTF-8 bytes while accepting
  the exact 65,536-byte boundary and the fixed 65-feature ordered declaration;
- any revision outside `1..9223372036854775807`, while accepting the maximum
  as readable and rejecting `9223372036854775808`;
- any Phase 1 command fingerprint other than exactly 32 storage bytes or the
  exact Phase 1 lowercase 64-hex representation, or any internal state-record
  fingerprint that does not equal SHA-256 of its independently recomputed
  canonical state-record bytes; and
- any opaque identifier that is empty, longer than 128 ASCII bytes, outside
  the Phase 1 alphabet, trimmed, case-folded, Unicode-normalized into a
  different value, semantically parsed, or otherwise reinterpreted.

Identity and round-trip obligations are exact: the accepted 128-character
maximum and shorter values preserve case and identical ASCII bytes; no
whitespace trimming, case folding, Unicode normalization, semantic parsing,
database generation, or cross-domain substitution is permitted. Omitted,
explicitly absent, intentionally undecided, and declared values remain
pairwise distinct. Ordered feature/custom-value collections retain order and
exact player-authored content. All existing Phase 1 field/type limits remain
in force and Slice 1 adds no replacement per-field or item-count ceiling.
Encoding, decoding, re-encoding, and fingerprint conversion must be
deterministic and byte-identical.

Permitted verification level: Offline only; no database, migration execution,
Provider, production, or network access. The focused command is:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_player_character_persistence.py tests/unit/test_player_character.py tests/unit/test_player_character_policies.py tests/unit/test_player_character_operations.py -q
```

The implementation task must also run
`.\.venv\Scripts\python.exe -m compileall -q src tests alembic`,
`.\scripts\verify.ps1 -Mode Offline`, and `git diff --check`.

Completion criteria: all named symbols and only the named six stored carriers
exist; port signatures preserve domain-directed dependencies; exhaustive
offline positive and malformed vectors prove exact canonical and fingerprint
round trips, relational cross-binding, receipt-to-history binding (including
later-revision reconstruction/replay), declaration states and limits,
65-feature ordering, opaque-identity behavior, receipt semantics, maximum
revision behavior, and fail-closed non-disclosure; the existing Phase 1 vectors
remain unchanged; and no SQLAlchemy model, migration, repository adapter, UoW
wiring, database test, production composition, or public behavior is added.

Explicit exclusions: ORM rows, DDL, an Alembic revision, SQL statements,
repository implementations, MySQL errors or locking, transaction orchestration,
production issuer/resolver behavior, public routes, API/frontend/Demo changes,
Run/story behavior, Provider integration, and Phase 3 work.

Database access required by the eventual Slice 1 implementation task: **No**.

Still blocked after Slice 1: all schema/migration work, MySQL adapters, UoW
wiring, transactional integration proof, every public or production
composition, and Phases 3–7.

##### Phase 2 Slice 2 — Exact six-family SQLAlchemy metadata and linear Alembic migration

Implementation status: **Implemented and verified; independently reviewed with
no remaining substantive issue; committed as
`a2802799b3d3a5497f4fc097b0cc05d573d8e0ca`; and pushed to `origin/main`.
Slices 3–4 were implemented later under their separate authorizations; every
runtime/public phase remains unimplemented.**

Why this occurs second: ORM metadata and DDL must implement the already tested
Slice 1 carriers and cannot safely precede their strict byte/identity contract.
Repositories cannot be implemented against tables that do not yet have one
reviewed exact mapping and migration.

Prerequisite slices: Slice 1 implemented, independently accepted, and present.

In scope: add exactly the six section 20 ORM mappings and one additive linear
Alembic revision; encode every frozen column type, length, `ascii_bin`
identity/token collation, `utf8mb4_bin` table default, key, named check,
restrictive foreign key, exact ordinary/unique index, timestamp rule, and
InnoDB option; preserve both ordinary non-unique indexes
`ix_spc_revisions_controller_binding (controller_binding)` and
`ix_spc_mutation_receipts_result_revision
(result_player_character_id, resulting_revision)` exactly; keep the migration
empty of backfill and make downgrade refuse unsafe use after issuance as
specified in section 20.

Explicit exclusions: repositories, SQL locking/CAS behavior, UoW wiring,
creation or mutation transaction harnesses, any seventh family or table,
Session/Run/account foreign keys, redundant indexes, SQLite, public
composition, and every Phase 3 concern.

Expected production paths:

- modify `src/deviation_protocol/infrastructure/orm_models.py`;
- create one
  `alembic/versions/<implementation-assigned-revision>_structured_player_character_phase_2.py`.

Only the later filename/revision identifier is deferred to the authorized
implementation session's collision-free Alembic convention; its
`down_revision` is fixed as `20260719_0003`, it must be the sole new head, and
its contents are fixed by section 20.

Expected test paths:

- modify `tests/integration/test_mysql_connection.py`;
- create `tests/integration/test_mysql_player_character.py` for schema-level
  checks that will be extended, not replaced, by Slices 3 and 4.

Permitted verification level: offline metadata/Alembic inspection plus real
MySQL 8 integration against only `deviation_protocol_test`; no Provider,
production, or other network service. Completion requires both the repository
Offline verifier and the authorized MySQL verifier, plus Alembic heads/history
and `git diff --check`.

Completion criteria: the migration upgrades from `20260719_0003` to exactly one
head; all six and only six families have the exact frozen schema; MySQL reports
the intended collations, constraints, foreign-key actions, and complete ordered
index inventory with no undeclared generated child index; an empty upgrade
creates no structured records and changes no legacy row; migration failure
behavior is verified without claiming transactional DDL where MySQL does not
provide it; and no repository or runtime behavior is claimed.

Database access required by the eventual Slice 2 implementation task:
**Yes**, limited to the approved MySQL integration-test database for completion
evidence. Migration execution against production or any non-test database
remains prohibited.

After Slice 3, the bounded MySQL Repository layer provides live-row
reconstruction, locking/CAS, and receipt operations. Slice 4 now supplies the
locally verified UoW composition and test-only cross-repository transaction
evidence; Phases 3–7 remain blocked.

##### Phase 2 Slice 3 — MySQL repositories, locking, CAS, and strict reconstruction

Status: **Implemented and independently approved for the exact four-path
candidate. The adapters cover the frozen four existing ports, use caller-owned
sessions, perform authorized SQL and `flush()` without commit, rollback, retry,
or transaction recovery, and add only the two narrow infrastructure error
classifications. Unit of Work composition and every public/runtime integration
were outside Slice 3; the former is now present only in the independently
approved Slice 4 implementation, while every public/runtime integration
remains deferred.**

Why this occurs third: repository SQL depends on the accepted Slice 1
ports/codecs and the accepted Slice 2 mapped physical schema. Keeping UoW
composition later permits an independent review of every individual
read/write/lock/CAS primitive before cross-family transaction claims.

Prerequisite slices: Slices 1–2 implemented, independently accepted, and
present.

In scope: implement all four Slice 1 repository interfaces over one supplied
`AsyncSession`; registry get/add/`SELECT ... FOR UPDATE`; allocation
exists/add with collision classification and no release; current get and
locked get; initial history then current insert; immutable successor-history
append; current CAS over exact identity, expected revision, and controller
binding with exactly one affected row; creation and mutation receipt get/add;
flush without commit; conversion through only the Slice 1 codec; MySQL
duplicate/constraint failure classification narrow enough not to translate
unrelated integrity failures; and focused real-MySQL concurrency,
round-trip, corruption, case/collation, and restrictive-FK tests.

Creation-receipt lookup remains binding-owned and requires no pre-existing
current player character. Mutation-receipt identity remains the collision-safe
natural scope `(player_character_id, player-character.mutate/v1,
operation_id)`. Exact replay data may be loaded after later revisions, but
only the future trusted caller may authorize and disclose it. Repository
methods do not invoke Phase 1 policies, choose transaction order, retry an ID,
resolve controllers, issue production IDs, commit, or return public responses.

Explicit exclusions: UoW repository construction, commit/rollback ownership,
business orchestration, unique-race winner reauthorization, public/API/Demo
composition, Run/story continuity effects, Provider behavior, and Phase 3.

Expected production paths:

- modify `src/deviation_protocol/infrastructure/repositories.py`;
- modify `src/deviation_protocol/infrastructure/errors.py` only for the narrow
  allocation, optimistic-concurrency, unique-race, and stored-integrity
  classifications required by the frozen ports; and
- reuse, without widening,
  `src/deviation_protocol/infrastructure/player_character_persistence.py`.

Expected test paths:

- create `tests/unit/test_player_character_repositories.py`;
- extend `tests/integration/test_mysql_player_character.py`.

Permitted verification level: focused offline mock/unit tests plus real MySQL
8 integration against only `deviation_protocol_test`; no production database,
Provider, API, frontend, Demo, or external network access. Completion also
requires Offline and MySQL verifiers, compileall, Alembic heads/history, and
`git diff --check`.

Completion criteria: all repository capabilities in section 20 pass exact
round-trip and malformed-row tests for all six families; case variants and
128-byte identities remain distinct and exact; 129-byte/malformed values fail;
the 65,536-byte declaration boundary and fixed 65 features reload unchanged;
receipt fingerprints and stored results are exact; maximum revision reloads,
the final representable successor CAS is supported, and overflow is rejected;
locking serializes the exact owner; one CAS winner is possible; losing or
unrelated integrity failures are classified without repair or false replay;
restrictive parents cannot be updated/deleted through repository behavior; and
no repository commits independently.

Database access required by the eventual Slice 3 implementation task:
**Yes**, limited to the approved MySQL integration-test database.

Still blocked after Slice 3: production UoW exposure, multi-family atomic
creation/mutation proof, rollback/fresh-transaction winner recovery proof,
Phase 2 closeout, every public/production invocation path, and Phases 3–7.

##### Phase 2 Slice 4 — SQLAlchemy Unit of Work wiring and atomic Phase 2 integration proof

Implementation status: **Implemented, verified locally, and independently
approved in a new session with verdict
`PHASE_2_SLICE_4_IMPLEMENTATION_INDEPENDENTLY_APPROVED`; no blocking findings
remained. Phase 2 is accepted and complete.**

Why this occurs fourth: only after each repository primitive and the physical
schema are accepted can the existing `SqlAlchemyUnitOfWork` safely expose all
four repositories over one `AsyncSession` and support evidence-backed
cross-family atomicity and rollback claims.

Prerequisite slices: Slices 1–3 implemented, independently accepted, and
present.

In scope: instantiate `controller_bindings`, `player_characters`,
`creation_receipts`, and `mutation_receipts` on one entered
`SqlAlchemyUnitOfWork`; preserve explicit commit/rollback and rollback-on-exit;
prove with a Phase 2-only transaction harness the frozen creation and mutation
orders without adding the Phase 3 trusted service; prove binding plus
allocation plus revision 1 plus current plus creation receipt commit or roll
back together; prove successor history plus current CAS plus mutation receipt
commit or roll back together; prove concurrent binding insertion, allocation,
receipt uniqueness, locks, CAS, and loser rollback; and prove a loser uses a
fresh UoW for durable-winner reread without repeating allocation or mutation.

The integration harness may inject deterministic typed IDs, bindings,
timestamps, and already validated Phase 1 commands/records. It is test-only:
it does not select production issuance, controller resolution, binding
creation/invocation, trusted orchestration, result disclosure, or public
composition. Exact replay and changed-command conflict are demonstrated by
reusing the Phase 1 receipt protocol over persisted repository results,
including authorized later-revision replay and current-state validation before
stored-result disclosure. `REVISION_EXHAUSTED` remains an internal failure and
creates no fingerprint, history, CAS, receipt, or persisted success.

Explicit exclusions: `player_character_service.py`, resolver/issuer
composition, `api/dependencies.py`, routes, response projections, frontend,
Demo, Provider/model, Run/story-line activation, migration execution outside
the approved test database, and every Phase 3 or later responsibility.

Expected production paths:

- modify `src/deviation_protocol/infrastructure/unit_of_work.py`;
- do not modify the accepted Slice 1 port contract. If UoW wiring proves that
  contract inadequate, stop for a separate reviewed amendment; no new port or
  record family may be added inside Slice 4.

Expected test paths:

- modify `tests/unit/test_repository_and_uow.py`;
- extend `tests/integration/test_mysql_player_character.py`;
- modify `tests/integration/conftest.py` only to add owned cleanup for the
  exact six Phase 2 families in restrictive-FK-safe order.

The implementation reused the existing module-local restrictive-FK-safe
`repository_test_scope`, so `tests/integration/conftest.py` remained unchanged.
Production changes are limited to the UoW imports and `__aenter__`; unit and
real-MySQL evidence is limited to the other two expected test paths.
The accepted evidence covers same-session Repository wiring, lazy autobegin
preservation, explicit UoW commit ownership, normal, exceptional, and
cancellation rollback, atomic creation and replay, controlled pre-COMMIT
failure rollback, a genuine uniqueness race with loser rollback and fresh-UoW
winner recovery, atomic mutation and replay after a later revision, and
mutation rollback across history, current row, and receipt. Failed sessions
are not reused, no automatic retry was added, and uncertain-COMMIT recovery
and exactly-once behavior remain excluded.

Permitted verification level: focused unit tests, the complete Offline
verifier, Full verification where safely configured, and real MySQL 8
integration/MySQL verifier against only `deviation_protocol_test`; no Provider,
production service, or other external network access.

Completion criteria: one entered UoW exposes the four exact repositories on one
session; repository methods never commit; commit publishes every required
family exactly once; explicit rollback, exception exit, commit failure, CAS
loss, constraint loss, and malformed reload publish no partial success; exact
creation replay performs no second allocation; exact mutation replay after a
later revision performs no second mutation; changed commands conflict;
creation receipts remain independent of a pre-existing current character;
mutation receipt scope is collision-safe; maximum-revision exhaustion persists
nothing; a fresh session reloads byte-identical complete records/receipts; all
Phase 2 MySQL tests pass; the canonical documentation-synchronization checklist
and a fresh independent Phase 2 implementation audit are complete before any
Phase 2 completion or commit request.

Database access used by this Slice 4 implementation task:
**Yes**, limited to the approved MySQL integration-test database.

Local verification evidence: focused UoW unit `16 passed`; focused
structured-character MySQL `34 passed`; MySQL verifier `81 passed`; Offline
verifier `1,389 passed, 71 skipped`; Full verifier `1,459 passed, 1 skipped`;
and `compileall`, Alembic heads/history, dependency checks, and
`git diff --check` passed. The initial sandboxed Full run completed test
execution but failed pytest user-temporary-directory cleanup with a sandbox
permission error; the exact permitted rerun outside that sandbox passed. Live
Provider behavior remained disabled.

Still unimplemented after Slice 4: trusted application orchestration, production
controller resolution and ID issuance, public routes/projections, frontend,
Demo, Provider, Run/story activation, and every Phase 3–7 responsibility.

### Phase 3 — Trusted canonical application service

Status: **P3-S1 canonical creation orchestration is implemented, independently
approved, committed, pushed, complete, and closed at
`7606e51523338247ea33ed9329346fdba046d29b`
(`feat(player-character): add race-safe creation recovery`). The earlier
changes-required review and bounded exception-suppression correction are
complete historical stages. P3-S2 canonical mutation orchestration, P3-S3
owned read and detached projection, and P3-S4 normal production composition
are implemented. P3-S1 through P3-S4 are complete. The complete Phase 3 code
candidate received independent read-only approval, and no implementation
finding remains open. Phase 3 is complete, committed, and pushed at
`cafb12272e703e8751c78bb6852cec90d7d7ec8d`. P4-G0 documentation authority is
approved and closed; P4-S1 is subsequently complete, without implying broader
Phase 4 completion.**

The repository-authoritative Phase 3 order is:

| Slice | Responsibility | Prerequisite | Explicitly deferred |
| --- | --- | --- | --- |
| P3-S1 — Canonical creation orchestration | Injectable creation/replay service over accepted typed commands, policy, repositories, and UoW | Accepted Phases 1–2 | Production composition, API, frontend, Demo, Run, Provider |
| P3-S2 — Canonical mutation orchestration | Receipt-before-stale workflow, policy evaluation, history, CAS, receipt, and commit | Accepted P3-S1 boundary | Public mutation, Run effects, unavailable authorities |
| P3-S3 — Owned read and detached self projection | Authorized canonical read and explicit privacy-bounded detached projection | Accepted authorization boundary | HTTP schemas/routes and frontend |
| P3-S4 — Normal production composition | Construct the accepted service in the normal MySQL composition root with the accepted production resolver and issuer adapters | Accepted P3-S1–S3 plus adapter decisions | Public routes and Demo parity |

#### P3-S1 — Canonical Creation Application Service

Objective: add one production application service that creates one canonical
player character atomically or returns the exact stored safe result for a valid
replay, without activating a runtime or public path.

P3-S1 had the following exact `4 + 2 + 3` maximum changed-path budget for its
separately authorized implementation, which the approved implementation
satisfied:

| Category | Maximum | Exact candidate inventory |
| --- | ---: | --- |
| Production | 4 | new `src/deviation_protocol/application/player_character_service.py`; extend `src/deviation_protocol/application/ports.py`; extend `src/deviation_protocol/infrastructure/errors.py`; minimally extend `src/deviation_protocol/infrastructure/repositories.py` only for the exact binding-add duplicate translation |
| Tests | 2 | new `tests/unit/test_player_character_service.py`; new `tests/integration/test_mysql_player_character_service.py` |
| Documentation synchronization | 3 | `PLANS.md`; `docs/architecture.md`; this plan |
| Dependencies, schema, ORM, migrations | 0 | none |

No additional path belongs to P3-S1. In particular, no dependency, schema,
migration, ORM model, UoW interface or implementation, other infrastructure
module, `__init__.py`, API route, composition root, Demo, frontend, Provider or
model integration, Run Protocol implementation, narrative, scenario, content,
or gameplay path is authorized. The implementation was required to stop rather
than exceed this budget; the approved implementation satisfied that historical
gate.

##### Existing authorities that P3-S1 must reuse

P3-S1 reuses, without redefining:

- `application.identity.RequestPrincipal`;
- `domain.player_character.PlayerCharacterId`,
  `ControllerBindingRef`, `PlayerCharacterOperationId`,
  `AuthoritySourceRef`, `CanonicalPlayerCharacter`,
  `revalidate_player_character_model`,
  `validate_canonical_player_character`, and
  `canonical_player_declaration_bytes`;
- `application.player_character_operations.CharacterCreationCommand`,
  `CreationReceiptKey`, `CreationSuccessResult`,
  `StoredCreationSuccessReceipt`, `CharacterOperationProtocolDecision`,
  `CharacterOperationProtocolCode`, `creation_fingerprint`,
  `evaluate_creation_receipt_protocol`, and
  `recover_creation_unique_race_winner`;
- `domain.player_character_policies.CreatePlayerCharacterPolicy.create`,
  `PlayerCharacterPolicyDecision`, and `PlayerCharacterPolicyCode`;
- `application.ports.ControllerBindingRegistryRepository`,
  `PlayerCharacterRepository`,
  `PlayerCharacterCreationReceiptRepository`,
  `PlayerCharacterMutationReceiptRepository`, `UnitOfWork`, and
  `UnitOfWorkFactory`;
- `infrastructure.repositories.SqlAlchemyControllerBindingRegistryRepository`,
  `SqlAlchemyPlayerCharacterRepository`,
  `SqlAlchemyPlayerCharacterCreationReceiptRepository`, and
  `SqlAlchemyPlayerCharacterMutationReceiptRepository`;
- `infrastructure.unit_of_work.SqlAlchemyUnitOfWork`;
- `infrastructure.errors.PlayerCharacterRepositoryError` and
  `PlayerCharacterRepositoryConflictError`; and
- `infrastructure.player_character_persistence.PlayerCharacterStoredRecordIntegrityError`.

The accepted Phase 2 concurrency evidence remains
`test_mysql_uow_creation_unique_race_rolls_back_loser_and_fresh_uow_reads_winner`.
P3-S1 adds application sequencing evidence; it does not recreate Phase 2
mapping, constraint, locking, rollback, or reconstruction tests.

##### Conflict ownership and exact Repository translation amendment

Repository inspection establishes that the exact shared infrastructure symbol
is `infrastructure.errors.PlayerCharacterRepositoryConflictError`. The
existing `_flush_row` translates a MySQL duplicate key identified by
`_is_mysql_duplicate_key` into that shared type for all of these operations:

- `SqlAlchemyControllerBindingRegistryRepository.add`;
- `SqlAlchemyPlayerCharacterRepository.add_allocation`;
- both revision and current-row flushes in
  `SqlAlchemyPlayerCharacterRepository.add_initial`;
- the revision flush in `append_revision`;
- the creation-receipt insert flush; and
- the mutation-receipt insert flush.

The same shared type is also raised directly for missing-current and
stale-current conditions in `append_revision`, creation-receipt key/result
prechecks, and mutation-receipt key/result prechecks. It is therefore a shared
infrastructure conflict identity, not a controller-binding-only signal. The
rejected first amendment would have made that existing shared class inherit or
implement an application-owned binding contract, which would have made
allocation, initial-state, receipt, stale-current, and other conflicts satisfy
the recovery type. That design is prohibited.

The exact approved translation boundary is the
`await self._flush_row(PlayerCharacterControllerBindingRow(...))` call in
`SqlAlchemyControllerBindingRegistryRepository.add`. That flush targets only
the one newly added binding row. The
`player_character_controller_bindings` table has
`controller_binding` as its primary key and no other unique constraint, so a
MySQL 1062 recognized at this exact row-only flush is the approved same-binding
uniqueness race. Translation at this call is therefore sufficiently narrow
without examining a message or classifying any other Repository operation.

The application dependency scan
`test_domain_and_application_dependency_direction_scan` prohibits every
`deviation_protocol.infrastructure` import from application modules.
Conversely, `infrastructure/repositories.py` and
`infrastructure/unit_of_work.py` already import application ports, and the
dependency scan imposes no application-import prohibition on infrastructure.
The amended dependency direction is therefore:

```text
application.ports.ControllerBindingUniquenessConflictError
                          ^
                          |
infrastructure.errors.PlayerCharacterControllerBindingConflictError
                          |
                          v
infrastructure.errors.PlayerCharacterRepositoryConflictError compatibility
```

`application.ports.ControllerBindingUniquenessConflictError` is the one narrow
application-owned typed exception contract. The unchanged shared
`PlayerCharacterRepositoryConflictError` must not inherit or implement it.
`infrastructure.errors.PlayerCharacterControllerBindingConflictError` is the
one new concrete binding-specific exception and must be a normal statically
catchable subtype of both the narrow application contract and the existing
shared infrastructure conflict. This preserves existing callers that catch the
shared type while keeping the shared type and all unrelated instances outside
the narrow application contract.

The smallest approved Repository change is a private, narrowly parameterized
`_flush_row` conflict type whose default remains
`PlayerCharacterRepositoryConflictError`. Only the controller-binding
Repository's exact add call supplies
`PlayerCharacterControllerBindingConflictError`; every other caller omits the
parameter and retains its current behavior. `_flush_row` must continue to use
`raise ... from exc`, and `_is_mysql_duplicate_key` remains unchanged. A local
catch-and-rethrow is not needed. This amendment authorizes no message matching,
module-name inspection, dynamic import, reflection, general exception
classifier, generic retry marker, Repository wrapper, broad helper refactor,
or application handling of MySQL or SQLAlchemy exceptions.

The authorized private shape is:

```python
async def _flush_row(
    self,
    row: Any,
    *,
    conflict_message: str,
    conflict_type: type[PlayerCharacterRepositoryConflictError] = (
        PlayerCharacterRepositoryConflictError
    ),
) -> None:
    ...
    if _is_mysql_duplicate_key(exc):
        raise conflict_type(conflict_message) from exc
```

Only `SqlAlchemyControllerBindingRegistryRepository.add` passes
`conflict_type=PlayerCharacterControllerBindingConflictError`. This is a
private helper signature adjustment, not a public abstraction or classifier.

##### Exact new production symbols

P3-S1 preserves the four previously approved public production symbols:

- `application.player_character_service.PlayerCharacterService`;
- `PlayerCharacterService.create`;
- `application.ports.ControllerBindingResolver`; and
- `application.ports.PlayerCharacterIdIssuer`.

The amendment authorizes only these two additional public production symbols:

- `application.ports.ControllerBindingUniquenessConflictError`; and
- `infrastructure.errors.PlayerCharacterControllerBindingConflictError`.

The existing `PlayerCharacterRepositoryConflictError` remains present with its
shared semantic scope and must not acquire the narrow contract as a base. No
generic application persistence-error hierarchy, second application conflict
contract, result code, UoW type, Repository wrapper, clock or policy port, ID
retry abstraction, generic retry, validation framework, adapter, composition
root, or persistence responsibility is authorized. Existing callable-clock
patterns, a trusted
`AuthoritySourceRef`, `CreatePlayerCharacterPolicy`, and `UnitOfWorkFactory`
are construction dependencies of the service, not caller-supplied method
authority and not new public ports.

The exact service operation is:

```python
async def create(
    self,
    principal: RequestPrincipal,
    *,
    operation_id: PlayerCharacterOperationId,
    command: CharacterCreationCommand,
) -> CreationSuccessResult | CharacterOperationProtocolDecision:
    ...
```

`READY_FOR_NEW_OPERATION` is internal control flow. Only
`CreationSuccessResult` or a non-success
`CharacterOperationProtocolDecision` may leave this method.

##### Exact new application/port contracts

The narrow exception contract and both ports belong in
`src/deviation_protocol/application/ports.py`:

```python
class ControllerBindingUniquenessConflictError(RuntimeError):
    """Only the approved controller-binding add uniqueness race."""


class ControllerBindingResolver(Protocol):
    async def resolve(
        self,
        principal: RequestPrincipal,
        /,
    ) -> ControllerBindingRef | None: ...


class PlayerCharacterIdIssuer(Protocol):
    def issue(self) -> PlayerCharacterId: ...
```

The infrastructure error module may add the corresponding concrete exception
with the following required static relationships:

```python
class PlayerCharacterControllerBindingConflictError(
    PlayerCharacterRepositoryConflictError,
    ControllerBindingUniquenessConflictError,
):
    """A duplicate at the exact controller-binding add flush."""
```

An equally narrow normal typed base ordering is acceptable only if static
`except ControllerBindingUniquenessConflictError` works, existing
`except PlayerCharacterRepositoryConflictError` compatibility is preserved,
and `PlayerCharacterRepositoryConflictError` itself remains outside the narrow
contract. The application service imports only
`ControllerBindingUniquenessConflictError`; it must not import the concrete
infrastructure subtype.

| Port | Form and position | Absence or failure | Persistence and trust restriction |
| --- | --- | --- | --- |
| `ControllerBindingResolver.resolve` | Asynchronous; initial call before UoW entry. The one permitted recovery reauthorization may occur after fresh-UoW context entry but before its first Repository SQL/lazy transaction. | `None` or an invalid returned object becomes `AUTHORIZATION_FAILED`; resolver exceptions propagate unchanged. | May consult its own trusted authority source; may not use player-character persistence to invent authority, auto-bind an unknown principal, or derive a binding by copying `principal.player_id`. |
| `PlayerCharacterIdIssuer.issue` | Synchronous; exactly once on a normal new-operation attempt, inside the active creation UoW after authorization and receipt evaluation return `READY_FOR_NEW_OPERATION`. | Exceptions or an invalid returned value propagate; allocation collision propagates the existing Repository conflict. | Accepts no caller input, performs no Repository/database access, supplies no collision recovery, and promises no predictable algorithm. |

`RequestPrincipal` construction owns NFC/safe-identifier validation.
`ControllerBindingRef` and `PlayerCharacterId` construction own opaque-reference
validation. Ports return fully typed values. The service defensively
revalidates those returned values and never normalizes them into different
identities.

A valid principal is input to trusted resolution, not authority by itself.
`None` never becomes accepted because the registry row is absent. The service
may add a missing registry row only after the resolver returned that exact
valid binding. It must never auto-register, auto-bind, copy
`principal.player_id`, or convert an unknown principal into authority.

The ID issuer returns a complete `PlayerCharacterId`; the allocation Repository
owns the database uniqueness backstop. Issuance occurs only after exact receipt
lookup produces `READY_FOR_NEW_OPERATION`. Exact replay never issues another
identity. Allocation collision never triggers a second issuance and is not an
idempotent-winner race. P3-S4 selects the configured allowlist resolver and
standard-library UUIDv4 production issuer described in sections 11 and 12.

##### Validation ownership

Creation validation remains one ordered set of existing authorities:

1. The caller constructs typed `RequestPrincipal`,
   `PlayerCharacterOperationId`, and `CharacterCreationCommand`.
2. Typed `PlayerCharacterOperationId` construction remains the normal
   structural-validation boundary. Before constructing `CreationReceiptKey`,
   any creation-receipt Repository lookup, or receipt-protocol evaluation, the
   service nevertheless calls
   `revalidate_player_character_model(operation_id, PlayerCharacterOperationId)`.
   It preserves the helper's existing validation/error behavior and does not
   catch or translate that failure into a new generic application error. This
   reuses the existing defensive helper; it is neither a second validation
   framework nor new domain policy.
3. `CharacterCreationCommand` is strict, frozen, and `extra="forbid"`; its
   `validate_declaration_envelope` validator calls
   `canonical_player_declaration_bytes`.
4. `canonical_player_declaration_bytes` uses
   `revalidate_player_character_model` for `CharacterCore` and
   `NarrationPreferences` and verifies the canonical declaration envelope.
   Successful command construction therefore completes structural input
   validation.
5. After trusted controller resolution and binding locking,
   `creation_fingerprint(command)` defensively calls
   `revalidate_player_character_model(command, CharacterCreationCommand)` and
   constructs the canonical fingerprint. This is not a second schema or
   business-validation system.
6. `evaluate_creation_receipt_protocol` defensively revalidates the binding,
   operation ID, and command while enforcing authorization-before-disclosure
   and receipt semantics. The service awaits the exact Repository read first
   and supplies the already-fetched value through the evaluator's synchronous,
   side-effect-free lookup callback.
7. For a new operation, `CreatePlayerCharacterPolicy.create` revalidates its
   typed inputs and owns trusted initial-record construction.
8. `CanonicalPlayerCharacter` validates the complete record, after which the
   service calls `validate_canonical_player_character` as the explicit
   complete-record boundary before persistence.
9. Repository codecs retain persistence representation and stored
   cross-record integrity; they do not duplicate application authorization or
   domain policy.

Trusted principal mapping belongs only to `ControllerBindingResolver`; opaque
binding validity belongs to `ControllerBindingRef`; stored exact-match,
authorization, and privacy belong to the existing operation protocol plus
registry/current reads. Domain-policy validity belongs to
`CreatePlayerCharacterPolicy` and the existing mutation policy classes. The
service only sequences these authorities.

##### First execution, replay, and commit order

First execution is exactly:

1. Receive already constructed typed principal, operation ID, and command.
2. Await `ControllerBindingResolver.resolve`.
3. Return `AUTHORIZATION_FAILED` if resolution is absent or invalid.
4. Enter one UoW.
5. Lock the exact controller-binding registry row.
6. If absent, add it only because the trusted resolver authorized that exact
   binding. Place `except ControllerBindingUniquenessConflictError` only
   immediately around the awaited `controller_bindings.add` call for the
   narrow recovery path; do not enclose any later operation.
7. Call
   `revalidate_player_character_model(operation_id, PlayerCharacterOperationId)`.
8. Call `creation_fingerprint(command)`.
9. Construct the exact `CreationReceiptKey` and await creation-receipt lookup.
10. Call `evaluate_creation_receipt_protocol` over the already-read receipt.
11. Return an existing rejection decision unchanged, or return the stored
   `CreationSuccessResult` for `EXACT_REPLAY`.
12. Only for `READY_FOR_NEW_OPERATION`, call
   `PlayerCharacterIdIssuer.issue` exactly once.
13. Revalidate the issued `PlayerCharacterId`.
14. Call `player_characters.add_allocation`; never recover or reissue on
   collision.
15. Call `CreatePlayerCharacterPolicy.create` with the injected trusted
   `AuthoritySourceRef`.
16. Call `validate_canonical_player_character` on the complete initial record.
17. Build the existing `CreationSuccessResult` and stored creation receipt.
18. Call `player_characters.add_initial`.
19. Call `creation_receipts.add`.
20. Call `uow.commit()` exactly once.
21. Return success only after commit returns.

The injected existing clock pattern supplies Repository `created_at` values;
it adds no caller authority and does not alter the authoritative sequence
above.

Exact replay resolves trusted authority, enters a UoW, locks the binding,
defensively fingerprints the command, reads the exact receipt, and evaluates
the protocol. `EXACT_REPLAY` returns only the stored
`CreationSuccessResult`. It performs no identity issuance, policy call, write,
or commit; UoW exit rolls back/closes its read transaction.

Same key with changed command data returns
`CharacterOperationProtocolDecision(code=IDEMPOTENCY_CONFLICT)` before
issuance, policy, write, or commit. A malformed or inconsistent stored receipt
returns `STORED_RECEIPT_INTEGRITY_FAILURE` and discloses no stored result.

`PlayerCharacterService` owns UoW construction, entry, and the single explicit
success-path commit. Repository adapters own flush-level SQL only.
`SqlAlchemyUnitOfWork` owns rollback and close on every uncommitted,
exceptional, cancellation, and controlled pre-COMMIT exit. A failed session is
never reused, and no success is disclosed before commit returns.

##### Exact uniqueness-race recovery boundary

Fresh-UoW recovery is allowed only when both conditions are true:

1. the application-owned
   `ControllerBindingUniquenessConflictError` contract is raised; and
2. it is raised synchronously from the exact awaited
   `ControllerBindingRegistryRepository.add` call enclosed by the service's
   narrow catch boundary while concurrently inserting the same newly resolved
   key in `player_character_controller_bindings.controller_binding`.

The expected real adapter signal is
`PlayerCharacterControllerBindingConflictError`, but the service neither
imports nor catches that infrastructure name. Exception identity alone does
not authorize recovery if the narrow contract appears at a later write,
another Repository operation, UoW lifecycle method, or any other call site.

The exact permitted sequence is:

1. Catch only `ControllerBindingUniquenessConflictError` at that add call, not
   around later writes or UoW lifecycle work.
2. Propagate out of the original UoW so its SQL-failed session rolls back,
   closes, and is abandoned.
3. Open at most one fresh UoW.
4. Re-resolve and defensively revalidate the principal's controller authority
   once.
5. Lock the same controller-binding registry row in the fresh UoW.
6. Directly call
   `revalidate_player_character_model(operation_id, PlayerCharacterOperationId)`
   as a second defensive boundary for the retained typed operation ID.
7. Only after that call succeeds, construct and read only the exact
   `CreationReceiptKey` through the fresh UoW's `creation_receipts.get`
   `(controller_binding, player-character.create/v1, operation_id)`.
8. Call `recover_creation_unique_race_winner` over that already-read receipt
   with `losing_transaction_rolled_back=True`.
9. Return the stored success only for `EXACT_REPLAY`.
   `IDEMPOTENCY_CONFLICT`, `STORED_RECEIPT_INTEGRITY_FAILURE`, or
   `AUTHORIZATION_FAILED` returns unchanged.
10. Perform no write, commit-required mutation, policy call, second allocation,
   or second issuance.

This second call neither replaces nor weakens the normal-path direct
revalidation in the first-execution sequence. It reuses the existing helper and
exact `PlayerCharacterOperationId` type, adds no validation framework, domain
policy, or Repository responsibility, and must complete before the caller
invokes any helper that could construct the key or perform the receipt lookup.
If it fails, the helper's existing validation exception propagates unchanged;
the service does not catch or translate it into an application result or
generic infrastructure error, constructs no recovery `CreationReceiptKey`, and
performs no fresh-UoW creation-receipt lookup.

`recover_creation_unique_race_winner` remains the sole recovery outcome mapper:
an identical winner yields `EXACT_REPLAY`, a conflicting winner yields
`IDEMPOTENCY_CONFLICT`, and absent or malformed winner evidence yields
`STORED_RECEIPT_INTEGRITY_FAILURE`; no internal `READY_FOR_NEW_OPERATION`
decision escapes to the caller.

The maximum is one fresh-UoW read. Write retries and ID reissuance are zero.
This recovery does not apply to allocation collisions, creation-receipt
conflicts, initial canonical-state revision/current conflicts, stale or
missing-current conflicts, mutation receipt or other Repository-operation
conflicts, authorization failures, validation failures, policy failures,
issuer failures, arbitrary integrity/DBAPI errors, generic database failures,
UoW enter or exit failures, rollback or close failures, commit failures, or
uncertain commit outcomes. No retry or receipt lookup may follow an uncertain
commit outcome.

##### Error and result boundary

The only new application-owned exception is the narrow static catch contract
`ControllerBindingUniquenessConflictError`; it is not a caller result code or
a generic application persistence hierarchy.
`PlayerCharacterApplicationError` and
`ConcurrentPlayerCharacterOperationError` are not P3-S1 symbols.

| Condition | Caller-visible result or error | Service rule |
| --- | --- | --- |
| Invalid untyped construction input | Existing `ValidationError`, `TypeError`, or `ValueError` | Service is not called; no translation |
| Corrupted typed instance | Original defensive-revalidation exception | No Repository write; no translation |
| Missing or invalid resolver binding | `CharacterOperationProtocolDecision(code=AUTHORIZATION_FAILED)` | No initial UoW for unresolved authority |
| Stored authority mismatch | `AUTHORIZATION_FAILED` | Reject before private result disclosure |
| Exact receipt replay | Stored `CreationSuccessResult` | No issuer, policy, write, or commit |
| Same key, changed command | `IDEMPOTENCY_CONFLICT` | Return existing decision unchanged |
| Malformed/inconsistent receipt | `STORED_RECEIPT_INTEGRITY_FAILURE` | Disclose no stored result |
| Creation policy or complete-record rejection | Original validation/domain exception | Preserve the owning authority; no receipt or translation |
| Proven binding-insert loser raising the narrow contract at the exact add call | Exact stored success for `EXACT_REPLAY`, otherwise the existing protocol decision | Only the one fresh-UoW sequence above |
| Narrow contract raised at any unapproved operation or later boundary | Original exception | Propagate; do not enter recovery |
| ID allocation collision | Original `PlayerCharacterRepositoryConflictError` | Roll back; no second ID |
| Initial-row or receipt conflict | Original `PlayerCharacterRepositoryConflictError` | Roll back; no recovery |
| Stored-record integrity failure | Original `PlayerCharacterStoredRecordIntegrityError` | Roll back/close; no translation |
| Other Repository/DB operation failure | Original sanitized `PlayerCharacterRepositoryError` | Roll back/close; no broad translation |
| Cancellation | Original `asyncio.CancelledError` or other cancellation `BaseException` | Do not catch, translate, or retry |
| Controlled failure before `AsyncSession.commit` begins | Original exception | Roll back/close; claim no durable rows only to the extent Phase 2 evidence supports |
| Commit exception with uncertain durability | Original exception; outcome explicitly unknown | No recovery read, success, or replay claim |

Infrastructure adapters may retain underlying database exceptions as
`__cause__`; the application service adds no translation layer and no public
surface may expose those causes. Callers own every retry decision outside the
single narrow winner-recovery read. Cancellation never triggers transparent
retry. Uncertain-COMMIT recovery is unsupported and exactly-once execution is
not claimed.

##### P3-S1 test and verification boundary

`tests/unit/test_player_character_service.py` must use strict fakes and
fail-if-called spies to prove:

- the application service source imports only
  `application.ports.ControllerBindingUniquenessConflictError` for this
  recovery and contains no application-to-infrastructure import;
- `PlayerCharacterControllerBindingConflictError` is statically catchable
  through both `ControllerBindingUniquenessConflictError` and the existing
  shared `PlayerCharacterRepositoryConflictError`;
- the existing shared error itself is neither an instance nor a subclass of
  the narrow application contract;
- exact first-execution order and one commit;
- exact replay with no issuer, policy, write, or commit;
- changed-payload conflict without stored-result disclosure;
- unresolved/invalid controller authority opens no initial UoW;
- structural and defensive validation ordering;
- only the exact `controller_bindings.add` catch boundary enters recovery;
- a narrow typed exception raised from allocation, initial-state, receipt, a
  later Repository operation, or any other unapproved boundary propagates
  unchanged and enters no recovery;
- a focused recovery-boundary case enters through
  `PlayerCharacterService.create` with a normally constructed typed
  `PlayerCharacterOperationId`; the strict original-UoW
  `controller_bindings.add` fake uses the existing `object.__setattr__`
  actual-state corruption convention on that retained instance immediately
  before raising the exact supported same-binding uniqueness
  `ControllerBindingUniquenessConflictError`.
  The original UoW must exit through its existing failed-UoW path, and the one
  permitted fresh UoW must reauthorize and lock the binding before its second
  direct
  `revalidate_player_character_model(operation_id, PlayerCharacterOperationId)`
  call rejects the now-corrupted typed ID. The original helper exception must
  propagate untranslated before recovery `CreationReceiptKey` construction,
  before `recover_creation_unique_race_winner`, and before the fresh-UoW
  `creation_receipts.get`. Following the existing receipt-lookup collection
  convention, that fresh recovery Repository's `lookups` collection must be
  exactly `[]`; this assertion is scoped only to the recovery Repository and
  makes no zero-lookup claim about any earlier normal-path Repository. Because
  the ID is validly typed on service entry and is corrupted only by the
  exact-conflict fake, constructor rejection or the normal-path revalidation
  cannot satisfy this case;
- original exception and cancellation propagation;
- no success before commit;
- commit and uncertain-commit failures propagate and enter no recovery or
  receipt lookup;
- failed initial UoW rollback, close, disposal, and non-reuse occur before
  construction or entry of the different recovery UoW;
- at most one fresh recovery UoW is entered;
- the one exact binding-add recovery with distinct UoW identities; and
- no reissue, write retry, broad conflict catch, or second recovery attempt.

`tests/integration/test_mysql_player_character_service.py` must use the real
MySQL adapters and `SqlAlchemyUnitOfWork` to prove:

- one normal creation durably publishes exactly one binding, allocation,
  revision, current row, and creation receipt;
- a real controller-binding duplicate emits
  `PlayerCharacterControllerBindingConflictError`, which satisfies both the
  narrow application contract and the existing shared infrastructure
  conflict;
- allocation, initial revision/current, creation-receipt, mutation-receipt,
  stale-current, and other relevant Repository conflicts continue to emit or
  satisfy only their existing shared boundary and never the narrow contract;
- the real binding-add uniqueness race alone may enter the service's one
  fresh-UoW recovery;
- fresh-session reload and exact replay return the same safe result without a
  second mutation;
- changed payload leaves row counts unchanged; and
- a controlled pre-COMMIT failure returns no success, publishes no partial
  creation rows to a fresh session, and permits a later fresh invocation.

Existing Phase 1 and Phase 2 tests remain unchanged regression evidence.
Cancellation needs no duplicate real-database test because Phase 2 already
proves real UoW cancellation rollback.

The separately authorized P3-S1 implementation was required to run
`git diff --check`, `compileall`, the new focused unit test, focused existing
player-character regressions, the new real-MySQL service test, Alembic
heads/history sanity checks, and the repository Quick, Offline, MySQL, and Full
verification modes. It was prohibited from enabling a live Provider/model call
or adding/installing a dependency; the approved implementation satisfied this
historical verification gate.

##### Binary P3-S1 acceptance criteria

P3-S1 was acceptable only if all were true; the approved implementation
satisfied these historical acceptance gates:

1. changed paths remain within the exact budget above;
2. the four previously approved and two amendment-authorized public production
   symbols are present, and no generic error hierarchy or second application
   conflict contract exists;
3. typed construction and every existing validation, protocol, policy,
   Repository, adapter, and UoW authority are reused rather than recreated;
4. an unknown or untrusted principal can never become accepted merely because
   no registry row exists;
5. receipt evaluation precedes issuance, exact replay never issues another ID,
   and allocation collision never reissues;
6. first execution writes allocation, initial state, and receipt before one
   service-owned commit and returns success only afterward;
7. replay, changed-payload conflict, validation failure, domain rejection,
   infrastructure failure, cancellation, and controlled pre-COMMIT failure
   perform no unauthorized commit or success disclosure;
8. only the binding-specific subtype raised at the exact controller-binding
   insertion call may use one fresh UoW; the shared conflict and every unrelated
   conflict remain outside the narrow contract, the failed session is never
   reused, and every other retry count is zero;
9. uncertain commit outcome remains unknown, unsupported for recovery, and
   never described as exactly once;
10. focused, regression, MySQL, Alembic, Offline, Quick, and Full verification
    required by the P3-S1 implementation task passed without Provider access;
11. canonical documentation synchronization and independent implementation
    review are complete before any completion or commit request; and
12. API, frontend, Demo, Run, Provider, narrative, content, gameplay, mutation,
    owned-read/projection, and normal production composition remain untouched.

Explicit P3-S1 exclusions are API schemas/routes and public error mapping,
frontend/profile UI, Demo composition, Run/story-line behavior, Provider,
narrative, content, gameplay, mutation orchestration, public read/projection,
account-system design, production resolver/issuer selection, auto-binding,
ID-collision retry, general retry, uncertain-COMMIT recovery, and exactly-once
claims.

#### P3-S2 — Canonical Mutation Application Service

Status: **Implemented and complete. P3-S2 is part of the complete Phase 3 code
candidate that received independent read-only approval with no remaining
implementation finding.**

Objective: extend the existing injectable `PlayerCharacterService` with one
canonical mutation operation that reuses the frozen Phase 1 mutation protocol
and policies plus the implemented Phase 2 repositories and UoW. The slice may
commit only an admitted canonical `RETIRE` or `FINAL_DEATH` successor, or
return the original committed safe mutation result for an exact replay. It
does not activate a public route, compose a production service, or apply a
Run/story-line continuity effect.

##### Exact P3-S2 path and symbol budget

The completed implementation stayed within the exact `4 + 2 + 3` modified-path
budget. P3-S2 added no file.

| Status | Exact path | Exact symbols added or changed | Responsibility and necessity |
| --- | --- | --- | --- |
| Modified production | `src/deviation_protocol/application/player_character_service.py` | Add `PlayerCharacterService.mutate` and private `PlayerCharacterService._recover_mutation_winner`; extend imports only. No constructor field or other public symbol is added. | Sequence trusted controller resolution, current-row lock/authorization, receipt-before-stale evaluation, one existing policy, complete successor validation, history/CAS/receipt/commit, and the single bounded winner read. This is the P3-S2 service itself. |
| Modified production | `src/deviation_protocol/application/ports.py` | Add `MutationReceiptUniquenessConflictError`. | Supply one application-owned catch identity for only the exact mutation-receipt add duplicate; the application cannot import infrastructure errors. |
| Modified production | `src/deviation_protocol/infrastructure/errors.py` | Add `PlayerCharacterMutationReceiptConflictError` as a subtype of both `PlayerCharacterRepositoryConflictError` and `MutationReceiptUniquenessConflictError`. | Preserve existing infrastructure compatibility while distinguishing only the recoverable receipt-row flush from revision, current-state, preflight, and other persistence conflicts. |
| Modified production | `src/deviation_protocol/infrastructure/repositories.py` | Import `PlayerCharacterMutationReceiptConflictError`; at only the final row-only `_flush_row` call in `SqlAlchemyPlayerCharacterMutationReceiptRepository.add`, pass `conflict_type=PlayerCharacterMutationReceiptConflictError`. The existing `_flush_row` signature and every other call remain unchanged. | Translate a MySQL duplicate at the precise local receipt insert that can support the bounded winner read. Existing key/result prechecks and unrelated conflicts remain shared and unrecoverable. |
| Modified unit test | `tests/unit/test_player_character_service.py` | Extend the existing strict service fakes and add P3-S2 tests; no production test helper. | Prove deterministic application ordering, result/error behavior, disposal, precise exception provenance, bounded recovery, and retry prohibitions without a database. |
| Modified MySQL test | `tests/integration/test_mysql_player_character_service.py` | Extend the existing service integration fixture/tests for mutation; no new fixture module. | Prove real atomic persistence, locked concurrency/CAS, exact receipt-flush classification, rollback, reload, and replay over the implemented adapters/UoW. |
| Modified documentation | `PLANS.md` | Correct the then-current baseline/status and summarize the P3-S2 boundary. | Own current project status and roadmap placement. |
| Modified documentation | `docs/architecture.md` | Record the service, transaction, CAS, conflict, and exclusion boundaries. | Keep architecture and authority direction synchronized. |
| Modified documentation | `docs/structured_player_character_implementation_plan.md` | Record the exact P3-S2 contract, inventory, gate, and acceptance allocation. | Preserve the accepted implementation boundary. |

Production maximum is four paths, test maximum is two paths, documentation
maximum is three paths, and dependencies/schema/ORM/migration/UoW paths have a
maximum of zero. No edit to
`application/player_character_operations.py`, domain models or policies,
`infrastructure/player_character_persistence.py`, `orm_models.py`,
`unit_of_work.py`, migration `20260728_0004`, package exports, or any other
path is authorized. If implementation requires another path, it must stop and
return to a separately reviewed planning amendment.

##### Existing authority and exact service contract

P3-S2 must reuse without modification:

- `RequestPrincipal`, `ControllerBindingResolver`, `UnitOfWorkFactory`, and
  the existing service clock/UoW construction;
- `CharacterMutationCommand`, `MutationReceiptKey`,
  `MutationSuccessResult`, `MutationCommandResult`,
  `CharacterOperationProtocolDecision`, `CharacterOperationProtocolCode`,
  `mutation_fingerprint`, `evaluate_mutation_receipt_protocol`,
  `evaluate_mutation_policy`, `build_mutation_success_receipt`, and
  `recover_mutation_unique_race_winner`;
- `PlayerCharacterOperationId`, `PlayerCharacterRevision`,
  `CanonicalPlayerCharacter`, `revalidate_player_character_model`, and
  `validate_canonical_player_character`;
- the existing `PlayerCharacterPolicyDecision` and
  `PlayerCharacterPolicyCode` values, including unavailable-policy denials;
- `PlayerCharacterRepository.append_revision`,
  `PlayerCharacterRepository.compare_and_swap_current`,
  `PlayerCharacterMutationReceiptRepository.get/add`, and the existing
  current-row lock/reconstruction;
- `SqlAlchemyUnitOfWork` rollback/close behavior; and
- the existing shared repository and stored-record integrity exceptions.

The exact added application operation is:

```python
async def mutate(
    self,
    principal: RequestPrincipal,
    *,
    operation_id: PlayerCharacterOperationId,
    command: CharacterMutationCommand,
) -> (
    MutationSuccessResult
    | PlayerCharacterPolicyDecision
    | CharacterOperationProtocolDecision
):
    ...
```

`READY_FOR_NEW_OPERATION` is internal control flow and must never escape.
There is no new command, result, policy, repository, UoW, clock, controller,
exception hierarchy, or public DTO. The only new public production symbols are
`PlayerCharacterService.mutate`,
`application.ports.MutationReceiptUniquenessConflictError`, and
`infrastructure.errors.PlayerCharacterMutationReceiptConflictError`.
`_recover_mutation_winner` is private. No generic concurrency error or generic
retry abstraction is authorized.

Trusted-controller authority remains the injected
`ControllerBindingResolver`. The principal is never a binding by itself.
Resolution occurs once before the initial UoW. `None` or an invalid returned
binding produces the mutation-namespace `AUTHORIZATION_FAILED` decision and
opens no initial UoW; resolver exceptions propagate unchanged. Recovery may
re-resolve exactly once in its one fresh UoW before Repository SQL, must obtain
the same exact valid binding, and may never auto-bind, copy
`principal.player_id`, or infer authority from character persistence.

##### Exact initial-UoW transaction and validation order

The method must perform this order exactly:

1. Receive an already constructed typed principal, operation ID, and mutation
   command.
2. Resolve and defensively revalidate the trusted controller binding. Return
   mutation-namespace `AUTHORIZATION_FAILED` on an absent or invalid binding.
3. Construct and enter exactly one initial UoW.
4. Use only the typed command's `target_player_character_id` as the lock
   address and call `player_characters.get_for_update`. This routing read
   grants no authority. If no current record exists, return
   `AUTHORIZATION_FAILED`, disclosing neither existence detail nor receipt.
5. Defensively validate the reconstructed complete current record, then
   compare its exact stored `controller_binding` with the resolved binding.
   On mismatch, return `AUTHORIZATION_FAILED` before any receipt lookup or
   success disclosure.
6. Directly call
   `revalidate_player_character_model(command, CharacterMutationCommand)` and
   then
   `revalidate_player_character_model(operation_id, PlayerCharacterOperationId)`.
   Original validation exceptions propagate unchanged. If the validated
   expected revision has no signed-64-bit successor, return the existing
   mutation-namespace `REVISION_EXHAUSTED` decision before receipt-key
   construction, lookup, policy, or write.
7. Only after operation-ID validation succeeds, construct the exact
   `MutationReceiptKey(player_character_id,
   player-character.mutate/v1, operation_id)` and read it once through
   `mutation_receipts.get`.
8. Call `evaluate_mutation_receipt_protocol` with the already-read value
   supplied by an exact-key synchronous callback. This existing authority
   revalidates the command, computes the canonical fingerprint, evaluates an
   immutable receipt before current-state stale-revision rejection, and
   validates exact target/result/contract/reference semantics. The
   successor-capacity rejection in step 6 remains earlier than both fingerprint
   construction and receipt lookup.
9. On `EXACT_REPLAY`, type-check and return only the stored
   `MutationSuccessResult`. Return every other non-ready protocol decision,
   including `IDEMPOTENCY_CONFLICT`, `STORED_RECEIPT_INTEGRITY_FAILURE`,
   `STALE_REVISION`, and `REVISION_EXHAUSTED`, unchanged.
10. Only for `READY_FOR_NEW_OPERATION`, rely on the evaluator's exact
    expected-revision/target checks and call `evaluate_mutation_policy` once.
    That existing dispatcher first validates the exact target contract and
    applicable reference, then invokes exactly one of the four existing
    independent mutation policies. No service-owned policy is permitted.
11. Return a rejected `PlayerCharacterPolicyDecision` unchanged. It creates no
    success receipt and performs no history append, CAS, or commit.
12. For an accepted decision, require a resulting record and call
    `validate_canonical_player_character` on that complete detached successor.
    The successor must retain the exact character ID, controller binding, and
    contract version; have the command's expected revision as provenance
    predecessor; advance exactly once; and carry the exact accepted mutation
    kind. Any mismatch fails closed with the original validation error or a
    `ValueError`, not a repaired candidate.
13. Call `mutation_fingerprint` over the validated command and operation ID.
    Construct the existing success result and receipt. `RETIRE` maps exactly
    to `MutationCommandResult.RETIRED`; `FINAL_DEATH` maps exactly to
    `MutationCommandResult.DECEASED`. No accepted result may be synthesized for
    `REACTIVATE` or `AUTHORIZED_CONTINUITY_RETURN`; an impossible accepted
    decision fails closed.
14. Read the existing service clock exactly once for this new operation and
    normalize its timezone-aware value through `_created_at`. Replay and
    denial do not read the clock.
15. Call `player_characters.append_revision(successor, created_at=...)`.
16. Call `player_characters.compare_and_swap_current(successor,
    expected_revision=current.record_revision.value, created_at=...)`.
17. If CAS returns `False`, return the existing mutation-namespace
    `STALE_REVISION` decision immediately. Do not add a receipt or commit.
18. If CAS returns `True`, call `mutation_receipts.add(receipt,
    created_at=...)`. The narrow
    `MutationReceiptUniquenessConflictError` catch is permitted only
    immediately around this awaited call and only for the recovery protocol
    below.
19. Call `uow.commit()` exactly once.
20. Return the new `MutationSuccessResult` only after `commit()` returns.

The initial UoW owns every normal mutation read and write. Repository methods
may issue SQL and flush but never commit. `PlayerCharacterService` owns the one
explicit new-operation commit. `SqlAlchemyUnitOfWork.__aexit__` must roll back
and close every replay, denial, stale, CAS-false, validation, policy,
persistence, cancellation, controlled pre-COMMIT, and commit-exception path
that has not completed its successful commit. No failed or merely
uncommitted UoW may be reused.

Commit is the sole boundary that turns a new operation into a reported
success. Exact replay is not a second mutation success boundary; it returns
evidence of an earlier committed success and therefore performs no policy
evaluation, history append, current-state mutation, receipt add, or commit.

##### Exact result, denial, stale, and failure semantics

| Condition | Exact caller-visible behavior | Transaction rule |
| --- | --- | --- |
| Newly accepted mutation | Existing `MutationSuccessResult` | Return only after one successful commit |
| Compatible exact replay, including after later revisions | Original stored `MutationSuccessResult` | No policy, write, receipt add, or commit; read UoW exits uncommitted |
| Missing character or controller mismatch | `CharacterOperationProtocolDecision(MUTATE_V1, AUTHORIZATION_FAILED)` | Same safe outcome; no receipt lookup or disclosure |
| Missing/invalid trusted resolver binding | `AUTHORIZATION_FAILED` | No initial UoW |
| Invalid untyped construction input | Existing constructor `ValidationError`, `TypeError`, or `ValueError` | Service is not called |
| Corrupted typed command, operation ID, or current record | Original defensive validation exception | No translation, success, or recovery |
| Unrepresentable revision successor | Existing `REVISION_EXHAUSTED` protocol decision | Before receipt key/lookup and all writes |
| Same operation ID with incompatible command/result binding after the pre-receipt gates succeed for a valid non-exhausted request | Existing `IDEMPOTENCY_CONFLICT` protocol decision | Receipt-before-current-state-stale; no policy/write/commit |
| Malformed or inconsistent stored receipt | Existing `STORED_RECEIPT_INTEGRITY_FAILURE`, or the Repository's original stored-record integrity exception | No stored success disclosure |
| Initially stale expected revision | Existing `STALE_REVISION` protocol decision | Receipt evaluated first; no policy/write/commit |
| Applicable-reference or target-contract mismatch on a new operation | Existing unchanged `PlayerCharacterPolicyDecision(code=APPLICABLE_REFERENCE_MISMATCH)` | The selected existing policy rejects before candidate construction |
| Existing policy denial | Exact unchanged `PlayerCharacterPolicyDecision` | No history/CAS/receipt/commit |
| `compare_and_swap_current(...) == False` | Existing `CharacterOperationProtocolDecision(MUTATE_V1, STALE_REVISION)` | Normal UoW exit rolls back appended history; no receipt, commit, or recovery |
| Exact local mutation-receipt flush raises the narrow contract | Bounded recovery result below | Failed UoW fully exits first |
| Existing receipt precheck, revision, current-state, or any unrelated shared conflict | Original `PlayerCharacterRepositoryConflictError` object | Propagate unchanged; no recovery |
| Other Repository or stored-record failure | Original sanitized Repository/integrity exception | Propagate unchanged; rollback/close |
| Clock, policy, result construction, or complete-candidate failure | Original exception | Propagate unchanged; rollback/close |
| Cancellation | Original cancellation `BaseException` | Never catch, translate, or retry |
| Controlled failure before commit starts | Original exception | Roll back/close; report no success |
| Commit failure, including uncertain durability | Original exception; outcome remains unknown | No receipt read, recovery, success, or exactly-once claim |

CAS false is the one exact service-level optimistic-concurrency outcome. The
already-flushed history row is transaction-local and is removed by normal UoW
exit. The service must not raise a new CAS exception, reopen a UoW, repeat the
policy, reuse the detached successor, rerun CAS, or recover from a receipt.
The caller may make a later independent decision after a fresh read; P3-S2
itself performs no retry.

##### Exact mutation-receipt conflict translation and recovery

Repository evidence establishes two mutation-receipt uniqueness backstops:
the exact operation primary key
`(player_character_id, operation_namespace, operation_id)` and
`uq_spc_mutation_receipts_result_revision
(player_character_id, resulting_revision)`. The normal P3-S2
`get_for_update` workflow serializes compliant service writers, so an insert
race should not be the normal same-service path: a waiting duplicate normally
reloads the committed current state and receipt, then returns replay or stale
before mutation. The constraints remain authoritative defensive backstops,
however, and a duplicate recognized at the exact row-only mutation-receipt
flush is sufficiently local to support a read-only winner check.

The application-owned contract is exactly:

```python
class MutationReceiptUniquenessConflictError(RuntimeError):
    """Only the approved mutation-receipt add uniqueness race."""
```

The infrastructure concrete type is exactly:

```python
class PlayerCharacterMutationReceiptConflictError(
    PlayerCharacterRepositoryConflictError,
    MutationReceiptUniquenessConflictError,
):
    """A duplicate at the exact mutation-receipt add flush."""
```

The shared `PlayerCharacterRepositoryConflictError` must not inherit or
implement the narrow contract. The existing direct key/result prechecks inside
`SqlAlchemyPlayerCharacterMutationReceiptRepository.add` continue to raise the
shared type. Only its final
`await self._flush_row(row, conflict_message=...,
conflict_type=PlayerCharacterMutationReceiptConflictError)` may select the
narrow subtype. `_is_mysql_duplicate_key`, exception chaining, `_flush_row`
defaults, every other flush site, and all messages remain otherwise unchanged.

Recovery is authorized only by the conjunction of:

1. `MutationReceiptUniquenessConflictError` was caught immediately around the
   exact awaited `mutation_receipts.add` call;
2. the service recorded that exact exception object and re-raised it through
   the initial UoW;
3. the initial UoW fully exited, rolled back, closed, and was discarded; and
4. the outer handler observed the same exception object, not merely the same
   type.

If `__aexit__` suppresses the recorded exception, the original recorded object
must be re-raised fail-closed without constructing a recovery UoW. If UoW
entry, exit, rollback, close, commit, or another operation raises a different
same-type object, that different exception propagates unchanged and recovery
is forbidden.

Once and only once after those conditions, `_recover_mutation_winner` may:

1. construct and enter one different fresh UoW;
2. re-resolve and defensively revalidate the principal's binding before the
   fresh UoW's first Repository SQL, requiring equality with the initial
   trusted binding;
3. lock/reconstruct the command target through
   `player_characters.get_for_update`, validate the complete current record,
   and authorize its exact stored controller binding;
4. directly revalidate `operation_id` as
   `PlayerCharacterOperationId` again;
5. only after that succeeds, construct the exact mutation receipt key and read
   it once through the fresh UoW;
6. call `recover_mutation_unique_race_winner` with
   `losing_transaction_rolled_back=True`, the reauthorized binding, recovered
   current record, validated operation ID and original command, and the
   already-read exact-key receipt; and
7. return the stored `MutationSuccessResult` only for `EXACT_REPLAY`, otherwise
   return the helper's decision unchanged.

A compatible durable receipt therefore returns only the already committed
winner. The same key with incompatible command/result binding returns the
frozen `IDEMPOTENCY_CONFLICT`. A missing receipt, a current record that cannot
prove the winner, or other invalid recovery evidence must fail closed as
`STORED_RECEIPT_INTEGRITY_FAILURE`, `AUTHORIZATION_FAILED`, or the original
integrity/validation exception. Recovery performs no policy call, history
append, CAS, receipt add, commit, or other write. It has no third UoW and no
second recovery attempt. Before any recovery outcome reaches the caller, the
fresh read-only UoW must itself exit uncommitted, roll back its read
transaction, close, and be discarded.

No recovery is permitted for CAS false; shared receipt prechecks; history,
current-row, allocation, creation-receipt, or controller-binding conflicts;
authorization or validation failure; policy denial; arbitrary DBAPI,
Repository, UoW lifecycle, cancellation, rollback/close, or commit failure; or
uncertain commit durability. There is no generic retry, delayed retry, state
reuse, commit retry, uncertain-commit read, or exactly-once claim. All
unrelated exception identities and causes propagate under their existing
boundaries.

##### P3-S2 acceptance-to-test allocation

Evidence must be non-redundant: deterministic orchestration belongs in the
existing unit service file; SQL atomicity, row locks, real CAS, constraint
translation, and fresh-session durability belong in the existing MySQL
service file. Existing operation, policy, Repository, UoW, mapping, and
migration tests remain regression evidence and are not copied.

| Acceptance behavior | Unit service evidence | MySQL service evidence |
| --- | --- | --- |
| Successful canonical mutation and committed return | Exact event order; result inaccessible before the commit spy returns; one clock and one commit | Real `RETIRE` and `FINAL_DEATH` representatives commit exact history/current/receipt and reload the safe result |
| Ownership and missing character | Same `AUTHORIZATION_FAILED`; no receipt/policy/write/commit spies | Fresh-session row counts/state prove no mutation or disclosure side effect |
| Invalid command and operation identity | Original validation exception; key constructor and receipt lookup are fail-if-called | None; deterministic validation is not duplicated |
| Receipt before stale | A stale command with a stored compatible receipt returns replay; incompatible receipt returns idempotency conflict; no policy | Real replay after a later committed revision returns the earlier stored result |
| Compatible replay without second mutation | No policy/history/CAS/add/commit/clock | Revision and receipt counts remain unchanged after fresh-service replay |
| Incompatible operation-ID reuse after pre-receipt gates | Exact `IDEMPOTENCY_CONFLICT` for a valid non-exhausted request, no stored result/write | Fresh-session counts remain unchanged |
| Initially stale expected revision | Exact `STALE_REVISION` after one receipt lookup and before policy | Locked current state and counts remain unchanged |
| Unchanged policy denial | The exact same `PlayerCharacterPolicyDecision` object is returned; all write/commit spies fail if called | Representative unavailable transition leaves durable state unchanged |
| History/current/receipt atomicity | Ordered append, CAS, add, one commit | Fresh sessions see all three or none; before/after fingerprints reconstruct |
| CAS false | Exact `STALE_REVISION`; appended fake history rolled back by UoW exit; no receipt, commit, recovery, or second UoW | Existing real Repository CAS-loser evidence remains authoritative; new locked service concurrency proves production writers normally serialize before CAS |
| Supported receipt uniqueness conflict | Static subtype relationships; only explicitly labelled narrow receipt-add fault injection with same-object provenance enters recovery | A synthetic direct-repository, out-of-topology row-only flush race proves MySQL constraint translation; it is not production-service reachability evidence |
| Compatible uniqueness recovery | Fault-injected original UoW exit/disposal precedes one fresh UoW; helper returns only stored winner; no recovery commit, write, retry, or third UoW | Normal locked duplicate service calls serialize to one mutation plus replay, demonstrating why the defensive flush recovery is not the current production path |
| Incompatible/missing/invalid recovery evidence | `IDEMPOTENCY_CONFLICT` for incompatible same-key reuse; missing/invalid evidence fails closed; no third UoW | Exact constraint and reconstruction behavior only; helper outcomes remain unit-owned |
| Rollback for every pre-commit failure | Parameterized failure at validation, policy, history, CAS exception/false, receipt add, and before commit; no success | Controlled failures after history and after CAS publish no partial row to a fresh session |
| Commit failure | Original exception, no recovery lookup or success | Controlled commit failure publishes no claimed success; only safe pre-COMMIT failure may assert zero durable rows |
| Cancellation and original exception propagation | Parameterized `Exception`/`BaseException` identity checks at resolver, UoW, repositories, policy, and commit | Existing real UoW cancellation evidence is reused, not duplicated |
| No generic retry or uncertain-commit success | Factory/operation call counts prove one initial UoW, zero or one recovery UoW only for exact receipt add, and no commit retry | Locked concurrency produces no duplicate mutation; no uncertain-commit test claims recovery |
| No later-slice behavior | Fail-if-called/source-boundary assertions cover projection/composition/API/Run/Provider absence | No Provider, browser, server, network, API, Demo, or Run fixture is used |

MySQL tests may remain skipped when Offline mode supplies no test database URL.
They must use only the existing approved MySQL test fixture and may not require
a Provider, browser, server, public route, external network operation, or live
model call.

##### Binary P3-S2 acceptance boundary and gate

P3-S2 implementation may be accepted only if all of the following are true:

1. changed paths are exactly within the `4 + 2 + 3` maximum above, with no
   added file, dependency, schema, ORM, migration, UoW, or operation-helper
   change;
2. the exact `mutate` signature and only the three new public symbols above
   exist;
3. trusted controller resolution, stored-binding authorization, typed
   validation, immutable receipt evaluation, one existing policy, complete
   successor validation, Repository operations, and UoW ownership are reused
   in the exact stated order;
4. receipt evaluation precedes stale rejection and exact replay performs zero
   policy calls, writes, receipt additions, or commits;
5. a new accepted operation appends history, wins CAS, adds one receipt,
   commits once, and returns success only afterward;
6. policy denial is returned unchanged, missing/unauthorized is
   non-enumerating, validation and persistence exceptions retain their
   original boundaries, and commit failure never reports success;
7. CAS false returns exactly mutation `STALE_REVISION`, rolls back normally,
   and performs no retry or recovery;
8. only the exact mutation-receipt row flush has the narrow conflict identity;
   prechecks and every unrelated conflict retain their original shared
   identity;
9. the exact receipt-add exception object must escape the disposed failed UoW
   before at most one fresh-UoW read; compatible evidence returns only the
   winner, incompatible reuse returns idempotency conflict, and missing or
   invalid evidence fails closed;
10. no third UoW, generic/write/policy/CAS/commit retry, failed-state reuse,
    commit-failure recovery, uncertain-commit recovery, or exactly-once claim
    exists;
11. the unit and MySQL allocations above pass when later implementation
   verification is separately authorized, with MySQL permitted to skip only
   when no database URL is supplied in Offline mode; and
12. public/API/frontend/Demo/Provider/Run/narrative/scenario/content/gameplay
    work and every other excluded surface remain untouched.

The implemented P3-S2 boundary satisfies these acceptance conditions and was
included in the independently approved complete Phase 3 code candidate.

#### Completed P3-S3 and P3-S4 slices

P3-S3 implements authorized canonical `get_owned` read and explicit detached,
frozen, allowlisted self projection. Authority resolves before UnitOfWork
construction. Missing and wrong-owner characters both return `None`; stored
identity and state are revalidated. Only ID, contract version, current
revision, and lifecycle are returned. The read performs no write, lock, receipt
operation, commit, retry, or recovery. HTTP schemas, routes, and frontend
activation remain deferred.

P3-S4 constructs the canonical service in `build_default_services()` and
exposes it through `ApiServices.player_character_service`. It reuses the
established lazy `SqlAlchemyUnitOfWork` factory and existing repositories and
policies; create, mutate, and `get_owned` remain available. Composition itself
performs no UnitOfWork, SQL, ID issuance, or mutation. Supported startup fails
closed when required controller bindings are absent, and no fake or development
resolver or fake issuer is installed. Public routes and Demo parity remain
deferred.

### Phase 4 — Run and continuous-story-line binding

Minimum Run Core is implemented, independently finally approved, committed,
and pushed at `e821cd922b61868097667b12c2b64cf8089a9681`; its null-only seam is
historical. P4-S1a is complete at `748003319ececa548b68b351746afbb2d54c66bb`
and P4-S1b at `8eabf9d4c3c592ea1de50f443f1816de9a46dc8f`. P4-S1 is complete;
the internal binding remains publicly inactive.

#### P4-G0 — Minimum Run-core authority and implementation-plan freeze

Status: **documentation authority approved and closed.**

The independent read-only review returned
`STRUCTURED_PLAYER_CHARACTER_P4_G0_REVIEW_APPROVED`; its prerequisite is now
implemented and pushed at `e821cd922b61868097667b12c2b64cf8089a9681`.

P4-G0 freezes, but does not implement:

- the smallest prerequisite Run core;
- both active character/story-line cardinality directions;
- a separate trusted Session participation record;
- Run-owned transaction, CAS, receipt, and replay behavior; and
- the future exact character/reference binding seam.

The canonical prerequisite sequence, path budgets, migration-head rule,
verification, exclusions, and acceptance evidence are owned by
[Minimum Run Core Implementation Plan](minimum_run_core_implementation_plan.md).
The P4-G0 independent-review approval condition cross-references that plan's
single canonical operative verdict
`STRUCTURED_PLAYER_CHARACTER_P4_G0_REVIEW_APPROVED`; this is not a second
verdict definition.

Historical pre-implementation workflow record: P4-G0 documentation authority
was closed before Minimum Run Core implementation and did not itself authorize
that implementation. Present state: Minimum Run Core is implemented,
independently approved, committed, and pushed at
`e821cd922b61868097667b12c2b64cf8089a9681`; its Run-to-Player-Character
binding carrier was the null-only historical baseline. P4-S1a and P4-S1b
complete its internal activation, while the reserved public
`RunService.bind_player_character(...)` command remains rejected and no public
Run or gameplay behavior is active.

#### Minimum Phase 3.3 Run-core prerequisite

The completed MRC-S1 through MRC-S3 prerequisite provides stable
Run/line identity, canonical state/version, durable persistence, separate
participation, Run service/UoW ownership, receipt/replay behavior, a reserved
all-null binding envelope, and Run-aware production composition without a
public route.

The prerequisite received fresh independent review, documentation
synchronization, milestone commit, and manual push at
`e821cd922b61868097667b12c2b64cf8089a9681`. It does not itself populate a
character binding or implement the full Run Protocol.

#### P4-S1 — Canonical character and applicable-reference binding

P4-S1 has the completed minimum Run-core baseline at
`e821cd922b61868097667b12c2b64cf8089a9681` and is complete through P4-S1a
(`748003319ececa548b68b351746afbb2d54c66bb`) and P4-S1b
(`8eabf9d4c3c592ea1de50f443f1816de9a46dc8f`). No concrete defect requires
reopening it.

Scope:

- resolve trusted controller authority and obtain the canonical owned
  character/reference through the approved narrow Phase 3-owned same-UoW read
  seam;
- activate the Run-owned binding envelope with exact `PlayerCharacterId`,
  contract version, and record revision;
- enforce exactly one active character binding per line and at most one active
  line per character;
- reject second/conflicting and concurrent bindings atomically;
- activate the binding-aware fail-closed `RETIRE`/`FINAL_DEATH` guard in the
  same completed slice as successful binding, using the existing P4-S1 evidence
  seam and Player Character -> Run lock order;
- preserve exact ID/reference across scenarios and any Run-authorized
  later-world transition in the same line;
- use the Run service as the one binding transaction owner; and
- add focused domain/service/MySQL concurrency, mismatch, rollback, replay,
  and continuity tests.

P4-S1 does not expose an API, frontend, Demo behavior, public resume, general
reference-following policy, arbitrary movement, replacement, transfer, or full
world/visit execution. Later Phase 4 continuity integrations require their own
authorized slice when the owning scenario/world transition surfaces exist.

Completion criteria: the exact binding commits once or not at all; both
cardinality conflicts fail with neither subject changed; `RETIRE` and
`FINAL_DEATH` reject before any write for a current active binding and fail
closed for malformed surviving binding evidence; historical non-active
references do not count as active; same-line boundaries preserve the exact
reference; Run authority remains intact; and no Session or detached projection
becomes writable character state.

Stop conditions: the minimum prerequisite is absent or unapproved;
`GameSession` would masquerade as Run; one Run-owned transaction cannot hold
the canonical binding change; either cardinality direction lacks a database
backstop; approved Phase 3 ownership semantics cannot be preserved; a
reference change, transfer, restart/resume, replacement, or post-return rule is
required; or implementation would activate a deferred public/runtime surface.

### Phase 5 — Public projection and narrow boundary integration

Phase 5 owns public activation and is not ordinary Phase 3 runtime
composition:

| Slice | Responsibility | Prerequisite | Explicitly deferred |
| --- | --- | --- | --- |
| P5-S1 — Owned-read activation | Thin authenticated public read over the accepted detached projection | P3-S3 and P3-S4 | Create, mutation, UI |
| P5-S2 — Creation activation | Thin authenticated creation/replay route | P3-S1, P3-S4, and accepted public contract | Mutation, frontend, Demo, Run behavior |
| P5-S3 — Retirement-only controller-mutation activation | One thin authenticated retirement/replay route for an owned, active, unbound character | P3-S2, P3-S4, completed P4-S1 guard, and an independently approved [dedicated P5-S3 plan](structured_player_character_p5_s3_implementation_plan.md) | Bound-character retirement, Run ending/historicalization, final death, reactivation/return, general mutation, frontend |

No repository authority defines a P4-S2 objective. P5-S1 is completed and
published at `5955c47eac07429107b93ef85da6a055bd2044ef`. It activates only a
thin authenticated public read over the accepted detached Player Character
projection. The P5-S2 public creation/replay contract is frozen and published
at `245caff3903666fcd2dd9a318785f323117deb24`; its exact bounded normal POST
implementation was independently approved, committed, and published at
`4ba66d8f277988325795c905fdf6fd9e416d7457`. It reuses the P3 service's
controller-first authority, operation namespace, receipt replay, durable
creation family, and one admitted controller-binding-race winner recovery;
ordinary, corrupt-receipt, unsupported-recovery, and uncertain-commit failures
remain sanitized, and cancellation propagates through rollback. P5-S1 remains
unchanged. Demo has no Player Character service, route, method, or OpenAPI path,
and no frontend creation method exists. P5-S3's first, first-corrected, and
re-corrected local candidates each received `CHANGES_REQUIRED`; the later
evidence candidate was followed by the focused verdict
`P5_S3_RECEIPT_ADD_RACE_NOT_REACHABLE_UNDER_CURRENT_PRODUCTION_PATH`. The
accepted and published normal-application retirement result follows
`STRUCTURED_PLAYER_CHARACTER_P5_S3_PLAN_APPROVED`; correction validation passed
  with the canonical counts above. Its focused final independent review
  returned `STRUCTURED_PLAYER_CHARACTER_P5_S3_FOCUSED_FINAL_REVIEW_APPROVED`
  with no material scoped defect, accepting real-MySQL aggregate-lock
  serialization, replay/conflict, and one durable mutation, and fault injection
  only as bounded defensive recovery; the unreachable receipt-add race is not a
  requirement. P5-S3 was committed and published at
  `34d063e387cde69500e4dc018ff087e87f3eee74`. P5-S3 is not a current unstaged
  candidate. Phase 5 ended with P5-S3; no P5-S4 exists or has begun. Phase 8
  now owns the separately planned minimum playable-loop connection without
  reopening Phase 5. Provider work, deployment, release, and every broader
  excluded feature remain deferred.

Every Phase 5 slice must preserve current Session recovery and safe public
error envelopes, explicit allowlists, privacy, non-enumeration, detachment, and
the distinction between controller identity and player-character identity.
Profile UI, general patch, Provider protocol, frontend redesign, production
rollout, and any unadmitted mutation remain excluded.

Phase 5 stops if there is no non-development controller authority, if
`PlayerVisibleStateProjection.player_id` would change meaning, if safe recovery
requires redesign of the current client contract, or if private fields would
become public.

### Phase 6 — Subject-reference compatibility hooks

Scope:

- require explicit player-character subject references at any new
  memory/relationship/consequence boundary touched by the structured slice;
- preserve runtime/logical NPC separation; and
- add compatibility tests without replacing current memory storage.

Prerequisites: explicit separate Run-owned Session participation and owning
adjacent-system contracts.

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

### Phase 8 — Structured Player Character Run Entry and Minimum Playable Loop

Phase 8 is the currently selected planning priority. Its approved and published
planning authority is the
[Phase 8 playable-loop plan](structured_player_character_run_playable_loop_plan.md).
The original exact seven-document candidate received
`STRUCTURED_PLAYER_CHARACTER_RUN_PLAYABLE_LOOP_PLAN_REVIEW_APPROVED` and was
committed and published at `de4d8c0e35c7864948306d751a00aaf295ff77ff`.
It owns only the minimum connection from owned structured-character discovery
through authoritative Run admission and immutable character binding into the
existing Session-backed Run progression and Demo/client experience. It does not
rename, replace, complete, or import Phase 6 or Phase 7. Neither phase is a
prerequisite for the planned minimum loop: no new
memory/relationship/consequence subject fact is introduced, and Phase 7's
whole-roadmap closeout remains deferred.

Phase 8 reuses the completed P5-S1, P5-S2, and P5-S3 capabilities without
reopening them, and it preserves the current Run and Session authority. Its
approved planning authority authorizes no implementation by itself. Phase 8 is
not implemented; P8-S1 has not begun and remains separately unauthorized, and
P8-S2 through P8-S6 remain unimplemented and unauthorized. Later modifications
to the planning-authority bytes require fresh exact-byte independent review
before a separately authorized documentation commit; that commit precedes user
publication and clean published-baseline confirmation. P8-S1 may begin only
through a separate explicit implementation task after that sequence. Later
phases may add the explicitly deferred game, Provider, content, progression,
profile, and production capabilities.

## 25. File-level implementation inventory

This inventory records the completed Phase 3 scope and prospective scope for
later phases. Later-phase placement remains prospective and authorizes no edit.

### Existing Phase 1 baseline files, implemented P3-S1 additions, and proposed later additions

The following existing Phase 1 baseline files will be extended during Phase 2
where their listed responsibility applies; they are not proposed additions and
their completed Phase 1 work is not pending.

| Status | Path | Layer and purpose | Obligation | Protecting tests |
| --- | --- | --- | --- | --- |
| Existing Phase 1 baseline; extend if needed | `src/deviation_protocol/domain/player_character.py` | Domain aggregate, distinct value objects, strict field groups, lifecycle, reference, provenance | Complete canonical record, identity separation, versions, lifecycle | Existing and extended domain unit tests |
| Existing Phase 1 baseline; extend if needed | `src/deviation_protocol/domain/player_character_policies.py` | Independent pure policies for creation and each lifecycle route | Guardrail policy separation; transition/authority matrix | Existing and extended policy matrix unit tests |
| Implemented P3-S1/P3-S2 service | `src/deviation_protocol/application/player_character_service.py` | Trusted create, replay, mutation, recovery, and owned-read orchestration | Existing validation/protocol/policy reuse, atomic create/mutate, CAS-false stale outcome, bounded receipt-winner read, privacy-safe owned read | Service unit/MySQL and owned-read tests |
| Existing Phase 1 baseline; extend if needed | `src/deviation_protocol/application/player_character_operations.py` | Server-owned operation namespaces, canonical fingerprints, replay equivalence, and strict safe-result envelopes | Independently reviewable successful-receipt protocol before persistence | Existing and extended golden-vector and replay/conflict unit tests |
| Implemented P3-S3 addition | `src/deviation_protocol/application/player_character_projection.py` | Detached frozen allowlisted self projection | Privacy and non-authoritative public data | Projection/privacy and owned-read tests |
| Implemented Phase 3 ports | `src/deviation_protocol/application/ports.py` | Controller resolver, ID issuer, and narrow binding/receipt uniqueness contracts | Trusted injected boundaries without a generic persistence hierarchy | Type-relationship, provenance, and service tests |
| Implemented P3-S4 authority adapters | `src/deviation_protocol/infrastructure/player_character_authority.py` | Exact configured controller allowlist and production UUIDv4 issuer | Fail-closed authority/configuration and opaque user-information-free IDs | Composition and authority tests |
| Proposed Phase 2 Slice 1 addition | `src/deviation_protocol/infrastructure/player_character_persistence.py` | Database-independent stored-record carriers, canonical codec, and integrity validation | Exact six-family conversion boundary | Persistence codec unit tests |
| Proposed Phase 2 addition | one Phase 2 Alembic revision whose parent is actual head `20260719_0003` | Add exactly the six section 20 tables only after this amendment is independently accepted and Phase 2 separately authorized | Exact columns/types/collations, uniqueness, non-reuse, binding, revision, provenance, and distinct successful creation/mutation receipts | Migration-head/schema/upgrade tests |
| Planned minimum Run-core prerequisite | one next-head Alembic revision selected only at implementation time | Add the five Run-owned record families and all-null future binding seam frozen by the minimum Run-core plan | Run/line identity, current/revision CAS, participation, receipts, both active cardinality backstops | Run migration/service/concurrency tests |
| Existing Phase 1 baseline; extend if needed | `tests/unit/test_player_character.py` | Domain record and validation matrix | Strict complete record | Existing and extended unit matrix |
| Existing Phase 1 baseline; extend if needed | `tests/unit/test_player_character_policies.py` | Lifecycle/confirmation/authority matrix | Every state mutation | Existing and extended unit matrix |
| Existing Phase 1 baseline; extend if needed | `tests/unit/test_player_character_operations.py` | Canonical fingerprint vectors, exact replay equivalence, conflicts, and safe-result validation | Receipt protocol before schema | Existing and extended application-boundary tests |
| Proposed Phase 2 Slice 1 addition | `tests/unit/test_player_character_persistence.py` | Stored-record codec, canonical bytes, and integrity matrix | Fail-closed persistence conversion | Offline persistence unit tests |
| Proposed Phase 2 Slice 3 addition | `tests/unit/test_player_character_repositories.py` | Repository capability and failure classification matrix | Exact repository behavior without commits | Repository unit tests |
| Implemented P3-S1/P3-S2 tests | `tests/unit/test_player_character_service.py` | Creation and mutation ordering, outcomes, CAS false, rollback, exception provenance, and bounded recovery using strict fakes | Deterministic Phase 3 application behavior | Focused service unit selection |
| Implemented P3-S1/P3-S2 tests | `tests/integration/test_mysql_player_character_service.py` | Real creation/mutation service, adapter, and UoW evidence | Atomic history/current/receipt, row lock/CAS, receipt-flush conflict, rollback, reload, and replay | Existing 42-pass MySQL selection |
| Implemented P3-S3 tests | `tests/unit/test_player_character_read.py` | Owned-read privacy, validation, and read-only ordering | Non-enumeration and detached allowlisted result | Focused owned-read selection |
| Implemented P3-S4 tests | `tests/unit/test_player_character_composition.py` | Controller/issuer strictness and lazy production composition | Fail-closed startup and no composition-time work | Focused composition selection |
| Proposed Phase 2 addition | `tests/integration/test_mysql_player_character.py` | Real MySQL repositories, transactions, CAS, constraints | Persistence/atomicity | Integration tests |

The Phase 3 placement above is implemented and independently approved. The
split among later proposed application/domain additions remains `T`.
Repository convention supports domain, application, infrastructure, and test
separation, but avoiding circular dependencies and keeping policy classes
independent is more important than these filenames.

### Modification inventory

| Existing path | Purpose | Obligation | Protecting tests |
| --- | --- | --- | --- |
| `src/deviation_protocol/domain/player_character_policies.py` | P4-S1a adds only the frozen internal `PlayerCharacterPolicyCode.ACTIVE_BINDING_ATOMIC_LIFECYCLE_TRANSITION_REQUIRED` member to the existing `PlayerCharacterPolicyCode` enum, with directly relevant support only | Keep the lifecycle-guard outcome domain-owned without a duplicate, lookalike, local-string, or application-layer policy identity | Existing Player Character service and policy regression coverage |
| `src/deviation_protocol/application/ports.py` | Preserve completed Phase 2 ports and Phase 3 authority/conflict symbols | Keep binding/issuance boundaries and exact receipt-add recovery signal application-owned and separate from shared conflicts | Phase 3 type-relationship, dependency-direction, provenance, and strict fake tests |
| `src/deviation_protocol/infrastructure/orm_models.py` | Add private normalized persistence models | MySQL canonical ownership/constraints | Schema and repository tests |
| `src/deviation_protocol/infrastructure/repositories.py` | Preserve completed Phase 2/P3-S1 behavior; P3-S2 changes only the exact final mutation-receipt row flush to select `PlayerCharacterMutationReceiptConflictError` | Distinguish only a duplicate at that local receipt insert; prechecks and all other Repository conflicts remain unchanged | P3-S2 unit provenance and real MySQL row-only flush-race tests |
| `src/deviation_protocol/infrastructure/errors.py` | P3-S2 adds `PlayerCharacterMutationReceiptConflictError` with the two exact bases | Preserve shared-error compatibility without reclassifying precheck, revision, current-state, creation-receipt, or other conflicts | P3-S2 static relationship and MySQL classification tests |
| `src/deviation_protocol/infrastructure/unit_of_work.py` | Expose new repositories in one `AsyncSession` transaction | Commit/rollback ownership | UoW rollback tests |
| `tests/unit/test_repository_and_uow.py` | Cover new repository/UoW wiring and failure restoration | Existing persistence convention | Focused unit tests |
| `tests/integration/test_mysql_connection.py` | Advance expected Alembic head and assert exact new schema | Migration verification | Real MySQL schema test |
| `tests/integration/conftest.py` | Slice 4 only: add owned cleanup for the six Phase 2 families in restrictive-FK-safe order | Isolated integration cleanup | Phase 2 MySQL integration tests |
| `src/deviation_protocol/api/main.py` and `src/deviation_protocol/api/dependencies.py` | P3-S4 production composition only; Phase 5 later owns narrow public routes | Expose the canonical service without activating HTTP behavior | Composition tests |
| `tests/unit/test_session_service.py` and relevant API integration tests | Prove existing Session identity/projection is unchanged | Compatibility | Regression tests |
| Run-owned paths implemented under `docs/minimum_run_core_implementation_plan.md` and P4-S1 | Minimum prerequisite and P4-S1a/P4-S1b are complete; `RunService.bind_player_character_internal` activates the exact internal binding seam while the reserved public command remains rejected | Same-line/later-world exact-reference continuity and both active cardinality directions | Run service/integration/contract tests |
| future adjacent-system owning modules, not nameable today | Phase 6 only: accept explicit logical subject refs | Memory/NPC/consequence correctness | Compatibility/integration tests |

The Phase 3-specific rows in both tables are implemented and preserve the
independently approved boundary. P4-G0 now delegates the exact minimum
Run-core path budgets to its owning plan. The prerequisite and P4-S1 are
implemented; broader Phase 4 lifecycle, scenario, and world integration remain
deferred. P5-S1 remains a completed and published Phase 5 implementation
slice. P5-S2 is independently approved, committed, and published at
`4ba66d8f277988325795c905fdf6fd9e416d7457`; it is not deployed or Demo/
frontend-activated. P5-S3's first, first-corrected, and re-corrected
implementation candidates each received `CHANGES_REQUIRED`; the
later evidence candidate and focused not-reachable verdict preceded the
accepted implementation. It follows
  `STRUCTURED_PLAYER_CHARACTER_P5_S3_PLAN_APPROVED`. Its focused final
  independent review returned
  `STRUCTURED_PLAYER_CHARACTER_P5_S3_FOCUSED_FINAL_REVIEW_APPROVED` with no
  material scoped defect; accepted real-MySQL evidence proves aggregate-lock
  serialization, replay/conflict, and one durable mutation, while fault injection
  is bounded defensive recovery only and the unreachable receipt-add race is not
  a requirement. Correction validation passed with the canonical counts above,
  and P5-S3 was committed and published at
  `34d063e387cde69500e4dc018ff087e87f3eee74`. Phase 5 is complete at P5-S3;
  no P5-S4 exists or has begun. Phase 6 and Phase 7 remain separately allocated
  and unimplemented. Phase 8 has approved and published planning authority only;
  no Phase 8 production, test, migration, Demo, or client implementation has
  begun. P8-S1 through P8-S6 remain unimplemented and unauthorized, and Phase 8
  is not complete.

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
| `active -> retired` | Policy + service | Explicit bound confirmation; unbound behavior is preserved, while P4-S1 current active binding rejects with `ACTIVE_BINDING_ATOMIC_LIFECYCLE_TRANSITION_REQUIRED` before any write |
| `retired -> active` | Policy + service | Explicit confirmation plus authorized binding evidence |
| `active/retired -> deceased` | Policy + service | Trusted event authority only; unbound behavior is preserved, while P4-S1 current active binding rejects `FINAL_DEATH` with `ACTIVE_BINDING_ATOMIC_LIFECYCLE_TRANSITION_REQUIRED` before any write |
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
| Second active story line for one character | Run application/service + persistence/integration | A character already bound to one active line rejects a different active line with neither aggregate changed; historical non-active references do not count |
| Concurrent conflicting line bindings | Run persistence/integration | Competing transactions for one story line produce exactly one committed active character binding; the loser rejects and no split binding state remains |
| Conflicting Session participation | Run application/service + persistence/integration | A separate immutable record permits multiple Sessions on one Run but prevents one Session from being routed to conflicting Runs; no `game_sessions` Run/binding columns or inferred backfill |
| Scenario continuity | Run integration/end-to-end | Exact ID and reference preserved |
| Later-world continuity | Run integration/end-to-end | Run selects world; exact ID/reference preserved |
| Unauthorized reference advance | Domain + Run integration | Rejected before boundary mutation |
| Unauthorized reference rollback/substitution | Domain + Run integration | Rejected even with same character ID |
| Creation receipt scope before ID | Application unit + persistence/integration | Receipt key is exact controller binding + `player-character.create/v1` + operation ID; replay occurs before allocation and returns the originally stored safe result |
| Mutation receipt scope | Application unit + persistence/integration | Receipt key is exact character ID + `player-character.mutate/v1` + operation ID; current controller binding is authorized before disclosure |
| Fingerprint canonicalization | Application unit golden vectors | Exact namespace/command/contract/declaration or target/revision/body/evidence fields use stable UTF-8 canonical JSON while preserving omission, absence, undecided, ordered data, and meaningful text |
| Duplicate exact creation operation | Service + persistence | Original safe result returned; one identity allocation/current record/history/receipt |
| Duplicate exact mutation operation after later revisions | Service + persistence | Original stored safe result returned without reconstructing from current state; no second revision/history entry |
| Canonical state-record fingerprint | Persistence unit | Deterministic canonical record serialization yields stable SHA-256 bytes for logically identical normalized revisions, changes for authoritative state changes, and remains distinct from unchanged Phase 1 `CharacterOperationFingerprint` semantics |
| Receipt/history cross-record integrity | Persistence/integration | Creation receipt binds its exact revision-1 result record; each mutation receipt binds its exact before/after records; parameterized corruption tests detect and fail closed on cross-character/controller substitution, missing history, extra history where prohibited, contradictory history, broken continuity, declaration/provenance/lifecycle/mutation-metadata mismatch, authority mismatch where authority applies, source-reference mismatch where source reference applies, and before/after/result fingerprint mismatch at both write and reconstruction/read boundaries before replay or disclosure |
| Conflicting replay after operation-specific pre-receipt gates | Service + persistence | A valid non-exhausted request using the same exact scope key with different fingerprint, command, target/result binding, or result-schema version conflicts; no allocation or mutation. Maximum-revision mutation requests reject before fingerprint or receipt evaluation as frozen above |
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
| Exact Phase 2 schema | Migration/integration | All six and only the six section 20 tables have the frozen exact columns, types, nullability, keys, indexes, checks, `ascii_bin` identity columns, restrictive FKs, and timestamp behavior; the inspected exact index inventory includes `ix_spc_revisions_controller_binding (controller_binding)` and `ix_spc_mutation_receipts_result_revision (result_player_character_id, resulting_revision)`, with the latter satisfying both mutation-receipt result-side child FKs; no undeclared MySQL-generated child-side index exists |
| Every Phase 2 record family round trip | Persistence/integration | Binding, allocation, current, history, creation receipt, and mutation receipt survive commit and strict reload without byte or meaning changes |
| Case-sensitive maximum opaque identities | Persistence/integration | Distinct case variants coexist; every applicable 128-character value round-trips exactly; 129-character, malformed, trimmed, folded, normalized, or reinterpreted input rejects |
| Aggregate declaration byte boundary | Domain + persistence/integration | Exact canonical UTF-8 declaration envelopes at 65,536 bytes commit/reload; 65,537 bytes reject before any insert despite MySQL character counts |
| Fixed 65-feature persistence | Persistence/integration | The accepted fixed 65-feature declaration commits and reloads with order, content, authority, and count unchanged and no item-count ceiling |
| Malformed current/history record | Persistence/integration | Invalid JSON/canonical bytes, cross-column mismatch, unknown field, invalid declaration envelope, or impossible provenance fails closed before any domain object or private data is returned |
| Malformed receipt/stored result | Persistence/integration | Invalid canonical receipt, key/fingerprint/result mismatch, impossible semantic result, or oversize blob is an integrity failure before stored-success disclosure |
| Deterministic fingerprint storage | Application + persistence/integration | `BINARY(32)` round-trips the exact Phase 1 lowercase command digest and the internal raw canonical state-record digest; neither changes Phase 1 public receipt construction or replay semantics |
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
| Development principal is treated as production controller authority | Reject it; production composition uses only the exact configured allowlist |
| `GameSession` is promoted to Run | Stop Phase 4 until a real Run aggregate exists |
| Applicable reference silently follows current revision | No mutation route; exact-match preservation; stop for any change request |
| Identifier becomes reusable after deletion/downgrade | Append-only allocation/no delete; stop destructive downgrade after issuance |
| JSON groups permit unbounded or unknown canonical fields | Strict bounded domain schema; stop where exact representation requires product choice |
| Optional declaration states collapse or preference defaults silently | Closed state wrapper, exhaustive unit/persistence tests, and a Phase 1 stop if omission, explicit absence, intentionally undecided, or selected preference cannot remain distinct |
| External or inferred material settles player-controlled inner state | Separate authority types and negative domain/service/contract tests; stop any server, Provider, narration, NPC, summary, event, memory, or consequence inference path |
| Player declaration is accepted as an external fact | Subjective declaration types cannot satisfy world/NPC/consequence authority; reject before canonical commit |
| Story-line integration violates either active cardinality direction | Enforce one active character per bound line and at most one active line per character in the Run service transaction and database backstops; historical non-active references do not count |
| Post-ending behavior is inferred | Preserve immutable history and deterministic active-to-historical ending effect; stop rather than select restart/resume, successor/replacement, transfer, or return behavior |
| Controller-binding registry implies transfer/recovery behavior | No binding mutation API; classify new behavior as product decision |
| Shared Repository conflict is mistaken for the binding-only race | Keep `PlayerCharacterRepositoryConflictError` outside the narrow application contract; emit the binding-specific compatible subtype only from the exact binding-row duplicate flush; require both type and call-site provenance for recovery |
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

- any post-first-slice history compaction or physical-schema evolution; the
  exact frozen six-table Phase 2 design in section 20 selects neither;
- exact structured field lengths, vocabularies, localization, custom-value
  representation, and profile/activation requiredness;
- defaulting and update workflows for narration preferences;
- character/profile creation drafts and UI;
- account/controller character limits and how many distinct canonical
  character records one controller may keep active; active line occupancy is
  already frozen separately;
- controller transfer, shared control, delegation, recovery, unbinding, and
  account-change behavior;
- restart/resume, Session reassignment, successor/replacement,
  post-retirement/death/return binding, cross-Run behavior beyond the frozen
  active-binding exclusivity, and arbitrary movement between unrelated
  Runs/story lines/accounts;
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

The four-document ordering amendment was approved under
`STRUCTURED_PLAYER_CHARACTER_PHASE_2_PLAN_APPROVED`, committed, and pushed at
`afa9f9c21900eebd4e08d65071a26903e83d4a65`. Its exact-candidate review
verified that this plan:

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
9. preserves the frozen rules that each bound continuous story line has
   exactly one active player-character binding and each character belongs to
   at most one active line, rejects either conflict atomically, retains
   historical non-active references, and selects no replacement behavior;
10. selects no general applicable-reference policy;
11. uses complete strict validation, expected revision, exact authority/context
    matching, and one atomic commit;
12. defines distinct creation and mutation receipt ownership/key scopes,
    Phase 1 operation fingerprints and separately derived internal canonical
    state-record fingerprints, exact replay/conflict and stored-original-result
    behavior, complete cross-record validation at write and reconstruction/read
    boundaries, accepted-operation-only persistence, transaction ordering, and
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
20. remains unimplemented, unstaged, uncommitted, and unpushed when the review
    occurs.

Implementation acceptance remains phase-specific and cannot be earned by
approval of this document alone. The plan approval did not approve the
then-local Slice 2 implementation candidate; Slice 2 instead received its own
later independent review.

## 31. Approval and implementation gate

The corrected four-document candidate passed its exact-candidate review and
was committed and pushed at
`afa9f9c21900eebd4e08d65071a26903e83d4a65`, closing the plan-level gate. The
separately authorized Phase 1 implementation passed fresh independent
read-only acceptance for the exact nine-path candidate after the third
correction round. Phase 2 Slice 1 was subsequently accepted and pushed at
`3ad39c7bb7a2c7cc6b2571f6dcb69685b7234101`. Phase 2 Slice 2 was subsequently
independently reviewed with no remaining substantive issue, committed as
`a2802799b3d3a5497f4fc097b0cc05d573d8e0ca`, and pushed to `origin/main`.
Phase 2 Slice 3 is implemented and independently approved. Unit of Work and
cross-repository transaction orchestration are implemented and verified
locally in Slice 4. A new-session independent implementation review returned
`PHASE_2_SLICE_4_IMPLEMENTATION_INDEPENDENTLY_APPROVED` with no blocking
findings. Phase 2 is accepted and complete.

The revised P3-S1 conflict-translation authority in section 24 was independently
approved, committed, and pushed unchanged at
`c6d0220a2442887e89717b5b6facb14af4604236`. The only operative success verdict
for that amendment review was
`APPROVED_STRUCTURED_PLAYER_CHARACTER_PHASE_3_SLICE_1_AUTHORITY_CONFLICT_AMENDMENT`,
and it applies only to the exact complete candidate in `PLANS.md`,
`docs/architecture.md`, and this plan. The former
`STRUCTURED_PLAYER_CHARACTER_PHASE_3_PLAN_APPROVED` token and all historical
planning, correction, Phase 1, and Phase 2 verdicts are non-operative for this
amendment gate. The candidate-preparation verdict
`STRUCTURED_PLAYER_CHARACTER_PHASE_3_SLICE_1_AUTHORITY_CONFLICT_AMENDMENT_CANDIDATE_COMPLETE`
is likewise not amendment approval. Any byte change to that approval-bound
amendment candidate before its documentation commit would have invalidated the
review and required new hashes and a fresh review.

That verdict did not authorize implementation. Separate authorization staged
and committed exactly the approved three-file amendment, the user completed
the push, and the clean pushed baseline was confirmed before this later,
separately authorized P3-S1 implementation task began. The resulting
implementation and bounded correction subsequently completed final independent
review, commit, and push as `7606e51523338247ea33ed9329346fdba046d29b`.
Its closure status synchronization was subsequently committed and pushed as
the then-current baseline `150074d58cdbf3aee08bea9c1084325b2b0f0a3f`
(`docs(player-character): close phase 3 slice 1 status sync`). P3-S1 is
complete and closed.

P3-S2 through P3-S4 were subsequently implemented as the complete Phase 3
candidate. The candidate received independent read-only approval with
`STRUCTURED_PLAYER_CHARACTER_PHASE_3_REVIEW_APPROVED`; no correctness,
authorization, privacy, transaction, composition, or material test-coverage
finding remains open. The complete milestone was committed and pushed at
`cafb12272e703e8751c78bb6852cec90d7d7ec8d`
(`feat(player-character): complete canonical application service`). Phase 3 is
complete. P4-G0 later received
`STRUCTURED_PLAYER_CHARACTER_P4_G0_REVIEW_APPROVED`; its documentation
authority is approved and closed. Historical pre-push wording that described
that P4-G0 milestone as local is superseded: Minimum Run Core is now
implemented, independently approved, committed, and pushed at
`e821cd922b61868097667b12c2b64cf8089a9681`. Its Run-to-Player-Character
binding carrier was null-only and unpopulated at that historical baseline.
P4-S1a (`748003319ececa548b68b351746afbb2d54c66bb`) and P4-S1b
(`8eabf9d4c3c592ea1de50f443f1816de9a46dc8f`) later completed internal binding;
the reserved public command remains rejected and no public Run or gameplay
behavior is active.

The substantive Phase 2 technical prerequisites in section 20 were
historically accepted and frozen under
`STRUCTURED_PLAYER_CHARACTER_PHASE_2_TECHNICAL_FREEZE_APPROVED` at
`1fd29798fe256593e56029baca743484cc221ae4`. That historical approval did not
by itself authorize any implementation slice.

The ordered Phase 2 slices added under section 24 were a distinct amendment.
That implementation-order amendment became operative only after all of these
conditions occurred in order:

1. a fresh independent read-only review returns
   `STRUCTURED_PLAYER_CHARACTER_PHASE_2_PLAN_APPROVED` for the complete exact
   resulting four-document candidate, with the review approving that exact
   candidate's four SHA-256 hashes;
2. separate authorization is obtained to stage and commit exactly those four
   approved documents, and the staged and committed bytes retain the approved
   hashes;
3. the documentation-only commit is pushed through the repository's established
   authorized push workflow;
4. after the push, a new clean baseline is confirmed: `main` is checked out,
   `HEAD` equals local `origin/main`, ahead/behind is `0/0` without an
   unnecessary fetch unless separately authorized, the worktree and index are
   clean, no staged or normal untracked path remains, and the pushed commit
   contains exactly the approved documentation scope; and
5. a separately authorized Phase 2 implementation task then begins.

Those conditions were satisfied before Slice 1 began, and the paragraph
self-executed without another status-only activation edit. Satisfaction of the
gate did not authorize implementation by itself. Every numbered slice still
requires its own prerequisite acceptance and explicit authorization.

Independent approval of the ordering amendment did not itself authorize
implementation, migration execution, database access, staging, commit, push,
deployment, public activation, or work outside the four-document review. Phase
1 acceptance and the historical Phase 2 technical-freeze approval likewise did
not authorize those actions.

No phase is approved, frozen, started, or completed by being listed here.
Approval of the frozen product contract is not implementation authorization.
Approval and freeze of this plan do not authorize staging, committing, pushing,
deployment, or work outside a separately authorized phase.

## 32. Review history

- 2026-07-29: P4-G0 prepared the five-path documentation-only minimum
  Run-core authority candidate after Phase 3 was independently approved,
  committed, and pushed at `cafb12272e703e8751c78bb6852cec90d7d7ec8d`.
  It freezes the minimum-core-first order, both active binding cardinality
  directions, separate trusted Session participation, and the P4-S1
  transaction seam. Its subsequent independent review returned
  `STRUCTURED_PLAYER_CHARACTER_P4_G0_REVIEW_APPROVED`, and the documentation
  authority is approved and closed. This is historical pre-implementation
  review context: the P4-G0 documentation milestone was then local pending a
  user push. Minimum Run Core is now implemented, independently approved,
 committed, and pushed at `e821cd922b61868097667b12c2b64cf8089a9681`; P4-S1 is
 subsequently complete. At that historical review point, Phase 5 and later
 implementation were unstarted or deferred; section 1 records the superseding
 P5-S1/P5-S2 status. Nothing in this entry is implementation authorization.
- 2026-07-29: The completed P3-S2 implementation-readiness review reported
  three blockers: no operative service/path/acceptance boundary, indeterminate
  CAS-loss and mutation-receipt uniqueness-conflict behavior, and operative
  baseline text still pointing to the superseded pre-push baseline. This
  three-document candidate resolves only those blockers. It records
  `150074d58cdbf3aee08bea9c1084325b2b0f0a3f` as the then-current pushed
  baseline,
  defines the exact `4 + 2 + 3` P3-S2 contract, maps CAS false to
  `STALE_REVISION`, and limits receipt-race recovery to the exact local
  receipt-add conflict followed by at most one disposed-then-fresh UoW read.
  The candidate remains unimplemented, unstaged, uncommitted, and pending one
  independent review. P3-S1 remains closed; P3-S3/P3-S4 remain not started.
- 2026-07-29: The first fresh independent read-only review of the local P3-S1
  implementation candidate returned changes required for one blocking
  control-flow defect. The exact controller-binding add exception was recorded
  and re-raised, but if the initial Unit of Work suppressed it, the recorded
  value alone could still select a fresh-UoW winner recovery. This bounded
  correction candidate requires the same exception object to escape the failed
  initial UoW and be confirmed by the outer handler; suppression instead
  re-raises the preserved original object without recovery, receipt lookup,
  success, or replay. Focused regression coverage was added. This describes
  the pre-correction review state; the bounded correction subsequently received
  final approval, was committed and pushed, and closed P3-S1. Phase 3 remains
  incomplete.
- 2026-07-29: The revised three-file P3-S1 authority-conflict amendment
  received its exact operative independent-review verdict, was committed and
  pushed unchanged at `c6d0220a2442887e89717b5b6facb14af4604236`, and was
  confirmed as the clean `main`/`origin/main` baseline. A later separately
  authorized task implemented P3-S1 and its bounded correction; final
  independent approval, commit, and push closed P3-S1 at
  `7606e51523338247ea33ed9329346fdba046d29b`. Phase 3 remains incomplete, and
  no API, composition, Demo, frontend, Provider, Run, narrative, content, or
  gameplay path was activated.
- 2026-07-29: The first P3-S1 implementation attempt stopped with
  `BLOCKED_STRUCTURED_PLAYER_CHARACTER_PHASE_3_SLICE_1_AUTHORITY_AMENDMENT_REPOSITORY_CONFLICT`
  after repository inspection proved that
  `PlayerCharacterRepositoryConflictError` is shared by controller-binding,
  allocation, initial-state, receipt, stale-current, and other conflicts. No
  P3-S1 production or test code was implemented.
- 2026-07-29: The first documentation amendment design was rejected because it
  would have made that shared infrastructure error implement an
  application-owned controller-binding-only contract. This revised
  documentation-only candidate instead assigns
  `ControllerBindingUniquenessConflictError` to application ports,
  `PlayerCharacterControllerBindingConflictError` to infrastructure, and the
  binding-specific subtype selection to the exact controller-binding add
  duplicate-key flush. Independent read-only amendment review remains pending;
  P3-S1 remains unimplemented, and nothing was staged, committed, or pushed.
- 2026-07-28: The corrected structured player-character Phase 3–5 roadmap and
  exact P3-S1 creation-orchestration candidate were written into `PLANS.md`,
  `docs/architecture.md`, and this plan. This was a bounded documentation
  planning write, not the required independent review. P3-S1 remained
  unimplemented and unauthorized; nothing was staged, committed, or pushed.
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
- 2026-07-27: A subsequent fresh independent read-only review of that exact
  substantive Phase 2 technical-prerequisite candidate returned
  `STRUCTURED_PLAYER_CHARACTER_PHASE_2_TECHNICAL_FREEZE_APPROVED`. The exact
  reviewed candidate was then committed and pushed unchanged to `main` as
  `1fd29798fe256593e56029baca743484cc221ae4`
  (`docs(domain): freeze structured player-character phase 2 prerequisites`).
  This acceptance froze the technical prerequisites only. It implemented no
  migration, database verification, persistence adapter, production
  composition, public route, frontend behavior, Provider integration, or
  story/Run activation and did not authorize Phase 2 runtime work.
- 2026-07-28: A bounded findings-correction task addressed all five findings
  from the first independent review of the local Phase 2 Slice 1 candidate.
  Creation reconstruction now binds revision 1 and its provenance to
  authoritative creation evidence through the existing Phase 1 creation
  policy; mutation receipt validation preserves one-to-one transition
  ownership; and stored revision, immutable-binary, nested-binary, and
  state-record-fingerprint columns fail closed. Fifteen focused regressions
  increased the persistence module from 79 to 94 passing tests while the 190
  Phase 1 regressions remained unchanged. The 284-test combined group,
  compileall, and Offline verification with 1,346 passed and 48 skipped also
  passed. Final independent acceptance remains pending. Nothing was staged,
  committed, or pushed; Slice 2 did not begin.
- 2026-07-28: After Slice 1 was independently accepted, committed, and pushed
  at `3ad39c7bb7a2c7cc6b2571f6dcb69685b7234101`, a separately authorized
  implementation task added only Phase 2 Slice 2. The local candidate adds the
  exact six SQLAlchemy mappings and linear Alembic revision
  `20260728_0004`, with `20260719_0003` as its parent, frozen MySQL
  collations/types/keys/checks, twelve named restrictive foreign keys, the
  exact index inventory, no backfill, and fail-closed data-present downgrade
  refusal before destructive DDL. Focused schema and all 284 Slice 1 tests,
  compileall, Alembic heads/history, MySQL verification with 61 passing tests,
  Offline verification with 1,357 passed and 51 skipped, and Full verification
  with 1,407 passed and one skipped opt-in live test passed. The candidate
  remains unstaged, uncommitted, and unpushed pending fresh independent review.
  No repository, locking/CAS, replay, Unit of Work, service, runtime, public,
  frontend, Provider, Demo, Session, Run, or story-line behavior was added.
- 2026-07-28: A fresh independent read-only review of the exact Phase 2 Slice 2
  candidate found no remaining substantive issue. Relevant real-MySQL
  verification passed with 64 tests, and the relevant Slice 1 regression passed
  with 284 tests. Exactly seven approved paths—`PLANS.md`,
  `docs/architecture.md`,
  `docs/structured_player_character_implementation_plan.md`,
  `src/deviation_protocol/infrastructure/orm_models.py`,
  `alembic/versions/20260728_0004_structured_player_character_phase_2.py`,
  `tests/integration/test_mysql_connection.py`, and
  `tests/integration/test_mysql_player_character.py`—were committed in exactly
  one commit, `a2802799b3d3a5497f4fc097b0cc05d573d8e0ca`, with parent
  `3ad39c7bb7a2c7cc6b2571f6dcb69685b7234101` and subject
  `feat(player-character): add structured persistence schema`, then pushed as
  `3ad39c7..a280279` (`main -> main`). Phase 2 Slice 3 is implemented and
  independently approved as the bounded MySQL Repository layer.
- The then-current committed Slice 3 baseline was
  `7313b5833cae7a9f9c0b618abe5b49cfcbaba604`
  (`feat(player-character): implement mysql repositories`). Slice 4 was
  implemented and verified locally, and its new-session independent review
  returned `PHASE_2_SLICE_4_IMPLEMENTATION_INDEPENDENTLY_APPROVED` with no
  blocking findings. Phase 2 is accepted and complete. No runtime, API, HTTP,
  frontend, Demo, Provider, Run, narrative, content, or gameplay integration
  was activated; Phase 3 and later work remain deferred.
