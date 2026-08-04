# Structured Player Character P8-S5 Minimum Web Connection Implementation Plan

Status: **Frozen implementation-plan candidate  independently unreviewed; implementation not authorized**

Slice identity: `STRUCTURED_PLAYER_CHARACTER_P8_S5_MINIMUM_WEB_CONNECTION`

Planning-task identity:
`STRUCTURED_PLAYER_CHARACTER_P8_S5_PLANNING_AND_AUTHORITY_RECONCILIATION`

Baseline commit: `60938260b3e63fffbe849a9a6de8863b7f429897`

Baseline subject: `docs(player-character): synchronize P8-S4 completion`

Required implementation base: the published, clean, aligned `main` baseline
above, or a later baseline that has passed the repository's pending-plan
baseline-invalidation assessment without making any fact in this plan stale.

This file is the sole planning artifact authorized by the planning task. It is
not an approval, publication record, implementation change, test change, or
authority/status synchronization. P8-S5 implementation remains prohibited
until the exact candidate is independently approved, separately committed and
published by the established workflow, its clean published baseline is
confirmed, and a separate implementation task is authorized. P8-S6 remains
unstarted.

## 1. Purpose and minimum user-visible outcome

P8-S5 connects the existing React/Vite Web client to capabilities already
implemented through P8-S4. It does not add server behavior. A user in the
current Web page can:

1. load the bounded server-owned collection of Player Characters eligible for
   Run entry;
2. observe an empty collection and create one minimal Player Character through
   the existing creation route, or select one returned eligible projection;
3. select one existing public scenario;
4. submit one idempotent Run-entry attempt using the selected projection's
   exact opaque identity and revision;
5. store the returned `session_id` through the existing same-tab recovery
   helper before discarding successful Run-entry retry evidence;
6. read the complete authoritative Session View; and
7. continue through the unchanged action, request-status, stale/uncertain,
   refresh, recovery, clear, and terminal-View behavior.

The page provides a minimum connection, not a profile editor or Web redesign.
The browser renders server projections and public errors. It never decides
ownership, current eligibility, character lifecycle, Run lifecycle, binding,
scenario settlement, action availability, or recovery success.

## 2. Planning baseline and authority fingerprints

Planning began only after these Git facts were verified:

| Fact | Verified value |
| --- | --- |
| Repository | `D:\deviation-protocol` |
| Branch | `main` |
| `HEAD` | `60938260b3e63fffbe849a9a6de8863b7f429897` |
| Local `main` | `60938260b3e63fffbe849a9a6de8863b7f429897` |
| Local `origin/main` | `60938260b3e63fffbe849a9a6de8863b7f429897` |
| Ahead/behind | `0/0` |
| Subject | `docs(player-character): synchronize P8-S4 completion` |
| Sole parent | `187d41ba3035c8d717c2fb2578a805402255d979` |
| Initial tracked/index/untracked state | Clean/clean/empty |
| Active Git operation | None |
| Live remote contact | None |

The published authority identities used for this plan are:

| Path | Raw bytes | SHA-256 |
| --- | ---: | --- |
| `PLANS.md` | 50,430 | `26a070e6e2bcc3a48b64271dd18be5c5634ac43a512f8d780e4e5b33caa86241` |
| `docs/architecture.md` | 101,306 | `d476d4be3ffd7ebbf24a7427daca22a49b1220020121cf290d097878d6925d87` |
| `docs/public_client_contract.md` | 75,404 | `bbcece6a2f5d03cc62fb87ca4f058e7abb096c87274fa57508a29c5082c55118` |
| `docs/run_protocol.md` | 26,835 | `e5d92bf3dc2baf135103adccce41af7e8a39e12995ded470cff6abe611da6b32` |
| `docs/structured_player_character_contract.md` | 72,930 | `2bafc637404f3bd8462996ac08ff3bd8a391f25c1792ba5f0c6cda1d47e7b07f` |
| `docs/structured_player_character_implementation_plan.md` | 303,180 | `1b8394f5d0cd750d05e91724bb052f666978455ce9e8e1ae610a105216630465` |
| `docs/structured_player_character_run_playable_loop_plan.md` | 90,601 | `9ee7f3d0181b22edbe0716ae1ce4cec1fa7b875301f83ec19962ec84f48fae0c` |

The completed frozen P8-S4 plan was also verified at 1,633 lines, 91,615 raw
bytes, and SHA-256
`8a26eb4d5e3517db76c69f3c4415738b8565a163f3fdd4468fb7bb1181a21b6f`:
`docs/structured_player_character_p8_s4_implementation_plan.md`.

Any relevant baseline or authority-byte change invalidates this candidate's
review binding. Reconciliation and a fresh exact-byte review are then required.

## 3. Applicable repository instructions

The only repository-local instruction file found is root `AGENTS.md`; no
narrower instruction file governs `docs/`, `web/`, `src/`, or `tests/`.
Applicable rules are:

- use PowerShell 7+ and explicit `\.venv\Scripts\python.exe` for repository
  Python commands;
- do not read or print `.env` secrets and keep live Provider calls disabled;
- preserve server authority, dependency direction, MySQL-only production
  persistence, and tests for every state mutation;
- follow pending-plan invalidation, approval-token consistency, canonical
  documentation synchronization, verification, and Git handoff rules in
  `docs/engineering/codex_workflow.md`;
- read `PLANS.md` before planning the next phase;
- do not stage or commit without exact separate authorization, and never push;
  and
- report Guardrail impact.

`docs/engineering/guardrails.md` was inspected for the applicable authority,
public-projection, uncertainty, Provider, persistence, playability, and
toolchain rules. No confirmed defect was established by this planning task, so
the expected Guardrail impact of the planned implementation is `None`. A later
confirmed defect that creates or changes a reusable rule is a stop condition
for this exact path budget and requires plan reassessment before a guardrail
edit.

## 4. Authority inventory and precedence

Authority is divided by subject; no inspected document is treated as a general
override of a narrower owner.

