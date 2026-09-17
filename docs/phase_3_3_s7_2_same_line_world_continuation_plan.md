# P3.3-S7-2 — First same-line authored-world continuation

Status: **Corrected documentation plan candidate, awaiting focused independent
re-review and explicit user approval of the product decisions in section 3.
Not approved, frozen, published or implementation authorization.** All new
identifiers, content, balance and technical extensions below are proposed for
freeze. Authoring this recommendation does not approve it.

The incoming candidate received **CHANGES_REQUIRED**: one blocking predecessor-
navigation finding and one non-blocking ending-priority contradiction. After
reload, successor-only storage v1 could not locate the preceding Session; the
declared deadline priority also contradicted the ascending selector. This bounded
correction addresses those contracts and their acceptance cases in sections 3,
8–11. The complete independent review was supplied in the user's message and
read; no external review file is required. Earlier conclusions for unchanged
content are preserved. This correction is not a passing review or product approval.

## 1. Baseline, authority and demonstrated predecessor

Initial plan authoring verified locally without fetch: branch `main`; HEAD,
local `main` and local `origin/main` are
`41d68aac13ca9129b7f6e08fad5f015987603fda`, subject
`feat: implement P3.3-S7-1 post-ending Run exit`, parent
`9fab18d8de4ba05000e38ee37fa6a2e8da17940a`; ahead/behind 0/0; initially clean
worktree/index, no conflicts, operations or locks. No runtime, database,
browser, Provider, installation or network verification is part of this task.
Correction preflight reconfirmed those refs and the exact incoming five-document
candidate against its preserved snapshot/patch, with empty index and no conflicts,
operations or locks. The worktree contains that candidate, not a clean checkout.

