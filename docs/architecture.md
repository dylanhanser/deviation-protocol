# Deviation Protocol Architecture

This document describes implemented architecture first. Sections named for
earlier phases preserve the implementation history of those boundaries; they
do not make later accepted designs current capabilities.

## Structured player-character Phase 1 pure foundation

The approved and frozen structured player-character plan now has a Phase 1
pure foundation that passed fresh independent read-only acceptance for the
exact nine-path candidate. This acceptance applies only to Phase 1; the
complete plan remains partially implemented.

`domain.player_character` owns distinct player-character, controller-binding,
operation, revision, contract, applicable-reference, and subject-reference
types; the complete strict v1 record envelope; four-state optional
declarations for every approved slot; adult-only proof; player-expression or
confirmation authority for subjective state; empty first-slice development;
and no unowned story-line binding or narration default. Complete-record
validation fail-closes on the admitted creation, retirement, and final-death
provenance/lifecycle/authority combinations and applies one lossless aggregate
65,536-byte canonical UTF-8 declaration envelope without field-specific text
or collection limits. A fixed 65-feature creation regression proves that the
former arbitrary 64-item ceiling remains absent. Exposed creation,
complete-record, reference, command, receipt, and policy boundaries recursively
inspect exact instance fields plus Pydantic extra, private, and fields-set
state, then revalidate the original instance without first dumping, repairing,
coercing, defaulting, or dropping source state. An already-instantiated
Pydantic object is therefore not treated as proof of validity.
`domain.player_character_policies` owns independent pure creation, retirement,
reactivation, final-death, and authorized-continuity-return policies.
Retirement and trusted final death produce detached, fully revalidated
successor records. Reactivation and return from death fail closed because the
required Run/continuity authorities do not exist and cannot have a Phase 1
success-result representation.

`application.player_character_operations` owns the separate
`player-character.create/v1` and `player-character.mutate/v1` receipt
namespaces and their non-interchangeable keys. It defines NFC UTF-8 canonical
JSON, sorted normalized object keys, ordered sequences, no floats or ambiguous
values, signed-integer and total-byte bounds, SHA-256 fingerprints, strict
privacy-safe stored success results, exact replay and deterministic mismatch
decisions, authorization-before-disclosure behavior, and the required
creation/mutation/unique-race transaction order for later persistence. Mutation
fingerprints bind the same typed applicable reference supplied to policy
evaluation; the reference selects no following or migration behavior.
Player-character revisions use the positive canonical signed 64-bit domain.
Revision `9223372036854775807` remains a readable existing revision, but it has
no representable successor: direct policy and operation processing reject that
transition before fingerprint serialization, receipt lookup, success-result
construction, or stored-success disclosure. A valid transition from
`9223372036854775806` to `9223372036854775807` and its exact replay remain
supported.
Mutation replay revalidates the complete current record before lookup and
checks the stored result against its key, fingerprint, command, subject,
contract, revision, lifecycle, provenance-mutation, and authority semantics;
unavailable operations and semantically impossible receipts disclose no stored
success. The 65,536-byte limit belongs only to the complete canonical
declaration envelope. Creation fingerprint serialization remains deterministic
and binds all required operational metadata without applying that declaration
ceiling to the larger command.
Checked-in unit vectors fix the exact canonical bytes and fingerprints for
creation and every Phase 1 mutation command.

This Phase 1 boundary is a pure protocol/domain foundation. It adds no
Alembic revision, ORM row, receipt table or repository, Unit of Work port, ID
issuer, controller resolver, canonical persistence, production transaction
wiring, public route, projection, frontend, Provider integration, Demo
behavior, Session request/action behavior, or Run/story-line binding. Later
bounded persistence slices do not change that ownership.

## Structured player-character Phase 2 Slices 1–4 persistence boundary

Phase 2 Slice 1 is implemented, independently accepted, committed, and pushed.
It adds application persistence ports plus exactly six database-independent
stored carriers, strict canonical record and receipt codecs, state-record
fingerprints, and aggregate cross-record integrity validation. Those carriers
remain non-authoritative and perform no ORM, repository, clock, or I/O work.

Phase 2 Slice 2 is implemented and verified, received independent review with
no remaining substantive issue, was committed as
`a2802799b3d3a5497f4fc097b0cc05d573d8e0ca`, and was pushed to `origin/main`.
Shared SQLAlchemy metadata contains exactly these six private mappings:

- `player_character_controller_bindings`;
- `player_character_id_allocations`;
- `player_character_current`;
- `player_character_revisions`;
- `player_character_creation_receipts`; and
- `player_character_mutation_receipts`.

All six use InnoDB with `utf8mb4_bin` table defaults. Opaque references and
closed tokens use exact `ascii_bin` columns, fingerprints use `BINARY(32)`,
canonical records and evidence use binary blob carriers, and timestamps use
server-supplied `DATETIME(6)` values without database defaults. Natural keys,
named checks, the exact unique and ordinary indexes, and twelve named
`RESTRICT` foreign keys encode the frozen physical contract without adding a
seventh family. The corrected `ck_spc_revisions_provenance_matrix` explicitly
requires non-NULL `prior_revision` for both `RETIRE` and `FINAL_DEATH`.

Alembic revision `20260728_0004` directly follows `20260719_0003` and is the
single head. It adds no backfill and leaves legacy Session data and schema
unchanged. The migration declares the complete child index inventory before
adding foreign keys so MySQL does not generate undeclared indexes. Downgrade
first probes all six tables and refuses before destructive DDL if any contains
data; only an empty new schema may be removed.

Phase 2 Slice 3 is implemented and independently approved. Its four existing-
port MySQL Repository adapters receive caller-owned `AsyncSession` instances
and provide controller-binding registry, character allocation/current/history,
and creation/mutation receipt operations. They reconstruct persisted values
only through the committed Slice 1 codec and canonical identity authorities,
retain immutable revision history, use exact current-row CAS and SQL row
locking, and return the frozen creation and mutation receipt forms. Adapters
may execute authorized SQL and `flush()`, but own no commit, rollback, retry,
transaction recovery, or application workflow. The boundary adds only
`PlayerCharacterRepositoryError` and
`PlayerCharacterRepositoryConflictError` as narrow infrastructure errors.

Real-MySQL evidence covers persistence, constraints, conflicts, CAS
concurrency, exact-row locking, and caller rollback; offline unit evidence
covers corrupt state and persistence-boundary failures.

Phase 2 Slice 4 is implemented and verified locally and received new-session
independent implementation approval with verdict
`PHASE_2_SLICE_4_IMPLEMENTATION_INDEPENDENTLY_APPROVED`; no blocking findings
remained.
`SqlAlchemyUnitOfWork.__aenter__` now constructs the controller-binding,
player-character, creation-receipt, and mutation-receipt adapters over the
same active `AsyncSession` already used by the existing repositories.
SQLAlchemy lazy autobegin remains authoritative: entry performs no SQL and
opens no explicit transaction; repository methods may flush; successful test
workflows commit explicitly; and uncommitted, exceptional, cancellation, and
controlled pre-COMMIT failure paths roll back and close. No other UoW
lifecycle method changed.

Evidence is limited to `tests/unit/test_repository_and_uow.py` and
`tests/integration/test_mysql_player_character.py`. It covers same-session
Repository wiring, lazy autobegin preservation, explicit UoW commit ownership,
normal, exceptional, and cancellation rollback, atomic creation and replay,
controlled pre-COMMIT failure rollback, a genuine uniqueness race with loser
rollback and fresh-UoW winner recovery, atomic mutation and replay after a
later revision, and mutation rollback across history, current row, and receipt.
This session passed the focused UoW unit selection (`16 passed`), focused
structured-character MySQL selection (`34 passed`), MySQL verifier
(`81 passed`), Offline verifier (`1,389 passed, 71 skipped`), and Full verifier
(`1,459 passed, 1 skipped`), plus `compileall`, Alembic heads/history,
dependency checks, and `git diff --check`.

Phase 2 is independently accepted and complete. Failed sessions are not
reused, no automatic retry was added, and connection-loss or uncertain-COMMIT
recovery and exactly-once behavior remain excluded. The test-only orchestration
is not a production application service. No runtime service, API, public route,
frontend, Provider, Demo, Session, Run, story-line, narrative, content, or
gameplay integration was activated. Structured player-character Phase 3 is now
implemented and complete: P3-S1 through P3-S4 are complete, and the complete
code candidate received independent read-only approval with no implementation
finding remaining open. Minimum Run Core is implemented, independently finally
  approved, committed, and pushed as `e821cd922b61868097667b12c2b64cf8089a9681`
  (`feat(run): implement minimum run core`). That null-only seam is the
  historical prerequisite baseline. P4-S1a is implemented at
  `748003319ececa548b68b351746afbb2d54c66bb`, and P4-S1b is implemented and
  pushed at `8eabf9d4c3c592ea1de50f443f1816de9a46dc8f`. The completed P4-S1
  boundary provides internal Run-owned binding only; the constructible Run
  lifecycle remains `pre_first_turn`, the reserved public
  `RunService.bind_player_character(...)` command remains rejected, and no
  public Run or gameplay behavior is activated.

## Structured player-character Phase 3–5 boundaries

P3-S1 canonical creation orchestration is implemented, independently approved,
committed, pushed, complete, and closed at
`7606e51523338247ea33ed9329346fdba046d29b`
(`feat(player-character): add race-safe creation recovery`). Its bounded
correction completed final independent implementation review and preserves the
boundary described below. The earlier recovery-provenance defect, typed-conflict
ownership contradiction, and rejected first amendment are historical; the
implemented correction requires exact exception-instance provenance and fails
closed when the initial Unit of Work suppresses the original conflict. The
three-document P3-S1 closure status synchronization was then committed and
pushed at the pre-closure `main`/local-`origin/main` baseline
`150074d58cdbf3aee08bea9c1084325b2b0f0a3f`
(`docs(player-character): close phase 3 slice 1 status sync`). P3-S2 mutation
orchestration, P3-S3 owned read and detached projection, and P3-S4 production
composition are implemented. The complete Phase 3 code candidate received
independent read-only approval, and no implementation finding remains open.

Structured player-character Phase 3 owns trusted application orchestration and
its later normal production composition. Its independently reviewable order is
creation orchestration, mutation orchestration, owned read plus detached self
projection, then normal MySQL composition with separately accepted production
controller resolver and player-character ID issuer adapters. Phase 4 retains
Run and continuous-story-line binding. Phase 5 retains public projection and
narrow authenticated activation. API routes, frontend and Demo parity are not
ordinary Phase 3 composition, and Run binding is not moved into it.

The P5-S1 scope, represented by the exact candidate or commit identified by
applicable exact-candidate review evidence and Git history, is limited to
`GET /v1/player-characters/{player_character_id}`. In the normal application,
the route receives the development-only trusted-principal dependency, delegates
unchanged ownership enforcement and strict reconstruction to
`PlayerCharacterService.get_owned`, and returns its detached
`PlayerCharacterSelfProjection`. The route is registered only when normal
composition supplies that service; the independent Demo composition supplies no
Player Character service and does not register the path. Missing, foreign, or
unmapped access converges on the same public 404 envelope. This does not make
the fixed development principal production authentication or permit Internet
deployment; `AUTH-001` remains mandatory.

The P5-S2 implementation was independently approved, committed, and published
at `4ba66d8f277988325795c905fdf6fd9e416d7457`
(`feat(player-character): add creation API`). The normal application adds only
`POST /v1/player-characters` beside the preserved P5-S1 GET. It
derives controller identity only from the trusted dependency, validates the
frozen JSON and `Idempotency-Key` transport boundary, and delegates one create
call to the existing service. First creation and exact replay share the same
200 detached projection; conflicting operation reuse is 409, unavailable
authority is non-enumerating 404, and validation, corrupt-receipt,
unsupported-recovery, ordinary persistence, and uncertain-commit failures are
sanitized without a success claim or generic retry. Cancellation propagates and
the existing Unit of Work rolls back. The durable creation family remains the
controller binding, allocation, revision-one history, current state, and
creation receipt; only the admitted controller-binding uniqueness race permits
one fresh read-only winner recovery. Normal composition reuses the existing
controller resolver and lazy MySQL Unit-of-Work graph, including the internal
Run evidence seam. Demo supplies no Player Character service and exposes
neither Player Character route or OpenAPI path; frontend creation remains
inactive, production authentication is incomplete, and Internet deployment
remains unsupported.