| Precedence | Authority | Role in P8-S5 |
| ---: | --- | --- |
| 1 | `docs/public_client_contract.md`, especially lines 61-357 and 864-1131 | Normative public wire, DTO, error, replay, privacy, client, and recovery contract for creation, discovery, Run entry, Session View, and logical mutation attempts |
| 2 | `docs/structured_player_character_run_playable_loop_plan.md`, especially lines 139-180, 242-536, 694-820, 834-857, 1235-1299, 1334, 1351-1354, and 1407-1415 | Current published Phase 8 allocation, exact P8-S5 purpose, maximum predecessor budgets, recovery rules, evidence, and separation from P8-S6 |
| 3 | `docs/architecture.md`, especially lines 540-625 and 760-820 | Architectural ownership, service/composition facts, Web boundary, and existing same-tab Session recovery contract |
| 4 | `docs/structured_player_character_contract.md`, especially lines 765-783 and 852-923 | Normative character identity, lifecycle, ownership, privacy, binding, and downstream-status constraints |
| 5 | `docs/run_protocol.md`, especially lines 111-240 | Normative narrow Session-backed admission, continuing active Run, immutable binding, and no Run-resume/discovery expansion |
| 6 | `PLANS.md`, especially its Phase 8 status and document-ownership sections | Roadmap status and the fact that P8-S5 is next while P8-S6, Phase 8, and the overall project remain incomplete |
| 7 | `docs/structured_player_character_implementation_plan.md`, especially lines 363-450 and 3780-3945 | Broader Structured Player Character implementation chronology and retained Phase 6/7 ownership |
| 8 | `docs/structured_player_character_p8_s4_implementation_plan.md`, especially lines 115-233 and 235-356 | Frozen slice-specific evidence that P8-S4 owns Demo parity and expressly excludes Web work |
| 9 | Current source and tests listed in section 5 | Implementation evidence only; proves what exists or is absent but cannot weaken published authority |

The explicit planning-task boundaries control this candidate's allowed write
set and workflow. They do not create a new product rule or expand P8-S5.
Historical commit messages and older phase statements are chronology and
descriptive evidence only. Dated statements that Demo lacked Player Character
or Run-entry services were true before P8-S4 and are not current normative
limits.

There is no material unresolved contradiction. The narrowest combined reading
is that P8-S5 changes only Web schemas, client calls, rendered pre-play controls,
and Web tests while reusing all backend and recovery authorities unchanged.

## 5. Verified current implementation state

### 5.1 Server and Demo capabilities already exist

Current `src/deviation_protocol/api/main.py` lines 969-1179 conditionally
register the exact routes needed by P8-S5:

- `GET /v1/player-characters/eligible-for-run-entry`;
- `POST /v1/player-characters`;
- `GET /v1/player-characters/{player_character_id}`, which remains public but
  is not required by this Web slice;
- `POST /v1/runs`; and
- the existing scenario, Session View, action, and request-status routes.

`POST /v1/sessions` remains a legacy compatibility route. It creates an
unbound Session and is not used by the new minimum Run-entry journey.

Current `src/deviation_protocol/api/demo_composition.py` lines 312 onward
construct one process-local Demo store and the existing Player Character,
Run, Run-entry, Session, and gameplay services with deterministic issuers and
the fixed Demo principal. P8-S4 published that parity without MySQL or
post-process durability. No server, Demo, DTO, route, dependency, configuration,
or persistence change is missing for the minimum P8-S5 journey.

### 5.2 Exact Web gaps

Current `web/src/api/schemas.ts` has scenario, legacy Session-create, View,
action, request-status, and error schemas. It has no runtime schema or inferred
type for:

- the minimal existing Player Character creation request;
- `PlayerCharacterSelfProjection`;
- `EligiblePlayerCharacterCollection`;
- the strict Run-entry request; or
- the Run-entry response.

Current `web/src/api/client.ts` exposes `listScenarios`, `createSession`,
`getSessionView`, `submitAction`, and `getNarrativeRequestStatus`. These exact
methods are absent:

1. `createPlayerCharacter(request, idempotencyKey, signal?)`;
2. `listEligiblePlayerCharacters(signal?)`; and
3. `enterRun(request, idempotencyKey, signal?)`.

Current `web/src/App.tsx` lines 515-985 load the scenario catalogue and use the
legacy `createSession` client method. It has no eligible-character collection,
selected Structured Player Character, create-character attempt, Run-entry
attempt, or manual same-pair retry state. Its scenario form still asks for a
static character definition that Run entry now selects server-side.

Current `web/src/sessionRecovery.ts` already supplies the exact strict
version-1 `sessionStorage` record, safe access/set/remove results, and
`writeSessionRecoveryRecord(sessionId, confirmedPendingClientRequestId?)`.
It can store a successful Run-entry `session_id` without modification. Its
record contains no Player Character, Run, View, body, idempotency key, or
pending Run-entry data.

Current `web/src/styles.css` already provides generic panel, form, fieldset,
select, button, status, alert, compact-list, focus, and narrow-screen rules.
The minimum controls fit those classes; no style change is required.

Current `web/src/test/server.ts` is a generic empty MSW server. Existing tests
register route handlers locally, so no central server change is required.

### 5.3 Existing tests that own the change

- `web/src/api/client.test.ts` owns wire calls, runtime response validation,
  error mapping, cancellation, and no-retry evidence.
- `web/src/App.test.tsx` owns discovery, pre-play controls, loading/empty/error,
  creation, selection, Run entry, View-read, duplicate-click, and existing
  manual Session-read behavior.
- `web/src/App.action-loop.test.tsx` owns the rendered canonical action journey
  and must begin its P8-S5 full-loop case through Player Character discovery or
  creation and `POST /v1/runs`, not legacy Session creation.
- `web/src/App.recovery.test.tsx` owns same-tab Session recovery, uncertainty,
  cancellation, late-response isolation, reload behavior, and the mandatory
  history-sensitive 404 regression.
- `web/src/test/fixtures.ts` owns typed reusable public fixtures.

`web/src/sessionRecovery.test.ts` remains unchanged because the helper and
record format remain unchanged. P8-S5 recovery integration belongs in
`App.recovery.test.tsx`.

### 5.4 Contract sufficiency decision

The existing public contract completes the minimum flow. No Run read/list or
Player Character binding query is needed to enter a new Run, and the existing
Session recovery record is sufficient after Run entry returns and its
`session_id` is stored. The absence of Run discovery means recovery before
that storage boundary is intentionally unsupported; it is a documented limit,
not a contract gap that P8-S5 may fill.

## 6. Slice ownership reconciliation

