# Minimum Run Core Implementation Plan

## 1. Status

Status: **Minimum Run Core implemented, independently finally approved,
committed, and pushed; P4-S1 remains unstarted.**

The prerequisite was implemented, independently finally approved, committed,
and pushed as `e821cd922b61868097667b12c2b64cf8089a9681`
(`feat(run): implement minimum run core`). The completed baseline retains the
all-null, unpopulated binding seam and rejects the reserved
`run.bind-player-character/v1` operation. P4-S1 is the next unstarted work;
no public Run behavior is activated.

This document freezes the smallest Phase 3.3 Run-owned prerequisite required
before Structured Player Character Phase 4 can begin. It is an implementation
plan and authority boundary only. It does not implement the Run core, a
player-character binding, any other Run Protocol feature, or any public
gameplay behavior.

Structured Player Character Phase 3 is complete and pushed. The minimum Run
core is its completed P4-S1 prerequisite. Phase 4 implementation remains
unstarted; this completed prerequisite does not itself bind a character or
activate a public surface.

## 2. Authority and ownership

Authority is divided by subject rather than by document breadth:

1. [Run Protocol, Difficulty, and World Profiles](run_protocol.md) owns Run
   lifecycle, the Run-owned continuous story line, world selection, visits,
   and world-transition protocol.
2. [Structured Player-Character Contract](structured_player_character_contract.md)
   owns canonical player-character identity, the exact applicable character
   reference, character lifecycle, controller separation, privacy, and
   character-continuity invariants.
3. [Structured Player-Character Downstream Implementation Plan](structured_player_character_implementation_plan.md)
   owns the structured player-character phase sequence, Phase 4 gates, and the
   P4-S1 binding boundary.
4. This plan owns only the minimum Run-core prerequisite implementation
   sequence, its persistence boundary, transaction order, expected path
   budgets, and acceptance evidence.
5. [`PLANS.md`](../PLANS.md) owns cross-phase status and immediate
   implementation order.
6. Existing narrower implemented authorities retain their present scopes,
   especially [Architecture](architecture.md),
   [Engineering Guardrails](engineering/guardrails.md), and
   [Codex Workflow](engineering/codex_workflow.md).

The approved
[Final Narrative Experience and Long-Term Systems](final_narrative_experience.md)
specification remains the product-level source for persistent character and
cross-scenario continuity. A broad roadmap or product statement does not
override a narrower frozen contract.

This minimum prerequisite is not the complete Phase 3.3 implementation. It
does not absorb world generation, profile resolution, scenario execution,
later-world selection, visit mechanics, narrative progression, or Phase 3.4
NPC relationship and residence behavior.

## 3. Motivation and Phase 4 dependency

P4-S1 must eventually bind one canonical player character and its exact
`ApplicableCharacterReference` to one Run-owned continuous story line. The
binding must survive scenario changes and Run-authorized later-world
transitions in that same line, and conflicting active bindings must fail
atomically.

Historical pre-implementation context: before Minimum Run Core, the repository
had no canonical Run or continuous-story-line identity, Run aggregate, Run state
version, Run Repository, Run application service, Run-owned transaction
boundary, separate Session participation record, or Run-aware production
composition. `GameSession`, `scenario_id`, `phase_visit_counts`, browser
storage, controller identity, and `character_definition_id` could not
substitute for those missing authorities. Minimum Run Core now implements that
prerequisite and was independently approved, committed, and pushed at
`e821cd922b61868097667b12c2b64cf8089a9681`.

The minimum objective is therefore:

> Establish one durable Run-owned aggregate and transaction owner with stable
> Run and continuous-story-line identities, monotonic state versioning,
> trusted separate Session participation, strict persistence, and an
> all-null reserved storage seam that P4-S1 can later activate for the exact
> player-character binding.

The minimum core supports later extension. It must not claim that a Run can
already select worlds, execute scenarios, advance narrative, manage NPC
residence, resolve combat, call a Provider, or serve public gameplay.

## 4. Accepted decisions

### 4.1 Minimum Run core first

Only the smallest Run core needed for identity, durable state, optimistic
concurrency, trusted participation, and the future atomic character-binding
seam precedes P4-S1. Completion of every deferred Phase 3.3 Run Protocol
feature is not a prerequisite.

### 4.2 Active character/story-line cardinality

The following are current authority:

- once a continuous story line has a player-character binding, it has exactly
  one active canonical player-character binding while the line is active;
- one canonical player character belongs to at most one active continuous
  story line;
- a conflicting active binding attempt fails atomically;
- a completed, terminated, or otherwise non-active historical line may retain
  its immutable character and applicable-reference history without counting
  as a second active binding;
- ending a Run or its owned continuous story line must make the binding's
  active or historical state deterministic in the same canonical change; and
- no cloning, transfer, replacement, automatic rebinding, or implicit
  ownership derivation is authorized.

The minimum Run core reserves this seam but does not create a character
binding. P4-S1 owns the first binding operation.

### 4.3 Separate Session participation

Session participation belongs to the Run domain and is stored separately from
the legacy Session:

- `game_sessions` receives no Run, continuous-story-line, or
  player-character-binding column;
- only trusted Run orchestration may create participation;
- request or Session data cannot authoritatively select, replace, or derive a
  Run;
- participation grants neither player-character ownership nor controller
  authority;
- one immutable minimum participation record maps one Session to one Run, so
  the same Session cannot be concurrently routed to a conflicting active Run;
- multiple distinct trusted Sessions may participate in the same continuing
  Run over time; and
