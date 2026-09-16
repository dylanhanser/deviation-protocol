# P3.3-S4 Native Run Admission and Entry-World Freezing Plan

Status: **Corrected documentation candidate; unapproved pending focused
independent re-review after one CHANGES_REQUIRED finding. S4 implementation
has not started.** Authored on 2026-09-16 against
`main` at `a53f8e65ad74c62bc6c40b9de26222eb889084f0`. Local HEAD, main and
origin/main were verified equal without fetch/pull, ahead/behind `0/0`, with
clean worktree/index and no conflicts or active Git operations before editing.

S3 implementation is published at that baseline, independently approved with
DF-001 deferred. Earlier changes-required reviews and frozen candidate wording
remain history. Phase 3.3 remains incomplete. This task changes documentation
only; every implementation, runtime verification and Git write needs its own
authorization under the [workflow](engineering/codex_workflow.md).

## 1. Deliverable and evidence basis

Deliver one production-composed internal `NativeRunAdmissionService.enter`
boundary accepting authorized intent, freezing an S2-resolved protocol and an
authored entry world, and atomically creating a character-bound Run and its
first initialized Session. Include strict detached reconstruction, owned replay,
failure recovery by explicit retry, and the migration/writer exclusion proof.
This is component implementation, not player-facing native reachability.

The [parent plan](phase_3_3_run_protocol_implementation_plan.md) assigns public
API/OpenAPI, Demo/Web activation, discovery and public recovery to S6; mechanics
and prompt-context compilation to S5; later worlds, visits, regions, progression
and continuity to S7. S4 adds none of them. The legacy entry service, public
routes, existing V1 evidence, fingerprints, and revision meanings are preserved.
No Provider dependency belongs in the new admission object graph.

The design follows these inspected dependencies, rather than a preset path count:

| Existing boundary | Consequence for S4 |
| --- | --- |
| `domain/run_protocol.py`, `domain/run_protocol_resolution.py`, `infrastructure/run_protocol_persistence.py` | Reuse exact S1 bytes/dispatch and public S2 lookup, override validation and resolution; no changes to S1/S2 algorithms or catalogue. |
| `application/run_entry_service.py`, `run_operations.py`, `run_service.py` | Reuse pure CREATE, bind, activation constructors and staging semantics. Existing entry is controller-scoped and commits revisions 1/2/3 once; do not call its committing `enter` from native entry. |
| `application/session_service.py` | Reuse detached preparation and caller-UoW staging. Existing replay accepts only P8 evidence; native replay needs an explicit sibling validator, not fabricated P8 evidence. |
| `infrastructure/run_persistence.py`, `repositories.py` | Creation receipt decoder dispatches by first byte; fingerprint/source validation and evidence insertion need an explicit native branch. Full Run validation needs the immutable character revision loaded first. |
| S3 classifier and [published S3 plan](phase_3_3_s3_persistence_legacy_native_compatibility_plan.md) | Existing native binding proves a persistence component, not admission. Preserve N01-N15 and legacy proof; add a distinct complete admitted result. |
| `infrastructure/unit_of_work.py` | Ordinary engine-bound Session may return its connection at commit. Native entry needs an explicitly checked-out connection surviving commit until named-lock cleanup. |
| `api/main.py`, `api/dependencies.py` | Normal `build_default_services` must supply the usable internal service. A private helper tested in isolation is insufficient. |
| Migration `20260828_0006`, S3 MySQL fixtures and migration assertions | Share its exact lock; add one successor migration. S3 fixtures intentionally exercise revision 006 and must restore the new head around that historical interval. |

## 2. Authored world authority

Proposed technical/content-reuse decision for this candidate: the internal
eligible catalogue is a single immutable tuple in `domain/entry_world.py`:

| `entry_world_id` | `entry_world_version` | Scenario association | Default scenario character |
| --- | ---: | --- | --- |
| `world.death_certificate` | 1 | `death_certificate` / `death-certificate-1.1.0` | `character.death_certificate.investigator` |

This assigns an opaque world reference to existing approved authored content in
`config/scenarios/death_certificate_v1.json`; it adds no prose, geography, NPC,
fixed fact, cross-scenario identity or story canon. Eligibility here means usable
by the S4 internal service only. There is no default selection and no permanent
designation of the Demo scenario as the production entry world. Public eligible
choices/rollout remain an S6 decision; catalogue expansion requires authored
review and versioned entries. That later product choice does not block this
bounded internal path. If reviewers reject this explicit content reuse, the
specific missing decision is which already-approved scenario/version may back
the first internally eligible world; do not substitute an empty production
catalogue or a test-only service and claim S4 complete.

`EntryWorldId` is exact ASCII `[A-Za-z0-9][A-Za-z0-9_.:-]*`, length 1..128;
`EntryWorldVersion` is exact int 1..9223372036854775807 (never bool).
`EntryWorldRefV1` contains exactly these two wrappers. The strict frozen
`AuthoredEntryWorldV1` additionally contains exactly `scenario_id`,
`scenario_content_version`, `default_character_definition_id`, with existing
scenario bounds 128/32/128. All carriers forbid extras and inspect original
nested state before serialization, including constructed/mutated instances.

Trusted lookup accepts only the reference, validates the authoritative tuple
and its entries, and returns the catalogue-owned definition; never accept a
caller-supplied definition. Unknown pair raises `EntryWorldLookupError`;
malformed values raise `EntryWorldValidationError`; corrupted server catalogue
raises `EntryWorldCatalogueIntegrityError` (all ValueError subclasses).
No filesystem path, arbitrary scenario ID, model content, null or missing world
can authorize admission. The application resolves the mapped scenario through
`SessionService.resolve_run_entry_definition` and checks all three associated
values against its loaded approved catalogue. Production construction performs
this compatibility check without opening a database. No generic engine branch
on this world or scenario ID is introduced.

All profiles admitted by S2 are eligible for this bounded world; S2's existing
presentation/override compatibility rules still apply. S4 stores resolved
objectives but does not apply S5 mechanics. An admitted reference is immutable:
retain version-1 catalogue records for reconstruction; future eligibility
removal must not reinterpret stored content. Mutable discovery/default choices
are never consulted to replay admission.