| Slice | Preserved ownership | P8-S5 treatment |
| --- | --- | --- |
| P8-S2 | Character revision/eligibility lock, Run revisions 1/2/3, binding, Session creation/participation, activation, replay, one UoW and commit | Consume only; do not reopen or duplicate in Web |
| P8-S3 | Normal public adapter, strict DTOs/errors/OpenAPI, composition, public Run-entry-to-terminal backend evidence | Consume only; no route, DTO, error, OpenAPI, composition, or MySQL edit |
| P8-S4 | Deterministic process-local Demo repositories, composition parity, rollback/lock parity, deterministic identities | Consume only; preserve temporary process-local behavior and no MySQL durability claim |
| P8-S5 | Minimum Web schemas/client calls, create-or-reuse/select/start controls, component-memory mutation recovery, Session-ID handoff, existing gameplay reuse | Exact scope of this plan |
| P8-S6 | Cross-surface evidence consolidation, final authority/status synchronization, complete Phase 8 review and closure | Remains unstarted and outside this plan |

P8-S5 does not absorb or reopen P8-S2, P8-S3, or P8-S4 merely because the Web
consumes their results. P8-S5 focused Web evidence is required for its own
implementation review; it is not P8-S6's complete cross-surface or final Phase
8 proof.

## 7. Exact public operations and DTO reuse

The Web calls only these existing operations:

| Order | Operation | Existing DTO/result reused | Web purpose |
| ---: | --- | --- | --- |
| 1 | `GET /v1/scenarios` | `PublicScenarioCatalog` | Select one currently public `scenario_id` |
| 2 | `GET /v1/player-characters/eligible-for-run-entry` | `EligiblePlayerCharacterCollection` of `PlayerCharacterSelfProjection` | Recover current server-listed active, unbound choices for the resolved controller |
| 3 | `POST /v1/player-characters` | Existing strict `CharacterCreationCommand` request and `PlayerCharacterSelfProjection` response | Empty-state creation using the smallest valid existing body |
| 4 | `POST /v1/runs` | Existing strict `RunEntryRequest` and `RunEntryResponse` | Start one server-authoritative Run/Session using selected projection identity/revision |
| 5 | `GET /v1/sessions/{session_id}/view` | Existing `PlayerSessionView` | Load complete authoritative gameplay state after entry or recovery |
| 6 | Existing action and request-status operations | Existing action/request/status/View DTOs | Continue the already implemented gameplay lifecycle |

The creation request is exactly the smallest valid body already defined by the
public contract:

```json
{
  "contract_version": "structured-player-character/v1",
  "character_core": {},
  "narration_preferences": {}
}
```

This is a bounded Web choice, not a new server DTO and not a default for
player-authored declarations. P8-S5 adds no profile or declaration editor.
The Web client accepts only this minimum body because it is the only body the
P8-S5 UI can construct. The server's complete existing creation contract
remains unchanged and available to other public clients.

The Run-entry body is exactly:

```json
{
  "player_character_id": "pc.example",
  "expected_record_revision": 1,
  "scenario_id": "death_certificate"
}
```

The three example values come respectively from the selected projection's
`player_character_id.value`, its `record_revision.value`, and the selected
public scenario's `scenario_id`. Web runtime validation rejects values
outside JavaScript's exact safe-integer range rather than round or alter a
public signed-64-bit revision. Such a response is contract-incompatible for
this Web client and cannot be submitted.

Both POSTs use one required `Idempotency-Key` matching the existing exact
1-through-128-character opaque ASCII grammar. The client adds no query value,
principal, controller, Run, line, Session, lifecycle, binding, applicable
reference, static character definition, View, state, receipt, fingerprint,
Provider, or recovery field.

The client methods perform exactly one fetch invocation per explicit call.
They retain the existing base-URL, `Accept`, JSON content-type, public
`ErrorResponse`, cancellation, response-status, and Zod-validation behavior.
They contain no automatic retry.

## 8. Browser-visible pre-play state

The existing scenario and manual Session-read sections remain. The former
legacy Session-create controls are replaced by this minimum pre-play state:

1. **Scenario discovery:** independent loading, success, empty, recoverable
   failure, or terminal contract-failure presentation for `GET /v1/scenarios`.
2. **Eligible-character discovery:** independent loading, success, empty,
   recoverable failure, or terminal contract-failure presentation for the
   eligible collection.
3. **Eligible selection:** when items exist, a compact selector uses the exact
   server order and displays only public opaque ID, contract version, revision,
   and lifecycle. The first returned item is initially selected.
4. **Truncation:** `truncated=true` displays an explicit notice that only the
   bounded first 32 eligible projections are shown and no count or pagination
   is available. It is not presented as an account limit.
5. **Empty creation:** only an authoritative empty eligible response exposes
   the minimum create control. The created projection becomes the selected
   entry candidate for the current page. The UI labels it as a server-returned
   creation result that will be revalidated on entry; it does not claim the
   response is a fresh-current-state guarantee after replay.
6. **Run start:** enabled only when one candidate and one public scenario are
   selected, no Session recovery/storage lock is active, no foreground
   operation exists, and no unresolved mutation attempt blocks a new body.
7. **Mutation recovery:** an uncertainty-tainted creation or Run-entry attempt
   displays the sanitized failure, states that server durability is unknown,
   disables controls that could change its body, and exposes one explicit
   manual retry button for the retained exact attempt.
8. **Session handoff:** after successful entry and Session-record persistence,
   the existing Session confirmation, View, action controls, stale warnings,
   recovery warnings, explicit View retry, and terminal presentation take over.

No new CSS class is required. Existing `panel`, form/fieldset controls,
`operation-status`, `stale-warning`, `compact-list`, `supporting-copy`, and
`role="status"`/`role="alert"` presentation are reused.

## 9. Client mutation-attempt model

`App.tsx` owns one component-memory-only discriminated union for unresolved
logical mutations:

```text
none
  | player-character-create {
      idempotencyKey,
      exactFrozenBody,
      uncertaintyTainted,
      inFlight
    }
  | run-entry {
      idempotencyKey,
      exactFrozenBody,
      uncertaintyTainted,
      inFlight
    }
```

The exact implementation may use TypeScript `Readonly` types, a ref for
synchronous duplicate protection, and React state for rendering, but it must
preserve these semantics:

1. generate and validate the key and construct/validate the body before the
   first POST;
2. install the exact pair synchronously before invoking the client method;
3. never mutate or reconstruct the retained body from current UI selection;
4. permit at most one in-flight send for the pair;
5. block every new mutation and every selection change that could produce a
   different body while the pair is unresolved;
