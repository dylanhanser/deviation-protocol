# Deviation Protocol Roadmap

This file is a concise navigation aid for the current baseline, next phase,
and intentional deferrals. Detailed design remains in its owning documents.

## Current Baseline

- Branch: `main`
- Repository HEAD: `269bd0b5e9a70467fa5fa7a10419107c205d4e15`
- Original Phase 3.2 planning baseline:
  `44258527c169170ee79540a130ac5e143211c748`
- Phase 3.1c implementation baseline: `4da6791cf43070b15b0c619129ffb3c0b59e22b2`
- Latest completed phase: Phase 3.1c
- `origin/main` matches Repository HEAD; Phase 3.2a remains an uncommitted local
  review object

## Phase Status

| Phase | Status |
| --- | --- |
| Phase 1 | Complete |
| Phase 2.1 | Complete |
| Phase 2.2 | Complete |
| Phase 2.3a | Complete |
| Phase 2.3b | Complete |
| Phase 2.4a | Complete |
| Phase 2.4b | Complete |
| Phase 3.0 | Complete |
| Phase 3.1a | Complete; independently audited and pushed (`43bf83dcaccf9e7400965f863f545ee1043beacf`) |
| Phase 3.1b | Complete; third independent read-only audit `APPROVED`; the first audit's 3 findings and the second audit's 3 Major and 1 Minor findings are closed; committed and pushed (`b4352230ef0c9bc91a5bf78e69e88e0feab4908c`) |
| Phase 3.1c | Complete; same-tab recovery boundary clarified (`a14a76d359d4aa777ed16ff239c2157c912e47dc`) and isolated-storage boundary covered (`4db377b4cdb195e2d05fbf9a67be1e0600cfba15`) |
| Phase 3.2 | Phase 3.2a implemented locally but not approved or committed; fresh independent read-only audit required; Phase 3.2b not started; phase incomplete |
| Later phases | Not started |

## Phase 2.4b

Phase 2.4b completed the first-copy public API playthrough:

- The public API is fully playable for the first copy.
- The `life_disputed` to resolution route is reachable in production.
- `protocol_broken` and `record_challenged` are successful endings.
- `deadline_reached` is a failure ending.
- Deterministic end-to-end and MySQL routes cover the complete path.

## Phase 3.1a

The first player-facing Web batch is complete, independently audited, and
pushed at `43bf83dcaccf9e7400965f863f545ee1043beacf`. It adds:

- an isolated React/Vite/TypeScript project under `web/`;
- Zod-backed public DTOs and one public API client boundary;
- scenario/role discovery, session creation, and manual full View reads;
- MSW contract tests plus a minimal accessible verification page; and
- no actions, polling, persistence recovery, authentication, or deployment.

## Phase 3.1b

**Status: complete. The third independent read-only audit returned `APPROVED`
with no new Critical, Major, or Minor findings. The first audit's 3 findings
remain closed, and all 3 Major and 1 Minor findings from the second audit's
earlier `CHANGES_REQUIRED` verdict are closed. The approved implementation was
committed as `b4352230ef0c9bc91a5bf78e69e88e0feab4908c` (`feat(web): complete
Phase 3.1b playable action loop`). Repository HEAD is the subsequent Phase 3.1b
status-documentation commit `3d3181f7ea216003e582e3e658f6afda9cbbd852`.
At that Phase 3.1b completion baseline, Phase 3.1c was approved/planned but had
not started; Phase 3.1c has since been completed as recorded below.**

Phase 3.1b is a complete minimum playable action loop in one browser tab, with
no persistence or reload recovery. A user can create a Session or manually load
one by Session ID, read the authoritative `PlayerSessionView`, act only through
that View's `action_affordances`, and replace the authoritative Session ID and
View atomically after each successful read. The loop supports ACTIVE to ACTIVE
play and ACTIVE to ENDED settlement; an ENDED View displays its ending and
offers no action controls.

### In Scope

- All three current affordance modes: `DECISION`, `FREE_ACTIONS`, and `ENDED`.
  `DECISION` submits `CHOOSE` with the current `decision_id` and one displayed
  `choice_id`. `FREE_ACTIONS` renders only actions advertised by the current
  View: `TALK` uses `input_kind=DIALOGUE` and the `dialogue` field;
  `CUSTOM`, `EXPLORE`, `OBSERVE`, and `MOVE` use
  `input_kind=DESCRIPTION` and the `description` field; and `CONTINUE` uses
  `input_kind=NONE` with no additional payload. Only advertised, currently
  visible targets are offered; `TALK` retains its public optional-target
  semantics. `narrative_frame.suggested_actions` is display-only and is not an
  executable contract.