The dedicated
[P5-S3 retirement activation plan](structured_player_character_p5_s3_implementation_plan.md)
received `STRUCTURED_PLAYER_CHARACTER_P5_S3_PLAN_APPROVED`. Its first local
implementation candidate received `CHANGES_REQUIRED`; the first corrected and
re-corrected candidates each received another fresh `CHANGES_REQUIRED` review.
The third review found no production-code defect and requested corrected test
and history evidence. The later evidence candidate obtained a receipt-add 1062
only by rolling back the original mutation transaction and resuming the stale
operation. The focused investigation verdict
`P5_S3_RECEIPT_ADD_RACE_NOT_REACHABLE_UNDER_CURRENT_PRODUCTION_PATH` established
that legitimate production writers serialize at the aggregate `FOR UPDATE`
boundary. The accepted implementation exposes
only the normal-application
`POST /v1/player-characters/{player_character_id}/retirement` boundary over
  the committed `PlayerCharacterService.mutate` and P4-S1 guard. Its focused
  final independent review returned
  `STRUCTURED_PLAYER_CHARACTER_P5_S3_FOCUSED_FINAL_REVIEW_APPROVED`, finding no
  material scoped defect. It accepted real-MySQL aggregate-lock serialization,
  exact replay or ordinary idempotency conflict, and one durable mutation; fault
  injection is bounded defensive recovery only, and the unreachable receipt-add
  race is not a requirement. P5-S3 was committed and published as
  `34d063e387cde69500e4dc018ff087e87f3eee74`
  (`feat(player-character): add idempotent retirement endpoint`). Phase 5 is
  complete at P5-S3; no P5-S4 exists and no P5-S3 review remains pending. It is
  not deployed or activated in Demo, public Run, frontend, Web,
  administration, or production; release and Provider work remain deferred.

P3-S1 adds only an injectable application service boundary over the accepted
Phase 1 and Phase 2 authorities. Typed `RequestPrincipal`,
`PlayerCharacterOperationId`, and `CharacterCreationCommand` construction owns
structural input validation. `CharacterCreationCommand` calls
`canonical_player_declaration_bytes`; later `creation_fingerprint` and
`evaluate_creation_receipt_protocol` defensively revalidate the actual typed
instance. `CreatePlayerCharacterPolicy.create` owns trusted creation policy,
and `validate_canonical_player_character` owns complete-record validation.
Repository codecs retain persistence representation and stored cross-record
integrity. The service sequences these authorities; it introduces no second
generic validation or policy system.

Principal-to-controller mapping is a separate trusted boundary. A valid
`RequestPrincipal` is input to resolution, not a controller binding by itself.
An absent, invalid, unknown, or untrusted mapping returns
`AUTHORIZATION_FAILED` before the initial UoW. A missing registry row never
authorizes a principal: the service may insert one only after the trusted
resolver returned that exact valid `ControllerBindingRef`. It must not
auto-register, auto-bind, copy `RequestPrincipal.player_id`, or consult
player-character persistence to invent authority.

Permanent character identity issuance is likewise separate from controller
identity and persistence. P3-S1 may call the injected issuer exactly once only
after binding authorization and the exact receipt protocol returns
`READY_FOR_NEW_OPERATION`. Exact replay never calls the issuer. The allocation
Repository remains the uniqueness backstop; an allocation collision propagates
the existing repository conflict, causes rollback, and never triggers another
identity issuance.

The production controller resolver uses an explicit configured allowlist and
matches only the complete exact `(authentication_scheme, player_id)`
`RequestPrincipal` identity. It returns only the configured `controller_id`;
unknown or invalid principals receive no authority. Configuration is immutable
or defensively copied, strict, duplicate-safe, and value-free in errors.
Resolution performs no database or UnitOfWork work, automatic registration,
development-principal fallback, partial matching, or ownership derivation.
When typed bindings are not supplied directly,
`PLAYER_CHARACTER_CONTROLLER_BINDINGS` is required runtime JSON. Missing,
empty, malformed, incomplete, non-canonical, duplicate-principal, or
shared-controller configuration fails closed before catalog, engine, database,
or UnitOfWork construction.

The production issuer directly uses Python standard-library `uuid.uuid4()`;
operating-system randomness supplies the UUID entropy. It formats the result as
`pc.<32 lowercase UUIDv4 hexadecimal digits>` and validates it through
`PlayerCharacterId`. The ID contains no principal, controller, timestamp,
sequence, or other user information. Production exposes no injection seam
that can replace UUIDv4 generation. Persistence uniqueness failures continue
to fail closed, and no generalized creation retry was introduced.

The application service owns `UnitOfWorkFactory` use, UoW entry and the one
explicit success-path `commit()`. Repository adapters own only their accepted
SQL/flush behavior and never commit. `SqlAlchemyUnitOfWork` rolls back and
closes every uncommitted, exceptional, cancellation, and controlled
pre-COMMIT-failure path. A SQL-failed session is never reused. Success is
returned only after commit returns.

The application/port layer may own the one narrow typed exception contract
`application.ports.ControllerBindingUniquenessConflictError` for only the
approved controller-binding uniqueness race. Infrastructure may satisfy that
contract through the correspondingly narrow concrete adapter exception
`infrastructure.errors.PlayerCharacterControllerBindingConflictError`.
The concrete exception must remain a
`PlayerCharacterRepositoryConflictError` for existing infrastructure
compatibility, but the existing shared
`PlayerCharacterRepositoryConflictError` must not inherit or implement the
narrow application contract. Allocation, initial revision/current, creation
or mutation receipt, missing-current, stale-current, and every other shared
Repository conflict therefore remain distinguishable and do not satisfy the
narrow contract.

This dependency direction is intentional. Infrastructure already depends on
application ports and may import the narrow application-owned contract.
Application code must not import `deviation_protocol.infrastructure` or any
concrete infrastructure error. `PlayerCharacterService` imports only
`ControllerBindingUniquenessConflictError` and places its static `except`
boundary immediately around the awaited `controller_bindings.add` call.
This scoped contract does not establish a generic application persistence-error
hierarchy, a second conflict contract, or an application translation of MySQL
or SQLAlchemy exceptions.

The exact infrastructure translation remains local to
`SqlAlchemyControllerBindingRegistryRepository.add`. Its
`PlayerCharacterControllerBindingRow` flush contains only that row, and
`player_character_controller_bindings.controller_binding` is the table's sole
unique key because it is the primary key. The existing
`_is_mysql_duplicate_key` test therefore identifies a duplicate of that exact
binding at that exact flush. A narrowly parameterized `_flush_row` call may
select `PlayerCharacterControllerBindingConflictError` there while every other
call retains the default shared conflict. No message matching, dynamic import,
reflection, classifier, wrapper, generic marker, or broad `_flush_row`
refactor is authorized, and existing exception chaining and diagnostics remain
intact.

Fresh-UoW winner recovery requires both conditions: the narrow
`ControllerBindingUniquenessConflictError` identity is raised, and it is raised
synchronously by the exact `controller_bindings.add` call enclosed by the
service's narrow catch boundary. The type alone never authorizes recovery at a
later operation or different call site. The failed initial UoW must first
fully exit, roll back, close, and be discarded. At most one different fresh
UoW may reauthorize, lock the same binding, perform the second direct operation
ID revalidation before constructing the recovery receipt key, read the exact
creation receipt, and call `recover_creation_unique_race_winner`. If that
revalidation fails, its original exception propagates unchanged and recovery
performs exactly zero receipt lookups.

The corrected service records the exact exception only at that enclosed add
boundary, re-raises it through the failed initial UoW, and authorizes recovery
only when the outer handler observes the same exception object after UoW exit.
If `__aexit__` suppresses that exception, the preserved original object is
raised fail-closed: no fresh UoW is created, no recovery binding lock or receipt
lookup occurs, and no success or replay result is returned. A different
same-type exception from UoW entry, exit, rollback, close, commit, or any other
operation cannot satisfy the identity check.

Recovery remains prohibited for allocation, creation-receipt, initial
canonical-state, stale or missing-current, other Repository-operation,
authorization, validation, policy, issuer, generic database, UoW enter/exit,
rollback/close, commit, and uncertain-commit failures. An approved recovery
performs no write, policy call, second allocation, second issuance, or generic
retry. No retry or receipt lookup follows an uncertain commit outcome.

Existing validation exceptions, protocol decisions, policy decisions,
`PlayerCharacterRepositoryError`,
`PlayerCharacterRepositoryConflictError`, and
`PlayerCharacterStoredRecordIntegrityError` cross the application boundary
without a new generic error hierarchy or broad infrastructure translation.
Cancellation propagates unchanged. Callers own every retry decision outside
the single narrow binding-insertion winner read. A controlled failure before
`AsyncSession.commit` begins makes no durability claim beyond rollback
evidence; an exception with uncertain commit durability is propagated without
a recovery read or a success/replay claim. Exactly-once execution is not
claimed.

The frozen P3-S1 implementation gate capped the approved implementation at
exactly `4 + 2 + 3` paths: production changes were permitted only in
`src/deviation_protocol/application/player_character_service.py`,
`src/deviation_protocol/application/ports.py`,
`src/deviation_protocol/infrastructure/errors.py`, and
`src/deviation_protocol/infrastructure/repositories.py`; test changes were
permitted only in
`tests/unit/test_player_character_service.py` and
`tests/integration/test_mysql_player_character_service.py`; documentation
synchronization changes were permitted only in `PLANS.md`, this document, and
`docs/structured_player_character_implementation_plan.md`. No dependency,
schema, migration, ORM, UoW, API, composition, Demo, frontend, Provider, Run,
narrative, scenario, content, or gameplay path was authorized. Commit
`7606e51523338247ea33ed9329346fdba046d29b` satisfied this historical gate; its
documentation synchronization was later committed and pushed as
`150074d58cdbf3aee08bea9c1084325b2b0f0a3f`. The present documentation
synchronization records the completed Phase 3 milestone without claiming that
its local closure commit has been pushed.

The completed P3-S1 implementation stays within that boundary. It adds
the injectable creation service and the two typed conflict symbols, selects the
binding-only subtype at the exact controller-binding row flush, requires outer
exception-instance identity after failed-UoW disposal, fails closed on
suppression, and supplies focused unit and MySQL integration tests. It changes
no schema, migration, ORM, UoW, composition root, API, Demo, Provider, Run,
narrative, scenario, content, or gameplay path. It completed final independent
review, commit, and push; no further P3-S1 implementation review is pending.

The implemented P3-S2 boundary is one
`PlayerCharacterService.mutate` method on the existing service. It resolves
the trusted controller before one initial UoW, locks and reconstructs the
target current record, authorizes that record's stored controller binding
before disclosure, defensively validates the typed command, operation ID, and
revision domain, constructs the mutation receipt key only afterward, and
evaluates the already-read immutable receipt before stale rejection. Exact
replay returns only the original committed safe result without policy,
history, CAS, receipt insertion, or commit. A new operation verifies the exact
target, contract, applicable reference, and expected revision, evaluates
exactly one existing mutation policy, validates the complete detached
successor, appends immutable history, performs the existing version-checked
current-row CAS, adds the immutable success receipt, commits once, and returns
success only after commit returns. P3-S2 applies no Run/story-line continuity
effect and activates no public runtime path.

`compare_and_swap_current(...) == False` has one outcome:
`CharacterOperationProtocolDecision` for
`player-character.mutate/v1` with code `STALE_REVISION`. It is returned from
inside the still-uncommitted initial UoW, whose normal exit rolls back the
already-flushed successor history and closes the session. CAS loss performs no
receipt add, commit, recovery read, generic retry, state reuse, or
uncertain-commit recovery.

The existing locked-current workflow serializes compliant P3-S2 writers, so a
mutation-receipt insert race is not the normal same-service concurrency path.
The physical mutation-receipt table nevertheless has both its exact operation
primary key and its one-result-per-revision unique key, and the existing
Repository reports duplicate-key insertion through the shared
`PlayerCharacterRepositoryConflictError`. P3-S2 uses one defensive,
application-owned
`MutationReceiptUniquenessConflictError` and one concrete
`PlayerCharacterMutationReceiptConflictError`, selected only by the exact
row-only `_flush_row` call in
`SqlAlchemyPlayerCharacterMutationReceiptRepository.add`. Existing preflight
key/result conflicts, revision/current conflicts, and every other Repository
operation retain their original shared identities.