## 3. Application command, evidence and ordered admission

`NativeRunAdmissionService.enter(principal: RequestPrincipal, *, command:
NativeRunAdmissionCommand) -> NativeRunAdmissionResult | NativeRunAdmissionDecision`
is the only composed native write boundary. Command fields are exactly:
`public_operation_key: RunEntryPublicOperationKey`, `player_character_id`,
`expected_record_revision`, `protocol: RunProtocolEnvelopeV1`,
`overrides: RunProtocolOverrideProposalV1`, `entry_world: EntryWorldRefV1`.
The caller proposes S1 presentation/profile and permitted S2 overrides; it
cannot submit resolved values, source, selectors, Run/line/Session identities,
scenario, fingerprints or a native/legacy switch. Source remains the configured
`source.production-run`; server issuers and clock own IDs and UTC time.

The result is a strict detached internal value with exactly schema
`run-entry.native-result/v1`, Run ID, line ID, Session ID, scenario ID/content
version, applicable character reference, resolved protocol, entry-world ref,
and admitted Run revision 3. It is not an API DTO or current gameplay view.
First success and replay return equal results; no replay-dependent field or
current character revision replaces the admitted reference.

Authorization belongs to the existing `ControllerBindingResolver` and
`PlayerCharacterBindingEvidenceReader.lock_owned_for_binding`, reused by the
new service, followed by Session ownership validation against
`principal.player_id`. Classification alone authorizes neither a caller nor
disclosure. Native decisions are exactly `AUTHORIZATION_FAILED`,
`IDEMPOTENCY_CONFLICT`, `PLAYER_CHARACTER_STALE`,
`PLAYER_CHARACTER_NOT_ELIGIBLE`, `INVALID_PROTOCOL`, `INVALID_ENTRY_WORLD`,
`INVALID_SCENARIO_DEFINITION`, `RUN_ENTRY_CONFLICT`.

Validation order is normative:

1. Validate exact principal and original command/carrier shape without SQL;
   malformed construction/state keeps its owning TypeError/ValueError/Pydantic
   ValidationError. Resolve controller before any UoW; absent/invalid controller
   returns `AUTHORIZATION_FAILED`. No issuer, clock or write runs yet.
2. Enter the dedicated native UoW and acquire the shared lock as section 6
   specifies. Lock and validate the owned current character. Missing/cross-owned
   target returns `AUTHORIZATION_FAILED`; impossible trusted evidence raises
   `NativeRunAdmissionIntegrityError`. Read the derived creation receipt next.
3. If the receipt exists, take only section 4's replay branch, before new-entry
   revision/lifecycle/occupancy checks, catalogue eligibility or Session creation.
4. For a new request require expected character revision, active lifecycle and
   successor capacity, in that order; require no active Run for that character
   using the existing locking occupancy read. Return the corresponding stale or
   ineligible decision. Do not mutate the character record.
5. Invoke the S1 validator and public S2 resolver (server-selected epoch/version
   1), preserving S2's lookup/override/compatibility order.
   `RunProtocolProfileLookupError` and `RunProtocolOverrideValidationError`
   return `INVALID_PROTOCOL`;
   corrupted authoritative S2 state (`RunProtocolResolutionIntegrityError`)
   propagates, never masquerades as caller rejection. Lookup the authored world;
   unknown pair returns `INVALID_ENTRY_WORLD`, server catalogue corruption
   propagates. Resolve/check the exact scenario association; unavailable or
   incompatible definition returns `INVALID_SCENARIO_DEFINITION`.
6. Check the derived Session creation request is absent; otherwise return
   `RUN_ENTRY_CONFLICT`. Issue Run/line and Session/event IDs, seed and one UTC
   transaction timestamp; prepare the detached Session. Construct and validate
   the complete native evidence, revisions, receipts and bindings before writes.
7. Stage the section-5 write set, flush and strictly reconstruct the whole
   admitted family in that same transaction; compare with the intended result.
   Commit once at the application boundary. Deliver success only after UoW exit
   has completed checked named-lock release and connection cleanup.

Evidence is `NativeRunEntryCreationEvidenceV1`, with exact payload fields:

| Field | Value |
| --- | --- |
| `evidence_schema` | `run-entry.native-creation-evidence/v1` |
| `controller_operation` | controller wrapper and operation-key string, same scalar bounds as P8 |
| `player_id` | authenticated Session player ID, existing 1..64 ASCII bound |
| `player_character` | character wrapper and pre-entry revision wrapper, same structure as P8 |
| `scenario` | scenario ID, content version, default character definition ID |
| `trusted_run_source` | configured source wrapper, same structure as P8 |
| `entry_world` | exact world reference |
| `resolution_input_hex` | lowercase hex of S2 canonical resolution input (contains exact S1 envelope hex, authorized profile and explicit override presence) |
| `resolution_fingerprint` | S2 lowercase 64-character SHA-256 |

Encode strict compact sorted-key UTF-8 JSON through the existing canonical Run
encoding rules. Prefix with `b"\x8aDP33S4E\r\n\x1a\n"` (12 bytes) then byte
`1`; enforce total length 14..4096. Reject duplicate/extra/missing keys,
noncanonical JSON/hex, BOM, non-integer numeric forms and unsupported versions;
decode/re-encode must be byte-identical. Admission fingerprint is SHA-256 over
these complete prefixed bytes. Store it in the existing creation receipt's
32-byte fingerprint and canonical receipt. Freeze independent literal goldens,
maximum legal field sizes, and unsupported/truncated/ambiguous-prefix failures
in implementation tests; do not generate expected bytes with the encoder under
test. Decoder dispatch adds only first byte `0x8a`; `0x89` P8 and `0x7b` historical
CreateRunCommand branches and their rejection precedence remain unchanged.

Derive four operation/request IDs as lowercase SHA-256 of
`b"deviation-protocol:p33-s4:internal-id:v1" + b"\0"` followed by big-endian
unsigned 16-bit length and ASCII bytes for each of purpose, controller value,
operation key. Purpose allowlist is the existing four strings `run.create/v1`,
`run.bind-player-character/v1`, `run.attach-session/v1`, `session.create/v1`.
The separate prefix prevents collision with P8 for the same caller key.
Retain those core operation namespaces/result schemas: they still describe the
same three mutations, while native admission evidence and ID derivation are a
separate family. Never change the existing P8 derivation function.