- `POST /v1/sessions/{session_id}/actions`, including synchronous HTTP 200 and
  asynchronous HTTP 202, followed on completion by
  `GET /v1/sessions/{session_id}/view` rather than treating `ActionResponse` or
  `NarrativeFrame` as a complete View.
- Only after an action POST returns 202, read-only polling of
  `GET /v1/sessions/{session_id}/requests/{client_request_id}` during the
  current page/component lifecycle. Polling uses the same `session_id` and
  `client_request_id`; it is not an action retry. It follows the existing public
  contract's retry indication and terminal semantics: `PENDING`/
  `POLL_SAME_REQUEST` checks the same request again, `COMMITTED`/
  `RESPONSE_AVAILABLE` fetches a new View, `STALE`/`REFRESH_VIEW` fetches a new
  View, and `OUTCOME_UNKNOWN` or `FAILED` with `DO_NOT_RETRY` never causes an
  automatic POST. The exact wait strategy must follow the existing public
  contract and schema and be proved by implementation tests; this plan adds no
  polling limit, timeout, header priority, or server semantic.
- One foreground-operation lock shared by create, manual View load, and action
  operations, preventing rapid double-clicks, concurrent submissions, and stale
  response commits. Within the current component lifetime, `AbortController`
  and an operation token stop obsolete work and polling on unmount or
  invalidation. Cancellation does not claim to retract an action already
  received by the server.
- Accessible `loading`, `pending`, `refreshing`, `error`, `ended`, and
  View-stale states, plus Zod, public API client, MSW, and React regression
  coverage for the loop.

The HTTP DTOs and authority rules remain owned by
[`docs/public_client_contract.md`](docs/public_client_contract.md); this phase
does not redefine or extend them. A refreshed View replaces every earlier
affordance, and no control may be derived from narrative prose or internal
state.

### Uncertain Results and View Refresh Failures

- If the action POST ends in a network error, abort, or another
  transport-uncertain result, the client does not resend the action, generate a
  new `client_request_id`, or claim that the action did not occur. It preserves
  the last confirmed View, marks it potentially stale, disables further
  actions, and warns that the action may have been submitted, must not be
  retried, and requires a fresh authoritative View.
- If an action completes but the following View GET fails, the client does not
  substitute `ActionResponse` or `NarrativeFrame` for the View. It preserves
  the last confirmed View, marks it stale, disables further actions, and permits
  a later explicit authoritative View read without replaying the action.
- Phase 3.1b does not promise recovery of an uncertain action after page reload
  or browser restart.

### Out of Scope

- Session recovery after reload; persisted `client_request_id`; pending recovery
  after reconnection; `localStorage`, `sessionStorage`, or URL state recovery;
  and cross-tab coordination.
- Background action retry, automatic actions or `CONTINUE`, optimistic updates,
  any action replay, action history, and chat history.
- User accounts, authentication, guest identity, abuse controls, telemetry,
  animation systems, and a broad visual redesign.
- Deployment, hosting, production CORS, Provider-direct access, and internal
  snapshot, job, or lease endpoints.
- ORM, Repository, database schema, Alembic, and public backend contract changes.
- Combat, `DeviationEvaluator`, and later anomaly systems.

### Minimum Playable Claim and Later Boundary

Phase 3.1b is complete as a minimum playable Demo that completes the public
action loop locally in one browser tab, without persistence or reload recovery.
It is not a publicly deployable, stable external-playtest,
reconnection-capable, or production-ready release.

Approved Phase 3.1c is planned to address only same-tab reload and recovery of
requests already confirmed pending by the server. Later work must still address
general reconnection; guest identity, authentication, and abuse controls;
deployment, base URL, and production CORS; an available Provider or
deterministic demo environment; and external-playtest usability and recovery
flows.

## Phase 3.1c

**Status: complete. The bounded recovery implementation was committed as
`4da6791cf43070b15b0c619129ffb3c0b59e22b2`; its same-browsing-session boundary
was clarified in `a14a76d359d4aa777ed16ff239c2157c912e47dc`, and the isolated-storage
boundary regression was added in `4db377b4cdb195e2d05fbf9a67be1e0600cfba15`.
Final verification passed with 167 Web tests and Offline verification at 842
passed, 48 skipped.**

The formally approved direction is **Web same-tab reload and
confirmed-pending-request recovery**. It adds a bounded client recovery loop to
the existing Web Demo without changing the public API, Python backend, ORM,
database schema, or Alembic migrations.

### Frozen Goal and Persistence Boundary

- Recovery is promised only after a reload in the same browser tab and uses
  `sessionStorage`. Browser-close or browser-restart recovery, cross-tab
  coordination, and general network reconnection are not supported.