The service may catch the narrow application contract only immediately around
that exact `mutation_receipts.add` call. It must record and re-raise the exact
exception through the failed initial UoW, then confirm that the same object
escaped after rollback, close, and disposal. Only then may at most one
different fresh UoW re-resolve authority, lock and validate the current
record, revalidate the operation ID before key construction or lookup, read
the exact durable receipt, and call the existing
`recover_mutation_unique_race_winner`. Compatible evidence returns only the
already committed winner; incompatible reuse returns
`IDEMPOTENCY_CONFLICT`; missing or invalid winner evidence fails closed.
Suppression, a different same-type exception, any shared conflict, commit
failure, or uncertain commit outcome authorizes no recovery. There is no third
UoW, write retry, policy retry, commit in recovery, or exactly-once claim.

For the current composed retirement writer, this recovery is defensive rather
than a reachable same-service race path. Real-MySQL HTTP evidence must show two
distinct connections/UoWs serializing at the aggregate lock: after the winner
commits one revision and one mutation receipt, the waiter observes exact replay
for an identical fingerprint or ordinary idempotency conflict for a different
fingerprint, with no second policy mutation, receipt-add conflict, or 1062.
Existing service-unit fault injection proves the bounded recovery branch, while
the direct repository flush test proves only test-topology constraint
translation. A real receipt-add 1062 race becomes mandatory only if a future
composed runtime writer or changed transaction topology can legitimately reach
receipt uniqueness without first serializing on this aggregate lock; no such
writer or topology is approved here.

The historical P3-S2 gate capped implementation at `4 + 2 + 3` paths:
`src/deviation_protocol/application/player_character_service.py`,
`src/deviation_protocol/application/ports.py`,
`src/deviation_protocol/infrastructure/errors.py`,
`src/deviation_protocol/infrastructure/repositories.py`,
`tests/unit/test_player_character_service.py`,
`tests/integration/test_mysql_player_character_service.py`, `PLANS.md`, this
document, and
`docs/structured_player_character_implementation_plan.md`. No domain,
operation-helper, persistence-codec, ORM, migration, UoW, dependency,
composition, API, Demo, frontend, Provider, Run, narrative, scenario, content,
or gameplay path was authorized. The implementation completed within that
boundary and received independent read-only approval as part of the complete
Phase 3 candidate.

P3-S3 implements `get_owned`. Controller authority resolves before UnitOfWork
construction. Missing and wrong-owner characters both return `None`; stored
identity and state are revalidated. Success is a detached, frozen, allowlisted
projection containing only ID, contract version, current revision, and
lifecycle. The read performs no write, lock, receipt operation, commit, retry,
or recovery.

P3-S4 makes the canonical service available from
`build_default_services()` as `ApiServices.player_character_service`. It
reuses the established lazy `SqlAlchemyUnitOfWork` factory and the existing
repositories and policies; create, mutate, and `get_owned` remain available.
Composition itself performs no UnitOfWork, SQL, ID issuance, or mutation.
Supported startup fails closed when required controller-binding configuration
is absent, and no fake or development resolver or fake issuer is installed.

P5-S1 owned read, P5-S2 creation/replay, and P5-S3 normal-application
retirement are published Player Character API surfaces. Other Player Character
API activation remains deferred. P5-S3 received
`STRUCTURED_PLAYER_CHARACTER_P5_S3_PLAN_APPROVED`; its first, first-corrected,
and re-corrected candidates received `CHANGES_REQUIRED`; the later evidence
  candidate was followed by the focused not-reachable verdict above. The accepted
  correction passed local validation (canonical Offline 1,814 passed/124 expected
  skips, MySQL 136 passed, and Full 1,937 passed/one opt-in Provider skip). Its
  focused final independent review returned
  `STRUCTURED_PLAYER_CHARACTER_P5_S3_FOCUSED_FINAL_REVIEW_APPROVED` with no
  material scoped defect, accepting real-MySQL serialization, replay/conflict,
  and one durable mutation, and fault injection only as bounded defensive
  recovery; the unreachable receipt-add race is not a requirement. P5-S3 was
  committed and published at `34d063e387cde69500e4dc018ff087e87f3eee74`.
  Phase 5 is complete at P5-S3, no P5-S4 exists, and P5-S3 remains closed. It
  is not a current unstaged candidate, and Phase 8 planning does not reopen it.
  Deployment, release, broader runtime activation, and Provider work remain
  deferred.
P4-S1 itself activated no frontend, Demo, Provider, Run Protocol, narrative,
scenario, combat, or broader public gameplay behavior. Later Phase 5 and Phase
8 activation is described below. P4-S1 alone is complete; no broader Phase 4
completion is implied.

## Phase 8 Run-entry and playable-loop boundary

Phase 8 is explicitly allocated to Structured Player Character Run Entry and
the Minimum Playable Loop. Its approved and published planning authority is
[`structured_player_character_run_playable_loop_plan.md`](structured_player_character_run_playable_loop_plan.md).
The approved planning bytes were committed and published at
`de4d8c0e35c7864948306d751a00aaf295ff77ff`, so P8-G0 is complete and
published. P8-S1 eligible-character discovery is implemented, accepted,
committed, and published. P8-S2 atomic internal Run entry is implemented,
accepted, committed, and published at
`70815b181624e5475d2d978bef0db1ed3b22324e`
(`feat(player-character): add durable run-entry initialization`); its
implementation and F1/F2/F3 evidence are closed and are not reopened. The
[P8-S3 implementation plan](structured_player_character_p8_s3_implementation_plan.md)
was independently approved and committed/published at
`e17172ad0a9febe4ec9e3a96e7be8204c9722d29`. The first independent review of
its local implementation candidate returned `CHANGES_REQUIRED` with five
bounded findings, and all five corrections are complete. A subsequent
independent read-only re-review found no remaining actionable technical defect
but formally returned `CHANGES_REQUIRED` solely for one Medium documentation-
synchronization finding. The complete 15-path candidate then received focused
independent read-only approval and was committed and published at
`ac07a5fe267adfb0281ec2658b2fcbd0085f6eb1`. P8-S3 is complete. The dedicated
[P8-S4 implementation plan](structured_player_character_p8_s4_implementation_plan.md)
was independently approved and committed/published at
`375a2a7ae018c9c9c79272e5de7da703818d1f20`. Its implementation received
`STRUCTURED_PLAYER_CHARACTER_P8_S4_IMPLEMENTATION_CORRECTION_INDEPENDENT_REVIEW_APPROVED`,
was committed as `187d41ba3035c8d717c2fb2578a805402255d979`, and was
manually published by the user. P8-S4 deterministic Demo parity is complete.
The dedicated
[P8-S5 implementation plan](structured_player_character_p8_s5_implementation_plan.md)
was independently approved and committed/published at
`dceecaf0d7a33ccde07f519f83997489acd5fc86`, remained frozen during
implementation, and its corrected implementation received
`STRUCTURED_PLAYER_CHARACTER_P8_S5_CORRECTED_IMPLEMENTATION_REVIEW_APPROVED`.
The exact eight-path Web implementation was committed and published at
`2ce56a757beed8a3989d38453da3b6d80342ca05`. P8-S5 is complete. The frozen
P8-S6 implementation plan was approved and published at
`4edf2e3341e60632765b85796e8554797c645692`. Its fresh executable evidence now
passes through C21; these current documentation bytes remain an unapproved,
unstaged, uncommitted, and unpublished implementation candidate. Phase 8, Phase
6, Phase 7, the Structured Player Character programme, and the overall project
remain incomplete pending the plan-defined review, commit, publication, and
aligned-ref gates.
Later modifications to the planning-authority bytes require exact-byte
independent review before a separately authorized documentation commit; that
commit precedes user publication and clean published-baseline confirmation.

The published P8-S3 implementation registers exactly one normal-composition
`POST /v1/runs` operation. Normal composition constructs one lazy
`RunEntryService` from the exact existing `RunService` issuers, source, clock,
controller resolver, Player Character evidence reader, shared SQLAlchemy UoW
factory, and already-built `SessionService`. The API adapter owns no UoW,
repository call, commit, replay lookup, retry, or post-result persistence; it
forwards the trusted principal and one strict command to the existing entry
coordinator at most once. P8-S4 leaves that normal composition unchanged and
composes the same Player Character, Run, Run-entry, and Session services in the
independent Demo root over one process-local store. Existing conditional route
registration now exposes the already-defined Player Character operations and
`POST /v1/runs` in Demo without duplicate routes or OpenAPI operations.
Real-MySQL production-ASGI evidence remains owned by P8-S3. P8-S4 added no
MySQL or live-Provider claim.

The Phase 8 architecture reuses the current MySQL/`AsyncSession` Unit of Work,
Player Character aggregate and detached projection, Run revision/current/
receipt families, P4-S1 binding seam, separate Session participation, existing
Session initialization/action/View lifecycle, and independent deterministic
Demo composition. Through P8-S5 all five items below are implemented:

- a bounded owned, active, currently unbound character discovery query;
- one application-owned atomic admission transaction that creates Run/line,
  binds the exact applicable character reference, creates one Session and
  participation, and changes the Run from `pre_first_turn` to `active`;
- one normal `POST /v1/runs` route plus exact public DTO/OpenAPI behavior;
- process-local Demo adapters for the existing Player Character and Run ports;
  and
- the P8-S5 minimum existing-Web create-or-reuse/select/start connection.

The primary Web composition now joins scenario discovery and eligible Player
Character discovery, creates one minimal character only when the eligible set
is empty, enters a Run with the selected exact projection revision, persists
the validated returned Session recovery record before loading the authoritative
View, and then reuses the established action/request-status/View/terminal loop.
The client does not call the legacy `POST /v1/sessions` route on this primary
journey; that route and its client method remain available for existing uses.
Run-entry mutation attempts preserve one pre-POST idempotency key and exact
body, remain single-flight, never retry automatically, and retain uncertain
attempts for explicit exact manual retry. Once Session storage succeeds, safe
View recovery is GET-only and never replays Run entry. Component-generation
guards prevent stale completions from mutating replacement client state, and
public UI/errors/storage continue to exclude the operation key and private
authority or persistence facts. P8-S5 changed no backend, database, migration,
provider, deployment, or Run-lifecycle authority.

The P8-S2 transaction has one owner and one commit. It creates Run revisions
1/2/3 for creation, binding, and first Session participation/activation,
respectively. Existing schema `20260729_0005` already admits those lifecycle,
mutation, binding, receipt, participation, and uniqueness forms; Phase 8
therefore prohibits ORM and migration changes. A proof that the current schema
is insufficient is a plan stop condition, not permission for a convenience
migration.

The selected `scenario_id` remains a scenario identity, never a world or visit.
Current Session initialization uses the scenario's server-selected default
static character definition as a compatibility fixture; that definition is not
the Structured Player Character. Scenario settlement remains the existing
Session `ENDED` plus `RESOLVED`/`FAILED` View. It does not complete or terminate
the continuing Run, which remains active and bound. Full Run Protocol/world
behavior, later Session/scenario progression, Run terminal transitions,
binding historicalization, profile/mechanics/prompt integration, Provider work,
and production activation remain deferred.

The existing Phase 6 and Phase 7 allocations remain unchanged and
unimplemented. Neither is a Phase 8 prerequisite: Phase 8 creates no new
memory/relationship/consequence fact, and its own final slice supplies only the
evidence/status closure for this stage.

## Current composition roots and Provider boundaries

`NarrativeProvider` is the supplier-neutral application-layer interface. It
accepts a validated `NarrativeRequest`, returns an
`UntrustedNarrativeProposal`, and can be closed asynchronously. The interface is
not a network gateway, Provider selector, or source of narrative authority.

The normal composition root is `deviation_protocol.api.main:app`.
`build_default_services()` loads the current scenario/content catalog, creates
the MySQL/SQLAlchemy Unit of Work, and configures
`DeepSeekNarrativeProvider` when valid server-side DeepSeek settings are
available. Without valid settings, normal composition has no narrative
Provider and follows the existing explicit not-configured failure boundary. It
does not fall back to the deterministic Demo Provider. The current configured
adapter supports one server-selected DeepSeek model; players do not select a
Provider/model route.