6. expose no background, effect-driven, timer-driven, mount-driven, or render-
   driven retry;
7. manual retry calls the same client method with the same retained key and
   semantically identical frozen DTO;
8. hide the opaque key from the page and never log it; and
9. clear or retain the pair only according to section 10.

`AppProps` gains a deterministic `idempotencyKeyFactory` test seam whose
production default is `crypto.randomUUID()`. Existing action identity creation
remains separate. The legacy `requestIdFactory` used only for direct Session
creation is removed from `AppProps` because the P8-S5 page no longer issues
legacy Session-create requests. `PublicApiClient.createSession` and its schema
remain unchanged for compatibility and existing direct client coverage.

## 10. Exact mutation result classification

### 10.1 Definitive creation results

| Result for retained creation pair | Browser decision |
| --- | --- |
| Valid HTTP 200 `PlayerCharacterSelfProjection` | Clear the attempt; select the returned projection; do not persist it; do not infer later eligibility |
| Direct, contract-matching 404 `PLAYER_CHARACTER_NOT_FOUND` before any uncertain send | Clear the attempt; show the public error; keep the authoritative empty/list state |
| Contract-matching 409 `IDEMPOTENCY_CONFLICT` | Clear the attempt; show the public error; permit a later new logical attempt only after the old attempt is resolved |
| Contract-matching 422 `REQUEST_VALIDATION_FAILED` | Clear the attempt; show the public error; no request/body salvage |

### 10.2 Definitive Run-entry results

| Result for retained entry pair | Browser decision |
| --- | --- |
| Valid HTTP 200 `RunEntryResponse` with scenario, character ID, and revision equal to the frozen request | Write the returned `session_id` through `writeSessionRecoveryRecord`; only after a successful write clear the entry attempt; then GET the authoritative View |
| Direct, contract-matching 404 `PLAYER_CHARACTER_NOT_FOUND` before any uncertain send | Clear the attempt; invalidate the selected candidate; show the public non-enumerating error and one explicit safe eligible-GET refresh control |
| Contract-matching 409 `IDEMPOTENCY_CONFLICT` | Clear the attempt; show the public error; do not replace the key inside the resolved attempt |
| Contract-matching 409 `PLAYER_CHARACTER_STALE`, `PLAYER_CHARACTER_NOT_ELIGIBLE`, or `RUN_ENTRY_CONFLICT` | Clear the attempt; invalidate the selected candidate; show the public error and one explicit safe eligible-GET refresh control; make no client-side lifecycle or binding claim |
| Contract-matching 422 `REQUEST_VALIDATION_FAILED` or `INVALID_SCENARIO_DEFINITION` | Clear the attempt; show the public error and one explicit safe control for the relevant catalogue GET; require a valid refreshed selection before another logical attempt |

The safe catalogue refresh controls above are user-triggered GETs. They never
resend a mutation and never run in the background. A valid response replaces
local selectable projections with the returned server collection.

### 10.3 Uncertain results for either mutation

These outcomes taint and retain the exact pair because the browser cannot know
whether the POST committed:

- transport loss or timeout;
- response loss;
- abort or cancellation after the POST may have begun;
- a safe HTTP 500 envelope, including `INTERNAL_SERVER_ERROR`;
- malformed, empty, non-JSON, schema-incompatible, identity-incompatible, or
  unexpected-status response;
- an unrecognized public status/code combination; or
- any other exception that cannot prove no send occurred.

The UI performs no automatic retry. It offers only explicit same-key/same-body
manual retry. A valid 200 resolves the attempt. A contract-matching 409 or 422
resolves it according to the tables above.

A later 404 after any uncertainty-tainted send is history-sensitive. Even when
its envelope is the operation's documented 404, it does not prove the earlier
send failed to commit. The client:

- retains the exact key/body pair;
- retains `uncertaintyTainted=true`;
- generates no replacement key;
- attaches no different body;
- performs no automatic retry;
- does not select a different character/scenario for that attempt; and
- permits only another explicit retry of the same pair.

A local request-schema or key-schema failure detected before fetch is a
terminal no-send client construction failure. It creates no retained sent
attempt and exposes no raw invalid value.

### 10.4 Session-storage failure after entry success

A valid Run-entry 200 resolves server operation uncertainty, but the retained
entry pair is not cleared until `writeSessionRecoveryRecord` succeeds. When
storage write fails:

- enter the existing fail-closed storage state;
- retain the exact entry pair in component memory;
- render no gameplay controls;
- accept no new mutation;
- disclose no key or raw storage exception; and
- after the existing explicit safe storage-clear recovery succeeds, allow a
  manual same-pair Run-entry replay so the same `session_id` can be stored.

No alternative Web storage or Run-discovery call is introduced.

### 10.5 View failure after successful storage

After the Session record is stored, the Run-entry attempt is resolved and
cleared. A failed initial View GET does not resend Run entry and does not undo
the server Run, binding, Session, participation, activation, or receipt. The
page retains the Session recovery record and exposes only an explicit safe View
GET retry. Reload performs the existing Session recovery GET path with zero
Run-entry or action POSTs.

## 11. Recovery state model

| Situation | Authoritative operation | Local decision and user affordance |
| --- | --- | --- |
| Initial or explicit eligible refresh | `GET /v1/player-characters/eligible-for-run-entry` | Replace selectable collection only after valid response; manual GET retry on recoverable failure |
| Local selected projection differs from server eligibility | `POST /v1/runs` revalidation, followed by eligible GET after definitive stale/missing/ineligible conflict | Server result wins; invalidate selection; never patch lifecycle locally |
| Missing or foreign Player Character | Existing non-enumerating entry 404 | Direct untainted 404 resolves attempt; tainted 404 retains attempt; no existence/owner inference |
| Retired, deceased, bound, or exhausted Player Character | Eligible GET omission or entry 409 `PLAYER_CHARACTER_NOT_ELIGIBLE` | Remove through refreshed server collection; never reveal which internal reason applied |
| Stale revision | Entry 409 `PLAYER_CHARACTER_STALE` | Resolve attempt, refresh eligible collection, require user to select the returned current projection |
| No eligible character | Authoritative empty eligible response | Show empty state and bounded minimum create control |
| No active Session recovery record | No automatic Run operation | Show pre-play discovery; absence is not proof that no Run exists |
| Valid Session recovery record | Existing View GET, or request-status GET when the record has a confirmed pending action | Preserve current Phase 3.1c behavior; no start/action replay |
| Recovery endpoint 404 | Existing Session recovery rule | Clear invalid Session record and return to pre-play UI; this does not mutate a Run or character |
| Existing active Run but no retained Session ID | No public operation exists | State honestly that this Web client cannot discover or resume that Run; do not invent a Run/receipt query |
| Demo process restart | Existing reads return missing state from the fresh process | Stored Session 404 clears under existing recovery; eligible collection reflects fresh process; pending tainted 404 remains unresolved while its component memory survives |