- this storage contract does not activate cross-tab, browser-restart,
  multi-device, reconnect, resume, or other public recovery behavior.

The minimum one-Run-per-Session record is deliberately narrower than a future
Session reassignment design. No update, delete, transfer, or replacement
operation is admitted.

## 5. Minimum domain and identity model

### 5.1 Canonical carrier names

No accepted authority currently defines concrete Run carriers. P4-G0 selects
the narrow repository-consistent names:

| Carrier | Meaning | Required separation |
| --- | --- | --- |
| `RunId` | Permanent identity of one canonical Run aggregate | Distinct from every other identity domain |
| `ContinuousStoryLineId` | Permanent identity of the one continuous story line owned by that Run | Distinct from `RunId` and every other identity domain |
| `RunOperationId` | Idempotency/replay identity for one Run application command | Never a Run, line, Session, character, authority, or capability |
| `RunAuthoritySourceRef` | Opaque trusted provenance reference supplied by server orchestration | Never controller proof or caller authority |
| `RunStateVersion` | Ordered optimistic-concurrency token for one Run | Never an identity, character revision, Session version, or contract version |

`RunId`, `ContinuousStoryLineId`, `RunOperationId`, and
`RunAuthoritySourceRef` follow the existing canonical opaque-reference
convention: distinct strict frozen value-object types, one exact ASCII value,
length 1 through 128, and the accepted
`[A-Za-z0-9][A-Za-z0-9_.:-]*` grammar. Values are preserved exactly; they are
not trimmed, case-folded, semantically parsed, or coerced between carrier
types. Already-instantiated models are defensively revalidated at public
domain/application and persistence reconstruction boundaries.

Normal production composition injects the validated
`RunAuthoritySourceRef` into `RunService`, matching the established
player-character service provenance convention. It is not a caller-selected
command field, credential, or capability, and a submitted copy cannot replace
the injected value.

Normal production issuance follows the accepted player-character identity
pattern:

- `RunId` is `run.` plus 32 lowercase hexadecimal digits from a directly
  invoked operating-system-random UUIDv4;
- `ContinuousStoryLineId` is `csl.` plus 32 lowercase hexadecimal digits from
  a separate directly invoked operating-system-random UUIDv4;
- each generated value is validated through its canonical carrier before use;
- production exposes no caller-supplied replacement seam for UUIDv4 issuance;
  bounded tests may inject deterministic issuers; and
- a collision or persistence uniqueness failure rolls back and fails closed.
  It does not trigger generalized identity issuance or transaction retry.

Neither identity contains or is derived from a principal, controller,
character, timestamp, sequence, world, visit, scenario, Session, account, or
Provider identity. A committed identity is never reused for another canonical
Run or line. No delete or release operation exists.

### 5.2 Exact Run-to-line relationship

The minimum model is:

```text
one RunId
  -> permanently owns exactly one ContinuousStoryLineId
```

The line identity is allocated atomically with the Run identity, is required
from revision 1, and cannot be replaced or moved. A
`ContinuousStoryLineId` belongs to exactly one `RunId`. The aggregate is not a
general container for unrelated or sequential story lines, and no separate
line aggregate is introduced by the minimum core.

## 6. Lifecycle and canonical state boundary

### 6.1 Run lifecycle vocabulary

The existing Run Protocol describes lifecycle positions but did not previously
name a persisted status carrier. P4-G0 freezes the smallest closed
`RunLifecycleStatus` needed to make active and non-active results
deterministic:

| Persisted value | Run Protocol meaning | Active-line classification |
| --- | --- | --- |
| `pre_first_turn` | The stable Run/line identities exist, but the first turn has not begun | Active for exclusivity and future binding cardinality |
| `active` | The first turn has begun and the Run continues | Active |
| `completed` | Trusted Run authority ended the line normally | Non-active and historical |
| `terminated` | Trusted Run authority ended the line through a non-normal authorized termination | Non-active and historical |

The minimum Run core creates only `pre_first_turn` state. It does not implement
the transition to `active`, `completed`, or `terminated`.

Full Phase 3.3 authority must later define and implement the exact transition
commands and preconditions. In particular, the Run Protocol still requires
the resolved protocol and selected `entry_world_id`/`entry_world_version` to
receive their Run binding and be frozen at the first turn. Session loss,
browser loss, inactivity, Provider failure, prose, or caller input never
changes Run lifecycle.

The continuous story line has no independent minimum status machine. Its
active/non-active state is derived exactly from its owning Run status. A
future terminal transition that has a character binding must move that binding
from active to historical inside the same Run-owned transaction.

### 6.2 `RunStateVersion`

`RunStateVersion` is a distinct positive signed-64-bit value from 1 through
`9223372036854775807`.

- canonical creation writes version 1;
- each successful Run mutation advances exactly one version;
- current-state replacement uses exact expected-version compare-and-swap and
  requires one affected row;
- replay of an already committed operation returns its stored original result
  without advancing the current version;
- stale state, CAS loss, rejection, rollback, or persistence failure leaves the
  version unchanged; and
- the maximum version remains readable but cannot produce a successor.

No Session `state_version`, player-character `record_revision`, Alembic
revision, content version, Run Protocol version, or world/scenario version can
serve as `RunStateVersion`.

### 6.3 Minimum canonical state

One strictly validated `CanonicalRun` consists of:

