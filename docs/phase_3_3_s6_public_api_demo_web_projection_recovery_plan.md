# P3.3-S6 Public API, Demo, Web, Projection and Recovery Plan

Status: **Documentation candidate, unapproved; S6 implementation has not started.**
Authored 2026-09-17 against `main` at
`86c258e9ad2e64199cabf8650bf6f3a7b5f04d87`, subject
`feat(run): implement Phase 3.3 S5 objective mechanics and prompt context`,
parent `ff866d2fd40181e0bf27937d255d70ebd1ae1544`. Local HEAD/main/origin/main
matched, ahead/behind was `0/0`, worktree/index were clean, and no conflicts,
operations or locks were present. Verification was local, without fetching.

S5 implementation is independently approved and published at this baseline,
with DF-001 deferred. Frozen candidate-time wording and historical reviews in
S1-S5 plans remain history. This plan neither reopens them nor authorizes code,
tests, database access, browser use, Provider calls or Git writes. Phase 3.3
remains incomplete after this bounded S6 allocation; S7 and Phase 3.4 remain later.

## 1. Deliverable and existing seams

The proposed primary journey is: select an owned eligible character or explicitly
create one -> explicitly select a difficulty profile and eligible authored world
-> review permitted numeric overrides and presentation -> enter once -> save
the validated Session recovery identity -> fetch authoritative View -> play,
reload/recover and reach an authored Session ending. Deterministic Demo supplies
the user-operable local experience. Normal composition exercises the same public
and application contracts with fake Providers in acceptance; S6 adds no production
Provider integration or fallback. Existing not-configured behavior stays explicit.

Controlling references: [AGENTS](../AGENTS.md), [workflow](engineering/codex_workflow.md),
[guardrails](engineering/guardrails.md), [deferred findings](engineering/deferred_findings.md),
[roadmap](../PLANS.md), [parent/S1](phase_3_3_run_protocol_implementation_plan.md),
[S2](phase_3_3_s2_deterministic_profile_resolution_plan.md),
[S3](phase_3_3_s3_persistence_legacy_native_compatibility_plan.md),
[S4](phase_3_3_s4_native_run_admission_entry_world_plan.md),
[S5](phase_3_3_s5_objective_mechanics_prompt_context_plan.md),
[public client](public_client_contract.md), and
[frozen Demo contract](phase_3_2_deterministic_demo_environment.md).

| Inspected existing interface | Required connection |
| --- | --- |
| `api/main.py:create_app`, `api/schemas.py`, custom OpenAPI installers | Add separate native routes/DTOs; preserve existing `POST /v1/runs`, `/v1/sessions` and their strict transport, status and evidence contracts. |
| `ApiServices.native_run_admission_service`, `build_native_run_admission_service` | Production already supplies S4 with its pinned-connection native admission UoW. The new POST calls that service once. |
| `NativeRunAdmissionCommand`, `NativeRunAdmissionService.enter` | Convert public intent into exact S1/S2/world carriers. Reuse owned replay before fresh eligibility and the existing single atomic admission. |
| S2 profile catalogue, `lookup_entry_world`, loaded `SessionService` catalogue | Source discovery from versioned authority and existing public copy. Scenario discovery is not world discovery. |
| `SessionService.get_view`, `PlayerSessionView` | Add one optional native context projection inside the same read UoW as the validated snapshot/View. No second recovery write or mutation endpoint. |
| `NativeTurnMechanicsCoordinator.load`, S3/S4 classifier, participation reverse lookup | Reuse complete native/legacy proof and original-state checks for native View recovery; never infer a native protocol from request/local storage. |
| `DemoProcessStore`, `_AuthorityMaps`, `DemoUnitOfWork` | Missing native protocol/world repositories and native receipt insertion need process-local adapters, staged and atomically published with existing maps. |
| `CanonicalDemoNarrativeTurnOrchestrator`, `CanonicalDemoProviderGuard` | Existing legacy script checks exact narrative stages/event counts; it cannot simply accept S5's extra events. Keep that script intact and compose a separate native delegate with equivalent call-authority protection. |
| `DeterministicDemoNarrativeProvider` | Already renders a bounded candidate deterministically. Native S5 supplies a singleton result; rendering cannot select mechanics. |
| `web/src/api/{schemas,client}.ts`, `App.tsx`, `sessionRecovery.ts` | Extend validated discovery/admission/View consumption while retaining single-flight, generation ownership, exact retry and the existing version-1 same-tab recovery record. |

All decisions below are S6 public/product proposals for review, not claims about
currently implemented routes. The approved numeric balance and authority rules
are reused unchanged. No unresolved product choice blocks this proposal.

## 2. Discovery and explicit choices

Add `GET /v1/run-entry-options`, operation ID `get_run_entry_options`. It accepts
no query, body or caller filter. Reject supplied query/body with the fixed 422
envelope. It returns public catalogue information, performs no private character
read, and needs no controller identity. HTTP 200 body is exactly:

```text
RunEntryOptionsResponse {
  schema_version: "run-entry-options/v1",
  native_entry_available: boolean,
  profiles: PublicRunProfile[],
  entry_worlds: PublicEntryWorld[],
  presentation_options: {
    world_tone: ["grim", "balanced", "heroic"],
    reality_boundary: ["lawful", "deviant", "chaotic"],
    relationship_overlay: ["off", "veiled", "charged"]
  }
}
PublicRunProfile {
  profile_ref: {profile_id: SafeId128, profile_version: PositiveInt64},
  label: string,
  defaults: FiveObjectives,
  override_rules: [{parameter: ObjectiveName, minimum: integer,
                    maximum: integer, step: 5}]
}
PublicEntryWorld {
  entry_world: {entry_world_id: SafeId128, entry_world_version: PositiveInt64},
  scenario_id: SafeId128, scenario_content_version: SafeId32,
  title: string, hook: string,
  eligible_profiles: [{profile_id: SafeId128, profile_version: PositiveInt64}]
}
```