The only supported Run resume is recovery or explicit manual read of the known
Session ID through existing Session endpoints. P8-S5 does not recover by
Player Character ID or Run ID.

## 12. Reload, navigation, duplicate action, and cancellation decisions

### Reload and browser contexts

- Reload after successful Session-record storage restores through the existing
  Session View/request-status GET logic. It sends no Run-entry or action POST.
- Reload before an authoritative creation response loses the creation attempt.
  It does not recover, retry, or discover the operation receipt.
- Reload after Run-entry POST but before response validation and Session-record
  storage loses the entry attempt. It sends no automatic replacement POST and
  may be unable to discover a committed active Run.
- Browser close, component unmount, cross-tab, cross-browser, cross-device, and
  multi-device pending-mutation recovery remain unsupported.
- Back/forward navigation carries no Player Character, Run, Session, body, or
  key in the URL. A navigation that unloads the component has the same bounded
  loss behavior as reload. A navigation that preserves the mounted component
  preserves only its in-memory attempt.

### Duplicate controls

- Install the attempt ref before starting fetch so two same-turn submissions
  produce one POST and one key.
- While a POST is in flight, disable create, start, manual Session switching,
  selector changes, and the retry button.
- While an uncertain attempt is retained but not in flight, disable every new
  mutation and body-changing selector; enable only its exact retry.
- Existing action controls remain protected by the existing foreground lock,
  action identity, Session state, and stale-state rules.

### Cancellation and late responses

- P8-S5 adds no new cancel control for mutation POSTs.
- Component unmount and client replacement abort active fetches through the
  existing `AbortController`/operation-generation pattern.
- An abort after a POST may have begun is uncertainty-tainted before any later
  same-page user action can create a replacement attempt.
- A late response from an aborted or superseded operation cannot write
  `sessionStorage`, clear an attempt, select a projection, commit a View, or
  release a newer foreground lock.
- Unmount necessarily loses component-memory retry evidence; this limitation
  is displayed or documented and is not represented as server rollback.

There is no streaming response in the P8-S5 create/discovery/entry flow. There
is no client generator, post-issuance rollback, compensation, or background
worker. Existing action 200/202 polling, Provider uncertainty, and terminal
View behavior remain unchanged; P8-S5 reaches them only after the authoritative
Session View has loaded.

## 13. Data authority, privacy, and storage rules

1. Server projections and responses remain the only authority for character
   identity/revision/lifecycle, eligibility, scenario catalogue, Run entry,
   Session identity, View, affordances, request status, and settlement.
2. A selector value is intent, not a capability. Run entry revalidates it.
3. `sessionStorage` remains limited to the existing versioned Session recovery
   record: `session_id` and an optional server-confirmed pending action
   `client_request_id`.
4. Creation and Run-entry key/body pairs exist only in current component/process
   memory while unresolved. They are not written to `sessionStorage`,
   `localStorage`, IndexedDB, cookies, cache storage, URL/query/hash state, or a
   service worker.
5. No Player Character, Run, projection, View, action payload, player input,
   response body, public error, or retry history is added to browser storage.
6. The UI does not display idempotency keys, raw response bodies, stack traces,
   storage exceptions, internal identifiers, authority sources, receipts,
   fingerprints, Provider data, SQL, or controller bindings.
7. Runtime response schemas expose only existing allowlisted public fields and
   discard harmless additive response fields in the same manner as the current
   client. Strict request schemas reject extra client fields.
8. Public errors are rendered through the existing `ApiClientError` and
   `formatApiClientError` boundary; private details are never synthesized.
9. Explicitly clearing the Session record is client-only. It does not end a
   Run, release a binding, retire/delete a Player Character, or delete server
   data.

## 14. Loading, success, empty, recoverable, and terminal states

| State class | Exact examples | Controls |
| --- | --- | --- |
| Loading | Scenario GET, eligible GET, create send, entry send, Session recovery/View GET, existing action/status polling | Disable controls whose data or single-flight authority is incomplete |
| Success | Valid catalog/eligible response, creation projection, stored entry Session ID, authoritative View, terminal View | Render only returned public fields; enable only controls valid for that state |
| Empty | Empty scenario catalogue; empty eligible collection | No Run start without scenario; empty eligible state exposes minimum create only when scenarios are usable |
| Recoverable failure | Safe GET network/500 failure; uncertain mutation with retained pair; View GET failure after stored Session | Explicit safe GET retry or exact manual same-pair POST retry; never automatic mutation retry |
| Terminal failure for one attempt | Direct contract-matching untainted 404/409/422; pre-fetch local schema failure | Clear resolved attempt where section 10 permits; show sanitized error; require refreshed selection or a new user-triggered logical attempt |
| Fail-closed client state | Contract-incompatible response; unavailable/failed `sessionStorage`; identity mismatch in existing recovery | Hide/disable authoritative controls; use existing safe clear or GET recovery only |

An `ENDED` Session View is a successful terminal scenario presentation, not a
Run terminal transition. The Run remains active and bound.

## 15. Existing behavior preserved byte-for-contract

The implementation must preserve:

- the public legacy `POST /v1/sessions` route as unbound compatibility behavior;
- `PublicApiClient.createSession` and `createSessionRequestSchema`, although the
  main P8-S5 App journey no longer invokes them;
- manual Session-ID View reads;
- the exact version-1 Session recovery record and helper implementation;
- same-tab startup recovery, confirmed-202 request-status recovery, stale View,
  outcome-unknown, explicit safe GET, and clear behavior;
- action generation, action submission, no automatic action retry, polling,
  cancellation, affordance rendering, and terminal View presentation;
- the deterministic Demo warning and mode isolation;
- backend routes, DTOs, error codes/messages, OpenAPI, authority, services,
  composition, transactions, repositories, schema, and migrations;