- A persistence record contains only a version number, the opaque Session ID of
  a previously verified Session, and, optionally, the `client_request_id` of a
  request for which the server already returned HTTP 202. A POST with no
  confirmed 202 is transport-uncertain and is not recovered as a pending
  request.
- The client does not persist a View, affordances, an action payload, action or
  user input, a response body, narrative output, or any other copy of server
  state.
- Every final state is read again from the authoritative
  `GET /v1/sessions/{session_id}/view`. Recovery never treats cached data or a
  request-status response as a complete View and never displays an old or
  unconfirmed affordance.
- No startup or recovery path automatically posts or replays an action, and no
  path automatically generates or substitutes a new `client_request_id`.
- There is no arbitrary client TTL. A valid record remains until the tab is
  closed, the user explicitly clears it, or the user creates or switches to a
  different Session.

### Frozen Recovery Semantics

- With no confirmed pending request, startup restores state by reading the
  authoritative `/view` for the recorded Session ID.
- With a confirmed pending request, the UI stays action-locked, renders no
  cached affordance, and queries request status using exactly the recorded
  Session ID and `client_request_id`. It emits no action POST.
- `PENDING` with `POLL_SAME_REQUEST` continues querying the same request,
  strictly honors the server's `retry_after_seconds`, and creates no new
  request ID.
- `COMMITTED` with `RESPONSE_AVAILABLE` reads the complete authoritative
  `/view`; the request-status response is not used as a View.
- `STALE` with `REFRESH_VIEW` reads the complete authoritative `/view` and does
  not replay the action.
- `FAILED` with `DO_NOT_RETRY` and `OUTCOME_UNKNOWN` with `DO_NOT_RETRY` never
  cause a POST. They may perform a controlled authoritative `/view` GET and
  continue to reuse Phase 3.1b's existing stale, uncertain, and
  confirmed-view-unavailable rules without inventing new server lifecycle
  semantics.
- A network error, damaged response, or result that cannot be parsed safely
  during request-status or other recovery work stops automatic recovery, keeps
  actions locked, and permits only a user-triggered retry of a safe GET. It
  never causes an automatic POST.
- A 404 from a recovery endpoint invalidates the persisted record. The client
  creates no action controls and safely returns to the initial Session/scenario
  UI.
- Persisted data is validated before use. A corrupt record, invalid shape,
  unsupported version, or Session/request identity mismatch is cleared
  directly.
- Creating a new Session, switching Sessions, writing or clearing a pending
  request, and committing an authoritative View remain atomic with respect to
  the current client state.
- Recovery reuses the existing foreground operation lock, generation/token,
  and `AbortController` protections so obsolete work cannot commit after an
  invalidation, Session switch, or unmount.

### Explicit Out of Scope

- Recovery of a transport-uncertain POST; automatic action retry or repost;
  and automatic replacement of an old request ID with a new one.
- General network reconnection, long-running background recovery, recovery
  after browser close or restart, `localStorage`, URL-persisted state, and
  cross-tab synchronization.
- Guest identity, authentication, abuse controls, deployment or hosting,
  production CORS, and a formal external playtest.
- A deterministic local Demo Provider, DeepSeek Provider changes, visual
  redesign or animation, and action or chat history.
- Any public API, Python backend, ORM, database schema, database, or Alembic
  migration change.

A deterministic local Demo Provider remains only an unnumbered candidate for
later work; it is not part of Phase 3.1c.

### Completion Evidence

Phase 3.1c is complete against the frozen boundary above:

1. After reload, an ACTIVE or ENDED Session is restored only through its
   authoritative `/view`.
2. A request already confirmed with HTTP 202 resumes status polling with
   exactly the same Session ID and `client_request_id`.
3. Every startup and reload recovery path has an action POST count of zero.
4. Web regressions cover every existing request-status state/instruction branch.
5. A missing persistence record means there is nothing to recover; it is not an
   expired record. Corrupt, tampered, unsupported, or identity-mismatched
   records cannot produce action controls and retain their existing safe
   handling. Time-expired records are not applicable to Phase 3.1c: the frozen
   record has no time field or client TTL, so this phase neither implements nor
   tests time-expiry recognition.
6. No old affordance flashes while recovery is in progress.
7. Session switches and obsolete asynchronous responses cannot commit into the
   new current Session.
8. After an ordinary network error or invalid response, the user can retry only
   a safe request-status GET manually; no automatic POST occurs. Storage access
   failure also remains safely action-locked. Corrupt, tampered, unsupported-
   version, and identity-mismatched records retain their safe handling.