`FiveObjectives` has exactly resource_pressure, social_trust,
consequence_severity, information_opacity, conflict_intensity; each exact integer
is in `0..100`, step 5. `ObjectiveName` contains only those five literals. Rules
have exactly those five entries in that order. All nested objects are closed;
required fields have no inferred defaults. IDs use existing ASCII
`[A-Za-z0-9][A-Za-z0-9_.:-]*`, lengths 1..128 (32 for content version, 64 for
Session ID). PositiveInt64 is exact non-Boolean integer `1..9223372036854775807`.
Published profile/world versions are all 1. Web continues rejecting integers
outside JavaScript's safe range rather than rounding, as it does for character
revisions; introducing a big-integer transport is outside this slice.

The profile list retains S2 catalogue order: Extreme, Standard, Easier. Exact
labels are `Extreme — Silent Hunting Ground`, `Standard — Fragile Alliance`,
`Easier — Open Expedition`; label bound is 1..128 Unicode code points. Defaults
and inclusive override ranges below use the five-field order above; every step
is 5. Read these from S2, not a second server or client balance table.

| Profile ID (version 1) | Defaults | Inclusive ranges |
| --- | --- | --- |
| `difficulty.silent-hunting-ground` | 95, 10, 95, 90, 90 | 80..100, 0..25, 80..100, 75..100, 75..100 |
| `difficulty.fragile-alliance` | 60, 45, 65, 60, 60 | 40..75, 30..65, 45..80, 40..75, 40..75 |
| `difficulty.open-expedition` | 25, 70, 35, 30, 35 | 10..40, 55..85, 20..50, 15..45, 20..50 |

S6 exposes exactly `world.death_certificate@1`, backed by `death_certificate` /
`death-certificate-1.1.0` / `character.death_certificate.investigator` from S4.
Only the first two associations are public. Title/hook are copied field by
field from that scenario's existing validated `public_client` description;
use its existing title 1..120 and hook 1..300 Unicode-code-point bounds, with
plain text and no new story text. All three listed profiles
are eligible. Sort worlds by ASCII ID then numeric version; eligible_profiles
follows profile catalogue order. No unlock, recommendation, random selection or
permanent default-world designation exists. This is bounded exposure of one
already authored world; adding another needs its own reviewed authoring scope.

Response arrays are bounded by the current catalogue: profiles 0..3, worlds
0..1, eligible_profiles exactly the three unique published pairs for that world,
and override_rules exactly five unique entries. When native composition is
installed, discovery contains exactly three profiles
and one world, validated against S4 and S5 catalogue associations at composition.
Missing/mismatched server catalogue is an integrity failure, not an empty usable
list. In the explicitly non-native Dynamic Demo, and deliberately injected
legacy-only services, `native_entry_available=false`, both lists are empty, and
presentation_options retains the same enums. No fallback is selected by a
failed HTTP request. Capability comes from the composed service graph, never
environment values in the response, prose, a scenario name or the client.

Character eligibility remains the existing
`GET /v1/player-characters/eligible-for-run-entry`: owned, active, no active Run,
case-sensitive ID order, at most 32 and `truncated` as implemented. Entry rechecks
revision/successor capacity and occupancy under its existing lock. Discovery is
advice, not a reservation. Existing minimal creation and owned read stay unchanged.

UI starts with no selected profile or world, including when only one world is
available. Selection explicitly fills displayed base values; unchecked override
controls emit no entry. A checked override equal to the base remains explicit.
All five overrides are optional individually; the array itself is required.
Profile changes clear overrides and world selection; world choices are filtered
by the returned exact eligible profile pairs. Presentation controls initially
display balanced/lawful/off as a **UI proposal**, shown in the final review;
every POST must include all three. These are not S1/S2 server defaults. Submission
is the explicit confirmation of the displayed choices. Missing profile, world,
overrides or presentation never causes implicit Standard/native/legacy selection.

Discovery refresh is GET-only and replaces the selection generation. Keep only
still-present exact pairs and still-valid overrides, visibly clear anything
removed/incompatible, and require another explicit entry confirmation. Never
upgrade/downgrade/alias a stale pair or clamp a value. While an entry attempt is
unresolved, lock discovery refresh and edits so its retained request cannot drift.

## 3. Native public admission and compatibility

Add `POST /v1/runs/native`, operation ID `enter_native_run`, HTTP 200 for first
committed success and exact replay. Existing `POST /v1/runs` remains exclusively
legacy with identical request/response/evidence/error precedence; no body-shape
overload or `native` switch is added there. `/v1/sessions` remains available.
New native routes are registered in all normal/Demo apps; an explicitly absent
native service returns the fixed 503 below, never a legacy call. Existing
conditional registration for old routes remains intact.

Native POST accepts no query parameters. Required single raw `Idempotency-Key`
and `Content-Type: application/json` follow
the current Run-entry transport validator: no duplicate headers, no whitespace
normalization of keys, exact opaque ASCII 1..128 grammar, same media-type parameter
handling. Reject duplicate JSON members at every depth before DTO conversion,
non-finite numbers, BOM/malformed encoding, extras/missing fields, nulls, booleans
as integers, floats (including `1.0`), coercion and invalid enums. New request
raw UTF-8 bound is 4,096 bytes, checked before JSON decoding; over-limit returns
the same 422. This public bound does not alter any internal S1-S5 byte ceiling.

Exact closed `NativeRunEntryRequest` example:

```json
{
  "player_character_id": "pc.example",
  "expected_record_revision": 1,
  "profile_ref": {"profile_id": "difficulty.open-expedition", "profile_version": 1},
  "entry_world": {"entry_world_id": "world.death_certificate", "entry_world_version": 1},
  "overrides": [],
  "presentation": {"world_tone": "balanced", "reality_boundary": "lawful", "relationship_overlay": "off"}
}
```

