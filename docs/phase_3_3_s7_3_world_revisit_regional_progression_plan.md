# P3.3-S7-3 — Important-world revisit and regional progression

Status: **Documentation plan candidate; awaiting one substantive independent
plan review and explicit user approval of P01–P09. Not implementation authority.**
All S7-3 rules below are proposed for freeze. S7-2 P01–P08 approval does not
approve these choices. S7 and Phase 3.3 remain incomplete.

## 1. Baseline, authority and predecessor evidence

Verified without fetch/pull on 2026-09-18: branch `main`; HEAD/local main/local
origin/main all `6dfbd37d127386b589a1e6c0c43b831aefd70279`, subject
`feat(run): implement P3.3-S7-2 same-line world continuation`, parent
`2c272487a2f12c60c28ada95dd9a3f1edf1d42ba`; ahead/behind 0/0; initially clean
worktree, empty index, no conflicts, Git operations or locks. The published
implementation is the planning base, not a still-unstaged S7-2 candidate.

The [parent plan](phase_3_3_run_protocol_implementation_plan.md),
[S7 allocation](phase_3_3_s7_1_post_ending_run_exit_plan.md#2-remaining-s7-allocation-in-dependency-order),
[published S7-2 plan](phase_3_3_s7_2_same_line_world_continuation_plan.md),
[Run product authority](run_protocol.md), [architecture](architecture.md),
[public client contract](public_client_contract.md) and
[workflow](engineering/codex_workflow.md) control their respective boundaries.
Frozen candidate-time wording and historical review findings remain history;
this candidate changes none of those frozen files.

The actual external `browser-acceptance-report.md` and `request-evidence.json`
under `C:/Users/dylanmonster/AppData/Local/Temp/deviation-s7-2-browser-20260918`
were inspected. They agree with the user's reported two completed public-page
journeys: RESOLVED after 19 source actions, composure 6/6 and destination clock
0/40; FAILED after 10 source actions, composure 4/6 and destination clock 4/40.
Both reached destination hold ending, explicit exit, separately confirmed
same-character admission and its first action, with arrival/action/reload and
history/return checks. Request records contain 44 explicit POSTs, zero writes
in cancellation/history windows, and six GETs/zero writes after restart,
including both old-Session 404s. These are inspected prior artifacts, not fresh
browser execution in this planning task. Report hashes and limits are recorded
in [current evidence](run_protocol.md#s7-2-publication-and-local-browser-evidence).

The report records DF-001 containment passing, DF-002 reproduced with effective
full-page reload containment, service/tab cleanup, released ports and unchanged
301-file/Git identity inventory. Its inventory is the report's own scope; this
planning preflight independently inventories all 303 tracked paths. Browser
storage calls, request bodies/keys, private line/root identities and atomicity
were not directly monitored. Do not promote those omissions to passes or infer
production readiness. No independent approval verdict is fabricated from a Git
commit or browser report; prior substantive review records retain their own scope.

## 2. Smallest meaningful journey and discovered dependencies

Recommended journey: play the original world -> continue into **未送达的回执**
under unchanged S7-2 rules -> genuinely choose **会签暂缓** -> explicitly accept
the engine's sole eligible regional return -> enter **核验档案室** as visit three
of the same Run and a second visit to `world.undelivered_receipt@1` -> see that
the prior hold remains effective and delivery remains unproven -> inspect the
archival discrepancy -> choose whether to seal its unresolved status -> reload,
read visits two and one, return to visit three -> explicitly exit -> separately
confirm a fresh admission with the same still-eligible character.

This uses two worlds, three Sessions/visits and a new region, not a third world
or another copy of the dispatch-hall scenario. The first milestone includes
new action, visible consequence and successor-only reload; delivery also requires
both new endings, exit and fresh admission. Zero rewards are deliberate: the
benefit is access to a new region and a new public consequence in the same world.

| Term | Exact distinction |
| --- | --- |
| Read old Session | GET of an immutable ended visit; no entry, progression, eligibility consumption or storage replacement. |
| Continue current play | Ordinary action in the current active Session; no new participation or Run revision. |
| Revisit | Create a distinct visit/Session in an already visited world, using its retained state and provenance. |
| Enter another region | Change authored region scope within that same world through the proposed visit-three transition; old region remains intact. No free movement API. |
| Fresh Run | Separate explicit admission after termination; new Run/line, no inherited progression or claim of continuity. |

Read-only inspection found these concrete dependencies:

| Implemented owner | Change required; preservation boundary |
| --- | --- |
| `domain/world_continuation.py` | v1 selection rejects visited worlds; roots map exactly two packs; visits allow ordinals 1/2, joins 3/4; position is exactly 4. Add separate closed evidence, not permissive v1 parsing. |
| `domain/run.py`, `domain/run_protocol_binding.py`, `infrastructure/run_persistence.py` | Current closed families are admission 3, terminated 3→4, continued active 3→4, continued terminal 4→5. Revision 5 alone cannot classify the new active family. |
| `infrastructure/repositories.py`, `demo_persistence.py`, `world_continuation_persistence.py` | Count/reverse-association checks assume two roots, two visits, one position and the second Session. Reconstruct the old prefix plus an explicit new suffix. |
| `application/session_content_registry.py` | Destination bytes are independently pinned and required at composition. Add one independently pinned regional bundle; preserve both existing identities and the original CRLF pin policy. |
| `application/session_service.py` | Continuation initialization is hard-coded to the second pack. Add a separate sealed regional initializer; do not weaken one-runtime memory validation. |
| `application/native_turn_mechanics.py`, `world_visit_context.py` | New visit envelope fixes revision 4/ordinal 2; prompt attachment and arrival are second-world specific. New visit-three envelopes/compilation are required. |
| `application/run_exit_service.py`, `native_run_admission.py`, character-binding readers | Current/historical classification is consumed beyond continuation. Extend exact recognized families and replay while retaining the immutable character reference. |
| `web/src/runContinuation.ts`, `App.tsx`, API schemas | v1 assumes predecessor one/successor two. Add explicit journey projection and complete association checking across three visits, retaining current recovery separately from display. |
| Migration 009 and ORM | Visit/position CHECKs allow only old bounds. A new migration and immutable initial entry evidence are necessary; changing Python alone cannot work. |

Source prefixes `domain/`, `application/`, `infrastructure/`, `api/` in this
plan mean `src/deviation_protocol/`. All listed paths in section 10 are concrete
future dependencies; this task edits documentation only.

## 3. Product decisions presented for approval together

There is an explicit authority tension: the existing **Important-world revisits**
product paragraph says players cannot approve/veto an engine-proposed revisit.
The current request asks for an explicit choice. P02 proposes a narrow amendment,
not an interpretation that the old prohibition already allowed confirmation.
Until explicitly approved, that amendment has no effect. Engine eligibility and
destination selection remain exclusive authority; the player chooses whether to
continue this journey, not which world to generate or unlock.

| ID | Exact proposed rule/value | Gameplay consequence | Recommendation and reason | Approval status |
| --- | --- | --- | --- | --- |
| P01 | Mark only `world.undelivered_receipt@1` important in `regional-revisit/v1`; revisit once in new `region.undelivered_receipt.verification_archive@1`, title 核验档案室. | Return to a world whose unresolved receipt the player has just affected; no third world or hospital replay. | Recommend: smallest authored consequence that satisfies important-world return and region progression. | PROPOSED |
| P02 | The engine offers exactly one eligible route; player explicitly confirms “进入核验档案室” or cancels before POST. Replace the old no-approve/no-veto rule only for consenting to this engine-selected journey transition. No destination input, free travel, reroll or alternative candidate. | Cancel leaves the ended visit and entitlement intact; exit remains a separate choice. | Recommend: fulfills this request's confirmation flow without granting selection authority. | PROPOSED |
| P03 | Source must be current ended visit two, exact `undelivered_receipt.ending.receipt_held` / RESOLVED, completed memory and true `dispatch_held`; Run active at 4, same active owned character. `dispatch_closed` and `deadline_reached` / FAILED are ineligible. First-world RESOLVED or FAILED provenance remains valid unchanged. | Successfully preventing dispatch opens verification; releasing/missing the deadline offers history/exit only. | Recommend: actual authored consequence, not ending-class-only authorization. | PROPOSED |
| P04 | Retain every prior local state and prior hold. New archive facts: hold remains effective; delivery remains unproven; the archive can seal an unresolved entry but cannot invent delivery. OBSERVE discrepancy then CHOOSE seal or defer. | Previous success changes access and the visible opening; the new choice records what remains unresolved. | Recommend: meaningful progression without undoing facts or inventing NPC continuity. | PROPOSED |
| P05 | Region unlock is a monotonic predicate of the validated visit-two hold ending/event/memory. It persists for this Run; one committed visit-three receipt consumes its single entry opportunity. Unlock and availability differ. No separate grant-on-GET writer. | Reload/history cannot unlock twice; entering does not revoke the fact that the region was unlocked. | Recommend: existing durable ending plus transition receipt is sufficient provenance. | PROPOSED |
| P06 | Carry full current PlayerState from visit two, including zero composure and all item instances, wallet, skills and cooldown values. No refill, reward, fee, item grant, attribute change or character revision. Archive has no threat clock; old dispatch clock remains frozen at its actual ended value in the retained region. Fresh local archive runtime/event numbering/memory only. | The hold has stopped this dispatch's time pressure; investigating still pays existing narrative composure costs. Old clocks are neither reset nor reused as a new budget. | Recommend: no reward economy or unrelated timer machinery; preserves S5 formulas. | PROPOSED |
| P07 | Cooldown unit is intervening completed visits to another world; threshold exactly 0 for this one newly unlocked region. At most one return, ordinal exactly 3; no replayable regional entry after consumption and no same-region revisit. | Can proceed immediately after hold; waiting, refreshing, turns or changing keys never restore eligibility. | Recommend: deterministic persisted bound; no wall clock or artificial detour. | PROPOSED |
| P08 | Required eligible edge has priority 0 and weight 1; it alone bypasses visited-world exclusion. No random draw, generic repeat exception, hidden-NPC priority or unresolved future predicate. Progress benefit is region access only, awarded once by the same transition. | Required progression is never stranded by randomness; no harvestable resources or items exist. | Recommend: closes anti-farming with one receipt/visit, not an invented reward ledger. | PROPOSED |
| P09 | Archive endings: RESOLVED `receipt_archive.ending.unresolved_sealed` (封存待核记录), priority 10; FAILED `receipt_archive.ending.review_deferred` (核验暂置), priority 20. Both permit explicit Run termination 5→6. No fourth visit, retrying archive, third world or normal `completed`. | Either decision ends this visit; history remains, and a fresh Run requires a separate confirmation after exit. | Recommend: complete bounded loop; S7-4 retains normal completion. | PROPOSED |

If a decision changes, update all dependent contracts/evidence and rebind the
candidate. Do not start implementation on inherited S7-2 approval or substitute
an unreviewed choice. No extra approval stage beyond the existing product
decision and single independent plan review convention is introduced.

## 4. Authored content and persistent world semantics

Add `config/scenarios/receipt_archive_v1.json`: scenario `receipt_archive`, pack
`receipt-archive-1.0.0`, displayed scenario title **未送达的回执：核验档案室**.
It belongs to existing `world.undelivered_receipt@1`, not a new world version.
An authored world identity can contain independently versioned regional packs;
the existing root's scenario/version continues to describe its first region.
Never replace that root's pack, repin an old digest or merge packs under v1.
The registry's trusted catalogue gains the exact new identity and a literal
SHA-256 derived once from final approved authored UTF-8/LF bytes at implementation.
There is no placeholder digest accepted at runtime. Record independent expected
bytes/digest and deployment byte-policy tests before enabling the bundle.
Reject missing required pack, same-version schema-valid mutation, wrong world/
region/scenario mapping, incompatible definitions or hash/version/configuration
mismatch. Existing destination pin remains
`74af55faf2eca0dd826be1f025272d070c23a2000383183e886ec823f495582c`.

The new pack copies required mechanical character/resource/item definitions
byte-equivalently for validation only; it grants no instances or learned skills.
It is continuation-only and absent from public initial entry/scenario choices.
Existing `death-certificate-1.1.0` and `undelivered-receipt-1.0.0` remain required,
unchanged, separately routed for all old reads/actions/jobs/receipts.

Authored minimum, proposed by P04/P09:

1. One location `receipt_archive.audit_desk`; no NPCs. Phases `.arrival`,
   `.decision`, `.resolution`. Fixed public facts `.hold_effective=true`,
   `.delivery_unproven=true`; mutable `.unresolved_sealed=false`.
   The first two facts are *certified regional observations* from the validated
   held-source evidence and the old public fact that a hold proves no delivery;
   their initializer has no public input and cannot run without that evidence.
2. Initial arrival notice: **“会签暂缓仍然有效，送达仍未得到证明。你进入核验档案室，决定如何保留这项待核记录；原有资源不会恢复。”**
   Show the actual previous public hold ending class/title separately. Never
   infer a first-world resurrection or copy private history into this notice.
3. OBSERVE at the audit desk yields declared SUCCESS, discovers
   `receipt_archive.clue.unresolved_entry`, and opens the bound decision.
   No clock component is declared. Existing narrative resource pressure applies
   with saturation; no NPC/social charge and no fabricated clock when none exists.
   Wrong/irrelevant CUSTOM uses declared NO_EFFECT with no clue/phase advance;
   it can consume composure but cannot unlock/grant anything. No text matching
   authorizes a clue. All existing gateway/local mechanics remain authoritative.
4. CHOOSE `receipt_archive.action.seal` or `.defer` requires that clue. Seal emits
   trusted `receipt_archive.record.sealed`, changes only the local mutable fact
   and reaches P09 RESOLVED. Defer emits `receipt_archive.review.deferred`,
   leaves the fact false and reaches P09 FAILED. Both local choices have zero
   cost and ordinary DB-002 ending/memory atomicity. No auto ending on arrival.
   Ascending `(priority, ending_id)` is unchanged: seal wins a synthetic
   both-events condition; real play can commit only one choice. Reversed
   definition-order tests are selector tests, not public reachability proof.

Persistent state is a Run-owned ordered composition of immutable initial roots
and the latest validated snapshot of each participating region/visit. At the
first continuation the two existing roots remain exactly S7-2 v1. While visit
two plays, its authoritative dispatch state is its latest snapshot, not its
initial root. At regional entry consume its **ended latest snapshot** and freeze
that source binding in the new entry evidence. Do not initialize from world
two's version-zero root, the latest character definition, browser state or a
default PlayerState. The immutable dispatch snapshot, including NPC state,
facts, clues, clock and unresolved events, stays retained and authoritative for
that region. Archive latest state adds only its own scoped consequences.

The archive initialization is a deterministic projection of that exact retained
world base plus a detached copy of its current PlayerState, not a blank copy of
the old scenario. Validate `.dispatch_held`, actual ending event/completed memory
and old fixed facts before issuing the initializer. Its public observations are
bounded; all other old state stays available through validated world state and
history without being copied into archive runtime/memory. Never merge old
memory records into a runtime that cannot validate them. Local archive memory
starts from its own ScenarioStarted event and approved public facts. Old NPC
instances stay with their source Session, inaccessible to new actions/prompts;
there is no matching by name/template and no NPC identity/canon transition.

After visit three advances, current player authority is its latest PlayerState,
while dispatch-local authority remains the ended visit-two state. After archive
ending, its latest snapshot is immutable too. A history read never becomes a
new source of current player state. No read repair or second mutable copy of
world facts exists. Unlock is derived from sealed history; `consumed` is derived
from the new successful receipt/visit. They are not independent mutable flags.

## 5. Exact families, evidence and reconstruction

Keep original admission at 3; S7-1 terminal 3→4; S7-2 active 3→4 and terminal
4→5 exactly valid. Their old carriers, namespaces, fingerprints, counts and
receipts are not widened or reinterpreted. Only these new closed families exist:

| New family | Exact sequence and current authority |
| --- | --- |
| `NativeRunRegionalRevisitV1` | Valid S7-2 continued prefix; revisions 1..5; mutation `REVISIT_NATIVE_REGION` 4→5 active; three participations joined at 3,4,5; two unchanged world roots; three visits; one new entry row/receipt; position visit three/version 5. Same active character binding/slot and permanent line. |
| `NativeRunRegionalRevisitTerminatedV1` | That prefix plus `TERMINATE_REVISITED_NATIVE_RUN` 5→6 terminated; same three participations and last position at 5; one exit receipt; historical binding and NULL active-character slot. |

No arbitrary `>=3`, generic N-visit family, fourth participation, skipped
ordinal, terminal revival or normal completion. Ending a Session does not
increment Run revision. In particular old terminated revision 5 is not new
active revision 5. Original bindings stay bound at revision 3. Every new
revision preserves reference/provenance except the explicit exit's existing
binding-state/inactivation changes. Historical reads do not require that the
character still have the admitted current revision or a free active slot.

New `WorldVisitV2` uses exactly v1's stored fields but admits only ordinal 3,
world `world.undelivered_receipt@1`, archive region@1, joined/materialized
revision 5, entered_at=created_at=new transition time. New `WorldPositionV2`
uses exactly v1's fields, position version 5 and visit-three identity; retain
the position row's original creation time at revision 4. The update is a CAS
from exact version-4 visit-two position. The new receipt owns the movement time.
v1 visits/roots remain immutable and byte-equivalent; no backfill/discriminator
change to old rows. Dispatch stored visit parsing by validated family and exact
ordinal/join tuple, never by successful fallback parsing.

New visit ID = lowercase SHA-256 of canonical `{schema:"run.world-visit-id/v2",
run_id, continuous_story_line_id, session_id, joined_state_version:5}`.
Old v1 derivation remains only joins 3/4. New operation namespace
`run.revisit-native-region/v1`, result `run.revisit-native-region-result/v1`;
Run safe result is active revision 5, exact third participation, no character
result. Request has the exact S7-2 request field set, but schema
`run.revisit-native-region-request/v1`. Expected-version fields retain their
strict int64 transport domains; equality to Run version 4 is a new-operation
precondition, not a coercion or decoder default. Thus changed valid version
tokens still participate in request fingerprint/conflict and stale checks. Operation
identity uses `{schema:"run.revisit-native-region-operation/v1",
controller_binding,public_operation_key,run_id}`; creation request uses the same
inputs with schema `run.regional-session-create/v1`. Fingerprint is SHA-256 of
the full canonical request. The public body still supplies only two versions.

`run.revisit-native-region-evidence/v1` has exactly:

```text
schema, request, source_ending, selection_inputs, selection_seed,
source_visit_id, destination_visit_id, destination_session_id,
destination_creation_request_id, destination_initial_event_id,
destination_random_seed, world_base_snapshot_sha256,
destination_entry_sha256, carryover_rule, occurred_at
```

`source_ending` has exactly scenario_id, scenario_content_version, ending_id,
ending_status, session_state_version, snapshot_sha256; values must match P03.
`carryover_rule="carry-player-state/v1"`. Times are trusted UTC whole seconds
encoded with six fractional digits and `Z`, preserving Session precision rules.
New Session/event/seed issuers run only for a fresh eligible preparation after
receipt lookup, outside the final transaction; revalidation rejects a stale
preparation. No identity/time/render work on known exact replay.

Selection inputs have exactly `selector_version="regional-revisit/v1"`, run_id,
continuous_story_line_id, source_session_id, source_session_state_version,
source_snapshot_sha256, resolution_fingerprint, visits, eligible_pool.
`visits` is the ordered pair of closed objects `{visit_id,visit_ordinal,world,
region,session_id}`; world/region use existing two-field references. The pool
is empty or one exact object `{world,region,scenario_id,scenario_content_version,
content_sha256,required_priority:0,weight:1,cooldown_completed_visits:0}`.
Eligibility tests family/currentness/ending/unlock/consumption first; only then
may this important-world edge override anti-repeat. Sort by priority, ASCII world
ID, numeric world version, ASCII region ID, numeric region version; reject
duplicates or multiple candidates. No random draw. Seed = SHA-256 of
`b"deviation-protocol:regional-revisit-selection:v1\0" + canonical(inputs)`.
Changing time/key/new Session ID cannot change selection. Important-NPC predicate
is unavailable and absent from inputs. Missing required content is integrity
failure, not an empty pool. An ineligible intact ending has a genuinely empty
pool; GET never persists a seed or consumes an entry.

New immutable entry canonical has exactly `schema="run-regional-entry/v1"`,
run_id, continuous_story_line_id, visit_id, session_id, world, region, scenario_id,
scenario_content_version, content_sha256, base_visit_id, base_session_id,
base_session_state_version, base_snapshot_sha256, unlock_ending_id,
snapshot_state_version (0), snapshot, snapshot_sha256. The snapshot is the full
validated regional initial GameState including local initialized memory. Base
is the exact ended second visit; it remains available rather than being copied
as another raw snapshot. Digest binds canonical entry bytes, and new receipt
binds that digest. Reconstruction independently rebuilds initialization from
base plus authored rule even after the single latest snapshot advances.

Operation/selection/evidence encoding retains strict original-type/closed-field
validation then existing NFC canonical Run JSON; maximum 16,384 UTF-8 bytes.
Entry encoding uses existing snapshot JSON (sorted keys, compact separators,
ensure_ascii=False, no NaN), **without NFC**, bounded 1..1,048,576 bytes. Reject
duplicate/unknown/missing fields, BOM, bad UTF-8, float/bool coercion, unsupported
schemas, noncanonical bytes and actual-model tampering. IDs, Session IDs,
content versions and int64 bounds retain S7-2 limits; digest is 64 lowercase hex
in canonical data and BINARY(32) in SQL. Independent goldens must not derive
expected bytes from the production codec under test.

Exit namespace `run.terminate-revisited-native/v1`; result
`run.terminate-revisited-native-result/v1`; operation/request/evidence schema
domains use `run.terminate-revisited-native-{operation,request,evidence}/v1`.
Exact keys/4,096-byte ceiling are those of S7-1 exit, with versions 5→6 and
archive ending evidence. Decoder selection remains explicit by namespace;
old original/continued exits replay their own original result indefinitely.

### Complete reconstruction order and failure ownership

SQL and Demo perform the same ordered validation; do not inspect corrupt fields
for ordering or eligibility first. Follow existing S3/S7 prefix precedence:

1. Authorize path Session/controller; fetch Run target and reverse participation.
   Missing/foreign path is opaque 404. Once path authority exists, a referenced
   missing/crossed family member is corruption, not a missing-path fallback.
2. Load current/revisions/participations/creation/mutation records in existing
   order. Validate original scalars before ordering; load and validate immutable
   character revision before supplying it to complete Run reconstruction.
   Reject orphan rows even if Run current is absent; scan reverse associations
   by Run/line/Session/visit IDs for the new entry table too.
3. Decode exact family by revision/kind/namespace tuple; validate old admission
   prefix, both native bindings, owner and original initialization. Validate
   S7-2 receipt, both roots and first two visits using their strict v1 codecs.
   New suffix validation may reconstruct the **historical** position at revision
   4 from the original continuation receipt/destination visit/time; it must not
   pass the actual revision-5 position to v1 or claim that a second SQL position
   row exists. For old families the actual persisted position remains mandatory.
4. For new families require exactly two roots, three visits, one entry, one
   position, four mutation receipts (five if exited) and three participations.
   Validate visit-two sealed ending/latest snapshot, owner, content, committed
   `dispatch.held` scenario-event provenance, the matching ending event and
   completed memory. Require exact `undelivered_receipt.fact.dispatch_held=true`
   and unchanged `undelivered_receipt.fact.hold_is_not_delivery`; the runtime
   event references must resolve to that Session's persisted events. A snapshot
   Boolean alone is not unlock evidence. Recompute pool/seed/cooldown/unlock
   from validated history.
5. Validate third visit/entry/receipt hashes and all reciprocal Run/line/Session/
   world/region/operation joins, entry initial event and local initial memory.
   Rebuild entry from old latest state plus sealed initializer; compare complete
   initial PlayerState, imported observations and root snapshot, not just hashes.
6. Validate archive latest snapshot with its exact registry bundle; at version
   zero require complete equality to entry, otherwise preserve initial authority
   while allowing legitimate turns. Position must reference third participation;
   no older current pointer or extra unconsumed entry is tolerated. Validate
   terminal suffix if present against latest ended state, receipt/time and slot.
7. Only now allow replay comparison, safe projection, prompt detachment or new
   eligibility. All owned path visits fail consistently on corrupt full family.

Domain malformed carriers raise existing strict validation/ValueError; Run row
codecs own `RunStoredRecordIntegrityError`, native/world reconstruction owns
`RunProtocolBindingStoredIntegrityError`, Session loading retains its existing
snapshot exceptions. Application/API maps those known failures to opaque 409
`SNAPSHOT_INVALID`; unrelated programming failures remain opaque 500. Registry
construction fails composition before service exposure on required pack failure;
late stored content mismatch is a reconstruction error. Never catch arbitrary
exceptions to classify legacy, repair state, omit a neighbor or enable an action.

## 6. Transaction, replay and concurrent outcomes

One `RunRegionalRevisitService` owns one atomic final UoW/commit attempt. Ordinary
read/preparation can precede it; neither is a second mutation transaction. Shared
named lock remains `deviation_protocol:p33:s3:run_protocol_bindings:ddl_write:v1`
with timeout 30 and one pinned physical connection. Lock character first, then
Run current/history/participations/receipts and native bindings in existing order,
roots/visits/position/entry in deterministic key order and Sessions by visit
ordinal at the existing classifier Session-read boundary. Preserve current reads
for mutable finalization prerequisites and active jobs (DB-001); no reverse
Run write locks in turns or rendering under locks.

An owned initial read fully reconstructs and resolves scoped exact replay before
new eligibility, IDs, seed or initialization work. For a new operation prepare
the detached archive candidate, Frame and prompt outside transactions/locks.
Under the final UoW reauthorize and reconstruct, compare exact receipt first,
then active family/character/current source, expected Run/Session versions,
P03 ending/job settlement and preparation/base/content identity. New request on
terminal/history/consumed source is unavailable before stale-token comparison;
otherwise wrong expected versions is stale. An active/unsettled Session is
unavailable; an ended snapshot contradicted by a still-live job is stored
integrity failure, as in S7-2. Never cancel/finalize that job in the transition.

Stage archive Session, ScenarioStarted/event/local memory/snapshot, revision 5,
third participation, visit, immutable entry and successful receipt, plus Run
current CAS 4→5 and position CAS to visit three. Original roots and ended
Sessions remain untouched. The same receipt consumes the one allowed regional
entry/benefit, so there is no separate entitlement commit. Reconstruct the full
intended family before the sole commit. Return success only after commit and
ordinary cleanup. Explicit exit uses the same lock/ownership order and atomic
revision/current/receipt 5→6; it historicalizes only this Run's binding.

- Same key/intent: one commit, exact immutable initialization result replay,
  including after archive turns, exit or new admission. Same key/different intent:
  `IDEMPOTENCY_CONFLICT`; no eligibility bypass or extra Session.
- Different keys: one regional-entry winner, other unavailable; position and
  entry uniqueness protect consumption independently of keys. Exit versus return
  from visit two: exactly old 4→5 terminal **or** new 4→5 active, never both.
  Losing old-Session exit cannot terminate visit three. Admission/retirement
  preserve character-first serialization and active-binding rejection.
- Final turn may settle first; finalization must then revalidate and reject stale
  detached preparation, allowing explicit retry. An in-flight action cannot be
  mistaken for a completed visit. GET uses one consistent snapshot.
- Precommit exception/cancellation/CAS/known unique failure rolls back all staged
  rows and detached versions. Cancellation propagates; no second commit,
  compensation, retry loop or partial unlock/entry. Unknown SQL errors are not
  successful replay. Use existing supported constraint identification only.
- Commit acknowledgement loss, cancellation during commit, or cleanup failure is
  outcome unknown. Retain exact request; safe GET or explicit exact retry resolves
  it. Do not promise rollback, replace the request or reconnect-and-continue.
  Preserve retained cleanup, pool detachment and failed physical-owner disposal.

## 7. Minimal persistence extension and migration

Propose `alembic/versions/20260918_0010_native_regional_revisit.py`, revision
`20260918_0010`, down_revision `20260918_0009` (actual source head). Earlier
migrations are protected byte-for-byte. No historical rows are rewritten.

One new table `run_world_visit_entries`, all columns NOT NULL:

| Columns | Type and constraints |
| --- | --- |
| run_id, continuous_story_line_id, visit_id | ASCII VARCHAR(128), ascii_bin; PK `(run_id,visit_id)` |
| session_id | Same VARCHAR(64)/collation as existing Session FK; unique |
| joined_state_version | BIGINT, exactly 5 |
| entry_schema | ASCII VARCHAR(64), exactly `run-regional-entry/v1` |
| entry_canonical | MEDIUMBLOB; OCTET_LENGTH 1..1,048,576 |
| entry_sha256 | BINARY(32), canonical digest |
| created_at | DATETIME(6) UTC, equal transition time |

Restrictive composite FK `(run_id,continuous_story_line_id,visit_id,session_id)`
to existing `uq_run_world_visits_exact`; restrictive FK `(run_id,
continuous_story_line_id,joined_state_version)` to Run revisions. Name unique
`uq_run_world_visit_entries_session`; FKs `fk_run_world_visit_entries_visit` and
`fk_run_world_visit_entries_revision`; CHECKs `ck_run_world_visit_entries_version`,
`ck_run_world_visit_entries_schema`, `ck_run_world_visit_entries_payload_size`.
All canonical duplicated columns and private base links are reverse-checked by
reconstruction. No reward ledger, mutable unlock flag or wall-clock column.

Change only these existing checks, mirrored in ORM:

- `ck_run_world_visits_versions`: preserve positive int64 world/region bounds;
  materialized version is 4 or 5. `ck_run_world_visits_ordinal_join`: require
  exactly `(ordinal,join,materialized)=(1,3,4)|(2,4,4)|(3,5,5)`. No arbitrary range.
- `ck_run_world_positions_versions`: exactly 4 or 5. World root checks remain
  unchanged at materialized revision 4; roots are still the original two.
- Existing three Run mutation/receipt matrix CHECKs: append exact new active
  prior/current 4/5 and terminal 5/6 branches, kinds/namespaces/result schemas
  from section 5. Active branch requires complete active immutable binding,
  non-NULL active slot equal to its character. Terminal requires historical
  binding, inactivation and NULL active slot. Guard every required nullable
  operand explicitly with IS NOT NULL. Receipt requires exact participation
  fields for revisit and NULL participation/character-result fields for exit.
  All old branches, FK/unique constraints and enforcement remain intact.

Both migration directions acquire the shared named lock/pinned owner before
preflight. Compare exact expected head, table/column/key/check/enforcement
definitions and absence of partial artifacts. Upgrade: replace the three Run
CHECKs in revision/current/receipt order, then visit versions, visit ordinal/join,
position versions, then create entries. Writers remain excluded throughout.
No schema-only wider family may become publicly readable until all checks pass.

Downgrade first performs **current locking probes** on entries, visits (ordinal
3/join or materialization 5), position (5), Run rows/receipts (either new kind,
namespace/schema or revision 6, and active revision 5), participations joined at
5 with native binding. Any complete, crossed or partial new evidence refuses
before the first DDL. Old S7-2 terminal revision 5 alone must not refuse.
Probe reverse evidence too; an empty entry table cannot justify dropping an
orphan new visit. If safe, drop entries, restore position, visit ordinal/join,
visit versions, then receipt/current/revision CHECKs to exact 009 definitions.
Unknown/partial schema refuses pending operator inspection; no row deletion.

MySQL DDL is statement-durable. At every ALTER/create/drop and post-statement
disconnect boundary stop, preserve actual prefix/remaining schema and dispose
unsafe physical owners. No rollback claim, reconnection, compensation or
automatic repair. Preserve acquisition/release outcomes and body-error precedence.
Fresh 010 fault tests must cover the new statements; unchanged internal 007–009
fault evidence is reusable only with explicit applicability checks. Deploying
anything is outside planning authorization; eventual runtime requires schema
010 and updated readers before enabling writers, without mixed old readers of
new families. Historical fixtures continue to name their real 005–009 heads.

## 8. Public contracts and recovery across three visits

Preserve `PlayerSessionView`, `public-run-context/v1`, storage v1 and all original
admission/exit result meanings. Add an explicit journey read for navigation;
do not widen the strict two-visit continuation DTO into arbitrary visits.

### Exact new public projection

`GET /v1/sessions/{session_id}/run-journey`, operation `get_native_run_journey`,
no body/query, returns 200 closed `native-run-journey/v1` with exactly:

```text
schema_version, session_id, run_id, run_state_version, lifecycle_status,
run_context, path, current, predecessor, successor, next_transition, arrival
```

`run_context` is the complete original admitted context. `path` and `current`
are required `VisitAssociation` objects with exactly `{session_id,
session_state_version,scenario_id,scenario_content_version,visit}`. `path`
matches the URL; `current` points to actual current position (first Session
before materialization), including after exit. `visit` is the existing six-field
object, extended in this **new** schema to exact supported ordinals 1/2/3 and
catalogue world/region pairs. It is null only for an unmaterialized first visit
(active 3 or old terminal 4). All materialized associations require it non-null.

`predecessor` and `successor` are required nullable VisitAssociations for the
path visit's immediate neighbors, regardless of current position. A first visit
has no predecessor; the latest has no successor. After revisit: 1↔2↔3, current
is 3 for all. Neighbor Session versions are their current versions at the same
read snapshot; predecessors are ended and immutable. Missing second/third-visit
evidence is 409, never null. No ordinal gaps, self-links, extra fourth visit or
crossed reciprocal association is accepted. Content version and all six visit
fields come from validated persisted authority, not received View inference.

`next_transition` is required nullable `{kind,world_title,region_title,notice}`,
with kind exactly `first_continuation|regional_revisit`. It is non-null only on
the eligible **path=current** ended Session: unchanged S7-2 source eligibility
for first_continuation; P03 for regional_revisit. Titles 1..120 characters;
notice 1..300. Kind does not let a client choose a destination or bypass checks.
Use original second-world title/region for first continuation and P01 titles
for regional return; regional notice is P04's authored notice. Empty pool is
null, not an error or automatic exit. Required bad content is an error.

`arrival` is required nullable `{previous_ending_status,previous_ending_title,
entry_notice}`, with S7-2 field bounds. It belongs to the **path** visit: null
for visit one; exact existing approved annotation for visit two; actual held
ending `RESOLVED` / `回执待核，发运暂缓` and section 4 notice for visit three.
All enum/title/notice combinations are closed catalogue values. Historical
display labels its own arrival/history; it never overlays visit-three arrival
on a previous View. No roots, hashes, seeds, private predicates, memory, line
ID, controller, operation key or generated summary enters the projection.

Existing strict ID grammars/lengths and signed int64 bounds apply, with Web
safe-integer enforcement. GET constructs all fields after owned complete
reconstruction in one ordinary read UoW/snapshot (Demo immutable snapshot).
No storage side effect, scan of unrelated Sessions or current character-slot
requirement for historical ownership. No partial projection on error.

### Mutation and compatibility

`POST /v1/sessions/{session_id}/run-revisit`, operation `revisit_native_region`,
requires Idempotency-Key and exactly `{expected_run_state_version,
expected_session_state_version}`. Strict 1,024-byte UTF-8 transport retains
duplicate-header/member/BOM/query/extra/null/coercion rejection from exit.
No destination or client unlock boolean. Success/replay 200 is closed
`native-run-revisit-result/v1` with the **same field names** as S7-2 continuation
result: source_session_id, source_session_state_version, run_id,
resulting_run_state_version (5), session_id, initial_session_state_version (0),
scenario_id (`receipt_archive`), scenario_content_version (`receipt-archive-1.0.0`),
run_context, visit (ordinal 3), plus schema_version. It is an immutable receipt
association, not a current View. No arrival prose in the receipt.

Old continuation POST remains the only first-world writer and replays its
original v1 result after visit three/exit/fresh admission by validating the
complete new family then extracting the original edge. For unchanged one/two-
visit families, old continuation GET is unchanged. On a new three-visit family
old continuation GET returns opaque 409 `RUN_CONTINUATION_NOT_AVAILABLE` after
ownership/integrity, not a misleading two-visit DTO or fabricated null. This is
an explicit new-family compatibility limit; the updated Web uses journey GET
for **all** native visits and never relies on old GET for history. Old clients
cannot navigate new families, and no mixed-version activation is promised.
Old Views, metadata, jobs, action/status receipts, admission/exit replay and
their content routing remain readable under complete reconstruction.

Run-status/exit DTO shape remains v1; recognize new active 5 and terminal 6.
Fresh exit requires current ended visit, active owned character and exact new
family. Old history never has can_exit=true. Terminal new result is revision 6;
earlier exit result remains its exact revision 4/5 even after a new Run.

| Ordered boundary | Response; mutation outcome |
| --- | --- |
| Malformed transport | 422 REQUEST_VALIDATION_FAILED; none |
| Unconfigured service/Dynamic composition | 503 RUN_REVISIT_NOT_AVAILABLE; none |
| Missing/foreign path/controller | 404 SESSION_NOT_FOUND; none/no disclosure |
| Proven legacy/standalone | 409 NATIVE_RUN_REQUIRED; none |
| Owned corruption/unknown schema/content mismatch | 409 SNAPSHOT_INVALID; none/no association |
| Scoped exact receipt / changed intent | 200 original result / 409 IDEMPOTENCY_CONFLICT; no new writes |
| Fresh terminal/history/consumed/inactive-character request | 409 RUN_REVISIT_NOT_AVAILABLE; none |
| Otherwise stale Run/Session versions | 409 RUN_REVISIT_STALE; none |
| Active/unsettled source or valid ineligible ending | 409 RUN_REVISIT_NOT_AVAILABLE; none |
| Known lock/CAS/unique contention | 409 RUN_REVISIT_CONFLICT; rolled back |
| Commit/cleanup uncertainty | 503 RUN_REVISIT_OUTCOME_UNKNOWN; durability unknown, no automatic retry |
| Other unexpected error | Opaque 500; no fabricated known outcome |

Journey GET returns 200 with nullable next_transition for valid native states;
uses the shared 404/409/422/500/503 branches above, never mutation conflicts.
Explicitly declare all actual response statuses/components/operation IDs in
OpenAPI and client schemas; no framework-default validation-body substitution.

### Rendered Web behavior

1. Load View and journey GET, validate path identity, Session version, full
   immutable admission context and lifecycle against run-status when needed.
   Inconsistent snapshots disable controls and permit safe GET reconciliation.
   Show engine-selected region/title and old consequence; one explicit confirm
   freezes URL/body/key and the full source/expected destination association.
   Cancel before dispatch has zero POSTs. Revisit/continuation/exit/actions share
   generation and foreground exclusion; double clicks cannot dispatch both.
2. Validate result against frozen source and authored displayed route; retain
   the complete confirmed POST result as immutable authority. Store only the
   new storage-v1 Session record, without old action request ID, **before** View
   retrieval/publication. Then fetch View/journey and compare Run/context,
   source/destination Session, scenario/content, all six visit fields and
   reciprocal source/destination link against the retained association. Current
   Session/Run versions may legitimately advance; never require version zero.
3. Schema-valid contradictory GET/View must not overwrite confirmed identity,
   enable gameplay, mutate storage again or dispatch another POST. Storage
   failure retains confirmed identity and blocks actions/admission/exit; explicit
   retry performs storage+GET only. Uncertain POST keeps exact bytes/key for
   explicit retry; GET cannot claim which competing key won. Cancellation after
   dispatch stops waiting, not the server commit. Reload never auto-POSTs.
4. With only successor storage v1 and all page memory/POST results discarded,
   GET/View recover visit three; journey supplies predecessor two and current
   identity. GET two supplies predecessor one and reciprocal successor three;
   GET one supplies reciprocal two. Compare every immutable association and
   complete context, validate ended historical versions and consistent current
   Run/lifecycle. Inconsistent reads get safe reconciliation, not partial display.
5. Keep authoritative recovery identity separate from displayed historical
   View/association. History traverses immediate previous/next links, at most
   three distinct visits; detects cycles. Historical navigation including next
   history/return-current is GET-only, no storage set/remove or write controls.
   Reload while displaying one/two returns to stored three. From an old recovery
   record, explicit “恢复当前旅程” may adopt the proven current association and
   perform storage-before-View; that is recovery adoption, not history browsing.
6. On return/reload/unmount/client replacement/target change, generation checks
   cover client instance, recovery identity and requested display target before
   any state/storage publication. Late history results cannot replace current
   View. Do not clear/replay uncertain mutations on navigation. Exit retains
   existing explicit permanent confirmation and storage-clear gating; fresh
   admission has empty selections and independent confirmation. Demo restart
   still yields 404/explicit clear, never replacement admission or replay.

Use normal deterministic Demo transport/store for the combined rendered case,
not unrelated mocks for each stage. Isolated contradictory/fault mocks are
additional tests, not the public journey. Preserve S6/S7-1/S7-2 recovery cases
and reassess DF-002 containment without broad discovery refactoring.

## 9. Turn evidence, prompt and Demo parity

Keep five S5 formulas and `run-prompt-context/v1` unchanged. Add catalogue mapping
for world two/archive pack; no formula change. Third-visit jobs use
`native-regional-turn-request/v1`, outer fields schema/request/binding/mechanics.
Binding has the existing visit-turn fields except `continuation_fingerprint`
is replaced by `regional_entry_fingerprint`; exact run_revision=5,
visit_ordinal=3, archive world/region/content and revisit request fingerprint.
Original entry_world still means admission. Old original and visit-two parsers
remain strict v1; dispatch by exact stored schema. Old committed replay precedes
fresh currentness checks; new actions require current active visit three.

Private `world-regional-prompt-context/v1` uses exactly the safe fields of
world-visit-prompt-context/v1 (schema,world_title,region_title,visit_ordinal,
previous_ending_status,previous_ending_title,entry_notice), with ordinal 3 and
approved archive literals. Keep 2,048 canonical UTF-8 byte ceiling, title/notice
bounds and authentic immutable detached seals. Bind source ending/base digest,
new receipt, turn inputs/current fingerprint and mechanics decision internally,
without exposing these private bindings in serialized prompt fields. Rebuild
attachment only after trusted job reconstruction; no client/model-created seal.
Compile/render outside transactions/locks; finalization revalidates exact bound
evidence, never recompiles under lock. Existing v1 prompt bytes stay unchanged.

Demo uses identical domain codecs, services, registry, errors and projection.
Add entry map and position CAS to complete snapshot/trial/stage/validation/
publication/rollback/reset machinery and exhaustive map manifests. Validate
whole family before publishing the trial store once. Preserve task-bound native
renderer allowance, no external-I/O fallback and no test-only public writer.
Restart loses process-local Sessions; it does not recover durable MySQL state.
Cross-process public journeys compare complete responses and private store
evidence across hash seeds, with both first-world ending classes.

## 10. Dependency-derived future implementation inventory

No source/content/test/migration file is edited by this task. The following
future paths are justified by inspected consumers. “New” means proposed file.
An existing listed path can remain unchanged when demonstrated sufficient;
record that disposition. Record a necessary additional mechanical dependency
and its verification impact **before editing**; product/schema/authority changes
require a revised approved plan, not an inventory exception or arbitrary cap.

| Concrete paths | Required responsibility |
| --- | --- |
| `domain/run.py`; `domain/run_protocol_binding.py`; new `domain/world_revisit.py` | Closed revision-5/6 families, v2 visit/position and strict new evidence/selection/entry/exit; no permissive old family. |
| `domain/world_continuation.py`; `domain/run_protocol_mechanics.py` | Reusable explicit prefix extraction only if needed; keep v1 codecs exact; add regional mechanics compatibility. |
| `application/run_operations.py`; `application/ports.py`; new `application/run_revisit_service.py` | New closed receipt namespace/result and repository ports; atomic owner, replay and journey projection. |
| `application/run_continuation_service.py`; `application/run_exit_service.py`; `application/native_run_admission.py`; `application/public_run_protocol.py` | Validate complete new families before extracting old admission/continuation replay; current-only exit, unchanged public admission context. |
| `application/session_content_registry.py`; `application/session_service.py`; `application/scenario_initialization.py` | Exact required third bundle, sealed base-derived regional initialization and routed old/new Session reads; preserve memory validator. |
| `application/native_turn_mechanics.py`; `application/world_visit_context.py`; `application/narrative_models.py`; `application/narrative_prompt.py`; `application/narrative_turn_orchestrator.py` | New bound turn envelope/private attachment and revalidation; existing formulas and outside-lock compiler/rendering. |
| `infrastructure/run_persistence.py`; `infrastructure/run_protocol_binding_persistence.py`; `infrastructure/world_continuation_persistence.py`; new `infrastructure/world_revisit_persistence.py` | Old prefix/new suffix dispatch, strict entry codec and complete reverse reconstruction; old v1 integrity unchanged. |
| `infrastructure/repositories.py`; `infrastructure/orm_models.py`; `infrastructure/unit_of_work.py` | Entry repository/position CAS, orphan detection, compatible character-binding/retirement reads and matching constraints, same pinned owner. |
| new `alembic/versions/20260918_0010_native_regional_revisit.py` | Section 7 exact schema/up/down/probes/failure boundaries; preserve 001–009. |
| `api/main.py`; `api/dependencies.py`; `api/schemas.py`; new `api/run_revisit_routes.py`; `api/run_continuation_routes.py`; `api/run_exit_routes.py` | Normal production composition and explicit public/OpenAPI errors/compatibility/read routing. |
| `api/demo_composition.py`; `infrastructure/demo_persistence.py`; `infrastructure/native_demo.py` | Atomic new map/position behavior, complete classifier and deterministic render parity. |
| new `config/scenarios/receipt_archive_v1.json`; new `docs/scenarios/receipt_archive_v1.md` | Approved authored mechanics/public consequences, independent raw digest and public play route; no old-pack edits. |
| `web/src/api/schemas.ts`; `web/src/api/client.ts`; new `web/src/runJourney.ts`; `web/src/runContinuation.ts`; `web/src/runExit.ts`; `web/src/App.tsx` | New schemas/frozen request/confirmed association; three-visit GET navigation, current/display separation, explicit confirm/exit/recovery. |
| new `tests/unit/test_world_revisit.py`; new `tests/unit/test_world_revisit_persistence.py`; new `tests/unit/test_run_revisit_service.py`; new `tests/unit/test_run_revisit_api.py`; new `tests/unit/test_receipt_archive_content.py` | New goldens, reconstruction matrices, authority/transaction/projection and genuine playable new region/endings. |
| `tests/unit/test_session_content_registry.py`; `tests/unit/test_world_visit_context.py`; `tests/unit/test_native_turn_mechanics.py`; `tests/unit/test_run_protocol_prompt_context.py`; `tests/unit/test_session_service.py` | Content pin/version/local-memory, new attachment/currentness and old prompt/turn preservation. |
| `tests/unit/test_run.py`; `tests/unit/test_run_operations.py`; `tests/unit/test_run_persistence.py`; `tests/unit/test_run_protocol_binding.py`; `tests/unit/test_run_protocol_binding_persistence.py`; `tests/unit/test_run_repositories.py`; `tests/unit/test_repository_and_uow.py` | Shared family/receipt/classifier/port regressions; exact old terminal versus new active 5. |
| `tests/unit/test_native_run_admission.py`; `tests/unit/test_public_run_protocol.py`; `tests/unit/test_run_continuation_service.py`; `tests/unit/test_run_continuation_api.py`; `tests/unit/test_run_exit_service.py`; `tests/unit/test_run_exit_api.py` | Old admission/continuation/exit replay on advanced family, history/current authority and opaque errors. |
| `tests/unit/test_native_demo.py`; `tests/unit/test_demo_persistence.py`; `tests/unit/test_demo_composition.py`; `tests/unit/test_run_composition.py`; `tests/unit/test_player_character_api.py`; `tests/unit/test_player_character_service.py` | Composition isolation, exhaustive route/DTO inventories and current/historical binding/retirement consumers. |
| new `tests/integration/test_mysql_world_revisit.py`; new `tests/integration/test_mysql_world_revisit_migration.py` | Real public journeys, atomicity/races/failure/corruption, installed checks and 010 migration evidence. |
| `tests/integration/test_mysql_world_continuation.py`; `tests/integration/test_mysql_native_run_admission.py`; `tests/integration/test_mysql_native_run_exit.py`; `tests/integration/test_mysql_native_turn_mechanics.py`; `tests/integration/test_mysql_player_character_run_binding.py` | Affected production readers, old-prefix/new-current behavior and runtime-head fixtures. |
| `tests/integration/test_mysql_player_character.py`; `tests/integration/test_mysql_run.py`; `tests/integration/test_mysql_run_protocol_binding.py` | Current-head/schema inventory expectations if needed; do not rewrite historical-head assertions. |
| new `tests/e2e/test_native_world_revisit.py`; `tests/e2e/support/native_world_continuation_child.py`; `tests/e2e/test_native_world_continuation.py`; `tests/e2e/support/demo_replay_child.py` | Normal Demo public transport for full three-visit play/cross-process identity and new map manifests; old journey regression. |
| new `web/src/runJourney.test.ts`; new `web/src/App.journey.test.tsx`; `web/src/api/client.test.ts`; `web/src/App.continuation.test.tsx`; `web/src/App.recovery.test.tsx`; `web/src/App.action-loop.test.tsx`; `web/src/App.test.tsx`; `web/src/runContinuation.test.ts`; `web/src/runExit.test.ts`; `web/src/test/fixtures.ts` | Combined public Demo rendered flow, schema-valid contradictions, multi-visit reload/storage/generation/uncertainty negatives and existing selection/exit recovery. |
| `PLANS.md`; `docs/architecture.md`; `docs/run_protocol.md`; `docs/public_client_contract.md` | Mutable implementation status/contracts/evidence and inventory disposition. Published S7-3 plan becomes protected after publication. |

Existing `tests/unit/test_world_continuation.py`,
`tests/unit/test_world_continuation_persistence.py`,
`tests/unit/test_undelivered_receipt_content.py`,
`tests/unit/test_scenario_catalog.py`, `tests/unit/test_story_director.py`,
`tests/unit/test_run_entry_service.py`, `tests/unit/test_run_service.py`,
`web/src/sessionRecovery.test.ts`, `web/src/runSetup.test.ts` are affected
verification consumers expected to run unchanged. Old migration suites
`test_mysql_native_run_migration.py`, `test_mysql_native_run_exit_migration.py`,
`test_mysql_world_continuation_migration.py` retain isolated historical preconditions;
only concrete new-head interaction/preservation cases require fresh execution.
No generic scenario engine rewrite, dependency installation, original entry
catalogue expansion or production Provider distribution is part of the inventory.

## 11. Acceptance and proportionate evidence responsibilities

Implement in dependency order: closed domain/codecs + schema/reconstruction;
authored pack/registry + sealed initialization; atomic service/replay/exit;
production API/Demo; rendered recovery/history; integrated acceptance and docs.
Keep a first public three-visit action/reload milestone, but do not deliver
without endings/exit or required persistence/failure proof.

| Case | Exact setup and owning boundary | Expected outcome / mutation and evidence |
| --- | --- | --- |
| R01 — public return | Normal public admission and actions produce first-world RESOLVED and FAILED in separate journeys; continue, OBSERVE/TALK/hold in world two; GET offer then explicit POST revisit. API + real MySQL + Demo. | Two worlds/three visits; Run 5; current ordinal 3/archive; identical carried PlayerState; visible hold/undelivered consequence. New OBSERVE advances legitimate Session turn, no new Run or character revision. Old Session Views/root/event/receipt bytes unchanged. No injected ending. |
| R02 — meaningful endings | From each actual eligible route, inspect archive and seal/defer separately. All three profiles × default/beneficial/adverse permitted objective boundaries; public-play zero-composure routes where pressure charges resources, separately labelled resource-only zero fixtures where pressure is zero. | Both declared endings publicly reachable; independently expected S5 resource effect and no clocks/refill/items/reward. Full PlayerState equality at entry; later changes only declared action effects. Exit 5→6 and fresh same-character admission/first action. Exhausted pool stays empty. |
| R03 — eligibility/anti-farming | Active visit two; actual release and actual deadline FAILED endings; held ending; before/after consumed receipt; fresh operation keys; GET/reload/history; clock/time/hash-seed changes. | Only held ending offers return. All rejected fresh attempts produce RUN_REVISIT_NOT_AVAILABLE and zero writes; one allowed zero-cooldown entry, no fourth visit or benefit. Mutation of purported client unlock/destination rejected 422. Missing required pack is integrity/config failure, not unavailable. |
| R04 — exact evidence/replay | Independent request/ID/seed/entry/receipt/turn/context goldens; replay after action, termination and later admission; same key altered versions; old continuation/admission/exit replay. | Exact original result, no IDs/clock/render/commit on replay; conflict on changed intent. Strict old parsers reject new records, new ones reject arbitrary ordinal/revision. Source/registry/map order does not change deterministic result. |
| R05 — corruption/authority | Each entry field missing/extra/coerced/rehash mismatch; crossed Run/line/Session/owner/region/base, missing entry/visit/position/receipt, bad initial event/local memory, changed old pack/version, corrupted new family requested via any of three Sessions. | Opaque 409 SNAPSHOT_INVALID after ownership, no partial/null association/no writes. Foreign path 404. SQL and Demo same first failure; double-corruption probes fix precedence. Matching progressed control accepted; no snapshot repair or legacy fallback. |
| R06 — concurrency | Separate actual MySQL physical connections, observe waiter/exclusion: same key, changed same key, different keys, return vs exit, same-PC admission/retirement, final turn, migration vs writer both orders. | Exactly one complete winner; exact replay/conflict/unavailable as section 6; no resource or unlock duplication, no leaked lock, current-read revalidation. Sequential calls or mocks do not prove concurrent exclusion. |
| R07 — failures | Inject exception/cancellation at each new stage/flush/CAS/entry insert/receipt/final reconstruction; commit before/after durability and cleanup; equivalent Demo trial-publication failure. | Precommit complete rollback and unchanged originals; cancellation propagates. Unknown result never claimed rollback/success; one commit attempt, exact explicit retry/GET finds authoritative result. Failed owner detached/disposed; independent observer verifies exclusion release. |
| R08 — migration | Recorded real dedicated DB initial state; 009 legacy/admission/original-terminal/continued-active/continued-terminal controls; upgrade 010, new family, unsafe downgrade, safe old-family downgrade; single-null/check/FK/bounds probes; partial-DDL boundaries/current snapshot. | Old data/evidence preserved, constraints enforced, ORM equal installed schema. New/partial evidence refuses before DDL; old terminal 5 permits 010→009. Exact actual prefix/disposal recorded on every new statement fault; restore initial schema/data/enforcement/lock state. No migration mock substitutes. |
| R09 — combined rendered recovery | Normal deterministic Demo store/transport, actual source play/hold/revisit/first archive action. Retain only new storage v1, discard component state and POST response, remount, GET journey, read 3→2→1→2→3; reload while historical; finish/exit/fresh entry. | Correct arrival/current progress, all reciprocal immutable identities; historical GET-only and zero storage set/remove; old controls absent. Retained confirmed POST vs schema-valid contradictory visit/world/region/content/context rejected without identity overwrite, enabled action or new POST; positive progressed control. Additional exact retry/lost response/storage failure/client replacement/unmount/stale completions and cancel/exclusion tests. |
| R10 — deterministic compatibility | Same full public three-visit journeys for first-world RESOLVED/FAILED and archive seal/defer in two processes/hash seeds; affected old family/turn/routing/Demo/prompt consumers. | Equal full public traces and complete store evidence; no external I/O; no implicit initial entry option. Reversed ending definitions and synthetic simultaneous seal/defer select same priority result. Synthetic selectors, corrupt fixtures and injected zero-resource states are labelled separately from genuine public-play reachability. |

R02 profile permutations must finish, not merely reach a decision. For effective
pressure q=resource_pressure//50 > 0, deplete before the two evidence actions
in the dispatch hall using exactly max(0,ceil(current_composure/q)-2) legitimate
ineffective CUSTOM actions, then OBSERVE/TALK/hold. At current cap 6, start at
most 4 and adverse cost bounds, at most four such waits cost 20 plus two evidence
actions at most 12, still below deadline 40. Assert actual effects and source
ending rather than trusting this bound. For q=0, current content has no skill
resource cost and this route cannot deplete; require a separately labelled
resource-only fixture for zero at that boundary, with all endings still reached
through public actions. It is not zero-resource public reachability evidence.
No source/runtime ending, receipt, unlock or visit may be injected into a claimed
public journey. Archive no-clock behavior needs
explicit independent assertions that all five unchanged policies compose without
creating a clock or reward. At least one source FAILED/hold/archive completion
must run through real persisted reconstruction, not just in-memory parity.

Future verification, only after separate implementation/access authorization:
use PowerShell 7+, explicit `.\.venv\Scripts\python.exe`, canonical
`scripts/verify.ps1 -Mode Offline` and sanitized MySQL mode; no `.env`, no real
Provider/Live. Focused tests first; once stable run affected shared family/turn/
admission/history consumers and canonical Offline once, affected real-MySQL
suites, compileall/dependency/Alembic metadata as applicable, affected Web then
complete Web once, typecheck, lint and deterministic-demo build. Configure UTF-8
in child and evidence wrapper; preserve raw commands/logs/exits and source,
content, dependency/environment identities from the first run. No broad rerun
just because prose changed; no overlapping pass totals or earlier-source run
labelled final-source. Cleanup/teardown errors are failures, retained as history.

Before any DB mutation prove mysql+asyncmy and database deviation_protocol_test
without printing URLs/secrets. Record actual initial schema/data/check definitions
and enforcement/named lock state; restore exactly that state, not an assumed
007/009 head. Run schema suites sequentially, with explicit per-suite preconditions
and restoration. Missing safe DB prerequisite is a precise missing proof, not a
SQLite/mocked pass. New reconstruction/entry/current-read/schema interactions
require fresh MySQL evidence even if old fault internals are unchanged.

Evidence reuse is conditional, not exercised by this planning task. Locate
S2's actual 5,624,910-call logs/proof/counters under
`C:/Users/dylanmonster/AppData/Local/Temp/s3-implementation-20260916-audit/correction`
and compare source/dependency/environment/scope before reuse; run other affected
S2 tests normally. Locate S7-2 original and correction manifests/logs through
[their evidence records](run_protocol.md#s7-2-evidence-map). Reuse unchanged
historical migration internal faults only after identity/method applicability;
new 010 boundaries and old/new family preservation are fresh. Registry/classifier
changes prohibit blanket reuse of old Session/turn/reconstruction suites. Missing
artifacts remain qualified missing evidence; do not search indefinitely or invent
passed results. Browser acceptance is separately authorized, not required or
performed by this documentation task.

## 12. Remaining ownership, documentation and review handoff

S7-3 owns the bounded important-world designation, priority/anti-repeat exception,
zero deterministic cooldown, one regional unlock/entry and anti-farming above.
It does not claim a reward system. No parent duty is renamed or discarded:
S7-4 retains authorized canon-preserving world-line transitions and normal Run
completion; S7-5 retains final continuity/revisit/regional/progression acceptance
and parent criteria 10–12 reconciliation. Important-NPC priority remains unavailable
until separately published logical-identity and world predicates exist. Absence
does not block this non-NPC regional progression. No Phase 3.4/6 hooks, golden
memory, copied NPC, line replacement, revival or broader-release claim.

DF-001/DF-002 retain their register and dispositions. Planning synchronizes the
inspected browser containment evidence in mutable status owners without editing
historical reports/register/workflow. Implementation reassesses actual exposure;
required authority/corruption/gameplay/recovery/evidence failures cannot be
deferred. Use existing risk-based rules, no speculative new finding or gate.

This candidate edits exactly five documents: this new plan, `PLANS.md`,
`docs/architecture.md`, `docs/run_protocol.md`, `docs/public_client_contract.md`.
All source/tests/content/migrations, published plans, workflow/guardrails and
deferred findings are protected. No project tests, compileall, Alembic execution,
database, application/browser or Provider run is needed or authorized now.
Check complete final files/diff, current-status consistency, local links/anchors,
UTF-8/LF/final newlines/whitespace, modes, exact scope/protected identities and
Git refs/index/operation state. Synchronize the workflow checklist in this one
candidate; no separate S7-2 lifecycle-closeout task.

External handoff freezes exact baseline and per-file bytes/lines/SHA-256/Git blobs/
modes; complete binary/full-index Git patch including the new file; patch bytes,
insertions/deletions/SHA-256; extracted P01–P09 and implementation/evidence tables;
checks and final Git state. A complete-file aggregate, if present, is separately
labelled with ordering/framing and is never called a Git patch. Hashes belong
outside their hashed documents to avoid self-invalidating identities. Any relevant
baseline or candidate-byte change requires rebinding and fresh review.

Exactly one operative **plan-review success token**, defined here as a required
future reviewer output, not issued by this authoring task:

`PHASE_3_3_S7_3_WORLD_REVISIT_REGIONAL_PROGRESSION_PLAN_INDEPENDENT_REVIEW_APPROVED`

Either APPROVED or APPROVED_WITH_DEFERRED_FINDINGS emits that same token and binds
all five files and product-decision disposition. Technical approval does not
approve P01–P09 for the user; pending product decisions must be stated, and
implementation remains blocked until accepted. CHANGES_REQUIRED, historical
tokens and authoring status cannot satisfy this gate. Companion documents define
no competing token.

Sole **dormant, non-operative implementation-review token**:

`PHASE_3_3_S7_3_WORLD_REVISIT_REGIONAL_PROGRESSION_IMPLEMENTATION_INDEPENDENT_REVIEW_APPROVED`

It becomes usable only after exact plan approval, explicit product acceptance,
separately authorized local documentation commit, manual user publication,
clean aligned baseline confirmation and separately authorized implementation.
Successful implementation review then binds complete code/content/docs and
R01–R10 evidence under either permitted successful disposition. No staging,
commit, push, deployment, runtime or implementation is authorized by this plan.
No extra post-commit audit is required. Next: one substantive independent
read-only plan review of the complete candidate. S7 and Phase 3.3 are incomplete.

## Guardrail impact

None. This proposal applies existing rules; no newly confirmed reusable defect
requires a guardrail/workflow edit. DF-001/DF-002 remain deferred.