| Field/group | Minimum rule |
| --- | --- |
| `run_id` | Required immutable `RunId` |
| `continuous_story_line_id` | Required immutable `ContinuousStoryLineId`, owned one-to-one by this Run |
| `lifecycle_status` | Required closed `RunLifecycleStatus`; minimum creation emits only `pre_first_turn` |
| `state_version` | Required `RunStateVersion`, initially 1 and advanced only by successful canonical mutation |
| `creation_provenance` | Required trusted creation operation ID, authority-source reference, mutation kind, and server UTC creation time |
| `current_mutation_provenance` | Required exact target Run/line, prior/resulting state version, mutation kind, operation ID, authority-source reference, and server UTC mutation time |
| trusted participation references | Reconstructed from immutable separate participation records, each exact-bound to this Run/line and its resulting Run revision |
| `player_character_binding` | Required logical slot whose only valid minimum-core value is absent; its complete future envelope is frozen in section 7 |

The closed `RunMutationKind` carrier reserves `CREATE`, `ATTACH_SESSION`, and
`BIND_PLAYER_CHARACTER`. The minimum service admits only `CREATE` and
`ATTACH_SESSION` and rejects `BIND_PLAYER_CHARACTER` as unsupported.
`CREATE` is valid only at version 1 with no prior version;
`ATTACH_SESSION` is valid only for an exact one-version successor with the
matching new participation. P4-S1 later admits
`BIND_PLAYER_CHARACTER` only with the complete active envelope.
`creation_provenance` remains byte-for-byte stable in every successor while
`current_mutation_provenance` changes to the exact committed mutation.

Canonical participation references form a frozen tuple ordered strictly by
their distinct joined `RunStateVersion`. Each version is positive, no greater
than the current Run version, and exact-bound to one immutable Run revision;
Session identity is unique across the complete participation family. Storage
row order is never canonical order.

Server timestamps are audit facts only. They do not establish identity,
ordering, replay equivalence, lifecycle, authority, or state version.

The minimum creation state contains no world, visit, scenario, difficulty,
resolved protocol, seed, narrative, inventory, combat, quest, NPC,
relationship, Provider, frontend, or content state. Because the minimum
aggregate is created at `pre_first_turn`, current Run Protocol authority does
not require an applicable world or visit reference in the minimum creation
record. The later `active` transition remains unavailable until the owning
Phase 3.3 implementation supplies and validates the required frozen protocol
and entry-world binding.

### 6.4 Validation and corruption rejection

Domain models are strict, frozen, extra-forbid, and fully revalidated.
Persistence reconstruction must validate:

- exact carrier types and values;
- Run-to-line ownership;
- lifecycle/status closure;
- positive version and exact predecessor/successor relationships;
- current row to current immutable revision equality;
- creation and mutation provenance;
- participation-to-Run/line/revision equality;
- receipt key, fingerprint, evidence, result, and referenced-record equality;
- the complete all-null or future all-required player-character binding
  matrix; and
- every relational duplicate against the canonical reconstructed value.

Missing, malformed, unknown, contradictory, cross-Run, cross-line,
cross-Session, or cross-character data is an integrity failure. It is never
repaired, defaulted, silently dropped, reinterpreted, or returned as trusted
state.

## 7. Reserved future player-character binding seam

### 7.1 Logical envelope

`CanonicalRun.player_character_binding` reserves this exact future envelope:

| Field | Future P4-S1 meaning |
| --- | --- |
| `run_id` | Exact owning `RunId` |
| `continuous_story_line_id` | Exact immutable line owned by that Run |
| `applicable_character_reference.player_character_id` | Exact canonical `PlayerCharacterId` |
| `applicable_character_reference.contract_version` | Exact supported `PlayerCharacterContractVersion` |
| `applicable_character_reference.record_revision` | Exact applicable immutable `PlayerCharacterRevision` |
| `binding_state` | Closed `active` or `historical` |
| `binding_operation_id` | Exact P4 binding operation identity |
| `binding_authority_source_ref` | Trusted Run-orchestration provenance |
| `bound_at` | Server UTC audit time |
| `inactivated_at` | Absent while active; required when historical |

The minimum Run-core service, Repository write model, and tests permit only the
fully absent envelope. They must reject a partial or populated binding as
unsupported before write. P4-S1 later admits the complete active form; a later
authorized Run terminal transition admits only the same immutable reference
changed to historical. No operation may replace the identity or applicable
reference in an existing envelope unless a separately approved future
applicable-reference policy expressly authorizes that change; neither the
minimum core nor P4-S1 has such authority.

The lifecycle/binding matrix is exact:

| Run lifecycle | Permitted binding forms |
| --- | --- |
| `pre_first_turn` or `active` | fully absent, or complete `active` |
| `completed` or `terminated` | fully absent only if the line was never bound, or complete `historical` |

A partial envelope, an active binding on a terminal Run, a historical binding
on an active Run, or a terminal absent binding after immutable history proves
that the line was previously bound is corruption.

The physical current and immutable-revision records reserve nullable columns
for this envelope. An additional nullable
`run_current.active_player_character_id` backstop is:

- equal to the bound character ID only for an active binding;
- `NULL` for an absent or historical binding; and
- globally unique when non-NULL.

Together with unique continuous-story-line ownership, this supplies the
database backstop for at most one active line per character and one binding
per line without activating binding behavior during the minimum prerequisite.
The exact character ID/revision pair references the immutable
`player_character_revisions` identity when populated. Adapter reconstruction
also exact-matches the stored character contract version.

### 7.2 P4-S1 authority requirements

P4-S1 must later:

1. resolve controller authority from trusted context;
2. obtain the owned canonical character/reference through the approved Phase 3
   application boundary;
3. treat any detached owned projection only as validated read evidence, never
   as mutable persistence state;