`overrides` is a required array of 0..5 closed `{parameter, value}` entries.
Public DTO validation enforces enum, lattice and unique parameter; S4/S2 enforce
the exact profile ranges and Cartesian compatibility. Caller order has no
semantic effect. Omission of an entry differs from an explicit base-valued
entry. Request forbids scenario/character-definition IDs, resolved objectives,
resource labels, fingerprints, envelope bytes/schema selectors, catalogue
definitions, controller/player/Run/line/Session IDs, state or authority fields.

The route constructs exact S1 wrappers/enums and envelope with server-selected
schema `run-protocol-envelope/v1`, an S2 proposal sharing that profile reference,
and S4 world reference, then calls the composed `NativeRunAdmissionService.enter`
once. It does not resolve defaults separately, stage records, call legacy entry,
preempt S4's receipt-before-fresh-eligibility order, or invoke a Provider. S4
owns the one admission transaction, receipts, all IDs and source, second-precision
time, reconstruction, named-lock release and collision recovery. Native and
legacy internal ID prefixes remain distinct; using a key on one route does not
replay the other family, and active-character occupancy still prevents two Runs.

Exact `NativeRunEntryResponse` fields are `session_id`, `scenario_id`,
`scenario_content_version`, `run_context`. `run_context` is exactly the following
closed `PublicNativeRunContext`, shared with the View projection:

```json
{
  "schema_version": "public-run-context/v1",
  "run_id": "run.example",
  "player_character": {
    "player_character_id": {"value": "pc.example"},
    "contract_version": "structured-player-character/v1",
    "record_revision": {"value": 1},
    "lifecycle": "active"
  },
  "entry_world": {"entry_world_id": "world.death_certificate", "entry_world_version": 1},
  "profile_ref": {"profile_id": "difficulty.open-expedition", "profile_version": 1},
  "objectives": {"resource_pressure": 25, "social_trust": 70, "consequence_severity": 35, "information_opacity": 30, "conflict_intensity": 35},
  "presentation": {"world_tone": "balanced", "reality_boundary": "lawful", "relationship_overlay": "off"},
  "resource_pressure_label": "Generous"
}
```

The character projection describes the **admitted immutable reference**, not a
new current eligibility claim. S4 proves its active lifecycle. Projection builds
new allowlisted objects from revalidated `NativeRunAdmissionResult`; compare
character/revision, profile, world and presentation against submitted intent,
and scenario/content against the validated result/world association before
returning. Do not serialize/exclude fields from an internal result. First success
and exact replay remain equal after gameplay advances. No initial Frame or live
Session revision is included; View is always fetched next.

Every error uses existing `{error:{error_code,message}}`, without extra detail.
The following exact native POST mapping preserves S4 decision order. Integrity
and impossible results are not misreported as caller errors.

| Owner/result | HTTP / code | Fixed message |
| --- | --- | --- |
| Transport/DTO | 422 `REQUEST_VALIDATION_FAILED` | `Request validation failed` |
| AUTHORIZATION_FAILED (missing/foreign character or controller unavailable) | 404 `PLAYER_CHARACTER_NOT_FOUND` | `Player character was not found` |
| IDEMPOTENCY_CONFLICT | 409 `IDEMPOTENCY_CONFLICT` | `Idempotency key was reused` |
| PLAYER_CHARACTER_STALE | 409 `PLAYER_CHARACTER_STALE` | `Player character revision is stale` |
| PLAYER_CHARACTER_NOT_ELIGIBLE | 409 `PLAYER_CHARACTER_NOT_ELIGIBLE` | `Player character is not eligible for Run entry` |
| INVALID_PROTOCOL (unknown/unsupported pair or incompatible override) | 422 `INVALID_RUN_PROTOCOL` | `Run settings are not available` |
| INVALID_ENTRY_WORLD (unknown/unsupported pair) | 422 `INVALID_ENTRY_WORLD` | `Entry world is not available` |
| INVALID_SCENARIO_DEFINITION | 422 `INVALID_SCENARIO_DEFINITION` | `Scenario definition is not available` |
| RUN_ENTRY_CONFLICT | 409 `RUN_ENTRY_CONFLICT` | `Run entry conflicts with current state` |
| Explicitly non-native composition | 503 `NATIVE_RUN_ENTRY_NOT_AVAILABLE` | `Native Run entry is not available` |
| Corruption, persistence, impossible result, uncertain commit | 500 `INTERNAL_SERVER_ERROR` | `Internal server error` |

Transport validation precedes the absent-service 503. Cancellation propagates
through S4 cleanup; no automatic retry. Options declares 200/422/500; native POST
declares 200/404/409/422/500/503 in OpenAPI using public DTOs and ErrorResponse,
never FastAPI's default validation body. Add no undocumented 201/202 here.
Generated OpenAPI must omit internal native result, envelope, job and evidence
models; legacy path schemas/statuses/operation IDs remain structurally equal.

## 4. View recovery and disclosure

Add optional `PlayerSessionView.run_context: PublicNativeRunContext`, omitted
entirely for proven legacy/standalone Sessions. No null or synthetic native
defaults. It is the same immutable setup object returned by admission, even at
an ending; ordinary View resources/clocks/affordances remain current state.
Do not add a Run read/list/resume route or a new recovery persistence record.

Production and deterministic Demo install a native View reader alongside the
coordinator. Composition must validate admission, native turn and native View
support as one complete graph; a partially installed graph fails construction,
never advertises native availability or silently omits native View context.
In the existing `get_view` UoW, first establish owned Session and
validate the original current snapshot using existing `_load_state`; read forward
participation and bounded reverse attachment evidence, then reuse complete S3/S4
classification and S5 `load` association validation. No participation plus no
reverse evidence is standalone; a participating legacy family needs positive
`LegacyRunCompatibilityV1` proof. Partial native family, missing world/protocol,
cross-bound receipt, orphan attachment or S3 component-only binding cannot omit
the field and continue. Preserve both receipt/protocol equalities and all immutable
character, Session initialization, latest snapshot and world/content checks.