The Phase 3.2a Demo has an independent composition root,
`deviation_protocol.api.demo:app`, built by `build_demo_runtime()`. It injects:

- `DeterministicDemoNarrativeProvider`;
- `DemoProcessStore`, a process-local transactional implementation of the
  existing Session, Player Character, Run, receipt, participation, and gameplay
  persistence ports, with detached reconstruction, locking reads, CAS,
  uniqueness enforcement, rollback, and one atomic UoW publication;
- independent deterministic Player Character, Run, and continuous-story-line
  identity sequences alongside the existing Session/event/job/lease/worker ID
  sequences, Session seeds, and one shared logical UTC clock;
- the existing `PlayerCharacterService`, `RunService`, `RunEntryService`, and
  single shared `SessionService`, using the fixed Demo principal/controller
  authority and existing service-conditional route registration; and
- `CanonicalDemoNarrativeTurnOrchestrator`, which preserves the normal
  validation, outcome-policy, issuer, StoryDirector, and public API authority
  chain.

The Demo composition does not create a database engine, read Provider
credentials, call DeepSeek, or serve as a normal-composition fallback. Demo
state and receipts last only for that backend process. Within one process,
exact create and Run-entry replay returns committed results without a new
mutation or generator consumption; values already emitted before rollback are
not rewound. Fresh-process evidence executes scenario discovery, Player
Character create/discovery, Run entry, authoritative View, and the canonical
19-action ending in separate OS processes and compares deterministic public and
generator traces without non-loopback network or real Provider access.

Fresh P8-S6 cross-surface evidence preserves that separation. The normal
production ASGI path passed the designated MySQL 8 public entry-to-terminal
playthrough and canonical MySQL/Full gates through the existing
SQLAlchemy/`AsyncSession`/`asyncmy` composition. The independent Demo path passed
its process-local persistence/composition and two-process fresh/replay evidence
through `DeterministicDemoNarrativeProvider` behind
`CanonicalDemoProviderGuard`, with exactly four completed Provider calls for
the canonical journey. The Web evidence passed the create-or-reuse, Run-entry,
stored-Session-before-View, action/request-status/View/recovery, and terminal
rendering lifecycle. No live Provider, production service, unrelated database,
or other external runtime service was contacted. This evidence changes no
composition, transaction, persistence, public-contract, migration, or Provider
authority; it supports only the pending P8-S6 documentation candidate.

## Phase 3.2b local Demo Web boundary

Phase 3.2b adds a local launch and Web presentation layer over the unchanged
Phase 3.2a Demo API composition:

- Vite mode `deterministic-demo` alone resolves `envDir: false`, so it loads no
  dotenv files; ordinary and unknown modes retain Vite's default behavior.
- `VITE_APP_MODE=deterministic-demo` controls only the exact visible
  local/temporary/non-production warning. It is not a Provider selector,
  security boundary, backend composition switch, or public mode choice.
- `scripts/start-demo.ps1` launches
  `deviation_protocol.api.demo:app` as one no-reload worker on
  `127.0.0.1:8000` and Vite on `127.0.0.1:5173`, after fail-fast prerequisite,
  environment, executable, and port checks. It installs nothing and terminates
  only the child process trees it owns.
- `scripts/smoke-demo.ps1` is a separate finite validation entry point. It
  starts its own loopback children, verifies the Vite proxy, executes the
  existing jsdom/React test stack after clearing independent ambient
  `VITE_APP_MODE` inheritance and then conditionally copying the launched Web
  child's effective value to require the exact rendered warning, verifies
  dotenv sentinel absence and a temporary Demo-mode build, and validates the
  public scenario response through a one-test Node Vitest validator that
  directly imports `publicScenarioCatalogSchema`. App source bytes are not
  warning presentation evidence.
- The React/MSW canonical regression creates the public scenario and default
  investigator through rendered controls, submits exactly the frozen 19-action
  path, asserts the exact catalog hook and all five character presentations,
  reads and asserts every rendered scene and decision presentation from a
  complete authoritative View after every action, and reaches the exact
  `death_certificate.ending.protocol_broken` presentation at state version 19.
  Added recovery regressions preserve GET-only same-tab restoration and safe
  404 invalidation with zero action replay.

Demo storage remains process-local and temporary. Normal MySQL/DeepSeek
composition, public API/schema shapes, Provider authority, and Phase 3.1c
recovery semantics are unchanged. Automated verification and the bounded smoke
passed. Controlled manual acceptance passed the canonical 19-action browser
walkthrough to version 19 and `ENDED`, same-tab recovery after backend restart,
Ctrl+C launcher shutdown, and final owned-process and port cleanup. Phase 3.2b
and Phase 3.2 are complete; this deterministic local Demo acceptance does not
establish production readiness or implement later final-product systems.

## Current public action composition

`SessionService` derives `action_affordances` from the current locked/validated
state, `NarrativeFrame`, `InputContractPolicy`,
`available_narrative_actions()`, and `ScenarioContinuePolicy`:

- an active decision produces only bound public `CHOOSE` choices;
- a free-action state produces only currently authorized action types, input
  contracts, and visible runtime-NPC targets; and
- an ended state produces no action controls.

Affordances are a public UI projection, not a second capability. Submission is
still revalidated through the Gateway, decision/continue policies, narrative
outcome policy, and locked authoritative state. The current public contract is
documented in [`public_client_contract.md`](public_client_contract.md).

## Current narrative authority

The model narrates confirmed state and proposes bounded outcomes. The engine
and trusted server policies own objective mechanics, resources, facts, clocks,
betrayal or death outcomes, relationship state, and permanent canon. A
versioned style profile controls prose hints only; it cannot change established
facts or authorize state mutation. Accepted public text with fixed semantic
meaning comes from trusted server templates.

## Future-design boundaries

These designs are accepted or approved for later phases and are not
implemented:

- Phase 3.3 owns the frozen Run Protocol and difficulty/world profiles:
  [`run_protocol.md`](run_protocol.md).
- Phase 3.4 owns NPC relationship progression and temporary residence:
  [`npc_relationship_residence.md`](npc_relationship_residence.md).
- Phase 4.0 owns the future **Production Distribution Gateway** (or **Provider
  Distribution Gateway**) and explicit Provider/model distribution:
  [`ADR 0001`](decisions/0001-production-provider-distribution.md).

Current architecture does not implement player-selectable multi-Provider
routing, commercial quota or billing, a frozen `RUN_PROTOCOL` input,
difficulty/world profiles, NPC residence mode, or unrestricted daily AI chat.
The future selected Provider/model channel remains distinct from both the
application `NarrativeProvider` abstraction and the future Production
Distribution Gateway.

## Phase 3.1c Web same-tab recovery contract

Phase 3.1c implements only same-tab reload recovery for a previously verified
Session and for a request that the server already confirmed as pending with
HTTP 202. Its strict, versioned `sessionStorage` record contains the opaque
`session_id` and, only for such a confirmed pending request, an optional
`client_request_id`. It stores no View, affordance, action payload, player
input, response body, narrative output, or other server-state copy.

There is no client TTL or timestamp. A valid record remains until the tab is
closed, the player explicitly clears it, or the player creates or switches to
another Session. A missing record means there is nothing to recover; it is not
treated as an expired record.

On startup, a record without a pending request restores only by reading the
complete authoritative `/view`. A record with a confirmed pending request
keeps actions locked, renders no cached affordance, and queries request status
with exactly the stored Session and request IDs. `PENDING` /
`POLL_SAME_REQUEST` polls that same request and honors
`retry_after_seconds`; `COMMITTED` / `RESPONSE_AVAILABLE` and `STALE` /
`REFRESH_VIEW` read the complete authoritative `/view`. `FAILED` or
`OUTCOME_UNKNOWN` with `DO_NOT_RETRY` never causes a POST and may use only a
controlled authoritative View read under the existing stale and uncertain
result rules. No recovery path replays an action, substitutes a request ID, or
treats request status as a complete View.

Recovery fails closed. A network error, malformed response, or unsafe result
stops automatic recovery, keeps actions locked, and permits only a
player-triggered retry of a safe GET. A recovery-endpoint 404 invalidates the
record and returns to the initial Session/scenario UI without action controls.
Corrupt, unsupported-version, or identity-mismatched records are cleared
before use. Storage-access or mutation failure remains action-locked. The
foreground-operation lock, operation generation/token, and `AbortController`
prevent obsolete recovery work from committing after invalidation, Session
switch, or unmount.

Transport-uncertain POST recovery, automatic action retry, browser-close or
browser-restart recovery, cross-tab coordination, `localStorage`, URL state,
general reconnection, and long-running background recovery are unsupported.
Authentication, abuse controls, deployment/hosting, production CORS, Provider
changes, and any public API, backend, ORM, database, schema, or migration
change remain outside Phase 3.1c and require future work.

## Phase 3.1a Web public API adapter

`web/` is an independent React/Vite/TypeScript client and depends only on the
sealed Phase 3.0 HTTP contract. Components do not call `fetch` directly. A
single client boundary owns base-URL resolution, path encoding, cancellation,
JSON handling, exact success statuses, public `ErrorResponse` mapping and Zod
runtime validation. Response schemas reject missing or incompatible contract
fields while discarding harmless additive fields; TypeScript DTOs are inferred
from those schemas.

The minimal page discovers public scenarios and roles, creates a session, then
reads the complete `PlayerSessionView` from the formal `/view` endpoint. It can
also perform an explicit in-page View read by session ID. Suggested actions are
display-only. The client never reads `/state` as a recovery substitute and does
not parse opaque IDs or tokens. This batch has no action submission, polling,
automatic retry, local/session storage, URL recovery, cross-tab coordination,
authentication or deployment adapter. MSW provides the only API used by Web
tests; unhandled requests fail the suite.

## Phase 3.0 Public Client Contract

Phase 3.0 adds a read-only, explicitly allowlisted client contract without a
frontend or a new persistence model. `GET /v1/scenarios` lists only scenarios
that declare bounded `public_client` metadata in their versioned content pack.
The response is constructed field by field from scenario ID/content version,
public copy and validated public character references; it never serializes a
`ScenarioDefinition` or exposes future phases, endings, facts, clues, NPC
knowledge, outcome rules or memory rules.

`PlayerSessionView` now combines the validated snapshot projections with the
current scene's public title/summary and deterministic action affordances. An
ending title/summary is selected only after authoritative runtime settlement.
The public `scenario_status` remains the two-value ACTIVE/ENDED lifecycle, while
the always-present nullable `ending_status` projects only the authoritative
runtime RESOLVED/FAILED classification for client settlement handling.
Missing phase/ending presentation bindings fail through the existing
`SNAPSHOT_INVALID` boundary. View construction remains read-only and never
advances state, claims a job, acquires a lease or calls `NarrativeProvider`.

Affordances do not form a second action authority. Free narrative types are
derived by the structural half of the existing `allowed_narrative_outcomes`
rule selection; input kind and limits are read from `InputContractPolicy`; and
`CONTINUE` is exposed only through `ScenarioContinuePolicy.allows`. Labels are
versioned content. Targets are the intersection of the current safe Frame and
player-visible runtime NPC projection. TALK retains its existing optional-target
domain contract. A submitted target is still checked by `EntityReferencePolicy`.

When a decision is active, the public affordance contains only `CHOOSE` entries
copied from the bound Frame. The public Frame replaces internal semantic choice
types with `choice`, removes definition-level targets and custom-action
constraints, while the decision policy re-resolves the choice ID against the
locked versioned definition before the trusted issuer copies any effect. Ended
sessions expose no actions. Details and field-level client behavior are in
[`public_client_contract.md`](public_client_contract.md).

## Phase 2.4b 完整生产可达边界

领域可达不等于玩家/API 可达。Phase 2.4b 以公共 ASGI API 补齐 `death_certificate` 的七阶段生产闭环：服务器模板授权临床复核、三个调查线索组与必要地点；CONTINUE 驱动 disposal escape 和 self-fulfilling truth；绑定当前 Frame 的 choices 驱动 core conflict rapid windows；可信事件产生成功或 deadline 失败 ending。完整成功路径使用内存 adapter 与真实 MySQL，deadline 路径覆盖公开推进、完成记忆和结束后拒绝；测试不使用私有 issuer 或直接状态写入。

现行链路为：