4. use the Run application service as the sole owner of the binding mutation;
5. lock or serialize the exact Run/line and evaluate the binding receipt before
   stale-version rejection;
6. write the complete binding envelope, Run revision, current-row CAS, and
   successful receipt atomically in the Run-owned UnitOfWork;
7. reject either cardinality conflict with no Run or character mutation;
8. preserve the same exact ID/reference across every scenario and
   Run-authorized later-world transition in the same line; and
9. add no Session copy of the mutable character aggregate and no independent
   character-service commit.

The character aggregate is read-only in the binding operation. P4-S1 must not
redesign existing `PlayerCharacterService` create, mutate, or `get_owned`
semantics, and caller-supplied Run state must not become character authority.
To preserve the one-operation/one-UnitOfWork rule, P4-S1 must add a narrow
Phase 3-owned internal read seam that accepts the already-owned Run
UnitOfWork, locks and canonically reconstructs the current character, performs
the same trusted controller, ownership, lifecycle, identity, and
exact-reference checks, and returns only the validated exact reference and
lifecycle evidence needed by the Run mutation. New binding requires the
character lifecycle to be `active`; that eligibility check occurs after
receipt evaluation so a compatible replay remains deterministic. The seam
must not open a nested UnitOfWork, commit, expose other private character
state, or alter the existing public `get_owned` behavior. Its implementation
and focused compatibility tests belong to P4-S1 review, not the minimum Run
core.

No API route or frontend behavior is defined here.

## 8. Session participation contract

The minimum participation record is an immutable Run-owned fact:

```text
existing Session identity
  -> one RunId
  -> that Run's exact ContinuousStoryLineId
  -> exact joined RunStateVersion and trusted provenance
```

The service may create it only when trusted Run orchestration has selected the
Run independently of request authority and the existing Session Repository has
proved the Session belongs to the current trusted principal. Run/line
disclosure and mutation occur only after that ownership check.

The dedicated record:

- uses `session_id` as its primary uniqueness boundary;
- exact-binds the Run, line, joined state version, operation ID,
  authority-source reference, and server UTC creation time;
- is insert-only;
- permits many different Session IDs to reference the same Run;
- rejects a Session already participating through any different or
  unreceipted command, whether the attempted target is the same or a different
  Run;
- survives as historical provenance after the Run becomes non-active; and
- does not update or reinterpret `game_sessions`.

Participation is not authentication, ownership, controller binding,
player-character binding, resume permission, or a public routing token.
Legacy Sessions remain valid and unbound. No backfill from `player_id`,
`character_definition_id`, scenario, browser storage, prose, or other
heuristic is permitted.

## 9. Persistence and UnitOfWork boundary

### 9.1 Minimum record families

The minimum durable schema has exactly five Run-owned record families:

| Record family | Planned table | Responsibility |
| --- | --- | --- |
| Canonical current Run | `run_current` | One current strictly validated Run row, immutable Run/line identity, lifecycle, state version, and reserved binding envelope |
| Immutable Run revisions | `run_revisions` | One complete authoritative snapshot and provenance record for each committed Run state version |
| Session participation | `run_session_participations` | Separate immutable Session-to-Run/line participation facts |
| Successful creation receipts | `run_creation_receipts` | Original committed result for `run.create/v1` |
| Successful Run mutation receipts | `run_mutation_receipts` | Original committed result for the admitted `run.attach-session/v1` mutation; structurally able to admit the separately reviewed P4 binding command later |

No separate generalized story-line container, event store, account mapping,
world, visit, scenario-run, NPC, relationship, narrative, Provider, rejected
operation, pending operation, archive, worker, or recovery table belongs to
this prerequisite.

Immutable Run revisions are required here because state-version CAS,
participation provenance, and the future retained historical character
reference must resolve to exact committed state. They are bounded aggregate
revision history, not event sourcing.

### 9.2 Relational integrity

The implementation migration must establish at least:

- primary `run_current.run_id`;
- unique immutable `run_current.continuous_story_line_id`;
- exact positive current version and a restrictive reference to the matching
  immutable `(run_id, state_version)` revision;
- unique nullable `run_current.active_player_character_id`;
- the all-null/active/historical binding-field matrix;
- a nullable restrictive reference from the exact bound character/revision to
  immutable player-character history;
- primary `run_session_participations.session_id`;
- restrictive participation references to the existing Session, exact Run/
  line, and joined Run revision;
- natural immutable receipt keys and exact result/revision references; and
- named checks and indexes sufficient for exact lookup, reconstruction, CAS,
  uniqueness, and corruption tests.

`run_mutation_receipts` uses a closed namespace-specific evidence/result
matrix. Minimum `run.attach-session/v1` rows require their exact Session and
participation result fields and keep all character-binding fields null. The
schema reserves the exact Run/line/character contract/revision result fields
for `run.bind-player-character/v1`; the minimum Repository rejects that
namespace and any populated reserved fields until P4-S1. When later admitted,
those fields must restrictively reference both the resulting Run revision and
the exact immutable player-character revision.

All identity/reference and closed-token columns follow the existing
case-sensitive ASCII convention; database storage does not trim, normalize,
fold, generate, or reinterpret them. Versions use signed `BIGINT` within the
canonical positive range. Server UTC audit times use the repository's current
`DATETIME(6)` convention with no identity or ordering authority.

Current and revision records duplicate only the small relational state needed
for strict reconstruction. Receipt evidence and stored safe results use the
established deterministic canonical-byte and SHA-256 fingerprint conventions.
Every duplicate is cross-validated on write and read.