- P8-S4 process-local Demo loss after process exit; and
- scenario catalogue/default static character-definition authority on the
  server. The Web no longer submits that definition during Run entry.

## 16. Explicit non-goals

P8-S5 adds none of the following:

- a route, DTO, public error, public status, server command, lifecycle state,
  OpenAPI change, or adapter/composition change;
- Player Character profile/declaration editing, retirement control, general
  list/search/filter/sort/page/count/admin UI, owned-ID lookup, or local
  lifecycle editing;
- Run read/list/resume/discovery/rebind/attach/complete/terminate/exit/delete
  behavior, later Session/scenario entry, or binding release;
- binding or ownership inference from a browser cache, selector, URL, response
  absence, or local variable;
- optimistic eligibility, optimistic Run binding, optimistic Session View, or
  action authority outside server affordances;
- pending-operation `sessionStorage`, `localStorage`, IndexedDB, URL state,
  service worker, background retry, automatic retry, cross-tab coordination,
  or cross-device recovery;
- ORM, migration, schema, MySQL adapter, transaction, receipt, UoW, dependency,
  configuration, scenario, content, generated evidence, or build-artifact
  change;
- live Provider, Provider selection, streaming, deployment, production
  authentication, CORS, release, Internet activation, or production durability;
- a claim that deterministic Demo data survives server restart;
- full Run Protocol/world/profile/progression, Run termination, later-world
  movement, NPC/memory/relationship/combat/inventory integration, or Phase 6/7
  work;
- P8-S6 cross-surface evidence, final status synchronization, or Phase 8
  closure; or
- a broad visual system, routing framework, state-management library, or Web
  architecture redesign.

## 17. Exact production implementation path budget

**Production implementation budget: exactly 3 existing paths.**

| Path | Exact responsibility |
| --- | --- |
| `web/src/api/schemas.ts` | Add the bounded minimum creation request, opaque idempotency key, Player Character projection, eligible collection, Run-entry request/response runtime schemas and inferred types; enforce required fields, bounds, closed values, collection cap/order, safe integer handling, and response relationships without changing existing schemas |
| `web/src/api/client.ts` | Add exactly `createPlayerCharacter`, `listEligiblePlayerCharacters`, and `enterRun`; validate keys/bodies, send exact methods/paths/headers/bodies once per call, validate 200 responses and Run-entry response/request identities, and reuse existing errors/cancellation with no retry |
| `web/src/App.tsx` | Replace the primary legacy Session-create form with the minimum create-or-reuse/select/start flow; own component-memory mutation pairs and exact classification; hand successful entry to existing Session recovery/View/action behavior; preserve manual Session reads and existing gameplay |

No fourth production path is admitted. In particular:

- `web/src/styles.css` remains byte-unchanged because existing generic styles
  cover the controls;
- `web/src/sessionRecovery.ts` remains byte-unchanged because its existing
  write/read/clear contract is sufficient;
- `web/src/api/errors.ts` remains byte-unchanged because current error kinds,
  status, code, reason, identity mismatch, and formatting support the exact
  classification;
- `web/package.json`, `web/package-lock.json`, Vite/TypeScript/ESLint
  configuration, and all backend paths remain byte-unchanged.

Proof that a fourth production file is required stops implementation and
returns for plan reassessment. It is not permission to expand the budget.

## 18. Exact test path budget

**Test budget: exactly 5 existing paths.**

| Path | Exact responsibility |
| --- | --- |
| `web/src/api/client.test.ts` | Runtime-schema positive/negative matrices; exact create/eligible/entry method, URL, headers, body, statuses, request/response identity, public error, abort, response-loss, and one-fetch/no-retry assertions |
| `web/src/App.test.tsx` | Scenario plus eligible loading/success/empty/failure; multi-item selection; truncation notice; minimum empty-state creation; start success; storage-before-View ordering; direct definitive errors; duplicate-click locks; manual Session-read and mode-warning preservation |
| `web/src/App.action-loop.test.tsx` | Change the canonical rendered 19-action journey to begin with empty/reuse Player Character discovery, minimum creation where selected by the case, `POST /v1/runs`, returned Session View, and every existing authoritative action/View step through terminal state; preserve all action-specific regressions |
| `web/src/App.recovery.test.tsx` | Exact creation/entry key-body retention, same-pair manual retry, no automatic/replacement retry, mandatory tainted-404 retention, pre-storage reload limitation, post-storage reload GET-only recovery, Demo restart 404, storage failure, cancellation, generation, and late-response isolation |
| `web/src/test/fixtures.ts` | Add typed minimum creation, Player Character projection, eligible collection, and Run-entry fixtures reused by the four focused test owners |

No sixth test path is admitted. `web/src/test/server.ts` remains the generic
empty MSW server. `web/src/sessionRecovery.test.ts` remains unchanged because
the record/helper contract is unchanged. No backend, integration, MySQL,
scenario, smoke-script, generated, or snapshot test path belongs to P8-S5.

Proof that a sixth test file is required stops implementation and returns for
plan reassessment.

## 19. Exact later documentation-synchronization budget

**Later documentation/status synchronization budget: exactly 7 existing
authority/status paths, separate from production and tests.**

1. `PLANS.md`;
2. `docs/architecture.md`;
3. `docs/public_client_contract.md`;
4. `docs/run_protocol.md`;
5. `docs/structured_player_character_contract.md`;
6. `docs/structured_player_character_implementation_plan.md`; and
7. `docs/structured_player_character_run_playable_loop_plan.md`.

All seven will require truthful P8-S5 implementation/status/evidence/next-step
reconciliation because all seven currently identify P8-S5 as unstarted or own
the Web/recovery/phase boundary. This budget admits no plan file, source, test,
migration, dependency, configuration, scenario, generated evidence, build
artifact, guardrail, or workflow file.

This planning task authorizes none of those seven edits. The frozen plan itself
is not part of the later implementation synchronization budget and must remain
byte-unchanged after approval.

## 20. Acceptance criteria and mapped evidence

