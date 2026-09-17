# P3.3-S7-1 — Explicit native Run exit after a Session ending

Status: **Plan candidate; not approved or implemented.** This document includes
the dependency allocation of remaining S7 work and specifies only S7-1. There
is one substantive independent plan review, not a separate decomposition gate.

## 1. Baseline, authority and selected playable increment

Planning baseline: `2f144599af5977e871c7a3466c52896b6a36510c`, with local
HEAD/main/origin/main aligned at 0/0, clean worktree/index, no conflicts or
active Git operations, verified without fetching before authoring.

S6 implementation is independently approved and published at this baseline.
Its representative local deterministic Demo browser journey reached the
version-10 `FAILED` ending **记录成为现实**, after explicit setup, one native
admission and ten UI actions. Same-tab recovery and missing-Session handling
after a coupled backend/frontend restart were observed. The
[bounded evidence record](run_protocol.md#s6-publication-and-local-browser-evidence)
preserves the report's instrumentation and screenshot limitations. This is
neither all-path browser proof nor wider-release readiness.

The [frozen parent allocation](phase_3_3_run_protocol_implementation_plan.md#p33-s7--later-worlds-visits-regions-revisits-progression-and-persistent-world-continuity)
assigns later continuity to S7. The
[minimum Run lifecycle](minimum_run_core_implementation_plan.md),
[Run product authority](run_protocol.md#lifecycle),
[character contract](structured_player_character_contract.md#12-lifecycle-state-model)
and [final product authority](final_narrative_experience.md) remain controlling.
This candidate proposes the first narrow terminal transition under the minimum
core's explicit delegation to Phase 3.3; it does not amend frozen parent bytes.

Actual dependency boundary:

- `domain/run.py:CanonicalRun` admits only the exact active revision-three
  entry shape and pre-first-turn history; it rejects terminal Runs.
- `domain/run_protocol_binding.py:NativeRunAdmissionV1` and the SQL/Demo
  classifiers require the exact three-revision native admission family.
- `SessionService.get_view`, the native mechanics coordinator and admission
  replay consume that classification. Simply changing a Run status would
  break ended-Session reads and replay, even if SQL accepted the row.
- Session settlement owns its ending event, completed scenario memory,
  snapshot and version. It does not terminate the Run, historicalize its
  binding, or change the Structured Player Character lifecycle.
- The current authored world catalogue has only `world.death_certificate@1`,
  mapped to `death_certificate` / `death-certificate-1.1.0`. There is no
  authored next-world destination, visit identity or persistent world-state
  contract. Restarting that Session cannot stand in for a revisit.

Selected increment: after a native Session has ended, its controller may
explicitly **end this journey**, retain its readable history, and return to
setup. The same still-active character becomes eligible for a separately
confirmed new Run through existing admission. This removes the completed
Session's active-binding dead end without requiring new fiction or inventing
a next-world rule. It advances repeated playable journeys, not same-line
continuation. Doing nothing leaves the existing active Run and its binding
intact for future authorized continuation.

The exit is an irreversible, explicit abandonment of this Run's line, represented
as `terminated`; it is not normal Run completion, character retirement, death,
resurrection, a world-line rewrite, or a reset of old state. A scenario `FAILED`
ending is not evidence of canonical character final death. Existing S6 makes
no such mapping, and S7-1 must not infer one from the ending ID or prose.

## 2. Remaining S7 allocation in dependency order

These are responsibilities and prerequisites, not advance implementation
authorization or fully frozen designs for later subdivisions.

| Subdivision | Useful result and dependencies | Decisions it must freeze before implementation |
| --- | --- | --- |
| **S7-1: post-ending Run exit** | This plan: ended native Session -> explicit terminal Run/binding transition -> retained history -> explicit fresh admission. Uses S1–S6. | Exact terminal lifecycle, historical reconstruction, replay, concurrency, public recovery and schema amendment below. |
| **S7-2: first same-line later-world continuation** | Builds on historical/current Run separation. An active Run with an ended Session receives a genuinely authored next playable destination while retaining character, protocol and line. Requires approved destination content and the minimum persistent world/visit/region representation before creating later participation. | Distinct world/version, visit occurrence, region and Session identities; canonical world-state fields/provenance and reconstruction; atomic handoff; content/mechanics compatibility; exact eligible pool, seed ownership/encoding, ordering, weights/tie-breaks, anti-repeat, required-progression priority and empty-pool behavior. No fake destination or repeated entry Session. |
| **S7-3: important-world revisits and region progression** | Requires S7-2's stored visits/world state and authored revisit content. Re-entry preserves prior facts/consequences and opens only authorized regions. | Authored importance, recovery/progression predicates, cooldown units/bounds, priority injection, anti-repeat exceptions, region unlocks, reward/progression provenance and anti-farming. Required progression cannot be stranded by random weighting. No reward system is presumed to exist. |
| **S7-4: authorized world-line transitions and terminal completion** | Requires the world-state/history and progression authorities of S7-2/3. Preserve Run-owned line and character identity unless a separately authorized transition expressly changes the relevant world state. | Exact canon-preserving transition representation, affected facts and atomicity; normal `completed` criteria; replay/recovery and forbidden reset/copy cases. This does not silently replace a Run's permanent `ContinuousStoryLineId`. |
| **S7-5: bounded continuity integration and final S7 evidence** | Reconciles all parent criteria 10–12 and the above implemented slices. Important-NPC priority can participate only after its separate owning authorities publish both logical-identity and authored-world predicates. | End-to-end continuity/revisit/regional/progression evidence and remaining exposure. Predicate absence leaves that priority unavailable and other valid deterministic selection operational; no NPC identity manufacture or Phase 3.4/6 dependency is added. |

The eventual subdivision boundaries may be narrowed by their own dependency
inspection; none of the parent responsibilities is dropped. S7-1 does not
complete parent criteria 10, 11 or 12, S7, or Phase 3.3. Phase 8 remains complete
at P8-S6; there is no P8-S7. Phase 3.4, golden memory, cross-scenario NPC identity,
Phase 6 hooks and production Provider distribution remain outside S7.

## 3. User-visible behavior and non-goals

On a fresh authoritative native `ENDED` View, fetch the Run-status projection
defined below. Only its `can_exit=true` enables **结束本次旅程**. Present an
explicit confirmation explaining: the current journey will end permanently;
its ending/history will remain; starting again creates a different journey,
not a continuation. Cancel before submission performs no request or mutation.

One confirmed click sends one exit POST. Disable duplicate exit/admission/action
controls while that operation is pending or uncertain. On confirmed termination,
keep the ended View readable and show **返回设置**. That separate local action
clears the existing Session recovery record, then refreshes eligible characters
and entry options; character/profile/world require explicit selection under S6
rules. Successful exit alone does not clear storage, select a character, create
a Session or submit admission. A later explicit confirmation may admit the same
eligible character into a new Run with a new line and Session.

An active Session has no exit control under S7-1. Legacy Session-backed Runs and
standalone Sessions retain existing terminal UI and behavior. Dynamic Demo
remains legacy-only. Local clear always remains client-only and must not be
relabelled as Run exit. A missing Session after Demo restart cannot authorize exit.

Non-goals: automatic exit on ending/reload/clear; mid-Session abandonment;
`completed`; character lifecycle mutation; another Session within the same Run;
world/visit/region creation, world selection, rewards, progression, NPC recovery,
cross-tab Run discovery, durable pending browser operations, UI redesign, new
story canon, Provider work, or changing the S6 discovery-refresh defect.

## 4. Exact identities, transitions and authority

Only this new transition is admitted:

| Before | Preconditions | After |
| --- | --- | --- |
| Exact S4 native admission at Run revision 3, `active`, one Session participation, active immutable character binding | Authenticated current controller and Session owner; complete native family; latest valid Session snapshot is `ENDED` with catalog-valid `RESOLVED` or `FAILED` ending and completed scenario memory; request matches Run revision 3 and exact current Session version | Run revision 4, `terminated`, new mutation kind `TERMINATE_NATIVE_RUN`; same Run/line/participation/protocol/world/character reference; binding becomes `historical` with one trusted UTC `inactivated_at`; current active-character uniqueness slot becomes NULL |

No other active shape, pre-first-turn Run, legacy family, fifth revision or
terminal-to-active transition is authorized. A later subdivision must explicitly
extend this closed transition contract. All initial provenance, binding operation,
source and `bound_at` remain unchanged. The new mutation provenance alone records
the exit operation/source/time. Revision three remains byte-identical with its
active binding; historicalization never rewrites prior revisions.

The Run application service owns the transaction and decision. Transport submits
intent, not terminal authority. Run/line/character/world IDs are resolved through
the owned Session participation and validated history; none can be supplied in
the exit body. Session version and Run version remain distinct concurrency tokens.
The Structured Player Character current row, revision, lifecycle, declarations,
development and controller binding are not mutated by exit. Later admission uses
its current revision through existing discovery and increments it only as the
existing admission contract requires. Existing retired/deceased ineligibility
continues to apply; no exit operation can reactivate a character.

Session snapshots, ending events, memory, resources, accepted prose, action
receipts and narrative jobs are unchanged. The exit records the ending evidence
it consumed; it does not issue another scenario ending or memory completion.
The new Run/line after a later admission has no inferred continuity relationship
to the terminated one. No old facts, consequences or identities are copied,
erased or claimed to have transferred across lines.

## 5. Persistence and strict reconstruction

Reuse `run_revisions`, `run_current` and `run_mutation_receipts`. Necessary new
storage is one immutable revision-four row and one successful exit receipt per
terminated Run, plus the atomic current-row update. No table/column, Session
schema, world-state schema or browser storage family is added.

Extend the Run receipt union with exactly:

- namespace `run.terminate-native/v1`;
- mutation kind `TERMINATE_NATIVE_RUN`;
- result schema `run.terminate-native-result/v1`, with the existing safe Run
  result fields: same Run/line, `terminated`, version 4, null participation and
  no applicable-character result member;
- existing receipt key `(run_id, operation_namespace, operation_id)`, unique
  resulting version and revision FK. It grants no controller authority.

Freeze internal operation ID as lower-case SHA-256 of canonical UTF-8 JSON
`{"controller_binding":C,"public_operation_key":K,"run_id":R,"schema":"run.terminate-native-operation/v1"}`.
Canonicalization uses existing `canonical_run_operation_bytes`: sorted keys,
compact separators, no ASCII escaping, strict exact scalar validation first.
No clock, random value, locale, presentation or model input enters this identity.

The request fingerprint is SHA-256 of canonical JSON containing exactly
`schema="run.terminate-native-request/v1"`, trusted controller binding,
principal player ID, public operation key, resolved Run ID/line ID, path Session
ID, expected Run version, expected Session version and configured trusted Run
source reference. Persist versioned operation evidence containing that exact
request plus `schema="run.terminate-native-evidence/v1"`, scenario ID/content
version, ending ID/status, committed Session version and SHA-256 of the existing
canonical snapshot state. These latter facts come from the locked validated
snapshot, never the request. No raw snapshot/prose is duplicated into the receipt.
The exact request keys are `schema`, `controller_binding`, `player_id`,
`public_operation_key`, `run_id`, `continuous_story_line_id`, `session_id`,
`expected_run_state_version`, `expected_session_state_version`, `source_reference`.
The exact evidence keys are `schema`, `request` (that object), `scenario_id`,
`scenario_content_version`, `ending_id`, `ending_status`, `session_state_version`,
`snapshot_sha256`. Reuse the existing `narrative_outcome_policy.state_fingerprint`
encoding over the fully validated `GameState` for the snapshot hash, not raw SQL
JSON text or a new serializer. Existing strict ID/content/version carriers apply;
ending status is exactly `RESOLVED|FAILED` and hashes are 64 lower-case hex digits.
Bound the complete canonical evidence to 4,096 UTF-8 bytes; reject unknown fields,
types, encodings, versions, overlong data and noncanonical bytes. The receipt's
fingerprint binds request intent; reconstruction separately validates all ending
evidence against the immutable ended Session snapshot. Exact receipt replay
compares the original request fingerprint before evaluating new-operation staleness.

Implement a new `NativeRunTerminatedV1` classified result holding the validated
revision-three `NativeRunAdmissionV1`, the current terminated `CanonicalRun` and
validated exit evidence. Keep `NativeRunAdmissionV1` itself strictly revision
three. Do not accept arbitrary revision >=3 or broaden legacy classification.
The typed exit-evidence carrier belongs in the domain binding module; it must
not import application receipt/command types into the domain. The native
classifier validates the original admission prefix independently, including its
original common timestamp, and then the terminal suffix. It must not apply the
old three-revision timestamp/count checks to the new current revision.
The terminated family requires exactly revisions 1/2/3/4, exactly three mutation
receipts and one participation; every receipt binds its adjacent revisions.
Protocol/world binding `bound_state_version` remains 3, not current version 4.

Extend common Run reconstruction narrowly: a binding can differ from the prior
one only in `binding_state` and `inactivated_at` on the validated terminal edge;
participation versions exclude that terminal edge as well as the binding edge.
All immutable reference/provenance equalities still hold. Require nondecreasing
trusted UTC exit time, equal across new receipt/revision/current/inactivation,
at the existing Run DATETIME(6) precision. Do not compare that time with a newly
invented Session timestamp or normalize stored evidence after reading it.

Reject partial histories, missing receipts, missing/cross-bound native markers,
changed bound versions, terminal rows with active uniqueness slots, historical
bindings before revision four, ending-evidence mismatch, and absent/corrupt
Session evidence. No read repair, legacy fallback, backfill or old-row rewrite.
Original admission/character revisions and initialization evidence remain the
source of historical native context even after another Run is admitted.

### Migration

Add `alembic/versions/20260917_0008_native_run_exit.py`, revision
`20260917_0008`, parent `20260916_0007`. Mirror only the necessary new branches
of the Run current/revision provenance checks and mutation-receipt protocol
matrix in ORM metadata. The terminal branch requires prior/current versions
3/4, `terminated`, `TERMINATE_NATIVE_RUN`, a complete historical binding and
the existing null active-character slot invariant. The new receipt matrix branch
requires namespace/kind/schema above, versions 3/4, terminal result and all
participation/character-result columns NULL. Keep every existing constraint
branch, FK, unique key, table/column and earlier migration byte unchanged.
The changed constraint names are `ck_run_revisions_mutation_matrix`,
`ck_run_current_mutation_matrix` and `ck_run_mutation_receipts_protocol_matrix`.

Upgrade changes constraints only and preserves every old row byte. Both migration
directions and the new writer use the existing pinned-connection advisory lock
`deviation_protocol:p33:s3:run_protocol_bindings:ddl_write:v1` with timeout 30.
Do not invent another lock order or generalized migration framework.

Downgrade performs current locking reads on the same physical connection of all
three tables for terminal-kind/status/namespace/schema evidence, including
malformed partial terminal families. Any such row refuses downgrade before DDL;
never delete, truncate, backfill or make a terminal Run active to downgrade.
An empty terminal probe permits restoration of the exact predecessor constraints.
Old active rows need not be absent. Preserve the existing loss/acquisition/release
and primary-error precedence/discard rules through every DDL boundary. MySQL DDL
is not transactionally atomic: partial DDL failure stops with exact remaining
constraint state recorded; no claimed rollback, automatic reconnect or continued
DDL after connection loss. A verified operator repair is required before writers
resume. Runtime use requires schema 008; old application deployments cannot read
terminal families and must not be mixed with new writers. If safe changes cannot
fit these three constraint amendments, stop for bounded scope reassessment.

## 6. Transaction, races, rollback and replay

Use the existing pinned native UoW factory as one owner; repositories flush and
never commit. There is no Provider, renderer, nested service commit or retry loop.

1. Strict transport validation and principal/controller resolution precede
   mutation. An owned read may resolve Session -> participation -> character
   for lock targeting only; it is not trusted until revalidated under locks.
2. Acquire the shared native advisory lock on its pinned connection, then lock
   the current character row, target Run current/history/receipts in the existing
   classifier order, then owned Session/latest snapshot. This preserves the
   admission/retirement character-first order. Recheck all target associations
   and ownership after locks; disappearance or substitution fails closed.
3. Validate the complete stored native family. Evaluate exact scoped receipt
   replay/conflict before new-operation lifecycle/version checks. An original
   same-key request replays the same terminal safe result after exit or later
   admission without changing any old/new Run, character, Session or receipt.
4. For a new key require exact active revision three, active binding, an active
   current character owned by this controller, the requested Session version and
   committed valid ending. Active Session, stale token or terminal Run rejects
   with no writes. Request/job status alone is not evidence of an ending.
5. Choose one trusted time; build/validate the detached terminal successor and
   ending evidence. Append revision 4; CAS current from version 3, historicalize
   the binding and free its active slot; append receipt. Validate the complete
   candidate family before the sole commit. Return success only after commit.

Failed validation, CAS loss, uniqueness collision, flush or pre-commit
cancellation rolls back all three writes. Propagate cancellation; do not swallow
it or synthesize success. Commit transport/cancellation or post-commit cleanup
uncertainty is not rollback proof: discard unsafe connections under the existing
UoW contract, report unknown outcome, and reconcile by safe GET or explicit exact
retry. No compensation, automatic admission, receipt deletion or generic replay
loop is permitted. A 1062 must be classified by the existing supported constraint
handling; an arbitrary integrity error is not an idempotent success.

Two same-key exits serialize and return one commit plus exact replay. Different
keys racing for the same Run produce one winner and `RUN_EXIT_NOT_AVAILABLE` for
the other. A changed request with an existing key produces `IDEMPOTENCY_CONFLICT`.
Concurrent new admission of the same character either sees the old active
binding and rejects or follows the committed exit and admits once under existing
rules. Exit of the old Run must never clear the new Run's active slot. Retirement
serializes on the same character lock and retains its existing eligibility rules.
An in-flight final turn either commits an ending first or leaves exit unavailable;
exit cannot cancel a job, finalize a proposal or treat an action's unknown outcome
as settlement. Verify the lock graph against actual turn readers (which do not
take the native writer lock); do not add Run-for-update reads to turn paths.

## 7. Public contract and recovery

Add two Session-scoped routes through normal production composition and
deterministic Demo. They use existing principal/ownership and ErrorResponse.

| Route | Request | Success |
| --- | --- | --- |
| `GET /v1/sessions/{session_id}/run-status` | No body/query; existing Session path grammar | HTTP 200, closed `schema_version="native-run-status/v1"`, `session_id`, `run_id`, `run_state_version`, `session_state_version`, `lifecycle_status`, `can_exit` |
| `POST /v1/sessions/{session_id}/run-exit` | Required existing Idempotency-Key grammar; closed JSON body with only exact integers `expected_run_state_version` and `expected_session_state_version` | HTTP 200, same status shape, version 4, `terminated`, `can_exit=false`; exact same response on replay |

Operation IDs are respectively `get_native_run_status` and `exit_native_run`.
Run versions are positive signed int64; Session versions are 0..2^63-1;
Web accepts only JavaScript-safe integers. IDs use the existing bounded Session
and public Run grammars. Public `lifecycle_status` is only `active|terminated`.
`can_exit` is true exactly for the validated active family, an active owned
current character and an ended Session;
it is false for active play or termination. Status GET returns current authoritative
versions and never mutates. POST response uses the receipt's committed versions,
not current character/new-Run facts. Strict transport rejects duplicate members,
duplicate relevant raw headers, BOM, non-UTF-8, extra/null/coerced fields and
query parameters; POST maximum is 1,024 bytes. GET rejects any body. OpenAPI
must advertise actual shapes and all runtime response statuses.

| Condition | HTTP / public code |
| --- | --- |
| Missing or foreign Session/controller association | 404 `SESSION_NOT_FOUND` |
| Positively established legacy or standalone Session | 409 `NATIVE_RUN_REQUIRED` |
| Malformed request/header/body/path | 422 `REQUEST_VALIDATION_FAILED` using the existing validation envelope |
| Valid new operation with wrong Run or Session version | 409 `RUN_EXIT_STALE` |
| Valid new operation but Session active, Run already terminal, or character not active | 409 `RUN_EXIT_NOT_AVAILABLE` |
| Same key with different intent | 409 `IDEMPOTENCY_CONFLICT` |
| Corrupt/cross-bound stored family or ending evidence | 409 `SNAPSHOT_INVALID`, same opaque treatment as View |
| Exit service unavailable, including Dynamic Demo | 503 `RUN_EXIT_NOT_AVAILABLE` |
| Commit result cannot be determined | 503 `RUN_EXIT_OUTCOME_UNKNOWN` |

Known contention that cannot produce a validated replay returns 409
`RUN_EXIT_CONFLICT`; unexpected failures use the existing generic 500 envelope,
never a fabricated known decision. No line ID, operation ID/key, fingerprint,
snapshot hash, controller binding, private ending predicate or SQL is projected.
Precondition precedence for new requests is ownership/family/integrity, existing
receipt replay/conflict, terminal/eligibility, then version comparison and ending
eligibility. Thus a different key after termination is unavailable, not stale.

Keep `public-run-context/v1` immutable and unchanged: lifecycle is not a field
of admission settings. Existing View DTO shape is unchanged. Historical native
View reads use the terminated family's admission component for `run_context`
and the actual ended snapshot for gameplay. Confirmed Session/scenario/content/
complete native-context checks remain intact in `assertViewAssociation`.
The status response must additionally match the currently loaded Session, Run
ID and Session version before it can enable exit; mismatch locks the control
and requests a fresh View. A newer Run status can change only lifecycle UI.

Web retains the exact exit path/body/key in memory before dispatch, with the
existing operation-generation ownership discipline. Uncertain send/malformed
success/network/5xx retains that attempt; only explicit same-byte retry may POST.
Safe GET reconciliation can show the authoritative terminal state even if the
response was lost, without claiming which competing operation committed it.
Cancel after dispatch only stops waiting; it cannot cancel server authority.
Late responses after client replacement/unmount/Session change cannot change
storage, binding, lifecycle or UI. No automatic retry or replacement mutation.

Reload keeps the current version-1 storage allowlist `{version, session_id,
client_request_id?}`. First recover View through existing rules, then GET status
for a native ended View; do not store the exit key, Run context, lifecycle or a
second recovery record. Pending exit key loss on reload prevents exact retry of
that lost attempt; GET status still recovers whether the Run is terminal. If it
remains active, a new explicit confirmation may submit a new key, whose guarded
transition cannot create a second termination. An uncertain old request may
still win first; the new request then returns unavailable and GET reconciles.

Storage removal failure on **返回设置** leaves the ended/terminated state visible
and blocks new admission until existing storage recovery succeeds. Retrying
clear is storage-only; it must not POST exit again. Native admission retains
storage-before-View and one explicit POST behavior. New admission/recovery must
not inherit old immutable settings across a genuine Session replacement.

## 8. Direct consumers, compatibility and content

The implementation must update these direct consumers as one coherent change:

- SQL and Demo complete Run reconstruction, per-revision validation and receipt
  decoding accept the exact fourth revision while retaining strict old shapes.
- Native classification exposes an explicit terminal family; absent markers
  never become legacy. Historical context reads and initial-admission replay
  explicitly extract the immutable admission component after validating the
  whole terminal family. Replay still validates current ownership and the
  original Session initialization evidence, including after a new admission.
- `NativeTurnMechanicsCoordinator.load` may return a validated terminal family
  for read/replay handling. `bind`/new mechanics must require active admission;
  it must not render or mutate a terminal Run. Existing committed action replay
  and request-status reads remain available from stored evidence, with no new
  mechanics/Provider call. New actions on ended Sessions retain existing ended
  rejection behavior. Do not reinterpret old native-turn `run_revision=3` bytes.
- Eligible-character discovery keeps current active-slot/lifecycle rules. After
  exit it can include the unchanged active character; after another admission
  it excludes it again. Old admission replay never steals that new binding.

Legacy Run-entry receipts/namespaces and standalone Session bytes remain exact.
No legacy termination or compatibility backfill is added. Dynamic Demo remains
legacy-only; deterministic Demo stages/publishes the new revision/receipt/current
state atomically using its existing process store and native UoW capability.
Rollback publishes nothing; restart still discards process-local authority and
produces missing-Session recovery, not durable Run recovery.

No authored fiction or world-selection algorithm is required for S7-1. Both
existing catalog-valid ending classes permit the explicit exit; do not branch
on `death_certificate`, its ending names or free text. Use a non-hospital fixture
to prove this. Production content and profile/mechanics catalogues remain exact.
Determinism here is canonical request/receipt identity and one guarded transition;
there is no weighted draw, seed consumption, cooldown, reward or progression rule.

## 9. Concrete future implementation inventory

The following dependency-derived inventory is the bounded implementation scope,
not a numerical path budget. New files are marked **new**. Any necessary addition
outside it requires a demonstrated dependency and bounded plan reassessment;
unrelated refactors or edits to published plans are prohibited.

| Files | Necessary responsibility |
| --- | --- |
| `src/deviation_protocol/domain/run.py`, `domain/run_protocol_binding.py` | One terminal successor/mutation and explicit terminal native carrier; preserve strict admission and legacy models. Paths in this table without a full prefix are relative to `src/deviation_protocol/`. |
| `application/run_operations.py`, **new** `application/run_exit_service.py`, `application/ports.py` | Closed canonical command/evidence/receipt union, one exit/status service and only necessary typed ports. |
| `infrastructure/run_persistence.py`, `infrastructure/run_protocol_binding_persistence.py`, `infrastructure/repositories.py`, `infrastructure/orm_models.py` | Full history validation, terminal evidence codec, staging/CAS/receipt and the three constraint amendments. |
| **new** `alembic/versions/20260917_0008_native_run_exit.py` | Guarded additive constraint migration and fail-closed downgrade; repository-root path. |
| `application/native_run_admission.py`, `application/native_turn_mechanics.py`, `application/public_run_protocol.py` | Admission replay, historical View context and terminal action/replay separation. |
| `application/session_service.py`, `application/turn_orchestrator.py`, `application/narrative_turn_orchestrator.py` | Only direct native-family read/replay/ended guards where consumed; no new turn algorithm or Provider path. Omit paths needing no edit and record that fact. Dynamic Narrative has no direct native coordinator dependency and remains unchanged. |
| **new** `api/run_exit_routes.py`, `api/schemas.py`, `api/main.py`, `api/dependencies.py`, `api/demo_composition.py` | Strict routes/OpenAPI/error DTOs, normal production composition and deterministic Demo parity. |
| `infrastructure/demo_persistence.py` | Existing pending/trial/commit/rollback maps and full classifiers handle the terminal extension. Reuse `infrastructure/unit_of_work.py` unchanged; if factory typing requires an edit, limit it to exposing the existing pinned factory to exit, not changing lock/disposal behavior. |
| `web/src/api/schemas.ts`, `web/src/api/client.ts`, **new** `web/src/runExit.ts`, `web/src/App.tsx` | Closed status/exit client, bounded attempt helper, explicit terminal controls and generation-safe recovery; repository-root paths. No general App refactor. |
| `tests/unit/test_run.py`, `test_run_operations.py`, `test_run_persistence.py`, `test_run_protocol_binding.py`, `test_run_protocol_binding_persistence.py`, `test_run_repositories.py`, **new** `test_run_exit_service.py`, **new** `test_run_exit_api.py` | Domain/codec/authority/transport/rollback cases. Unprefixed test names in this row are under `tests/unit/`. |
| `tests/unit/test_native_run_admission.py`, `test_native_turn_mechanics.py`, `test_public_run_protocol.py`, `test_native_demo.py`, `test_demo_persistence.py`, `test_run_composition.py` | Direct-consumer compatibility and normal service graph; remaining names under `tests/unit/`. |
| **new** `tests/integration/test_mysql_native_run_exit.py`, **new** `tests/integration/test_mysql_native_run_exit_migration.py`, `tests/e2e/test_native_demo_playthrough.py` | Real MySQL persistence/race/migration and deterministic playable journey. Existing schema/head expectation owners `tests/integration/test_mysql_player_character.py`, `test_mysql_run.py`, `test_mysql_run_protocol_binding.py` may change only current-head inventory assertions where demonstrably necessary; historical migration assertions remain fixed. |
| `web/src/api/client.test.ts`, **new** `web/src/runExit.test.ts`, `web/src/App.test.tsx`, `web/src/App.recovery.test.tsx`, `web/src/App.action-loop.test.tsx` | Exit/recovery, explicit reselection and retained S6 regressions. Existing storage tests run unchanged. |
| `PLANS.md`, `docs/run_protocol.md`, `docs/architecture.md`, `docs/public_client_contract.md` | Implemented behavior/evidence/status only after implementation; this plan then remains frozen. Findings register changes only if actual reassessment evidence warrants them. |

## 10. Executable acceptance for the implementation

These are future verification requirements, not claims of tests run during
planning. Every mutation needs its negative/rollback counterpart. Named cases
are independently identifiable; overlapping suite counts must not be summed.

| Case | Required executable proof |
| --- | --- |
| E01 — public playable repeat | Through production ASGI with real repositories on `deviation_protocol_test`: create/select owned character, native admit once, play authoritative actions to a valid ending, GET status, explicitly exit, GET ended View/status, discover same character, explicitly admit a second Run and perform its first action. Assert distinct Run/line/Session, unchanged old ending/history/protocol and same character identity/current eligibility rules. No private ending issuer or direct snapshot mutation substitutes for this journey. |
| E02 — outcome and content boundaries | Repeat terminal decision for both authored `RESOLVED` and `FAILED`; a non-hospital valid fixture; ACTIVE, malformed/missing ending, incomplete memory, wrong scenario/content, wrong Session/Run and forged controller. Verify exact error and zero writes/Provider calls. FAILED never changes canonical character lifecycle. |
| E03 — exact family and corruption | Reconstruct active and terminated histories in SQL and Demo; separately corrupt each immutable association, version, time, receipt field, terminal marker, uniqueness slot and ending evidence. Reject partial terminal/legacy masquerade; assert all original revisions and bindings byte-identical. Canonical operation/evidence golden bytes and hashes have independent expected values. |
| E04 — replay after progression | Same-key exit replay before/after second admission, changed-body conflict, new-key terminal rejection, old native admission replay and committed action/status replay. Assert exact original responses, no new versions/identities/rows/rendering and no effect on the second Run's binding. |
| E05 — races | Independent real-MySQL connections: same-key and different-key exits, exit versus new admission/retirement/final turn. Prove actual lock waiting/serialization and committed outcomes, not scheduler timing alone. One terminal revision/receipt, no dual active binding, no history loss or deadlock caused by the new lock order. |
| E06 — failures/cancellation | Faults after revision append, CAS, receipt stage and before commit roll back all state. Commit-unknown and cleanup failure keep explicit uncertainty; safe GET or explicit exact retry resolves it. Preserve original failures/cancellation and connection disposal, with no fallback mutation. Demo trial publication has equivalent atomicity. |
| E07 — migration | Fresh upgrade, populated old legacy/native rows unchanged, metadata/head/history equality, schema constraint rejection, no-terminal downgrade with old rows preserved, terminal/partial evidence refusal before any DDL, old-snapshot current-read probe and compliant writer/downgrade serialization. Inject connection loss and failure at each changed-constraint DDL boundary and release/disposal boundary; record actual partial-DDL state and restore test schema deliberately. No SQLite substitute. |
| E08 — rendered Web | Ended native only, explicit confirmation/cancel, duplicate click lock, one exit POST; response lost after commit -> GET-only reconciliation; exact manual retry; reload/client replacement/unmount with late completion; malformed/mismatched status; storage-clear failure and storage-only retry; explicit new character/profile/world selection and no admission before confirmation. Preserve all S6 context/scenario/content association, same-Session read, genuine replacement, delayed character selection and explicit creation regressions unchanged. |
| E09 — projection and parity | Strict DTO/OpenAPI/error/key-and-value privacy scans; no lifecycle change to immutable `run_context`; old routes/schemas unchanged; legacy/standalone absence behavior; deterministic Demo one-commit/no external fallback and restarted-store 404; Dynamic Demo unavailable. |

Run focused new cases and affected Run/classifier/admission/Session/turn/API/Demo/
character suites first. Use installed dependencies and repository sanitized
verification workflow: `scripts/verify.ps1 -Mode Offline` for offline coverage;
project `.venv` Python for focused pytest and compileall; designated MySQL mode
and focused suites only after separate implementation-task authorization for
database access, with exact `mysql+asyncmy` / `deviation_protocol_test` preflight.
Real-MySQL E01/E05/E07 cannot be replaced by mocks or deferred as optional.
Inspect Alembic heads/history and metadata through the same approved environment.

The focused new-suite commands, inside those appropriately sanitized/authorized
child environments, are:

```powershell
# Repository root; future implementation verification only.
.\.venv\Scripts\python.exe -m pytest tests/unit/test_run_exit_service.py tests/unit/test_run_exit_api.py -q
.\.venv\Scripts\python.exe -m pytest tests/integration/test_mysql_native_run_exit.py tests/integration/test_mysql_native_run_exit_migration.py -q
.\.venv\Scripts\python.exe -m pytest tests/e2e/test_native_demo_playthrough.py -q
.\.venv\Scripts\python.exe -m compileall -q src tests alembic
# web/ working directory in a sanitized child; deterministic-demo disables dotenv.
npm.cmd run test:run -- src/runExit.test.ts src/api/client.test.ts src/App.test.tsx src/App.recovery.test.tsx src/App.action-loop.test.tsx src/sessionRecovery.test.ts --mode deterministic-demo
npm.cmd run test:run -- --mode deterministic-demo
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build -- --mode deterministic-demo
```

Run affected Web suites, then the complete Web suite once after stabilization,
plus typecheck/lint/build through sanitized repository workflow. Preserve native
diagnostics, source identities, command arguments and exit codes externally.
Broaden only for demonstrated shared impact or applicable workflow requirements;
reuse unchanged exhaustive S2/mechanics/Provider evidence with explicit source
applicability, never as fresh counts. No real Provider/network installation is
needed. Browser acceptance requires separate authorization and does not replace
deterministic contract/transaction evidence. It is not authorized by this plan task.

## 11. Decisions deferred without blocking S7-1

No unresolved product decision blocks the explicit post-ending exit proposed
here: this review must substantively accept or reject its controller-confirmed
`terminated` semantics. This is proposed authority, not an already implemented
permission. Normal `completed` criteria, mid-play exit and canonical death/
retirement integration remain unavailable.

S7-2 is genuinely blocked on an authored next playable destination and its
eligibility/progression relationship to the ended entry world, including whether
each supported ending can continue. The product/content owner must supply that
bounded authority before the S7-2 implementation plan can freeze a selector.
No current content proves it. The same plan must specify persistent world facts,
visit/region identity and mechanics compatibility before allowing continuation.
Rewards, numeric progression, importance and cooldowns await their owning later
plan and content; this allocation selects none. Important-NPC priority is
unavailable until separately published identity/world predicates exist and must
not block other authorized selection or pull Phase 3.4/6 into S7.

DF-001 retains its existing deferred disposition. DF-002 records only the observed
startup-race discovery recovery issue, contained by explicit reload. Reassess it
at S7-1's return-to-setup acceptance (E08/E09), or earlier if exposure expands;
if reload no longer restores the required flow, it becomes a blocker under the
existing policy. It is not silently included as a code fix in this subdivision.

## 12. Documentation scope, review binding and handoff

This documentation candidate contains exactly six paths:

| Document | Owned change |
| --- | --- |
| `docs/phase_3_3_s7_1_post_ending_run_exit_plan.md` (new) | Dependency allocation, complete S7-1 contract, acceptance and review authority. |
| `PLANS.md` | Current S6 publication/readiness and next S7-1 plan status; Phase 3.3 remains incomplete. |
| `docs/run_protocol.md` | Current lifecycle boundary, preserved review history, S6 publication and bounded browser evidence; link proposed S7-1 without claiming implementation. |
| `docs/architecture.md` | Replace stale S6 candidate status with actual publication and distinguish S7-1 proposal from current architecture. |
| `docs/public_client_contract.md` | Current S6 publication/evidence status; new exit routes remain only proposed in this plan. |
| `docs/engineering/deferred_findings.md` | New DF-002 with evidence, containment, role and reassessment; DF-001 unchanged. |

Frozen parent/S1–S6 plans, product specifications, Demo specification, guardrails,
workflow, source, tests, migrations and dependencies remain byte-identical.
The Demo browser report is external evidence, not a change to the frozen Phase
3.2 acceptance plan. No separate S6 closeout task or decomposition approval is due.

After final edits, freeze an external manifest binding the exact baseline/ref
topology, six-path inventory, per-file line/byte/SHA-256 and Git blob/mode
identities, plus a canonical path-ordered complete binary/full-index patch that
includes the new file. Include documentation/reference/status/scope/UTF-8/LF/
whitespace checks and final Git state. Do not put the candidate's own hash in an
approval-bound document. Candidate changes invalidate its measurements and any
prior exact-byte review. Relevant baseline changes follow the workflow's
pending-plan invalidation rule; do not carry stale hashes into a later review.

The one operative success token for independent review of this whole candidate is:

`PHASE_3_3_S7_1_POST_ENDING_RUN_EXIT_PLAN_INDEPENDENT_REVIEW_APPROVED`

Either disposition `APPROVED` or `APPROVED_WITH_DEFERRED_FINDINGS` must emit that
same token and bind the exact manifest/patch, technical contract, documentation
and findings disposition. `CHANGES_REQUIRED` is not approval. Historical S6 or
parent approvals and authoring-complete labels cannot satisfy this gate.

The sole **dormant**, non-operative implementation-review token is:

`PHASE_3_3_S7_1_POST_ENDING_RUN_EXIT_IMPLEMENTATION_INDEPENDENT_REVIEW_APPROVED`

It becomes usable only for a separately authorized implementation after this
plan's exact approved bytes are separately authorized for local commit, manually
published by the user and confirmed at a clean aligned implementation baseline.
Both successful dispositions must then bind the full implementation candidate
and required E01–E09 evidence. Plan approval alone authorizes no implementation,
runtime verification, browser, database, Provider, staging, commit or push.
There is no extra post-commit audit stage.

Next action: **one substantive independent read-only review of this plan
candidate**, including the allocation and proposed terminal semantics. No
implementation or Git write is currently authorized.

## Guardrail impact

None. Existing DB-001/002, AUTH-001/002, STATE-001, API-001, SCENE-001,
MODEL-001/002 and PLAY-001 govern the proposed change. DF-002 is a bounded
observed UI recovery defect, not a new reusable rule or a workflow failure.