```text
POST ActionType.CONTINUE（无载荷）
  -> ownership
  -> session row lock
  -> turn-request idempotency replay/conflict
  -> reload + validate session/snapshot/catalog/runtime
  -> TrustedResolutionContext
  -> ActionGateway ContinueInputPolicy
  -> DeterministicRuleResolver local protocol marker
  -> re-plan current safe NarrativeFrame
  -> ScenarioContinuePolicy(ACTIVE + CONTINUE + no decision)
  -> StoryDirector.advance_after_verified_result(state, definition, ()) once
  -> server ScenarioAutoBeatAdvanced + generated scenario events
  -> persist/flush events -> memory rules -> snapshot + response + version
  -> one UoW commit
```

客户端不能通过 CONTINUE 提供 fact、clue、NPC、location、clock delta、ending、memory operation 或任何模型字段；已知载荷字段和 extra 字段都由严格 API schema 在 orchestration 前以 422 拒绝，Gateway/ContinueInputPolicy 继续保护非 HTTP 构造。每次合法请求只调用一次 Director 推进一步，不调用 NarrativeProvider。AWAIT_PLAYER、SCENARIO_ENDED 和非活动场景在应用边界稳定拒绝且不改变 beat、clock、memory、snapshot 或 version。同请求的串行重放和并发竞争都返回持久化 winner。

`PlayerSessionView` 是应用服务聚合，不是 snapshot DTO。服务以 ownership 查询 session，重新验证最新已提交 snapshot，重新规划 safe Frame，并组合 metadata、公开 player state、公开 memory、公开 clock、active/ended 状态和有界 COMMITTED 正文。它不读取或改变 narrative lease；pending Narrative 期间看到的仍是最后已提交权威状态。近期正文按 Repository 的 `(updated_at, job_id)` 稳定顺序取最多 6 条，再施加 12,000 字符和 24,000 UTF-8 bytes 总预算；活动场景不序列化 ending。

Narrative request status 同样只读。持久化 TurnResponse 优先由逐字段 allowlist DTO 投影为公共 `COMMITTED` response；PREPARED/IN_PROGRESS/PROPOSAL_VALIDATED 映射为可轮询 PENDING；STALE 要求先刷新 view；OUTCOME_UNKNOWN 明确禁止自动重发；FAILED_TERMINAL 和遗留 FAILED_RETRYABLE 都映射为无供应商细节的 `FAILED/DO_NOT_RETRY`。当前生产代码没有 FAILED_RETRYABLE 转换路径，公共协议不返回 RETRY_WITH_NEW_REQUEST。查询不 claim lease、不执行 Provider，也不公开 job/proposal/lease/outcome token/provider metadata。

公共 ASGI playtest 使用真实 SessionService、ActionGateway、RuleResolver、DurableNarrativeTurnOrchestrator、NarrativeOutcomePolicy、NarrativeEventIssuer 和 StoryDirector，以及无网络 Scripted Provider。最小成功路径和 MySQL 成功路径各调用 Provider 5 次；内存 E2E 额外提交一次直接猜测隐藏真相的对抗输入并验证安全 no-effect，因此调用 6 次；deadline 路径固定为 7 次。CONTINUE、CHOOSE、查询和本地拒绝均不调用 Provider。每个 prompt 都验证 32,000 字符与 64,000 UTF-8 bytes 上限，且 Provider 调用期间活动 UoW 与 session lock 为零。

结束候选存在一个有意受限的两段验证边界。Director 可能先产生 ENDED runtime，而 `ScenarioMemoryRecord` 只有在同一 UoW 的 ending event 已 insert/flush 并匹配声明式 `COMPLETE_SCENARIO` rule 后才能变为 COMPLETED。预检精确匹配 source、内层 event、outcome、rule 与 ending，并只在把唯一 STARTED scenario record 临时投影为该 ending 的 COMPLETED record 后执行完整 snapshot/catalog/memory 验证；事件与真实 memory 应用后再执行最终完整验证。不能匹配规则、错误玩家、无 ending 或任何其他结构/catalog/runtime/memory 非法的候选仍在签发持久化能力前拒绝。最终 event、memory、snapshot、response、job 和 version 只 commit 一次，任何失败全部 rollback。Narrative action 写通常的 COMMITTED Provider job；本地最终 CHOOSE 写 `local-server-template-v1` COMMITTED job，attempt 为 0，不调用 Provider，正文只来自可信 decision template。

## Phase 2.3b production player memory boundary

`GameState` 的当前快照 schema 仍为 v3，`PlayerMemoryState.memory_model_version` 独立升级为 2。它是玩家长期记忆的有界索引，不是第二套运行时剧情状态，也不是事件流副本：同一 `scenario_id`、稳定 NPC subject key 和 experience ID 更新或幂等复用现有记录。旧 snapshot 与 memory payload 都经纯函数迁移，不修改输入，也不根据旧正文、runtime 或 catalog 虚构经历。

唯一事实来源保持分离：当前属性/资源/技能属于 `PlayerState`，货币属于 `WalletState`，物品/装备属于 `InventoryState`，当前 NPC 属于 `GameState.npcs`，当前副本 phase/fact/clue/clock/decision/ending 属于 `ScenarioRuntimeState`，完整已持久化历史属于 `domain_events`，只有长期有界索引属于 `PlayerMemoryState`。记忆仅保存稳定引用、封闭里程碑和最后可信事件顺序；不保存当前数值、runtime NPC ID、完整事实字典、`NarrativeFrame` 或文学正文。

生产写入顺序固定为：锁定并加载原状态；分配稳定 event ID/sequence；Repository 在当前 UoW insert/flush `domain_events`；成功后返回绑定 session/event/sequence/turn/state-version/type/规范 payload 摘要的 opaque `PersistedEventReceipt`；可信 catalog 中的声明式 `MemoryRule` 稳定匹配；`AuthoritativePlayerMemoryPlanFactory` 从权威候选状态派生并密封 plan；最后保存 snapshot、turn response、narrative job 和 session version并单次 commit。Repository 从不 commit。receipt 只表示当前事务内 flush 成功，不是最终提交证明；rollback 时上述写入全部消失。普通 `DomainEvent`、事件类型字符串、JSON/Pydantic、Frame、玩家或模型文本不能构造 receipt、签发 plan 或篡改有效绑定。

`ScenarioDefinition.memory_rules` 仅允许封闭 source event enum、权威 outcome/event/result/completion 条件、封闭 operation 和固定 NPC/fact/ending/milestone/experience 引用。Catalog 严格拒绝重复 ID、未知事件、extra 字段、不兼容 operation、无效或不可达引用；无 eval/exec、脚本、任意字段路径或 setattr。事件按 sequence、规则按 ID 执行，同一事件多规则先在独立候选上完成，任一非容量失败回滚整笔事务。容量失败是唯一降级路径：当前 event 的所有 memory 修改放弃，索引进入 `REBUILD_REQUIRED`，记录有界缺口元数据，游戏的机械/剧情结果、正文、事件和响应仍正常提交；索引不越过缺口，完整历史保留在 `domain_events`。

`ScenarioRuntimeState.narrative_outcome_evidence` 私有保存服务器授权 outcome 的精确 rule/result/event-type/NPC-target 组合，以及服务器模板固定的 NPC definition 与当时匹配的具体 runtime NPC ID；`NarrativeEventIssuer` 将两者绑定进密封事件，`StoryDirector` 在候选 runtime 中稳定去重写入，snapshot reload 再核对 runtime ID 确实指向该 definition。成功 ending 的 `NPC_ALIVE_ACKNOWLEDGED` 条件读取具体 runtime NPC 证据，而不读取模型对话。`decision_outcome_evidence` 同样记录可信 CHOOSE 的 decision/event-type 对，completion memory 不能把任意选择冒充 `core.conflict.resolved`。snapshot 完整性校验不再把 memory rule 或 `applied_event_ids` 当作发生证明：outcome 条件 fact、NPC、ending、milestone 和 experience 必须匹配精确 evidence；没有 runtime/evidence 的动态历史严格拒绝。只有 catalog 无条件标记 `PLAYER_KNOWN` 的初始公开 fact 可不依赖动态发生证据。新增字段只进入 snapshot JSON，ORM/Alembic 不变。

`PlayerMemoryProjector` 输出不可变、深度隔离、稳定排序的玩家已知投影，具有集合数、字符数和规范 JSON byte 上限，并剥离 source event/sequence、deferred 细节、receipt/seal/capability 和 rule ID。投影进入只读玩家状态和 prompt-v2 的规范 JSON 数据区；`complete=false` 只告知索引可能不完整，不授予 Provider 任何权限。Prepare 在锁内创建并用 state version/fingerprint 和 request fingerprint 绑定，Provider 在无 UoW/锁时只读，Finalize 重新锁定、重载、重算并比较后，只有 `NarrativeEventIssuer` 的可信世界事件可以匹配 memory rule。升级前的活动 job 安全转 STALE且不重复调用 Provider；已 COMMITTED 响应先于 job schema 检查按幂等结果读取。

Session 创建也使用相同边界：`ScenarioStarted`、初始规则记忆、version-zero snapshot 和 session 同事务提交；查询、拒绝和 narrative pending 不更新记忆；选择事件只能证明玩家做了选择，不能冒充 NPC 响应或世界成功。当前不支持同一 scenario 重入或跨 scenario NPC identity。只有存在重大隐藏设定、关键 NPC、新路线或明确二周目价值时，未来才值得引入 `scenario_run_id`；普通副本不为回收而回收。`game_snapshots.state_json` 足以承载 memory-v2，ORM 和 Alembic revision 均不变化。详细模型与容量见 [`player_memory.md`](player_memory.md)。

## Phase 2.2c production narrative architecture

The production action boundary now uses `DurableNarrativeTurnOrchestrator`. Phase A locks the session and persists a PREPARED narrative job only after authoritative idempotency, snapshot/content/scenario, Gateway, RuleResolver, frame, and outcome-candidate checks. Phase B atomically claims the job, commits and closes every database context, calls the provider, validates untrusted output, and persists PROPOSAL_VALIDATED in a new short transaction. Phase C locks session then job, performs version/fingerprint/action/scenario/request/lease/proposal CAS, recomputes outcome authorization, and commits once.

`ScenarioDefinition.narrative_outcome_rules` is a closed, versioned vocabulary. Rules reference validated phase/NPC/fact/clue/decision/current-location IDs and existing StoryDirector action costs. Effect payloads are fixed server templates; no model value can become a fact, clue, location, clock delta, event payload, resource, inventory, NPC-existence change, FIXED fact, ending, memory operation, or anomaly effect. Catalog validation rejects unknown references, invisible destinations, unreachable decision bindings, invalid fact effects, and ambiguous mutual-exclusion priorities. The production investigation pack gates clue sources on a public decision, a server-opened authoritative current location, and mechanical `OBSERVE`/`EXPLORE`; player wording is not clue authority. It also includes phase-safe no-effect fallbacks. A narrative rule cannot run while a decision is open unless it binds that exact decision and every effect resolves it.

The provider sees opaque tokens rather than internal rule IDs/templates. `NarrativeOutcomePolicy` recomputes candidates from locked state and verifies the real narrative route, job/action/state/scenario binding, current location, visible entities/NPCs, preconditions, result/prose consistency, and mutex rules. Prose consistency is deliberately conservative, but every production effect publishes fixed server text; Provider prose is validated and stored only as an internal candidate, not selected as the public result. Dialogue and prose therefore never prove or contradict a world fact. Only the policy can create the capability consumed by `NarrativeEventIssuer`; the issuer rechecks job and lease plus all bindings and proposal digest, and derives `VALIDATED_NARRATIVE_OUTCOME` solely from server data. `StoryDirector` applies the sealed event on a deeply isolated candidate, so there is no second state-mutation system.

The validated proposal JSON deliberately contains bounded candidate prose so a PROPOSAL_VALIDATED job can survive a crash. That text is validated-but-unaccepted, internal, non-authoritative, and unavailable to APIs, player projections, recent context, prompts, snapshots, facts, NPC knowledge, or summaries. STALE, FAILED, and OUTCOME_UNKNOWN rows may retain it until job/session deletion; retention does not make it accepted history. The accepted narrative text, snapshot, events, turn response, COMMITTED job, and session version share one UoW commit. Accepted text is invisible before commit, is replayed from the stored response, and is not stored in snapshots. Only bounded COMMITTED accepted text feeds later context; continuity notes do not enter authoritative knowledge.

