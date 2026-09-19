# Run Protocol, Difficulty, and World Profiles

## Current S7-3 implementation status

S7-2 implementation is published at `6dfbd37d127386b589a1e6c0c43b831aefd70279`.
The independently approved [S7-3 plan](phase_3_3_s7_3_world_revisit_regional_progression_plan.md)
is published at `0ea295e358f526c5101856e4dc2370d66b23b938`, the clean aligned
main/HEAD/local origin/main baseline verified for this implementation without
fetching. P01–P09 are explicitly approved. P02 is operative: the engine determines
eligibility and destination; the player confirms whether to continue, and
cancellation before submission consumes no eligibility. The published plan's
PROPOSED/unapproved language remains frozen historical candidate wording.

The local implementation candidate adds the approved archive journey described
below. Required automated verification is recorded; the complete candidate and
its identities are frozen in the external handoff. The latest focused review returned CHANGES_REQUIRED: F1 is closed and the
original ACTIVE-View mismatch is corrected, but automatic Journey/status
synchronization still enabled exit from inconsistent reads. That remaining
finding is corrected locally; next is focused independent re-review of this
correction, its direct dependencies and replacement evidence. No implementation approval token,
commit, browser acceptance, deployment, real Provider acceptance, limited trial
or broader release is claimed. S7 and Phase 3.3 remain incomplete; S7-4 owns
canon-preserving line transitions/normal completion and S7-5 final integration.
DF-001/DF-002 remain deferred under existing containment and reassessment rules.

## S7-3 implementation candidate evidence

The implemented path is actual first-world RESOLVED or FAILED -> ordinary
second-world continuation -> OBSERVE/TALK/hold -> explicit archive confirmation
-> archive OBSERVE -> seal/RESOLVED or defer/FAILED -> three-visit GET history and
recovery -> explicit 5→6 exit -> separately confirmed same-character admission
and first action. All three profiles and permitted objective boundaries finish;
public depletion and resource-only zero fixtures are separately identified.

Archive entry carries the complete latest ended PlayerState, including zero
composure, without fees, replenishment, items, rewards, character revision or a
new clock. The two original world roots remain immutable. New active revision 5
is distinguished from old terminal revision 5; new termination is revision 6.
One immutable `run_world_visit_entries` record, third visit, successful receipt,
Session initialization, Run CAS and current-position CAS share one commit.
Strict prefix reconstruction validates historical position 4 from committed
S7-2 evidence without fabricating a second persisted position row.

New required archive content is independently pinned to raw SHA-256
`fa0af413ee0db565d9fa2cc3d46971518fccef123790a21fb9f16155be4edc39`.
Its authored public route is documented in [receipt_archive_v1](scenarios/receipt_archive_v1.md).
GET `run-journey` supplies complete path/current/neighbor associations and trusted
path-specific arrival. POST `run-revisit` preserves immutable replay after turns,
exit and later admission. Old continuation POST replay remains valid; old
continuation GET returns `RUN_CONTINUATION_NOT_AVAILABLE` on three-visit families.
View, public-run-context/v1 and recovery storage v1 retain their meanings.

Evidence is retained outside the repository at
`C:/Users/dylanmonster/AppData/Local/Temp/deviation-s7-3-implementation-20260919`.
`R01-R10.json` maps acceptance responsibilities to exact command records, raw logs,
exit codes and per-file source identities. Earlier-source runs are progressive
proof, not automatically final-source evidence; overlapping counts are not added.
The original review returned **CHANGES_REQUIRED** for F1 (confirmed POST target
replaced during recovery) and the original F2 (terminal Journey/ACTIVE View).
The next 610,849-byte candidate, +5,537/-333, SHA-256
`45a46eba6c47f253f96b8087d49bf9cf5c7d1a054c19059be28578d0d153a88f`,
was reviewed at
`C:/Users/dylanmonster/AppData/Local/Temp/deviation-s7-3-focused-rereview-20260919`.
That latest **CHANGES_REQUIRED** verdict closes F1 and the original ACTIVE-View
mismatch, but reproduces one remaining blocker: automatic synchronization enabled
exit using terminal Journey 6 with active Run-status 5. The current correction
awaits the same reviewer's focused re-review; no approval is implied.

The incoming 70-file snapshot, unchanged rendered diagnostic, replacement evidence,
complete corrected candidate and incoming-to-corrected delta are saved at
`C:/Users/dylanmonster/AppData/Local/Temp/deviation-s7-3-consistency-correction-20260919`.
Each patch has its own bytes, line changes and SHA-256 in the external manifest;
all other candidate paths and protected files remain byte-identical. Backend,
content, migrations, dependencies, published plans and DF-001/DF-002 are unchanged.
Existing API-001 covers the correction; Guardrail impact: None.

One shared consistency rule now validates automatic synchronization, explicit
recovery and confirmed exit publication. The pair is bound to the loaded View
and client; generation/client/target checks reject superseded reads. Pending or
contradictory responses cannot authorize exit, continuation/revisit or dependent
action submission, including a previously opened confirmation. Separately read
snapshots may advance: only matching GET reconciliation restores authority,
without rewriting responses, automatic POST retry or uncertain-request disposal.
Run lifecycle stays distinct from current and historical Session lifecycle;
active Runs with ended Sessions and old terminal-5/new active-5 remain supported.
The retained confirmed continuation POST still determines successor identity.

Final `web-final-02` passed **409 tests with one existing skip**, all 12 files,
in 250.23 seconds. `static-final-03` passed typecheck, lint and deterministic Demo
build. The final rendered diagnostic independently exercises the real App with
the review fixture and confirms disabled exit and zero POST. Source-bound commands
are recorded in the new `command-evidence-index.json` and `R01-R10.json`. The previous correction's
`web-final-02` (398 passed, one existing skip) and `static-final-02` are historical
for changed Web source; focused and affected results overlap and are not added.
The new rendered regressions cover both completion orders, reverse and same-revision
lifecycle contradictions, schema-valid association mismatches, matching controls,
ended history in an active Run, confirmation invalidation, retained uncertain
requests, matching GET recovery and late client/target responses. F1/F2 regressions
and legacy/native compatibility cases remain in the complete Web suite.

The original rendered diagnostic is preserved unchanged: it passes on preserved
incoming source by asserting the defect, and fails as expected on corrected
source because exit remains disabled. A separately labelled acceptance derivative
uses the same valid fixtures and asserts disabled exit, no confirmation and zero
POST. Raw commands, logs, nonzero/intermediate attempts and final-source identities
are retained, including the incoming diagnostic's command-path and sandbox
collection failures. The same narrow Offline entry point was escalated after the
sandbox denial; it ran only the rendered diagnostic wrapper and built-in offline
metadata/compile/dependency checks, not a broad backend suite.
Unchanged source, dependency and environment identities and rehashed prior
artifacts support reuse of the accepted backend, Offline, MySQL, S2 and migration
evidence below. Saved database restoration remains historical, not a new observation.
`public-final-01` passed 26 public/explicitly labelled resource-only journeys,
including all 18 profile/objective/ending permutations and eight resource-only
zero cases. These counts overlap focused evidence and are not added to it.
`mysql-affected-runtime-03` passed all 283 affected continuation, admission, exit,
turn-mechanics and character-binding tests against the new head.
`mysql-regional-final-02` passed all 119 collected regional and 010 migration cases;
two subsequently added legacy/pre-admission preservation controls passed in
`mysql-legacy-preservation-final-01`, with unchanged existing test bodies verified
by an AST comparison. `mysql-shared-schema-final-01` passed 52 affected schema,
Run and character-persistence cases; 16 unrelated historical S3 fault cases were
explicitly deselected. These groups are separate from Offline database skips.
`canonical-offline-04` completed successfully: 3077 passed, 709 skipped, 1 deselected, 2 warnings in 2305.45s (0:38:25).
Compilation, dependency consistency, Alembic heads/history and whitespace
checks also passed through the canonical Offline entry point. The one
deselected S2 exhaustive resolver node uses the separately verified original
5,624,910-call proof. The earlier `canonical-offline-03` was stopped at the
user's request and is not a passing run. On resumption, relevant source and
dependency identities were rechecked before reusing the successful Web and
MySQL records; this Offline run accessed neither databases nor real Providers.

Real MySQL work is restricted to mysql+asyncmy / deviation_protocol_test. Its
recorded actual initial state is MySQL 8.0.43, revision 20260916_0007, 19 tables,
zero application rows and a free shared lock. The completed schema groups and
`database-final-check-01` verify exact restoration of that observed state,
including every CREATE TABLE, row, constraint/enforcement and named-lock state.
A failed concurrency-test cleanup was inspected and repaired by exact
recorded test identities; `race-database-restoration-01` proves full restoration.
The historical 009 current-read fixture initially held a metadata read lock
across 010 DDL. Its exact blocked test query was released, the observed partial
prefix and owned rows were inspected, and `metadata-database-restoration-01`
restored the complete initial state. The fixture now establishes 009 before
opening its stale reader. A nullable-column fault also made MySQL rewrite a
CHECK literal's charset marker; `nullable-database-restoration-01` restored the
exact original DDL, and the fixture now restores that marker too.
`mysql-final-boundaries-03` passed all seven replacement corruption, preflight,
ORM and historical current-read checks. Nonzero runs are not counted as successful.
The current-writer migration race also needed its starting revision moved from
008 to 009: its shared Alembic proxy had paused 009 before 010 existed. Both race
tasks now finish before cleanup. The failed attempt left an empty, valid 010
schema; `migration-race-restoration-01` restored the exact recorded initial state.
The first sandbox attempt's
public-journey-01 raw log was overwritten before unique-label enforcement was
added; that missing first log is an explicit evidence limitation. Later failures
and their successful replacements remain separate.

The section-10 inventory governs implementation. Current-head test fixtures,
Demo snapshot/replay inventories, composition route lists and native Web fixtures
are direct consumers and change mechanically.
The exact public route/component inventories in `tests/unit/test_player_character_api.py`
also require the two new endpoints and their closed DTOs; this dependency is
recorded before updating those assertions, with focused and Offline verification.
The exact classifier-query inventory in
`tests/unit/test_run_protocol_binding_persistence.py` also needs the new regional
entry read between world-position and character reconstruction. This mechanical
test dependency is recorded before its assertion update; the query must remain
present to detect orphaned regional evidence even for an old-family request.
Historical migration contracts remain isolated; old packs, published plans and migrations 001–009 are protected.
Unchanged owners retain responsibility through their current shared service or
parser. A per-path disposition and complete candidate identities accompany the
external reviewer handoff. No product scope beyond the published plan is added.

Guardrail impact: None. Regression checks enforce existing authority, transaction,
recovery and evidence-retention rules; no new reusable rule is introduced.

### S7-2 publication and local browser evidence

During this planning task the actual report and request record were read at:

- `C:/Users/dylanmonster/AppData/Local/Temp/deviation-s7-2-browser-20260918/browser-acceptance-report.md`
- `C:/Users/dylanmonster/AppData/Local/Temp/deviation-s7-2-browser-20260918/request-evidence.json`

Report SHA-256:
`68ba838522e9cccc7aeefe3340221fb38b579b6498e184ffc4abf07f29fb1aa8`;
request-record SHA-256:
`2abc5c5ee044230ba2438d4b78f1bfcfa031ad2d5de767582d74be73392de8b1`.
These are inspected prior artifacts agreeing with the user's report, not fresh
browser execution or an independent code approval in this planning task.

| Inspected prior result | Scope and limits |
| --- | --- |
| RESOLVED source | 19 actual source UI actions; composure 6/6 carried, destination starts 0/40. |
| FAILED source | 10 actual source UI actions; composure 4/6 carried, destination starts 4/40. |
| Both full local journeys | Explicit continuation; correct trusted arrival; first destination action; refresh recovery; history/return; destination hold ending; explicit exit; separately confirmed same-character admission and first action. Supplementary public GETs compare Run/context and public player fields. |
| Mutation boundaries | 44 POSTs: character creation 1, admissions 3, actions 36, continuations 2, exits 2. Cancellation window 6 GETs, RESOLVED history 17 GETs and FAILED history 14 GETs, each zero writes. Restart record six GETs/zero writes, two old Sessions 404. |
| Deferred findings | DF-002 partial discovery refresh reproduced; full reload once backend was ready restored discovery with confirmation still requiring explicit selection. DF-001 original containment assertion passed. Neither finding is closed. |
| Environment/cleanup | Report records deterministic local Demo only, no DB/real Provider/.env access, tabs/services stopped and ports released, original 301-file comparison/Git refs unchanged. Planning does not claim it independently reran cleanup. |

The report did not monitor browser storage API calls, request bodies or keys;
history reload behavior is not direct proof of zero set/remove calls. Private
line IDs/roots, SQL atomicity and concurrency were not browser evidence. Both
destination routes chose hold, not release/deadline; not every profile/zero-resource
case was exercised in a browser. Restart coverage was coupled Web/backend with
Web first, not a separate backend-only experiment. No precise lost-response or
storage-fault acceptance was added. Earlier automated evidence retains those
separate responsibilities where applicable. This demonstrates the bounded local
integrated flow, not production readiness, S7 completion or Phase 3.3 completion.

## S7-2 bounded correction (2026-09-18)

Historical correction checkpoint. Incoming independent disposition was
**CHANGES_REQUIRED**, with four P2 findings:
independent destination-pack pinning, missing public arrival annotation,
incomplete confirmed successor association, and incomplete playable-boundary /
FAILED-source cross-process evidence. P01–P08 remain approved. The incoming
68-path candidate and exact binary patch are preserved externally at
`C:/Users/dylanmonster/AppData/Local/Temp/deviation-s7-2-correction-20260918/incoming`.
The published plan remains byte-exact; this correction is not independent approval.

Correction-to-test map and bounded inventory (recorded before implementation):

| Finding | Existing candidate owners | Required focused proof |
| --- | --- | --- |
| R1 | `session_content_registry.py`, its unit suite | Literal approved raw-byte digest; altered same-version / missing / incompatible pack rejection; exact original pack retained; composition regressions. |
| R2 | `world_visit_context.py`, `run_continuation_service.py`, API and Web schemas, App, continuation API/MySQL/rendered tests | Required nullable `arrival` on the new unpublished continuation status only, exactly `{previous_ending_status, previous_ending_title, entry_notice}`; trusted completed reconstruction and approved authored strings; initial/action/reload for both classes and both RESOLVED titles. View, admission context and storage v1 stay unchanged. |
| R3 | `runContinuation.ts`, App and their existing tests | Retain confirmed POST result plus source association; complete immutable visit/context checks on adoption and recovery before View publication, with schema-valid contradictions and progressed positive controls. |
| R4 | Existing destination content, E2E and MySQL continuation suites | Actual hold/release/deadline/exit with profile/objective/zero-composure boundaries; reversed independent selector order; both source classes across processes. |

Direct dependency extension recorded before editing: `.gitattributes` needs one
exact destination-pack `-text` override. The incoming approved raw pack uses CRLF
and SHA-256 `74af55faf2eca0dd826be1f025272d070c23a2000383183e886ec823f495582c`;
the existing JSON `eol=lf` rule would otherwise change its deployment bytes on
commit/checkout. Preserve the content bytes, pin that one exact raw identity and
disable Git conversion for this pack alone. Verify the clean-filter Git blob
hash equals the raw bytes; reject line-ending substitution through the registry.
The same path's whitespace policy recognizes CRLF terminators while retaining
blank-at-eol, blank-at-eof and space-before-tab checks; the inherited LF attribute
is unset. No content byte is repaired to make a whitespace check pass.
No original-world or other file line-ending policy changes. Other extensions must
be recorded here before editing. Real MySQL was used only after dedicated
test-database preflight and recording its actual initial state. Unchanged schema,
locking, commit/fault logic and S2 formulas retain narrowly qualified
C03/C05/C06/C07 and historical evidence; source, method and environment
applicability checks passed in `evidence-reuse.json`.

The additive arrival projection is an explicitly authorized bounded correction
to the unpublished status DTO to fulfill P03's approved visible arrival requirement;
it was absent from the incoming implementation. It does not revise balance,
mechanics, persistence, lifecycle or the frozen plan. At that checkpoint the
corrected unstaged candidate awaited focused re-review; it issued no approval.
Publication/current browser status is recorded above; these historical evidence
identities and limitations remain unchanged.

### Correction C01–C10 evidence

New evidence is saved under
`C:/Users/dylanmonster/AppData/Local/Temp/deviation-s7-2-correction-20260918`.
The new `review-package` owns complete/delta patch identities, raw per-file
identities, commands/logs/exits, final-source applicability and incoming snapshot.
Patch aggregates are distinct from complete-file aggregates.

| Case | Fresh correction proof and retained scope |
| --- | --- |
| C01 | `offline-affected-final` includes actual public eligibility/arrival/action/reload for both classes and distinct RESOLVED titles; `mysql-correction-01` covers all three profiles and the other RESOLVED title through production persisted reconstruction. |
| C02 | `content-final`: 18 completed hold/exit/fresh-admission journeys across three profiles × default/beneficial/adverse permitted bounds × ordinary/zero composure; six actual deadline/exit/fresh-admission journeys; six synthetic 39/40 priority cases each executed with original and reversed definitions. Actual effects, independent integer costs, full PlayerState and unchanged source/character checks are asserted. Release remains covered across all three profiles in public API/MySQL journeys. Entry class follows actual source play; no ending is injected. |
| C03 | Fresh API/MySQL journeys retain exact replay after later action/exit/admission. Original receipt codecs/writers/replay methods and prior fault evidence remain applicable. |
| C04 | Fresh registry substitution/missing/configuration rejection, public DTO bounds, complete Demo corruption matrix and eight SQL corruption cases. Source and successor reject corrupt evidence before annotation disclosure. |
| C05 | Retain original observed real-connection exclusion/race evidence: mutation/locking methods, SQL/Demo repositories/UoWs and concurrency test bodies are unchanged. Registry construction now rejects unsupported bytes before writers exist; valid approved bytes remain identical. |
| C06 | Retain original staging, rollback, cancellation, uncertain-commit/disposal proof: transaction/receipt/publication code and injected fault cases unchanged. No new writer or commit boundary. |
| C07 | Retain original 009/008 migrations, constraints, downgrade/failure and zero-difference ORM metadata proof; all schema/migration dependencies unchanged. No new migration matrix was run. |
| C08 | Corrected rendered normal public Demo tests cover both arrival classes/titles, first action and successor-only remount, history/return, schema-valid crossed visit/predecessor, storage retry/client replacement, and progressed adoption. Rejection preserves confirmed identity/storage and dispatches no extra POST. Full Web and tooling results are in the external index. |
| C09 | Fresh four cross-process journeys: both source classes × hold/release, each across two hash seeds with identical complete public traces/private store, exit and fresh admission. Fresh affected original replay, native/Demo composition and public schemas. |
| C10 | Fresh independent registry digest, Git byte-preservation and mismatch controls plus unchanged canonical root/receipt/context and v1 prompt/mechanics tests. S2 exhaustive 5,624,910-call evidence and historical 007 internal faults revalidated against original artifacts and environment. |

Canonical sanitized `offline-affected-final`: **714 passed, 1 deselected**;
`content-final`: **30 passed**; `registry-deployment-final`: **9 passed** (overlaps
the earlier registry selection). The first two runs have the existing schema-name
warning; the affected run also records the unavailable Turkish locale warning.
All canonical commands completed compileall, dependency, Alembic heads/history
and whitespace stages. These are focused correction passes, not a claim that the
old 2,954-case broad run passed on corrected source. The sole exhaustive S2 node
is reused; other selected S2 tests ran. Failed/intermediate runs remain history.

`web-affected-final-02`: **208 passed**; `web-full-final`: **369 passed, 1 skipped**
across ten files. The focused cases are included in the full result, not additive.
The skip is the unchanged explicit presentation-probe gate. `types-final`,
`lint-final` and `build-final` passed; the deterministic Demo build transformed
103 modules. All final production Web source identities match these records.
Intermediate fixture-name/assertion-timing failures, the fixed arrival-status
clearing window, the first lint dependency warning and a wrapper argument-quoting
failure remain in raw history. None is counted as a complete pass.