## 4. Replay, classification and failure ownership

Revalidate current caller/controller ownership on every attempt. A stored native
receipt is strictly decoded before comparing intent. Require stored player ID,
controller and configured source to match current authority; authorization
failure returns no result. Compare operation key, character ID, requested
pre-entry revision, world pair, exact S1 canonical bytes and normalized explicit
override set with stored intent. Override order is immaterial; omitted override
and explicit default override remain different. Well-formed differing intent
returns `IDEMPOTENCY_CONFLICT`; a receipt of another valid evidence family under
the native derived key also conflicts. Invalid stored evidence is integrity
failure, not a conflicting retry. Replay does not re-resolve changed defaults or
regenerate a Session; retained versioned S1/S2/world authority validates stored
values. Current eligibility is not reapplied to a committed receipt.

Load the Run with its immutable character prerequisite, native protocol, world
row, receipts/revisions, sole participation, owned Session, initialization event
and latest snapshot. The Session sibling replay validator verifies the native
evidence directly and preserves the existing initial-versus-progressed snapshot
rules. Missing owned Session after caller authorization is stored inconsistency,
not permission to create a replacement. A changed principal mapping cannot
reveal another player's admitted Session. Replay after Session gameplay advances
returns the original admission result and changes no rows. S4 supports Run
revision 3 only; later Run lifecycle evolution belongs to S7.

Extend S3 classification with a distinct `NativeRunAdmissionV1` detached result
(canonical Run, protocol binding and world binding). Admission evidence remains
an application-owned value; the domain never imports application types. Keep
`NativeRunProtocolBindingV1` for the existing S3 component-only family carrying
historical `CreateRunCommand` evidence; it is never a successful admission or
replay result. This preserves S3's valid revision-1 fixtures without treating
them as admitted production Runs. For explicit native admission evidence:

1. Preserve S3's initial Run/immutable-character loading and validation, now
   including native creation-evidence fingerprint/source decoding.
2. Require native protocol and world rows; apply unchanged S3 N01-N15 to the
   protocol before validating world physical types/versions/catalogue mapping.
3. At the complete native-admission reconstruction boundary in
   `infrastructure/run_protocol_binding_persistence.py`, invoked by both
   repository classification methods, require **both** receipt-to-binding checks
   after steps 1/2 have individually validated the native receipt and S3 binding:

   - Strictly decode receipt `resolution_input_hex` under section 3's canonical
     lowercase-hex rules and require byte equality with the stored binding's
     `resolution_input_canonical`.
   - Require receipt `resolution_fingerprint` to equal the stored binding's
     `resolution_fingerprint.hex()` (the existing 32-byte S3 storage expressed
     as lowercase 64-character hex, already verified by S3 to equal the
     reconstructed `resolved_protocol.fingerprint.value`).

   Neither equality may be omitted or substituted for the other. Successful S3
   internal reconstruction proves binding consistency, not receipt agreement.
   A mismatch in either comparison raises exactly
   `RunProtocolBindingStoredIntegrityError` with `__cause__ is None` (`from None`),
   with no trusted result, repair or writes. Malformed individual evidence keeps
   its earlier owning failure; this comparison adds no exception or encoding.
4. Require revisions 1/2/3 and current revision 3, the three native-derived IDs,
   matching receipts, exactly one participation at 3, both bindings at 3, and
   common UTC creation/binding/activation/Session/event time.
5. Validate immutable/current character/controller consistency and the full
   structural Session/event/snapshot association, including stored player ID.
   Construct the detached admitted result only after all comparisons succeed.

Both detached classification and owned replay must use this same complete
reconstruction, including both step-3 equalities, before returning any trusted
admitted result. Replay preserves the caller/controller/character authorization
and receipt-intent ordering above; matching caller intent to receipt A does not
validate a substituted binding B. The repository's stored-integrity failure
passes through replay unchanged, not as `IDEMPOTENCY_CONFLICT` or a new service
wrapper. Existing S1/S2/S3 individual validation and cause ownership is unchanged.

Include the world table in missing-current orphan probes. A world row on legacy
or component-only evidence is contradictory stored state; incomplete native
evidence never returns the S3 component result or legacy. The classifier reads
only and never infers a family from an omitted field. Existing valid legacy
classification and complete legacy-plus-protocol contradiction retain S3
behavior/order. New world-origin failures use
`RunProtocolBindingStoredIntegrityError` with no cause; lower native codec/world
validation failures are wrapped once with the exact lower exception as cause.
Existing S3 exceptions pass through unchanged. SQL reads retain
`RunProtocolBindingRepositoryError` with exact SQLAlchemy/driver cause.

Service-origin impossible associations raise
`NativeRunAdmissionIntegrityError(RuntimeError)` with no cause; lower Session
validation failures receive one such wrapper preserving the exact cause.
Keep application dependent only on domain/application error contracts:
repository-owned S3 exceptions pass through without importing infrastructure
classes into the application; the service wraps its own Session validation seam.
Invalid native creation storage uses existing `RunStoredRecordIntegrityError`.
Unexpected programming errors and process-control exceptions propagate.

Insertion of either new binding translates only a failed flush scoped to that
single insert with SQLAlchemy IntegrityError/asyncmy numeric 1062 into
`NativeRunAdmissionWriteConflictError` (application port; exact lower cause).
No localized key-name parsing. Other SQL faults remain infrastructure failures;
3819 is not idempotency conflict. Existing receipt/Run/participation/Session
conflict types and CAS false cause full rollback. After exit, one fresh
read-only reconciliation attempt returns an owned exact winner or conflicting
receipt; without a receipt return `RUN_ENTRY_CONFLICT`. Never query a failed
transaction, retry the writes automatically, or treat an ID collision alone as
proof of a winner. Cancellation is re-raised as the identical exception.