There is no Run or line delete/release port. Once any Run data exists,
destructive downgrade that could release an identity or discard history must
fail before destructive DDL; operational recovery is forward-only.

### 9.3 Repository ports

The application layer owns narrow ports for:

- `RunRepository`: get, get-for-update, add initial current/revision, append
  immutable revision, and compare-and-swap current;
- `RunSessionParticipationRepository`: get by Session and add one immutable
  participation;
- `RunCreationReceiptRepository`: get/add immutable successful creation
  receipts; and
- `RunMutationReceiptRepository`: get/add immutable admitted mutation
  receipts.

Every MySQL Repository:

- receives an already-owned SQLAlchemy `AsyncSession`;
- performs only its accepted load, lock, insert, CAS, reconstruction, and
  `flush()` work;
- never creates, commits, rolls back, closes, replaces, or independently
  retries the database session;
- performs no application orchestration or external network access; and
- fails closed on integrity mismatch, uniqueness conflict, stale/CAS loss, or
  malformed storage.

The existing application `UnitOfWork` later exposes `runs`,
`run_participations`, `run_creation_receipts`, and
`run_mutation_receipts` over the same entered `AsyncSession` as the existing
Session and player-character repositories. The Run application service owns
the transaction. No Repository may hide a retry or independent commit.

### 9.4 Migration-head rule

Implementation must inspect the then-current single Alembic head, create the
next linear revision from that exact head, and verify both `alembic heads` and
`alembic history`. This plan deliberately records no future revision
identifier or parent hash. The migration must not backfill or infer a Run,
line, participation, or binding from existing data.

## 10. Transaction ownership, concurrency, and failure

`RunService` is the only application transaction owner for minimum Run
mutations and the future P4 binding mutation.

For every admitted mutation:

- trusted authority and complete command validation precede targeted private
  disclosure;
- exactly one mutation UnitOfWork is entered;
- all state belonging to one canonical change is written in that UnitOfWork;
- Repositories flush but never commit;
- the service calls `commit()` exactly once after every required write
  succeeds;
- success is returned only after that commit returns successfully;
- uncommitted normal exit, exception, cancellation, uniqueness conflict,
  persistence failure, stale version, or CAS loss rolls back and fails closed;
- a failed SQLAlchemy session is discarded; and
- no generalized transaction, mutation, identity-issuance, or commit retry is
  introduced.

### 10.1 Canonical creation order

`create_run` uses this order:

1. validate the trusted creation source, typed command, and
   `RunOperationId`;
2. enter one UnitOfWork;
3. read the exact creation receipt key and evaluate compatible replay or
   incompatible reuse before issuing identities;
4. issue and validate one `RunId` and one `ContinuousStoryLineId`;
5. construct and completely validate version-1 `pre_first_turn`
   `CanonicalRun` with an absent binding;
6. insert immutable revision 1;
7. insert current Run referencing revision 1;
8. insert the immutable successful creation receipt and stored safe result;
9. commit once; and
10. return success only after commit.

An identity collision, line uniqueness conflict, receipt conflict,
persistence failure, or commit failure rolls back everything. No second ID is
issued in the operation.

### 10.2 Trusted Session participation order

`attach_session` uses this order:

1. validate the principal/trusted orchestration context, internal target
   `RunId`, Session intent, exact expected `RunStateVersion`, source reference,
   and `RunOperationId`;
2. enter one UnitOfWork;
3. use the existing Session Repository ownership boundary to prove the Session
   belongs to the trusted principal before Run or receipt disclosure;
4. lock and strictly reconstruct the target Run;
5. evaluate the exact mutation receipt before stale-version rejection;
6. reject a non-active Run, stale expected version, exhausted version, or any
   existing Session participation not proven by the exact receipt;
7. construct and validate the successor Run revision;
8. append the immutable Run revision;
9. insert the immutable participation referencing that successor;
10. compare-and-swap current Run by exact Run ID, line ID, and expected
    version, requiring one affected row;
11. insert the immutable successful mutation receipt;
12. commit once; and
13. return success only after commit.

Same-Run compliant writers serialize on the exact Run. Cross-Run attempts to
claim one Session meet the Session primary-key backstop; at most one commits.
The loser rolls back and returns conflict. It does not reinterpret the winner
as authority, open a recovery transaction, or retry.

### 10.3 Future P4 binding transaction

P4-S1 must use this Run-owned order:

1. validate the trusted principal/orchestration context, typed target
   character and Run intent, exact expected `RunStateVersion`, source
   reference, and binding operation ID, then resolve trusted controller
   authority before private disclosure;
2. enter one UnitOfWork;
3. use the narrow Phase 3-owned internal read seam over that same UnitOfWork
   to lock and strictly reconstruct the current canonical character, prove
   controller ownership, and produce its exact reference and lifecycle
   evidence;
4. lock and strictly reconstruct the target Run/line;
5. evaluate the exact binding receipt before stale-state or new-operation
   eligibility rejection;
6. for a new operation, require an active character and active Run/line,
   exact current expected version, an absent existing line binding, and no
   other active line for that character;
7. construct and validate the complete active binding envelope and one
   successor Run revision;
8. append that immutable Run revision;
9. compare-and-swap `run_current` by exact Run ID, line ID, and expected
   version, including the unique active-character backstop, and require one
   affected row;
10. insert the immutable successful binding receipt;
11. commit exactly once; and
12. return success only after commit.