`mysql-correction-01`: **15 passing cases**, exit zero, covering six public
hold/release journeys, the other RESOLVED title and eight corruption cases. Quiet
output supplies no deselection total. The later test-helper assertion comparing
the expected title directly to the source View is additionally covered Offline;
production Python bytes are unchanged from this MySQL run. Each fixture restored
its initial schema. Fresh initial/final snapshot records are byte-identical,
SHA-256 `1fb00d7f67da9069a00c30972d079ecbbab600790858232698d3236f3a9533d2`:
MySQL 8.0.43, `mysql+asyncmy`, only `deviation_protocol_test`, revision 007,
18 empty application tables plus version row, exact definitions/enforcement and
free shared named lock. No production database, `.env`, Provider or browser access.

The original reviewer Python diagnostics reproduced both content defects and both
missing arrival classes before correction. Their unchanged post-correction runs
exit nonzero at the expected fixed boundaries; these are negative diagnostic
results, not test-suite passes. The unchanged TypeScript diagnostic now rejects
its old fixture's missing required arrival member. A separately labelled fixture
adaptation proves the original substituted visit stays schema-valid but fails the
new confirmed-association check, with matching positive control. The normal
rendered public-Demo regressions provide the fresh integrated proof.

Guardrail impact: **AUTH-001** now requires independent approved content identity
and preserved deployment bytes; **API-001** retains confirmed immutable transition
associations across reads. Existing **DB-001** and workflow cleanup corrections are
preserved; workflow bytes and DF-001/DF-002 dispositions are unchanged. No new
deferred blocker, product decision, schema or later-slice implementation is added.

## P3.3-S7-2 implementation candidate

The following records the incoming implementation and its original evidence.
Its four P2 gaps and replacement evidence are owned by the correction section
above. Earlier runs are not relabelled as complete corrected-source passes.

The same-line continuation plan is independently approved and published at
`2c272487a2f12c60c28ada95dd9a3f1edf1d42ba`. The user approved P01–P08 and
authorized implementation on 2026-09-18. Candidate-time pending wording is
historical; published plan/review bytes remain unchanged. At this incoming
implementation checkpoint the increment was unstaged for independent review;
no approval or browser acceptance was claimed then. Subsequent publication and
bounded browser evidence are recorded above, without relabelling these runs as
later-source passes or claiming broader readiness, S7 or Phase 3.3 completion.

Actual public play demonstrates eligible first-world endings, explicit handoff
into 《未送达的回执》, legitimate destination actions, reload, old history and
return, all destination endings, explicit continued exit and separately confirmed
fresh admission. Continuation preserves the Run, permanent line, character
association and full remaining PlayerState. RESOLVED starts at 0; FAILED at 4;
deadline maximum is 40. There is no refill/reward/character revision, third world,
revisit or normal Run completion. Destination content SHA-256:
`74af55faf2eca0dd826be1f025272d070c23a2000383183e886ec823f495582c`.

Dependency inventory amendments recorded before their edits:

| Additional direct consumer | Dependency and bounded verification |
| --- | --- |
| `tests/e2e/support/demo_replay_child.py` | Exhaustive Demo snapshot manifest needs three new maps; historical one-world replay requires them empty and retains its prior bytes. Fresh cross-process Offline coverage. |
| `web/src/App.continuation.test.tsx` | Isolates combined C08 using the normal Demo child/public transport/store; complete Web suite and affected recovery suites executed. |
| `tests/integration/test_mysql_native_run_admission.py` | Shared current production reconstruction reads 009 tables; only current runtime head advances, while historical migrations retain explicit versions. Fresh admission/turn/exit readers and exact database restoration. |
| `docs/engineering/codex_workflow.md` | Repeated Windows sandbox failure during final pytest temporary-directory cleanup. Preserve failed completion evidence, exact outside-sandbox rerun and prohibition on deleting unrelated temp directories. |

Final inventory reconciliation also records `tests/unit/test_repository_and_uow.py`:
its FakeSession needs the real AsyncSession `info` surface consumed by new repository
composition. This one-line mechanical fixture addition was recorded here after
editing, rather than prospectively; it changes no product/schema/authority contract.
Its existing regression suite ran in the canonical Offline verification. Reviewers
should retain this bounded process deviation in the candidate assessment.

Plan-listed files left unchanged retain sufficient contracts: exit routes and
`runExit.ts` already dispatch through the extended service/status; existing
Run/admission/turn/Session/prompt/scenario unit suites and Web client/App/recovery/
exit suites exercise shared consumers without duplicating their assertions.
New matrices live in the dedicated continuation suites. All plan section 10
no-change production dependencies, original content and earlier migrations remain
unchanged. Current-head fixture updates do not rewrite historical 005–008 contracts.

### S7-2 evidence map

External evidence and the frozen review package are at
`C:/Users/dylanmonster/AppData/Local/Temp/deviation-p33-s7-2-implementation-20260918/review-package`.
The package records exact commands, raw UTF-8 logs, exits, source/content/environment
identities, final applicability, failed/interrupted history, per-file inventory,
protected comparisons and the complete binary/full-index patch including new files.
Its patch aggregate is distinct from complete-file byte/line aggregates.

| Case | Executed evidence and scope |
| --- | --- |
| C01 | `mysql-s7-2-final-02`, canonical Offline public API/E2E suites: actual Easier/Extreme play and the other RESOLVED ending; carryover/local reset/history; first action; hold/release; exit/fresh admission. No fabricated ending snapshot substitutes for play. |
| C02 | Incoming content tests covered zero-composure deadline failure and permitted-extreme arrival at the decision, but omitted successful completion and reversed-order controls. R4 replacement evidence is above. |
| C03 | Canonical Offline service/API and MySQL journey/race suites: exact replay after later actions/exit/fresh admission, changed-body conflict, competing fresh key; replay consumes no clock, preparation or commit. |
| C04 | `matrix-final-01` independently removes every canonical root/receipt key and corrupts every new storage column; existing 16 Demo cases and eight SQL cases cover missing/crossed evidence, coherent rehash/local-memory corruption, active source jobs and exact content. Foreign owner/controller paths return 404; owned corruption returns opaque 409 without writes or null fallback. |
| C05 | `mysql-s7-2-final-02`: observed real-connection same/different-key waiting; continuation versus exit/admission/retirement; final-turn revalidation; migration/writer exclusion in both orders; current-read downgrade refusal. |
| C06 | Same MySQL run: exception/cancellation at nine service boundaries and each of five individual world-row inserts, uncertain commit before/after durability, cleanup exception/cancellation and exact retry. Canonical Offline Demo trial-publication tests prove no partial maps. |
| C07 | `mysql-009-final-03` (64 cases), `mysql-008-fault-final-01` (30), MySQL family preservation/constraint cases and `mysql-active-null-final-01`: enforced constraints, nullable current/revision operands, contradictory schema refusal, every 009 DDL/disconnect/lock/disposal boundary, and restoration. `metadata-final-01`: no ORM differences; one 009 head. |
| C08 | `web-c08-final-01` (13 rendered public-Demo cases), `web-full-final-01` (361 passed, one existing skip): double confirmation, exact retry, old/new record reload, lost/malformed response, storage failures, stale return/unmount/client replacement, successor-only remount/predecessor GET/history/return and continued exit/reselection. History performs GET only with no storage writes. |
| C09 | Incoming two-process continuation E2E covered RESOLVED source only; FAILED source is added by R4 above. Original replay/standalone/Dynamic suites remain separately scoped. |
| C10 | `goldens-final-01`, `context-final-03`, canonical Offline S5/mechanics/prompt suites: independent request/operation/creation/visit/root/receipt/context bytes and hashes, strict scalar/actual-model rejection, registry order/empty pool/closed edge/anti-repeat, exact visit envelope and unchanged v1 prompt/formulas. |

Canonical Offline result: `2954 passed, 586 skipped, 1 deselected, 2 warnings in 1155.86s (0:19:15)`. Only the unchanged S2 exhaustive
node is deselected and validly reused: actual **5,624,910 resolver calls**, original
logs/instrumentation/source/dependencies/Python/platform verified by
`s2-reuse-applicability.json`. Other S2 tests ran normally. The first full run
reached 100% but failed sandbox temp cleanup; `offline-final-01-attempt-2` is the
exact canonical outside-sandbox rerun on final code/content/test source. Matrix,
NULL and golden additions also have named focused passes; the package lists
source differences instead of relabelling earlier broad runs as final-source passes.
Fresh shared MySQL suites are `mysql-shared-native-01` and
`mysql-shared-readers-02`. The independent review corrects the prior annotation-only
qualification: shared-native also predates changes in continuation domain code and
migration 009; shared-readers also predates migration 009 changes, and both have
repository declaration differences. The original review's per-run identity record
is preserved. Later original final 009/continuation runs cover those changes;
the correction does not relabel the shared runs as entirely source-identical.
No blanket reuse of reconstruction/turn consumers occurs. Unchanged 007 internal
fault evidence alone is reused under `historical-migration-reuse.json`; 008 and all
009 interactions have fresh proof. Counts overlap and must not be summed.
Unchanged pre-007 migration internal fault suites were not rerun or counted;
the selected shared-reader command explicitly excludes those historical schema
fixtures while running the affected current-head reconstruction consumers.

Canonical verification also executed compileall, pip dependency checks and
Alembic heads/history. Web typecheck, lint and deterministic-demo build passed.
No dependency install, real Provider/Live call or interactive browser was used.
No production database was accessed. Schema suites ran sequentially.

The dedicated database was verified as `mysql+asyncmy` / `deviation_protocol_test`.
Its actual initial state was revision `20260916_0007`, 18 empty application tables,
one version row, original definitions/enforcement and a free shared named lock.
`database-initial.json` and `database-final-restored.json` are byte-identical:
SHA-256 `1fb00d7f67da9069a00c30972d079ecbbab600790858232698d3236f3a9533d2`.
Authorized fixtures/migration fault prefixes were explicitly restored; no runtime
read repair, automatic compensation or reconnect-and-continue was introduced.

Confirmed implementation defects were fixed with regressions: locking finalization
must current-read the active-job prerequisite after a concurrent final turn;
sealed initial memory must match independently reconstructed authored facts;
historical reload must not rewrite successor storage, and client replacement must
retain an uncertain exact continuation request while rejecting stale completion.
DB-001 records the reusable current-read rule; the workflow's Offline/database
section records the repeated final-cleanup evidence failure and exact rerun rule.
Fixture/verification failures remain
in raw history, including the MySQL ALTER CHECK charset-marker restoration fix.
DF-001 remains contained by process-local invariant locale; DF-002 remains deferred
with existing explicit discovery retries/reload containment and fresh rendered
regressions. Neither disposition changed; no new deferred code defect is claimed.

Documentation synchronization covers behavior/API, architecture, roadmap/status,
authored-content identity, evidence/limits and the confirmed DB-001 rule. Published
plans/reviews and prior migrations are protected. The external inventory documents
every modified/new path and inspected no-change boundary. At that historical
checkpoint review was the next step; it authorized no staging/commit/push or
later-slice implementation. Current publication/planning status is above.

Status: **Approved product design. P3.3-G0 is approved, published, frozen, and
complete. The corrected exact no-migration P3.3-S1 implementation is
independently approved, committed, manually published by the user, and
confirmed clean/aligned at
`6212a760a549920c1c11dcb01e07566945df5556`; its exact three-document
publication closeout is independently approved, committed, manually published,
and fully closed at `4d146679e782ff555819b411fc5048e55299de4d`.
The exact P3.3-S2 deterministic profile-resolution plan is approved, committed,
manually published by the user, and confirmed at
`2f3f84a4d63d00d2e3bbbe0e4eb6dafd9c3435fe`. Its exact five-path
implementation is independently approved and published at
`20eab60a99c093f2ccf0224dee200e142fc194b6`. The S3 plan is independently
approved and published at `465c53d24ea96e64988dce8ef4c8a015d0e72814`
(`docs(run): approve Phase 3.3 S3 persistence plan`). Earlier `CHANGES_REQUIRED`
reviews remain accurate history; the frozen plan's candidate-time wording is
historical. S3 implementation and migration `20260828_0006` are independently
approved with DF-001 deferred and published at
`a53f8e65ad74c62bc6c40b9de26222eb889084f0`. The corrected S4 plan was independently approved with DF-001 deferred and
published at `42411b27537bbcd7c6a88f6cc0e4c5e8ca871fcd`. Its frozen candidate-time
wording is historical. S4 internal implementation was independently approved
and published at `34dc752295ba270617e5d29020f3a0c0b133544e`. DF-001 remains
deferred. The S5 plan was independently approved and published at `ff866d2fd40181e0bf27937d255d70ebd1ae1544`.
S5 implementation is independently approved with DF-001 deferred and published
at `86c258e9ad2e64199cabf8650bf6f3a7b5f04d87`. S6 plan is approved and published
at `4365721`; separately authorized S6 implementation received `CHANGES_REQUIRED`
for two Web findings. Focused re-review closed character selection and returned
a second `CHANGES_REQUIRED` solely for automatic recovery's scenario/content
binding. Subsequent independent approval and publication at
`2f144599af5977e871c7a3466c52896b6a36510c` close S6 implementation. Its bounded
local Demo browser journey passed. S7-1's plan is independently approved and
published at `9fab18d`; implementation is published at
`41d68aac13ca9129b7f6e08fad5f015987603fda`, including the reviewed nullable
terminal-CHECK correction. Bounded local Demo browser acceptance covers both
endings, exit/re-entry and recovery. S7-2 has an independently approved published plan and approved P01–P08;
its implementation is published at `6dfbd37` with inspected bounded local browser
evidence. S7-3 has an approved published plan and P01–P09; its local implementation
candidate awaits focused independent re-review. S7-4/5 remain outside this increment. DF-002
records the observed discovery-refresh issue with explicit reload containment.
Phase 3.3 remains incomplete.**