Uncertain commit raises `NativeRunAdmissionOutcomeUnknownError` with the exact
commit failure as cause after cleanup; it issues no automatic second admission.
An explicit same-command retry reauthorizes and reconstructs the stored result
if committed, or may perform one fresh admission if absent. A cleanup failure
after acknowledged commit also withholds success; explicit replay recovers that
known committed family. No exactly-once delivery claim is made.

The concrete port additions are `RunCreationReceiptRepository.add_native_with_evidence`
(same receipt/created_at arguments as P8, native evidence type),
`RunProtocolBindingRepository.add_native(binding: NativeRunProtocolBindingV1,
*, created_at: datetime)`, and `RunEntryWorldBindingRepository.add_native`
(world-binding value and created_at). These stage/flush only. The existing
classified read methods add `NativeRunAdmissionV1` to their return union and own
complete world reads; no standalone world lookup authorizes admission. The
dedicated UoW exposes `run_entry_world_bindings` alongside the existing ports.
Native revision-one staging lives in the new admission module and calls
`runs.add_initial` plus `add_native_with_evidence`; the existing P8 creation
stager and committing service are not reused with an incompatible evidence type.
Reuse existing binding/activation stagers and pure constructors unchanged.

## 5. Atomic write set and physical schema

Use unchanged revision semantics: 1 CREATE/unbound `pre_first_turn`; 2
BIND_PLAYER_CHARACTER/immutably bound `pre_first_turn`; 3 ATTACH_SESSION/sole
participation and `active`. Native evidence belongs to the creation receipt,
not another revision. Both protocol and world `bound_state_version` equal 3.
Resolve and prepare before staging; freeze becomes durable at the one commit.
No intermediate revision is visible as a committed admission.

The write set is exactly three `run_revisions`, one `run_current` brought to 3
by existing CAS 1->2->3, one creation receipt, two mutation receipts, one
`run_session_participations`, one `game_sessions`, one initial `domain_events`,
one `game_snapshots`, one `run_protocol_bindings`, one `run_entry_world_bindings`.
The embedded immutable character binding is in Run revisions/current; character
current/revision rows are locked/read, never revised by admission. Stage creation,
bind, Session initialization, activation/participation, protocol then world.
Repository methods flush as required by FK/uniqueness but never commit. Any
exception, decision after staging, cancellation or CAS loss rolls back all of it.
No compensation, repair, backfill, partial success or read-time write exists.

Add migration `20260916_0007_native_run_entry_world.py`, revision
`20260916_0007`, down_revision `20260828_0006`; check uniqueness before
implementation. Preserve all older migration bytes. Add exactly one InnoDB
table `run_entry_world_bindings` (utf8mb4/utf8mb4_bin), with these ordered
non-null columns and no defaults:

| Column | Physical representation |
| --- | --- |
| `run_id`, `continuous_story_line_id` | ASCII/ascii_bin VARCHAR(128) each |
| `bound_state_version` | signed BIGINT, exactly 3 |
| `binding_epoch` | ASCII/ascii_bin VARCHAR(64), exactly `run-entry-world-binding` |
| `binding_record_version` | signed BIGINT, exactly 1 |
| `entry_world_id` | ASCII/ascii_bin VARCHAR(128), world ID grammar |
| `entry_world_version` | signed BIGINT, positive int64 |
| `scenario_id` | ASCII/ascii_bin VARCHAR(128), opaque ID grammar |
| `scenario_content_version` | ASCII/ascii_bin VARCHAR(32), opaque ID grammar |
| `default_character_definition_id` | ASCII/ascii_bin VARCHAR(128), opaque ID grammar |
| `created_at` | DATETIME(6), trusted UTC represented MySQL-naive |

PK `pk_run_entry_world_bindings(run_id)`; FK
`fk_run_entry_world_bindings_protocol(run_id)` -> `run_protocol_bindings(run_id)`;
FK `fk_run_entry_world_bindings_revision(run_id, continuous_story_line_id,
bound_state_version)` -> `run_revisions(run_id, continuous_story_line_id,
state_version)`; index `ix_run_entry_world_bindings_revision` on that triple.
Both FKs use RESTRICT for update/delete. Three checks are
`ck_run_entry_world_bindings_identity` (nonempty grammar for all six identity/
content strings), `ck_run_entry_world_bindings_versions` (bound=3, record=1,
positive int64 world version), and `ck_run_entry_world_bindings_epoch` (exact
epoch). App and stored validators enforce catalogue equality, timestamp and
cross-row binding; SQL checks do not claim to prove these. No ORM relationship,
cascade, update/delete method or second evidence table is added. Native evidence
uses existing creation-receipt BLOB/4096 limit without widening old columns.

Upgrade creates the empty table, checks/index/FKs only; prove byte-for-byte
old-row preservation. Downgrade 007 uses the same lock and connection/error
discipline as S3, then exact current/locking probes in order:
`SELECT 1 FROM run_entry_world_bindings LIMIT 1 FOR UPDATE`, then
`SELECT 1 FROM run_creation_receipts WHERE LEFT(operation_evidence_canonical, 1) = X'8A' LIMIT 1 FOR UPDATE`.
Native evidence even with
a missing world row refuses downgrade. Exact refusal is built-in
`RuntimeError("Refusing to downgrade P3.3-S4: native admission data exists; recovery must be forward-only")`
with no cause, before DDL. Otherwise drop protocol FK, revision FK, supporting
index, then table, checking connection state between acknowledged steps. Loss
or failure stops all later DDL; inspect/restore partial schema in test cleanup,
never reconnect and continue the failed operation. Do not delete admitted rows
to permit downgrade. Subsequent unchanged 006 downgrade still refuses existing
S3 bindings. Tests preserve distinct historical 005/006 states and final 007
head; no migration is run during this planning task.

## 6. Physical connection, locks and cleanup