Any ownership, lifecycle, binding, uniqueness, FK/reference, stale-version,
CAS, persistence, or commit failure rolls back and fails closed. P4-S1
updates no character row, opens no nested UnitOfWork, coordinates no
independent service commit, and performs no retry.

A Run or line ending that has an active binding must later write the terminal
Run status, historical binding state, immutable revision, current CAS, and
receipt in that same Run transaction. No current minimum command implements
that transition.

## 11. Operation identity, receipts, and replay

### 11.1 Exactly admitted minimum commands

| Command | Server-owned namespace | Receipt scope | Why a receipt is required |
| --- | --- | --- | --- |
| `create_run` | `run.create/v1` | `(operation_namespace, operation_id)` | A retry must return the originally allocated Run/line pair instead of allocating another canonical Run |
| `attach_session` | `run.attach-session/v1` | `(run_id, operation_namespace, operation_id)` | A retry must not add participation twice or advance Run state twice |

Read-only Run lookup, validation, and reconstruction have no operation ID and
create no receipt. The minimum core implements no lifecycle-transition or
character-binding command, so it creates no receipt for either. The distinct
server-owned `run.bind-player-character/v1` namespace is reserved and rejected
by the minimum service; P4-S1 later admits its successful receipt because that
mutation crosses the same retryable application boundary.

`RunOperationId` is validated opaque data. It is never authority, a capability,
a Run/Session/character identity, or permission to disclose a receipt.
Operation namespaces are selected by server code and are not caller authority.

### 11.2 Fingerprint and stored result

After typed command validation, each mutating command produces deterministic
canonical UTF-8 JSON and a SHA-256 operation fingerprint. It includes the
server-owned namespace, command kind, exact operation scope, source reference,
and every semantically relevant validated input. Participation additionally
binds exact Run, line, Session, and expected Run state version. It excludes
newly issued Run/line IDs from the creation command fingerprint because they
do not exist before successful issuance.

Canonicalization follows the existing operation convention: NFC strings,
sorted normalized object keys, stable separators, no floats or non-JSON
values, preserved meaningful whitespace and ordered collections, and no
case-folding or invented equivalence.

The immutable safe result stores only the exact Run ID, line ID, lifecycle
status, resulting Run state version, and the admitted participation reference
when applicable. It stores no principal, controller binding, private Session
data, authority internals, database details, Provider data, or future
player-character data.

### 11.3 Replay decisions

After required authority checks:

- exact key plus exact fingerprint, command, scope, result schema, and
  referenced authoritative records returns the original committed result
  without policy, issuance, state mutation, CAS, receipt insertion, or commit;
- the same key with any incompatible fingerprint, command, scope, target,
  result binding, or result schema conflicts safely;
- receipt evaluation precedes stale-version rejection for an exact retry;
- malformed or cross-record-inconsistent receipt data is an integrity failure;
  and
- only successfully committed mutations have receipts.

Validation, authorization, stale-version, lifecycle, uniqueness, CAS, and
persistence rejections have no receipt. There is no pending receipt, rejected
receipt, TTL, cleanup, deletion, archival, uncertain-commit recovery, or broad
winner-recovery mechanism.

## 12. Coherent minimum Run-core implementation slices

Every slice requires a separately authorized implementation task. Each ends
with an unstaged, reviewable checkpoint and does not authorize the next slice.
The complete minimum Run-core candidate receives one fresh independent
read-only review before documentation synchronization and the separately
authorized milestone commit.

### MRC-S1 — Pure Run aggregate and operation protocol

**Behavioral outcome:** strict Run/line identities, canonical minimum state,
lifecycle/status carrier, version successor rules, reserved binding envelope,
creation and Session-participation commands, fingerprints, safe results, and
replay decisions exist without I/O.

**Authoritative requirement:** sections 4 through 8 and 11 of this plan.

**Prerequisites:** P4-G0 independently approved, documentation milestone
committed and manually pushed, and a new clean baseline confirmed.

**Production path budget:** exactly two new paths:

- `src/deviation_protocol/domain/run.py`;
- `src/deviation_protocol/application/run_operations.py`.

**Test path budget:** exactly two new paths:

- `tests/unit/test_run.py`;
- `tests/unit/test_run_operations.py`.

**Persistence/migration effect:** none.

**Transaction/authorization boundary:** pure construction and protocol
evaluation only; no Repository, UnitOfWork, clock I/O, UUID call, principal
resolution, or disclosure.

**Compatibility:** no import from infrastructure into domain/application; no
existing Session, player-character, Provider, API, Demo, or scenario type
changes.

**Focused verification:** the two new unit modules, applicable dependency
direction checks, `compileall`, Offline verification, and `git diff --check`.

**Completion evidence:** exhaustive identity separation, invalid/corrupt
model, lifecycle, version maximum, binding-matrix, fingerprint vector, replay,
conflict, and safe-result tests.

**Review/commit boundary:** leave unstaged for slice review. Do not commit or
begin MRC-S2 until the slice is accepted under separately authorized workflow.

### MRC-S2 — Durable Run creation and trusted Session participation

**Behavioral outcome:** the canonical Run service can create and strictly
reload one durable Run/line and can attach separately persisted trusted
Session participation with exact version CAS, atomic receipts, rollback, and
concurrency rejection.

**Authoritative requirement:** sections 8 through 11 of this plan.

**Prerequisites:** accepted MRC-S1 and a clean intended implementation
baseline.

**Expected production path budget:** at most nine paths, limited to:

- the two MRC-S1 paths when an already-frozen persistence conversion requires
  a narrow extension;