`20260719_0003` adds `narrative_jobs` with PREPARED, IN_PROGRESS, PROPOSAL_VALIDATED, COMMITTED, FAILED_RETRYABLE, FAILED_TERMINAL, STALE, and OUTCOME_UNKNOWN. FAILED_RETRYABLE is retained solely for legacy-row deserialization; production orchestration does not transition to it. A same-job caller that cannot claim returns 202; other same-session mutations return 409 while read-only queries remain possible. An expired PROPOSAL_VALIDATED job can acquire a new finalize-only fenced lease and continue without Provider. An expired IN_PROGRESS job becomes OUTCOME_UNKNOWN because storage cannot prove whether HTTP was never sent; it is not resent. Job-level provider invocation is one. DeepSeek defaults to one HTTP transport attempt; explicit retry configuration allows at most three attempts total but cannot guarantee exactly-once billing. Expired/old leases cannot save a proposal, finalize, or change terminal state. Future workers may reuse the job ports, but no worker, queue, or distributed task system is included. DeepSeek is built/closed in application lifespan, missing keys do not prevent startup, and default tests never use the network. `DeviationEvaluator`, anomaly effects, combat, and frontend work are still absent.

请求先进入 `ActionGateway`。它按 JSON 配置装配策略链，遇到拒绝或本地动作即停止，且保留截至该点的完整 `policy_trace`。只有通过全部本地规则的输入才得到 `NARRATIVE_NORMAL`。

Phase 1.2 的确定性链路为：

```text
PlayerAction
  -> AuthoritativeStateView
  -> AuthoritativeActionContextFactory
  -> TrustedResolutionContext(ActionContext)
  -> DeterministicRuleResolver
       -> ActionGateway（内部强制执行）
  -> ResolutionResult
  -> 候选 GameState + DomainEventDraft + NarrativeFact + PlayerFeedback
```

Phase 1.3 在该纯结算链路外增加事务编排：

```text
ActionSubmission
  -> UnitOfWork
       -> SELECT game_session ... FOR UPDATE
       -> 按 client_request_id 返回已存响应（命中时立即结束）
       -> 加载 session + 最新 snapshot
  -> 校验 snapshot state/schema/content version
  -> ContentCatalog 完整验证并反序列化 GameState
  -> AuthoritativeActionContextFactory.create_trusted（每次新建、默认空授权）
  -> DeterministicRuleResolver
  -> ResolutionResult
  -> TurnResponse + 可选 snapshot/events/session version
  -> 同一 UnitOfWork 单次 commit
```

`ContentCatalog` 是编排器的构造依赖；application 不读取 JSON 文件。会话和最新快照必须同时存在，且 `game_snapshots.state_version` 必须等于 `game_sessions.state_version`。快照结构版本固定走 `GameState` 支持的 schema，内容版本必须与注入 catalog 一致，玩家身份还必须与会话一致。任何缺失、损坏或版本错误都会停止事务，不允许用默认空状态覆盖。

## Phase 1.4 API、身份与会话生命周期

API 仍遵守 `api/infrastructure -> application -> domain`。FastAPI 类型和 HTTP 状态只存在于 `api`；`RequestPrincipal`、`SessionService`、安全 DTO 和 `PlayerVisibleStateProjection` 位于 application，不依赖 FastAPI。`create_app()` 接受可替换的 `ApiServices`，默认依赖只在 lifespan 中装配，导入模块不连接数据库也不运行 migration。

```text
FastAPI dependency -> RequestPrincipal
  -> SessionService
       -> UnitOfWork
            -> owned session query (session_id + player_id)
            -> versioned snapshot
  -> FirstPhaseTurnOrchestrator (actions only)
```

当前 principal provider 名为 `demo-dev-only`，固定为 `demo-player`，清楚表明它不是生产认证。测试和未来认证适配器通过 dependency override 提供可信 principal。请求模型中没有 `player_id`；行动正文也没有 `session_id`，路径是 session identity 的唯一外部来源。会话 ownership 来自 principal 与已加载 session，API 对不存在和无权访问统一采用 404，避免枚举其他玩家会话。

会话创建事务的输入是创建幂等键和 catalog 角色定义 ID：

```text
(principal.player_id, client_request_id, character_definition_id)
  -> validate character in current ContentCatalog
  -> construct PlayerState + GameState(schema_version=2, content_version=catalog)
  -> stage game_sessions(state_version=0)
  -> stage game_snapshots(state_version=0)
  -> one commit
```

`game_sessions.creation_client_request_id` 与 `character_definition_id` 由独立 revision `20260719_0002` 添加。唯一约束 `(player_id, creation_client_request_id)` 处理跨连接竞争；application 在唯一约束失利并 rollback 后重新读取 winner。相同键与相同角色重放 winner，不同角色是 `IDEMPOTENCY_CONFLICT`。旧数据的两个新字段保持 nullable，不会用 session ID 回填并混淆两种身份；所有 Phase 1.4 API 新建行都写入非空值。

`GET /v1/sessions/{id}` 从关系字段和 catalog 生成安全元数据，不返回 snapshot JSON、random seed 或内部对象。`GET /state` 先重新验证 snapshot schema/content/player/version，再从 `GameState` 构造新的只读 DTO tuple。投影仅包含玩家公开属性、资源、钱包、库存、装备、技能、phase、state version 和任务占位。权威快照中的 NPC 不等同于“玩家可见 NPC”；在持久化的可信场景可见性来源出现前，`visible_npcs` 必须为空。

行动 endpoint 只将严格 HTTP 请求转换为已有 `ActionSubmission`，在 ownership 通过后调用 `FirstPhaseTurnOrchestrator`，不复制 gateway、resolver、context minting 或 UoW 事务。turn 幂等仍由 `(session_id, client_request_id)` 唯一约束与 action signature 共同保证，但公共响应不暴露该持久化完整性字段，也不公开尚未支持的异常评估状态。`REJECTED_LOCAL` 是稳定业务响应，`NARRATIVE_REQUIRED` 只报告 pending/required；Phase 1.4 没有接入 `NarrativeProvider`、LLM、剧情、战斗、`DeviationEvaluator` 或前端。

统一异常映射将请求校验映射到 422，安全 not-found 映射到 404，创建/行动幂等冲突和乐观锁映射到 409，snapshot/content/schema 不兼容映射到 409，领域规则异常映射到稳定 4xx。兜底 500 只返回固定错误码与公共消息，数据库异常文本、URL、路径和堆栈不会进入响应。

`AuthoritativeActionContextFactory` 校验传入视图确实来自同一 `GameState` 与 `ContentCatalog`，然后分别投影 `item_instance_id -> item_definition_id`、`item_instance_id -> equipment_definition_id`、`skill_definition_id -> level` 和 `npc_id -> npc_definition_id`。场景可见性仍由 application 层显式传入，因为当前 `GameState` 不建模场景；缺省可见/可交互集合为空，玩家文本不会自动把 target/tool 加入权威集合。静态 definition ID 不能冒充物品、环境工具或 NPC 的 runtime ID。每次状态改变后必须重新构造视图和上下文。普通 `ActionContext` 是不可变投影但不是结算授权；只有工厂签发且绑定当前 state/catalog 摘要的 `TrustedResolutionContext` 能进入 resolver。

`ActionGateway` 是行动资格和路由边界。它拒绝陈旧回合、重复请求、错误字段组合、不可见目标、非本人持有的实例、未知技能引用、胡言乱语、越权叙述、NPC 控制、系统奖励命令和多主行动。`RuleResolver.resolve` 不接受调用方传入 route 或 `GatewayResult`，而是从密封上下文内部调用真实 gateway 后执行更具体的领域规则；因此手工构造 `RESOLVE_LOCAL` 或异常 route 不能进入结算。网关拒绝不会成为叙事或异常候选。

## Phase 1.2 本地结算与叙事边界

以下操作返回 `RESOLVED_LOCAL`：状态、库存、装备、技能、资源、货币和任务占位查询；装备与卸下；使用内容标签明确允许的消费品；在权威可学习机会中学习技能；升级已学习技能；使用已学习的结构化技能。查询不改变状态，也不调用 `NarrativeProvider`；尚未建模的任务查询明确返回空列表，不伪造任务。

技能结算检查技能是否已学习、等级和前置、资源成本、现有 `cooldown_remaining` 以及当前是否要求尚未建模的目标。成功时成本、所有效果和 `uses` 计数一起提交为候选状态；任何一步失败都不扣资源、不改变次数、不产生成功事件。当前内容没有冷却时长或每级学习成本定义，因此解析器只严格执行已存在的冷却状态，不能自行发明数值。

消费品按真实 `item_instance_id` 读取。普通堆叠物品每次减少一个数量，带 charge 的消费品每次减少一次 charge，并在最后一次使用后移除实例；已装备实例、非消费品、未知实例或不足 charge 都会失败且不改变原状态。装备仍由 `GameState.equip` 检查定义存在、槽位、角色槽位、属性/技能要求、占用和耐久。

`DeterministicEffectExecutor` 只支持内容模型已经判别、且与已验证 `ContentCatalog` 中对象完全一致的 `ATTRIBUTE_MODIFIER` 与 `RESOURCE_MODIFIER`；调用方自建或改写的 effect 会失败。属性倍率使用整数基点和整数除法，结果受非负 64 位整数技术边界约束；资源负 delta 表示消耗，正 delta 表示恢复，并走 `GameState` 校验。执行顺序必须是内容定义中的显式稳定序列。当前 `ATTRIBUTE_MODIFIER` 仅表示由 `SYSTEM_RULE` 或 `REWARD_SETTLEMENT` 产生的永久基础属性变化，事件明确记录 `modifier_scope=PERMANENT`；技能与装备不得借此永久叠加临时加成，装备派生值和战斗临时效果尚未实现。缺失、被改写、语义不支持或类型不支持的 effect 都会明确失败。执行器不使用 `eval`、`exec`、动态导入、脚本或全局随机数。

开放式探索、观察、移动、对话、选择和特殊尝试返回 `NARRATIVE_REQUIRED`。结果只携带标记为 `VALIDATED_INTENT` 的玩家意图和标记为 `AUTHORITATIVE_CONTEXT` 的已验证 instance/runtime ID 映射，不把意图伪装成已发生结果、不写永久状态、不认定行动“独特”，也不触发 NPC 异常或场景崩坏。`ANOMALY_EVALUATION_REQUIRED` 是未来真实 gateway/anomaly evaluator 的预留状态；Phase 1.2 不包含 `DeviationEvaluator`，调用方不能向 resolver 传入该 route，resolver 也从不自行提升行动。

玩家协议没有 grant item/skill、增加货币/资源、改属性、改 NPC、伪造已验证事实/网关 route 或生成实例的字段。自然语言中的此类系统命令由独立 `SystemAuthorityPolicy` 拒绝。合法系统奖励和资源变化只能由授权规则/剧情事件直接调用领域方法或结构化效果执行器。技能学习授权不在 `PlayerAction` 或普通 `ActionContext` 中：应用层必须从 `PERSISTED_FACT`、`REWARD_SETTLEMENT` 或 `SYSTEM_RULE` 签发不可由请求 JSON 重建的 `SkillLearningAuthorization`，其来源和 source ID 会进入成功事件。未来编排器负责保证该 source ID 确实对应已持久化事实或已完成结算。

## 原子性、事件和事务

每次突变先由 `GameState.to_snapshot()` / `from_snapshot()` 创建并验证候选副本。技能成本先写候选，效果执行器再克隆该候选；嵌套字典、集合、物品、装备、技能和资源对象均不与原聚合共享可变引用。只有全部效果和最终 catalog 校验成功，`ResolutionResult.updated_state` 才存在。失败结果没有新状态、成功事件或叙事事实，因此调用方不可能误提交部分变化。

`DomainEventDraft` 表示已经在成功候选状态中发生、但尚未包裹持久化元数据的结构化事件；事务编排器负责注入 `event_id`、`sequence_no`、`occurred_at`、会话和回合后生成现有 `DomainEvent`。`NarrativeFact` 以 kind 区分已验证意图、权威上下文、查询结果和已发生状态，且不是 `StoryFact` 真相突变；`PlayerFeedback` 仅含稳定代码和安全参数。三者的 JSON 值在构造时深度复制、校验并冻结，`ResolutionResult` 还执行成功/拒绝/叙事的跨字段约束。`RuleResolver` 不访问 Repository、不提交 UoW、不生成数据库序号/时间/随机 UUID，也不负责 `client_request_id` 幂等或最终文学文本。