Use dedicated `SqlAlchemyNativeRunAdmissionUnitOfWork` and factory, composed
from the normal engine; keep ordinary gameplay/P8 UoWs free of the named lock.
The application owns the transaction; all repositories share its AsyncSession.
Acquire an explicit `AsyncConnection` from the engine, retain it until cleanup,
and create the Session bound to that connection with explicit
`join_transaction_mode="rollback_only"`, `expire_on_commit=False`. The UoW owns
an explicit connection transaction; Session participation does not independently
commit it. Commit flushes Session state then commits the owned connection
transaction; rollback rolls it back and restores pending Session versions.
No pool return, reconnect, nested transaction/savepoint or connection replacement
occurs between acquisition and release. Integration tests prove actual connection
IDs at lock, inserts, commit/rollback and release, including reuse from the pool.

Begin the connection transaction, read `CONNECTION_ID()`, execute exactly
`SELECT GET_LOCK('deviation_protocol:p33:s3:run_protocol_bindings:ddl_write:v1', 30)`
before character/Run/Session locks, any admission SELECT or any staging/flush.
Require `type(result) is int and result == 1`. Acquire once; do not reenter this
connection-owned lock. A pinned-connection lifecycle guard prevents the protocol
and world writers from being invoked through an ordinary unguarded UoW. All
native writers, including future ones, must follow this exclusion protocol.
The lock serializes S4 admissions globally; bounded throughput is accepted for
this slice. No external/Provider work occurs while any lock is held; controller
resolution and file-backed content loading happen before UoW entry, all remaining
validation is in-memory or same-transaction database work.

| Outcome | Required handling |
| --- | --- |
| Acquire 0 | `NativeRunAdmissionLockError("ACQUIRE_TIMEOUT")`, no body/release SQL, rollback/close. |
| Acquire NULL or non-exact scalar | LockError `ACQUIRE_NULL` / `ACQUIRE_INVALID_RESULT`, no body/release; invalidate and physically discard. |
| Acquire statement failure or connection loss before/pending/after result 1 | LockError `ACQUIRE_STATEMENT_FAILED`, `ACQUIRE_CONNECTION_LOST_BEFORE`, `ACQUIRE_CONNECTION_LOST_PENDING` or `ACQUIRE_CONNECTION_LOST_AFTER`, exact observed cause (None for state-only); no body/release/reacquire, invalidate and physically discard. |
| Commit/rollback acknowledged, owner valid | Release exactly once on that same connection using `SELECT RELEASE_LOCK('deviation_protocol:p33:s3:run_protocol_bindings:ddl_write:v1')`; only exact integer 1 proves release. |
| Release 0/NULL/invalid scalar/statement failure | LockError `RELEASE_NOT_OWNER` / `RELEASE_NULL` / `RELEASE_INVALID_RESULT` / `RELEASE_STATEMENT_FAILED`; discard, never return apparent success. |
| Connection lost before/during release | LockError `RELEASE_CONNECTION_LOST_BEFORE` / `RELEASE_CONNECTION_LOST_PENDING`; no SQL on a known dead connection, invalidate/discard; no success claim. |
| Failure or cancellation before commit | Complete rollback before release; preserve the identical body/cancellation exception. A failed rollback forces discard, never release-and-reuse an unresolved transaction. |
| Commit acknowledgement lost | Do not infer rollback; discard the owner, report outcome unknown, explicit retry only. |

`NativeRunAdmissionLockError` is an application-port RuntimeError subclass.
Errors above have no cause for scalar/state-only failures, exact observed
exception cause for statement failures. Preserve primary traceback/cause and
attach cleanup failure as `primary.cleanup_error`; cleanup/discard failure never
replaces the primary. Without a primary, cleanup error is raised. Record failed
discard as `close_error`; never put that connection back into usable circulation.
Cancellation-safe rollback/release cleanup has one five-second total deadline
and is awaited (shield a retained cleanup
task and wait for completion, including repeated cancellation); do not abandon
a background task owning a pooled connection. If rollback/release cannot finish,
invalidate and physically discard; record a cleanup TimeoutError when the
deadline expires. Cancellation during commit still propagates the original
CancelledError, with `commit_outcome_unknown=True`; it never proves rollback,
and explicit retry is the only recovery. Client invalidation alone does not prove
instant server release: real-MySQL observer must confirm owner termination and
`IS_FREE_LOCK=1`. Retain original cancellation; never convert it to success.

Release SQL can autobegin a cleanup transaction after commit/rollback; close or
rollback that read-only transaction before pool return. Closing Session or
rolling back alone is not proof of named-lock release. Migration 007 uses local
built-in RuntimeErrors prefixed `P3.3-S4 downgrade ` for the corresponding S3
acquisition/release codes. Define body step labels `WORLD_PROBE`, `EVIDENCE_PROBE`,
`DDL_PROTOCOL_FK`, `DDL_REVISION_FK`, `DDL_INDEX`, `DDL_TABLE`: detected pre-step
loss uses `BODY_CONNECTION_LOST_BEFORE_<step>` with no invented cause; loss
during an issued statement uses `BODY_CONNECTION_LOST_<step>` with its exact
cause. After acknowledged table removal use `BODY_CONNECTION_LOST_AFTER_TABLE`.
Ordinary non-disconnect body errors propagate unchanged. Apply S3 saved-primary
precedence and prove each issued/unissued distinction. Existing migration
006 is neither imported as a runtime lock helper nor modified.

## 7. Risk-based acceptance matrix

Each row requires focused unit proof where suitable and real MySQL for database
claims. Fresh isolated fixtures own teardown; assert complete row sets and
old-row digests, not merely returned decisions. No arbitrary vector quota.

