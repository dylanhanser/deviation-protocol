# P3.3-S7-4 — Canon-preserving line transition and normal Run completion

Status: **PROPOSED documentation plan candidate; awaiting one substantive
independent read-only plan review and explicit user disposition of P01–P09.
Not approved, frozen, published, or implementation authorization.** S7-3 product
approval does not approve these new decisions. All new contracts below are
proposals for that single review, not descriptions of shipped behavior.

## 1. Baseline, controlling allocation and publication evidence

Planning preflight on 2026-09-20 verified branch `main`, HEAD/local main/local
origin/main `0b20dcd1d0ec2a6264dacd9e27c3d9dc37d3c597`, ahead/behind 0/0,
clean worktree and empty index, no conflicts, active Git operations or locks.
No fetch/pull was used. An external initial manifest records all 322 tracked
files' raw identities, index blobs/modes and Git refs. It is the protection
baseline for this five-document task, not a test/database-state assertion.

The [parent Phase 3.3 plan](phase_3_3_run_protocol_implementation_plan.md),
[published S7 allocation](phase_3_3_s7_1_post_ending_run_exit_plan.md#2-remaining-s7-allocation-in-dependency-order),
[S7-2 plan](phase_3_3_s7_2_same_line_world_continuation_plan.md) and
[S7-3 plan](phase_3_3_s7_3_world_revisit_regional_progression_plan.md) control
scope. Apply [workflow](engineering/codex_workflow.md) and
[guardrails](engineering/guardrails.md), especially AUTH-001, API-001,
STATE-002, DB-001/002, MODEL-001/002 and PLAY-001. The allocation requires a
concrete canon-preserving world-line transition representation **and** normal
completion. It does not require replacing the permanent line or building a
branching-world engine. S7-5 retains final integration and reconciliation of
parent criteria 10–12; neither this plan nor its future implementation closes S7.

S7-3 implementation publication is recorded at the baseline above. Its frozen
plan remains unchanged at `0ea295e358f526c5101856e4dc2370d66b23b938`; P01–P09
there apply only to S7-3, including consent to the engine-selected destination.
Earlier CHANGES_REQUIRED reviews/corrections remain historical evidence. This
task does not issue or infer an independent approval token from a commit.

The external S7-3 browser report and evidence index at
`C:/Users/dylanmonster/AppData/Local/Temp/deviation-s7-3-browser-20260919`
were inspected, not merely inferred from the user's account. They record both
representative routes, ineligible-ending/restart checks, 38 screenshots and
360 completed-response request records (292 GET, 68 POST). Cancellation/history
windows and the eight post-restart GETs contain zero writes. Cleanup and unchanged
322-file/Git identity are reported by those artifacts, not re-executed here.
The resource observations on both archive routes are 6/6; storage internals,
request bodies, private authority, atomicity and depleted-resource archive entry
were not directly observed. DF-001/DF-002 remain deferred with existing containment.
One ClientDisconnect log observation was not a reproduced blocker or new finding.
See [publication/evidence reconciliation](run_protocol.md#s7-3-publication-and-bounded-browser-evidence)
for exact inspected artifact identities. These limits do not block planning and
do not constitute real Provider, production, or broader-release acceptance.

## 2. Existing concepts and the smallest playable result

| Concept | Implemented meaning at this baseline | S7-4 treatment |
| --- | --- | --- |
| Session ending | Committed RESOLVED/FAILED runtime, event-derived memory, immutable ended snapshot; Run may remain active. | Preserve. Ending class alone never completes a Run. |
| Same-line continuation | S7-2 revision 3→4, second world/Session, same permanent Run/line/character/protocol. | Preserve old operation and immutable replay. |
| Regional revisit | S7-3 revision 4→5, third Session in the existing second world, archive region, retained consequences. | Preserve; no fourth visit or retry of consumed entry. |
| Authorized world-line transition | Allocated/reserved; no current separate canon-transition writer. Permanent ContinuousStoryLineId is already immutable. | Propose one explicit change of the Run-owned second world's verification disposition, inseparable from completion. |
| Explicit termination | S7-1/2/3 post-ending exit, terminal revisions 4/5/6; historical binding. | Preserve as abandonment, with no normal-completion record. |
| Normal completion | Enum/SQL lifecycle vocabulary reserves `completed`, but CanonicalRun and closed classifiers reject it; no public writer. | Add exactly the qualified 5→6 completed family below. |
| Fresh admission | Separate explicit creation of a new Run/line/Session using an eligible character. | Available after either terminal outcome; never resumes or inherits the old line. |

Recommended play: first world RESOLVED **or** FAILED → second world
**会签暂缓发运** → confirm archive → OBSERVE → **封存待核记录** → engine
explains that verification can close with the unresolved fact preserved → player
opens **完成本次旅程** and confirms **确认结案并完成旅程** → durable completed
journey, with readable three-visit history → reload → separately return to setup
and explicitly admit the same eligible character, then perform its first action.
The player may instead cancel or explicitly terminate; neither grants completion.

This is a real world-state transition: the line's verification disposition changes
from `open_unresolved` to `closed_unresolved`, with an immutable provenance record.
The UI displays **待核事项保留，核验旅程已结案**. The dispatch hold stays true;
delivery remains unproven; the sealed record remains sealed. A Session ending
alone leaves the disposition open. Exit abandons the Run without this closure.
Thus equal terminal revision numbers or released bindings do not make completion
and termination synonyms. No claim of successful delivery, repaired hospital
record, resurrection or solved mystery follows from completion.

Existing worlds and archive contain all prerequisite gameplay evidence. A new
world/Session/scenario pack would add travel unrelated to the allocated proof.
The smallest new authored content is a fixed completion rule and two notices in
`domain/run_completion.py` and `application/run_completion_service.py`, versioned
`receipt-archive-closure/v1`; it is a closed singleton, not a configurable rule
framework. Existing three scenario packs/digests, actions, ending priorities,
initialization, world/region versions and immutable roots remain unchanged.
This addition supplies the previously absent meaning of *closing this journey
while retaining its unresolved canon*, not additional in-world delivery evidence.

## 3. Consolidated product decisions

All rows are one coherent recommendation and require user disposition. Technical
review can approve implementability while explicitly leaving product acceptance
pending; no extra approval stage or separate closeout task is introduced.

| ID | Exact proposed rule/value | Plain-language gameplay effect | Recommendation and reason | Approval status |
| --- | --- | --- | --- | --- |
| P01 | Only current archive visit three of exact active regional family 5, with `receipt_archive.ending.unresolved_sealed` / RESOLVED, committed seal event/completed memory, true hold-effective/delivery-unproven/unresolved-sealed facts and intact prior hold provenance, qualifies. Both valid first-world ending classes remain allowed. | Finish the authored investigation without pretending the missing delivery was proved. | Recommend: meaningful reachable completion based on concrete facts, not RESOLVED or an empty pool alone. | PROPOSED |
| P02 | Archive defer/FAILED has history and explicit exit only. Original-world endings and second-world hold do not complete; their existing continuation/revisit/exit choices remain. Dispatch-closed/deadline FAILED has exit only. | No skipped investigation, automatic failure completion or new retry route. | Recommend: preserves the already published routes and distinguishes session settlement from journey completion. | PROPOSED |
| P03 | Normal completion requires a separate explicit confirmation after ending. Cancel sends zero POST and changes nothing. Completion and existing explicit termination are mutually exclusive alternative outcomes; first committed operation wins. | Player chooses to record a qualified completion or abandon; doing nothing retains active binding. | Recommend: durable consent and clear lifecycle semantics. | PROPOSED |
| P04 | Completion atomically transitions the same Run/line's `world.undelivered_receipt@1` verification disposition `open_unresolved`→`closed_unresolved`, transition `close_unresolved_verification/v1`, and changes lifecycle active 5→completed 6. Destination is a terminal disposition, not another world/line/Session. | Shows the preserved unresolved case as a completed journey; no new travel or identity. | Recommend: minimal observable canon-preserving transition satisfying the S7 allocation. | PROPOSED |
| P05 | Carry/reference all prior committed facts, consequences and provenance. Hold remains effective; delivery stays unproven; sealed archive remains sealed. Transform only the new line-owned verification disposition. | Old history and failure consequences remain truthful after completion. | Recommend: no canon reset, LLM summary authority or NPC copying. | PROPOSED |
| P06 | Completion changes no PlayerState, inventory instances, wallet, equipment, skills, cooldowns, attributes or Structured Player Character revision/lifecycle. Historicalize only this Run's binding and free its active slot. | No refill or character retirement; same eligible character can later start afresh. | Recommend: reuse existing terminal ownership boundary. | PROPOSED |
| P07 | Completed history stays readable by existing owner/controller rules after reload, later admission and later character retirement. No action, exit, continuation, revisit or second completion on that Run. Fresh admission requires new explicit setup and confirmation, new Run/line, no transfer claim. | A completed journey is permanently readable and cannot be revived. | Recommend: bounded recovery with no cross-line inheritance. | PROPOSED |
| P08 | No reward, fee, currency, item, skill, stat gain, achievement or unlock for another Run. Completion record and preserved outcome are the only new benefit. | Cannot farm completion for resources. | Recommend: no new economy or reward ledger. | PROPOSED |
| P09 | Reuse the two worlds/three visits and all frozen packs; add only the versioned fixed closure rule/notices. No fourth visit, branching line, global world update, major-NPC identity, later-phase hook or Provider decision. | Completes the existing playable journey with a small explicit epilogue. | Recommend: fulfills transition/completion without unrelated content or engine expansion. | PROPOSED |

P04 is the proposed new product authority for the world-state transition. It
does not amend the permanent-line invariant: `ContinuousStoryLineId` still names
one line owned for the Run's lifetime. If review requires a replacement line,
fourth playable destination, or rewriting a fixed scenario fact, that conflicts
with this proposal and must return CHANGES_REQUIRED with the exact narrow
product amendment; implementation must not silently relax validation to fit it.

## 4. Canon ownership, provenance and content versions

“Canon” means the following validated facts, never a narrative summary:

| Authority | Provenance/owner | Completion treatment |
| --- | --- | --- |
| Run, permanent line, frozen profile/protocol and entry world | Original revisions 1–3, creation/binding/participation receipts, immutable admitted character reference and bound native records | Reference unchanged; native bindings stay bound at 3. |
| First-world ending and consequences | Original ended Session/latest snapshot, its exact content version and committed event/memory; S7-2 source-root and continuation evidence | Reference unchanged, including FAILED. Do not convert it to survival/death claims. |
| Dispatch hold and unproven delivery | Visit-two ended latest snapshot; catalog fixed `hold_is_not_delivery`; persisted ScenarioDecisionSelected with inner `dispatch.held`, matching runtime and completed memory; S7-3 entry base hash | Revalidate and reference, never lift a Boolean out of its provenance. Old NPCs/clocks remain in that Session. |
| Archive initialization and observations | Immutable regional entry, source/base associations, pinned `receipt-archive-1.0.0` bundle and initial event/memory | Preserve; archive fixed `hold_effective=true` and `delivery_unproven=true` cannot change. |
| Archive seal/ending | Latest ended snapshot; `.unresolved_sealed=true`; one persisted ScenarioDecisionSelected for `receipt_archive.action.seal`, decision `receipt_archive.decision.record`, inner `receipt_archive.record.sealed`; applied scenario event and completed memory source IDs/sequences | Require this exact authored tuple from the frozen pack, never an alias. No new ScenarioCompleted event is invented. |
| Line verification disposition | New closed rule `receipt-archive-closure/v1`, authenticated completion request, exact source chain and immutable completion evidence | Before receipt: derived `open_unresolved` only for qualifying sealed active archive. After receipt: `closed_unresolved`; one irreversible trusted transition. Other endings have no such qualified disposition. |
| Current character/player state | Admitted immutable character revision plus archive latest PlayerState; current owned character row governs fresh operation eligibility | Reference unchanged; only Run binding becomes historical. Future fresh admission uses existing current eligibility. |

The archive decision ID above is the inspected authored value;
section 6 evidence uses that identity and never a prose inference. Old events,
roots, visits, positions, entries, snapshots, memory, jobs and accepted prose are
not rewritten. Persistent world state remains the composition of roots and each
region's authoritative snapshot, augmented by the one validated closure record.
No second mutable world-state copy or read-time “completed” flag is introduced.

Completion evidence is the authoritative transition record in the existing
successful mutation receipt, not a new event inserted into an ended Session.
The closed policy changes only the line-level verification disposition, never
the scenario fact dictionary. Completed reads expose the original View plus a
separate completion projection. Older Views remain byte-equivalent. Stored
completion absence is valid on every old family; on a completed family it is
corruption, not a default to open or terminated.

All NPC instances remain owned by their original Session. They are readable
only through authorized old state; no new scene, identity match, counterpart,
copy, resurrection, memory merge or action target is created. Model text may
render existing permitted public facts under the old rules, but completion is a
fixed server notice with zero Provider calls. It cannot infer delivery, invent
closure eligibility or change a fact. Unknown versions, missing content, bad
event links or contradictory facts fail closed before any public trusted result.

Version inventory: preserve every original v1 codec and pack. Add only
`receipt-archive-closure/v1`, completion request/operation/evidence/result v1,
`run.canon-transition/v1`, and the explicit completed-only public v2 branches in
section 9. There is no protocol-envelope, snapshot, memory, visit, region,
world-position or recovery-storage version change.

## 5. Closed lifecycle families and current position

| Family | Exact lifecycle/revision/mutation | Immutable counts and position |
| --- | --- | --- |
| Existing admitted / original terminated | active 3 ATTACH_SESSION / terminated 4 TERMINATE_NATIVE_RUN | Existing one-Session family unchanged. |
| Existing continued / continued terminated | active 4 CONTINUE_NATIVE_RUN / terminated 5 TERMINATE_CONTINUED_NATIVE_RUN | Existing two-visit family unchanged. |
| Existing regional / regional terminated | active 5 REVISIT_NATIVE_REGION / terminated 6 TERMINATE_REVISITED_NATIVE_RUN | Existing three-visit family unchanged; actual position remains at revision 5, visit three. |
| New `NativeRunRegionalCompletedV1` | completed 6, prior 5, `COMPLETE_REVISITED_NATIVE_RUN`; exact active regional prefix, qualified sealed ending | Revisions 1..6, one creation receipt, five mutation receipts, three participations joined 3/4/5, two unchanged roots, three visits, one regional entry, one unchanged position at 5. |

New family carrier has exactly `revisited: NativeRunRegionalRevisitV1`,
`canonical_run: CanonicalRun`, `completion_evidence: NativeRunCompletionEvidenceV1`
and a read-only `admission` accessor from that prefix. A pure constructor
`complete_revisited_native_run` accepts only the validated prefix, completion
evidence and its bound timestamp; it yields exactly the new successor.
Do not add completed to an old terminated carrier or classify by revision alone.

CanonicalRun admits completed only with this mutation, prior/current 5/6 and
joins (3,4,5). Binding must be complete historical with inactivated_at equal
to current provenance time and no earlier than bound_at/preceding mutation.
Creation/line/reference/binding operation/source/bound_at remain exact. Exclude
this explicit terminal edge from participation coverage, as with the three
existing terminal edges; retain the single binding edge. There is no new
participation, position movement or Session version increment. Terminal-to-active,
terminated-to-completed, fourth visit and revision ≥7 remain rejected.

Historical authorization uses the admitted immutable character version and
current controller ownership, not continued active binding or current character
revision equality. Fresh completion additionally requires current active owned
character, exact current archive path and active binding. Later admission or
retirement cannot invalidate owned history or old exact receipts, and replay
must never release a newer Run's slot.

## 6. Exact operation and immutable evidence

Add namespace `run.complete-revisited-native/v1`, mutation
`COMPLETE_REVISITED_NATIVE_RUN`, safe receipt result schema
`run.complete-revisited-native-result/v1`. Existing receipt key remains
`(run_id, operation_namespace, operation_id)` and unique resulting Run revision.
Safe internal result is same Run/line, completed 6, null participation and null
applicable-character result. The completion record lives in the receipt's
`operation_evidence_canonical`; no parallel completion table/map or mutable flag.

`NativeRunCompletionRequestV1` has exactly:

```text
schema="run.complete-revisited-native-request/v1", controller_binding,
player_id, public_operation_key, run_id, continuous_story_line_id,
source_session_id, expected_run_state_version, expected_session_state_version,
source_reference
```

Use original strict opaque IDs (1..128 ASCII pattern), Session 1..64,
versions signed int64 with Run ≥1 / Session ≥0. Expected 5 is an eligibility
comparison, not the decoder domain; otherwise changed intent could evade
idempotency conflict. Internal operation ID is lowercase SHA-256 of canonical
`{schema:"run.complete-revisited-native-operation/v1", controller_binding,
public_operation_key,run_id}`. Fingerprint is SHA-256 of the complete canonical
request. Trusted source reference is composition-owned; client supplies neither
Run/line, destination, character, ending, rule nor facts.

Completion ID is lowercase SHA-256 of canonical
`{schema:"run.completion-id/v1",run_id,continuous_story_line_id,operation_id}`.
It is an opaque public association ID, not permission or a raw evidence digest.
No random issuer, Session creation ID, selection seed or gameplay clock is required.

`NativeRunCompletionEvidenceV1` has exactly:

```text
schema="run.complete-revisited-native-evidence/v1", request, completion_id,
rule_version="receipt-archive-closure/v1", sources, held_event, sealed_event,
transition, occurred_at
```

`sources` is an ordered tuple of exactly three closed objects, each with
`visit_id, visit_ordinal, session_id, session_state_version, world, region,
scenario_id, scenario_content_version, content_sha256, snapshot_sha256,
ending_id, ending_status`. World/region are existing two-field references.
Require exact ordinal/content/world/region association from the reconstructed
chain; source three equals path/version in request. Hash each validated ended
snapshot with existing `state_fingerprint`, not raw SQL JSON. Source one must
equal the S7-2 ended-source identity, source two the S7-3 sealed base and source
three the latest qualified archive. Content digests must equal the immutable
registry bundles, never a digest self-approved from replaced content.

`held_event` and `sealed_event` each have exactly `session_id, event_id,
sequence_no, scenario_event_id, decision_id, selected_action_id` (strict positive
int64 sequence, bounded IDs). Require each field to equal its respective
persisted ScenarioDecisionSelected columns/payload and runtime applied-event record.
Hold is `undelivered_receipt.action.hold` / inner `dispatch.held`; seal is
`receipt_archive.action.seal` / inner `receipt_archive.record.sealed`.
Require completed memory's last source event ID and sequence to match that
persisted decision, its scenario/version/ending to match the source, and all
runtime applied event references to resolve to the same Session's stored events.
Do not trust caller-constructed receipts or sort/read receipt-like values before
authenticating repository provenance. Full prefix validation owns first-world
ending evidence; the new record does not invent an extra standalone ending event.

`transition` has exactly `schema="run.canon-transition/v1"`,
`kind="close_unresolved_verification/v1"`, `world` (second world@1),
`from_disposition="open_unresolved"`, `to_disposition="closed_unresolved"`,
`preserved_facts={dispatch_held:true,delivery_unproven:true,unresolved_sealed:true}`.
These are typed canonical values with the ownership table's exact provenance,
not copied narration. No arbitrary fact map is accepted. The entire evidence
is the completion record; `occurred_at` equals receipt/revision/current/binding
inactivation time, canonical UTC six-digit fractional seconds and Z. It is
nondecreasing against the previous Run mutation and uses existing DATETIME(6)
precision; no new Session/event timestamp is introduced or truncated.

Strict actual-carrier validation precedes canonicalization. Reuse NFC canonical
Run JSON: sorted keys, compact separators, ensure_ascii=False, no NaN. Evidence
ceiling 16,384 UTF-8 bytes; request follows the same bound and transport body
remains 1,024 bytes. Decode rejects duplicate/extra/missing keys, BOM, invalid
UTF-8, aliases, bool/float coercion, noncanonical bytes and unknown schema/rule.
Existing v1 receipt/envelope ceilings remain unchanged. Independent literal
goldens must bind bytes/hash, complete source associations and time; round-trip
agreement alone is insufficient. No schema/content digest placeholders ship.

### Complete reconstruction and first-failure ownership

SQL and Demo use one ordered shared validation contract for every owned path:

`RunCompletionEligibilityPolicy` is an independent domain policy over detached,
fully validated source evidence. The application obtains that evidence only
after the ordered reconstruction below; a public request, model output or
caller-made Boolean cannot issue eligibility. The policy is pure and does not
read persistence, call a Provider, infer NPC identity or grant a write capability.

1. Strict transport then principal/path ownership. Missing/foreign Session is
   opaque 404. Resolve reverse participation; absence with orphan evidence is
   corruption after ownership, not legacy fallback.
2. Load aggregate/current/revision/creation/mutation/participation evidence in
   existing order; validate original scalars and record types before sorting or
   comparing. Reject missing/crossed/orphan references. Load immutable admitted
   character revision, original native bindings and exact ownership proof.
3. Classify explicit lifecycle/mutation/namespace tuple. For completed 6,
   reconstruct the actual immutable revision-5 regional prefix using only its
   original first four mutation receipts, two roots, three visits, entry and
   actual position 5. Its historical position 4 remains derived by the unchanged
   S7-3 prefix path. Never feed completion evidence into the old exit decoder.
4. Validate all three Session identities, registry bundles, latest snapshots,
   initialization evidence, held-source events/memory and archive seal events/
   memory. Active jobs are current-read excluded for all ended sources under
   locks; an ENDED snapshot with a live job is integrity failure, not ineligible.
5. Require exact counts and new fifth receipt; recompute operation/fingerprint,
   completion ID, three source hashes and every event association. Re-evaluate
   rule facts and transition, bind timestamp/receipt/revision/current/historical
   binding/NULL active slot, and compare full constructed successor. Reject an
   old family with unexpected completion evidence or a completed family without
   it; checking a valid receipt in isolation is insufficient.
6. Only after full family validity may readers project history, perform exact
   replay comparison or test fresh eligibility. Every historical path shares
   this validation; no partial trusted View/summary on a corrupt neighbor.

Domain carriers/rule validation raise strict ValueError/validation errors; Run
row/receipt codecs own `RunStoredRecordIntegrityError`; native/world/completion
reconstruction owns `RunProtocolBindingStoredIntegrityError`; Session loaders
keep their current snapshot exceptions. Known stored-integrity errors map to
opaque 409 `SNAPSHOT_INVALID`. Catalog construction fails composition for
required missing/changed content; late mismatches are integrity errors. Unrelated
programming failures stay opaque 500, never a broad catch-and-fallback result.

For an intact owned family, lookup the exact scoped receipt before fresh checks:
changed fingerprint → `IDEMPOTENCY_CONFLICT`; matching receipt → immutable
completion result. With no receipt: terminal/noncurrent/wrong family/inactive
character → `RUN_COMPLETION_NOT_AVAILABLE`; then wrong expected versions →
`RUN_COMPLETION_STALE`; then unsettled/nonqualifying ending → unavailable.
Corrupt evidence precedes all these; request/job status never proves an ending.

## 7. Atomic operation, replay, concurrency and cleanup

One `RunCompletionService` owns one final native UoW/commit attempt. An ordinary
owned read may resolve the character lock target and full exact replay first;
it grants no authority that survives locked revalidation. Acquire existing
named lock `deviation_protocol:p33:s3:run_protocol_bindings:ddl_write:v1`, timeout
30, on the pinned physical connection. Lock current character first, then Run
current/history/participations/receipts/native bindings, roots/visits/position/
entry in existing deterministic order, then Sessions in visit order and their
snapshots/events/jobs. Preserve DB-001 current locking reads for mutable final
turn prerequisites; do not combine an earlier repeatable-read snapshot with a
newly locked ending. Do not add reverse Run write locks to turn paths.

Reauthorize/reconstruct, replay/conflict first, then new eligibility and versions.
Choose one trusted time only for a fresh eligible operation. Stage one revision
6, current CAS 5→6 and one successful completion receipt containing the complete
transition record. The current update historicalizes this Run's binding and
sets active_player_character_id NULL. Position remains byte-exact at revision 5;
all Sessions, roots, entries, events, memory and character rows remain unchanged.
Reconstruct the intended complete family before the sole commit. There is no
second completion writer, entitlement commit, reward ledger or post-commit fixup.
Project fixed notices only after leaving UoW/locks; no rendering or Provider call
inside this transaction. Demo stages the same receipts/revisions/current row in
its trial maps and validates the entire trial store before atomic publication.

| Competing or failed operation | Required outcome and subsequent assertion |
| --- | --- |
| Same completion key/intent | One commit plus identical immutable result replay, before/after reload, later admission or retirement; no clock read, identity issuance or new narrative rendering on known replay. |
| Same completion key, changed versions/path | Exact namespace/Run key resolves then fingerprint conflict, zero mutation. A foreign path stays opaque 404 before key disclosure. |
| Different completion keys | Exactly one completed 6; loser unavailable after reconstruction. Unique resulting-version constraint prevents a second record. |
| Completion vs archive exit | Exactly completed 6 with completion evidence OR terminated 6 with exit evidence. Loser unavailable; never both, no terminal conversion. Same textual keys in different namespaces do not alias. |
| Completion vs continuation/revisit | No common fresh eligible source: earlier paths fail current/family checks; exact old receipt replays unchanged. An obsolete operation cannot create visit four or move position. |
| Last seal turn vs completion | While unsettled, unavailable/stale with zero writes; if lock wait observes a committed ending, revalidate current snapshot/events/jobs and versions before deciding. A stale confirmation rejects and requires explicit fresh consent; no automatic retry. |
| Same-character admission/retirement | Character-first serialization: admission before completion sees active binding and rejects; after completion may admit once. Retirement retains its own eligibility rules. Old replay cannot free the new Run's slot or reactivate a retired character. |
| Stage/flush/CAS/known uniqueness error; precommit cancellation | Roll back revision/current/receipt and detached versions; keep qualified ending and binding intact. Propagate cancellation; classify only supported constraint names, not every 1062 as replay. |
| Commit acknowledgement loss, cancellation at commit or cleanup failure | Outcome unknown; no fabricated rollback/success, retry loop, compensation or reconnect-and-continue. Keep original identity for safe GET or explicit exact retry. |

UoW failure handling retains physical owner until release/disposal is proved;
preserve primary error plus cleanup evidence. Invalidation failure must still
prevent pool reuse and close physical owner/wrappers. A release returning 0,
NULL, invalid type, disconnect or exception is not successful cleanup. The
API exposes `RUN_COMPLETION_OUTCOME_UNKNOWN` when commit/cleanup is uncertain,
409 conflict for supported precommit lock/write conflicts. No returned success
is invented after unsafe cleanup. Rendering outside locks remains independently
instrumented even though this operation uses fixed prose and zero Providers.

## 8. Minimal migration derived from source head

Actual source head is `20260918_0010` (parent `20260918_0009`); this task did
not inspect or assume a database head. Add only
`alembic/versions/20260920_0011_native_run_completion.py`, revision
`20260920_0011`, down_revision `20260918_0010`. Never edit older migrations.

Three current CHECKs require amendment: `ck_run_revisions_mutation_matrix`,
`ck_run_current_mutation_matrix`, `ck_run_mutation_receipts_protocol_matrix`.
Lifecycle/result vocabulary and lifecycle-binding CHECKs already include
completed; evidence is already non-null MEDIUMBLOB, receipt payload allows
1..65,536 bytes, and existing exact revision FK/unique result version suffice.
No new table, column, FK, index, nullability or world-position CHECK is needed.
An arbitrary completed enum value still does not satisfy the old mutation matrix.

Append exactly one branch to revision/current mutation matrices, leaving every
old branch unchanged: kind COMPLETE_REVISITED_NATIVE_RUN, prior IS NOT NULL
and =5, state_version=6, lifecycle completed; all eight binding members required
by the terminal branch explicitly non-NULL (including binding_state), binding
state historical, inactivated_at=occurred_at, occurred_at≥bound_at. Current
additionally requires active_player_character_id IS NULL. Do not rely on SQL
UNKNOWN to enforce presence. Application reconstruction additionally checks
monotonic previous mutation time and exact immutable reference/provenance.

Receipt branch requires exact new namespace/kind/result schema, expected=5,
resulting=6, resulting_lifecycle_status=completed; all three participation result
columns and all three character-result columns NULL. Existing result Run/line
FK (`fk_run_mutation_receipts_revision`), receipt key and
`uq_run_mutation_receipts_result` remain unchanged. Evidence owns the source
Session/visit association and is validated against existing reverse joins; no
new SQL FK can express the whole canonical evidence graph. ORM metadata must
match exact deployed constraints. Upgrade preserves every old row byte.

Both directions acquire the same pinned named lock before exact head/schema/
constraint/enforcement preflight. Upgrade replaces the three CHECKs in revision,
current, receipt order. Downgrade first uses current locking reads on all three
tables, probing **any** completed lifecycle, new mutation kind, namespace or
result schema, and completion evidence schema (including canonical bytes whose
discriminators disagree). Any complete or partial new evidence refuses before
DDL. A genuine old terminated 6 remains allowed; revision 6 alone is not a
refusal predicate. Malformed/unknown schema or unclassifiable evidence refuses
for operator inspection. If clear, restore receipt/current/revision CHECKs in
reverse order to exact 010 definitions. Never delete, rewrite or revive rows.

Use the existing statement-durable migration pattern: exact before/after stage
and completed-constraint prefix, strict lock acquire/release outcomes, primary
error precedence and physical-owner disposal. Test loss before/after each of
the three ALTERs in both directions and failure during final preflight/release;
no claimed transactional DDL rollback, automatic repair or continued DDL after
loss. Writers need verified complete 011 schema and compatible readers; no mixed
old reader deployment after new completion rows. Historical fixtures continue
to name their actual old heads. Changed 011 authority/migration behavior needs
fresh real-MySQL proof even if unchanged 007–010 internals have reusable records.

## 9. API, Demo and Web contracts

Add GET `/v1/sessions/{session_id}/run-completion` (operation
`get_native_run_completion`) and POST `/v1/sessions/{session_id}/run-complete`
(`complete_native_run`). GET rejects body/query; POST uses the existing strict
Idempotency-Key/header/content-type/duplicate-member transport and exactly
`{expected_run_state_version,expected_session_state_version}`, ≤1,024 bytes,
no query. No client-supplied eligibility, destination or approval Boolean.
Production and deterministic Demo install identical services/routes. Dynamic
Demo and standalone/legacy Sessions gain no completion authority.

### Exact public allowlists

GET 200 `native-run-completion-status/v1` has exactly:

```text
schema_version, session_id, run_id, run_state_version, lifecycle_status,
run_context, path, current, can_complete, reason, offer, completion
```

Path/current use existing complete VisitAssociation (Session/version/scenario/
content/six-field visit). Original native context is unchanged.
`can_complete=true` iff active5/current archive ENDED qualifies and current
character active. `reason` is exactly one of `eligible`, `run_terminal`,
`not_current_visit`, `character_ineligible`, `session_not_ended`,
`ending_not_eligible`, `route_not_eligible`. After full integrity validation,
reason priority is terminal → noncurrent → inactive character → unsupported
active family → unsettled → wrong ending → eligible. GET never consumes a key,
inserts evidence or changes eligibility. Valid legacy/standalone returns 409
NATIVE_RUN_REQUIRED, not a forged native result.

`offer` is required nullable; non-null exactly when can_complete, with exactly
`title="完成本次旅程：保留待核事项"` and
`notice="封存待核记录已确认；可以将本次旅程以待核事项保留结案。发运暂缓继续有效，送达仍未得到证明。"`.
This is preview text, explicitly labelled as pending confirmation.

`completion` is required nullable; non-null exactly for completed6, on every
authorized path. Its exact fields are `completion_id`,
`outcome="unresolved_record_preserved"`,
`title="待核事项保留，核验旅程已结案"`,
`notice="本次旅程已正常完成。发运暂缓继续有效，送达仍未得到证明；旧记录与资源保持原状。"`,
`canon_outcome={dispatch:"held",delivery:"unproven",record:"sealed",verification:"closed_unresolved"}`.
These strings and closed values are server-authored allowlist constants for
receipt-archive-closure/v1; no internal rule IDs, evidence hashes, event payloads,
snapshots, line IDs, source references or Provider text are projected.

POST 200 `native-run-completion-result/v1` has exactly `schema_version,
source_session_id, source_session_state_version, run_id,
resulting_run_state_version` (6), `lifecycle_status` (completed), `run_context`,
`visit` (exact third visit), `completion` (non-null object above). It is an
immutable outcome association, not a mutable View. Exact replay returns that
same result after admission/retirement. The original archive View is unchanged.

Old `native-run-status/v1` and `native-run-journey/v1` meanings and response bytes
remain unchanged for all old families. At their existing GET routes a completed
family returns a **separate discriminated v2 branch**: `native-run-status/v2`
has the old field set, literal completed, revision6, can_exit=false;
`native-run-journey/v2` has the old field set plus required non-null `completion`,
literal completed/revision6, current ordinal3 and next_transition=null. Its
neighbors/arrival keep the exact old path semantics. v2 is completed-only; v1
never starts accepting completed. OpenAPI and both client decoders express
these explicit unions. Old two-visit continuation GET remains unavailable for
all three-visit families, including completed; old continuation/revisit POSTs
still replay their original results. No mixed old client support is promised.

Errors: 404 missing/foreign; 422 strict transport; 409 NATIVE_RUN_REQUIRED,
SNAPSHOT_INVALID, IDEMPOTENCY_CONFLICT, RUN_COMPLETION_NOT_AVAILABLE,
RUN_COMPLETION_STALE or RUN_COMPLETION_CONFLICT as owned above; 503
RUN_COMPLETION_NOT_AVAILABLE for absent service and
RUN_COMPLETION_OUTCOME_UNKNOWN for commit uncertainty; unrelated 500 opaque.
Declare each real status using existing ErrorResponse in OpenAPI, no framework
validation-body substitute or unsupported 202. Public scans cover values as
well as keys. An ending is still not canonical character death.

### Supported state combinations and one client authority rule

| Run / path state | Supported public state and write affordance |
| --- | --- |
| active3/current ACTIVE or ENDED | v1 Journey/status, can_complete=false and completion=null; existing action or ending continuation/exit rules. |
| active4/current ACTIVE or ENDED | v1, can_complete=false and completion=null; existing action or held revisit/exit. |
| active5/current archive ACTIVE | v1, can_complete=false and completion=null; normal actions only through existing validated Journey. |
| active5/current archive sealed ENDED | v1, can_complete=true and completion=null; completion and exit alternatives, no action/new visit. |
| active5/current archive deferred ENDED | v1, can_complete=false and completion=null; exit only. |
| active Run / older ended path | v1, read-only; can_complete/can_exit false and no continuation/revisit for that path even if current visit qualifies. |
| terminated4/5/6 / any owned ended path | v1, completion=null, all fresh Run writes disabled; historical reads/exact old replay only. |
| completed6 / any owned ended path | v2 Journey/status plus matching completion status/result; same current third visit, history and return-to-setup only. |

Terminal Run with ACTIVE View, completed without third visit/record, completed
with can_exit or next_transition, identical revision with contradictory lifecycle,
or a wrong source/current/neighbor/context association is invalid. Do not accept
arbitrary later revisions. Compatible progress after retained continuation or
revisit POST is only one of these explicitly supported descendant families.

One shared association/lifecycle validator in `web/src/runJourney.ts` plus
`runCompletion.ts` must serve explicit load/recovery, automatic synchronization,
button enablement, confirmation creation and confirmation-to-submit. Bind View,
Journey, Run-status and completion status to the same client/generation/Run/
path/current and complete immutable native context. Current active action flow
keeps its existing Journey-only gate; new completed descendants are never active.
For ended-current mutation controls, require all fetched authorities to agree;
pending/mismatched responses disable every affected write, including previously
opened completion/exit confirmations. Preserve readable old text separately.
GET reconciliation may establish a later consistent supported state but cannot
rewrite a received response or consume a retained uncertain command.

Freeze URL/path, Run association, exact body bytes, operation key, source View
and complete authority tuple on confirmation. Before first submission rerun the
same consistency rule against current refs; stale/client-replaced/history/pending
state dispatches zero POST. Cancel before submit creates no durable operation.
One confirmed click sends one POST. While pending/uncertain, disable competing
completion/exit/actions/admission; explicit exact retry uses frozen identity,
even when a GET shows completed. Changed intent requires a new explicit operation,
never silent key replacement. Do not auto-replay on mount, reload, focus or GET.

Retain every confirmed POST's immutable association as authority. Completion
result must match confirmed Run, source Session/version/content/third visit and
context; matching GET must preserve its completion ID/outcome and terminal6.
For prior continuation/revisit confirmation, completion is an allowed exact
descendant, not a reason to adopt a different target. A separately fetched
schema-valid contradiction disables writes and permits safe GET without
overwriting expected identity, clearing the request or fabricating success.
Late response protection applies to all four reads and mutations.

Storage v1 stays Session-only; completion introduces no new Session and neither
sets nor removes storage. Preserve existing admission/transition storage-before-
first-View rule. Reload fetches current Session and validated Journey/status/
completion by GET. History 3→2→1→2→3 is GET-only with zero storage set/remove;
current recovery identity is separate from displayed history, so refreshing a
historical page restores current third visit. Confirmed completion plus matching
GET enables explicit **返回设置**; only that action clears the record. Failed
removal blocks admission until explicit clear succeeds. Fresh discovery requires
explicit selections and confirmation; no automatic admission. Keep DF-002's
backend-ready → explicit missing-Session clear → full reload containment, with
confirmation disabled until discovery succeeds. Demo restart remains 404 and
explicit clear, never replay of any old write.

## 10. Future implementation dependency inventory

These are concrete future paths/reasons, not edits authorized now. Source
prefixes below are relative to `src/deviation_protocol/`; test/web/config paths
are repository-relative. Record a discovered necessary dependency before editing
it during implementation; no arbitrary path-count budget or general framework.

| Paths | Required change and preservation responsibility |
| --- | --- |
| `domain/run_completion.py` (new), `domain/run.py`, `domain/run_protocol_binding.py` | Strict singleton rule, evidence codecs/transition, completed family, exact participation/binding invariants; no generic terminal widening. |
| `application/run_completion_service.py` (new), `application/run_operations.py`, `application/ports.py` | Single UoW owner, receipt namespace/result, closed classifier unions and required event-read contract. Completion record reuses mutation receipt port; no new store. |
| `infrastructure/run_completion_persistence.py` (new), `infrastructure/run_persistence.py`, `infrastructure/run_protocol_binding_persistence.py`, `infrastructure/world_revisit_persistence.py` | Strict row/evidence decoding, immutable revision-5 prefix then new suffix, old historical binding comparison and exact namespace dispatch. |
| `infrastructure/repositories.py`, `infrastructure/demo_persistence.py` | Fetch archive events/jobs for completed suffix, reverse/orphan checks; encode completion evidence into existing receipt maps; trial-store reconstruction/snapshot/restore/export parity. |
| `infrastructure/orm_models.py`, `alembic/versions/20260920_0011_native_run_completion.py` (new) | Three CHECK branches only, exact metadata/preflight/refusal/failure behavior. Older migration bytes protected. |
| `application/native_run_admission.py`, `application/run_exit_service.py`, `application/run_continuation_service.py`, `application/run_revisit_service.py` | Historical admission/exit/continuation/revisit replay recognizes new family through original prefix; no fresh operation on completed. Journey/status explicit v2 projection. |
| `application/native_turn_mechanics.py`, `application/world_visit_context.py` | Completed historical load unwraps exact regional/continued/admission prefix; fresh bind still rejects terminal; old action/job/context replay retains meaning. No new prompt schema. |
| `api/run_completion_routes.py` (new), `api/schemas.py`, `api/main.py`, `api/dependencies.py`, `api/demo_composition.py` | New routes/closed DTOs/OpenAPI, compatible production/Demo composition and source reference. No Live/provider branch. |
| `web/src/runCompletion.ts` (new), `web/src/runJourney.ts`, `web/src/runExit.ts`, `web/src/api/client.ts`, `web/src/api/schemas.ts`, `web/src/App.tsx` | Shared complete authority checks, fixed confirmation/result/history/recovery controls and explicit v1/v2 unions; no UI redesign. |
| `tests/unit/test_run_completion.py`, `test_run_completion_service.py`, `test_run_completion_persistence.py`, `test_run_completion_api.py` (new under tests/unit) | Literal codec/provenance/rule/failure/replay and API goldens; each mutation and fixed integration regression covered. |
| `tests/unit/test_run.py`, `test_run_operations.py`, `test_run_persistence.py`, `test_run_protocol_binding.py`, `test_run_protocol_binding_persistence.py`, `test_run_repositories.py`, `test_run_exit_service.py`, `test_run_continuation_service.py`, `test_run_revisit_service.py`, `test_native_run_admission.py`, `test_native_turn_mechanics.py`, `test_world_revisit_persistence.py`, `test_world_visit_context.py` | Closed-family/old-replay/query inventory and historical/fresh authority regressions. |
| `tests/unit/test_demo_persistence.py`, `test_demo_composition.py`, `test_native_demo.py`, `test_api.py`, `test_player_character_api.py`, `test_run_composition.py` | Update exact route/schema/store/family assertions; the binding integration owner is listed below. |
| `tests/integration/test_mysql_native_run_completion.py`, `test_mysql_native_run_completion_migration.py` (new) | Fresh real-MySQL public journey, atomicity, race, integrity and 011 migration evidence. |
| `tests/integration/test_mysql_native_run_admission.py`, `test_mysql_native_run_exit.py`, `test_mysql_native_turn_mechanics.py`, `test_mysql_world_continuation.py`, `test_mysql_world_revisit.py`, `test_mysql_player_character_run_binding.py`, `test_mysql_run.py`, `test_mysql_player_character.py`, `conftest.py` | Affected old-family replay/current-head fixtures/binding and schema owners; preserve historical-head fixture scopes. |
| `tests/e2e/test_native_run_completion.py` (new), `tests/e2e/support/native_world_continuation_child.py`, `tests/e2e/test_native_world_revisit.py` | Fresh public-play and cross-process completion trace, receipt/store export including closure evidence; preserve old exit journeys. |
| `web/src/runCompletion.test.ts`, `web/src/App.completion.test.tsx` (new), `web/src/runJourney.test.ts`, `web/src/runExit.test.ts`, `web/src/App.journey.test.tsx`, `web/src/App.continuation.test.tsx`, `web/src/App.recovery.test.tsx`, `web/src/api/client.test.ts`, `web/src/test/fixtures.ts`, `web/src/test/server.ts` | Rendered reachability, independent schema-valid contradictions, automatic-sync/submission races and old replay/recovery controls; real Demo transport cases separate from mocked faults. |
| This plan, `PLANS.md`, `docs/run_protocol.md`, `docs/architecture.md`, `docs/public_client_contract.md` | Same-round implementation/evidence/status synchronization; frozen predecessor plans and historical reports remain protected. |

Read-only dependency checks also cover `session_service.py`,
`narrative_turn_orchestrator.py`, `player_character_operations.py`,
`infrastructure/unit_of_work.py`, `native_demo.py`, `player_character_persistence.py`
and `web/src/sessionRecovery.ts`: their transaction, ownership, renderer and
storage contracts are retained. Edit only if a concrete new-family consumer
requires it, explaining that dependency first. Existing scenario packs,
registry digests, balance/mechanics, migrations 001–010, dependencies, workflow,
guardrails and DF register are not prospective feature targets.

## 11. Executable acceptance and evidence responsibilities

This is required future implementation evidence, not results from this task.
Each test records exact inputs, owning boundary, expected result/error, write
delta and subsequent full reconstruction. API journeys obtain states through
real public actions; synthetic corruption/resource fixtures are separately
labelled and never evidence of gameplay reachability. No real Provider is needed.

| ID / owner | Setup and execution | Expected result, mutation and subsequent assertion |
| --- | --- | --- |
| A01 Public API + deterministic Demo + real MySQL | Explicit character/native admission; first-world canonical 19-action RESOLVED path and legitimate FAILED path; second OBSERVE/TALK/hold; revisit; archive OBSERVE/seal; GET offer; explicit completion. Cover all three profiles with actual achievable source ending, plus both ending classes across the corpus. | Reach completed6 through normal routes, fixed closure text/canon_outcome, one receipt; unchanged three snapshots/full PlayerState/roots/entry/position/character and closed binding. No injected ending. GET from all visits reconstructs same completion. |
| A02 Rule/API negatives | Original RESOLVED/FAILED; second held/dispatch-closed/deadline; archive ACTIVE/deferred; valid historical source path; retired/ineligible character in labelled synthetic fixture. Submit completion with new key. | GET false/reason or existing owning eligibility error; POST unavailable (stale only under section 6 precedence); zero write delta. Current correct route remains playable or exit eligible. Both source RESOLVED titles stay accepted by old prefix. |
| A03 Canon/event/codec integrity | Start a qualified public journey; independently remove/alter each source hash, ID, version, held/seal event, applied event, decision/action, memory link, fixed/mutable fact, ownership/reference, prefix/receipt/position; inject unsupported versions/partial rows/extra record. Include alias/coercion/duplicate JSON and same-version content substitution. | Known owning integrity error/opaque SNAPSHOT_INVALID from every owned path before eligibility/replay, zero trusted partial projection/writes, untouched control Run remains valid. Independent literal bytes/hash and reordered-input/locale/hash-seed controls. |
| A04 Normal completion versus exit | On separate identical qualified Runs choose completion, exit, cancel, and do nothing. Also exercise archive defer→exit. | Only completion has completed6 and canon closure; exit terminated6 with old evidence; cancel/no consent retains active5 and active binding. Neither outcome grants reward or revives; normal completion cannot be inferred from RESOLVED or empty pool. |
| A05 Carryover and binding | Public profiles exercise actual resource costs; separate valid resource-only fixtures include zero composure and supported inventory/skills/wallet/cooldown values. Complete; later explicitly admit same character and perform first action; later retire where allowed. | Completion changes no resource/character bytes, no duplicate reward/event; release only old Run slot. New Run/line distinct, old history and exact replay stay valid after later admission/retirement. Do not claim synthetic item reachability. |
| A06 Full old/new replay | Save admission, all prior action/continuation/revisit and completion/exit receipts; replay original identities after completion and after later admission/retirement. Changed-intent same key, changed path, competing new key. Include original active3/terminal4, active4/terminal5, active5/terminal6 controls. | Old safe responses remain exact; completion result exact; changed intent conflict; new terminal operations unavailable. No clock/issuer/renderer/state change on replay. Counts and historical character reference remain exact. |
| A07 Real MySQL atomicity/uncertainty | Inject failures after revision append/current CAS/receipt flush/reconstruction/before commit; cancellation; actual CAS loss/known unique conflict; commit acknowledgement loss and cleanup failure. | Precommit total rollback and retryable untouched qualification; ambiguous commit flagged unknown with exact GET/retry resolution, at most one complete family. Verify physical connection identity, release/disposal/no unsafe pool reuse with independent observer. |
| A08 Real MySQL races | Same/different keys; complete vs exit; obsolete continuation/revisit vs complete; last-turn lock wait from a prior consistent snapshot; same-character admission/retirement. Use barriers and observed locks, not sleeps as proof. | Exactly one permitted winner, defined loser/error and intact family; current-read job/ending validation, no deadlock from reverse Run locks, no release of later Run binding. Explicit retry only after stale finalization. |
| A09 Migration 011 | Empty/populated actual010→011→010 with old legacy/native and original/continued/revisited terminals; exact ORM/CHECK/FK metadata. Every nullable terminal prerequisite set NULL independently; each completed/partial-evidence probe; writer-vs-downgrade and stale reader; failure before/after each ALTER both ways. | Old bytes exact; named CHECK rejects invalid new branch with rollback; completed/partial rows refuse downgrade before DDL while old terminated6 permits it. Exact partial-prefix/physical-owner evidence on failure; restore observed initial DB schema/rows/lock state, never assume source head. |
| A10 Rendered Web + actual deterministic Demo transport | Play both source classes to archive seal, preview/cancel/confirm, completed reload, 3→2→1→2→3 history, historical refresh, explicit setup clear/new admission/first action; preserve defer→exit route. | Zero POST on cancel/history/reload, zero history storage writes, current third visit restored, durable completion text and unchanged old ending Views. No action/exit/revisit after complete; storage removal failure blocks setup/admission. Prior transition storage-before-View preserved. |
| A11 Web association/races | Inject individually schema-valid mismatches across View/Journey/status/completion and retained POST: same-version active5/terminal5; completed6/terminated6; wrong source/current/visit/content/context/completion ID; ACTIVE View with terminal; both read orders; automatic sync, open-confirmation→submit, client replacement, late result. | One shared validator disables affected writes and dispatches zero POST; retain receipt/request/storage; safe GET matching control including legitimate progressed old transition restores only allowed state. Uncertain exact retry remains explicit. No self-authorizing received View/GET. |
| A12 Cross-process and recovery | Same scripted public journeys in fresh deterministic processes under distinct PYTHONHASHSEED; export complete maps, trace and completion evidence. Separate restart loses process store; old Session GET404 then explicit clear/full discovery reload. | Canonical evidence/traces match under deterministic test clock/IDs; one closure/no hidden writes. Restart performs GET only and never replays admission/action/completion. Browser storage internals are asserted in rendered instrumentation, not claimed from screenshots. |

Implementation owner supplies A01–A12 manifests with command/exit/raw-log/source
identities and negative/overlap accounting. Focused unit/API/rendered tests and
affected old replay suites run fresh; changed persistence, current-read lock
behavior and migration require real MySQL 8/asyncmy restricted to
`deviation_protocol_test` under separately authorized implementation verification.
Record actual initial schema/rows/lock state and restore it after tests.
Compilation and Alembic heads/history/metadata checks apply to changed code and
migration; use canonical Offline for no-DB checks and the repository's MySQL
entry point for DB proof. Web typecheck/lint/build and complete affected rendered
suites are relevant to the shared client gates. Expand testing only on affected
dependencies or new failures; no broad Full rerun prescribed without a requirement.

Unchanged exhaustive S2 and historical migration internals may be reused only
with locatable command/raw-log/result/source/dependency/environment records and
an explicit applicability comparison. S7-3 references its accepted evidence in
[the existing evidence map](run_protocol.md#s7-3-implementation-candidate-evidence);
presence of a summary alone is not new proof. Missing or inapplicable required
evidence must be obtained in the later authorized verification task. Changed
completion/011 boundaries cannot be satisfied by old S7-3 browser or MySQL counts.
Browser acceptance remains separately authorized; this plan neither runs it nor
adds it as an unapproved execution. S7-5 owns final parent acceptance reconciliation.

## 12. Documentation scope, review and handoff

This candidate changes exactly this new plan plus `PLANS.md`,
`docs/architecture.md`, `docs/run_protocol.md`, `docs/public_client_contract.md`.
The published S7-3 status and inspected bounded browser evidence are synchronized
in this same task; historical reviews and frozen plans are not rewritten.
No code/content/test/migration/dependency/workflow/guardrail/DF edit, staging,
commit, push, tests, database, application/browser run, Provider or subagent is
authorized. Documentation validation only: complete final files/diff including
new file, status/ownership/links, UTF-8/LF/final newline, whitespace/modes, exact
scope, all protected tracked hashes and index/refs/operation state.

External reviewer package contains baseline, five-path inventory, raw bytes/
SHA-256/Git blobs/modes, complete binary/full-index patch including new file,
patch byte count/line changes/SHA-256, consolidated P01–P09, implementation
dependencies, A01–A12 ownership, validation report and final Git state. Hashes
stay outside hashed files. Any byte change invalidates the candidate identity
and its approval; relevant baseline change requires reassessment before review.

Exactly one operative **plan-review success token**, specified for the future
independent reviewer and **not issued by this authoring task**:

`PHASE_3_3_S7_4_CANON_PRESERVING_LINE_TRANSITION_RUN_COMPLETION_PLAN_INDEPENDENT_REVIEW_APPROVED`

APPROVED and APPROVED_WITH_DEFERRED_FINDINGS both emit that exact token and bind
all five files/hashes. Review must state product-decision disposition; technical
approval does not substitute for the user's P01–P09 approval. CHANGES_REQUIRED,
historical tokens, partial review and authoring labels cannot satisfy the gate.
Keep one substantive independent plan review and focused correction review of
concrete findings/direct dependencies; no additional approval/closeout stages.

Sole **dormant, non-operative implementation-review token**:

`PHASE_3_3_S7_4_CANON_PRESERVING_LINE_TRANSITION_RUN_COMPLETION_IMPLEMENTATION_INDEPENDENT_REVIEW_APPROVED`

It becomes operative only after plan review, explicit product acceptance,
separately authorized local documentation commit, manual user publication,
confirmed clean aligned implementation baseline and separately authorized
implementation. That later review binds the complete implementation and required
fresh/applicable A01–A12 evidence. This task issues neither token. No separate
post-commit independent audit is required. Next is the independent plan review;
S7, Phase 3.3, real Provider acceptance and broader-release readiness stay open.

## Guardrail impact

None. Existing rules govern this proposal; no confirmed new defect or reusable
rule is asserted. DF-001/DF-002 retain their recorded owners, containment and
reassessment milestones; do not create speculative deferred findings.