| ID | Acceptance criterion | Planned evidence |
| --- | --- | --- |
| P8S5-AC-01 | The client runtime schemas accept only the bounded minimum creation input and exact existing projection/collection/entry contracts, reject unsafe revision precision and incompatible/missing fields, enforce maximum 32 items and authoritative order, and expose no internal fields | `web/src/api/client.test.ts` schema matrices |
| P8S5-AC-02 | The three new client methods send exact paths, methods, `Accept`, `Content-Type`, `Idempotency-Key`, and JSON body, accept only HTTP 200 success, validate entry response/request identity, and make one fetch per explicit call | `web/src/api/client.test.ts` request-capture and fetch-count tests |
| P8S5-AC-03 | Scenario and eligible GETs render independent loading, success, empty, recoverable failure, and fail-closed contract-error states without a POST | `web/src/App.test.tsx` rendered state matrix |
| P8S5-AC-04 | Multiple eligible items preserve server order, allow explicit selection, and submit the selected exact ID/revision; `truncated=true` is disclosed without count or pagination claims | `web/src/App.test.tsx` multi-item/truncation tests |
| P8S5-AC-05 | Authoritative empty eligibility exposes one minimum creation control whose first POST uses the exact minimum body and a key created before send | `web/src/App.test.tsx` empty creation test plus `web/src/api/client.test.ts` capture |
| P8S5-AC-06 | Creation success clears its attempt and selects only the server projection as an entry candidate without browser persistence or a current-eligibility claim | `web/src/App.test.tsx` creation-to-selection assertions |
| P8S5-AC-07 | Run start freezes exact selected character ID/revision and scenario with one pre-created key, prevents duplicate POST, and does not submit the static character definition | `web/src/App.test.tsx` body/key/single-flight tests |
| P8S5-AC-08 | Direct contract-matching untainted 404/409/422 outcomes clear according to section 10; stale/missing/ineligible results invalidate selection and refresh safe server data | `web/src/App.test.tsx` definitive-result matrix |
| P8S5-AC-09 | Network/timeout/abort/response-loss/500/unrecognized outcomes retain an uncertainty-tainted exact pair, make no automatic retry, and allow only exact manual retry | `web/src/App.recovery.test.tsx` mutation uncertainty matrices |
| P8S5-AC-10 | After a tainted send, a manual exact retry receiving authorization/non-enumerating 404 retains the same key/body, generates no replacement, accepts no changed body, and performs no silent retry | Mandatory focused regression in `web/src/App.recovery.test.tsx` |
| P8S5-AC-11 | Entry 200 is fully validated, Session storage succeeds before the attempt clears, and View GET occurs only afterward | `web/src/App.test.tsx` ordered call/storage assertions and storage-failure case in `web/src/App.recovery.test.tsx` |
| P8S5-AC-12 | View failure after stored entry retains Session recovery and uses only safe View GET retry, with zero duplicate Run-entry POST | `web/src/App.test.tsx` View-failure test and `web/src/App.recovery.test.tsx` reload test |
| P8S5-AC-13 | Reload after Session storage restores by GET/request-status only; reload before response/storage does not recover or automatically repeat creation/entry | `web/src/App.recovery.test.tsx` two reload-boundary regressions with POST counters |
| P8S5-AC-14 | Demo process restart invalidates a stored missing Session through existing 404 clearing, while an uncertainty-tainted mutation 404 remains retained in the still-loaded component | `web/src/App.recovery.test.tsx` restart/missing-state cases |
| P8S5-AC-15 | Unmount/client replacement aborts in-flight work; obsolete responses cannot store Session state, clear an attempt, select a candidate, commit a View, or unlock a newer operation | `web/src/App.recovery.test.tsx` cancellation/generation/late-result tests |
| P8S5-AC-16 | The canonical rendered Demo-mode journey starts through Player Character create-or-reuse and Run entry, reads the exact returned Session View, performs every existing displayed action, follows 202/status behavior, and renders the terminal View | `web/src/App.action-loop.test.tsx` canonical 19-action test |
| P8S5-AC-17 | Existing manual Session read, Session recovery, action/stale/uncertain/clear/terminal behavior, and exact Demo warning remain supported | Existing and adjusted `App.test.tsx`, `App.action-loop.test.tsx`, and `App.recovery.test.tsx` regressions |
| P8S5-AC-18 | Browser storage contains only the existing Session record; pending mutation data, Player Character, Run, View, errors, and keys never enter storage or URL state | Storage spies and URL assertions in `web/src/App.recovery.test.tsx` |
| P8S5-AC-19 | No backend, route, DTO, OpenAPI, schema, migration, dependency, configuration, scenario, generated, style, or recovery-helper file changes | Exact Git inventory and diff inspection |
| P8S5-AC-20 | Focused Web tests, typecheck, lint, build, canonical Offline verification, and diff checks pass with no live Provider or non-loopback network | Commands in section 21 and recorded implementation evidence |

Every acceptance criterion has an identified evidence owner. P8-S6 remains
responsible for later complete cross-surface evidence and Phase 8 closure; it
does not replace these focused P8-S5 acceptance gates.

## 21. Focused and canonical verification strategy

The future authorized implementation uses layered local verification. These
commands are requirements of that later task; they are intentionally not run
during planning.

### Layer 1: exact focused Web behavior

```powershell
npm --prefix web run test:run -- src/api/client.test.ts src/App.test.tsx src/App.action-loop.test.tsx src/App.recovery.test.tsx
```

This selection executes `web/src/test/fixtures.ts` through its importing tests.
It must include the mandatory history-sensitive 404 regression and the full
rendered canonical action loop.

### Layer 2: canonical Web static/build checks

```powershell
npm --prefix web run typecheck
npm --prefix web run lint
npm --prefix web run build
```

The build is local and uses the existing Vite configuration. It must not
install or update packages and must not contact a non-loopback service.

### Layer 3: repository canonical Offline verification

```powershell
.\scripts\verify.ps1 -Mode Offline
```

Offline mode supplies the required sanitized child process, full offline
pytest, Python compilation, dependency check, Alembic metadata checks, and Git
diff check. It is required before P8-S5 implementation completion even though
P8-S5 changes only Web files.

### Layer 4: exact candidate hygiene

```powershell
git diff --check
git status --short
git diff --stat
git diff -- web/src/api/schemas.ts web/src/api/client.ts web/src/App.tsx
git diff -- web/src/api/client.test.ts web/src/App.test.tsx web/src/App.action-loop.test.tsx web/src/App.recovery.test.tsx web/src/test/fixtures.ts
```

Inspect the later seven-document synchronization separately and confirm the
exact `3 production + 5 test + 7 documentation` inventory before independent
implementation review.