| Setup and owning boundary | Observable result | Mutation outcome |
| --- | --- | --- |
| Normal composed service, owned active character, explicit world and valid protocol/overrides; service + repositories | Exact admitted result; reopen independent UoW/connection and classify `NativeRunAdmissionV1`; IDs, bytes, timestamps, revisions and Session state agree; objects detached | One complete section-5 family and one commit; immutable character unchanged |
| Same command again, including after normal Session snapshot progression; service replay | Same result, zero issuers/preparation/writes/commit; retained versioned world mapping | No additional rows or refingerprinting |
| Same native key, one changed intent field at a time; reordered overrides; legacy key with same public text; service/evidence codecs | Changed field -> IDEMPOTENCY_CONFLICT; reorder -> exact replay; legacy/native derive distinct IDs, occupancy still enforced | Existing family byte-identical; no new partial family |
| Missing principal mapping, foreign character, stale revision, retired/exhausted character, occupied character; service | Authorization first; then exact stale/ineligible decisions in section-3 order | No admission writes; no information from another owner |
| Unknown/invalid/cross-profile proposal, world ref replaced by scenario ID, unknown world version, forged catalogue, incompatible scenario version/character; domain + service | INVALID_PROTOCOL / INVALID_ENTRY_WORLD / INVALID_SCENARIO_DEFINITION; corrupted server authority raises its integrity error; exact-type failures retain owning exception | No Run, Session or binding; no fixed-content mutation |
| Change stored controller/player/source or Session ownership; corrupt or omit each required row, alter binding revision/time/world association, unsupported evidence; classifier + owned replay | Exact integrity/authorization boundary and cause from section 4; no partial trusted result; native never classified legacy/component | Zero repair writes; surviving rows unchanged |
| Internally consistent A/B substitution described below; complete detached classifier + owned service replay | B passes individual S2/S3 checks; both complete boundaries raise exactly `RunProtocolBindingStoredIntegrityError`, `__cause__ is None`, including replay with intent A; no trusted result | Receipt A and all post-substitution rows remain byte-identical; zero repair/admission writes or commit |
| Genuine P8 legacy before/after upgrade and native calls; legacy entry/classifier/public ASGI | Existing V1 goldens, revisions 1/2/3, replay, recover/playthrough, public responses and route schemas unchanged | No protocol/world backfill and no legacy evidence rewrite |
| Two physical connections: same key/same intent, same key/different characters, different keys/same character; also native versus legacy admission on one character; service | Shared-lock ordering observable for native writers; exact follower replays or conflicts, distinct-key occupancy rejects; legacy competition uses existing character locks/uniqueness, including deadlock rollback; exactly one winner | One complete family; all loser candidate rows absent |
| Force generated-ID collision; independently exercise protocol/world/receipt/participation duplicate flush and CAS false; repository + service reconciliation | 1062 translation only at owning insert, exact cause; failed transaction rolled back before fresh read; no winner inference without receipt | Winner preserved, loser fully rolled back; no automatic write retry |
| Inject failure/cancellation at every staging boundary, post-flush/pre-commit, during acquisition/commit/release; UoW | Original primary/cancellation retained, cleanup error attached; uncertain commit explicitly reported; same-key explicit retry reconciles | Observer sees either zero family or complete committed family, never a subset; owner/locks gone |
| Migration 007 upgrade, empty downgrade and occupied downgrade; migration/metadata | One linear head 007; full column/constraint parity; exact refusal before DDL; raw malformed 0x8a evidence also refuses | All preexisting bytes retained; failed/partial DDL inspected before independent restoration |
| Native writer owns shared lock, commits or rolls back, while 007 downgrade starts with an older RR snapshot; physical migration boundary | Current/locking probe sees committed data and refuses, or sees rollback and permits empty downgrade; preserved S3 tests prove the same for component writer/006 at the historical schema | No lost binding/admission; no stale-snapshot empty decision |
| Downgrade owns lock after empty probe, real writer starts; observer is a third connection | Observe writer's exact GET_LOCK in server `User lock` wait and `IS_USED_LOCK` equal migration connection ID; zero insert/flush before grant. Release DDL or inject failure, then observe grant separately from transaction-close barrier | After successful removal writer fails missing-table with SQLAlchemy ProgrammingError/asyncmy 1146 and rolls back; after failed DDL/closed probe transaction valid writer can commit one complete family |
| Controlled different-lock negative control for preceding exclusion test; test-local wrapper only | Exclusion assertion must fail before releasing unrelated barrier; instrument actual acquisition rather than an unfinished task | Fixture restores schema/head/data/locks independently in each variation |
| Acquire/release scalar faults, DB disconnect, rollback/discard failure, repeated cancellation; native UoW and 007 migration | Exact stage/code/cause/primary precedence, no later SQL on lost owner; observer confirms termination; no pool-reuse lock leak | No false success; committed data retained, uncommitted family removed |
| `build_default_services` and explicit native builder with production MySQL adapters, existing configured resolver and SessionService; composition + ASGI | Callable service present without opening DB during build; production-composed internal enter succeeds; OpenAPI/route inventory byte-equivalent, legacy route still selects RunEntryService; Demo native service absent | Native writes only through internal service; no public native reachability claim |

The A/B setup uses the existing S2 literal vectors `RESOLUTION_001` and
`RESOLUTION_004` in `tests/unit/test_run_protocol_resolution.py`: A is profile
`difficulty.fragile-alliance` version 1, presentation balanced/lawful/off, no
overrides; B has the same envelope/profile with explicit `conflict_intensity=65`.
Admit A normally, then use fixture-owned SQL to replace only the binding's
canonical resolution input, all five objectives and fingerprint together with
valid B values. The objectives change from `(60, 45, 65, 60, 60)` to
`(60, 45, 65, 60, 65)` in S2 parameter order. Preserve receipt A byte-for-byte,
Run/line/revision/timestamp associations, envelope/selectors, world and Session
rows. Independently establish B's individual S2/S3 reconstruction success, then
use fresh UoWs for complete detached reconstruction and authorized owned replay
of the original command A. Each must reject at section 4 step 3 with the exact
stored-integrity outcome above, not an intent conflict. Compare all row bytes
before/after these reads; setup substitution is the only mutation. Verify both
normative comparisons in implementation review: this combined mismatch case
alone cannot prove that neither equality was silently omitted.

Native writer tests use migration 007; historical 006 migration tests retain their
S3 component writer. Also run unchanged 006 downgrade against a committed native
family at 007: its protocol current-read must refuse before DDL. Never claim an
empty 006 downgrade can drop a parent still referenced by 007's FK: normal
Alembic ordering removes empty 007 first. A production writer acquiring after
that removal fails closed on absent schema, rolls back and releases; it cannot
recreate removed tables or fall back to legacy.

## 8. Future implementation path inventory