For native disclosure additionally resolve the current principal's controller
and use the existing `uow.player_characters.get` and `uow.controller_bindings.get`
read ports to prove the admitted character remains owned by that controller.
Reuse their canonical validation; compare with the classifier's bound reference,
never treat classification alone as caller permission. No locking character
reader, nested service UoW or fresh eligibility check is needed. Missing caller
authority/foreign Session or character yields the existing non-enumerating
404 `SESSION_NOT_FOUND` / `Session was not found`. Corrupt surviving evidence,
snapshot or associations yields the existing View 409 `SNAPSHOT_INVALID` /
`Session state is unavailable or incompatible`; unrelated infrastructure failures
retain safe 500. This is a bounded View error adapter, not an exception rewrite
inside S3/S4. No raw cause, canary, SQL or model payload is returned or logged.

Perform the context read and normal View projection within the same ordinary
read transaction, with no FOR UPDATE, named-lock acquisition, commit, repair,
Director advancement, compiler or Provider. Exit closes the AsyncSession. S4's
Run revision 3 and character binding remain immutable during current Session
play. No extra Session version is invented for the immutable setup. Native
context is never constructed from a previously returned DTO or browser cache.

Discovery exposes only section 2 fields; admission and recovery expose only
section 3 fields in addition to the existing View. Public pressure label is
derived using S5's existing projection: Generous 0..30, Fluid 35..65, Scarce
70..100 on the valid step-5 lattice. Boundaries 30/35 and 65/70 must be tested.
Keep the exact numeric value alongside the label; 31/34/66/69 are invalid
inputs, not values to round. Labels are output-only, never override aliases.

Exclude line/controller/source identities, fingerprints, receipts, mechanics
decisions/audits, compiled prompt context, model output, private clocks/NPC state,
hidden clues/facts, future scenes/endings and static-character authority from
the new fields. Scan serialized values as well as keys. Do not reuse the private
S5 compiler as a public serializer: its selected_result has no place here.
Presentation does not alter mechanics, resources, relationships, death, world
selection or canon. Overlay neither reads nor anticipates Phase 3.4 state.

## 5. Web journey, uncertainty and explicit recovery

Use the existing foreground-operation and mutation-attempt generation ownership.
Keep protocol IDs internal to controls; player copy describes actions such as
“选择角色”, “选择难度”, “选择起始世界”, “确认并开始”, “重试本次进入”,
“刷新可用选项”, “重新读取进度”, “清除此标签页进度”. Never show fingerprints,
key/body dumps, transaction details or promises of guaranteed success/survival.

| Screen/state | Primary action and required behavior |
| --- | --- |
| Loading discovery/characters | GET options and eligible characters; disable entry. Separate bounded loading/failure states; explicit GET refresh. Failed options do not activate legacy automatically. |
| Character selection/creation | Select an exact eligible projection. Offer explicit minimal creation with the existing request/idempotency rules; creation never also enters a Run. Empty/truncated collections are shown accurately. |
| Native setup | Explicit profile/world selection; display five values, permitted min/max/step and override enable controls; show all presentation settings. Invalid input blocks submission without network. Profile/world are never selected from the first list element. |
| Native unavailable / legacy mode | `native_entry_available=false` displays native unavailability and offers explicit existing scenario entry. When native is available, legacy scenario entry remains a secondary explicit mode. Modes have distinct frozen attempt types; switching is forbidden during an unresolved attempt. Dynamic Demo retains its existing scenario and suggestions. |
| Review / sending | One confirmation freezes URL, idempotency key and serialized validated body before POST. Lock all entry/creation/mode controls synchronously before any await; duplicate clicks issue no second send. |
| Admission uncertain | Retain exact key/body/URL and uncertainty history in component memory. Only explicit same-attempt retry may POST; no replacement key, body edits, discovery refresh or automatic replay. |
| Admitted, storage pending | Validate response and identity, retain it in memory, write existing recovery record before View fetch or clearing the attempt. Storage failure locks controls; explicit storage retry writes the retained identity without POST. |
| Admitted, View loading/failed | Identity is already stored. Fetch View, bind Session/scenario/content and immutable native context to the admitted response. Failure permits explicit GET retry only. Missing/mismatched expected native context fails closed. |
| Active play | Display setup summary from View and existing resources/affordances; action results/polling require the current operation generation and Session. Fresh authoritative View replaces prior controls. No optimistic mechanics or local outcome prediction. |
| Reload/manual recovery | Existing version-1 Session record or validated manual Session ID -> GET View (and request-status for an already confirmed pending request). Native context is learned from validated View. No discovery setting is used to reconstruct it. |
| Ended | Show only authoritative ENDED plus RESOLVED/FAILED and public ending text; no action controls. Clearing this tab permits another explicit setup, but does not complete/detach the still-active Run or make its character eligible. |

Freeze a native attempt's exact serialized request string at first send; client
validation must not reserialize it from mutable form data on retry. Retain the
selected public association for response checks, not as server authority. Verify
profile/world/character/revision/presentation and explicit overrides agree with
the response; numeric fields and labels satisfy the strict response schema and
the selected version's advertised values/ranges. No response from an old client
instance, mode, Session, operation generation or unmounted component may update
storage or UI, even if abort cannot cancel the transport.

For native attempts, definitive first-send documented 404/409/422 can end that
attempt. Stale/ineligible/conflict character outcomes clear the selection and
require eligible-character GET refresh; protocol/world/scenario rejection clears
affected setup and requires options refresh. Validation error returns to editing.
Idempotency conflict stops that attempt; a new entry always requires explicit
review and a fresh key. A received absent-service 503 can end an untainted attempt
and require options refresh. None of these transitions automatically POSTs.