The [parent plan](phase_3_3_run_protocol_implementation_plan.md) and the
[published S7 allocation](phase_3_3_s7_1_post_ending_run_exit_plan.md#2-remaining-s7-allocation-in-dependency-order)
remain controlling. Apply the current
[playable-delivery workflow](engineering/codex_workflow.md), including its
risk-based disposition and evidence-reuse rules, without rewriting frozen
plans or historical verdicts. The [Run product authority](run_protocol.md),
[architecture](architecture.md), [public contract](public_client_contract.md)
and [roadmap](../PLANS.md) retain their respective ownership.

S7-1 implementation is published at this baseline. Its first implementation
review's `CHANGES_REQUIRED` nullable terminal-CHECK finding and correction
remain history. The actual external browser report was read at
`C:/Users/dylanmonster/AppData/Local/Temp/deviation-p33-s7-1-browser-20260918/acceptance-report.md`.
It records both authored ending classes, explicit exit/cancel, return to setup,
same-character fresh admission and first action, refresh/history recovery, and
backend restart followed by old-Session 404 with only GETs. It records five
focused Offline passes plus compilation/dependency/metadata checks, stopped
owned services, released ports, unchanged repository and no database/real
Provider access. These are inspected prior report results, not tests rerun by
this planning task. Its limited instrumentation and absent uncertainty/storage
fault browser cases remain explicit in the
[current evidence record](run_protocol.md#s7-1-publication-and-local-browser-evidence).
Neither this report nor S7-1 publication completes S7 or Phase 3.3.

## 2. Playable increment and actual dependencies

Deliver: actual public play ends the current authored world -> the owner
explicitly confirms **继续本次旅程** -> the engine commits one eligible next
world in the same Run/line -> the player performs its first legitimate action
-> reload recovers that same committed continuation. The new destination must
also have playable authored endings, even though the first milestone stops
after its first action/reload. **结束本次旅程** remains a separate irreversible
choice; its success releases the character for a separately confirmed new
Run. An already terminated Run can never continue.

Inspection establishes the following minimum dependencies; they are not
interfaces assumed to exist already:

| Existing boundary | Consequence for this slice |
| --- | --- |
| `domain/entry_world.py` has only `world.death_certificate@1`, scenario `death_certificate`, pack `death-certificate-1.1.0`. | Author one genuinely different continuation-only world; preserve the old pack and entry catalogue. Test fixtures are not approved production destinations. |
| `CanonicalRun`, `NativeRunAdmissionV1`, SQL/Demo classifiers and exit require the exact 3-active / 4-terminated family. | Add closed continuation families and update every direct consumer; do not loosen admission to arbitrary revisions. |
| `run_entry_world_bindings` and protocol bindings freeze revision 3; participation is keyed by Session and joined revision. | Retain those originals; add a second participation and distinct world/visit/region authority with an explicit current position. |
| `SessionService`, turn orchestration and `ScenarioCatalog` use one content version; `GameState.from_snapshot` checks that exact catalogue. | A preloaded registry and owned Session routing to version-specific service bundles are required for both historical and new Sessions. Do not relabel old content or merge packs under an old version. |
| `GameState.validate_player_memory_against` requires each memory record to have the snapshot's own participating runtime. | Keep local memory local. Preserve old memory/history through its owned Session and a trusted visit link; do not copy old records into the new runtime or weaken this validator. |
| Native turn binding fixes Run revision 3, entry world and one participation; prompt context v1 carries mechanics/presentation only. | Add a distinct visit-turn evidence envelope and a separate bounded trusted visit-context attachment. Old job/prompt evidence retains its meaning. |
| Web `assertViewAssociation` checks Session, scenario/content and the complete immutable admission context; storage v1 contains Session identity only. | A validated continuation result must establish a new Session association before storage/View. Recovery from the old Session needs a GET link to the committed successor; successor reload needs the trusted predecessor association defined in section 8 for historical navigation. |
| Demo publishes a fully validated trial store atomically; native renderer has a task-bound capability. | Extend its maps/classifier and content routing, preserving the same transition and renderer guard. No UI-only handoff. |

All `domain/`, `application/`, `infrastructure/` and `api/` source paths in this
plan are relative to `src/deviation_protocol/` unless written in full.

## 3. Product decisions for approval together

These are genuine pending decisions, not approved defaults. The user should
approve or revise this table as one coherent proposal alongside the independent
plan review. A changed decision requires corresponding contract, evidence and
candidate rebinding; do not implement an unapproved alternative.

| Decision | Recommended value | Reason | Gameplay consequence |
| --- | --- | --- | --- |
| P01 — destination | New `world.undelivered_receipt@1`, title **未送达的回执**, scenario `undelivered_receipt`, content `undelivered-receipt-1.0.0`; continuation-only. | Uses existing signed-record, audit and evidence-versus-automatic-procedure concepts in a distinct dispatch setting. | One new world, not another hospital Session, reskin, revisit or public entry choice. |
| P02 — source eligibility | Both RESOLVED IDs `death_certificate.ending.protocol_broken` and `.record_challenged`, and FAILED `.deadline_reached`, at exact source world/content version; active owned character and Run required. | Ending classification alone is not canonical death authority; no approved character-death transition exists here. | Failure preserves the failed outcome and can continue. Termination, unsupported endings and active Sessions cannot. |
| P03 — entry consequence | RESOLVED starts destination `dispatch_deadline` at 0; FAILED at 4; maximum 40. Display the actual source ending title/class and a fixed, outcome-specific arrival notice. | Meaningful bounded pressure difference without editing past facts or inventing resurrection. | Failure gives less time; both paths can perform the first action and finish successfully at every supported profile. |
| P04 — carryover | Same Structured Player Character reference, full current `PlayerState`, including remaining composure, attributes, inventory instance state, wallet and skill/cooldown values; no refill, fee, reward or character revision. | The journey continues; a new Session must not reset resources or become a farming route. | Even zero composure may continue; existing saturating S5 rules keep legitimate actions available. |
| P05 — local reset and memory | Fresh destination runtime/NPC instances, clocks except P03, local event/job/action numbering and local scenario memory. Old facts, NPC state, memory and accepted prose remain in the immutable old Session, accessible as linked history. | Current memory validates one participating runtime; no cross-scenario NPC authority exists. | Previous outcomes affect entry through a closed authored rule, not copied NPC relationships or hidden knowledge. |
| P06 — selection | One required successor edge, integer weight 1, deterministic seed/evidence below; no random draw. Exclude visited worlds; no third destination. | Implements required progression and reproducibility without unnecessary randomness or a general catalogue. | Player confirms continuation of the journey, not a world selection. Empty pool offers history/exit, never replacement admission. |
| P07 — playable structure/endings | Two evidence actions, then an explicit hold/release dispatch decision; held receipt is RESOLVED, release/deadline is FAILED. No rewards or unlocks beyond this scenario. | Gives a complete, bounded investigation with meaningful consequences using existing policies. | Both outcomes are final for this visit; second ending offers history and S7-1-style explicit exit, but no third world/revisit/normal Run completion. |
| P08 — recovery/navigation | Confirmed continuation opens the new Session after durable local recovery storage; old history remains navigable and GET can recover its committed successor. Keep Session storage v1. | Covers lost response/reload without durable browser mutation authority. | Storage failure blocks new actions/admission; retry stores/reads only. No automatic POST on reload. |

### Authored content sufficient for implementation

This is new proposed canon, not a claim that the destination is already authored.
The setting is a dispatch hall in a distinct authored world: an automatic
schedule treats a missing delivery receipt as completed delivery. The player
must secure an independently checked hold before a disputed dispatch closes.
The link to the first world is the character's carried experience and recorded
outcome, not a claim that the hospital and dispatch hall are one world, that
the first ending was false, or that an old NPC has followed the player.

Source FAILED prose says the procedure completed its predicted result. The
new entry must quote/preserve that outcome without asserting survival in that
facility, undoing it, or explaining a revival. Its minimum new assertion is
that this still-active character's journey now enters another world. If product
review intends the old ending to establish final character death, that conflicts
with P02 and existing lifecycle evidence: resolve P02 explicitly before freeze;
do not silently rewrite the old pack or add a revival mechanic.

Proposed region identities are `region.death_certificate.facility@1` (the
existing visit's authored scope, not a renamed location) and
`region.undelivered_receipt.dispatch_hall@1`. The destination has two locations,
`undelivered_receipt.receiving_desk` and `.dispatch_counter`, one new local NPC
`npc.undelivered_receipt.dispatch_clerk`, and four phases: `.arrival`,
`.verification`, `.dispatch_decision`, `.resolution`. Reuse the unchanged
investigator mechanical definition and composure resource in the new pack;
the definition ID denotes a template, not world or NPC identity. Copy required
item definitions byte-equivalently for carried inventory validation, not new
instances or grants. No NPC template is a cross-world identity predicate.

Required fixed facts: the receipt is absent; the schedule currently marks the
dispatch complete; a countersigned hold prevents this dispatch; a hold does
not establish whether delivery occurred. Mutable `dispatch_held` starts false
and can become true only from the authored hold decision's trusted event.
No new global law about records creating all reality is inferred from either
world. Initial entry annotation reports only the prior public ending and P03's
queue urgency. Hidden first-world facts never become destination knowledge.

1. Arrival exposes OBSERVE at the receiving desk. Its bound server rule returns
   SUCCESS, reveals `receipt_gap`, advances the clock with base 1, and opens the
   counter/verification phase. Free text is intent; location/action/runtime
   qualify the rule. This is the required first legitimate public action.
2. At verification, TALK to the visible new clerk returns SUCCESS and reveals
   `dispatch_schedule` with base clock cost 1, then opens the dispatch decision
   once both clues exist. Public suggestions use existing generic action DTOs.
   Wrong-location/irrelevant OBSERVE/CUSTOM may produce authored NO_EFFECT with
   base cost 1; no hidden clue is granted by text matching.
3. One bound CHOOSE offers hold or release. Hold requires both clues and emits
   the declared `dispatch.held` event, setting the mutable fact and RESOLVED
   ending `undelivered_receipt.ending.receipt_held`. Release emits
   `dispatch.released` and FAILED `undelivered_receipt.ending.dispatch_closed`.
   Deadline >=40 produces the same FAILED dispatch-closed meaning through
   `undelivered_receipt.ending.deadline_reached`. Freeze three distinct rules:
   deadline priority **10**, hold priority **20**, release priority **30**.
   The unchanged `DeterministicStoryDirector._apply_ending` sorts ascending by
   `(priority, ending_id)` and returns the first match. Thus deadline wins over
   hold, release or both; without deadline, hold wins if both decision conditions
   are synthetically present, otherwise the matching hold/release rule wins.
   No priority ties or new tie-break mechanism are introduced. The separate
   deadline identifier is necessary because `ScenarioDefinition` requires unique
   ending IDs and each rule's conditions are conjunctive; do not encode two
   alternative conditions as one conjunction or duplicate `dispatch_closed`.
   This technical split preserves P07's FAILED meaning, all clocks/balance values
   and the release identifier; it adds no gameplay outcome, reward or authority.
   This local decision adds no clock cost. Simultaneous-condition tests are
   synthetic selector boundary evidence, not proof of normal-play reachability.
4. The ending event and matching COMPLETE_SCENARIO memory rule commit under
   DB-002; no new ending setter, reward event or character lifecycle mutation.

S5 remains `run-mechanics/v1`: ResourcePressure charges saturating composure
on narrative actions; SocialTrust adds cost on the qualifying visible-NPC TALK;
ConsequenceSeverity adds cost on adverse/no-effect outcomes; InformationOpacity
adds cost on new clues; ConflictIntensity adds to each authored clock component.
Use the original-state composition and floor rules unchanged. At extreme values,
the successful OBSERVE costs at most 5 and TALK at most 7 clock units; even the
FAILED start 4 leaves room before 40. Zero composure never becomes death or a
new action prohibition. Repeated ineffective actions can reach the deadline.
No presentation, prompt or model output can alter these rules. Validate every
profile and boundary with actual public execution, not only this arithmetic.

## 4. Identity, persistent world state and closed Run families

Keep `RunId`, permanent `ContinuousStoryLineId`, original character binding and
its applicable reference, frozen S2 output, revision-three protocol/entry-world
bindings and all original admission receipts unchanged. Character current row
need not still have the admitted revision for historical reads; ownership must
still be valid. New continuation requires the current character to be active
and this Run to hold its active uniqueness slot. It never rebinds to the newest
character reference, retires/deceases the character, or releases the slot.

Exactly these new edges are permitted, in addition to existing closed families:

| Family/edge | Exact state and evidence |
| --- | --- |
| `NativeRunContinuedV1` | Original strict `NativeRunAdmissionV1` prefix, revisions 1/2/3/4, new `CONTINUE_NATIVE_RUN` mutation 3 -> 4, active binding, two participations joined at 3 and 4, one validated continuation receipt and world/visit/position family. |
| `NativeRunContinuedTerminatedV1` | That exact continued prefix plus revision 5 `TERMINATE_CONTINUED_NATIVE_RUN`, 4 -> 5, historical binding, second Session's valid ending evidence and one new exit receipt. |

`NativeRunTerminatedV1` remains exactly the old 3 -> 4 terminated family and
`NativeRunAdmissionV1` remains exactly revision three. Never accept `>=3`,
reinterpret old mutation kinds, broaden a legacy carrier, or revive either
terminal family. `completed` and a third participation are unavailable. At 4
active the current position is visit two even after its Session ends; ending
alone changes neither Run revision nor binding. Historical visit one cannot
terminate the now-continued Run using a fresh exit key.

### World/visit materialization and storage proposal

Introduce `WorldId`, `WorldVersion`, `WorldVisitId`, `RegionId`, `RegionVersion`
as separate strict carriers, using the existing bounded ASCII ID grammar and
positive int64 versions. World identity is persistent within this Run/line;
the authored world/version is content identity, the visit ID one occurrence,
and region/version an authored content scope. Neither Session ID nor scenario
ID substitutes for any of these domains.

No migration backfill or read repair. For the first successful continuation,
materialize visit one from the fully reconstructed admission and locked ended
Session, explicitly recording **materialized at Run revision 4**, origin/joined
revision 3 and the original admission time. Do not claim that a visit row existed
at admission. Materialize visit two with joined/materialized revision 4, a newly
issued Session and transaction time. Existing active/terminated native Runs
without continuation remain valid without these rows. New admissions retain
their original exact prefix; they use the same first-continuation boundary.

Three new tables, with no changes to Session/snapshot schema, are sufficient:

| Table | Exact proposed columns and key responsibilities |
| --- | --- |
| `run_world_states` | `run_id`, `continuous_story_line_id`, `world_id`, `world_version`, `first_visit_id`, `scenario_id`, `scenario_content_version`, `region_id`, `region_version`, `state_schema`, `state_canonical`, `state_sha256`, `materialized_state_version`, `created_at`. PK `(run_id, world_id)`; exact version frozen per world in this bounded slice. Immutable root of each persistent world's state/provenance, not a resettable world copy. |
| `run_world_visits` | `run_id`, `visit_id`, `continuous_story_line_id`, `visit_ordinal`, `world_id`, `world_version`, `region_id`, `region_version`, `session_id`, `joined_state_version`, `materialized_state_version`, `operation_id`, `source_reference`, `entered_at`, `created_at`. PK `(run_id, visit_id)`; unique `session_id`, `(run_id, visit_ordinal)` and `(run_id, joined_state_version)`. Only ordinals 1/2 and joins 3/4 in v1. Immutable associations. |
| `run_world_positions` | `run_id`, `continuous_story_line_id`, `visit_id`, `session_id`, `position_state_version`, `created_at`. PK `run_id`; unique Session; position version exactly 4, points to visit two. No turn-time updates; termination retains the last position. It is not a Session-version token. |

IDs use existing Run/Session column types/collation: Run/line/world/visit/region/
scenario/operation/source IDs are ASCII VARCHAR(128), Session IDs use the
existing 64-character Session type, content version ASCII VARCHAR(32), state
schema ASCII VARCHAR(64). Version/ordinal columns are BIGINT and times
DATETIME(6) UTC; hashes BINARY(32); canonical root bytes MEDIUMBLOB with explicit
1..1,048,576 byte application/SQL bounds. All columns are NOT NULL. No JSON
extension field or nullable presence discriminator. Row FKs are restrictive:
Run/line/materialized revision to the existing unique
`run_revisions(run_id, continuous_story_line_id, state_version)`; visit
`(session_id, run_id, continuous_story_line_id, joined_state_version)` to the
existing exact participation key; visit `(run_id, continuous_story_line_id,
world_id, world_version)` to a matching new unique key on its world root;
position `(run_id, continuous_story_line_id, visit_id, session_id)` to a matching
new unique key on visits. Root
`first_visit_id` is cross-validated by reconstruction, avoiding circular insert
FKs. Add the needed composite unique parent key on visits, not on old tables.
Preserve all old columns, rows, keys and migration bytes.

New checks enforce positive world/region versions, materialized/position version
4, exact state schema/byte bounds, and the visit ordinal/join mapping
`(1,3)|(2,4)`; their names are respectively rooted in
`ck_run_world_states_`, `ck_run_world_visits_`, `ck_run_world_positions_` with
suffixes `versions`, `schema`, `payload_size`, or `ordinal_join` as applicable.
Use `uq_run_world_states_exact` and `uq_run_world_visits_exact` for the composite
FK targets above. SQL cannot validate canonical BLOB associations itself;
strict complete reconstruction remains mandatory in addition to constraints.

`state_schema="run-world-state/v1"` canonical root contains exactly `schema`,
`run_id`, `continuous_story_line_id`, `world` (world_id/world_version), `region`
(region_id/region_version), `first_visit_id`, `session_id`, `scenario_id`,
`scenario_content_version`, `content_sha256`, `basis`, `snapshot_state_version`,
`snapshot`, `snapshot_sha256`. `basis` is `sealed_ending` for world one and
`session_initialization` for world two. `snapshot` is the full strictly validated
canonical GameState, including runtime facts, NPC state, discovered clues,
unresolved clocks and local memory. Its digest uses the existing
`state_fingerprint` algorithm. Root digest is SHA-256 of canonical root bytes.
These are private durable evidence; none enters a public DTO or prompt wholesale.

Root encoding is the existing snapshot JSON convention: `json.dumps` with
`ensure_ascii=False`, `sort_keys=True`, compact separators and `allow_nan=False`,
then strict UTF-8. Unlike operation-intent encoding, it performs **no NFC
normalization** of snapshot strings. Stored root decoding rejects duplicates,
unknown fields and noncanonical bytes and revalidates exact original scalars;
it must preserve even decomposed Unicode state verbatim. Fix independent root
goldens for this boundary; do not run a snapshot through the Run operation
normalizer and silently change old facts or their fingerprints.

World one's root must equal the exact old ended snapshot, which remains
unchanged. World two's immutable root binds its initialized state at Session
version 0. Its current world state is the validated root plus that associated
Session's latest durable snapshot, under the existing event/snapshot mutation
authority; no second mutable copy of gameplay facts is introduced. While active,
turns update that Session normally; after ending it is immutable. Thus confirmed
facts and local NPC state remain persistently available even without another
Run transition. A future revisit must consume that retained state and provenance;
it cannot initialize another blank instance. No revisit writer is added here.

Full classification checks all rows in both directions, including orphan
markers and reverse participation evidence; both Session owners; original
admission initialization; continuation initialization/event/memory; content
hashes; exact world/region mappings; position; full adjacent receipts; and any
exit suffix. Source ending/class/completed memory must match the sealed source
snapshot. Destination initial PlayerState must equal carried source PlayerState,
and destination current state must pass its own exact catalogue/runtime/memory
validation. At version 0 it must also equal the stored initial root. At later
versions do not require resources to equal their initial values. Initial root
evidence remains verifiable after the single latest-snapshot row advances.

Prefix reconstruction receives only revisions 1/2/3, their two mutation
receipts and first participation; its original common-time checks remain exact.
Continuation adds the third mutation receipt; continued exit adds the fourth.
Only the new join at 4 counts as an additional participation, never the exit
edge at 5. Binding reference/provenance remains identical through active 4;
only state/inactivation time changes at terminal 5, at a nondecreasing trusted
UTC time shared by that exit revision/current/receipt. Never hard-code the old
`version < 4` binding-restoration rule for this new family.

## 5. Content loading, deterministic selection and canonical evidence

Load both immutable packs at composition, before database locks. A closed
`SessionContentRegistry` maps exact `(scenario_id, content_version)` to validated
content/scenario catalogues, native mechanics entries and Session/turn service
bundles. It refuses duplicates, missing definitions, version/hash mismatches or
incompatible character/resource references. The original pack stays byte-exact.
No filesystem lookup, mutable catalogue lookup, Provider or model selection
occurs inside the transition UoW. Route owned Session reads/actions/status/jobs
using trusted persisted identity, revalidated by the delegate; a public request
cannot supply the content version. Metadata, initialization replay, old View,
old action/status replay and destination turns must all use this routing.
Legacy/standalone/Dynamic entry stays on the original bundle; discovery still
advertises only the existing entry world/scenarios. Destination `public_client`
metadata is for its playable View, not permission for direct entry.

The continuation catalogue is separate from `AUTHORED_ENTRY_WORLDS_V1` and has
version `same-line-continuation/v1`. One edge maps the three exact source endings
in P02 to P01, required priority 0, weight 1, both region refs above, exact pack
SHA-256 identities, mechanics version and carryover rule `carry-player-state/v1`.
The new pack's literal digest is computed and fixed in its production catalogue
when the approved content is authored; not a placeholder accepted at runtime.
That byte identity and independent goldens are implementation evidence.

Selection order is frozen as follows:

1. Validate source world/content, ended Session, completed memory, active Run/
   current participation and character authority before forming an eligible pool.
2. Include only exact authored edges with true ending prerequisites, loaded
   compatible content/mechanics and an unvisited destination. History is the
   full validated Run visit sequence, including the admission-derived first
   world before materialization. Important-NPC priority is unavailable because
   no separately approved identity/world predicate exists; no substitute input.
3. Required eligible edges precede optional edges. Sort by ascending required
   priority, ASCII world ID, numeric world version, ASCII region ID, numeric
   region version; reject duplicate keys. In v1 exactly the single required edge
   can survive. Weight domain is exactly integer 1, not float/zero/negative.
   Multiple surviving entries or unsupported weights are configuration integrity
   failures, not an unspecified draw. A required edge with missing/incompatible
   content is also integrity failure, not silently an empty pool.
4. Choose its first entry; there is no random draw, entropy source or modulo.
   A genuinely empty pool returns unavailable with zero writes/identity issuance.
   Anti-repeat excludes every previously visited world ID regardless of version;
   no cooldown, exception or revisit priority is implemented. Required progression
   cannot be lost to weighting. At the second ending no outgoing edge exists.

Derive a reproducibility seed as SHA-256 over
`b"deviation-protocol:world-continuation-selection:v1\0" + canonical(inputs)`.
Exact inputs: `selector_version`, `run_id`, `continuous_story_line_id`,
`source_session_id`, `source_session_state_version`, `source_snapshot_sha256`,
`source_world` (world_id/world_version), `source_ending_id`,
`source_ending_status`, `resolution_fingerprint`, `visited_worlds` (ordered by
visit ordinal; each world_id/world_version), and `eligible_pool` (ordered entries
with world/region/scenario/content refs, content_sha256, required_priority and
weight). Store these inputs and lowercase hex seed in successful evidence.
They come only from locked authority. Seed does not include a key, time, new
Session ID, client choice or model output, and is not used to randomize v1.
Tests fix independent bytes/hashes and ordering vectors, including empty,
incompatible, repeat and required-edge cases. Later selection breadth needs its
own reviewed version, not an unreviewed change to this deterministic rule.

### Operation and receipt contract

For operation requests, receipts and selection inputs, use existing
`canonical_run_operation_bytes` after original exact-type and
closed-field validation: UTF-8, NFC, sorted keys, compact separators, no BOM,
duplicates, non-finite values, coercion, extra/missing fields or noncanonical
stored bytes. Existing IDs and signed int64 limits apply. Snapshot roots have
the separate bound above; continuation evidence <=16,384 bytes, contains hashes
and references, never duplicate raw snapshots or prose.

New namespace `run.continue-native/v1`, mutation `CONTINUE_NATIVE_RUN`, result
schema `run.continue-native-result/v1`. Receipt key remains
`(run_id, operation_namespace, operation_id)` and uniquely binds result revision
4. `RunSafeResult` adds this closed branch: same Run/line, active version 4,
the exact second participation and no character-result member. Do not call the
generic attach service or legacy entry coordinator to continue.

Request object has exactly `schema="run.continue-native-request/v1"`,
`controller_binding`, `player_id`, `public_operation_key`, `run_id`,
`continuous_story_line_id`, `source_session_id`, `expected_run_state_version`,
`expected_session_state_version`, `source_reference`. Public body supplies only
the two version expectations; all other associations are derived/authorized.
Operation ID is lower-case SHA-256 of canonical
`{schema:"run.continue-native-operation/v1", controller_binding,
public_operation_key, run_id}`. Request fingerprint is SHA-256 of the complete
canonical request. Reuse does not incorporate changing destination state.

Evidence has exactly `schema="run.continue-native-evidence/v1"`, `request`,
`source_ending` (scenario_id, scenario_content_version, ending_id, ending_status,
session_state_version, snapshot_sha256), `selection_inputs`, `selection_seed`,
`source_visit_id`, `destination_visit_id`, `destination_session_id`,
`destination_creation_request_id`, `destination_initial_event_id`,
`destination_random_seed`, `source_world_state_sha256`,
`destination_world_state_sha256`, `carryover_rule`, `entry_variant`, and
`occurred_at` (canonical UTC ISO text with six fractional digits and `Z`).
`entry_variant` is `resolved|failed`. Derive visit IDs from SHA-256 of canonical
`{schema:"run.world-visit-id/v1", run_id, continuous_story_line_id,
session_id, joined_state_version}`; derive destination creation-request ID
with the same controller/key/Run operation domain and distinct schema
`run.continuation-session-create/v1`. New Session/event IDs and Session random
seed use existing trusted issuers, invoked only for a new eligible operation.
The Session seed is stored evidence, not world-selection entropy.

S7-1 original exit namespace/evidence/result stays exact. Add only for the
continued prefix: `run.terminate-continued-native/v1`, mutation
`TERMINATE_CONTINUED_NATIVE_RUN`, result
`run.terminate-continued-native-result/v1`, expected/result versions 4/5,
second Session ending evidence. Its request/evidence keys and 4,096-byte ceiling
match the original exit family, with new corresponding schema literals and
operation domain `run.terminate-continued-native-operation/v1`. Its result is
terminated, no participation/character result. Decoder selection uses stored
namespace/version, never best-effort decoding. Historical original exits remain
replayable after a separate new admission; a continued exit replay is equally
immutable after later fresh admission.

## 6. Transaction, ordering and failure ownership

One `NativeRunContinuationService` owns the handoff. Repositories stage/flush,
never commit. Reuse the existing pinned native UoW and shared named lock
`deviation_protocol:p33:s3:run_protocol_bindings:ddl_write:v1` (30 seconds).
No renderer, Provider, nested transaction owner, compensation or retry loop.

1. Strict transport validation, principal/controller resolution and owned source
   Session lookup. A preliminary read only identifies character/Run lock targets.
   Missing/foreign targets have the same safe 404; no private catalogue leak.
2. Native UoW acquires the named lock, then character current row, then Run
   current/history/participations/receipts/protocol/world in the existing
   classifier order, then new world roots/visits/position in key order. Existing
   classifier Session reads remain at their current point; visit-two Session
   reads follow visit-one reads, ordered by visit ordinal, never arbitrary ID
   ordering. Lock source/latest snapshot before validation/staging. Revalidate
   all targets, controller and owned Session associations after locking.
3. Fully validate native stored family. Lookup the operation's scoped receipt.
   Exact matching request replays the original result, including destination
   initial association, before new eligibility/current-position/version checks.
   Same key/different intent is conflict. Replay does not issue IDs, seed, time,
   writes, a new View, renderer call or commit. Validate the entire stored family
   including any later exit; corruption is never successful replay.
4. For new requests: require exact active revision-three admission, current
   source participation, active owned character and same active binding; then
   compare expected Run/Session versions; then require trusted ENDED snapshot,
   exact authored ending and completed memory. Check no still-live PREPARED,
   IN_PROGRESS or PROPOSAL_VALIDATED job; job state alone is not settlement.
   Valid unsupported ending/empty pool is unavailable; malformed ending/memory
   or a catalogue contradiction is integrity failure. No writes on any rejection.
5. Resolve the deterministic eligible edge and carryover. Choose one UTC time
   rounded to whole seconds before building Session/event/evidence, consistent
   with existing Session column precision. Build revision 4, two visit records,
   two world roots, position, complete new Session initialization and receipt.
   The destination initializer starts with a detached copied PlayerState,
   invokes ordinary scenario initialization and memory application, and applies
   P03 via a sealed, closed entry-variant initializer before snapshot publication.
   It never first persists a refill/default player. Validate all references.
   Variant initialization recomputes initial Frame after applying the clock
   offset; it neither advances a turn nor fabricates a prior event. The standard
   ScenarioStarted event remains sequence 1 and records the actual destination
   scenario/version. The continuation receipt/root bind the added variant and
   carried player authority; do not reuse admission's default-player replay
   assumptions for destination initialization.
6. Stage Run revision, Session/event/memory/snapshot, new participation, roots,
   visits, position and receipt; CAS Run current from 3 to 4 without changing
   the binding or active uniqueness slot. Reconstruct the complete candidate
   family against the intended result, then make exactly one commit attempt.
   Return success only after commit and successful ordinary cleanup.

Two same-key requests serialize to one commit and exact replay; differing intent
under that key conflicts. Different continuation keys yield one winner and
unavailable for the second. Exit versus continuation yields exactly one complete
edge from revision 3; losing fresh exit on old Session is unavailable, never
termination of visit two. Same-character admission stays ineligible while the
continued Run is active. Retirement uses the same character-first lock and
retains its existing active-Run rejection. Final turn may settle first, allowing
continuation after revalidation, or continuation finds an active/unsettled
Session and rejects. Turn paths retain Session/job locks plus nonlocking Run
reads: do not introduce reverse Run write locks or hold locks during rendering.

Flush/CAS/unique/precommit failure and cancellation roll back every staged row
and restore detached versions. Classify known contention as conflict only with
the existing supported constraint identification; no arbitrary SQL exception
becomes replay success. Propagate cancellation. A commit acknowledgement loss,
commit cancellation or postcommit cleanup failure is outcome unknown, never
proof of rollback/success. Retain exact request for explicit retry or use the
GET recovery below. Use existing retained cleanup, invalidation, pool detachment
and physical-owner disposal. No reconnect-and-continue, automatic retry,
compensating Session/Run, receipt removal or replacement admission.

## 7. Migration and deployment compatibility

Propose `alembic/versions/20260918_0009_native_world_continuation.py`, revision
`20260918_0009`, parent `20260917_0008`. Create the three tables above and extend
only the three existing Run mutation/protocol CHECKs with the two new exact
branches: continued active 3/4 and continued terminal 4/5. Preserve corrected
008 branches byte-semantically, all previous migrations and all existing rows.
Run current/revision branches require exact kind/status/prior/current pairs,
complete active/historical binding respectively, and all necessary nullable
operand `IS NOT NULL` guards under DB-001. Receipt branches require their exact
namespace/kind/result/version/participation matrix. Current active-slot and
binding invariants stay enforced. ORM expressions must match installed schema.
In particular the new active-current branch explicitly requires a non-NULL
active character slot equal to the binding character; equality alone is not
presence. The new terminal-current branch requires that slot NULL.

Upgrade takes the same shared lock before any DDL. Create world states, visits
(with composite keys/FKs), positions in that dependency order, then replace
`ck_run_revisions_mutation_matrix`, `ck_run_current_mutation_matrix`,
`ck_run_mutation_receipts_protocol_matrix` in that order. Validate the expected
008 starting definitions and absence of partial 009 artifacts before proceeding.
No data rewrite. Both old active and old terminated native families survive.

Downgrade takes the same lock and performs current locking probes on all three
new tables plus existing Run current/revisions/receipts/participations for either
new mutation/namespace/schema, active revision 4, any revision >=5, or a later
native participation. Any complete or partial continuation evidence refuses
before the first DDL. Also refuse contradictory/unknown partial schema; do not
drop evidence simply because one table is empty. If safe, restore the three
exact 008 CHECKs in their upgrade order, then drop positions, visits, states.
Old 008 termination alone does not prohibit returning to 008.

Use the existing bounded migration locking/disposal pattern, not a generalized
framework. MySQL DDL is statement-durable: failure/disconnection at every create,
ALTER or drop boundary must record actual completed prefix and remaining schema,
stop and discard unsafe owners. No DDL rollback claim or automatic reconnect.
Operator inspection/repair precedes resuming writers. Required fault evidence
includes acquisition, statement, post-statement loss, release and failed disposal
on both directions, stale repeatable-read probe and live writer serialization.
Schema 009 and the updated readers must be deployed before enabling continuation;
old applications cannot read new families and must not run concurrently with
new writers. No deployment is authorized by this planning task.

## 8. Public API, projections and Web recovery

Keep `public-run-context/v1` byte/shape semantics unchanged: it describes original
admission settings, including the entry world, not current world. Existing
Session View and storage v1 stay unchanged. Do not weaken `assertViewAssociation`
or substitute current lifecycle for an immutable admission field.

Add `GET /v1/sessions/{session_id}/run-continuation`, operation ID
`get_native_run_continuation`, and `POST` at the same path, operation ID
`continue_native_run`. GET accepts no body/query. POST requires existing
Idempotency-Key grammar and exactly `expected_run_state_version` and
`expected_session_state_version`; maximum 1,024 bytes. Apply the existing exit
transport's duplicate-header/member, UTF-8/BOM, query, extra/null/coercion rules.
Int64 bounds follow exit; Web rejects non-JavaScript-safe integers. Neither
request contains destination, visit, region, line, character, seed or result.

Closed GET DTO `native-run-continuation-status/v1` has exactly `schema_version`,
`session_id` (path), `run_id`, `run_state_version`, `session_state_version`,
`lifecycle_status`, `can_continue`, `current_session_id`, `visit`, `predecessor`
and `successor`.
`visit` is null for unmaterialized admission or old S7-1 termination; otherwise
exactly `{visit_id, visit_ordinal, world_id, world_version, region_id,
region_version}` for the **path Session**, never a substitute for its View.
`successor` is null unless this path Session has the committed handoff; then it
is the immutable continuation result below, including after the new Session has
advanced or exited. `current_session_id` is original before continuation and
destination afterward, including after termination. `can_continue` is true only
for the exact eligible current source. No candidate world list is projected.

`predecessor` is a **required, nullable** field. Non-null values are closed
objects with exactly `session_id`, `session_state_version`, `scenario_id`,
`scenario_content_version` and `visit`. `session_id` is a strict existing
Session-path ID (ASCII `[A-Za-z0-9][A-Za-z0-9_.:-]*`, length 1..64);
`session_state_version` is the source's immutable ending version, strict
nonnegative int64; `scenario_id` is the existing strict ASCII ID, length
1..128; `scenario_content_version` uses the same grammar, length 1..32.
`visit` is the non-null six-field visit object above, ordinal exactly 1.
Web applies the same safe-integer checks as other versions. No omitted field,
extra member, coercion or empty-object substitute is valid. These fields locate
and validate the old View; Run identity is already in the enclosing response
and immutable admission context is checked against the recovered current View.

For the first Session, `predecessor=null` before continuation, after original
S7-1 termination and when reading materialized visit one as history. For the
second Session, `predecessor` is non-null and identifies that edge's source,
including after destination actions, ending, continued exit or a later separate
Run admission. Its `successor` remains null in this slice. A valid first visit's
null predecessor is not permission to erase missing evidence for a second visit.

Derive this association only after authorizing the path Session/controller and
completely reconstructing the native family in the same read snapshot. Match
the continuation receipt's request source Session and source ending/version to
visit one, its sealed root and participation joined at 3; match the receipt's
destination Session/visit to the path Session, visit two, participation joined at
4 and authoritative position. All must share the exact Run/line and satisfy
both Session ownership checks, the admission prefix and any terminal suffix.
Neither an occupied active character slot on an old Run nor browser memory is
required for historical ownership. Never infer a predecessor by scanning
unrelated Sessions, trusting caller-supplied IDs or retaining a historical POST
response. The existing evidence suffices; no extra column or storage format.

Missing/foreign **path** Session or caller/controller authority returns the
existing opaque 404 `SESSION_NOT_FOUND`, with no association disclosed. Once
that authority is established, missing referenced Session/root/visit/receipt,
cross-owner or crossed Run/line references, self-links, contradictory source/
destination/version/content/position or partial evidence are stored-integrity
failures: the trusted loader rejects and GET returns opaque 409
`SNAPSHOT_INVALID`, never a partial DTO, null fallback, scan or repair. A direct
GET on an unauthorized historical target also returns 404. These cases perform
no mutation and disclose no rejected association. SQL and Demo own identical
validation/error behavior; public DTO/OpenAPI and Web schemas include this field.

Closed POST DTO `native-run-continuation-result/v1` has exactly `schema_version`,
`source_session_id`, `source_session_state_version`, `run_id`,
`resulting_run_state_version` (4), `session_id` (destination),
`initial_session_state_version` (0), `scenario_id`, `scenario_content_version`,
`run_context` (unchanged admitted context) and `visit` (non-null visit-two shape).
HTTP 200 on first success and exact replay; replay returns original initialization
identity/version, never the now-current View or Run lifecycle. GET may establish
that a handoff occurred without identifying which competing key won it.
Every success and error status/schema is explicitly in OpenAPI/ErrorResponse.

| Ordered condition | Public ownership/result; no mutation except committed success |
| --- | --- |
| Malformed transport | 422 `REQUEST_VALIDATION_FAILED` |
| Unconfigured service, including Dynamic Demo | 503 `RUN_CONTINUATION_NOT_AVAILABLE` |
| Missing/foreign path Session/controller | 404 `SESSION_NOT_FOUND` |
| Positively proven legacy/standalone | 409 `NATIVE_RUN_REQUIRED` |
| Crossed/corrupt/unknown stored evidence or incompatible required content | 409 `SNAPSHOT_INVALID`, opaque |
| Existing scoped receipt matches / differs | 200 original result / 409 `IDEMPOTENCY_CONFLICT` |
| New request on terminal/continued/history-only source or inactive character | 409 `RUN_CONTINUATION_NOT_AVAILABLE` |
| New eligible-family request with stale expected Run or Session version | 409 `RUN_CONTINUATION_STALE` |
| Active/unsettled Session, unsupported valid ending or empty pool | 409 `RUN_CONTINUATION_NOT_AVAILABLE` |
| Known lock/CAS/uniqueness contention | 409 `RUN_CONTINUATION_CONFLICT` |
| Commit or postcommit cleanup uncertainty | 503 `RUN_CONTINUATION_OUTCOME_UNKNOWN` |
| Other failure | Existing opaque 500; never synthesize a known outcome |

GET returns 200 unavailable for valid native terminal/history/active-play states;
it never runs a mutation or allocates identity. Ownership/integrity precedes all
eligibility. Public output omits line/controller/key/fingerprints, seed, private
predicates, root snapshots, hidden facts, SQL and local paths; scan keys and
values, not just top-level fields.

Each GET constructs its complete result in one ordinary read UoW from one
consistent database snapshot (Demo: one immutable store snapshot). Registry
routing's preliminary owned identity is only a target; the chosen delegate
rechecks the same persisted scenario/version and ownership inside that read.
No cross-UoW mixture of source ending, current position, predecessor and successor
evidence. Every related lookup is scoped to the reconstructed Run and exact edge.

Extend existing run-status/exit behavior only for the two new families, keeping
their DTO shape: status Run versions may now be 4 active or 5 terminated.
`can_exit` requires the path Session to be the current participation and ended;
it is false for old visit one after continuation. New exit uses the continued
namespace/4->5 evidence above. Exact old exit replay remains prior to new
availability checks. A terminated destination remains readable, and explicit
return to setup retains storage-removal gating and fresh admission confirmation.

### Client state transitions

On a fresh ended native View load status and continuation GET; bind each to the
loaded Session ID, Run ID, Session version and each other's Run revision. If
responses reflect different snapshots, disable controls and refresh by GET.
Only a consistent `can_continue=true` enables the explicit continue confirmation;
explain same journey/remaining resources, no destination choice and permanent
retention of old history. Cancel before dispatch does nothing. Continue and exit
share the operation/generation exclusion; they cannot both be dispatched by a
double click. Backend concurrency is still authoritative.

Before POST, freeze exact URL/body/key and source Session/Run/context in memory.
An uncertain response, 5xx, malformed success, cancellation after dispatch or
tainted later rejection retains those exact bytes. Only explicit retry resends
them. GET reconciliation never POSTs and never synthesizes success from local
state. No pending mutation payload/key is added to storage.

Validate result source/Run/version, complete immutable admission context, distinct
destination Session and exact destination scenario/content/visit association.
Write the existing storage v1 record with the new Session and no inherited
`client_request_id` **before fetching or displaying its View or enabling actions**.
Replace the expected native association atomically with that validated result;
do not compare the new scenario against the old world's association or clear the
entire immutable-context check. Fetch View, run normal full association validation
and validate the destination visit via continuation GET. Subsequent same-Session
reads must preserve the complete new association. A stale generation, unmount,
client replacement or Session switch cannot publish its result or modify storage.

If storage write fails after confirmed handoff, retain the validated result and
lock gameplay/admission/exit; explicit storage retry does only set+GET, never
continuation POST. After reload with the old recovery record, GET old View then
continuation status reveals the committed successor. Show **恢复已继续的旅程**;
explicit navigation stores successor then reads it, no mutation. Reload with the
new record recovers that Session normally; GET supplies visit and predecessor
identity even if every prior page object and POST response was lost. GET 404
after Demo restart uses existing explicit clear/no-automatic-replay behavior.
If GET proves no handoff, a lost in-memory key cannot be reconstructed; a new
explicit confirmation may create a new key, still guarded by the one-edge CAS.

Keep **查看上一世界记录** separate from recovery of the current journey. Maintain
an authoritative recovery Session/association (the stored successor after the
handoff) and a separate temporarily displayed historical Session/association.
On successor reload, fetch continuation GET even during active play; do not gate
predecessor discovery on an ended View. Bind its path/Run/Session version/visit
and current Session to the recovered View before enabling history navigation.

History navigation uses only GET on the trusted `predecessor.session_id`: fetch
its View and continuation status. Before display, require the exact target
Session, scenario/content and sealed ending version from `predecessor`, the
complete same immutable admission context, visit-one identity and ENDED View.
Require the old status's `predecessor=null`, matching Run, source Session/version
and visit, `current_session_id` equal to the retained successor, and `successor`
linking back to that exact successor/visit/scenario/content/context at result
Run version 4. Compare the two statuses' Run revisions; a legitimate intervening
exit requires fresh GET reconciliation, never mixing snapshots. The server owns
same-line proof; no private line ID is newly projected for the client to trust.
Missing, unauthorized, invalid or contradictory responses do not publish history
or change the recovery association; surface read failure and allow safe GET retry.

Historical display cannot enable gameplay, continuation, exit, retained mutation
retry or other write controls for the predecessor. It never sets/removes storage
or replaces the authoritative current association. **返回当前旅程** reads the
retained successor View/status by GET, revalidates its full association and
predecessor edge, then restores only controls permitted by its current state.
Reload during historical display recovers the successor from unchanged storage
v1. Navigation in either direction advances the existing operation generation,
invalidates prior reads and checks client instance, generation, recovery Session
and requested display target before publishing. A late history response after
return/reload/unmount/client replacement cannot replace the current View, change
storage or activate old controls. Navigation never clears or replays an uncertain
mutation; preserve existing operation exclusion and safe-read recovery rules.
Show actual old ending/history, not a generated cross-world summary. S6 selection,
delayed-character selection, discovery retries, immutable-context checks and
S7-1 uncertain-exit/storage-clear regressions remain required. Preserve DF-002's
existing disposition; assess required recovery with faults, not a reload waiver.

## 9. Mechanics, prompts and deterministic Demo

Add a new exact `native-visit-turn-request/v1` envelope for visit-two jobs only.
Keep old `native-turn-request/v1` bytes and strict revision 3 parser. New envelope
outer fields remain `schema`, `request`, `binding`, `mechanics`; binding retains
all old fields, fixes `run_revision=4`, and adds exactly `visit_id`,
`visit_ordinal=2`, `world` (world_id/world_version), `region`
(region_id/region_version), and `continuation_fingerprint`. `entry_world` still
denotes frozen admission. New Session/scenario/content use the destination;
mechanics remains `run-mechanics/v1`. Fully validate each discriminator; never
reinterpret old v1 fields as current world. Old committed replay precedes fresh
mechanics, including after continuation/exit. New actions require current active
visit and Session; ended/history requests keep existing ended rejection.

Keep `run-prompt-context/v1` unchanged. Add a separate authentic immutable
`CompiledWorldVisitContextV1` attachment, maximum 2,048 canonical UTF-8 bytes,
schema `world-visit-prompt-context/v1`. Exact public fields: `schema`,
`world_title`, `region_title`, `visit_ordinal`, `previous_ending_status`,
`previous_ending_title`, `entry_notice`. Titles <=120 characters, notice <=300;
closed strings from approved public content and the validated source outcome.
No world/line/Session/NPC IDs, root facts, secret history or prose inference.
Compiler authenticates detached visit evidence before inspecting it and binds
it to the same turn inputs/state/continuation fingerprint as mechanics. The
nonserialized request attachment is rebuilt after trusted job reconstruction;
it never becomes client input or durable model authority. PromptBuilder adds
only this safe object. No changes to public NarrativeRequest or legacy prompt
bytes. Native Demo checks the new attachment as strictly as the old one.

Compilation and rendering run outside UoWs/locks; finalize reconstructs and
compares evidence without calling the compiler/Provider under lock. Previous
accepted narrative is available only through old history reads; new prompts
receive the bounded ending/entry annotation plus the new Session's safe Frame,
memory and recent committed text. No cross-NPC memory, global recap, canon
rewrite, death inference or model-owned selection/mechanic is introduced.

Demo uses the same service, codecs, catalogues and evidence. Add all three maps
to trial/snapshot/validation/publication/rollback/reset, validate complete
cross-map state before publication, and preserve per-task renderer allowance.
Continuation GET projects the same required nullable predecessor from one fully
validated store snapshot, with the same ownership, reverse-edge and corruption
rejections as SQL. It does not maintain a separate browser-derived history map.
Its new Session uses deterministic existing issuers; same inputs across processes
must produce identical public results and complete store evidence. Restart loses
the entire process store and yields missing Session, not durable recovery.
Dynamic Demo stays legacy-only. No external-I/O fallback or test-only production
mutation port.

## 10. Dependency-derived future implementation inventory

This is an implementable dependency inventory, not an arbitrary path count.
**New** denotes a proposed new file. Every listed existing path may be left
unchanged if inspection proves its contract already sufficient; record that
explicitly. Any additional path requires a demonstrated direct dependency,
bounded impact/verification reassessment and a revised inventory before editing
it. Product/schema/authority changes require renewed plan approval; mechanical
direct-consumer additions do not license unrelated refactoring.

| Paths | Responsibility |
| --- | --- |
| `domain/run.py`; `domain/run_protocol_binding.py`; **new** `domain/world_continuation.py` | Exact new transitions/families, separate world/visit/region carriers, deterministic selection, strict root/transition evidence and pure carryover/entry rules. |
| `domain/run_protocol_mechanics.py` | Add destination compatibility entry only; five policy formulas unchanged. |
| `application/run_operations.py`; `application/ports.py`; **new** `application/run_continuation_service.py`; **new** `application/world_visit_context.py` | Closed receipt/result branches, typed repository/registry ports, sole handoff owner, safe predecessor/successor projection from complete owned reconstruction and trusted visit-context compiler. |
| **new** `application/session_content_registry.py`; `application/session_service.py`; `application/native_run_admission.py`; `application/public_run_protocol.py`; `application/run_exit_service.py` | Versioned service routing, continuation initialization/replay, original admission extraction, same immutable context for either Session, current-only exit and exact historical replay. |
| `application/native_turn_mechanics.py`; `application/narrative_turn_orchestrator.py`; `application/narrative_models.py`; `application/narrative_prompt.py` | New visit-bound jobs/detachment/finalization and private prompt attachment; no new mechanics algorithm. |
| `infrastructure/run_persistence.py`; `infrastructure/run_protocol_binding_persistence.py`; **new** `infrastructure/world_continuation_persistence.py`; `infrastructure/repositories.py`; `infrastructure/orm_models.py` | Adjacent revision/receipt and participation reconstruction, strict codecs, roots/visits/position, staging/CAS and matching constraints. |
| `infrastructure/unit_of_work.py` | Attach new repositories to existing ordinary/pinned UoWs; preserve lock, commit and disposal control flow. |
| **new** `alembic/versions/20260918_0009_native_world_continuation.py` | Three new tables, narrowly additive branches, bounded up/down/current probes/fault behavior. |
| `api/main.py`; `api/dependencies.py`; `api/schemas.py`; **new** `api/run_continuation_routes.py`; `api/run_exit_routes.py` | Production composition/routing, closed HTTP/OpenAPI/error contract including required nullable predecessor and its 404/409 ownership, extended exact exit eligibility. |
| `api/demo_composition.py`; `infrastructure/demo_persistence.py`; `infrastructure/native_demo.py` | Multi-content native service graph, atomic maps/classifier and owned predecessor/reverse-edge projection parity, deterministic rendering guard parity. |
| **new** `config/scenarios/undelivered_receipt_v1.json`; **new** `docs/scenarios/undelivered_receipt_v1.md` | Reviewed proposed content, approved product decisions translated into declarative rules, pack digest and explicit public play routes. |
| `web/src/api/schemas.ts`; `web/src/api/client.ts`; **new** `web/src/runContinuation.ts`; `web/src/App.tsx`; `web/src/runExit.ts` | Strict status/result/predecessor validation, retained attempts, cross-operation exclusion, successor storage-before-View; separate current recovery and historical display associations with reciprocal GET-only navigation and stale-generation protection. |
| **new** `tests/unit/test_world_continuation.py`; **new** `tests/unit/test_world_continuation_persistence.py`; **new** `tests/unit/test_run_continuation_service.py`; **new** `tests/unit/test_run_continuation_api.py`; **new** `tests/unit/test_session_content_registry.py`; **new** `tests/unit/test_world_visit_context.py` | Independent goldens, corruption, selection, carryover, command/replay/rollback, transport/projection/routing/prompt authority. |
| `tests/unit/test_run.py`; `tests/unit/test_run_operations.py`; `tests/unit/test_run_persistence.py`; `tests/unit/test_run_protocol_binding.py`; `tests/unit/test_run_protocol_binding_persistence.py`; `tests/unit/test_run_repositories.py` | Exact old/new family and receipt matrices, reverse/orphan evidence and predecessor preservation. |
| `tests/unit/test_native_run_admission.py`; `tests/unit/test_native_turn_mechanics.py`; `tests/unit/test_public_run_protocol.py`; `tests/unit/test_session_service.py`; `tests/unit/test_run_exit_service.py`; `tests/unit/test_run_exit_api.py` | Historical replay after handoff/exit/new admission, current Session authority, unchanged admission context and continued exit. |
| `tests/unit/test_run_protocol_prompt_context.py`; `tests/unit/test_native_demo.py`; `tests/unit/test_demo_persistence.py`; `tests/unit/test_demo_composition.py`; `tests/unit/test_run_composition.py`; `tests/unit/test_player_character_api.py` | Prompt v1 preservation, Demo/production graph, exhaustive public route/schema inventory assertions. |
| **new** `tests/unit/test_undelivered_receipt_content.py`; `tests/unit/test_scenario_catalog.py`; `tests/unit/test_story_director.py` | New content validity/entry variants/endings, exact deadline 10 / hold 20 / release 30 and synthetic simultaneous-condition boundaries, balance and generic scenario authority; old pack identities retained. |
| **new** `tests/integration/test_mysql_world_continuation.py`; **new** `tests/integration/test_mysql_world_continuation_migration.py`; `tests/integration/test_mysql_native_run_exit.py`; `tests/integration/test_mysql_native_turn_mechanics.py` | Public play/replay/history, all real persistence/race/fault/migration proof and both new ending paths. |
| `tests/integration/test_mysql_player_character.py`; `tests/integration/test_mysql_run.py`; `tests/integration/test_mysql_run_protocol_binding.py` | Current-head/table inventory expectations only where necessary. Never replace historical 005/006/007/008 expectations by 009. Isolate old migration suites and restore their required schema. |
| **new** `tests/e2e/test_native_world_continuation.py`; **new** `tests/e2e/support/native_world_continuation_child.py` | Deterministic full public journey and cross-process complete-store identity with external I/O denied; normal Demo public transport/store support for the combined rendered C08 journey. |
| **new** `web/src/runContinuation.test.ts`; `web/src/api/client.test.ts`; `web/src/App.test.tsx`; `web/src/App.recovery.test.tsx`; `web/src/App.action-loop.test.tsx`; `web/src/runExit.test.ts` | Rendered confirmation, lost response, retained exact retry, storage faults/reload/history/reselection and stale completion. |
| `PLANS.md`; `docs/architecture.md`; `docs/run_protocol.md`; `docs/public_client_contract.md` | Synchronize implemented behavior, source/content identities, actual evidence and limits during implementation. This plan then remains frozen. |

Inspected dependencies expected to need **no production change**:
`domain/entry_world.py` (entry catalogue stays one world);
`domain/state.py`, `domain/player_memory.py`, `application/player_memory.py`
(local-memory validation is preserved);
`domain/scenario.py`, `domain/scenario_runtime.py`, `application/story_director.py`,
`application/scenario_initialization.py`, `infrastructure/scenario_loader.py`
(use existing declarative schemas and initialization; new sealed entry variant
belongs in continuation service/domain);
`application/turn_orchestrator.py` (ordinary turn engine delegates native
coordination); `application/run_protocol_prompt_context.py` (v1 unchanged);
`application/player_character_service.py` (retirement/eligibility use Run
repository); `web/src/sessionRecovery.ts`, `web/src/runSetup.ts` (storage and
explicit setup contracts retained); `infrastructure/demo_authority.py`, Dynamic
Narrative code and `config/demo_content_pack.json`. Their affected suites still
run. Preserve `config/scenarios/death_certificate_v1.json` and its design doc,
all earlier migrations and all published plans. No product-interface dependency
is excused merely because a file was initially placed in this no-change list.

## 11. Executable implementation acceptance and evidence ownership

The cases below are future requirements; none ran in this planning task.
Every mutation has a rollback/no-mutation counterpart. Use installed `.venv`
and sanitized repository verification. MySQL authority must be separately
granted for implementation and preflight must prove `mysql+asyncmy` and database
`deviation_protocol_test` without printing URLs/secrets. No SQLite or mocked
substitute for changed persistence, races or DDL. Independent case labels must
remain locatable in logs; overlapping suite counts are not additive evidence.

| Case / exact setup and boundary | Expected outcome / mutation | Owning suite |
| --- | --- | --- |
| C01 — Create/select owned active character; native admit Easier, actually play public ASGI actions to `protocol_broken`, GET/confirm continuation, OBSERVE in destination, GET/reload. Repeat Extreme actual public play to `deadline_reached`; also reach the other RESOLVED ID through its public decision. | One same Run/line/binding, second Session at 0 then 1; source ending/history bytes unchanged; P03 variants and retained resource values; only intended revision/receipt/world/visit/position/new Session rows. All source ending IDs are eligible; direct snapshot mutation is not journey evidence. | New `test_mysql_world_continuation.py`; Demo E2E repeats both classes. |
| C02 — From each entry variant, OBSERVE -> TALK -> CHOOSE hold; separately release and repeated ineffective actions to deadline. Exercise all three profiles, permitted objective extremes and composure zero. Public ASGI/Demo actions; separately run the synthetic selector boundaries below. | Actual authored RESOLVED/FAILED endings, memory/event atomicity, all five policies visible in costs; exact priority/ending-ID assertions; no third continuation; explicit current-Session exit reaches 5 and same-character fresh admission remains possible. No reward/refill/death. | New content unit suite and `test_story_director.py` own synthetic boundaries; MySQL continuation suite and Demo E2E own actual play. |
| C03 — Same key/body replay before/after destination action/ending/exit and after new separate Run admission; changed body; fresh key on old source; old admission/action/status replay. | Exact original result and no new ID/clock/render/row/commit; conflict before stale; old history readable; new Run binding untouched. | Continuation service/codec units; MySQL continuation and exit suites. |
| C04 — Foreign owner/controller, crossed Session/Run/visit/region/content, missing reverse evidence, every root/receipt key and version/digest corrupted independently, malformed numeric/null/private actual-model state. Include each partial new table marker and predecessor disclosure negatives below. | Owned-family corruption is opaque SNAPSHOT_INVALID, foreign/missing path Session 404; strict storage exception internally; no predecessor leak, null fallback/read repair/writes. Untouched predecessor families still reconstruct. | New domain/persistence/API units, SQL corruption cases, Demo parity cases. |
| C05 — Independent real connections: same/different continuation keys, continuation vs exit, admission, retirement and actual in-flight final turn. Observe server lock wait from another connection before releasing holder. | One complete winner/replay or specified rejection, no dual current Session/active binding, no reverse-lock deadlock; named-lock/character order and final-turn revalidation observed, not assumed from sleeps. | MySQL continuation suite; retained exit-race regressions where affected. |
| C06 — Inject failure/cancellation after each staged revision/Session/event/snapshot/participation/root/visit/position/receipt/CAS and before commit; acknowledgement loss both committed/uncommitted, postcommit cleanup/disposal failure. | Every precommit path rolls back complete family; uncertain commit stays unknown; GET/exact retry recovers one actual result; no automatic compensation. Demo trial failures publish nothing. | Continuation service/Demo units plus real MySQL continuation suite. |
| C07 — Record initial schema/checks/rows/lock; upgrade empty/populated 008, native active/terminated and legacy controls; genuine invalid single-field mutations on valid new families. Downgrade with empty new evidence, then complete/partial evidence; stale read snapshot and waiting writer; fault each DDL/loss/cleanup boundary. | Old rows/branches unchanged; exact named CHECK/FK rejection with clean rollback and valid-family control, including nullable operands; refusal before DDL for unsafe downgrade; observed partial DDL/disposal and deliberate restoration; ORM parity, one 009 head. | New MySQL migration suite, sequentially isolated from other schema suites. |
| C08 — Render ended controls; cancel; confirm/double-click; continue-vs-exit lock; lost/malformed POST then GET; explicit exact retry; old-record and new-record reload; failed storage set and retry; late completion/unmount/client replacement; combined predecessor reload/navigation and negatives below; continued exit/clear failure/reselection. | One intentional POST; GET-only recovery/history/return; complete old/new associations; successor storage unchanged during historical display; storage-before-View; storage retry never repeats handoff; no stale completion writes, predecessor gameplay or automatic admission; all S6/S7-1 recoveries preserved. | New `runContinuation.test.ts`, client and rendered App/recovery/action-loop/exit suites, using normal Demo public transport/store via the listed E2E child for the combined journey; C01/C09 own SQL/Demo parity. |
| C09 — Normal production composition loads both packs; old legacy/native/history and new Session routes; closed OpenAPI/projections/key-and-value scans; independent Demo processes with external I/O denied and restarted store. | Correct version-specific loading and current-world mechanics, immutable entry context, original route/DTO compatibility, no hidden roots/seeds; Demo exact transition/store parity and restart 404, Dynamic unavailable. | Registry/composition/API units, MySQL continuation, Demo E2E. |
| C10 — Independent canonical fixtures for request/operation/seed/receipt/world roots/visit-turn/context; permuted maps/catalogue ordering, locale/hash seed; unknown versions, empty pool, required incompatible edge, anti-repeat and absent NPC predicates. | Fixed bytes/hashes; no client/model/time selection input; no manufactured NPC identity, arbitrary revisions or implicit destination. V1 mechanics/prompt/job goldens preserved. | New domain/persistence/context units and affected S5 suites. |

**C02 selector boundary assertions:** use the approved destination definition and
otherwise valid active runtime at the internal Director/condition-selection
boundary, without a database fixture mutation or public-reachability claim.
Independently arrange (a) clock 40 and hold condition true, (b) clock 40 and
release condition true, and (c) all three true. Each must select FAILED
`undelivered_receipt.ending.deadline_reached`, priority 10. At clock 39, hold-only
must select RESOLVED `.receipt_held` (20), release-only FAILED `.dispatch_closed`
(30); synthetic hold+release selects hold. Assert unique IDs/exact priorities
and identical selection with reversed definition order. These are detached
selector tests with no persistent mutation. Normal public play usually settles
the deadline before a later decision; only C02's public journeys prove reachable
outcomes, and all existing clock values/costs remain unchanged.

**C08 combined reload/history acceptance (one continuous case):**

1. Publicly complete the first world and confirm continuation; retain the old
   ending/history as expected test evidence, not as browser state.
2. Retain only the new Session's existing storage-v1 recovery record.
3. Discard every page-memory object and the continuation POST response.
4. Reload and recover the successor View and continuation status using GET.
5. Discover its validated non-null `predecessor` through that GET.
6. Choose previous-world history, GET/validate the reciprocal association, and
   display the old ending/history.
7. Choose return to current journey, GET/revalidate, and display the successor.

Assert exact predecessor/current Session, Run, visit, scenario/content and
immutable admission associations; unchanged old ending/history; and byte-exact
successor recovery storage throughout steps 4–7 (no set/remove). Record every
request in those steps: only GET, zero POST or other write request. Compare
Run/Session/receipt/root/visit/position/binding evidence before step 4 and after
step 7: no continuation duplicate, repair, version advance or other mutation.
While history is displayed, attempts to activate old gameplay/continuation/exit
or mutation retry dispatch nothing. Returning enables only the successor's
current eligible controls. Run the combined rendered C08 case against the normal
deterministic Demo public API/store through a test transport using the listed
E2E child support: steps 1–7 share that actual committed store, with a fresh
client mount at step 4. A separately mocked successor fixture or direct snapshot
seeding does not satisfy this case. C01 also proves the persisted GET associations
on real MySQL; C09 owns Demo parity. No browser execution is implied by this
future automated requirement.

**C04/C08/C09 bounded negatives:** query successor as an unauthorized caller
(404, no association); independently remove referenced source evidence, cross
the source to another Run/line/owner or contradict receipt/visit/position on an
otherwise valid stored family (409 SNAPSHOT_INVALID, no association or mutation,
clean independent fixture state). SQL C04 and Demo C09 prove server rejection.
Rendered C08 supplies a crossed predecessor/reciprocal successor or mismatched
historical View: reject display, retain successor storage/association, lock old
controls and issue no write. Delay a history GET, return to current journey,
then resolve the stale GET; repeat with unmount/client replacement. It cannot
replace the current View, change storage or enable predecessor gameplay.

Implement in dependency order: closed domain/evidence + schema/reconstruction;
versioned content registry and approved content/carryover; atomic service/replay
and continued exit; production API + Demo; Web recovery/history; integrated
acceptance and documentation. Keep useful vertical progress visible, but do not
claim completion with a revision-three-only consumer or an unplayable destination.

Focused future commands, only within appropriately sanitized authorized child
environments, start with the new unit suites, then:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/integration/test_mysql_world_continuation.py -q
.\.venv\Scripts\python.exe -m pytest tests/integration/test_mysql_world_continuation_migration.py -q
.\.venv\Scripts\python.exe -m pytest tests/e2e/test_native_world_continuation.py -q
.\.venv\Scripts\python.exe -m compileall -q src tests alembic
# web/; sanitized deterministic-demo mode, no dotenv or installation
npm.cmd run test:run -- src/runContinuation.test.ts src/api/client.test.ts src/App.test.tsx src/App.recovery.test.tsx src/App.action-loop.test.tsx src/runExit.test.ts src/sessionRecovery.test.ts src/runSetup.test.ts --mode deterministic-demo
npm.cmd run test:run -- --mode deterministic-demo
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build -- --mode deterministic-demo
```

After stabilization run canonical Offline and affected real-MySQL acceptance,
compilation/dependency/Alembic heads/history/metadata checks, affected Web then
complete Web once/typecheck/lint/deterministic build. The new content registry
and classifier affect shared readers: do not blanket-reuse S3-S7-1 native
reconstruction/history/turn evidence. Run those affected suites. Isolate schema
suites, pre-record and restore actual database schema/fixtures/locks, and save
commands, raw logs, exit statuses, source/content/dependency/environment
identities and exclusions externally. Do not rerun broad suites solely for docs.

Unchanged pure S2 exhaustive evidence is eligible for reuse after locating
original logs/proof/counters at
`C:/Users/dylanmonster/AppData/Local/Temp/s3-implementation-20260916-audit/correction`
and checking relevant six source identities/dependencies/environment and scope.
Do not automatically repeat 5,624,910 resolver calls. Historical migrations
001–008 may reuse unaffected internal fault evidence with locatable identities;
new 009 interaction, preservation, constraints and migration/concurrency proof
must be fresh. Original S7-1 and correction locators are in
[the protocol evidence](run_protocol.md#p33-s7-1-implementation-candidate-evidence).
Browser acceptance remains a separately authorized follow-up surface, not an
unrun claim or a substitute for deterministic public/MySQL proof.

## 12. Later allocation, findings and limits

S7-2 implements only the minimum persistent world roots/visits/regions, current
position and one deterministic required successor. It does not complete parent
criteria 10–12. Keep the published ownership:

| Later slice | Retained responsibility; S7-2 prerequisite only |
| --- | --- |
| S7-3 | Important-world revisits, authored importance/cooldown, regional unlock/progression, priority/anti-repeat exceptions and anti-farming. Receives preserved world roots/latest local state; no reset or reward system is presumed. |
| S7-4 | Authorized canon-preserving world-line transitions and normal Run completion. Receives same permanent line and immutable history; S7-2 neither replaces the line nor authorizes canon replacement. |
| S7-5 | Final continuity/revisit/regional/progression acceptance and remaining parent criteria; important-NPC priority only after separately published logical-identity/world predicates. Absence leaves other selection operational. |

No third world, world catalogue breadth, player-selected later destination,
revisit, NPC continuity, reward economy, permanent worldline replacement,
revival, Phase 3.4 state, Phase 6 hook, production Provider distribution or
release readiness. The necessary 4->5 explicit exit is a bounded extension of
S7-1's irreversible semantics, required so finishing the second world does not
reintroduce the occupied-character dead end. It is not S7-4 normal completion.

DF-001 and DF-002 retain their existing register bytes/dispositions. The two
plan-contract findings recorded above are corrected here, pending focused
re-review; no new deferred finding is created. Implementation must fix bounded
defects and record eligible nonblocking findings under the workflow; authority,
corruption, required gameplay/recovery and essential-proof failures cannot be
deferred. Reassess exposure during C08/C09 and before wider release; reload is
not a waiver if required recovery fails. No separate publication-closeout task.

## 13. Documentation scope, approval and review package

This documentation candidate contains exactly:

| Path | Why it changes now |
| --- | --- |
| `docs/phase_3_3_s7_2_same_line_world_continuation_plan.md` (new) | Complete proposed product/technical/implementation/verification contract and sole review authority. |
| `PLANS.md` | Published S7-1, bounded browser evidence and next S7-2 candidate; incomplete S7/Phase 3.3. |
| `docs/architecture.md` | Current S7-1 publication versus proposed content routing, continuation families and state boundaries. |
| `docs/run_protocol.md` | Current lifecycle/evidence/status, preserve historical findings and separate new proposal. |
| `docs/public_client_contract.md` | Published exit behavior and evidence; link proposed continuation API/client extension without advertising it as implemented. |

All code/tests/content/migrations/dependencies, published plans, historical
reviews, workflow/guardrails and deferred register are protected. Complete the
workflow's documentation-synchronization checklist now and during implementation.
Review the full diff including the new file, local links/anchors, current status,
authority, UTF-8/LF/final newline/whitespace, exact scope and protected identities.
No project tests, compileall, Alembic or runtime verification for this task.

After final edits create an external package with exact baseline/ref topology,
per-file lines/bytes/SHA-256/Git blob/mode, full binary/full-index Git patch
including `/dev/null` additions, patch bytes/SHA-256/insertions/deletions,
checks, product table, verification responsibilities and reviewer handoff.
A complete-file aggregate, if supplied, must separately describe its ordering/
framing/size/hash and must not be called a Git patch. Do not embed self-invalidating
candidate hashes in these documents. Relevant baseline or candidate-byte changes
invalidate measurements and approval under the workflow.

The **one operative plan-review success token** for the complete candidate is:

`PHASE_3_3_S7_2_SAME_LINE_WORLD_CONTINUATION_PLAN_INDEPENDENT_REVIEW_APPROVED`

Both `APPROVED` and `APPROVED_WITH_DEFERRED_FINDINGS` dispositions emit that
same token and bind exact candidate identities, the entire technical contract,
and the explicit disposition of P01–P08. Independent technical approval does
not substitute for the user's product approval. If product approval is still
pending, the review must state that dependency; implementation remains blocked.
`CHANGES_REQUIRED`, authoring labels and historical approvals cannot satisfy
this gate. Companion documents define no competing approval token.

The sole **dormant, non-operative implementation-review token** is:

`PHASE_3_3_S7_2_SAME_LINE_WORLD_CONTINUATION_IMPLEMENTATION_INDEPENDENT_REVIEW_APPROVED`

It becomes usable only after this exact plan is approved, P01–P08 are explicitly
accepted, the exact documentation is separately authorized for local commit,
manually published by the user, a clean aligned baseline is confirmed and
implementation is separately authorized. Either successful implementation
disposition then binds complete code/content/docs and C01–C10 evidence.
No token here authorizes staging, committing, pushing, runtime/database/browser
access or implementation. No extra audit or post-commit review stage is added.

Next: **focused independent read-only re-review by the same reviewer** of these
corrections, their direct dependencies and replacement evidence, preserving prior
conclusions for unchanged content. P01–P08 remain presented together for explicit
user approval. S7 and Phase 3.3 remain incomplete.

## Guardrail impact

None. Applies existing DB-001/002, AUTH-001/002, STATE-001/002, API-001,
SCENE-001/002, MODEL-001/002, CONTENT-001, PLAY-001 and environment/Git rules.
No newly confirmed reusable failure warrants changing guardrails or workflow.