Paths below are the expected edit inventory derived from those boundaries.
New files are marked **new**. Do not silently absorb unrelated work; reassess
material contract/schema/scope changes under the workflow. A mechanical path
adjustment must be explained and authorized with its dependency evidence, not
made into a new lifecycle gate. Frozen plans and old migrations stay untouched.

| Path (relative to repository) | Concrete responsibility |
| --- | --- |
| `src/deviation_protocol/domain/entry_world.py` **new** | Strict world reference, one authored internal catalogue, trusted lookup and association definition |
| `src/deviation_protocol/domain/run_protocol_binding.py` | Add world-binding and complete native-admission detached carriers; retain existing component/legacy types |
| `src/deviation_protocol/application/native_run_admission.py` **new** | Command/result/decisions, versioned evidence and deterministic native IDs, ordered service/replay/reconciliation |
| `src/deviation_protocol/application/ports.py` | Native evidence carrier union, explicit native creation insert, protocol/world writer/read contracts and dedicated UoW/factory/errors |
| `src/deviation_protocol/application/session_service.py` | Native sibling replay validator using shared field-level initialization checks; preserve P8 validator contract |
| `src/deviation_protocol/infrastructure/run_persistence.py` | Native evidence dispatch, fingerprint and source validation in full Run record-set checks |
| `src/deviation_protocol/infrastructure/run_protocol_binding_persistence.py` | World stored codec and admitted-family checks, including both receipt-to-protocol equalities; preserve S3 N01-N15 and lower-exception ownership |
| `src/deviation_protocol/infrastructure/orm_models.py` | Exact world-binding table mapping |
| `src/deviation_protocol/infrastructure/repositories.py` | Guarded protocol/world insertion, native receipt insert, complete classification and orphan detection |
| `src/deviation_protocol/infrastructure/unit_of_work.py` | Dedicated pinned-connection native UoW; shared repository construction and complete cleanup without changing ordinary UoW semantics |
| `src/deviation_protocol/api/main.py` | `build_native_run_admission_service`, normal production wiring to dedicated factory and approved catalogue; no route change |
| `src/deviation_protocol/api/dependencies.py` | Optional `ApiServices.native_run_admission_service` internal field, default None for legacy/Demo injected service bundles; no public dependency endpoint |
| `alembic/versions/20260916_0007_native_run_entry_world.py` **new** | Additive schema and shared-lock, data-preserving downgrade |
| `tests/unit/test_entry_world.py` **new** | Catalogue/ref strictness, unknown/forged inputs and fixed scenario mapping |
| `tests/unit/test_native_run_admission.py` **new** | Literal evidence goldens, service order/replay/conflicts, transaction doubles implementing native ports and rollback semantics |
| `tests/unit/test_run_persistence.py` | New evidence branch, original V1 golden preservation, full native history validation |
| `tests/unit/test_run_protocol_binding.py` | Complete-admission versus component carrier distinction and detached immutability |
| `tests/unit/test_run_protocol_binding_persistence.py` | World/native association corruption, A/B substitution and first-failure/cause proof, retained S3 fixtures |
| `tests/unit/test_run_repositories.py` | Update exact two-read-method surface expectation for explicit guarded writer; test native scope/flush errors while retaining no-public-exposure assertions |
| `tests/unit/test_repository_and_uow.py` | Native factory/adapter doubles, same physical connection through commit, release, rollback and cancellation; ordinary UoW regressions |
| `tests/unit/test_run_composition.py` | Production native object graph/build laziness and unchanged API/Demo composition |
| `tests/integration/test_mysql_native_run_admission.py` **new** | Real production-composed admission, authority/replay/concurrency/rollback/uncertainty and detached reconstruction, including A/B substitution at both complete boundaries; test-local barriers/doubles |
| `tests/integration/test_mysql_native_run_migration.py` **new** | 007 metadata/upgrade/downgrade, writer coordination and cleanup/loss/negative-control proof |
| `tests/integration/test_mysql_run_protocol_binding.py` | Distinguish historical S3 target 006 from current head 007; run row/classifier tests at 007, isolate old destructive migration tests in their exact 005/006 interval, then restore 007 before any new classifier query; preserve all S3 proof assertions |
| `tests/integration/test_mysql_connection.py` | Current head/table inventory includes world-binding table |
| `tests/integration/test_mysql_run.py` | Current-head/schema inventory changes only; keep historical Run migration expectations |
| `tests/integration/test_mysql_player_character.py` | Current-head/table inventory changes only; retain historical character migration assertions |
| `PLANS.md`, `docs/run_protocol.md`, `docs/architecture.md` | Same-round implemented/status/evidence synchronization, no separate S3 closeout |

New native test doubles live in their owning unit/integration files. Ordinary
P8 test UoWs and Demo adapters do not gain a fake native path; the dedicated
factory and optional service field preserve their compatibility. Shared UoW
changes must be tested with existing subclass overrides. No package re-export,
configuration/story edit or S1/S2 implementation edit is required.

Execution-only regressions (not edit allowances): `tests/unit/test_run.py`,
`test_run_operations.py`, `test_run_service.py`, `test_run_entry_service.py`,
`test_run_entry_api.py`, `test_run_protocol.py`, `test_run_protocol_persistence.py`,
`test_run_protocol_resolution.py`, existing Session/character-authority suites,
Demo persistence/composition suites, `tests/integration/test_mysql_run_entry_playthrough.py`
and `tests/integration/test_mysql_player_character_run_binding.py`. Their existing
UoW adapters and receipt/replay fault injection must still work. No Web edits or
browser run is needed to prove unchanged public contracts.

## 9. Implementation sequence and proportionate verification

After approved plan publication and separate implementation authorization:

1. Implement strict world/evidence/result contracts and native Run codec branch;
   freeze independent goldens and run focused unit tests. Build the native UoW
   and staging adapters with failure/cleanup tests before exposing the service.
2. Add schema/strict reconstruction and service together, then normal composition.
   Run focused entry, Session, repository and composition regressions while
   changing their boundaries, including section 7's A/B substitution and exact
   stored-integrity cause. Verify both section-4 receipt-to-protocol equalities
   are enforced; successful S3 reconstruction alone is insufficient.
   No partial-admission milestone counts as S4 done.