Network loss, abort/timeout after dispatch, malformed/unrecognized response,
identity mismatch or safe 500 taints uncertainty. For a **tainted native attempt**,
retain it after every non-success, including later 404, 409, 422 or 503: none is
used to infer that an earlier send did not commit. Only a matching authoritative
200 plus successful Session identity storage resolves it automatically. This is
the proposed conservative native rule; existing legacy/character-creation error
classification remains unchanged, including its history-sensitive 404 handling.
The user may explicitly leave the experience, with a clear warning that the
pending entry cannot be recovered after reload; do not offer a silent replacement.

Keep sessionStorage's exact current `{version:1, session_id,
client_request_id?}` allowlist. No protocol/world/key/body/character/Run data goes
into it, URLs, logs, localStorage or IndexedDB. Pending entry attempts remain
memory-only as in Phase 8: reload before validated success and storage cannot
recover them. This limitation is stated before entry, not hidden behind a false
recovery promise. Cross-tab/device/browser-close recovery is not added.

After confirmed 202, retain only the existing bound request identity and poll
GET status as directed. COMMITTED -> GET fresh View; STALE -> explicit View
refresh; OUTCOME_UNKNOWN/FAILED -> no replay; missing/unavailable/malformed
recovery pauses controls. Explicit “retry recovery” repeats GETs only. Manual
Session replacement, API-client replacement, clear, restart and unmount invalidate
old generations and clear display-only setup/evidence. A previously native View
cannot become legacy within that live Session generation merely because a later
response omits context.

Demo backend restart discards process-local state. Recovery of an old Session
in the empty restarted backend returns safe 404; pause and offer explicit local
record clearing, then a newly confirmed character/setup journey. Never use 404
to manufacture a replacement Session. Deterministic IDs are process-local, not
global cross-restart identity; no cross-process pending-operation guarantee is
claimed. Browser storage failure remains fail-closed until explicit successful
storage repair/clear. Clearing a record has no server mutation.

## 6. Demo adapters and production integration

Extend deterministic `build_demo_runtime`, not normal production persistence or
the legacy fixed script. Compose real `NativeRunAdmissionService` with the Demo
UoW factory, existing deterministic Run/line/Session/event/seed/clock issuers,
configured Demo controller and source, SessionService and real S5 coordinator.
Do not call the SQL-native factory or introduce MySQL/SQLite fallback in Demo.
Production continues using `SqlAlchemyNativeRunAdmissionUnitOfWorkFactory` and
its existing migration exclusion lock unchanged.

Required Demo storage additions mirror **existing** durable families only:
protocol-binding and entry-world-binding maps and pending maps, native creation
receipt encoding, and read-only reverse attachment lookup from mutation receipts.
Include them in detached snapshots, trial maps, commit conflict checks, atomic
publication, rollback and restart reset. Implement the existing
`RunProtocolBindingRepository` and `RunEntryWorldBindingRepository` ports;
repositories never commit. Restrict native inserts to an explicitly constructed
Demo native-admission UoW capability, not an ordinary turn/read UoW. This is a
process-local writer guard, not a simulated database named lock.

Use S3/S4 pure storage codecs and validators in
`run_protocol_binding_persistence.py`: stored protocol/world carriers,
`_reconstruct_native_binding`, `_reconstruct_world_binding`,
`_native_entry_evidence`, `_validate_native_character`, `_complete_native_admission`,
and the corresponding positive legacy checks. Build detached field-for-field
row-shaped inputs from Demo's existing stored records; no fake SQLAlchemy Session
or mock DB query engine in runtime. Preserve original types and failure ordering.
The Demo classifier implements the same load prerequisite/branch sequence as
`SqlAlchemyRunProtocolBindingRepository._classify`, including immutable character
before Run validation, orphan checks and both receipt/protocol equalities.
Do not reduce reconstruction to presence of two maps or cache a trusted DTO.
Shared pure codecs need no semantic change; any necessary adapter extraction
must be behavior-preserving, separately identified and covered by both adapters.

At Demo `handle`, reject nested/inherited active Provider authorizations before
sequence-lock lookup, UoW construction or snapshot work (AUTH-002). A composed
dispatcher then performs read-only complete family validation and chooses the
legacy canonical delegate or native S5 delegate; errors never fall through.
Standalone and proven legacy retain the existing script, progress counters,
deterministic event issuer and exact historical cross-process trace. Native uses
`DurableNarrativeTurnOrchestrator` with S5 and the same deterministic event-ID/time
issuer, without legacy stage/event-count assertions or completion counter.

The native fake-rendering guard is task-bound, bound to Session/turn/request/
signature and the prepared job, and consumed synchronously once before delegation.
It verifies the authenticated compiled attachment, single candidate/result and
detached job association; S5 remains the outcome authority. Run PromptBuilder
and the existing deterministic renderer outside all UoWs and gameplay locks.
Only the per-Session orchestration sequencing lock may span rendering. Never expose
the capability/wrapped renderer on public objects. Failure/cancellation cannot
restore an allowance; validated-proposal resume finalizes without another call,
and committed replay bypasses rendering. Independent later transactions remain
usable. Direct/nested/same-task/cross-Session/inherited/concurrent calls require
the existing AUTH-002 strength of denial evidence, not just store equality.

Native Demo accepts ordinary policy-valid public actions, not only the canonical
test transcript. Reuse S5's preselection and validator; the deterministic provider
produces expression only and is still untrusted. No separate Demo mechanics,
resource saturation, clock order, clue rules, ending logic or weakened prompt
contract. Native semantic state/events must match production with equal injected
inputs (compare legitimate metadata differences explicitly).

Dynamic Demo keeps its existing legacy admission, fake/live opt-in boundaries,
public suggestions and committed-response recovery unchanged; it advertises native
entry unavailable. No native-to-Dynamic promotion or new Live permission. A native
request to it fails with the documented 503. External database/Provider/settings
constructors, dotenv reads and network delegation remain denied in deterministic
Demo. No new production content, configuration flag, package or migration is needed.

## 7. Dependency-derived future implementation inventory

Paths are exact proposals, not a numerical cap. Prefixes below are repository
relative. New files are marked **new**; all other listed paths exist at baseline.

| Edit path | Concrete responsibility |
| --- | --- |
| `src/deviation_protocol/application/public_run_protocol.py` **new** | Closed public projection models, catalogue projection and field-by-field immutable native context construction; no Provider or write authority. |
| `src/deviation_protocol/api/run_protocol_routes.py` **new** | Strict bounded raw native request parsing, options/native POST, decision/error translation and public OpenAPI installation. |
| `src/deviation_protocol/api/schemas.py` | Exact native request/response DTOs sharing application projection types; no changes to old DTOs. |
| `src/deviation_protocol/api/dependencies.py` | Explicit native/discovery dependency access and capability from the service graph; optional injection keeps old test/service compositions valid. |
| `src/deviation_protocol/api/main.py` | Register routes, install native View reader/coordinator/controller resolver and share composition authorities; preserve SQL native UoW. |
| `src/deviation_protocol/application/session_service.py` | Optional View context/read integration, same-UoW ownership/classification, safe error boundary, omit field on legacy; no turn effects. |
| `src/deviation_protocol/infrastructure/demo_persistence.py` | Native binding/receipt/reverse-read adapters, complete classifier inputs, native writer capability and atomic process-store map lifecycle. |
| `src/deviation_protocol/infrastructure/native_demo.py` **new** | Native deterministic orchestration dispatcher/guard, task-bound single-use fake-rendering boundary and legacy delegation. |
| `src/deviation_protocol/infrastructure/demo_authority.py` | Minimal shared active-authorization rejection across legacy/native delegates; keep legacy checkpoints and progress semantics. |
| `src/deviation_protocol/api/demo_composition.py` | Compose both deterministic delegates, S4 admission and native View projection; explicit Dynamic unavailability. |
| `web/src/api/schemas.ts` | Strict options/native admission/context schemas, safe integers, exact enums/ranges/label consistency and optional View field. |
| `web/src/api/client.ts` | Discovery and native methods, exact serialized body retention/retry, response binding and no automatic fallback. |
| `web/src/api/errors.ts` | Bounded user-facing native validation/unavailability error copy without leaking internals. |
| `web/src/runSetup.ts` **new** | Pure typed setup/attempt transitions, explicit selections/override presence, generation-bound response expectations and tainted native retry rules. |
| `web/src/App.tsx` | Character -> setup/review -> native admission -> storage -> View; explicit legacy mode, GET recovery, ending and stale completion handling. |
| `web/src/styles.css` | Accessible setup/validation/disabled-state layout using current visual system. |
| `tests/unit/test_public_run_protocol.py` **new** | Discovery/projection literal allowlists, catalogue associations, labels and closed disclosure. |
| `tests/unit/test_native_run_entry_api.py` **new** | ASGI native transport/dispatch/identity/errors/OpenAPI and no-write rejection. |
| `tests/unit/test_session_service.py` | Native View binding/ownership/read-only errors and legacy omission; instrument read adapters. |
| `tests/unit/test_run_composition.py` | Native routes and View share actual production services, no Provider construction for discovery/admission. |
| `tests/unit/test_phase_3_0_public_client_contract.py` | Additive View/OpenAPI shape and nested value disclosure; preserved legacy contract. |
| `tests/unit/test_demo_persistence.py` | Native staged maps, shared-codec corruption, conflicts, atomic rollback/cancel and detachment. |
| `tests/unit/test_demo_composition.py` | Updated additive route set, actual native entry/play/View and explicit Dynamic exclusion/external-I/O denial. |
| `tests/unit/test_native_demo.py` **new** | AUTH-002 negative call probes, native non-script actions, fake rendering, replay/resume and legacy dispatcher isolation. |
| `tests/integration/test_mysql_native_run_api.py` **new** | Normal public admission -> all native turns -> View/reload/replay/ending, real transaction/failure/ownership evidence. |
| `tests/e2e/test_native_demo_playthrough.py` **new** | In-process public full journey and independent child-process deterministic native replay without HTTP listener/browser. |
| `tests/e2e/support/native_demo_replay_child.py` **new** | Sanitized child ASGI driver for fixed caller inputs, response/store observations and process reset; no runtime import from tests. |
| `web/src/api/client.test.ts` | Exact route/status/schema/body retry, identity/label mismatch, no implicit dispatch. |
| `web/src/runSetup.test.ts` **new** | Setup/override/state transition unit cases and uncertainty retention. |
| `web/src/App.test.tsx` | Rendered explicit native and legacy selection, minimal creation, validation, single-flight and setup confirmation. |
| `web/src/App.recovery.test.tsx` | Storage-before-View, storage retry without POST, stale response, tainted errors, native reload and restarted backend. |
| `web/src/App.action-loop.test.tsx` | Native setup through returned affordances and authored ending; unchanged Dynamic evidence and action polling. |
| `web/src/test/fixtures.ts`, `web/src/test/server.ts` | Closed public native/options fixtures and request-recording MSW handlers for authoritative responses/faults. |
| `PLANS.md`, `docs/run_protocol.md`, `docs/architecture.md`, `docs/public_client_contract.md`, `docs/narrative_provider.md` | Implemented versus proposed scope, public contract, actual composition, deterministic rendering limits and locatable evidence at implementation completion. |

Keep this plan frozen during implementation. No edit is currently required to
`sessionRecovery.ts`, S1-S5 domain/application algorithms, SQL repositories/UoWs,
ORM, migrations, config, dependency locks or the old Demo plan. Demo adds in-memory
representations of already-existing storage, not a new durable family. If an
unforeseen schema, new public contract or changed S1-S5 invariant becomes necessary,
stop for explicit reassessment; do not hide it in adapters. Mechanical inventory
extensions must name the dependency and verification owner before editing.

Execution-only regressions include existing `tests/unit/test_run_entry_api.py`,
`test_player_character_api.py`, `test_run_protocol_resolution.py`,
`test_run_protocol_prompt_context.py`, `test_run_protocol_mechanics.py`,
`test_native_turn_mechanics.py`, `test_native_run_admission.py`,
`test_run_protocol_binding.py`, `test_run_protocol_binding_persistence.py`,
`test_narrative_provider.py`, `test_dynamic_narrative.py`, `test_demo_scripts.py`,
`test_deterministic_demo_provider.py`; `tests/e2e/test_demo_cross_process_replay.py`;
`tests/integration/test_mysql_native_run_admission.py`,
`test_mysql_native_turn_mechanics.py`, `test_mysql_run_entry_playthrough.py`,
`test_mysql_player_character_run_binding.py`, `test_mysql_session_api_persistence.py`;
and `web/src/sessionRecovery.test.ts`, `web/vite.config.test.ts`.
They are not automatically edit paths. Relevant shared test adapters inside the
listed edit tests must implement genuine native evidence, never return a mocked
legacy result to avoid the new View checks.

## 8. Executable acceptance and delivery order

| Acceptance boundary / owner | Required observable result |
| --- | --- |
| Public DTOs and OpenAPI / native API and public-client unit suites | Exact request/success/error allowlists and statuses, duplicate raw headers/JSON, 4,096 inclusive/4,097 rejection, wrong numeric types, extras/authority inputs, response cross-binding and sanitized failures. Assert zero application calls on transport failure, one real admission call on accepted request. Compare old route schemas/operation IDs/status sets with baseline; only optional native View extension is added. |
| Discovery/choices / public projection and Web setup tests | Exact three profiles/defaults/rules/order, one world/version and existing title/hook; no implicit selection. Each profile's inclusive range endpoints, off-step/outside rejection, empty/explicit-base overrides, duplicate parameter rejection and compatible combinations through S2. Changed presentation preserves five values. Unavailable composition is explicit; corrupt catalogue fails, never silently empties. |
| Ownership/disclosure / API, View and MySQL tests | Owned current character only; missing/foreign/controller-unavailable are non-enumerating. Cross-player Session returns same 404. Same player with changed controller cannot obtain native context. Corrupted receipt/protocol/world/immutable reference/reverse evidence produces safe failure and zero repair. Canary scans cover nested strings, errors, options, admission, active/ended View and request-status. |
| Public production loop / new real-MySQL API suite | Configure normal `build_default_services` with authorized fixture principal and fake Provider, then create/select character, GET options, POST native, GET View, submit every action via public routes using current affordances, reload through a fresh service instance, replay and reach an authored ending for each default profile. Follow the canonical route while ACTIVE; RESOLVED or authored deadline FAILED is a valid observed ending, never force success by bypassing policy. Assert final public status, completed scenario memory, stored snapshot/response/events and unchanged Run revision 3/character/protocol/world bytes. |
| Admission durability / same MySQL suite plus S4 regressions | Same key/body after progress returns exact admission body and no second write/ID/clock/Provider use; changed explicit override presence conflicts; same key in another family cannot replay native. Concurrent duplicate has one full winner, different-key occupancy has one admitted character binding. Inject failure/cancel at protocol/world staging and commit acknowledgement, verify all-or-none family and exact explicit recovery. Restore all fixtures. |
| S5 integration / new API suite plus unchanged native-turn suite | Public Easier charge 0, exhausted composure with positive nominal charge, positive depletion control: respectively zero/zero/one consume_resource calls and spend events; all continue legitimate Director effects. Paired TALK/discovery/adverse/CONTINUE cases show approved additive policies. Existing combined-order, saturation, stale-finalize, adversarial output, 27-presentations, compiler goldens and no-compile-under-lock evidence remains required at its appropriate owner, not duplicated exhaustively through every UI. |
| Transaction separation / real-MySQL S5 regression and View tests | Existing independent connection acquires Session row/named lock during compiler, PromptBuilder and fake Provider; mock counters cannot replace this. New View/discovery invoke neither compiler nor Provider, no locks/commits/writes. Admission still exits pinned native UoW before HTTP success. |
| Native Demo adapters / persistence/composition/native guard tests | Shared reconstruction rejects independently corrupted receipt input bytes and fingerprint, missing/orphan map, crossed world/character and original snapshot anomalies. Staged protocol/world/receipts/Session either all publish or none on failure/cancel/CAS conflict. Nested/inherited guard attempts execute zero protected work; cancellation consumes allowance, valid later transaction works, replay/resume does not render twice. Ordinary valid actions outside the legacy script work. |
| Demo parity/determinism / native E2E and existing legacy cross-process suite | Public selection/admission/play/reload/ending for each default, plus valid override/presentation variation. Equal fixed inputs/seeds/generators produce exact native public responses and detached final store across fresh processes/hash seeds. Compare semantic native deltas with production; preserve legacy golden trace unchanged. External DB/Provider/network constructors are raising sentinels with zero calls. Restart empties native maps and old View is 404 before any new entry. |
| Web contracts/state/UI / client/setup/App suites | Disabled until explicit selections; safe integer/lattice/label rejection; exact pre-POST string/key retained; double click one send; uncertain retry body/header byte equality; tainted subsequent errors retain pair; mode/catalog/character edits blocked; stale or old-client completion cannot write storage. Authoritative success stores identity before View and before pair clear; failed storage makes no GET/POST, explicit storage retry uses retained response. |
| Web recovery/endings / recovery/action-loop suites | GET-only reload and confirmed-202 status recovery, no mutation replacement after View failure/backend restart; schema/identity failure pauses; missing later native context rejects; explicit clear has no server effect. View resources and ending are server data; all actions disable when ended. Preserve legacy and Dynamic suggestions/count recovery and storage schema. |

Implement the narrow vertical dependency chain first: public projection/DTOs and
native POST -> production public integration through View/play/ending -> Demo
atomic adapters/native rendering -> Web selection/storage/recovery -> synchronized
docs. Run focused tests at each boundary. Do not finish isolated option widgets
while the actual admission/play/recovery path is disconnected.

At stable code, canonical `.\scripts\verify.ps1 -Mode Offline` and the relevant
`.\scripts\verify.ps1 -Mode MySQL` acceptance are mandatory for this shared public,
transactional-adapter and playable milestone. Use `.\.venv\Scripts\python.exe`
for all Python commands, `-m pytest` for focused tests, and
`-m compileall -q src tests alembic` when due through verification. Run dependency
checks and Alembic heads/history metadata checks, with no new migration or
unrequested upgrade/downgrade fault matrix. MySQL 8/asyncmy tests require separate
implementation authorization and safe identity preflight for
`deviation_protocol_test`; no URL/secret output or production database. Fake
Providers only; Live disabled. Use existing authorized runner options/selections
and report exact executed/skipped/deselected nodes, not reconstructed pass counts.

Web stable acceptance: from `web`, `npm run test:run`, `npm run typecheck`,
`npm run lint`, `npm run build`, using installed locked dependencies. Include
rendered MSW tests and in-process ASGI integration as mandatory automated evidence.
Any additional comprehensive runner is chosen by the workflow's actual affected
scope; no automatic duplicate Full run after the same acceptance or prose edits.

Create an external implementation evidence directory before verification, retain
commands, raw logs, exit codes, source/dependency/environment identities, fixture
restoration and selection reasons. Preserve the S5 bundle at
`C:\Users\DYLANM~1\AppData\Local\Temp\deviation-protocol-s5-implementation-20260917-1318b56094c540e4a491d05698b3db37`
and its `s2-reuse-applicability.json`, which points to the original
`C:\Users\dylanmonster\AppData\Local\Temp\s3-implementation-20260916-audit\correction`
evidence. Before reusing S2, inspect actual original logs/counter plugin, source
and test hashes, dependencies (including Python/Pydantic), environment, command,
exit and 5,624,910-call counters. If still applicable, deselect only
`tests/unit/test_run_protocol_resolution.py::test_complete_direct_exhaustive_public_resolution_domain`
and execute all other S2 tests. Otherwise execute the exhaustive node. A summary
or missing bundle is insufficient. Reuse unchanged migration proof only with the
same locatable/applicability discipline and explicit node/file exclusions; changes
to writer/lock behavior would require reassessment and relevant fresh MySQL proof.
Apply only DF-001's documented process-local containment and restore settings.

Browser evidence is **not authorized by this plan or the planning task**. After
separate explicit authorization, the bounded walkthrough would use the local
deterministic Demo, sanitized environment, installed Web dependencies and a fresh
tab: create/select -> choose profile/world -> confirm an override/presentation ->
enter -> play -> reload/GET recovery -> authored ending; then one controlled
backend-restart recovery check and explicit clear. Capture only safe visible UI
and request method/status evidence. No production credentials, Live, deployment
or public exposure. If authorization is absent, report browser evidence omitted;
automated contract evidence still remains mandatory. This is not an extra plan
approval stage and does not grant wider-release readiness.

## 9. Lifecycle, scope and handoff

The planning candidate contains this new plan plus `PLANS.md`,
`docs/run_protocol.md`, `docs/architecture.md`, `docs/public_client_contract.md`
and one bounded status correction in `docs/narrative_provider.md`. The last owns
the implemented S5 compiler/Provider boundary and still describes S5 review as
pending at baseline; its update changes publication status only. The public-client
document owns the proposed public extension and distinguishes it from implemented
Phase 8 contracts. Current S5 statements synchronize to approved publication at
`86c258e9ad2e64199cabf8650bf6f3a7b5f04d87`; historical reviews/evidence and frozen
plans remain intact. There is no separate S5 closeout task.

DF-001 remains deferred with its existing owner, containment and reassessment
milestone. No new eligible confirmed finding was identified while planning.
Required authority, corruption, playable/recovery and essential-evidence failures
cannot be deferred. S6 does not implement new worlds, visits, progression, Run
completion/detachment, production authentication/Provider distribution, story
content or Phase 3.4 relationship/residence state. Trial/release readiness needs
its own evidence and the post-playable stabilization checkpoint.

Exactly one operative plan-review success token is:

`PHASE_3_3_S6_PUBLIC_API_DEMO_WEB_PROJECTION_RECOVERY_PLAN_INDEPENDENT_REVIEW_APPROVED`

Both `APPROVED` and `APPROVED_WITH_DEFERRED_FINDINGS` dispositions use that same
token and bind the complete candidate/manifest with all technical requirements.
Exactly one dormant implementation-review token is:

`PHASE_3_3_S6_PUBLIC_API_DEMO_WEB_PROJECTION_RECOVERY_IMPLEMENTATION_INDEPENDENT_REVIEW_APPROVED`

It becomes operative only after plan approval, separately authorized exact local
documentation commit, user publication, clean baseline confirmation and separately
authorized implementation. Both future successful dispositions use that same
implementation token. Neither token authorizes implementation or Git writes;
companion documents link here rather than duplicating token literals. No extra
approval stage. Next action is one substantive independent plan review.

After final edits, freeze externally: baseline/ref/parent/status, exact paths,
per-file byte/line/SHA-256/mode, binary/full-index per-path patches and identities,
and lexicographically concatenated complete patch bytes/SHA-256 and insertion/
deletion counts. Include new files through `/dev/null`, not tracked diff alone.
Any byte change invalidates prior identity/approval; relevant baseline drift
requires reassessment under the workflow. Planning checks are document scope,
references/status, complete diff, whitespace, strict UTF-8/LF/final newline,
protected identities and Git state only. No project tests, compileall, application,
database, Alembic, browser, Provider or network runs are part of this task.

## Guardrail impact

None. Apply existing AUTH-001/002, API-001, DB-001/002, MODEL-001/002,
STATE-001, SCENE-001, PLAY-001 and environment/Git rules. Technical guardrails,
workflow, published plans, source, tests, configuration and migrations stay unchanged.