- new `src/deviation_protocol/application/run_service.py`;
- `src/deviation_protocol/application/ports.py`;
- new `src/deviation_protocol/infrastructure/run_persistence.py`;
- `src/deviation_protocol/infrastructure/orm_models.py`;
- `src/deviation_protocol/infrastructure/repositories.py`;
- `src/deviation_protocol/infrastructure/unit_of_work.py`;
- one next-head Alembic revision whose identifier is selected only at
  implementation time.

**Expected test path budget:** at most seven paths:

- new `tests/unit/test_run_service.py`;
- new `tests/unit/test_run_persistence.py`;
- new `tests/unit/test_run_repositories.py`;
- `tests/unit/test_repository_and_uow.py`;
- `tests/integration/test_mysql_connection.py`;
- new `tests/integration/test_mysql_run.py`;
- `tests/integration/conftest.py`.

**Persistence/migration effect:** add exactly the five section 9 record
families from the then-current single Alembic head, with no backfill and no
other schema.

**Transaction/authorization boundary:** `RunService` owns one UoW and one
commit. Session ownership is checked through the existing Repository inside
that UoW. Repositories receive the owned `AsyncSession`, flush, and never
commit.

**Compatibility:** existing `game_sessions` columns and meaning are unchanged;
legacy Sessions remain unbound; existing UoW lifecycle and player-character
repositories remain available over the same session; no public or Demo
composition is added.

**Focused verification:** all new Run unit tests; existing UoW and
player-character UoW regressions; migration heads/history and exact schema;
real-MySQL creation, reload, corruption, rollback, receipt, CAS, row-lock, and
same-/cross-Run participation races; `compileall`; Offline, MySQL, and
applicable Full verification; `git diff --check`.

**Completion evidence:** one committed effect or complete rollback for each
mutation; strict fresh-session reload; one winner for every uniqueness/CAS
race; no hidden retry; exact unchanged legacy Session and player-character
behavior.

**Review/commit boundary:** leave unstaged for slice review. No production
composition, documentation closeout, commit, or MRC-S3 begins until accepted.

### MRC-S3 — Run-aware production composition and complete prerequisite proof

**Behavioral outcome:** normal production composition can construct the
canonical `RunService` lazily with UUIDv4 Run/line issuance and the existing
SQLAlchemy UoW factory, while exposing no Run API route or gameplay behavior.

**Authoritative requirement:** minimum Run-core production reachability only;
no public activation.

**Prerequisites:** accepted MRC-S2 and a clean intended implementation
baseline.

**Expected production path budget:** at most three paths:

- new `src/deviation_protocol/infrastructure/run_authority.py`;
- `src/deviation_protocol/api/dependencies.py`;
- `src/deviation_protocol/api/main.py`.

**Expected test path budget:** at most two paths:

- new `tests/unit/test_run_composition.py`;
- `tests/unit/test_api.py` only for unchanged-route/object-graph compatibility.

**Persistence/migration effect:** none beyond the accepted MRC-S2 migration.

**Transaction/authorization boundary:** composition performs no UoW entry,
SQL, identity issuance, mutation, or commit. Runtime service calls retain the
MRC-S2 boundary.

**Compatibility:** existing routes, schemas, Session behavior, character
service, Provider selection, Demo composition, and frontend remain unchanged.
Missing optional public Run integration is not a startup error because no
public Run route is admitted.

**Focused verification:** UUIDv4 shape/validation and user-information
separation; lazy composition and object-graph tests; existing player-character
composition and API route inventory; complete Run unit/MySQL selection;
`compileall`; Offline, MySQL, and applicable Full verification; Alembic
heads/history; `git diff --check`.

**Completion evidence:** production composition exposes one canonical
RunService over the shared UoW without activation or composition-time work,
and the complete prerequisite satisfies section 15.

**Review/commit boundary:** freeze the complete unstaged minimum Run-core
candidate for a fresh independent read-only review. Only after that review and
canonical documentation synchronization may the user separately authorize
one milestone commit; the user performs the push manually.

## 13. Verification strategy and evidence

Every state mutation receives regression coverage. Verification is layered:

- pure identity, aggregate, validation, lifecycle, version, operation,
  fingerprint, replay, and result behavior in unit tests;
- persistence conversion, strict reconstruction, and corruption matrices in
  offline unit tests;
- Repository session ownership, flush/no-commit behavior, and UoW rollback in
  unit tests;
- schema, constraints, restrictive references, CAS, locks, uniqueness races,
  receipts, rollback, and fresh-session reconstruction against real MySQL 8;
- production UUIDv4 issuance and lazy composition in unit/object-graph tests;
  and
- existing Session, player-character service/UoW, API route, Demo, Provider,
  and dependency-direction regressions for compatibility.

The implementation task must run focused tests during each slice and, before
the complete-candidate review, the repository-required full tests,
`compileall`, relevant Alembic heads/history/schema checks, canonical Offline
verification, MySQL verification, and `git diff --check`. Live Provider calls
remain disabled. Web/browser commands are unnecessary because this plan
changes no Web path or public behavior.

No test count is frozen here. Completion evidence records only results
actually produced by the later implementation candidate.

## 14. Compatibility requirements

The minimum core must preserve all of the following:

- dependency direction remains toward the domain;
- MySQL 8, SQLAlchemy `AsyncSession`, and `asyncmy` remain the only production
  persistence boundary; no SQLite fallback;
- existing UnitOfWork commit/rollback/close semantics remain unchanged;
- existing player-character create, mutate, owned read, detached projection,
  controller resolution, UUIDv4 issuance, receipt, CAS, and production
  composition behavior remain unchanged;