3. On stable code, run new real-MySQL admission/migration suites plus affected
   S3, Run, character-binding and legacy-playthrough integrations locally with
   zero environment skips, including the A/B detached/owned-replay rejection
   with no writes. Verify ORM/schema parity and the historical fixture
   restoration sequence before broad suites. Test only MySQL 8 using asyncmy
   and `deviation_protocol_test`; no SQLite/mocks substitute for physical proof.
4. Run canonical `scripts/verify.ps1 -Mode Offline`, `-Mode MySQL`, and
   `-Mode Full` once the affected code is stable (reuse earlier identical focused
   results where applicable). Retain the required compileall of src/tests/alembic,
   dependency consistency and sanitized Alembic heads/history (one linear head
   `20260916_0007`). Broad coverage is warranted by shared Run codecs/UoW and
   composition; repeated exhaustive baseline runs before each edit are not.
5. Complete canonical documentation synchronization, exact diff/scope/encoding
   checks, freeze candidate/evidence, then obtain one substantive independent
   implementation review. Corrections receive focused review of affected risks.

All project Python commands use `.\.venv\Scripts\python.exe`; tests use
`-m pytest`. Offline work uses the sanitized canonical runner. MySQL/Full work
requires separately authorized test DB access and safe driver/database preflight;
never print a URL or read `.env`. Keep Live disabled and Provider calls absent.
Do not edit scripts merely to schedule evidence reuse.

S3's recorded complete S2 proof has 23 passed, zero skips and 5,624,910 public
resolver calls, retained under `s3-implementation-20260916-audit/correction`.
Reuse its expensive exhaustive test only after locating actual manifest/output
and verifying source, tests, dependency identity and environment assumptions are
unchanged and applicable. Run adjacent non-exhaustive S1/S2 tests and new native
resolution round trips. Neither a documentation edit nor a head/table assertion
change alone requires exhaustive S2 rerun. Changed resolver/authority/dependencies,
missing records or unverified applicability require fresh relevant evidence;
never relabel deselected evidence as executed. S3's old schema/lock proofs do
not replace new writer/007 proof; preserve required unchanged historical proof
and rerun affected tests without weakening their assertions.

For each implementation verification retain **outside the repository** sanitized
command, complete output/first traceback, exit status, tested revision or
candidate per-path hashes, dependency/environment applicability, selections,
skips/deselections and their reasons. Store a manifest linking each acceptance
row to those records. The implementation handoff must name an absolute external
bundle location so the next reviewer can actually locate it. Before broad runs
record which expensive proof is reused and why; missing evidence is not a pass.
DF-001 remains deferred with its documented process-local language containment
and owner/reassessment milestone. Apply workflow non-blocking deferral to genuine
new eligible findings; optional refinements do not prevent implementation from
starting and no speculative finding is added by this plan.

## 10. Candidate, review and lifecycle

The documentation candidate contains exactly this new plan, `PLANS.md`,
`docs/run_protocol.md`, and `docs/architecture.md`. Deferred register is unchanged;
DF-001 remains deferred. Frozen plans, source, tests, migrations and workflow
rules remain untouched. Current S3 status is synchronized in roadmap, protocol,
architecture, deferred-topic and document-index sections in this same candidate.

Review record (2026-09-16): **CHANGES_REQUIRED**, one finding: complete native
admission reconstruction did not explicitly bind the individually valid S3
protocol to the native receipt, allowing an internally consistent A/B protocol
substitution to escape the stated checks. Sections 4/7/8/9 now specify both
equalities, their owner/order/failure semantics and the focused regression.
This is a documentation correction, not approval or an implementation finding;
the corrected candidate remains unapproved pending focused re-review by the
previous independent reviewer of this binding check, its A/B specification and
direct dependencies. Preserve prior conclusions for unchanged content; prior
review conclusions do not approve the changed candidate bytes.

The single operative plan-review success token is:

`PHASE_3_3_S4_NATIVE_RUN_ADMISSION_ENTRY_WORLD_PLAN_INDEPENDENT_REVIEW_APPROVED`

An independent reviewer may use disposition `APPROVED` or
`APPROVED_WITH_DEFERRED_FINDINGS`; both require the same token and complete
technical-plan acceptance. Neither disposition is a competing token. The review
must assess authority/content reuse, byte contracts, transaction/lock ownership,
schema/downgrade, complete production composition, test feasibility, and scope
against the complete four-file candidate and recorded hashes. Authoring does not
approve the plan. Next step is the focused independent read-only re-review
specified above, preserving applicable prior conclusions for unchanged content.

The sole implementation-review success token is **dormant**, not operative now:

`PHASE_3_3_S4_NATIVE_RUN_ADMISSION_ENTRY_WORLD_IMPLEMENTATION_INDEPENDENT_REVIEW_APPROVED`

It becomes operative only for separately authorized implementation after this
plan is independently approved, separately authorized for exact staging/commit,
manually pushed by the user and confirmed at a clean aligned baseline. Both
successful dispositions above also emit that same implementation token when its
gate is active. No post-commit audit or separate lifecycle-closeout gate is added.

Record SHA-256 for each candidate file and a reviewable complete patch externally
in the authoring handoff, avoiding a self-referential hash in the candidate.
Patch construction: raw UTF-8 Git diffs, one per candidate path in ordinal path
order, `--no-ext-diff --no-color --binary --full-index --src-prefix=a/
--dst-prefix=b/`; tracked paths diff against HEAD, the new file uses
`git diff --no-index` from `NUL` to its relative path. Concatenate exact stdout
bytes, no separators/BOM/newline conversion. Record command exit codes (1 is
expected for the new-file diff), patch byte length/SHA-256 and per-file hashes.
Any changed candidate byte invalidates approval; a relevant baseline change
requires workflow reassessment and fresh identity/review. Approval authorizes
no Git writes, runtime work or later slice by itself.

## Guardrail impact

None. This plan applies existing DB-001, AUTH-001, STATE-001, SCENE-001,
CONTENT-001, API-001, MODEL-002, PLAY-001 and environment/Git rules; no new
confirmed defect establishes or changes a reusable guardrail.
