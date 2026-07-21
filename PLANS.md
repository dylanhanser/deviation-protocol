# Deviation Protocol Roadmap

This file is a concise navigation aid for the current baseline, next phase,
and intentional deferrals. Detailed design remains in its owning documents.

## Current Baseline

- Branch: `main`
- Commit: `43bf83dcaccf9e7400965f863f545ee1043beacf`
- Latest completed phase: Phase 3.1a
- Committed baseline status: clean

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
| Phase 3.1b | Scope sealed; implementation not started |
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

**Status: scope sealed; implementation not started.**

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

When complete, Phase 3.1b may be called a minimum playable Demo that completes
the public action loop locally in one browser tab, without persistence or reload
recovery. It is not a publicly deployable, stable external-playtest,
reconnection-capable, or production-ready release.

Later work must still address reload/reconnection/pending recovery; guest
identity, authentication, and abuse controls; deployment, base URL, and
production CORS; an available Provider or deterministic demo environment; and
external-playtest usability and recovery flows.

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