- `game_sessions`, current Session ownership, Session state version, public
  Session DTOs, routes, action replay, and same-tab recovery remain unchanged;
- legacy Sessions receive no inferred Run participation;
- static character definitions remain content and never become canonical
  player-character identity;
- current scenario and Demo fixtures do not become a Run, world, visit, or
  continuous story line;
- no Provider or network work occurs in a Run transaction;
- Phase 3.4 NPC relationship/residence authority remains separate; and
- Phase 5 public projection and activation remain deferred.

## 15. Independent review, documentation, and Git gates

Under the Approval-token consistency requirement in
`docs/engineering/codex_workflow.md`, the sole operative success verdict for
the P4-G0 independent read-only review is
`STRUCTURED_PLAYER_CHARACTER_P4_G0_REVIEW_APPROVED`. Only that exact verdict,
if returned for this complete candidate, can satisfy the P4-G0 independent-review
approval condition. A reference to this token in another document is a
cross-reference to this single canonical declaration, not a second verdict
definition. Historical report tokens, author-completion tokens,
changes-required tokens, blocked tokens, and illustrative example tokens are
non-operative for closing P4-G0.

The completed P4-G0 approval order was:

1. complete this P4-G0 five-document candidate;
2. conduct a fresh independent read-only review of the complete candidate;
3. correct only concrete review findings and obtain a new review if bytes
   change;
4. obtain separate authorization for one documentation milestone commit;
5. create that resulting local milestone; the user next pushes it manually and
   confirms a new clean baseline;
6. implement MRC-S1 through MRC-S3 under separate scoped authority;
7. conduct a fresh independent read-only review of the complete minimum
   Run-core candidate;
8. complete the canonical documentation-synchronization checklist, including
   updating `docs/architecture.md` only for behavior that then exists;
9. obtain separate authorization for the minimum Run-core milestone commit;
10. the user pushes that commit manually and a new clean baseline is
    confirmed;
11. begin P4-S1 only under separate explicit authorization; and
12. leave Phase 5 and later public activation deferred.

No review verdict, candidate hash, migration revision, commit, push, or
verification result is predicted by this plan.

## 16. Explicit exclusions

Neither P4-G0 nor the minimum Run-core prerequisite authorizes:

- player-character binding before P4-S1;
- a complete Phase 3.3 implementation;
- world generation, entry-world catalogue behavior, later-world selection,
  visit mechanics, world-line transitions, or scenario execution;
- Run Protocol profile/difficulty resolution or prompt serialization;
- NPC residence, relationship progression, golden memory, or NPC recovery;
- inventory, quest, combat, progression, or generalized consequence systems;
- narrative generation, Provider changes, live-model calls, or prompt work;
- API routes, DTO activation, frontend components, Demo changes, browser
  behavior, or public gameplay activation;
- public resume, reconnect, cross-tab, browser-restart, or multi-device
  behavior;
- account registration, Steam integration, permission administration,
  controller transfer, or a second player-character model;
- character cloning, transfer, replacement, automatic rebinding, or
  reference-following policy;
- event sourcing, distributed transactions, outbox/saga behavior, generalized
  retries, uncertain-commit recovery, background workers, or monitoring
  infrastructure;
- receipt TTL, cleanup, deletion, archival, or rejected/pending receipts;
- schema backfill from existing Session, principal, scenario, character
  definition, browser, or prose data; or
- unrelated refactoring, configuration, dependencies, generated artifacts, or
  deployment.

## 17. Minimum Run-core completion criteria

The prerequisite is complete only when implemented code and evidence prove:

1. distinct stable validated `RunId` and `ContinuousStoryLineId` values with
   permanent one-to-one ownership and no reuse;
2. strict canonical `pre_first_turn` Run state and positive monotonic
   `RunStateVersion`;
3. durable current state and immutable revisions with exact CAS and
   reconstruction;
4. immutable separate Session participation with trusted ownership checking,
   multiple Sessions per Run, and no Session routed to conflicting Runs;
5. atomic successful creation and participation receipts with deterministic
   replay/conflict behavior;
6. one service-owned UoW and one commit per mutation, complete rollback on
   every failure, and no generalized retry;
7. an all-null reserved binding envelope and database uniqueness/reference
   seam ready for P4-S1 but no populated binding;
8. fail-closed corruption, identity mismatch, uniqueness, stale-version, and
   CAS behavior;
9. lazy Run-aware production composition with no API/public activation;
10. unchanged legacy Session, player-character, Provider, Demo, scenario, and
    public behavior;
11. a single then-current Alembic head and complete required verification;
12. synchronized implementation documentation and fresh independent review;
    and
13. truthful status that only the minimum prerequisite is implemented while
    P4-S1 and the full Run Protocol remain unimplemented.

## 18. Deferred work

The following remain outside the minimum prerequisite:

- authorization and implementation of Run transitions from
  `pre_first_turn`;
- resolved Run Protocol/profile storage and compatibility;
- entry-world and visit identities and persistence;
- later-world selection, revisit, transition, region, and world-line rules;
- Run completion/termination commands and their exact product triggers;
- arbitrary restart/resume, Session reassignment, reconnect, successor,
  replacement, or cross-Run movement;
- P4-S1 population of the character-binding envelope;
- any future approved applicable-character-reference following/change policy;
- later Phase 4 scenario and world-transition integration;
- Phase 3.4 NPC relationship/residence implementation; and
- Phase 5 public projection or narrow boundary activation.

None of these deferrals supplies authority to infer a default or widen the
minimum implementation.