`NARRATIVE_ANOMALY_CANDIDATE` 是应用层稳定路由值，但第一阶段不会自行提升任何输入。后续独立 `AnomalyEvaluator` 只能评估已经通过可行性和权限检查的合法行动，因此胡言乱语、不可实现动作和随机输入不会绕过本地闸门。

会话快照代表频繁变化的聚合状态，使用 MySQL JSON 保存；会话身份、阶段、回合号和 `state_version` 保留为关系列。领域事件提供审计与重建线索。Repository 在同一个 `AsyncSession` 中先执行带版本条件的会话更新，再写快照和事件，最终由 Unit of Work 统一提交。

第一阶段的回合处理在查询幂等记录前以 `SELECT ... FOR UPDATE` 锁定对应会话行，使同一会话的回合串行化；`turn_requests(session_id, client_request_id)` 唯一约束继续作为最终数据库防线。命中记录后必须同时校验已存 `turn_id`、`action_signature` 与响应中的会话/请求/签名绑定：同一动作才重放，不同动作或不同 turn 复用该键会抛出 `IdempotencyConflictError`。正常并发重试会在首个事务提交后读取已保存响应，不会再次进入业务处理；若唯一约束仍捕获到绕过锁检查的竞态，失败事务先完整回滚，再在新锁定事务中读取 winner，且不再次调用 resolver。

Phase 1.3 的版本和持久化规则是：

- `REJECTED_LOCAL` 保存严格响应；不写快照/事件，状态版本不变。
- 无状态变化的 `RESOLVED_LOCAL` 是纯本地查询；只保存响应和查询结果，不调用叙事提供者，状态版本不变。
- 有候选状态的 `RESOLVED_LOCAL` 再次完成 snapshot/catalog 验证后，以当前 `state_version` 做乐观锁更新，恰好增加一次版本；对应版本快照、全部事件与响应在同一事务提交。
- `NARRATIVE_REQUIRED` 保存明确的 required/pending 响应；不预写永久状态或行动成功事件，状态版本不变。
- 默认流程不接受 `ANOMALY_EVALUATION_REQUIRED`；`DeviationEvaluator` 尚未接入。

事件封装属于可信应用层而非 resolver。编排器通过可注入 Clock/ID generator 增加 `event_id` 和 UTC `occurred_at`，在会话行锁内从当前最大值分配连续 `sequence_no`，保留 `DomainEventDraft` 的原顺序，并把冻结负载深复制成普通 MySQL JSON 值。现有事件表以 `(session_id, turn_id)` 关联 `turn_requests`；同一 turn response 的 `resulting_state_version` 提供等价的状态版本关联，因此 Phase 1.3 不需要迁移。失败、拒绝和查询不产生成功事件。

`TurnResponse` 是唯一可持久化返回模型。它不暴露完整 `GameState`、`TrustedResolutionContext`、技能学习 capability、数据库异常或不可序列化对象。重复请求在锁内读取 `response_json` 后必须重新通过该模型验证，并与 turn request 的会话、请求和签名元数据交叉校验，返回值与首次结果等价。`action_signature` 不参与幂等键查找，但参与命中后的冲突判断；语义相同但 `client_request_id` 不同的请求仍是两个顺序处理的 turn request。

会话乐观更新、带预期版本条件的 snapshot update/insert、event insert 和 turn response insert 共用同一个 `AsyncSession`。快照行已存在但版本与会话预期不符时明确抛出 `OptimisticLockError`，不能用较旧候选覆盖。Repository 不得 commit；编排器只调用一次 UoW commit。任一写入或 commit 失败由 UoW 完整 rollback，除已确认由相同幂等键 winner 产生的唯一约束竞态外，数据库异常不会被转换成成功响应。

剧情事实的责任边界由 `StoryMutationValidator` 固化。FIXED 不可写，DEFERRED 首次绑定后不可写，MUTABLE 和 `dynamic.*` 都需要真实 `causal_event_id`。

## Phase 1.1 角色与能力边界

`domain.content` 保存版本化静态定义与 `ContentCatalogLoader` 端口；静态定义只使用稳定 `definition_id` 互相引用。目录在成为可用对象前统一检查重复 ID、缺失引用、技能前置循环、不可达等级以及装备与物品定义的一致性。效果仅有受判别字段约束的结构化类型，倍率统一使用整数基点，不支持任意表达式或脚本。

`domain.state.GameState` 是写入 `game_snapshots.state_json` 的运行时聚合，显式携带快照 `schema_version` 和内容版本。`schema_version` 描述 JSON 结构兼容性，`content_version` 标识状态所引用的具体内容包，两者不能互换。玩家、NPC、物品实例、装备状态、技能状态、钱包与资源只保存会变化的数据；名称、上限、前置条件、装备需求与效果仍由 `ContentCatalog` 掌管。所有领域操作先验证完整前置条件，再改变聚合，失败使用稳定领域错误码且不留下部分修改。快照输出还会重新验证嵌套结构，阻止绕过聚合方法产生的非法状态进入持久化边界。

原有 `domain.models.Player`、`NPC` 和 `Inventory` 保留原构造语义，仅作为 Phase 1 兼容 DTO，不参与 `GameState` 或 Phase 1.1 规则。权威运行时模型是 `PlayerState`、`NpcState` 和 `InventoryState`；原有 `GameSession` 持久化聚合与 `Scene` 保持不变。

`AuthoritativeStateView` 为 `RuleResolver` 和行动上下文适配器提供脱离可变聚合的不可变投影。物品输入按 `item_instance_id` 检查，技能按 `skill_definition_id` 检查，NPC 按当前会话中的运行时 `npc_id` 检查；玩家叙述文本不是状态来源。状态改变后需要重新创建投影。Phase 1.2 已由 `AuthoritativeActionContextFactory` 自动完成投影和一致性校验；resolver 使用 `create_trusted` 的结果，普通 gateway-only 场景可使用 `create`。Phase 1.3 的 `FirstPhaseTurnOrchestrator` 已负责数据库快照加载、catalog 验证、可信上下文签发、draft event 封装、幂等响应与原子提交。当前没有可信的持久化场景/奖励/事实来源，因此它传入空可见 NPC 集合、空环境工具集合和空技能学习授权；未来扩展必须来自应用端口，不能来自玩家请求。

装备槽位同时受装备定义和玩家角色定义约束。同一实例只保存一个 `equipped_slot`，槽位占用不另建第二份记录。零耐久装备不能新装备；已装备物品在耐久降到零时不会被隐式卸下，必须显式卸下后才能移除。

JSON 内容包文件由 `infrastructure.content_loader` 以 UTF-8 读取并交给领域目录验证。领域层不知道文件路径，基础设施加载器也不改变运行时状态。Phase 1.1 继续复用现有 MySQL JSON 快照、Repository、UoW 和领域事件模型，不增加业务表。

## Phase 2.1 通用剧情框架

### 定义、目录、运行时与加载器

`domain.scenario.ScenarioDefinition` 是不可变、数据驱动的副本规则集合；`ScenarioCatalog` 将它与现有 `ContentCatalog` 组合，以同一套 `CharacterDefinition`、`NpcDefinition` 和 `ItemDefinition` 完成职业标签、NPC 与剧情物品交叉引用。`infrastructure.scenario_loader.JsonScenarioCatalogLoader` 是唯一文件系统入口，领域层不读取 JSON。顶层目录版本、副本 schema 版本、内容版本与快照 schema 版本分别验证，未知规则判别值和额外字段明确失败。

通用条件词汇是封闭的判别联合，包括 beat、事实值、线索组、整数时钟、已开放地点、决策数、已验证事件与访问次数。多个 Transition 表达替代路线；引擎按 `(priority, transition_id)` 稳定选择，Ending 同样按 `(priority, ending_id)` 选择，不依赖对象字典顺序。必要阶段必须结构可达，非终止阶段必须有出口；自动转场环只有声明 `max_uses` 或 `max_visits` 时才允许。没有表达式求值、代码执行或动态导入。内容包还受文件大小、节点数、集合大小、字符串长度、嵌套深度和整数上界限制，重复 JSON key 与非标准数值会明确失败。

`domain.scenario_runtime.ScenarioRuntimeState` 是 `GameState.scenario_runtime` 的可选子状态，只保存 scenario/content ID、阶段与 beat、当前位置、线索与组、Deferred 绑定、Mutable 当前值、`dynamic.*` 事实、整数时钟、开放地点、当前/已完成决策、rapid 状态、结局、阶段访问数、转场使用数和有界已应用事件去重标记。NPC 关系与存在性仍只在 `NpcState`，物品仍只在 `InventoryState`，技能仍只在 `PlayerState.skills`，钱包与资源仍使用原聚合。

快照 v2 增加可选 `scenario_runtime`。`migrate_snapshot_payload` 以深拷贝把 v1 纯迁移为 v2/`scenario_runtime=null`，不会改变输入；新快照写 v2。含剧情状态的 v2 快照必须同时用匹配的 `ContentCatalog` 与 `ScenarioCatalog` 校验。数据库模型和 JSON 列没有变化，因此 Phase 2.1 不需要 Alembic migration。

### 事实、线索、知识与时钟

现有 `facts.py` 扩展为四种稳定性：FIXED 只能发现不能改写；DEFERRED 只能从预先声明候选首次绑定；MUTABLE 只能按当前值、目标值和可信事件类型组成的显式转换改变；DYNAMIC 只能使用 `dynamic.*` 命名空间，并受数量、键长、JSON 值长度及因果事件约束。运行时保存当前值，不追加历史副本。

事实可见性区分 HIDDEN、DISCOVERABLE、PLAYER_KNOWN 与 NPC_KNOWN 等价边界。线索引用其支持事实，只能由 `VerifiedScenarioEvent` 的允许来源事件发现；重复发现由集合去重。线索组使用 N 中满足 M 的阈值并产生稳定完成事件。职业标签只能开放替代线索或建议动作；加载器还要求所有通关线索组存在不依赖职业标签的满足集合。

威胁时钟由 phase 的自动 beat 成本或 action time cost 以整数推进，达到上界时钳制且不会倒退。阈值只触发一次确定性事件。玩家可见性由时钟定义决定；渲染文本没有任何修改时钟的能力。所有变更先发生在候选聚合，失败不会留下部分时钟、线索或事实变化。

### 决策节奏、StoryDirector 与 NarrativeFrame

`DecisionCadencePolicy` 独立选择声明式 DecisionWindow。普通阶段用 `min_auto_beats` 与稀疏的 earliest/latest beat 保持连续叙事，避免门、单句对话等琐事停顿；核心阶段可声明 rapid 模式和紧邻窗口。每个窗口只有一个受限 reason，`NarrativeFrame` 只有一个可选决策槽。达到 `max_auto_beats` 仍无合法决策或转场会明确失败，阻止无限自动推进；当前决策未获得已验证玩家响应时也不能继续自动推进。

`application.story_director.DeterministicStoryDirector` 的输入是 `GameState`、`ScenarioDefinition`、职业标签和零个或多个服务器密封的 `VerifiedScenarioEvent`。同形 JSON、普通模型实例和密封后改写的副本都不能进入推进路径；未来 RuleResolver/NarrativeResult 验证器可以在不改变事件公共数据形状的前提下接入内部密封步骤。相同输入产生相同候选状态、稳定派生 frame ID、阈值事件和 `NarrativeFrame`。Director 不访问时间、全局随机数、数据库、`NarrativeProvider` 或异常评估器，也不修改输入聚合。纯本地查询走只读路径，不增加 beat、时钟、决策次数或事件去重记录；重复已应用事件明确拒绝且不推进状态。

`NarrativeFrame` 是不可变结构化渲染合同，包含必须/可选呈现事实、运行时真实存在的可见实体、已发现线索、明确允许披露且已经发生的最近事件、按 NPC 分区的玩家安全知识交集、语气与长度、代码生成的建议动作、自定义动作约束、停止条件和公开时钟。它不含隐藏事实、NPC 秘密、隐藏时钟事件、未来结局、可变 `GameState` 引用、`TrustedResolutionContext`、系统授权或可执行表达式。frame ID 只由公开投影派生，隐藏状态变化不会形成 ID 侧信道。未来 `NarrativeProvider` 可以替换，但只能把框架渲染成文本，不能增加系统动作或改写权威状态。