9. Transport-uncertain POST recovery and cross-tab recovery remain unsupported.
   The unsupported-boundary regression keeps the old pending record in one
   Storage context while starting the application in an independent empty
   context. This proves that a new browsing session without the prior
   `sessionStorage` record does not recover the old Session, View, pending
   identity, or action affordance and performs no old status GET, old `/view`
   GET, action POST, or identity generation. It does not simulate or claim an
   end-to-end browser-process close, restart, or tab restore; browser-close and
   browser-restart recovery remain unsupported.
10. Final verification passed: `npm run test:run` reported 5 files and 167 Web
    tests passed; `.\scripts\verify.ps1 -Mode Offline` reported 842 passed and
    48 skipped. Lint, typecheck, build, compileall, `pip check`, Alembic
    heads/history, and `git diff --check` also passed.
11. Completion review covered no action replay, authoritative View use,
    persisted-data validation, operation/Session races, stale-response
    isolation, and the recovery-time UI action lock.
12. Phase 3.1c requires no live DeepSeek, MySQL, network verification, or
    Alembic migration.

## Phase 3.2 Deterministic Demo Environment

**Status: Phase 3.2a is implemented locally but is not approved or committed.
The second independent audit returned `CHANGES_REQUIRED`; its earlier findings
and the subsequent Demo Provider authorization findings, including the
nested/re-entrant follow-up, have been corrected locally. This complete
follow-up, including the latest authorization-entry ordering and public
authority encapsulation corrections, still requires a fresh independent
read-only audit. Phase 3.2b has not started, and Phase 3.2 remains incomplete.**

Phase 3.2 freezes a local-only, explicitly selected Demo composition that lets
the existing Web action loop complete one meaningful `death_certificate` route
without MySQL, DeepSeek, an API key, secrets, or any non-loopback network
service. It reuses the sealed public API, DTOs, action-affordance authority and
Phase 3.1c recovery/no-replay semantics. It does not make the normal
`deviation_protocol.api.main:app` composition or the fixed `demo-dev-only`
principal production-ready.

The implementation is split for review atomicity:

- **Phase 3.2a — Demo backend runtime:** an explicit demo-only composition
  root, a process-local transactional in-memory adapter and a generic
  deterministic `NarrativeProvider`, with a complete public-HTTP playthrough,
  two-process deterministic replay whose test-only IPC trace proves the exact
  private generator stream, and external-I/O denial evidence.
- **Phase 3.2b — Web launch and playthrough:** one documented PowerShell launch
  command, Demo-only Vite dotenv isolation, an unmistakable
  ephemeral/non-production Web label, a full Web-loop regression to an ENDED
  View, the separately bounded `scripts/smoke-demo.ps1` startup/proxy/sentinel
  smoke with direct `publicScenarioCatalogSchema` validation and fail-closed
  Windows `cmd.exe`/`npm.cmd` resolution plus validator ExitCode propagation,
  and the frozen manual walkthrough. Phase 3.2b depends on a completed,
  verified and independently approved Phase 3.2a; it cannot be claimed
  complete in parallel with an unapproved Phase 3.2a. Phase 3.2 is complete
  only after both subphases are separately completed, verified and
  independently reviewed.

The current `death_certificate` content is sufficient; no scenario, database
seed, ORM model, schema or Alembic migration is planned. Demo state lives only
for the backend process lifetime. Same-tab reload remains supported while that
process lives; backend restart is ordinary session loss and follows the
existing safe 404 recovery behavior. The exact frozen specification, including
determinism, isolation, boundaries, test matrix, completion conditions and
verification commands, is in
[`docs/phase_3_2_deterministic_demo_environment.md`](docs/phase_3_2_deterministic_demo_environment.md).

## Deferred by Design

- Memory rebuild and compaction.
- Scenario replay and `scenario_run_id`.
- Cross-scenario NPC identity.
- `DeviationEvaluator`.
- Combat.
- Worker, queue, or distributed system.

## Stable Decisions

- Models generate narrative candidates only.
- Local server rules own state-write authority.
- Ordinary scenarios are not designed for replay solely to enable collection.
- Live DeepSeek is not a normal test dependency.
- MySQL is the only database target; there is no SQLite fallback.

## Workflow

1. Sol High implements the bounded phase.
2. Sol XHigh performs an independent review.
3. Run the applicable Quick, Offline, and MySQL verification.
4. Explicitly stage only reviewed paths.
5. Commit and push only when separately authorized.

## Document Ownership

- `PLANS.md` records phase status, next steps, and intentional deferrals only.
- Architecture details: `docs/architecture.md`.
- Memory boundaries: `docs/player_memory.md`.
- Playable-slice contract: `docs/playable_vertical_slice.md`.
- Engineering guardrails: `docs/engineering/guardrails.md`.