The playable-loop-first workflow amendment is published at `67a5d501`. See
[PLANS.md](../PLANS.md#immediate-delivery-priority)
for delivery priority and the workflow's prospective S3 applicability; it
changes no technical contract or feature ownership described here.

Phase ownership: **Phase 3.3**

Phase 8 historical planning amendment: **The approved and published Phase 8 Structured
Player Character Run Entry and Minimum Playable Loop planning authority defines
one narrow Session-backed activation path below. Its planning bytes were
published at `de4d8c0e35c7864948306d751a00aaf295ff77ff`, so P8-G0 is complete.
P8-S1 discovery and P8-S2 atomic internal admission are implemented and
published; P8-S2 is closed at `70815b181624e5475d2d978bef0db1ed3b22324e`.
The P8-S3 plan is approved and published at
`e17172ad0a9febe4ec9e3a96e7be8204c9722d29`, and its implementation introduced
normal public `POST /v1/runs` activation. The first independent implementation
review returned `CHANGES_REQUIRED` with five bounded findings, and all five
corrections are complete. A subsequent independent read-only re-review found no
remaining actionable technical defect but formally returned `CHANGES_REQUIRED`
solely for one Medium documentation-synchronization finding. The complete
15-path candidate then received focused independent read-only approval and was
committed and published at `ac07a5fe267adfb0281ec2658b2fcbd0085f6eb1`.
P8-S3 is complete. The dedicated P8-S4 implementation plan was independently
approved and committed/published at
`375a2a7ae018c9c9c79272e5de7da703818d1f20`. Its implementation received
`STRUCTURED_PLAYER_CHARACTER_P8_S4_IMPLEMENTATION_CORRECTION_INDEPENDENT_REVIEW_APPROVED`,
was committed as `187d41ba3035c8d717c2fb2578a805402255d979`, and was
manually published by the user. P8-S4 deterministic Demo parity is complete;
the dedicated P8-S5 implementation plan was independently approved and
committed/published at `dceecaf0d7a33ccde07f519f83997489acd5fc86`, remained
frozen during implementation, and its corrected implementation received
`STRUCTURED_PLAYER_CHARACTER_P8_S5_CORRECTED_IMPLEMENTATION_REVIEW_APPROVED`.
The exact eight-path Web implementation was committed and published at
`2ce56a757beed8a3989d38453da3b6d80342ca05`. P8-S5 is complete. The frozen
P8-S6 implementation plan was approved and published at
`4edf2e3341e60632765b85796e8554797c645692`. At the historical P8-S6 candidate
checkpoint, its executable evidence had passed through C21 while those
documentation bytes were unapproved, unstaged, uncommitted, and unpublished;
Phase 8 and the overall project were then incomplete. That candidate-time
status did not mark Phase 3.3, Phase 6, or Phase 7 complete.** This paragraph
preserves the historical P8-S6 candidate record. Current status: P8-S1 through
P8-S6 are implemented and
complete; the closure documentation was independently approved, committed, and
published at `7dae3f5bbd3055e60e33b8ce6b1e05ce75f4824d`, and no P8-S7 exists.

P4-S1 status: **Minimum Run Core is the historical prerequisite at
`e821cd922b61868097667b12c2b64cf8089a9681` (`feat(run): implement minimum run
core`). P4-S1a is implemented at `748003319ececa548b68b351746afbb2d54c66bb`
and P4-S1b at `8eabf9d4c3c592ea1de50f443f1816de9a46dc8f`. The completed binding
is internal-only; no public route exists, the reserved public
`RunService.bind_player_character(...)` command remains rejected, and the
constructible lifecycle remains `pre_first_turn`.**

## Current P3.3-S6 implementation boundary

The [S6 public API, Demo, Web, projection and recovery plan](phase_3_3_s6_public_api_demo_web_projection_recovery_plan.md)
was independently approved with DF-001 deferred and published at `4365721`.
Its frozen candidate wording is historical. The implementation connects an explicit
character -> profile/world -> permitted overrides/presentation -> native S4
admission -> authoritative Session View -> S5 play -> reload/recovery -> authored
Session ending journey. Existing legacy entry remains compatible. Discovery and
native POST are additive; View exposes only allowlisted frozen setup, including
exact numeric pressure and the approved S5 output bands. No public field becomes
mechanics, catalogue, relationship or canon authority.

The plan owns exact contracts, Demo adapters, Web uncertainty and GET-only
recovery, dependency-derived paths, verification allocation and review tokens.
[Public contract status](public_client_contract.md#proposed-p33-s6-native-public-extension)
describes the implementation independently approved and published at `2f144599`.
The two earlier `CHANGES_REQUIRED` reviews remain history; current approval and
bounded browser evidence are recorded [below](#s6-publication-and-local-browser-evidence).
The [S7-1 plan](phase_3_3_s7_1_post_ending_run_exit_plan.md) was independently
approved and published at `9fab18d`. Its first post-ending Run transition is
published at `41d68aac`; see [current evidence](#s7-1-publication-and-local-browser-evidence)
and [preserved implementation evidence](#p33-s7-1-implementation-candidate-evidence). DF-001/DF-002
remain deferred. No separate S6 closeout,
new story/world content, production Provider, S7 continuity or Phase 3.4 state
is included. Phase 3.3 remains incomplete and no release readiness is claimed.

## Goals

- Give players bounded pre-game control over world pressure and narrative
  presentation.
- Keep objective mechanics, character definition, presentation, and
  relationship atmosphere under separate authorities.
- Resolve all permitted choices before play, then freeze a versioned protocol
  for deterministic use throughout the run.
- Let a narrative model render confirmed state and results without giving it
  authority to invent mechanics, permanent state, or canon.

## Non-goals

- Completing Phase 3.3 or implementing P3.3-S3 through P3.3-S7 through the
  bounded P3.3-S1 foundation, its completed closeout, the published S2 plan and
  implementation, or the published documentation-only S3 plan.
- Letting prose or model preference change resources, success, betrayal, death,
  relationship progression, or permanent facts.
- Replacing scenario-authored facts, character definitions, or engine rules.
- Defining NPC residence progression or production Provider pricing.
- Letting a player freely select an arbitrary world or directly select every
  later world.

## Published Phase 3.3 plan, implemented P3.3-S1, and publication closeout

The repository-specific
[Phase 3.3 Run Protocol implementation plan](phase_3_3_run_protocol_implementation_plan.md)
was originally authored against
`49bb7c9c8f616e4036cbe56549f9621544ebf84b`. Its first independent review
returned `CHANGES_REQUIRED`; the bounded B1-B4 correction later received
`PHASE_3_3_RUN_PROTOCOL_IMPLEMENTATION_PLAN_INDEPENDENT_REVIEW_APPROVED`, was
separately committed and user-published as
`76064d200d1aa5af7cddff22d33acb03e608e598`, and was confirmed at a clean,
aligned baseline. P3.3-G0 is approved, published, frozen, and complete.

The frozen plan records the exact repository compatibility boundary without
changing current legacy runtime behavior:

- existing Phase 8 revisions 1/2/3, immutable character binding, first Session
  participation, Session initialization family, V1 evidence/fingerprints/
  replay, recovery, and production/Demo/Web/Dynamic Narrative compatibility are
  legacy behavior;
- existing rows are valid and replayable only when trusted stored legacy proof
  passes its current strict decoder and cross-row integrity checks. They receive
  no synthesized protocol, profile, world, visit, region, or world state and no
  rewrite, backfill, refingerprint, relabel, default, or Provider/canon authority;
- caller-controlled absence cannot select legacy handling;
- a Phase-3.3-native Run will require explicit trusted server-owned versioned
  state, an exact validated and authorized protocol/profile binding, and—before
  native admission—an explicit authored entry-world ID/version. Missing,
  malformed, unknown, contradictory, or incompatible state fails closed;
- `scenario_id` remains scenario-definition identity only. It is never world,
  visit, region, protocol, or profile identity.

The plan's no-migration P3.3-S1 representation has exactly one initial envelope
schema, `run-protocol-envelope/v1`. The independently approved and published
implementation supplies that representation, strict original-state validator,
canonical encoder, v1 decoder, trusted version dispatcher, golden and boundary
evidence, and no-I/O in-memory stored-record conversion/reconstruction
boundary. It contains only an exact versioned profile reference and the
approved presentation values `world_tone`, `reality_boundary`, and
`relationship_overlay`. It contains no numeric engine values, defaults,
overrides, catalogue definitions, scenario/world/visit/region fields, prose,
secrets, or Provider output. Representation validity remains separate from
profile authorization, lookup, and deterministic resolution, and S1 creates no
durable Run Protocol.

The implementation's first independent read-only review returned `CHANGES_REQUIRED`
for four findings: missing operative S1 review authority, missing exact
pre-normalization scalar-type enforcement, synthetic 1,024/1,025 canonical
branch evidence incorrectly characterized as genuine valid-envelope evidence,
and stale Phase 8/Dynamic Narrative status text in `architecture.md`. The
authority defect and ceiling clarification were independently approved and
published in commit `a722dbf7f07e6e55cd4918a80b5153d6043f2100`. That amendment
was separately committed, manually pushed by the user, and confirmed as the
published predecessor authority.

The corrected exact seven-path implementation preserved the complete frozen S1
contract. Its carrier validators require exact `str` for profile ID and schema
literal and exact `int` for profile version before Pydantic normalization, so
equal-valued subclasses, `StrEnum`, `IntEnum`, and Boolean-as-integer inputs fail
both direct construction and original-state revalidation. Genuine real-encoder
maximum evidence uses the frozen 128-byte `A` profile ID, maximum signed-positive
64-bit profile version, `balanced`, `deviant`, and `charged`; it is exactly 329
bytes with SHA-256
`0e0b1f498e1bf51656f1c5e5c742074e864da9678964c048087f52bdf5066e78`.
The internal 1,024/1,025 canonical-guard test is defensive branch-isolation
evidence only, while the public decoder retains genuine raw-input boundary
evidence at both sizes. Neither 1,024-byte ceiling changes.

The historical pre-correction seven-path patch identity of `80,019` bytes and
SHA-256 `064dd425f1b412495ddbf62e6995b18d1266c5b0b7dc2ab7d12b41c6e58bfe25`
is non-operative after correction. The corrected candidate received
`PHASE_3_3_S1_IMPLEMENTATION_INDEPENDENT_REVIEW_APPROVED` and was committed
byte-identically as the one-parent non-merge commit
`6212a760a549920c1c11dcb01e07566945df5556`, directly after `a722dbf7`, with
exact subject `feat(run): implement Phase 3.3 S1 protocol envelope`. The user
manually pushed `a722dbf..6212a76, main -> main`. Public `main` was confirmed
identical to that commit, and local `main` and local `origin/main` were aligned
at ahead/behind `0/0`, with a clean worktree and empty index. The implementation
publication is complete and awaits no further implementation review, commit,
push, or published-baseline confirmation.

The published implementation inventory is exactly:

| Kind | Exact path | Diff |
| --- | --- | ---: |
| Documentation | `PLANS.md` | `+99/-46` |
| Documentation | `docs/architecture.md` | `+107/-18` |
| Documentation | `docs/run_protocol.md` | `+90/-26` |
| Production | `src/deviation_protocol/domain/run_protocol.py` | `+463/-0` |
| Production | `src/deviation_protocol/infrastructure/run_protocol_persistence.py` | `+85/-0` |
| Tests | `tests/unit/test_run_protocol.py` | `+760/-0` |
| Tests | `tests/unit/test_run_protocol_persistence.py` | `+327/-0` |

That is exactly seven files, 1,931 insertions, 90 deletions, and a complete
binary-safe patch of 95,987 bytes with SHA-256
`30e592f751937786d58f64e90a36aa0355b66803c7fb06eafea96f4ab7371e23`.

The former authoring verification (`126` focused tests, `222` adjacent Run
tests, and Offline `2,463 passed, 182 skipped`) is historical evidence for the
pre-correction bytes.

The final corrected and independently reviewed evidence accepted for the exact
published implementation is 141 focused P3.3-S1 tests, 222 tests across the
eight adjacent Run suites, passing `compileall`, and canonical Offline
verification at `2,478 passed, 182 skipped`. Dependency consistency passed.
Alembic `heads` and `history` were metadata-only at head `20260729_0005`, with
a linear migration graph from `20260719_0001` through `20260729_0005`. There
was no database connection and no Provider, Live, or network operation. These
results are accepted publication evidence, not merely authoring evidence, and
they are not rerun by the later documentation-only closeout task.

### Exact implemented and deferred boundary

The exact 22-symbol S1 contract and public signatures remain frozen. The 18
domain symbols own only the exact envelope epoch and trusted record-version
constants, profile ID/version/reference carriers, three presentation enums,
strict v1 envelope, validation and unsupported-version exceptions, original-
state validator, canonical encoder, v1 decoder, and trusted version dispatcher.
The four infrastructure symbols own only the frozen slotted no-I/O stored
carrier, stored-record integrity exception, deterministic storage conversion,
and detached reconstruction. Domain remains independent of infrastructure.

The published implementation preserves strict exact types, UTF-8 without BOM,
NFC, duplicate-key rejection, byte-identical canonical compact JSON, positive
signed-int64 profile versions, closed enum values, exact corruption taxonomy,
both 1,024-byte ceilings, detached no-I/O reconstruction, and no fallback,
repair, upgrade, downgrade, coercion, or default. The exact 193-byte golden and
329-byte genuine maximum identities above remain normative S1 evidence. Raw
1,024/1,025 decoder tests are genuine input-boundary evidence; the unreachable
canonical guard test remains defensive branch isolation only.

P3.3-S1 does not implement durable Run Protocol persistence; an ORM model;
database table or column; migration; repository or Unit of Work integration;
Run binding; profile catalogue, lookup, default, override, or deterministic
resolution; objective numeric mechanics; native Run admission; entry-world
freezing; public API or projection; Demo, Web, or Provider integration; world,
visit, region, revisit, progression, or continuity behavior; identity or memory
schema; or P3.3-S2 through P3.3-S7. It does not implement the complete Run
Protocol or complete Phase 3.3.

Legacy Run revisions 1/2/3 remain unchanged. Their existing strict proof,
binding, participation, V1 evidence, replay, recovery, production, Demo, Web,
and Dynamic Narrative behavior remains unchanged. No legacy Run receives
synthesized protocol, profile, world, visit, region, or world-state authority.
`scenario_id` remains scenario-definition identity only.

Phase 3.4 remains later. Phase 6 remains paused under
`PHASE_6_NO_CURRENT_EXECUTABLE_SURFACE`, and Phase 7 remains inactive. Phase 8
is complete at P8-S6 and no P8-S7 exists. Dynamic Narrative corrective and
publication work remains closed. Production Provider Distribution remains
deferred.

### Post-publication status-synchronization closeout

At its explicit 2026-08-15 candidate-time checkpoint, the exact closeout
contained only `PLANS.md`, `docs/architecture.md`, and this document and was
unapproved, unstaged, uncommitted, and unpublished. That historical candidate
then received its exact independent approval, separate commit authorization,
commit, user-controlled manual push, and clean aligned published-baseline
confirmation. The closing commit is
`4d146679e782ff555819b411fc5048e55299de4d`, with exact subject
`docs(run): close Phase 3.3 S1 publication`. P3.3-S1 is fully closed and
requires no further review, commit, push, confirmation, or synchronization.

The historical closeout review token was:

`PHASE_3_3_S1_POST_PUBLICATION_STATUS_SYNCHRONIZATION_INDEPENDENT_REVIEW_APPROVED`

It has satisfied only its exact historical closeout gate and is non-operative
for current or future work. It grants no S2 plan approval, implementation, Git,
or later-slice authority.

### Published P3.3-S2 implementation

The dedicated
[P3.3-S2 deterministic profile-resolution plan](phase_3_3_s2_deterministic_profile_resolution_plan.md)
preserves its explicit 2026-08-16 candidate-time history, but those exact plan
bytes subsequently completed independent approval, separate commit, user manual
publication, and clean aligned confirmation at
`2f3f84a4d63d00d2e3bbbe0e4eb6dafd9c3435fe`.

Historically, the first independent read-only review returned `CHANGES_REQUIRED` for four
material plan findings. The second independent read-only review returned
`CHANGES_REQUIRED` for exactly two remaining Medium findings: the unfrozen
universal-verification method and overlapping exception ownership for the S1
profile reference nested in an S2 catalogue entry. The third independent
read-only review returned `CHANGES_REQUIRED` for exactly one remaining Medium
finding: repeat and aggregate public-resolver invocation counts were not frozen
or asserted. None of those three reviews emitted a plan or implementation
approval verdict. The later corrected plan completed its own separate approval
and publication lifecycle; that approval did not approve an implementation.

The published implementation realizes the frozen five-parameter
numeric domains, three version-1 profiles and defaults, exhaustive per-profile
overrides, complete authority and precedence, resolver v1 with no randomness/
PRNG/seed, canonical binding of the complete S1 envelope and exact override
presence, domain-separated SHA-256 goldens, exact 33-symbol pure-domain module,
and exact five-path budget. The focused literal oracle directly completed all
`104,165` maps across 27 presentation triples, with `2,812,455` primary and
`2,812,455` immediate repeat calls—`5,624,910` public resolver invocations.
It was independently approved, committed, manually published by the user, and
confirmed at `20eab60a99c093f2ccf0224dee200e142fc194b6`. It grants no
persistence, migration, runtime/public/categorical activation, S3, or later-
slice authority.

The published frozen planning allocation is exactly:

1. **P3.3-G0 — Plan and compatibility freeze candidate**;
2. **P3.3-S1 — No-migration protocol/profile foundation**;
3. **P3.3-S2 — Deterministic profile resolution**;
4. **P3.3-S3 — Persistence and legacy/native compatibility**;
5. **P3.3-S4 — Native Run admission and entry-world freezing**;
6. **P3.3-S5 — Objective mechanics application and trusted prompt-context compilation**;
7. **P3.3-S6 — Public API, Demo, Web, projection, and recovery parity**; and
8. **P3.3-S7 — Later worlds, visits, regions, revisits, progression, and persistent world continuity**.

P3.3-S7 belongs to Phase 3.3 and is unrelated to the nonexistent P8-S7.
Phase 8 remains implemented and complete at P8-S6. Publication of this
allocation did not authorize any implementation slice. P3.3-S1 was separately
authorized, independently approved, and published as the bounded foundation
described above, and its closeout is fully closed at `4d146679`. The exact S2
plan and bounded implementation are published at `2f3f84a4` and `20eab60a`.
The dedicated S3 plan is independently approved and published at `465c53d`;
S3 implementation is published at `a53f8e65ad74c62bc6c40b9de26222eb889084f0`,
approved with DF-001 deferred. The
[Published S4 native admission/entry-world plan](phase_3_3_s4_native_run_admission_entry_world_plan.md)
was independently approved and published at `42411b2`. S4 implementation is
independently approved and published at `34dc752295ba270617e5d29020f3a0c0b133544e`.
The [published S5 plan](phase_3_3_s5_objective_mechanics_prompt_context_plan.md)
is independently approved at `ff866d2`; its candidate-time wording is historical.
S5 implementation is independently approved and published at `86c258e9`.
S6 public flow is independently approved and published at `2f144599`. S7-1
post-ending Run exit is published at `41d68aac` under its approved published
plan (`9fab18d`). The [published S7-2 plan](phase_3_3_s7_2_same_line_world_continuation_plan.md)
authorizes the first same-line successor; its product choices and technical plan
are approved. Implementation is published at `6dfbd37` with inspected bounded
local browser evidence. The S7-3 plan is published at `0ea295e` with P01–P09 approved; the local
implementation candidate awaits focused independent re-review. Later S7 allocation is preserved.
DF-001/DF-002 remain deferred.

P3.3-S5 owns deterministic application by
server-owned policies of `resource_pressure`, `social_trust`,
`consequence_severity`, `information_opacity`, and `conflict_intensity`, with
objective mechanics tested independently from prompt construction. It also
exclusively owns any separately reviewed exact numeric-to-categorical
mechanics/prompt projection from `resource_pressure` to the product labels
`Scarce`, `Fluid`, and `Generous`. It additionally owns a deterministic, pure
or side-effect-free, Provider-independent compiler from
validated trusted protocol state to canonical context bytes or one exact
deterministic structured representation fixed by that plan. It must not call a
real Provider. Provider calls remain outside database transactions and locks.

P3.3-S6 received its bounded plan and independent public-contract approval at
`4365721`; its separately authorized implementation is now a candidate. It owns public API,
OpenAPI, Demo, Web, projection, recovery, or client representation of
`Scarce`, `Fluid`, and `Generous`. S5 and S6 may only project from the exact
numeric S2 value; neither may change, round, clamp, or replace it.

The P3.3-S5 compiled context grants no outcome, resource, relationship, death,
world-selection, permanent-state, or canon authority. Presentation changes
permitted expression only. Regression evidence must prove that model output
cannot create, change, or override mechanics or canon. Relationship overlay is
presentation-only and cannot mutate Phase 3.4 relationship or residence state.

## Minimum Run-core prerequisite for player-character Phase 4

The complete Run Protocol remains approved product design and is not complete
or durably implemented. The independently approved and published P3.3-S1
foundation now supplies only the standalone no-migration boundary described
above. Before Structured Player Character P4-S1, only the smaller
prerequisite specified by the
[Minimum Run Core Implementation Plan](minimum_run_core_implementation_plan.md)
has been implemented, independently finally approved, committed, and pushed.

That prerequisite freezes:

- distinct strict opaque `RunId` and `ContinuousStoryLineId` carriers;
- one Run permanently owning exactly one continuous story line, rather than a
  generalized container for unrelated lines;
- a canonical current Run record, immutable Run revisions, and a positive
  monotonic `RunStateVersion` with compare-and-swap persistence;
- the closed minimum lifecycle values `pre_first_turn`, `active`, `completed`,
  and `terminated`;
- a separate immutable Run-owned Session participation record, with no Run,
  line, or character-binding column added to `game_sessions`;
- a Run application service as the one transaction owner for minimum Run
  mutations and the future character binding; and
- an all-null authoritative storage seam for the future exact
  player-character and applicable contract/revision reference.

`pre_first_turn` and `active` are active continuous-story-line states for
binding exclusivity. `completed` and `terminated` are non-active historical
states. The minimum core creates only `pre_first_turn`; it does not implement
the transition to any other lifecycle value. When a later authorized terminal
transition has a character binding, Run authority must make the binding
historical in the same atomic change.

The minimum aggregate is allocated before the first turn and therefore does
not pretend that a resolved protocol, entry world, current visit, or scenario
already exists. The existing lifecycle below remains authoritative: before
the first turn can begin, the resolved protocol plus
`entry_world_id`/`entry_world_version` must receive their Run binding and be
frozen. Full Phase 3.3 implementation continues to own that transition,
world/visit identity, later-world selection, revisits, and world-line rules.

Session participation is created only through trusted Run orchestration.
Caller-supplied Session data cannot select or replace a Run; participation
does not grant character ownership or controller authority. Multiple distinct
trusted Sessions may participate in the same Run, while one Session cannot
participate in conflicting Runs. This record does not activate public resume,
reconnect, cross-tab, browser-restart, or multi-device behavior.

The completed minimum Run core and its production composition remain internal.
The reserved character-binding seam was populated by the completed separately
authorized P4-S1 work. That internal completion does not activate a public
binding route or the `active` lifecycle transition.

## Phase 8 Session-backed minimum admission

Status: **Implemented and complete through independently approved, committed,
and published P8-S6 closure at
`7dae3f5bbd3055e60e33b8ce6b1e05ce75f4824d`; no P8-S7 exists**

The explicit Phase 8 allocation and detailed implementation boundary are owned
by the
[Structured Player Character Run Entry and Minimum Playable Loop plan](structured_player_character_run_playable_loop_plan.md).
The original exact seven-document planning candidate received
`STRUCTURED_PLAYER_CHARACTER_RUN_PLAYABLE_LOOP_PLAN_REVIEW_APPROVED` and was
committed and published at `de4d8c0e35c7864948306d751a00aaf295ff77ff`.
Later modifications to the canonical planning bytes require fresh exact-byte
independent review before a separately authorized documentation commit; that
commit precedes user publication and clean published-baseline confirmation.
P8-G0 is complete and published. P8-S1 eligible-character discovery is
implemented, accepted, committed, and published. P8-S2 atomic internal Run
entry is implemented, accepted, committed, and published at
`70815b181624e5475d2d978bef0db1ed3b22324e`; its implementation and F1/F2/F3
evidence are closed, and P8-S2 is not being reopened. The
[P8-S3 implementation plan](structured_player_character_p8_s3_implementation_plan.md)
was independently approved and committed/published at
`e17172ad0a9febe4ec9e3a96e7be8204c9722d29`. Its implementation reaches
the existing atomic admission authority through normal production composition
and public `POST /v1/runs`, with real-MySQL replay/no-write decisions and the
canonical Session terminal journey verified. The API owns no transaction and
the Run remains active and immutably bound after scenario settlement.
Its five bounded first-review corrections are complete. The subsequent
independent read-only re-review found only the Medium documentation-
synchronization finding described above and returned `CHANGES_REQUIRED`. The
complete 15-path candidate later received focused independent read-only approval
and was committed and published at
`ac07a5fe267adfb0281ec2658b2fcbd0085f6eb1`. P8-S3 is complete. P8-S4 Demo
parity was then implemented under the dedicated approved plan, independently
approved with
`STRUCTURED_PLAYER_CHARACTER_P8_S4_IMPLEMENTATION_CORRECTION_INDEPENDENT_REVIEW_APPROVED`,
committed as `187d41ba3035c8d717c2fb2578a805402255d979`, and manually
published by the user. P8-S4 is complete. The dedicated
[P8-S5 implementation plan](structured_player_character_p8_s5_implementation_plan.md)
was independently approved and committed/published at
`dceecaf0d7a33ccde07f519f83997489acd5fc86`, remained frozen during
implementation, and its corrected implementation received
`STRUCTURED_PLAYER_CHARACTER_P8_S5_CORRECTED_IMPLEMENTATION_REVIEW_APPROVED`.
The exact eight-path Web implementation was committed and published at
`2ce56a757beed8a3989d38453da3b6d80342ca05`. P8-S5 is complete. P8-S6
fresh evidence now confirms the unchanged Session-backed Run protocol. The
designated MySQL 8 production-ASGI journey entered one active, immutably bound
Run and played all 19 authoritative actions to Session settlement; replay
produced no extra Provider call or durable write, and the Run remained active
and bound at state version 3 after the terminal `ENDED`/`RESOLVED` View. The
deterministic Demo journey separately completed the same canonical action,
request-status, authoritative-View, and terminal sequence with exactly four
completed guarded Provider calls. Focused Web evidence confirmed Session ID
storage before the first View GET, a single action POST, confirmed-202 GET-only
status polling, authoritative View refresh, and no automatic replay. Those
results and the synchronized closure documentation were independently approved,
committed, and manually published at the P8-S6 closure baseline. They complete
Phase 8 only; they do not implement or approve Phase 3.3, Phase 6, or Phase 7.

### Narrow authority amendment

Phase 8 authorizes one composite trusted operation for the current
Session/scenario engine:

```text
owned active unbound Player Character
  -> create Run revision 1 at pre_first_turn
  -> bind exact character/reference in revision 2
  -> create one existing gameplay Session
  -> attach first Session participation in revision 3
  -> change Run lifecycle to active in that same revision
  -> one Run-entry-owned UnitOfWork commit
```

The first participation retains `ATTACH_SESSION` as its Run mutation kind. No
new Run lifecycle value or mutation token is selected. The existing active
binding and `ApplicableCharacterReference` remain exact and immutable across
activation. A Run may not change character through any Phase 8 surface.

This is a narrow compatibility amendment to the earlier rule that an active
Run must already have a full resolved protocol and entry-world binding. The
amendment applies only to Phase 8 Session-backed Runs using the current
implemented scenario lifecycle. It does not implement, simulate, or claim:

- a resolved/frozen Run Protocol;
- `entry_world_id`, `entry_world_version`, world, visit, or region identity;
- world/profile parameters or permitted overrides;
- later-world selection, revisits, world-line movement, or progression; or
- Phase 3.3-native Run acceptance.

The request's `scenario_id` remains the existing versioned scenario identity
and MUST NOT be relabelled as a world or visit. The server selects the
scenario's already validated default static character definition for current
Session initialization. That definition remains distinct from the Run-bound
Structured Player Character.

When full Phase 3.3 is implemented, its plan must explicitly preserve,
version, or migrate these legacy Session-backed active Runs before applying a
Phase 3.3-native protocol/world requirement to them. Phase 8 selects no future
column, migration, backfill, or compatibility representation.

### Admission authority and transaction

The public client may submit only an owned Player Character ID, its expected
current revision, one scenario selected from the existing bounded public
catalogue, and an idempotency key. It cannot submit Run, line, Session, world,
visit, lifecycle, binding, applicable-reference, static character-definition,
state, or authority data.

One application entry service resolves principal/controller authority, locks
and validates the exact active unbound character, evaluates compatible replay
before new-operation stale/eligibility rejection, creates all identities and
authoritative state server-side, and commits the Run revisions/current rows,
binding, existing Session initialization family, participation, and successful
receipts in one UoW. Repositories flush and never commit. No nested service
commit, generic retry, compensation, outbox, saga, or uncertain-commit recovery
is permitted.

Concurrent admissions for one character serialize at the Player Character
lock and retain the unique active-character database backstop. Exactly one new
Run may commit. The loser receives exact replay, incompatible-key conflict, or
already-bound ineligibility without a second Run, Session, participation, or
binding.

Published P8-S4 makes this same established admission service reachable in the
deterministic Demo through process-local Player Character, Run, receipt,
participation, and Session repositories sharing one UoW publication boundary.
It does not originate revisions 1/2/3 or activation. Exact entry replay returns
the committed Run/Session result without another mutation or generator
consumption, while conflicts and rollback publish no partial authority and do
not reuse an already emitted deterministic identity.

### Progression, completion, recovery, and exit

After admission, the existing Session View/action/request-status protocol is
the only Phase 8 progression authority. Current stale, pending, uncertain,
Provider-failure, rollback, and same-tab recovery rules remain unchanged.

Published P8-S5 now connects the primary Web journey to the existing public
Player Character discovery/create and Run-entry contracts, then to the existing
Session progression protocol. It does not use the legacy `POST /v1/sessions`
route for that journey; the route remains available for existing uses. A
validated Run-entry success is persisted through the existing same-tab Session
recovery record before the authoritative View is loaded. Thereafter safe View
recovery is GET-only and never replays Run entry. Mutation uncertainty retains
the exact pre-POST idempotency key/body pair for explicit manual retry only,
with no automatic retry, duplicate in-flight send, stale-completion authority,
or disclosure of the key or private Run authority.

The accepted rendered provider-backed action path continues through the
established `202` response, request-status `PENDING`, request-status
`COMMITTED`, and authoritative View refresh. Existing terminal behavior remains
the Session/scenario behavior below; P8-S5 adds no Run terminal transition.

In Demo, a failed View read after committed admission likewise does not undo
the Run, binding, Session, participation, activation, or receipts. The returned
Session identity remains the authority for retrying the existing View read; no
Demo-specific recovery operation exists.

An existing scenario ending is not a Run ending. `ENDED`, `RESOLVED`, and
`FAILED` remain Session/scenario projections. The Run remains `active`, its
character binding remains active, and participation remains immutable. Phase 8
does not implement `completed`, `terminated`, binding historicalization,
later-Session attachment, later-scenario admission, Run resume/discovery, or
line continuation. Clearing browser/sessionStorage state is client-only and
never mutates the Run or character.

### Phase relationship

Phase 6 subject-reference hooks are not a prerequisite because Phase 8 creates
no new memory/relationship/consequence fact. Phase 7 remains separately
allocated and unimplemented; Phase 8 owns only its own bounded final evidence
and status slice. Neither allocation is absorbed, reinterpreted, or marked
complete.

The current schema and migration `20260729_0005` already admit Run lifecycle
`active`, the three existing mutation kinds, active binding, Session
participation, CAS, and the required receipt families. Phase 8 therefore
authorizes no ORM or migration change. A contrary implementation finding is a
plan stop condition.

## Responsibility separation

The pre-game UI may expose these choices together, but their internal authority
remains separate:

| Concern | Authority | Effect |
| --- | --- | --- |
| Difficulty/world rules | Engine-owned world profile | Objective resources, trust environment, failure consequences, information opacity, and conflict incentives |
| Character definition | Versioned character definition | Abilities, knowledge boundaries, personality, and viewpoint |
| Run Protocol | Frozen structured presentation contract | How confirmed state and results are narrated |
| Relationship atmosphere | Presentation overlay | Tension and expression only; never objective relationship progression |

Difficulty may recommend presentation defaults, and a character may recommend
viewpoint-compatible defaults. Neither merges its authority into the Run
Protocol. Relationship atmosphere is not world tone.

## World selection and ordering

Status: **Approved product design — not implemented**

- At the beginning of a run, the player may select the entry world only from a
  small, explicitly authored set of eligible initial worlds.
- The player cannot freely select an arbitrary world.
- Once selected and the run begins, `entry_world_id` and
  `entry_world_version` are frozen for that run and cannot be changed.
- The player does not select later worlds directly.
- Later worlds are selected dynamically by the engine from the currently
  eligible world pool.
- Dynamic selection is deterministic and reproducible from engine-owned state
  and seed. It does not rely on uncontrolled model randomness.
- Selection may consider prerequisites, completed worlds, current run state,
  difficulty/world profile, major hidden-setting requirements, and only the
  important-NPC recovery predicate boundary defined below.
- Pure randomness must not prevent required narrative progression or recovery
  of a major hidden setting or important NPC.

`death_certificate_v1` is the current canonical Demo and vertical-slice
scenario. It is not permanently designated as the production entry world.

The published S4 implementation supplies the exact internal catalogue: `world.death_certificate`
version 1 maps to scenario `death_certificate`, content
`death-certificate-1.1.0`, default character
`character.death_certificate.investigator`. This reuses approved authored content
without new story canon and is not a permanent/default public-world choice. Public catalogue exposure belongs to S6. Later-world
weighting, anti-repeat, progression and priority-injection remain Deferred.

### Important-world revisits

Status: **Bounded S7-3 archive route implemented as a local candidate; general
revisit selection remains deferred. Independent implementation review pending.**

P02 in the published, independently approved S7-3 plan amends the former
no-approve/no-veto wording: the engine determines eligibility and destination;
the player confirms whether to continue. Cancellation before submission consumes
no eligibility. The player does not select a destination or grant unlock/canon
authority. The implemented bounded route is the held receipt's archive visit;
general arbitrary revisits remain outside this increment.

- An explicitly authored important world may remain eligible for later engine
  selection after the player has already visited it.
- The engine owns selection and eligibility; the player owns consent to continue.
- Revisiting a world is not automatically a scenario restart or state reset.
- Confirmed world state, important NPC state, player-caused consequences,
  discovered facts, and unresolved events persist unless an engine-authorized
  world-line transition explicitly changes them.
- A world's first accessible region does not define the power level, scale, or
  narrative depth of the entire world.
- An initial world may appear beginner-oriented only because the player begins
  in a remote, protected, or peripheral region.
- Later visits may reveal previously inaccessible regions, major factions,
  powerful inhabitants, hidden history, and higher-level conflicts within the
  same persistent world.
- Re-entry must provide meaningful progression, revelation, or consequence
  rather than unrestricted repetition, duplicated rewards, or resource
  farming.
- The engine may prioritize an important-world revisit when required for:
  - a major hidden-setting revelation;
  - an important NPC's recovery or later arc;
  - unresolved world consequences;
  - access to a newly eligible region;
  - a major scenario or world-line event.
- Ordinary worlds do not require later recovery merely because they were
  previously visited.
- Anti-repeat rules and random weighting must not permanently exclude an
  important world whose authored recovery conditions have become true.
- Re-entry eligibility, persistent world state, region unlocking, and recovery
  priority are engine-owned.
- The model must not independently return the player to a world, reset world
  state, unlock a region, or invent a required recovery event.

### Important-NPC recovery predicate boundary

P3.3-S7 recovery priority is engine-owned. It may consume only an
already-authorized logical-NPC-identity predicate and authored-world predicate
published by their owning authorities before the applicable P3.3-S7
subdivision. It must not derive logical identity from runtime `npc_id`, treat a
scenario NPC definition as cross-scenario identity, or match by name,
appearance, role, template, model output, or semantic similarity. It must not
create counterpart, reincarnation, copy, successor, replacement, or other
continuity relations.

P3.3-S7 recovery priority must not read or mutate relationship state, golden
memory, cross-scenario NPC persistence, Phase 6 subject-reference hooks, an
identity-resolution schema, or a memory schema. If no already-authorized
predicate exists, important-NPC priority is unavailable and selection continues
deterministically using other authorized eligibility and progression inputs.
Absence must not manufacture identity, block unrelated valid selection, imply a
Provider decision, promote a runtime NPC, or pull Phase 3.4 or Phase 6 into
Phase 3.3. Future integration requires a separately published identity/memory
authority and a fresh bounded P3.3-S7 subdivision review.

The design distinguishes three conceptual identities without defining current
schema fields:

1. the persistent identity of an authored world;
2. an individual visit or run-local entry identity; and
3. the region or scenario content accessible during that visit.

These identities prevent a revisit from being treated as a fresh copy of the
world while allowing each visit to expose different authored content.

## Main pre-game dimensions

### World tone

- `Grim`
- `Balanced`
- `Heroic`

### Resource pressure

- `Scarce`
- `Fluid`
- `Generous`

These three names are approved product vocabulary. S5 now implements an internal
projection only; the labels carry no authority and are not public representation. P3.3-S2 resolves only the exact numeric
`resource_pressure` objective value. `Scarce`, `Fluid`, and `Generous` are not
S2 resolver inputs, profile identities, override values, alternative objective
values, S1 presentation fields, or current runtime authority, and no label may
be accepted as an alias for a numeric S2 value.

P3.3-S5 owns the approved exact numeric-to-categorical internal
mechanics/prompt projection. P3.3-S6 owns any separately reviewed public API,
OpenAPI, Demo, Web, projection, recovery, or client representation. Neither
slice may change, round, clamp, or replace the numeric S2 value; each may only
project from it. The approved S5 internal bands are Generous 0..30, Fluid
35..65 and Scarce 70..100 on the S2 lattice. Published S5
uses these bands in trusted context. Published S6 exposes
the same exact numeric values and bands publicly, under its separately approved
plan; implementation is independently approved and published at `2f144599`.

Numeric resource pressure is an engine-owned world/difficulty input. A model
may narrate confirmed effects supplied by later trusted mechanics/prompt
authority but cannot directly add, remove, restore, spoil, or otherwise modify
resources.

### Reality boundary

- `Lawful`
- `Deviant`
- `Chaotic`

### Relationship atmosphere overlay

- `off`
- `veiled`
- `charged`

This overlay changes presentation only. It cannot create affection, change a
relationship stage, satisfy a relationship flag, or unlock residence.

## Difficulty/world parameters

The engine owns these parameters:

- `resource_pressure`
- `social_trust`
- `consequence_severity`
- `information_opacity`
- `conflict_intensity`

Profiles provide defaults. Permitted player overrides occur only before the run
starts.

### P3.3-S2 exact pure-domain implementation — published

The dedicated
[published P3.3-S2 plan](phase_3_3_s2_deterministic_profile_resolution_plan.md)
freezes the complete decisions below. The exact five-path
implementation is independently approved and published at
`20eab60a99c093f2ccf0224dee200e142fc194b6`.

All five values are implemented as exact discrete Python integers in `0..100`
inclusive with step `5`. They are normalized engine profile points, not
percentages, probabilities, quantities, or multipliers. Exact profile defaults
are implemented as:

| Stable profile ID/version | Human label | Resource | Trust | Consequence | Opacity | Conflict |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `difficulty.silent-hunting-ground` / `1` | `Extreme — Silent Hunting Ground` | 95 | 10 | 95 | 90 | 90 |
| `difficulty.fragile-alliance` / `1` | `Standard — Fragile Alliance` | 60 | 45 | 65 | 60 | 60 |
| `difficulty.open-expedition` / `1` | `Easier — Open Expedition` | 25 | 70 | 35 | 30 | 35 |

All five parameters are directly overrideable only within these
inclusive step-`5` profile ranges:

| Parameter | Extreme | Standard | Easier |
| --- | ---: | ---: | ---: |
| `resource_pressure` | 80..100 | 40..75 | 10..40 |
| `social_trust` | 0..25 | 30..65 | 55..85 |
| `consequence_severity` | 80..100 | 45..80 | 20..50 |
| `information_opacity` | 75..100 | 40..75 | 15..45 |
| `conflict_intensity` | 75..100 | 40..75 | 20..50 |

Including independent absence for each parameter, the implementation's exhaustive
finite domain is exactly `12,348` Extreme maps from
`(5 + 1) × (6 + 1) × (5 + 1) × (6 + 1) × (6 + 1)`, `59,049` Standard maps
from `9^5`, and `32,768` Easier maps from `8^5`: exactly `104,165` valid
profile/override maps. The three world tones, three reality boundaries, and
three relationship overlays create exactly `3 × 3 × 3 = 27` presentation
combinations.

Published S2 evidence has one frozen method. In
`tests/unit/test_run_protocol_resolution.py`, a direct exhaustive test must
declare independent literal tuples for the exact three profile IDs/versions,
their exact five-value defaults, every valid integer for each profile/parameter,
and all 27 presentation triples. Production catalogue data and enum iteration
may be compared with, but may not generate, that oracle. One `object()` sentinel
represents absence. Each dimension is the sentinel followed by its independent
valid integers in ascending order; fixed-order Cartesian generation omits only
sentinel keys and retains every explicit integer, including one equal to the
profile default.

Before resolution, the test must assert the `12,348`, `59,049`, `32,768`,
`104,165`, and 27 counts. It must then call the public
`resolve_run_protocol_objectives` facade for every map and every presentation:
exactly `333,396` Extreme, `1,594,323` Standard, and `884,736` Easier distinct
trusted inputs, for `2,812,455` total.

For each exact input, the frozen order is: select the profile in existing fixed
Extreme, Standard, Easier order; generate its override map in existing fixed
Cartesian order; select the presentation triple in existing fixed presentation
order; make one primary call to public `resolve_run_protocol_objectives`;
validate that primary result against the independent expected result; then
immediately make one real repeat call to the same public callable using the
exact same trusted input objects, or an exactly equivalent permitted detached
input only where the relevant test expressly specifies detached reconstruction;
compare exact resolved objective output, canonical resolution-input bytes, and
fingerprint; and increment each separate primary or repeat counter only after
its corresponding public call returns successfully. Every primary result must
equal the independently computed defaults-plus-present-overrides tuple, retain
exact override presence and canonical order, omit absent keys, identify the
exact profile pair, and accept every Cartesian combination. Across each map's
27 presentations, the first primary objective result is only the comparison
baseline; presentation values never enter or alter the five objective fields.
Fingerprints may differ because the canonical S1 envelope differs.

The separately asserted primary public-call counters are exactly `333,396`
Extreme, `1,594,323` Standard, `884,736` Easier, and `2,812,455` aggregate. The
separate repeat public-call counters are exactly the same four values. Combined
public-resolver invocation counters are exactly:

- Extreme: `333,396 + 333,396 = 666,792`;
- Standard: `1,594,323 + 1,594,323 = 3,188,646`;
- Easier: `884,736 + 884,736 = 1,769,472`; and
- aggregate: `2,812,455 + 2,812,455 = 5,624,910`.

The counter structure separately asserts primary count per profile, repeat
count per profile, aggregate primary count, aggregate repeat count, combined
count per profile, and aggregate combined public invocation count. Exact private
variable names remain a test detail. The meanings are not interchangeable:
`2,812,455` distinct trusted inputs, `2,812,455` primary public calls,
`2,812,455` repeat public calls, and `5,624,910` aggregate public resolver
invocations.

No static or property argument, source inspection, representative set, random
or Hypothesis sampling, partial enumeration, short circuit, or deduplication
may replace a required public resolver call. A repeat is an immediate real
public invocation, not reuse of the primary result, memoized test data,
comparison of an object with itself, an internal-helper call, source inspection,
a cached assertion that suppresses the invocation, or a deferred later pass.
Ordinary test optimization is permitted only if all `2,812,455` distinct
trusted inputs, all `2,812,455` primary calls, all `2,812,455` repeat calls, all
`5,624,910` aggregate public resolver invocations, and all assertions still
occur. Unknown, duplicate, missing, wrong-type, Boolean/enum/subclass,
global/profile-range, wrong-step, unknown-profile, unsupported-version,
corruption, and contradictory-reference failures remain in a separate negative
matrix and increment none of the distinct-input, primary, repeat, per-profile
combined, or aggregate combined public-invocation counters.

The implementation has no server-selected profile default and no
cross-parameter rule beyond the Cartesian product of those exact ranges.
Missing/unknown/retired/unsupported profile pairs, duplicate or unknown
override keys, missing/invalid/out-of-range/wrong-step values, contradictions,
and corrupted state fail closed. Equal-to-base overrides remain explicitly
present. Recommendations have no authority.

Resolver epoch `run-protocol-resolution` version `1` is implemented as a pure
non-random algorithm with no PRNG or seed. Its compact canonical input binds
the resolver version, authorized profile pair, the complete canonical S1
envelope as lowercase hex, and exact canonical overrides. Scenario/content and
server identity are excluded because no S2 rule consumes them. A
domain-separated, length-framed SHA-256 preimage produces lowercase hexadecimal
fingerprints. Presentation fields are audit-bound but never read when deriving
the five objective values. The exact byte grammar, independently reproduced
goldens, 33-symbol contract, five-path implementation budget, and review gates
remain exactly those frozen by the published plan. The implementation is the
published authority at `20eab60a99c093f2ccf0224dee200e142fc194b6`.

The first independent implementation review returned `CHANGES_REQUIRED` for
two material findings. The resolution input's trusted profile field exposed
`Annotated[RunProtocolProfileDefinitionV1, SkipValidation()]`, allowing ordinary
construction with a fresh equal profile or hostile integer label and allowing
that invalid input to be nested in an ordinary resolved-output constructor.
The first correction restores the exact plain field annotation, performs
complete owner-ordered nested revalidation, preserves the exact authoritative
profile identity for valid construction, and makes both demonstrated attacks
fail during construction without waiting for a later explicit validator.

The implementation preserves field-level exception ownership. Direct invalid S1
carrier construction retains `pydantic.ValidationError`, direct invalid
presentation-enum construction retains `ValueError`, and the wrong exact
envelope top-level type retains `TypeError`. Mutation of an exact S1 envelope,
its embedded profile reference, presentation enums, or another nested S1-owned
carrier retains `RunProtocolValidationError`; a well-typed unsupported S1
dispatcher pair retains `UnsupportedRunProtocolVersionError`; and the published
stored boundary retains `RunProtocolStoredRecordIntegrityError`. S2 never
catches, wraps, translates, adds a cause layer to, or replaces those outcomes.

For the S2 catalogue, the authoritative tuple binding/type/cardinality/order,
the three entry object identities and exact `RunProtocolProfileDefinitionV1`
types, and the entry fields `label`, `base_values`, `override_rules`, and
`server_default_eligible` are S2-owned. The exact five named fields and nested
`value` state under `base_values`; the exact ordered `parameter`, `minimum`,
`maximum`, and `step` state under every `override_rules` member; the
`RUN_PROTOCOL_OBJECTIVE_PARAMETER_ORDER` tuple; and the original-state metadata
of those exact S2 carriers are also S2-owned. Replacement, removal, duplication,
or reordering of entries, replacement by an equal fresh entry, and corruption
of that closed S2 list raise `RunProtocolResolutionIntegrityError`.

The catalogue entry's `profile_ref` boundary is split without overlap. Presence
of the field and its association by identity with the one catalogue-owned
reference originally installed in the authoritative entry are S2 structure.
The already-associated exact `RunProtocolProfileRefV1` object, its
`profile_id`, `profile_version`, nested `value` fields, exact types,
normalization, validation, and original-state invariants remain S1-owned.
Rebinding the association to another object, even an equal or malformed one,
is S2 corruption; mutating only the internals of the still-associated object is
S1 corruption. Outer ownership never absorbs nested S1 authority, and no object,
field value, or association belongs to both classifications.

Because S1 publishes no standalone profile-reference validator, the S2 plan
freezes one private adapter: embed the same exact reference by identity in an
otherwise-valid private `RunProtocolEnvelopeV1` created with `model_construct`
and fixed `balanced`/`lawful`/`off` presentation, then call the published
`validate_run_protocol_envelope_v1`. The adapter is validation-only and never
resolved, encoded, fingerprinted, returned, or used as objective input. Its
`RunProtocolValidationError` and direct cause behavior pass through unchanged.

Catalogue lookup order is deterministic: validate the caller reference's exact
top type and then its S1 state; validate catalogue tuple type, identity,
cardinality, entry order/identities, and objective-parameter order; for each
entry in Extreme, Standard, Easier order validate exact S2 entry type/identity
and outer state, then `label`, `base_values`, `override_rules`, and
`server_default_eligible`, then the `profile_ref` association, then the nested
reference through S1; only then match exact ID/version and return the
authoritative catalogue object. The first check to fail determines the outcome.
In particular, an S2 field failure precedes nested S1 validation, a malformed
replacement reference fails at the S2 association check, and internal mutation
of the still-associated reference reaches the unchanged S1 outcome. All
resolver, override, compatibility, reconstruction-input, encode, fingerprint,
and dispatch paths reuse this order with no wrapper or fallback.

The plan's N20 changes only the authoritative Standard entry's S2-owned
`base_values.resource_pressure.value` from `60` to `65` and requires exactly
`RunProtocolResolutionIntegrityError`. Separate N22 retains the outer tuple,
entry, and association, mutates only the nested S1
`profile_ref.profile_version.value` from `1` to `True` by the published hostile
original-state technique, invokes lookup with a separate valid Standard
reference, and requires exactly the published `RunProtocolValidationError` and
direct `pydantic.ValidationError` cause without an S2 wrapper. N22 is distinct
from S2 resolution state N16, equal fresh definition N17, S2 catalogue state
N20, and S1 envelope corruption N21.

N10 and N11 retain every direct `pydantic.ValidationError` case and now also
begin from valid override/value carriers, apply each hostile post-construction
scalar mutation, invoke the public resolver, require exact
`RunProtocolResolutionIntegrityError`, produce no output/fingerprint, and
restore state in `finally`. Corrected N16 no longer calls a private validator or
expects `_S2StateError`: it exercises public compatibility/resolution boundaries
for override, resolution-input, resolved-output, fingerprint, nested scalar and
tuple state plus relevant `__dict__`, fields-set, extra, and private metadata.
Every category produces the public integrity exception and no partial result;
N17, N20, N21, and N22 retain their distinct subjects and outcomes.

Legitimate detached S2 reconstruction starts from trusted profile ID/version
and reacquires the exact catalogue-owned profile through the implemented exact
`lookup_run_protocol_profile` contract. Only value-authoritative
carriers, including the S1 envelope through its published reconstruction
boundary and fresh proposal/input values, may be rebuilt. An equal fresh
profile definition remains unauthorized and rejected; re-lookup restores
catalogue authority without preventing identical objective output, canonical
resolution input, and fingerprint.

Corrected local authoring evidence has completed focused S2 verification with
all 23 tests and two reported warnings in 2,566.53 seconds (42:46), directly
executing the complete invocation counts above. Published S1 regression passed
141 tests; the eight adjacent Run suites passed 222 tests; compileall and
tracked/new-file whitespace checks passed. Canonical Offline completed full
pytest with `2,501 passed, 182 expected skips, 2 warnings` in 2,982.13 seconds
(49:42), then passed compileall, dependency consistency, metadata-only Alembic
heads/history at `20260729_0005`, and diff checking. Its sanitized child had no
database, Provider, or Live variables and made no database connection. The
former 22-test focused result and Offline `2,500 passed, 182 skipped, 2
warnings` result are historical pre-correction evidence only. The candidate
was subsequently approved and published at `20eab60a`; the implementation
activates no durable, runtime, public, or categorical representation.

### Published P3.3-S3 plan and implementation

The dedicated
[P3.3-S3 persistence and legacy/native compatibility plan](phase_3_3_s3_persistence_legacy_native_compatibility_plan.md)
is independently approved and published at
`465c53d24ea96e64988dce8ef4c8a015d0e72814`
(`docs(run): approve Phase 3.3 S3 persistence plan`). The following correction
history preserves the earlier verdicts; fixed planning findings are historical
closures, not deferred debt. Its first independent review returned
`CHANGES_REQUIRED` with exactly five material findings: a hidden production test
writer, an unimplementable/conflated legacy proof, a race-unsafe downgrade,
unsupported 1062 key identification, and non-executable vectors. The first
correction freezes the same 19-column durable representation and exact S1/S2
reconstruction while making production S3 binding access read-only. Native test
rows are constructed only by a direct `AsyncSession.add()` helper in
`tests/integration/test_mysql_run_protocol_binding.py`, never by production code.

The corrected classifier proves persisted Run revisions/receipts, immutable and
current active character/controller association, participation, structural
Session/event/snapshot initialization, canonical namespaces/fingerprints, and
cross-row source consistency. The shared loading sequence first uses the
persisted current Run's character-reference triplet to load/decode its immutable
revision, then supplies that exact object as
`referenced_player_character_revision` to the unchanged complete Run validator.
Current-character/controller and legacy Session proof remain later separate
checks. Missing/partial/crossed references detected by S3 have no-cause stored
integrity failures; immutable codec, reference-constructor, and Run-validator
failures receive one S3 wrapper with the exact owning lower exception as direct
cause, at their respective first-failure positions. It contains no caller
principal. The unchanged
`RunEntryService` continues to resolve and lock the caller-owned controller/
character, authorize replay and disclosure, bind results to
`principal.player_id`, and enforce configured source authority; the unchanged
`SessionService` retains behavioral Session validation. Classification alone
grants no replay, recovery, disclosure, or public authority.

Downgrade uses the exact MySQL connection-owned lock
`deviation_protocol:p33:s3:run_protocol_bindings:ddl_write:v1`, acquired by
`GET_LOCK(..., 30)` before the exact
`SELECT 1 FROM run_protocol_bindings LIMIT 1 FOR UPDATE` current/locking probe
on the same physical connection and retained transaction. It observes committed
rows newer than an already-established REPEATABLE READ snapshot; named-lock
acquisition does not refresh snapshots. No fresh Alembic transaction is assumed.
A visible row prevents every destructive DDL statement. The named lock is held
across ordered destructive DDL despite implicit commits; it excludes compliant
lock-taking writers, not arbitrary SQL writers. Future compliant S4 binding writers must share
that exclusion contract, but S4 remains the first owner of any production
write, conflict translation, admission evidence, and entry-world binding. S3
has exactly four new infrastructure exception types and exactly 36 executable
top-level vectors and 56 blocks. After the first correction completed, the
second review returned `CHANGES_REQUIRED` with five Medium findings. The second
correction supplied acquisition/release/connection-loss matrices, preserved
the primary body error over cleanup failure, froze exactly one S3 wrapper
and direct-cause contract per lower exception, and used the single N01-N15
physical/semantic/reconstruction/comparison sequence. V05/V06 prove simultaneous
defect precedence; V02 starts with no binding and performs one test-local add/
flush; V03 uses isolated literal in-memory inputs twice with no I/O.
The third review returned `CHANGES_REQUIRED` with exactly three findings:
stale-snapshot downgrade visibility, complete Run validation before its required
immutable-character load, and missing state-only between-DDL loss branches.
The published third correction specifies the current-read/old-snapshot V31-B proof and
the L01-L04 immutable-preload sequence, synchronized with V01-A/V13/V14/V29.
After acknowledged FK removal, state-only loss before index removal raises
`RuntimeError("P3.3-S3 downgrade BODY_CONNECTION_LOST_BEFORE_INDEX")`; after
acknowledged index removal, state-only loss before table removal raises
`RuntimeError("P3.3-S3 downgrade BODY_CONNECTION_LOST_BEFORE_TABLE")`. Both have
`__cause__ is None`, prohibit subsequent DDL and release SQL, preserve the
primary over cleanup errors, and invalidate/discard without reconnecting.
V30-D2/D3 each retain one primary block with explicit independent (a) ordinary
statement-failure, (b) during-statement disconnect, and (c) between-statement
state-only variations. An observer inspects partial schema and server-session/
lock termination before fixture restoration; client detection alone does not
prove immediate lock release. The published S3 implementation includes these
paths; its accepted verification evidence follows below.
The plan's exact vector allocation assigns P=27 persistence-unit, R=4
repository-unit, E=1 existing entry-service-unit, and M=24 real-MySQL
blocks, with one uncounted existing composition secondary proof. Mandatory unit
suites pass their assigned blocks; focused MySQL passes only M with zero
environment skips; the union covers exactly 56. The 15-path implementation
budget has a task-authorized conditional exception for genuine findings in
`docs/engineering/deferred_findings.md`; that exception is used for DF-001.
The user subsequently authorized three additional integration-test paths for
stale migration-head/schema-inventory expectations, listed in the evidence
section below. That test-only scope extension left the frozen plan and production
implementation unchanged.
The E/C regression files remain unchanged and execution-only. None of the
three prior reviews was approval. It creates no public/native
admission, entry-world binding, objective mechanics, prompt compilation,
API/OpenAPI, Demo, Web, Provider, visit, region, world-state, or continuity
authority.

The exact three-document corrected plan was subsequently independently approved
and published. Its frozen candidate-time lifecycle wording is historical;
earlier `CHANGES_REQUIRED` reviews do not describe the current approval state.
The implementation and migration `20260828_0006` subsequently received independent
approval with DF-001 deferred and were published at
`a53f8e65ad74c62bc6c40b9de26222eb889084f0`. S4's plan was approved and published at `42411b2`; its separately authorized
implementation is independently approved and published at `34dc752`. S5 has an approved, published plan at `ff866d2` and independently approved
implementation published at `86c258e9`. S6 plan is published at `4365721`;
its implementation is independently approved and published at `2f144599`. S7-1
is published at `41d68aac` under its approved published plan; the S7-2
plan is approved and published at `2c272487`, with P01–P08 approved. Implementation
is published at `6dfbd37`. S7-3 plan is published at `0ea295e` with P01–P09 approved; its authorized
implementation candidate awaits focused independent re-review. S7-4/5 remain outside this increment.
Phase 3.3 remains incomplete. No separate S4 publication-closeout task is required.

### P3.3-S3 published implementation evidence

The implementation published at `a53f8e65ad74c62bc6c40b9de26222eb889084f0`
was independently approved with DF-001 deferred. It implements frozen domain/stored
carriers, exact four-exception ownership, L01-L04 loading, N01-N15 reconstruction,
the 19-column mapping with four checks/composite FK/supporting index, two
read-only repository methods, same-session UoW exposure, and additive migration
`20260828_0006` over `20260729_0005`. No production binding writer, seed hook,
duplicate-key translation, admission service, package export, or public route
has been added. Canonical S1/S2 and existing service ownership are preserved.
S3 types are imported lazily by read adapters so unrelated CLI commands do not
eagerly import S2 and emit its existing model-definition warning.

The independent implementation review returned `CHANGES_REQUIRED` for two
reproduced defects: a missing common entry/binding timestamp check and a V32
lock-exclusion assertion confounded by the transaction-close barrier. Both are
corrected before the subsequent independent approval and publication. That
earlier changes-required verdict remains accurate review history.
S3 now rejects an otherwise internally consistent legacy family when binding
and entry creation times differ, with the exact S3 stored-integrity exception,
no direct cause, no trusted classification, and no write. Existing Run-entry
caller authorization and its stricter replay validation remain unchanged.
Both read methods retain valid legacy behavior.

V32 observes writer acquisition separately from transaction completion. A third
physical MySQL connection observes the writer executing GET_LOCK in the server's
User lock wait state and confirms the migration owns the shared named lock.
The bounded observation precedes DDL release; it cannot pass for an unscheduled
writer or a writer waiting only for transaction closure. The latter barrier
remains in place. Both normal branches pass, and controlled test-local different
lock names make each branch fail at the intended exclusion assertion. Each
normal/mutated variation checks old-row column digests and schema signatures,
revision 006, zero native rows, released locks, and unchanged migration bytes.

The published 19-path scope comprised 15 implementation paths, the existing DF-001
register, and three explicitly authorized integration-test expectation updates.
Historical migration-state assertions remain intact. Allocation remains 36 IDs
and 56 primary blocks (P=27/R=4/E=1/M=24); the two timestamp regression cases and
external mutation/restoration checks add no primary blocks.

The corrected candidate's recorded authoring evidence, retained for the approved
publication, is: 418 affected regressions;
canonical MySQL 218 passed with zero skips; complete S2 23 passed with zero skips
and 5,624,910 calls; canonical Offline 2,537 passed, 207 expected skips, one
explicit deselection; canonical Full 2,742 passed, two expected skips, one
explicit deselection. Canonical compilation, dependency checks,
sanitized Alembic heads/history, and whitespace stages passed. MySQL includes
all 24 S3 primary blocks and required existing Run/legacy suites. Detailed
commands, selections, results, exit statuses, source/dependency identities,
environment containment, and raw child output are retained in the external
`s3-implementation-20260916-audit/correction` evidence bundle and its manifest.

The earlier 2,667.82-second exhaustive S2 claim, detailed Offline child output,
and standalone MySQL invocation record could not be substantiated from the
supplied audit directory or its referenced records. They are historical author
claims, not reused acceptance evidence. The fresh complete S2 run preserves all
104,165 maps, 2,812,455 distinct inputs/primary calls and immediate repeats;
a test-local forwarding counter independently records exactly 5,624,910 public
resolver invocations. Published S1/S2 source and assertions are unchanged.

The subsequent canonical Offline and Full runs explicitly deselect only
`tests/unit/test_run_protocol_resolution.py::test_complete_direct_exhaustive_public_resolution_domain`
and reuse that freshly recorded proof. They rerun the other 22 S2 tests and
all other selected tests; the exhaustive case is not represented as executed
in either aggregate. Source/dependency/environment records establish reuse
applicability; final documentation-only synchronization does not alter tested
behavior. Offline's 207 expected skips are 205 database tests, Live, and the
Windows symlink-privilege case. Full skips only Live and that symlink case.
The existing S2 model-field warning and unavailable Turkish locale are reported
without claiming a substituted locale proof.

DF-001 remains deferred with its existing process-local .NET language
containment, owner, and post-playable stabilization reassessment before wider
release. Its test is unchanged; no S3 acceptance evidence is waived. Initial
external mutation-harness invocation/matcher errors are retained as failed
attempts and are not counted as successful sensitivity evidence. No unrelated
failure is attributed to DF-001.

There is no new integrated-play, user-trial, release, or Phase 3.3 completion
claim. S3's implementation review and publication are complete; no Provider/Live
call, browser session or production database change is claimed by these records.
S4's plan was subsequently approved and published at `42411b2`. Its
published implementation and preserved evidence appear below; S3 remains closed.
Guardrail impact: None.

### P3.3-S4 published native admission and entry-world component

The [bounded S4 plan](phase_3_3_s4_native_run_admission_entry_world_plan.md)
was independently approved with DF-001 deferred and published at `42411b2`.
The implementation published at `34dc752295ba270617e5d29020f3a0c0b133544e`
supplies one production-composed internal application service. It accepts
trusted-caller intent, revalidates character ownership, resolves S1/S2 input,
looks up the explicit authored world reference, and atomically persists Run
revisions 1/2/3, immutable protocol/world bindings at 3, native admission evidence
and the complete first Session family. Native evidence has its own discriminator,
version, ID-derivation prefix and fingerprint; legacy P8 V1 bytes and revision
semantics remain unchanged. Replay reauthorizes ownership and reconstructs the
same admitted result without new writes or synthesized legacy evidence.

Complete admission reconstruction enforces both receipt-to-protocol
equalities after individual receipt and S3 validation: strictly decoded receipt
`resolution_input_hex` bytes equal binding `resolution_input_canonical`, and
receipt `resolution_fingerprint` equals the binding's existing 32-byte
`resolution_fingerprint.hex()`. The admitted-family persistence validator owns
these checks for detached classification and owned replay before any trusted
result; either mismatch raises `RunProtocolBindingStoredIntegrityError` with
`__cause__ is None`, passed through replay unchanged, with no repair or writes.
Caller authorization and individual S1/S2/S3 failure ownership remain unchanged.
S3 internal consistency is insufficient: the plan's A/B regression retains
receipt A and all associations while substituting valid B input/objectives/
fingerprint, and requires complete reconstruction and replay of intent A to
reject the stored mismatch with that exact outcome.

A pinned physical connection owns the transaction and S3 shared named lock
through commit/rollback and checked release. Successor migration
`20260916_0007` adds only `run_entry_world_bindings` and refuses destructive
downgrade when native admission evidence exists. Its complete acceptance matrix
requires real-MySQL atomicity, concurrency, acquisition-state observation,
failure/cancellation, schema and legacy-preservation evidence, including that
A/B detached/owned-replay rejection. Both equality checks are mandatory.

The earlier plan review finding is closed by the corrected approved plan and
both implemented comparisons. The subsequent `CHANGES_REQUIRED` implementation
review identified one migration-disposal finding; its correction was independently
approved and published with S4 at `34dc752`. Earlier reviews remain history.
S4 does not expose native API/OpenAPI, Demo or Web entry (S6), apply objective
mechanics or compile prompts (S5), or implement later worlds/visits/continuity
(S7). It adds no story canon or public/default entry-world designation.

### P3.3-S4 implementation candidate evidence

This heading and the evidence below preserve the original candidate records and
their locatable references. S4 subsequently received independent approval and
was published at `34dc752295ba270617e5d29020f3a0c0b133544e`. No new execution
or retroactive expansion of earlier test selections is claimed here.

The external evidence bundle is `s4-implementation-20260917`; the handoff gives
its absolute location and manifest. It retains exact commands, full output and
first failures, exit statuses, candidate source hashes, dependency/environment
identities, test selections and database restoration checks. Failed development
attempts remain failed records, not acceptance passes.

Canonical MySQL verification passed 340 tests with zero skips, including 78
new admission tests, 44 new migration tests, and affected historical S3, Run,
character-binding, Session and legacy-playthrough regressions. Earlier focused
unit verification passed 156 tests; final native contract/service coverage
passed 33 tests and the composition/P8 introspection selection passed 42.
The new native tests cover normal production composition, complete
atomic families, read-only replay after Session progression, both independent
receipt comparisons and valid A/B substitution at both complete boundaries,
concurrency, staging rollback/cancellation, uncertain commit and explicit retry,
physical connection ownership, release failure, repeated cancellation, cleanup
deadline, schema parity, old-row preservation, issued/unissued DDL faults, current
locking probes, and observed GET_LOCK exclusion with different-lock controls.

Canonical Offline passed 2,599 tests, with 329 skips (327 database, one disabled
Live test, one unavailable Windows symlink privilege) and one deselection.
Canonical Full passed 2,926 tests, with two skips (disabled Live and unavailable
Windows symlink privilege) and one deselection. All three canonical runs used
the incoming candidate runtime source, before the isolated migration-disposal
correction described below. Three final test-only assertions then passed: actual
admission INSERT/transaction/lock connection identity for commit and rollback,
and exact ORM/live-schema parity plus preservation of an existing legacy
Run/Session family across empty 007 downgrade/upgrade. These supplemental cases
are recorded separately, not attributed to the earlier broad selections.
Compilation, dependency consistency and sanitized Alembic metadata checks pass;
the single linear head is `20260916_0007`. Final database inspection confirms
head 007, restored schema, no fixture rows, enabled FKs and a free shared lock.
The complete S2 exhaustive proof is reused from
`s3-implementation-20260916-audit/correction`: 23 passed, zero
skips, 5,624,910 public resolver calls. Actual records were located; unchanged
S1/S2 implementation/catalogue/tests and dependency/interpreter/platform and
relevant environment assumptions were checked. Only its exhaustive node is
deselected in broad Offline/Full runs; adjacent S1/S2 tests and native resolution
round trips execute. Deselection is not claimed as execution.

The normal-composition regression exposed differing physical timestamp
precision: Run rows retained fractions while Session/event rows did not. Native
admission now chooses one whole-second UTC timestamp before constructing any
family row; old schema and P8 behavior are preserved. Failure injection also
exposed an open connection wrapper after combined rollback/invalidation failure;
disposal now detaches and invalidates the retained pool handle before closing
the wrappers. Real-MySQL tests prove primary-error preservation and owner/lock
termination. DB-001 records both rules. Demo import isolation and runtime type
introspection regressions were fixed and verified without changing public routes.
DF-001 remains deferred with its existing process-local language containment,
owner and post-playable reassessment milestone. No Provider/Live call, public
native activation, deployment, staging, commit or push is part of this work.
Next step: focused re-review by the previous independent reviewer of the
correction, regression and direct dependencies; preserve earlier conclusions
for unchanged content. No approval or Phase 3.3 completion is claimed.

The implementation review returned `CHANGES_REQUIRED` with one reproduced
finding: migration 007's failed invalidation could return a live named-lock
owner to the pool despite wrapper closure. The isolated correction retains the
pool proxy and asyncmy driver before invalidation, detaches on failure, closes
the physical transport synchronously, invalidates the detached proxy and closes
the wrapper. The original primary exception and cause are unchanged;
`close_error` retains the first disposal failure and `disposal_errors` retains
any subsequent failures. If physical close fails too, pool reuse is prevented
but physical termination and lock release are not claimed.

The correction bundle `s4-migration-disposal-correction-20260917` records the
installed SQLAlchemy/asyncmy lifecycle, incoming 28-path identity check and
dependency/environment applicability. Before the fix, both new acquisition
failure cases failed at the bounded physical-owner termination check, after
passing primary/cause/cleanup assertions. The corrected regression passed four
cases: NULL and statement failures, each with successful or failed physical
close. An independent observer proves the owner is alive when invalidation
raises; successful fallback removes that owner and frees the lock before any
diagnostic teardown. A different subsequent checkout remains usable. Forced
physical-close failure instead proves the owner remains alive and detached,
with both disposal failures retained; independent teardown then removes it.
No shared S3 helper was changed; the native migration suite adds only a local
connection-property adapter for its existing test views.

Focused acceptance passed 91 real-MySQL tests with zero skips: all 48 native
migration cases, historical S3/current-head dependencies and selected native-UoW
disposal/cancellation tests. Compilation, dependency consistency, sanitized
linear-head metadata, whitespace and independent database restoration checks
are retained in the correction manifest. Prior admission/timestamp, broad-suite
and exhaustive S2 evidence is reused for unchanged content after source,
dependency and environment checks; Offline/Full and exhaustive S2 were not rerun
and do not prove the changed migration. DB-001's enforcement reference is
updated without adding a rule. DF-001 remains deferred. At that historical
checkpoint the correction was ready for focused re-review; it subsequently
received independent approval and publication with S4 at `34dc752`.

### P3.3-S5 implementation candidate evidence

The [frozen S5 plan](phase_3_3_s5_objective_mechanics_prompt_context_plan.md) was
independently approved with DF-001 deferred and published at
`ff866d2fd40181e0bf27937d255d70ebd1ae1544`, parent `34dc752`. Its first review's
CHANGES_REQUIRED resource-call finding and corrected candidate wording remain
historical. The implementation follows the approved correction: computed charge
and actual depletion are distinct; only positive depletion calls `consume_resource`
and emits `RunProtocolResourceSpent`. Both zero cases still advance the Director
and commit legitimate effects. The positive-amount resource API is unchanged.

The independently approved implementation, published at
`86c258e9ad2e64199cabf8650bf6f3a7b5f04d87` with DF-001 deferred, implements the five pure policies, trusted
native coordinator, native job evidence codec, canonical compiler, production
composition, atomic native turns, replay/reload and authored endings. Gameplay
uses the exact approved coefficients and catalogue association. The integration
is internal: public native discovery/admission, API/OpenAPI, Demo/Web activation
and public recovery remain S6; later worlds/visits/continuity remain S7;
relationship/residence state remains Phase 3.4. Phase 3.3 remains incomplete.

The compiler emits closed `run-prompt-context/v1` canonical UTF-8 JSON, at most
1,024 bytes, after all UoWs/AsyncSessions close. It includes exact numeric
objectives, three presentation enums, selected result and the approved internal
pressure label. Generous=0..30, Fluid=35..65, Scarce=70..100 on the S2 lattice;
labels do not replace numeric values. The private request attachment is not
serialized into legacy requests or public DTOs. PromptBuilder only inserts
validated data and fixed expression instructions; neither it nor the compiler
selects outcomes, mutates or persists state. Finalize compares reconstructed
bindings/decisions without compilation. Model output and compiled text grant no
mechanics, relationship, death, world-selection, permanent-state or canon authority.

Dependency-derived candidate inventory follows section 6: new domain policies,
new application coordinator/compiler, existing two turn orchestrators, outcome
policy, Director, internal request/prompt, production composition, and the
participation reverse-read port/SQL repository. New tests cover pure policies,
trusted decisions/compiler and real native MySQL turns. Existing Director tests
prove generic multi-clock order; Provider and composition tests add compatibility
assertions. Documentation changes are this
protocol, roadmap, architecture and narrative Provider boundary. No storage,
public-contract, frozen-plan or migration extension was necessary. Acceptance
is concentrated in those tests rather than editing every execution-only regression.

External implementation evidence is under
`C:\Users\DYLANM~1\AppData\Local\Temp\deviation-protocol-s5-implementation-20260917-1318b56094c540e4a491d05698b3db37`.
The external manifest freezes exact file identities and the complete lexicographic
binary/full-index patch including new files; it is not embedded in the candidate
whose bytes it identifies. Raw logs retain failed development attempts separately
from final evidence. Verification and restoration results are recorded below.

The original external S3 correction bundle's S2 exhaustive evidence is reused
only after comparing actual raw logs, the counter plugin hash, S1/S2 source/test
hashes, full dependency versions, Python 3.12.14, platform, command, exit status
and environment containment. It proves 23 tests and 5,624,910 resolver calls;
`s2-reuse-applicability.json` records the comparison and original absolute paths.
Canonical Offline deselects only
`tests/unit/test_run_protocol_resolution.py::test_complete_direct_exhaustive_public_resolution_domain`;
all other S2 tests execute. The unchanged S3/S4 migration fault matrices are
excluded from MySQL acceptance with explicit recorded paths/nodes; schema metadata
remains checked. No summary substitutes for a missing test result.

Executed canonical acceptance (all commands exited 0):

| Run | Passed | Skipped | Deselected | Scope |
| --- | ---: | ---: | ---: | --- |
| `canonical-offline` | 2,659 | 375 | 1 | Broad offline regression; only exhaustive S2 node reused |
| `canonical-mysql` | 322 | 0 | 16 | Real MySQL integration; unchanged S4 migration file excluded before collection and S3 migration fault nodes explicitly deselected |
| `final-focused-offline` | 436 | 40 | 2,564 | Final native policies/compiler/coordinator, Director, outcome, turn, Provider, composition and repository regressions |
| `final-focused-mysql` | 40 | 0 | 346 | Final production-composed native integration suite |

The broad source identities were captured before final decision-carrier and
catalogue integrity hardening. Broad Offline completed across that edit interval;
it is not claimed as a byte-exact final-source run. The final focused runs cover
those direct dependencies and the added non-hospital multi-clock regression;
their separate source manifest binds the final code. Unaffected broad results
remain applicable. No broad suite was repeated merely for prose edits.
Every canonical run also passed compileall, dependency checks and Alembic
heads/history (`20260916_0007`); no migration ran. The verification runner's
online Alembic check was deliberately skipped because it lacks a test-URL-only
entry point. Offline skips are database/Live guards and unavailable Windows
symlink privilege. Existing schema-shadow and unavailable-Turkish-locale warnings are
retained in raw logs. Focused Offline skips are its 40 MySQL cases.

The three resource controls and three profile routes to authored endings pass
through normal production composition and real MySQL. Evidence covers one-winner
concurrency, exact replay, validated-proposal resume, stale rejection, uncertain
commit acknowledgement, Provider cancellation and rollback at all six persistence
fault points. Compiler, PromptBuilder and fake Provider probes find no active
UoW or unclosed AsyncSession; an independent MySQL connection acquires the same
Session row lock and verifies the admission named lock is free at each probe.
Canonical compiler goldens, all 27 presentations at each default, hidden-data
boundaries and adversarial output rejection pass. Locale evidence records C,
English and Chinese as verified, Turkish as unavailable; unavailable is not a pass.

Designated-database identity and complete table row-count/hash records match
before and after verification. Fixture mutations are restored. Database/Provider
environment sanitization, test selection and DF-001 containment were child-process
only; the parent environment is unchanged. No real Provider or production database
was used. The external manifest includes raw logs, command/exit metadata, source
epochs, reuse applicability, restoration and exact patch identities.

Historical candidate handoff defined
`PHASE_3_3_S5_OBJECTIVE_MECHANICS_PROMPT_CONTEXT_IMPLEMENTATION_INDEPENDENT_REVIEW_APPROVED`
for both successful dispositions and requested substantive independent review;
that session did not claim approval. Subsequent independent approval with DF-001
deferred and publication at `86c258e9ad2e64199cabf8650bf6f3a7b5f04d87` close that
implementation gate. The token and candidate evidence above are historical, not
an operative S6 gate. No separate closeout is due. DF-001 retains its documented
process-local containment; no new finding is deferred. Guardrail impact: None.

### P3.3-S6 implementation candidate evidence

The approved S6 plan was published at
`4365721abe2eeff9bf21cb766b5c43f28eab5d58`, parent
`86c258e9ad2e64199cabf8650bf6f3a7b5f04d87`. Implementation began only after
local `main`, HEAD and local `origin/main` matched that baseline at 0/0 with
clean worktree/index and no conflicts, operations or locks; no fetch occurred.
Frozen plan wording is historical. The following records preserve implementation
candidate evidence and its original limitations. S6 was subsequently independently
approved and published at `2f144599`; the [publication/browser record](#s6-publication-and-local-browser-evidence)
owns current status. Phase 3.3 remains incomplete.

The delivered journey is explicit character selection/creation -> profile/world
and optional overrides/presentation -> confirmation -> shared S4 native admission
-> identity storage -> authoritative View -> public S5 actions -> fresh-service
reload/replay and authored Session ending. Production and deterministic Demo
support all three published defaults. Demo additionally proves an allowed
override/presentation variation across independent processes and hash seeds.
Web uses returned affordances and resources, locks ended actions, and preserves
the exact version-1 recovery allowlist. Pending native entry is memory-only;
reload before validated success and storage cannot recover that attempt.

The public contract adds exactly options GET, native POST and optional
omitted-not-null View context. Baseline OpenAPI comparison preserves all old
paths, operation IDs, response status sets and component schemas except that
optional View member. Closed DTOs and revalidated authority exclude internal
binding, receipt, compiler, controller and hidden-state data. Corrupt native
families cannot become legacy omission. Discovery/View are read-only and do not
compile or render. Current ownership is checked in the existing View UoW.

Demo adds only process-local representations of existing S3/S4 storage families.
Its shared codecs, staged/trial maps and explicit writer capability preserve
atomicity. AUTH-002 denial runs before protected work; native rendering is
task-bound and single-use, outside gameplay locks/UoWs. Failure/cancellation,
validated resume, committed replay and later independent use are covered.
Ordinary valid actions need not follow the legacy script. The legacy golden
trace and every historical component hash remain unchanged. Section 7's
dependency-derived mechanical extensions are the legacy replay child's complete
snapshot inventory and its parent's exact field-set assertion
(`tests/e2e/support/demo_replay_child.py` and
`tests/e2e/test_demo_cross_process_replay.py`); that replay suite owns verification.
The two new maps are empty in legacy snapshots. The existing shared denial gate
made an edit to `demo_authority.py` unnecessary.
Broad regression also identified stale route/schema absence assertions in
`tests/unit/test_player_character_api.py` and `tests/unit/test_run_repositories.py`.
These dependency-derived mechanical extensions retain the old DTO/schema and
repository boundaries while permitting exactly the approved S6 additions; the
Player Character API and Run repository suites own their verification.

External evidence directory:
`C:\Users\dylanmonster\AppData\Local\Temp\deviation-protocol-s6-implementation-20260917-0bae04dac6a04caf9a16e6923dc5b8e6`.
`candidate-manifest.json` binds the exact path inventory, complete per-file
identities, all new-file patches and lexicographic aggregate patch. Raw logs,
commands, exit statuses, source/dependency/environment identities and acceptance
mapping are retained alongside it. Development failures and earlier focused
passes are authoring evidence. Final-source applicability is recorded explicitly
in `final-source-applicability.json`.

- Broad canonical Offline: **2,730 passed, 385 skipped, one deselected, five
  failed**. Four failures were stale inventory assertions; the fifth caught
  infrastructure exception imports in the new application View helper. Those
  imports were redundant with its existing ValueError boundary and were removed,
  preserving safe corruption mapping and dependency direction. Final canonical
  focused Offline reruns all five failures and the affected public/View/Demo
  dependencies: **556 passed, 205 expected database skips, 2,360 deselected**,
  exit 0 (`final-focused-offline.json` and its log).
  The broad run is not represented as a passing final-source run.
- Canonical MySQL: **332 passed, 16 deselected**, exit 0. The unchanged native
  migration file's 48 cases are excluded before collection. All remaining S4/S5
  runtime, admission/concurrency/rollback, public ASGI, lock-separation and
  resource controls run against MySQL 8/asyncmy `deviation_protocol_test` only.
  Final canonical focused MySQL after the View-helper correction passes
  **130 tests, 266 deselected**, exit 0 (`final-focused-mysql.json` and its log).
- Incoming-candidate Web: **293 passed, one existing opt-in Demo-presentation probe skipped**;
  `npm run test:run`, `typecheck`, `lint` and `build` all exit 0. Rendered MSW
  covers explicit setup through ending, exact retry bytes, tainted errors,
  storage-only retry, stale generations, native context continuity and GET-only
  restart/reload recovery. The skip is not browser evidence.
- `compileall -q src tests alembic`, dependency consistency and linear Alembic
  heads/history metadata pass through canonical verification. Head remains
  `20260916_0007`. Online Alembic current/check is intentionally omitted because
  its entry point is not TEST_DATABASE_URL-only; no new migration is applied.
- `openapi-compatibility.json` compares actual baseline/current OpenAPI from
  isolated imports. New native child ASGI journeys compare exact public trace
  and complete detached storage across fresh processes; legacy cross-process
  gameplay/replay remains covered. No HTTP listener or browser is used by the
  native driver. Existing legacy loopback/script checks retain their scope.

`s2-reuse-applicability.json` verifies the original S3 correction log, counter
plugin, 5,624,910 resolver calls, source/tests, Python/Pydantic/dependencies,
environment and exit status. Only
`tests/unit/test_run_protocol_resolution.py::test_complete_direct_exhaustive_public_resolution_domain`
is reused; all other S2 tests run. `migration-reuse-applicability.json` checks
actual S4 broad evidence plus the later
`s4-migration-disposal-correction-20260917/affected-migration-disposal` 91-case
proof, including final migration/test bytes and unchanged native writer bodies.
The older pre-correction migration evidence alone is not treated as final proof.
Exact exclusions and reasons are retained in `mysql-selection.json`.

The broad source snapshot predates five corrected paths: the new public View
helper, the two mechanical inventory tests above, and Web `schemas.ts` /
`client.test.ts`. Three failing regression cases proved that legacy nested
character parsers stripped unknown fields; native context now rejects those
fields at every nested character level without changing legacy parsing. The
final full Web run supersedes its earlier 290-pass result. Final canonical
focused Offline and MySQL runs verify the helper and its public admission,
View, Demo and S5 gameplay dependencies at final code. Unchanged broad evidence
remains applicable with these limits; no duplicate Full run or documentation-only
runtime rerun is claimed.

`database-before.json`, `database-after.json` and `database-final.json` have
identical per-table counts and SHA-256 fingerprints, including the revision table. Authorized fixture
mutations are restored; native fixture teardown verifies the shared lock is free.
DF-001's documented globalization settings exist only in verification child
processes, with parent settings unchanged. Its owner and post-playable
reassessment milestone are unchanged; no additional finding is deferred.

At the implementation-candidate checkpoint, automated integrated flow was
demonstrated on public ASGI and rendered MSW surfaces. Browser evidence was
omitted then, not passed. That checkpoint made no browser-verified usability,
limited-trial or wider-release readiness claim. That implementation task used no
real Provider/Live calls, dependency installations, production database operations,
deployment, staging, commits or pushes. S1-S5 authority algorithms, SQL native
writer/UoW/shared-lock topology, ORM, migrations, content, dependencies and
recovery storage schema remain unchanged. Ending a Session does not complete
its Run or detach its character; S7 continuity and Phase 3.4 state remain absent.

#### S6 first bounded Web correction and focused re-review

The independent review returned `CHANGES_REQUIRED` with two reproduced findings:

1. Confirmed native identity was lost after admission storage failure -> safe
   clear -> storage-only retry, and on manual reads of the same Session. A
   legacy-shaped View could then load. Storage retry now reinstates the complete
   retained Session/scenario/content/native-context association before releasing
   the attempt. Same-Session manual reads preserve it; genuine replacements
   clear the old association under existing operation-generation ownership.
2. A late eligible-character GET could automatically select its first item after
   switching to native mode. Completion now consults the current mode and keeps
   the request's existing active-generation guard. Native entry still requires
   explicit selection, with the existing explicit-creation exception; legacy
   first-item selection remains unchanged.

The incoming 42-path candidate was verified against its original manifest and
complete patch before editing. External evidence and the byte-preserved incoming
snapshot are in
`C:\Users\dylanmonster\AppData\Local\Temp\deviation-s6-web-correction-20260917`.
The reviewer's original three rendered cases fail against that incoming source
(`incoming-review.log`, exit 1). Original independent reports are untouched.
The same unmodified reviewer cases pass against the corrected source snapshot
(`corrected-review.log`: three passed, exit 0).
Production correction is confined to `web/src/App.tsx`; rendered regressions
are added to existing App and recovery suites. The storage allowlist, memory-only
pending entry, API, backend, Demo runtime, migrations, SQL UoWs, published plans,
guardrails and DF-001 are unchanged.

First-correction Web evidence uses installed dependencies and repository npm scripts
with database/Provider/live environment variables removed. Vite's existing
`deterministic-demo` mode disables env-file loading. No browser, network install,
real Provider, database or Python broad suite ran in this correction task.

- Targeted rendered corrections: **18 passed**, 80 excluded by the name filter.
  Coverage includes missing/mismatched context, changed scenario/content, valid
  storage recovery, same-Session manual reads, genuine native/legacy replacement,
  late initial/refresh lists, obsolete client completion, explicit valid choice,
  legacy behavior and explicit creation. Admission/storage/View ordering and
  absence of gameplay on rejection are asserted.
- Affected setup/client/App/recovery/action-loop/storage suites: **305 passed,
  one existing opt-in probe skipped** (`affected.log`, exit 0).
- Complete Web suite once after source stabilization: **311 passed, one existing
  opt-in probe skipped** (`full-web.log`, exit 0). Typecheck, lint and build each
  exit 0. Counts overlap and are not added together. This replaces the incoming
  293-pass Web acceptance result; it is not browser evidence.

All commands, logs, exit codes and source identities are external. Historical
failures remain recorded: the incoming broad Offline five-failure result and
earlier nested-parser failures above are unchanged history. Correction authoring
also encountered a Python console-encoding error, a short-TEMP-path Vite setup
resolution failure, and one test fixture using a non-retryable generic error
instead of the intended network error. These are retained in the external logs;
the corrected fixture preserves the assertions. None is attributed to DF-001.

Accepted backend evidence above remains applicable: backend and Python tests,
Demo, migrations, dependencies and verification scripts are byte-identical to
the incoming snapshot. The original broad/focused applicability limits and S2 /
migration reuse remain in force. No new backend pass count or stronger guarantee
is claimed, and no Python/MySQL/S2/migration matrix is rerun.

The external `candidate-manifest.json` and `complete.patch` identify the complete
corrected candidate; `correction-delta.json` and `correction.patch` identify the
exact incoming-to-corrected change. `unchanged-paths.json` verifies unaffected
paths, and `handoff.md` supplies the focused review scope and evidence map.
That candidate remained `CHANGES_REQUIRED` pending focused re-review. The next
subsection records its result and the replacement recovery correction. No
approval, staging, commit, push or extra post-commit audit is claimed or due.
Guardrail impact: None; existing AUTH-002, API-001, DB-001/002, MODEL, STATE and
PLAY constraints apply.

#### S6 automatic-recovery association correction

The focused independent re-review returned a second `CHANGES_REQUIRED`: character
selection was closed, but direct admission success -> storage failure -> repaired
storage -> storage-only retry -> automatic View recovery still accepted a different
scenario or content version and replaced the confirmed identity with that View.
Earlier applicable conclusions, including safe-clear retry, same-Session reads,
genuine replacement and character selection, remain preserved. This correction
did not itself claim independent closure of the remaining finding; subsequent
approval/publication is recorded separately below.

`App.tsx` now shares the pure `assertViewAssociation` boundary between automatic
recovery and `commitLoadedSession`. It checks the requested/confirmed Session,
scenario, content version and complete native context before either path replaces
the association or activates gameplay. The existing public schema also checks
internal View consistency. Validation uses the retained admission expectations;
the received View cannot establish its own comparison identity. Automatic recovery
keeps its generation checks and validation -> binding -> storage -> current-generation
check -> gameplay ordering; it does not call unrelated commit/storage effects to
reuse validation. Bounded inspection confirmed that manual reads, entered-Session
retry and action/status refresh reach the same commit validation; stale marking
only changes the existing View's stale flag. No character handler changed.

The incoming 42-path candidate, 270,520-byte complete patch with SHA-256
`58d64cbb940753eec368b57ce5b082226577b7c350746738208149b79d117236`, was verified
and snapshotted before edits. New external snapshots, logs, commands, exit statuses,
source hashes, complete/delta manifests and patches are in
`C:\Users\dylanmonster\AppData\Local\Temp\deviation-s6-auto-recovery-correction-20260917`.
Original reports in the prior correction and focused-review directories are
untouched. The latest reviewer's unchanged three cases reproduce **two failures
and one matching pass** against the incoming snapshot (exit 1), and all **three
pass** against the corrected snapshot (exit 0). Both negative fixtures explicitly
pass `playerSessionViewSchema`; the content case changes both content-version
fields consistently.

New rendered regressions cover direct recovery with missing/mismatched context,
changed Session/scenario/content and matching View, plus abort-insensitive late
completion after client replacement/unmount. They assert one admission POST,
one automatic View GET after successful storage, no gameplay on rejection,
GET-only repeated rejection followed by matching recovery (the admission binding
survives), and no stale-generation storage/UI/binding mutation. Existing safe-clear
and manual-read content fixtures now also keep both content fields consistent and
assert schema validity. All earlier character-selection regressions remain intact.

Final replacement Web evidence uses installed dependencies, the same sanitized
runner and repository npm scripts, with Vite env-file loading disabled:

- Targeted correction regressions: **26 passed**, 80 filtered out.
- Affected setup/client/App/recovery/action-loop/storage suites: **313 passed,
  one existing opt-in probe skipped**.
- Complete Web suite, once after code stabilization: **319 passed, one existing
  opt-in probe skipped**. Typecheck, lint and build each exit 0.

Counts overlap and are not added; these replace the first correction's Web
acceptance evidence. Test authoring initially asserted a Run ID absent from the
UI, then used an objective outside the schema's five-point increments; a typecheck
also caught unchecked mock-call indexing. Their failing logs remain external.
Assertions were retained with a schema-valid visible objective and safe indexing.
These failures and all earlier verification failures remain history, with no
attribution to DF-001.

Backend/Demo/Python tests, migrations, SQL UoWs, dependencies, verification scripts,
published plans, guardrails and DF-001 are byte-identical. Accepted backend evidence
and its original broad/focused applicability limits remain valid; no Python broad
suite, MySQL, exhaustive S2 or migration reruns or overlapping pass counts are
added. No browser, database, real Provider, network install or Git write occurred.

At this correction checkpoint, disposition remained `CHANGES_REQUIRED` pending
the previous independent reviewer's focused re-review of the binding correction,
direct dependencies and replacement Web evidence under the existing token. The
subsequent approval is recorded below. No new approval stage or post-commit audit
was introduced. Guardrail impact: None.

#### S6 publication and local browser evidence

Current status supersedes the candidate-time checkpoints above: S6 implementation
was independently approved and published at
`2f144599af5977e871c7a3466c52896b6a36510c`. The first `CHANGES_REQUIRED` covered
native recovery identity and late character selection; the second closed
character selection and retained only automatic recovery's scenario/content
binding. Both remain accurate historical reviews. Subsequent independent approval
accepts the corrected implementation; no S6 review or separate closeout is pending.

On 2026-09-17, separately authorized local deterministic Demo browser acceptance
at that exact commit passed the representative journey: explicit character
creation/selection, Standard profile and authored entry world, pressure override
55 and heroic/lawful/off presentation -> one native admission -> ten UI actions
-> version-10 `ENDED` / `FAILED`, **记录成为现实**. Same-tab reload at version 2
restored play and continued to the ending. The ending is a Session result; the
Run remains active and bound. No same-line continuation or canonical character
death was demonstrated.

The actual external report is
`C:\Users\dylanmonster\.codex\visualizations\2026\09\17\01a0ad1f-763c-74e1-865b-44360d4b0bc0\p33-s6-browser-acceptance\acceptance-report.md`.
It is browser acceptance, not the independent implementation review. Its
`requests-redacted.json`, `runtime-redacted.txt`, redacted DOM snapshots and
delivered screenshots support the stated observations. The planning manifest
records report identity; no browser acceptance is rerun for this documentation.

After a controlled coupled backend/Web restart, startup-race proxy 502s paused
recovery. Explicit safe GET later returned 404; explicit local clear made no
server request. Full page reload restored discovery, with native profile/world
unselected and admission disabled. The partial discovery refresh is recorded as
[DF-002](engineering/deferred_findings.md#df-002--partial-discovery-refresh-after-demo-startup-race),
contained by that explicit reload. DF-001 remains unchanged.

Preserve these limits: storage-before-View was not directly observed in the
browser (existing automated evidence owns that ordering); the saved restart
recovery crop failed and no usable screenshot of that panel was delivered,
although contemporaneous text/request evidence exists; restarting also restarted
the frontend, so uninterrupted-Web/backend-only recovery was not exercised;
terminal Ctrl+C was ineffective and verified task-owned process-tree cleanup
was used instead. No browser 202/pending-job path, all-profile/race matrix,
database persistence, real Provider, wider-release readiness or Phase 3.3
completion is claimed. Technical presentation U2 is a usability observation;
the single ClientDisconnect R1 has no established reproducible cause and is not
registered as a confirmed code defect.

The [published S7-1 plan](phase_3_3_s7_1_post_ending_run_exit_plan.md) was approved
at `9fab18d`. Implementation published at `41d68aac` supplies explicit native Run
exit, historical binding and separately confirmed fresh admission. Its
[automated evidence](#p33-s7-1-implementation-candidate-evidence) is distinct from
the historical S6 browser evidence above. Subsequent separately authorized
[S7-1 browser acceptance](#s7-1-publication-and-local-browser-evidence) is recorded
below. Later-world continuation remains unimplemented.

### Extreme — Silent Hunting Ground

- Extreme scarcity.
- Severe consequences.
- Opaque information.
- Very low default social trust.
- High cooperation cost.
- High betrayal incentives.
- Dark-forest-like conflict.

### Standard — Fragile Alliance

- Local scarcity.
- Trust must be earned.
- Cooperation and betrayal are both meaningful.
- Betrayal is possible but not universal.

### Easier — Open Expedition

- Sufficient resources.
- Trade, rescue, and cooperation are more common.
- Betrayal incentives are lower.
- Conflict intensity is reduced, but narrative conflict still exists.

## Determinism and authority

- Difficulty controls objective mechanics and world conditions.
- Character definition controls abilities, knowledge, personality, and
  viewpoint.
- Protocol presets control presentation.
- Difficulty and character may supply recommended defaults.
- Under the published S2 implementation, recommendations are presentation advice outside the
  resolver and cannot select a profile or create/mutate an override.
- Player-approved overrides are resolved before the first turn.
- The resolved protocol is versioned and frozen when the first turn begins.
- The published S2 profile resolver consumes no randomness, PRNG, or seed.
  Later dynamic/world behavior may use separately frozen engine state and seed
  only under its owning later-slice authority.
- The model does not perform its own uncontrolled random selection.
- The model does not invent resource loss, betrayal, death, permanent state
  changes, or major canon facts.
- `Grim` may intensify language, but cannot make a valid potion expired or an
  on-time rescue late unless the engine established that fact.
- `Heroic` may emphasize opportunity and reversal, but cannot manufacture
  success.
- `Chaotic` may add dreamlike, surreal, or limited meta presentation.
- Permanent canon arising from `Chaotic` presentation requires engine
  authorization and world-line consistency validation.
- Relationship atmosphere affects tension and expression, not objective
  relationship state.

These rules preserve the existing authority principle: the model narrates
confirmed state and results; the engine owns objective mechanics and permanent
state.

## Structured prompt input

The accepted direction is:

```text
difficulty + character + permitted pre-game overrides
  -> resolved, versioned Run Protocol
  -> fixed structured prompt prefix
```

A proposed representation is:

```text
[RUN_PROTOCOL v1]
difficulty_profile=<resolved profile>
character_id=<resolved character>
world_tone=<grim|balanced|heroic>
resource_pressure=<scarce|fluid|generous>
social_trust=<resolved value>
consequence_severity=<resolved value>
information_opacity=<resolved value>
conflict_intensity=<resolved value>
reality_boundary=<lawful|deviant|chaotic>
relationship_overlay=<off|veiled|charged>
preset_version=1
[/RUN_PROTOCOL]
```

The structured, versioned boundary is accepted. The frozen P3.3-S1 plan fixes
the exact `run-protocol-envelope/v1` representation and the published S1
foundation implements its standalone codec/validation evidence. This does not
select or implement the illustrative `[RUN_PROTOCOL]` prompt block above; no
`RUN_PROTOCOL` block exists in the implemented prompt today. In particular,
`resource_pressure=<scarce|fluid|generous>` is not an S2 output, alias, band,
or authoritative input field. That illustration did not establish thresholds.
The published S5 plan now fixes the separate internal projection implemented
above: Generous=0..30, Fluid=35..65, Scarce=70..100 on the numeric S2 lattice.
The exact S2 value is preserved without rounding, clamping or replacement.
Public/client representation remains S6-owned.

## Lifecycle

1. The game offers engine-approved profile, character, and eligible
   initial-world choices.
2. Difficulty and character definitions supply defaults or recommendations.
3. The player selects one eligible entry world and applies only permitted
   pre-game overrides.
4. The engine validates and resolves the complete profile.
5. The resolved protocol, `entry_world_id`, and `entry_world_version` receive
   their run binding and are frozen at the first turn.
6. Each turn uses the frozen protocol with current engine-confirmed state.
7. S2 profile resolution is non-random; any later dynamic behavior is resolved
   deterministically from separately authorized state and seed. The Provider
   only renders permitted presentation.
8. When a later world is required, the engine deterministically selects it from
   the eligible pool while preserving required progression and recovery.
9. Replay uses the same frozen protocol, authoritative state, and deterministic
   inputs.

## Deterministic requirements

- Resolution order, defaults, override precedence, and validation are stable.
- The published S2 resolver uses canonical input and a deterministic fingerprint
  and consumes no seed; later-world seed behavior remains S7 work.
- The published S2 resolver produces only exact numeric `resource_pressure`;
  categorical mechanics/prompt projection is published in S5 and public/client
  representation is implemented in published S6.
- No setting depends on unordered collection iteration, wall-clock time, or a
  Provider-selected random value.
- Entry-world identity remains frozen, and later-world selection is
  reproducible from engine-owned state and seed.
- Required progression and engine-confirmed major-setting constraints take
  priority over pure random weighting. Important-NPC priority participates only
  when the already-authorized logical-identity and authored-world predicates
  required by the boundary above exist.
- The stored/frozen representation is sufficient to reproduce presentation
  inputs for a run.
- Objective results are reproducible independently of prose variation.
- A missing, unknown, incompatible, or mutated protocol fails explicitly under
  its owning S1 or S2 exception taxonomy; S2 never translates S1 corruption,
  and no failure silently selects new defaults mid-run.

## Implementation acceptance criteria

Phase 3.3 is acceptable only when:

1. The engine has a validated, versioned world/difficulty profile and frozen
   Run Protocol boundary.
2. Profile defaults and permitted overrides are resolved before the first turn;
   S2 acceptance directly executes all `104,165` valid maps and all `2,812,455`
   distinct presentation inputs through the public resolver using the
   independent literal oracle in fixed profile, Cartesian-map, and presentation
   order. It makes one validated primary call and one immediate real repeat call
   per input, compares exact output/canonical bytes/fingerprint, and separately
   asserts per-profile primary and repeat counts `333,396`, `1,594,323`, and
   `884,736`, aggregate primary and repeat counts `2,812,455` each, combined
   per-profile invocation counts `666,792`, `3,188,646`, and `1,769,472`, and
   `5,624,910` aggregate public resolver invocations. It also preserves exact
   field-level S1/S2 catalogue ownership and deterministic exception order and
   reacquires catalogue identity for detached reconstruction.
3. Objective parameter effects are implemented and tested independently from
   presentation settings; any `Scarce`/`Fluid`/`Generous` mechanics/prompt
   projection is separately frozen in S5 and any public/client representation
   is separately frozen in S6 without changing the numeric S2 value.
4. Character authority remains separate from difficulty and presentation.
5. Relationship atmosphere cannot mutate objective relationship state.
6. Identical state, seed, character, and resolved settings produce identical
   engine-owned outcomes.
7. Prompt construction uses only the validated frozen representation and does
   not grant model authority over resources, betrayal, death, or canon.
8. `Grim`, `Heroic`, and `Chaotic` authority limits have regression coverage.
9. Current scenarios retain their fixed facts unless a trusted engine event
   changes a mutable fact.
10. Entry-world selection is limited to an authored eligible set, freezes the
    selected ID/version, and later-world selection is deterministic,
    reproducible, and cannot strand required progression or recovery.
11. Important-world revisits preserve confirmed state and consequences, expose
    only engine-authorized regions/content, resist reward farming, and cannot
    be permanently excluded after authored recovery conditions become true.
12. Documentation and phase status are synchronized before audit or completion.

## Deferred questions

- Successor-version compatibility, durable schema/migration, and later decoder
  policy beyond the frozen standalone v1 representation.
- The exact S2 numeric domains, profile defaults, override catalogue,
  precedence, resolver, canonical input, fingerprint, symbol contract, and path
  budget are frozen by the published S2 plan and implementation. Durable S3
  representation is frozen in the independently approved published S3 plan;
  its implementation is published at `a53f8e65ad74c62bc6c40b9de26222eb889084f0`,
  independently approved with DF-001 deferred. S4 internal implementation is
  independently approved and published at `34dc752`. S5 internal integration is independently approved and published at `86c258e9`;
  S6 public integration is independently approved and published at `2f144599`;
  S7-1 is published at `41d68aac` under its approved published plan.
  S7-2 minimum later-world continuity is published at `6dfbd37` with automated
  and bounded local browser evidence. S7-3's approved regional-return plan is published at `0ea295e`; its local
  implementation candidate awaits focused independent re-review.
- P3.3-S5 owns the exact numeric-to-`Scarce`/`Fluid`/`Generous` mechanics and
  prompt projection; its approved bands and implementation are published.
  S6 implements the same bands for public output, with exact numeric values preserved.
- P3.3-S6 owns every public API, OpenAPI, Demo, Web, projection, recovery, and
  client representation of those labels; it may not replace the numeric S2
  value.
- Compatibility and migration policy for future protocol versions.
- S6 world/profile discovery is implemented under its published plan; later unlock policy remains S7.
- Public entry-world catalogue exposure (S6; no expansion in this slice); S4's bounded internal
  catalogue and explicit world/scenario mapping are implemented and published
  at `34dc752`; S6 public activation is independently approved and published at
  `2f144599`.
- Later-world weighting algorithm and general anti-repeat rules.
- Progression constraints and priority-injection rules for required story
  progression and major hidden settings; important-NPC integration remains
  unavailable until separately published owning authorities supply the required
  logical-identity and authored-world predicates.
- Important-world designation schema.
- Revisit limits and cooldowns.
- Region-unlock rules.
- Reward anti-farming rules.
- Recovery-priority weighting.
- World-line transition representation.
- How world-line consistency validation represents permanent canon approved
  after `Chaotic` presentation.

## P3.3-S7-1 implementation candidate evidence

The independently approved plan was published at baseline
`9fab18d8de4ba05000e38ee37fa6a2e8da17940a` (parent `2f144599`). The published
implementation delivers native admission -> actual public play -> valid Session
ending -> explicitly confirmed irreversible Run exit -> readable old history ->
refreshed eligibility -> separately confirmed admission with the same character
-> first action in the new journey. The independent implementation review returned
`CHANGES_REQUIRED` with one nullable terminal-CHECK finding. The bounded corrected
implementation was subsequently published at `41d68aac`; that earlier verdict
and [replacement evidence](#s7-1-nullable-terminal-check-correction) remain history.
[Publication and subsequent browser acceptance](#s7-1-publication-and-local-browser-evidence)
record current status separately from the original automated execution below.
Neither S7 nor Phase 3.3 is complete; S7-2 is published at `6dfbd37`, and the
S7-3 implementation candidate awaits focused independent re-review. No limited
user trial, broader release, deployment or real Provider acceptance is claimed.
The frozen plan and historical reviews retain their candidate-time wording.

The sole native transition is active revision 3 -> terminated revision 4. It
preserves the strict `NativeRunAdmissionV1` prefix and adds the exact
`NativeRunTerminatedV1` suffix, including the ended snapshot and completed-memory
evidence. Only this Run's character binding becomes historical; the character
lifecycle, old Session, protocol and entry world do not change. SQL and Demo
classifiers, historical View, admission replay, action/status replay and
eligibility all recognize the exact terminal family. Historical ownership does
not require the old binding to occupy the current active uniqueness slot.

The exit writer reuses the pinned native Unit of Work and shared advisory lock,
locks character before Run, revalidates after locking, stages revision/binding,
CAS and receipt atomically, reconstructs the candidate and commits once. Scoped
receipt replay/conflict precedes new-operation eligibility/version checks.
Turn readers acquire no reverse Run write lock. Uncertain commit or cleanup
does not trigger compensation, retry or replacement admission. Demo uses its
existing trial-store publication and enforces the same native writer guard.

Migration `20260917_0008` amends only three named CHECK branches and matching
ORM metadata. It adds no tables or columns. Upgrade and downgrade hold the
same writer lock; downgrade uses current locking probes and refuses complete
or partial terminal evidence before DDL. Each successful ALTER is durable at
its own statement boundary. Failure records the completed constraint prefix,
disposes of lost/uncertain owners and never reconnects to continue. Test-only
restoration explicitly inspects and repairs the three known checks on a new
connection; this is not MySQL DDL rollback.

Public status/exit contracts and rendered recovery are specified in the
[client contract](public_client_contract.md#p33-s7-1-session-scoped-native-run-exit).
Immutable `public-run-context/v1`, View associations and Session storage v1 are
unchanged. Exit retains history/storage. Return to setup is a separate local
operation; failed removal blocks admission and storage retry never repeats
exit. New character/profile/world selections and confirmation are explicit.

### Fresh acceptance and retained records

The following records describe the incoming implementation candidate, preserved
as history. The correction below replaces its affected constraint evidence.
Original terminal-family and migration evidence was freshly executed. Raw commands,
source identities, logs and exit statuses are retained under
`C:/Users/dylanmonster/AppData/Local/Temp/deviation-p33-s7-1-implementation-20260918`.
The original `evidence-index.json` binds these records; `candidate-manifest.json`
and `candidate.patch` bind that incoming unstaged candidate, not the corrected one. These external
artifacts are local handoff evidence, not committed repository files.

| Requirement | Actual evidence and boundary |
| --- | --- |
| E01 | `test_mysql_native_run_exit.py` public journeys use production ASGI, real test-MySQL repositories and actual authoritative actions to reach both authored endings. They then exit, read history/status, discover eligibility, admit the same character into distinct Run/line/Session identities and perform the first new action. No direct snapshot mutation supplies these endings. Rendering is deterministic and makes no Provider call. |
| E02 | Both RESOLVED and FAILED journeys preserve canonical character lifecycle. API tests cover active/missing/malformed ending, incomplete memory, wrong scenario/content, Session/Run association and forged controller with no writes. A catalog-valid non-hospital alpine fixture proves the generic ending boundary at component level; it is a test-only authored fixture, not a second E01 public-play journey or new production content. |
| E03 | SQL/Demo full reconstruction rejects partial terminal evidence, corrupted current/receipt fields and ending/catalog/memory associations. Demo parametrizes every stored current-row and mutation-receipt field; real SQL covers corruption at the repository boundary. Old revisions/admission and immutable binding/world bytes remain unchanged. Independent literal canonical bytes and fixed operation/request/evidence hashes prevent self-derived golden expectations. |
| E04 | Real public journeys replay old exit, admission, action and committed request status after the second admission and compare original responses and unchanged second binding. Changed-body conflict and new-key terminal rejection are covered. `mysql-old-status-final` adds the final committed-status comparison to both ending journeys. |
| E05 | Independent MySQL owners cover same/different-key exit, admission, retirement and final-turn races. Tests observe named-lock waiters or the actual waiting `SELECT ... FOR UPDATE` in PROCESSLIST before releasing the holder, then verify one terminal receipt/revision and preserved history. No timing-only or mocked substitute. Extra performance-schema privileges were unavailable and were not requested. |
| E06 | SQL faults/cancellation after append, CAS, receipt and before commit prove atomic rollback. Committed/uncommitted acknowledgement loss, cancellation and postcommit cleanup failure prove explicit uncertainty, GET/exact replay and owner disposal. Demo trial-store fault tests prove matching publication atomicity. |
| E07 | Real MySQL covers empty/populated upgrade and downgrade, old legacy/native row preservation, exact metadata, invalid partial branch rejection, terminal/partial refusal before DDL, stale repeatable-read snapshot and writer/downgrade serialization. Both directions inject failure/disconnect before each of three ALTERs, plus state-only connection loss immediately after each successful ALTER. Exact partial check definitions and completed-prefix diagnostics are asserted. Acquisition/release/disposal result and exception boundaries are fresh. |
| E08 | Rendered App tests cover explicit confirm/cancel, click locking, response loss with GET reconciliation, exact retry, reload/client replacement/unmount, malformed/mismatched status, failed storage removal and storage-only retry, cleared selections and separate new admission confirmation. Existing S6 immutable associations, replacement/recovery and delayed selection tests pass unchanged. No browser was used. |
| E09 | Closed DTO/OpenAPI/transport and key/value projection scans, unchanged old route/schema contracts, legacy/standalone behavior, Dynamic Demo unavailability and restarted-store 404 pass. Independent Demo processes repeat the full journey with identical complete store/result evidence while external I/O is denied. |

| Execution record | Result / applicability |
| --- | --- |
| `canonical-offline-stable` | Canonical sanitized Offline: 2,837 passed, 444 skipped, one deselected; compileall, dependency check, Alembic head/history and diff check passed. Skips were 443 database-dependent cases and one disabled live opt-in. Two warnings: existing S2 model field and unavailable Turkish locale. |
| `final-demo-guard` | 84 focused passes after the final Demo terminal-append guard and classifier type annotations; verifies the last runtime delta after the broad Offline run. Later changes are test assertions/documentation only. |
| `final-canonical-golden` | Final independent literal operation/request/evidence golden case passes; includes a fixed evidence SHA-256 as well as byte equality. Canonical compileall, dependency and Alembic metadata checks also pass on the final test sources. |
| `mysql-canonical-current` + `mysql-current-head-correction` | 223 passes plus five current-head tests rerun successfully after explicitly preparing schema 008. The first five failures were schema-head precondition mismatches; historical migration assertions were not weakened. |
| `mysql-native-stable` | 168 native admission/mechanics/007-migration regression passes, isolated after explicit schema-007 preparation. |
| `mysql-exit-stable` | 60 fresh exit/008 migration passes (27 exit and 33 migration), isolated from other schema-changing suites. |
| `mysql-old-status-final` | Two ending journeys rerun successfully with final old committed-status replay assertions. Overlaps the 27 exit cases; do not add it to unique counts. |
| `mysql-ddl-loss-after` | Six additional fresh upgrade/downgrade post-ALTER state-loss cases pass. Together the isolated MySQL groups cover 462 distinct integration cases; some are metadata-only tests, not 462 real-connection experiments. |
| `metadata-008-02` | Real database at 008 has no Alembic metadata differences, all 18 tables empty and shared lock free. This uses a safe test-only live connection, not the general `.env`-loading Alembic online entry point. |
| `database-restoration-handoff` | Test database restored to original revision 007, all 18 tables empty, shared lock free after final fault/journey tests. |
| `web-stable` | Complete stabilized deterministic-demo Web suite: 340 passed, one existing skipped case, eight files. Earlier affected suites passed; counts overlap. |
| `web-typecheck-final`, `web-lint-02`, `web-build-final` | Typecheck, lint and deterministic-demo production build pass. Build includes final TypeScript compilation. No browser or network installation. |
| `s2-reuse-applicability.json` | Original exhaustive pure S2 node reused only after validating the original correction-run logs/proof/counters, six unchanged source identities, dependency/Python/platform identities and recorded 5,624,910 resolver calls. Original directory: `C:/Users/dylanmonster/AppData/Local/Temp/s3-implementation-20260916-audit/correction`. Other S3-S6 evidence is fresh here. |

Earlier development failures remain in raw logs and are superseded only by
identified corrected runs. In particular, an external helper import failure
prevented schema preparation before `mysql-native-regressions`; the corrected
preparation and `mysql-native-stable` establish the required result. Verification
uses installed `.venv`, sanitized child environments and safe driver/database
identity checks. No production database, real Provider/Live call, dependency
installation or browser acceptance was used. Broad suites were not repeated
solely for documentation changes.

### Dependency inventory, findings and handoff

Section 9 of the frozen plan governs scope. The following listed paths need no
edit: `application/session_service.py`, `application/turn_orchestrator.py` and
`application/narrative_turn_orchestrator.py` already delegate native family
reads/replay and enforce ended guards; no turn algorithm or lock-order change
is needed. `api/demo_composition.py` obtains exit from the normal `ApiServices`
graph. `infrastructure/unit_of_work.py` already supplies the required pinned
factory, writer lock, cancellation and disposal behavior.

The listed existing unit suites `test_run.py`, `test_run_operations.py`,
`test_run_persistence.py`, `test_run_protocol_binding.py`,
`test_run_protocol_binding_persistence.py`, `test_run_repositories.py`,
`test_native_run_admission.py`, `test_native_turn_mechanics.py`,
`test_public_run_protocol.py`, `test_native_demo.py` and
`test_demo_persistence.py` run unchanged. New exit suites own the new contracts.
Web `api/client.test.ts`, `App.recovery.test.tsx`, `App.action-loop.test.tsx`
and existing Session storage tests remain unchanged and pass.

Three necessary inventory additions have bounded demonstrated dependencies:
`tests/unit/test_player_character_api.py` owns exhaustive route/schema inventory
assertions, so adding the two approved routes requires updating those expected
sets while retaining all 75 old components. `docs/engineering/guardrails.md`
records confirmed evidence-before-sort reconstruction and UTF-8 wrapper rules;
`docs/engineering/codex_workflow.md` records the actual evidence-wrapper encoding
failure. Repository AGENTS requires both reusable rules to be synchronized in
the same change. These additions add no feature scope or architectural authority.

DF-001 retains its existing disposition and process-local locale containment.
DF-002 is reassessed and remains deferred: rendered return-to-setup tests prove
separate eligibility/options GET recovery without automatic mutation or stale
selection. Its historical startup browser race was not rerun, and no unrelated
general discovery refresh fix is included. The confirmed Demo corruption defect
(sorting malformed receipt evidence before validating it) is directly related
and fixed with regression coverage; it is not deferred.

The canonical documentation-synchronization checklist is complete: roadmap,
architecture, public contracts, protocol/evidence and findings describe this
candidate and its limits; frozen plans/reviews and prior migrations stay
byte-identical. Original guardrail impact: ENV-001 updated; STATE-002 added. External
candidate checks bind scope, references, UTF-8/LF, whitespace, modes, protected
identities and unchanged baseline/ref/index state. No approval token is issued
by implementation. That independent review returned `CHANGES_REQUIRED` with
one finding; the correction and focused re-review boundary below supersede this
incoming handoff. Staging, commit, push and deployment were not performed.

### S7-1 nullable terminal-CHECK correction

The previous independent review returned **CHANGES_REQUIRED, one finding**:
MySQL accepted NULL `prior_state_version` or `binding_state` in a valid terminal
row because CHECK accepts UNKNOWN. Application validation already rejected the
malformed family; it did not satisfy the required database integrity backstop.
At the historical correction checkpoint this finding was corrected locally,
with no approval issued by the correction task; the replacement candidate then
awaited focused independent re-review of its direct dependencies and evidence.
The corrected implementation is now published at `41d68aac`. Preserve the
earlier verdict and measurements below; neither S7 nor Phase 3.3 is complete.

The production delta is restricted to migration 008 and matching ORM checks:
explicit `prior_state_version IS NOT NULL` and `binding_state IS NOT NULL` in
both Run-table terminal branches. Exact prior/current 3/4 and historical-binding
rules remain. The other required nullable operands already have explicit guards;
the receipt branch uses nonnullable required columns and explicit NULL result
fields. No predecessor branch, earlier migration, column nullability, receipt
branch, lock, probe, DDL ordering or disposal code changed. DB-001 now records
this confirmed SQL three-valued-logic rule and its meaningful regressions.
ENV-001 and STATE-002 and both deferred-finding dispositions are preserved.

External correction evidence is in
`C:/Users/dylanmonster/AppData/Local/Temp/deviation-p33-s7-1-null-check-correction-20260918`.
The original report in `deviation-p33-s7-1-independent-review-20260918` remains
unchanged; a copy, incoming file snapshot, incoming manifest and regenerated
incoming patch are preserved in the correction directory. Incoming verification
matched 41 paths, +2,694/-191. Its **file-content aggregate** was 1,827,791 bytes,
SHA-256 `9a00033d6e9f64bce7327d42a0656cdf7c02555d1bc9b9e23dcdf6a571de5c9a`:
exact full-file bytes concatenated in lexicographic path order without separators.
Its distinct **actual Git binary/full-index patch** was 250,281 bytes, SHA-256
`c1144508210da967b2363d70748b5ee8dab5891d7c60bea9f8492d1e955d2605`.
Historical measurements are preserved; the file-content aggregate is not a patch.

| Replacement record | Result and limits |
| --- | --- |
| `incoming-null-probes` | Before correction, public play/exit produced a valid terminal family. Each of the four independent single-field NULL updates succeeded under enforced original constraints; each was rolled back and the complete scoped family compared unchanged. |
| `corrected-null-regressions` | Four independent MySQL cases pass, each starting with a separately committed public terminal family. Each UPDATE changes only its target field and fails with error 3819 naming `ck_run_revisions_mutation_matrix` or `ck_run_current_mutation_matrix`. Enforcement is YES; clean transaction/rollback, unchanged family, successful status reconstruction and unchanged ended View are asserted. |
| `affected-migration-valid-controls` | 47 passes: all 39 other migration cases, six SQL terminal-corruption/reconstruction cases and both RESOLVED/FAILED public exit/re-entry/replay journeys. Together with the four new cases, all 43 affected migration cases and 51 distinct MySQL nodes pass. Legacy/native predecessor rows survive downgrade/upgrade unchanged. Partial DDL, current probes, writer serialization and disposal cases remain successful. |
| `metadata-and-restoration` | Safe test-only 008 install: Alembic `compare_metadata` has no differences, all three ORM expressions equal migration expressions, and installed CHECK expressions match after MySQL rendering normalization with enforcement YES. Exact initial schema restored afterward. |
| `scope-and-evidence-reuse` | All 133 original evidence artifacts, dependency/environment identities and original S2 proof/log/counter records reverified. Only two production files changed, exclusively the four guards in each; migration control flow, predecessor branches and all application/classifier/Web sources remain identical to the incoming reviewed candidate. |

The MySQL runs use the repository virtual environment and sanitized verification
workflow after `mysql+asyncmy` / `deviation_protocol_test` preflight. Both run
records retain raw commands, source hashes, logs and exit statuses (all zero),
and complete compileall, dependency, Alembic head/history and whitespace checks.
The existing S2 model-field warning remains; no new runtime warning appeared.
No disabled CHECK enforcement, mocked rejection, browser, real Provider,
production database, installation or unrelated network activity was used.

Initial state was freshly observed, not inferred from the review: revision 007,
all 18 application tables empty, shared lock free. `database-initial.json` and
`database-final-restored.json` are byte-identical, including all CREATE TABLE
statements, CHECK definitions/enforcement, table counts, schema version and
shared-lock state. Fixtures were scoped and removed; suites sharing schema ran
sequentially. Restoring the test fixture to 007 does not make it runtime-ready
for terminal writes; runtime still requires corrected 008.

Unaffected stable Offline and its final focused follow-ups, complete Web/lint/
build, pure exhaustive S2, lifecycle and concurrency evidence are reused after
identity/applicability checks. Changed schema evidence is fresh. No full 466-node
integration execution, broad Offline, complete Web or exhaustive S2 rerun was
needed. The four added nodes account for the collection increase from 462.

The correction checkpoint's `candidate-manifest.json` binds that complete candidate and its actual
`candidate.patch`; `correction.patch` binds the incoming-to-corrected delta.
Their sizes/SHA-256 values are separate from the explicitly ordered/framed
file-content aggregate. `correction-delta.json` lists exact changed and
byte-identical preserved paths. That historical correction handoff synchronized
the finding, correction and evidence; it performed no staging, commit, push or
approval. Subsequent publication does not rewrite those measurements or reports.

### S7-1 publication and local browser evidence

S7-1 is published at `41d68aac13ca9129b7f6e08fad5f015987603fda`, subject
`feat: implement P3.3-S7-1 post-ending Run exit`, parent `9fab18d`.
Local HEAD/main/origin/main were verified aligned at 0/0 with clean worktree/index
before the S7-2 planning task, without fetch. No separate publication-closeout
task remains. Frozen plans and earlier CHANGES_REQUIRED verdicts remain history.

The actual report at
`C:/Users/dylanmonster/AppData/Local/Temp/deviation-p33-s7-1-browser-20260918/acceptance-report.md`
was inspected during S7-2 planning; the following summarizes recorded evidence,
not fresh execution by the planning task:

- Actual local deterministic Demo UI play reached RESOLVED `protocol_broken`
  at Session version 19 and FAILED `deadline_reached` at version 10. It exercised
  explicit exit/cancel, terminal refresh/history equality, return to setup,
  separate same-character admission and first action in each new journey.
- Backend restart after service readiness produced old-Session 404 and explicit
  local clear. Restart logs recorded only GET requests, with no automatic write
  replay. First-runtime logs recorded exactly two exit POSTs for the two endings.
- Five focused Offline Demo tests passed, plus compilation/dependency and offline
  Alembic metadata checks. The report notes that Tee-Object did not produce the
  intended raw transcript; observed native output and result JSON were retained.
- The report records unchanged repository, no database or real Provider access,
  owned services stopped, ports 8000/5173 released and the temporary tab closed.

The report's reused implementation patch is a **Git binary/full-index patch**:
262,139 bytes, SHA-256
`cc3e41bab266b04cf357b0e6bcad279542b2e4d7df414fba6a82f4acbd7f4596`.
Its separate correction delta is 38,489 bytes, SHA-256
`65d19e07a90ba5ff3f47b4be885f9aaf51a577265160d5187665b40fbf2a4c8c`.
These report measurements are historical bindings, not a file-content aggregate
or the new S7-2 plan patch.

Browser coverage did not newly exercise response loss, races, storage-removal
faults, late completions, malformed status, every profile, non-hospital content
or real Provider behavior; prior applicable automated evidence owns those cases.
Rendered history equality is not a database-byte audit. No Run/line ID comparison
was exposed by the UI. DF-001/DF-002 remain unchanged: normal return/setup and
ready-before-reload recovery succeeded, but the original startup race was not
deliberately reproduced and DF-002 is not closed. This establishes the bounded
integrated local flow, not limited-trial or broader-release readiness, S7 or
Phase 3.3 completion. Planning did not rerun acceptance or access the database.

## P3.3-S7-2 same-line continuation

The [published plan](phase_3_3_s7_2_same_line_world_continuation_plan.md) is
independently approved at `2c272487a2f12c60c28ada95dd9a3f1edf1d42ba`; the user
approved P01–P08 and chose to complete this journey before reconsidering genre
or balance. Its published patch was 124,937 bytes, +1,289/-61, SHA-256
`91b6e2332a693b1eb5e88b5ae9061c1bd15c04bdf3cd6a4ae7b59ee222c0f9f9`.
The plan bytes and historical reviews are unchanged.

The published implementation continues the existing Run and line into **未送达的回执** after
explicit confirmation. The character association and full remaining PlayerState
carry unchanged. Local state resets, original history remains owned/readable,
and GET exposes a required nullable predecessor from complete reconstruction.
Original admission context retains its meaning. Continued exit reaches revision
five; a separately confirmed admission creates a new Run. There is no third
world, revisit, reward, refill, character revision or normal Run completion.

Current code, C01–C10 automated evidence, source applicability, documentation
synchronization and the frozen review package are recorded at the top of this
document, with subsequent publication at `6dfbd37` and inspected local browser
evidence above. This synchronization issues no independent approval or broader
readiness claim. S7-3 now has an approved published plan and a separately authorized local
implementation candidate awaiting focused independent re-review after the automatic Journey/status consistency correction; S7-4/5
and parent criteria 10–12 completion remain outside the delivered increment. S7 and Phase 3.3 are incomplete.

## Related documents

- [Project roadmap](../PLANS.md)
- [Published P3.3-S2 deterministic profile-resolution plan](phase_3_3_s2_deterministic_profile_resolution_plan.md)
- [Published P3.3-S3 persistence plan](phase_3_3_s3_persistence_legacy_native_compatibility_plan.md)
- [Published P3.3-S4 native admission and entry-world plan](phase_3_3_s4_native_run_admission_entry_world_plan.md)
- [Published P3.3-S5 mechanics and prompt-context plan](phase_3_3_s5_objective_mechanics_prompt_context_plan.md)
- [Frozen Phase 3.3 implementation plan](phase_3_3_run_protocol_implementation_plan.md)
- [Minimum Run Core Implementation Plan](minimum_run_core_implementation_plan.md)
- [Narrative Provider boundary](narrative_provider.md)
- [NPC Relationship and Temporary Residence](npc_relationship_residence.md)
- [Current scenario specification](scenarios/death_certificate_v1.md)

## Experimental Dynamic Narrative Vertical Spike boundary

The DNVS candidate reuses the current implemented Run-entry operation and its
one active Player Character binding. It creates the Session, participation,
snapshot, initial event, and declared runtime NPCs atomically, assigning NPC
instance IDs from scenario declaration order as `scenario-npc-1..N`. Dynamic
story state remains Session/GameState authority; Run identity, continuous-story
line identity, participation, binding, lifecycle, and ownership remain unchanged
and are revalidated on every reconstruction.

This experimental composition neither implements nor amends the deferred formal
Run Protocol described in this document. It is outside Phase 8, creates no
P8-S7, and leaves completed P8-S6/Phase 8, paused Phase 6, and inactive Phase 7
exactly as recorded in `PLANS.md`. The DNVS and its bounded autonomous
improvement lifecycle are closed; neither supplies Phase 3.3 implementation
evidence or Provider/world authority.