Phase 2.1 提供的领域能力现已由 Phase 2.2a 接入生产 `FirstPhaseTurnOrchestrator` 与 API；真实 Provider 接线仍留给后续阶段。首个内容包及文档只包含原创结构化设计，参考文本没有进入仓库内容、测试或提示词。

## Phase 2.2a 事务接线与可信剧情边界

### 依赖装配与会话创建

默认应用只在 FastAPI lifespan 中加载只读 `ContentCatalog` 和 `ScenarioCatalog`、创建 engine/UoW 工厂，并在退出时释放数据库资源。模块导入不读文件、不建 engine、不连接数据库；测试可向 `create_app()` 注入微型目录。`ScenarioCatalog`、`StoryDirector` 是应用服务的构造依赖，不是全局可变单例；domain/application 仍不依赖 infrastructure、FastAPI 或 SQLAlchemy。

玩家创建请求必须显式提供 `character_definition_id` 和服务器允许的 `scenario_id`，但不能提供 scenario 内容版本、初始 phase、事实、线索、时钟、运行时、Frame 或可信事件。角色由 `ContentCatalog` 验证，scenario 与其内容版本由 `ScenarioCatalog` 决定。创建事务为：

```text
RequestPrincipal + creation_client_request_id
  -> validate character_definition_id in ContentCatalog
  -> validate scenario_id in ScenarioCatalog
  -> construct base GameState and declared runtime NPC instances
  -> DeterministicStoryDirector.start_scenario
  -> ScenarioRuntimeState + player-safe initial NarrativeFrame
  -> stage game_sessions(state_version=0)
  -> stage game_snapshots(schema_version=2, state_version=0)
  -> one UoW commit
```

创建幂等身份是同一玩家范围内的创建键，并同时绑定角色与 scenario；完全一致时从已提交 v2 快照重建同一个确定性初始 Frame，任一绑定不同则返回 409。数据库现有唯一约束仍允许不同玩家复用相同创建键。旧的无 `scenario_runtime` 快照继续按兼容路径读取，不会补造运行时状态。

### 回合事务

回合入口保留原有 session 行锁、幂等命中检查、action signature 冲突检查、CAS 与单 UoW 边界。加载器先验证 session、最新 v2 快照及其匹配的两个目录，再从当前位置和实际运行时 NPC 计算可信可见/可交互集合。`ActionGateway` 和 `DeterministicRuleResolver` 总是先于剧情协调执行，玩家文本不能成为剧情事实来源。

```text
ActionSubmission
  -> SELECT game_session ... FOR UPDATE
  -> idempotency replay/conflict check
  -> load and validate v2 GameState + both catalogs
  -> mint TrustedResolutionContext
  -> ActionGateway + DeterministicRuleResolver
  -> scenario coordination on one detached candidate
       -> read-only StoryDirector plan, or
       -> trusted decision event + StoryDirector advance
  -> candidate validation
  -> CAS session version + snapshot + ordered events + response
  -> one UoW commit
```

各路由的状态语义固定如下：

- `REJECTED_LOCAL`：仅持久化稳定幂等响应及当前安全 Frame；不推进 phase、beat、clock、decision，不写新快照或成功事件，版本不变。
- 本地查询：返回 resolver 的权威查询结果和只读 Frame；不调用 Director 的推进方法、不写快照，版本不变。
- 本地机械突变：仅提交 resolver 已确认的机械候选。Phase 2.2a 尚无机械结果到剧情事实的明确映射，所以 runtime 保持不变，只从候选重新规划 Frame。
- `NARRATIVE_REQUIRED`：无 Provider 时返回 required/pending 和当前 Frame；意图不是已发生结果，不写永久事实、线索、时钟或 NPC 响应，版本不变。
- 声明式决策：`CHOOSE` 只接受当前 Frame 公布的 session/state-version/scenario 绑定 `decision_id` token 及其中一个 choice ID，不能混入文本、target、tool 或其他结构化结算字段。合法选择经应用策略验证和密封后，Director 可记录玩家确实选择了该项，并应用 scenario action 中固定声明且经目录验证的 event/fact effect；请求不能自行提供或改写这些效果，也不能额外声称 NPC、环境或其他行动结果已经发生。
- 已终局 runtime：拒绝后续普通剧情推进，仍可返回安全结算 Frame。

机械状态与剧情状态需要同时改变时，先用 `GameState.detached_copy()` 建立不共享嵌套可变引用的单一候选；Director 同样返回独立候选。只有所有规则、目录验证、事件写入和 CAS 都成功才提交。session 版本一次成功回合只加一；resolver draft 在前、可信决策审计 draft 及 Director draft 在后，原顺序封装为连续 `sequence_no`。任一阶段或 commit 失败均由 UoW 回滚机械状态、剧情状态、事件、快照、版本和幂等记录。

### 可信剧情事件桥梁

`ScenarioDecisionResponsePolicy` 只能为“当前活动决策中公开允许的选择”构造不可由请求 JSON 重建的内部验证 capability。capability 绑定 session、turn、request、action signature、state version、完整状态指纹、scenario 内容版本及内部/公开决策 ID；`TrustedScenarioEventIssuer` 再用锁内权威状态检查这些绑定和来源，默认密封 `player.decision.selected`。若目录 action 声明固定 server event/fact effect，该事件必须属于某个 mutable fact 的已声明 transition，fact/value 也必须匹配同一 transition；issuer 只从当前权威 action 复制它，不读取玩家字段。事件 ID 由 session/turn/request/decision/choice 稳定派生。密封摘要绑定完整负载、source 和内部 decision ID，修改后真实性失效；Director 只允许事件解析其所绑定的当前决策，runtime 的 applied-event 集合使同一事件重放不能再次推进。

来源白名单预留了 resolver 已确认机械结果和未来已验证 NarrativeResult，但 Phase 2.2a 对两者的事件类型集合均为空，因此没有通用签发入口。普通 `VerifiedScenarioEvent`、Pydantic 对象、`PlayerAction`、API JSON 和未来原始模型输出都拿不到 capability。比如“护士承认我活着”仍只是需要 Provider 处理的玩家意图，不会因为文本或建议选择而变成 NPC 已确认事实。

### 安全 Frame 与后续 Provider

`NarrativeFrame` 是唯一进入创建/行动响应的剧情投影，并增加当前公开 `decision_id` 以绑定决策窗口。Frame 只含已知事实、已发现线索、真实可见实体、公开时钟、公开建议动作及呈现约束；响应模型继续 `extra="forbid"`，不包含 action signature、完整 `GameState`/snapshot、Scenario 定义、隐藏事实、未来结局、密封信息、策略 trace、数据库异常或 `ANOMALY_EVALUATION_REQUIRED`。

Phase 2.2b 的 `NarrativeProvider` 只能根据 Frame 提出候选叙事结果。独立服务器验证器必须核对结果与权威公开上下文；Phase 2.2b-1 即使验证通过也不会取得密封 capability。Provider 本身不能写 Repository、调用 UoW 或直接修改事实、线索、时钟、NPC 和决策。Phase 2.2a 生产路径没有模型 SDK/API 调用、异常评估、文学正文生成、战斗或场景崩坏。

### 持久化选择

所有 scenario 标识、内容版本、phase、facts、clues、clocks 和 decisions 已包含在 v2 `game_snapshots.state_json.scenario_runtime`。ORM 及关系表没有变化，现有 `20260719_0001`、`20260719_0002` revision 足以支持本阶段，因此 Phase 2.2a 不新增或修改 Alembic migration。

## Phase 2.2b-1 供应商无关叙事边界

本阶段新增的链路是独立模型适配与验证能力，不接入生产事务编排：

```text
safe NarrativeFrame copy
  + normalized validated player intent
  + bounded public context
  + versioned style profile
  -> NarrativeRequest
  -> PromptBuilder
  -> NarrativeProvider Protocol
  -> DeepSeekNarrativeProvider
  -> UntrustedNarrativeProposal
  -> NarrativeProposalValidator + authoritative public allowlists
  -> ValidatedNarrativeProposal (still non-authoritative)
```

application/domain 不导入 `httpx`、DeepSeek SDK、环境设置或供应商配置。`NarrativeRequest` 重新验证并深拷贝 `NarrativeFrame`，且把 `ActionSubmission` 投影为不含 session、turn、client request、signature、gateway route、trace 或 capability 的 `NarrativePlayerIntent`。PromptBuilder 使用可替换的版本化 style profile，玩家输入只序列化进明确的不可信数据段；通用提示词不含任何首副本 ID、医院专属文本或参考作品原文。

`NarrativeProposalPayload` 是 `extra="forbid"` 的判别式严格 JSON。封闭 outcome 类型只表达非权威候选；模型没有事件、事实/线索写入、clock/phase/beat delta、grant、资源、属性、技能、state version、decision、capability、seal 或 anomaly 字段。Provider metadata 与官方实际返回的 token/cache usage 由适配器补充，模型无权声明。

验证器只读取当前请求 Frame 与应用调用方提供的权威公开 allowlist。它校验实体存在且已向模型公开、NPC speaker 是当前可见运行时 NPC、物品是玩家拥有并在当前意图中公开的实例、正文长度匹配 Frame，并拒绝隐藏标识、内部 ID、seal/capability 形态、float、NaN、Infinity 和非 JSON 对象。验证失败只抛稳定错误，不保存或返回原始模型输出。验证器不导入、持有或调用 `TrustedScenarioEventIssuer`，`ValidatedNarrativeProposal` 也没有真实性 capability，因此不能进入 `StoryDirector` 或创建 `VerifiedScenarioEvent`。

DeepSeek adapter 只在 infrastructure，配置限制为官方 HTTPS host、`deepseek-v4-flash`/`deepseek-v4-pro`、显式 timeout、有界 max tokens 和最多 2 次 retry（最多 3 次 HTTP attempt）。生产默认 retry 为 0，因为 read timeout、连接中断等错误不能证明供应商没有收到请求；显式开启 retry 可能重复供应商工作或计费，本系统不保证 exactly-once billing。请求固定 non-stream、JSON object、thinking disabled，并禁用所有工具/Beta/Web 能力。400/401/402/422 不重试；429、500、503、连接与 timeout 仅在配置允许时使用可注入的有界退避；空 content 或 JSON 解析失败最多额外尝试一次且受总上限约束；`finish_reason=length` 直接作为截断失败。client 延迟创建并支持异步关闭，日志和 DTO 不包含 key、Authorization、完整 prompt 或原始响应。

本段记录 Phase 2.2b-1 当时尚未接线的边界；现行 Phase 2.2c 生产行为以文首的三阶段架构为准。详细配置、数据合同与 smoke 规则见 [`docs/narrative_provider.md`](narrative_provider.md)。

## Experimental Dynamic Narrative Vertical Spike candidate

The DNVS candidate is a separate local Demo composition, not a production
composition or a new formal phase. It enters the existing authoritative Run,
Session, participation, Player Character, snapshot, event, turn-response, and
narrative-job boundaries through a director-free dynamic Session service. The
server constructs every View and exact suggestion submission; the Web client
only renders and returns those contracts. Provider output remains an untrusted
candidate until current authority, finite public/hidden provenance, state
version, job lease, request binding, and storage-slot validation all succeed.

Each accepted dynamic turn uses prepare/call/finalize transactions. The single
Provider await occurs outside every UoW and lock. Finalize atomically publishes
the successor snapshot, event, response, committed job, accepted prose, and
Session version. Cancellation and uncertain publication are reconciled from a
fresh UoW and never cause automatic Provider replay. A permanent process-local
ledger admits exactly 512 distinct attempts per Session; attempt 512 may create
a job, while the next distinct attempt is rejected before job creation or
Provider invocation. Exact replays and concurrent followers join existing
authority and consume no new reservation.

No schema or migration changes are needed: existing narrative-job JSON,
snapshots, turn responses, and the literal 20-slot dynamic-facts allowlist carry
the bounded experimental state. The candidate remains unstaged and awaits
independent implementation review. It does not establish production or evidence
completion and does not change Phase 6, Phase 7, completed Phase 8, or P8-S6.