MySQL, Full, live Provider, deployment, and non-loopback verification are
excluded from P8-S5. The server contract, normal real-MySQL entry path, and Demo
persistence/composition were completed by P8-S3/P8-S4; this slice changes no
backend or database behavior. P8-S6 owns the complete cross-surface rerun and
final Phase 8 evidence consolidation.

## 22. Implementation ordering

The separately authorized implementation proceeds in this order:

1. Reconfirm the approved plan's exact SHA-256, clean aligned implementation
   baseline, and unchanged path inventories.
2. Add only the new runtime schemas/types in `web/src/api/schemas.ts`.
3. Add only the three client methods in `web/src/api/client.ts`.
4. Add typed fixtures and focused client tests in their exact two test paths;
   establish request/response/error/no-retry behavior before UI orchestration.
5. Replace the App's primary legacy creation journey with exact eligible,
   minimum-create, selection, Run-entry, and Session handoff state.
6. Update `App.test.tsx` for pre-play and entry behavior.
7. Update the canonical full-loop case in `App.action-loop.test.tsx` so entry
   begins through the P8-S5 journey while all existing action evidence remains.
8. Add the exact uncertainty, history-sensitive 404, storage, reload, restart,
   cancellation, and late-response evidence in `App.recovery.test.tsx`.
9. Run Layers 1 and 2; correct only failures within the exact authorized paths.
10. Run canonical Offline verification and candidate hygiene.
11. Complete the canonical documentation-synchronization checklist and update
    exactly the seven paths in section 19 with truthful implementation evidence
    and status.
12. Freeze exact changed bytes and hashes, then stop for fresh independent
    implementation review. Do not stage or commit.

## 23. Rollback and preservation expectations

P8-S5 has no database, migration, server, receipt, or deployment rollback.
Until a later commit is explicitly authorized, all work remains an unstaged
local candidate.

If implementation cannot satisfy this plan:

- stop without broadening the path inventories;
- preserve evidence of the exact mismatch;
- do not alter backend or authority documents to hide the mismatch;
- do not delete or rewrite an unexpected user-owned path;
- return for plan reassessment; and
- keep P8-S6 unstarted.

Removing an uncommitted P8-S5 candidate under separate explicit authorization
would restore the prior Web behavior only. It would not mutate server state.
Existing Session recovery records remain valid because their schema and helper
are unchanged. Component-memory mutation attempts have no durable rollback
artifact and disappear on reload exactly as documented.

## 24. Documentation, review, and publication workflow

This plan has one operative plan-review success verdict:

`STRUCTURED_PLAYER_CHARACTER_P8_S5_IMPLEMENTATION_PLAN_APPROVED`

No historical approval token or generic approval phrase can satisfy that gate.
The required sequence is:

1. fingerprint this exact candidate;
2. perform a separately authorized independent read-only plan review bound to
   its exact bytes and SHA-256;
3. if any byte changes, invalidate the hash and review result, correct only
   under separate authority, refingerprint, and obtain a fresh review;
4. after the exact operative verdict, obtain separate authorization to stage
   and commit only this plan;
5. verify staged and committed bytes and sole-path scope;
6. the user publishes manually;
7. confirm a clean aligned published baseline; and
8. only then request a separately authorized P8-S5 implementation task bound to
   this plan and exact path budgets.

During implementation, all applicable owners in section 19 must become
truthful before independent implementation review. The implementation
candidate then receives its own fresh review and separate commit authority.
No plan approval pre-approves implementation, correction, staging, commit,
publication, P8-S6, or final Phase 8 closure.

## 25. Residual limitations

The accepted P8-S5 result will still have these deliberate limits:

- unresolved creation/entry attempts survive only in the currently loaded
  component;
- reload before authoritative entry response and Session-record storage can
  strand a committed Run from this Web client's perspective;
- no Run read/list/discovery route exists, so a bound character with no known
  Session ID cannot be used to rediscover or resume its Run;
- no pending-operation receipt discovery exists;
- browser close, cross-tab, cross-browser, cross-device, and multi-device
  pending-operation recovery are unsupported;
- deterministic Demo state, including Player Characters, Runs, Sessions, and
  receipts, is lost on server-process restart;
- the smallest valid blank declaration is the only P8-S5 creation UI; character
  profile authoring remains future work;
- scenario settlement leaves the Run active and the character bound;
- production authentication, deployment, production durability claims, live
  Provider behavior, broader Run Protocol, later progression, P8-S6, Phase 8
  closure, and overall project completion remain outstanding.

These limits are represented honestly in tests and documentation. P8-S5 does
not promise recovery or durability the public contract cannot provide.

## 26. Explicit implementation blockers

No blocker exists at the planning baseline. Implementation must stop for fresh
reconciliation if any of these conditions appears:

1. the approved plan hash or implementation baseline differs without a
   completed baseline-invalidation assessment;
2. any required public route, DTO, error, response relationship, Demo service,
   or Session recovery helper is absent or contradicts this plan;
3. the minimum flow requires a new server route, server command, public DTO,
   public error, OpenAPI change, lifecycle state, or recovery promise;
4. correct Session-ID handoff requires changing `sessionRecovery.ts`;
5. implementation requires a fourth production path, sixth test path, or an
   eighth later documentation path;
6. a confirmed defect requires a guardrail/workflow change outside the exact
   budgets;
7. exact revision identity cannot be preserved by the Web runtime schema;
8. a test requires non-loopback network, live Provider, dependency installation,
   MySQL, Full verification, deployment, or P8-S6 scope to establish a P8-S5
   acceptance criterion; or
9. any implementation decision would reopen P8-S2, P8-S3, or P8-S4 ownership.

The implementer must report the precise gap and must not repair it by silent
scope growth.

## 27. Exact next actions

For this unreviewed candidate now:

1. leave `docs/structured_player_character_p8_s5_implementation_plan.md`
   unstaged and uncommitted;
2. return control to the user;
3. perform a separately authorized independent review bound to the candidate's
   exact raw bytes and SHA-256;
4. do not correct, commit, publish, or implement the plan until that review
   returns its exact verdict; and
5. keep P8-S6 unstarted.

After exact plan approval, the next authorized workflow action is a separately
authorized plan-only commit and manual user publication followed by clean
aligned-baseline confirmation. P8-S5 implementation may begin only in a later
separately authorized task. P8-S6, Phase 8 closure, and overall project closure
remain prohibited.

P8-S6 remains unstarted. Phase 8 and the overall project remain incomplete.
