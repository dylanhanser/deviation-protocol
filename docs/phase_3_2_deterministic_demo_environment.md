# Phase 3.2 Deterministic Demo Environment

## Frozen status and evidence baseline

Status: **specification frozen for review**. Implementation has not started,
Phase 3.2 is not complete, and this document records target behavior rather
than current capability.

The planning baseline is `main` at
`44258527c169170ee79540a130ac5e143211c748`, with `origin/main` at the same
commit and a clean index and worktree before this planning edit.

Current repository evidence establishes the following boundary:

- The Phase 3.1c Web client already creates and reads Sessions, renders only
  authoritative `action_affordances`, submits every current action shape,
  handles HTTP 200/202, reads the complete `/view` after completion, and safely
  recovers only a same-tab Session or a server-confirmed pending request.
- `deviation_protocol.api.main:app` currently requires `DATABASE_URL` for its
  MySQL engine. It injects `DeepSeekNarrativeProvider` only when DeepSeek
  settings are valid; otherwise Narrative actions fail through the existing
  not-configured boundary. There is no runnable Demo mode.
- `NarrativeProvider` is already a supplier-neutral application Protocol.
  `ScriptedOpeningProvider` and `BlockingScriptedProvider` prove deterministic,
  no-network playthroughs, but they are test-local, contain scenario-copy
  branches, and are not reusable runtime Providers.
- The public ASGI and MySQL playtests already prove that
  `death-certificate-1.1.0` can reach `protocol_broken` and
  `record_challenged`, or fail at `deadline_reached`, through public endpoints.
- The test-local `MemoryStore`/`MemoryUnitOfWork` proves that the existing
  Repository ports can be backed in memory, but it is a fixture, not supported
  application persistence or a launchable environment.

Nothing in this specification relabels those test assets as current runtime
features.

## Frozen architecture answers

1. **Reusable Provider:** no supported runtime deterministic/fake Provider
   exists. The test-local scripted Providers are behavior oracles only; Phase
   3.2a adds a generic implementation of the existing Protocol without
   importing test code or branching on scenario copy.
2. **API versus mode selection:** the Demo reuses the complete formal public
   HTTP contract without DTO/schema changes. Mode selection occurs only through
   a dedicated composition root and launcher, never through public input or a
   default fallback.
3. **Persistence:** process-lifetime server persistence is required so the
   existing Session/action/recovery loop works. Because MySQL is a network
   service requiring configuration, the Demo uses a new in-process adapter for
   existing ports. It is neither durable storage nor a production/SQLite
   fallback.
4. **Repeatability:** each clean Demo process uses the exact deterministic
   logical-time and ID/seed sequences in section C, while the Provider is a
   pure function of the validated request. Cross-process exact replay and the
   mechanically bounded caller-identity comparison are defined there.
5. **Minimum play path:** the canonical path is the existing successful
   `death_certificate` route to `protocol_broken`, frozen in section H.
6. **Scenario sufficiency:** current `death-certificate-1.1.0` content already
   supports the path. No scenario or narrative content is added.
7. **New support assets:** no database row, database seed, ORM model or
   migration is needed. Implementation does require the Demo Provider/store,
   deterministic generator state, the PowerShell launcher, one non-secret Web
   mode value, the cross-process test-only IPC bootstrap/trace protocol, and
   test-only full-path and public-scenario-schema validation evidence.
8. **Production confusion:** the dedicated module, explicit command, loopback
   binding, sanitized environment, fixed internal Provider/model sentinels and
   exact local/temporary/non-production banner keep the Demo distinct. Normal
   startup never selects it.

## A. Problem statement

The Web action loop is complete, but a normal local run cannot finish Narrative
actions without both a MySQL service and a configured external Provider. This
prevents a repeatable, secrets-free Demo and makes later external-playtest work
depend on infrastructure that is unrelated to the gameplay slice being
evaluated.

Phase 3.2 must provide the smallest complete local vertical slice: one explicit
launch command, one existing scenario, one complete path through the existing
Web loop, deterministic gameplay results, and automated proof that neither the
database nor an external Provider/network service is used. It is not a full
Demo product, a production Provider, or a deployment phase.

The implementation is split into two reviewable subphases because the
transactional in-memory adapter and the Web/startup integration have different
failure surfaces:

1. **Phase 3.2a — Demo backend runtime.** Add the isolated composition,
   transactional process-local storage, deterministic Provider, public-HTTP
   happy path, cross-process determinism proof and external-I/O denial proof.
2. **Phase 3.2b — Web launch and playthrough.** Add the single-command process
   launcher, Demo-only Vite dotenv isolation, Web Demo label, full Web-loop
   regression, the separately bounded startup/proxy/sentinel smoke,
   documentation and manual walkthrough.

Phase 3.2b depends on a completed, verified and independently approved Phase
3.2a. It must not be implemented or claimed complete in parallel with an
unapproved Phase 3.2a. Neither subphase alone permits a Phase 3.2 completion
claim; Phase 3.2 is complete only after both subphases are separately
implemented, verified and independently reviewed.

## B. User-observable behavior

From the repository root, after existing Python and Web dependencies have been
installed, the user runs exactly:

```powershell
pwsh -NoProfile -File .\scripts\start-demo.ps1
```

The command performs no dependency installation. It fails clearly if the
repository `.venv`, required Web dependencies, ports, or executable
prerequisites are unavailable. On success it starts one single-worker backend
without reload at `127.0.0.1:8000` and the Vite Web client at
`127.0.0.1:5173`, prints the latter loopback URL, waits until interrupted, and
stops both child processes on Ctrl+C or child failure. It does not open a GUI
or browser automatically.

The page displays the exact meaning, not merely the word “Demo”:

> Deterministic Demo · local only · temporary data · not a production Provider

The user can select the existing public `death_certificate` scenario and its
default investigator, create a Session, complete the path frozen in section H,
and receive an authoritative ENDED View for `protocol_broken`. Every control is
still derived from the latest `action_affordances`; the Demo adds no shortcut,
auto-play, hidden state control, or Provider-direct endpoint.

State survives page reload in the same tab while the backend process remains
alive. Stopping or restarting the backend intentionally loses all Demo server
state. A subsequent recovery GET receives the existing safe 404 behavior, and
the existing Phase 3.1c client invalidates its same-tab record without replaying
an action.

## C. Exact meaning of deterministic

“Deterministic” is frozen at two levels.

### Exact cross-process server replay

Given:

- the same committed code and `death-certificate-1.1.0` content;
- two independently started, clean, single-worker Demo backend OS processes;
- the same ordered HTTP requests, including identical scenario, character,
  `turn_id`, `client_request_id`, action type, input text, targets, decision ID
  and choice ID; and
- no concurrent or reordered requests,

the replay harness sends the complete section H path over real loopback HTTP to
each process and compares every response's HTTP status plus canonical JSON. It
must not construct two apps or two ASGI transports inside one Python process as
a substitute. Both processes start from empty Demo storage and generator state.
Canonical JSON means parse the response as JSON and serialize UTF-8 with keys
sorted, no insignificant whitespace, no ASCII escaping and no NaN/Infinity;
array order is unchanged. Exact replay performs no normalization; any
difference fails immediately.
This includes initial state, state-version progression, public clocks, frames,
action affordances, accepted narrative text, memory projection and ending.

The two exact-replay processes use fixed, different `PYTHONHASHSEED` values
`1` and `2`. Current public and persistence field types accept all values below;
the implementation must use these exact sequences rather than UUID, random or
wall-clock substitutes:

| Generator | First value and type | Per-call order and advance | Clean-process reset |
| --- | --- | --- | --- |
| Shared logical UTC clock | timezone-aware `datetime(2000, 1, 1, 0, 0, 0, tzinfo=timezone.utc)` | The process shares one callable across Session and turn orchestration. Its zero-based call `n` returns the base plus `n` seconds, then advances by one second. | Counter returns to `n=0`. |
| Session ID | string `demo-session-00000001` | One value per new Session, decimal suffix plus one after emission. | Suffix returns to `00000001`. |
| Persisted event ID | string `demo-event-00000001` | One shared stream for Session creation and turn orchestration; event drafts consume values in tuple order, suffix plus one per event. | Suffix returns to `00000001`. |
| Narrative job ID | string `demo-job-00000001` | One per prepared Narrative job, suffix plus one after emission. | Suffix returns to `00000001`. |
| Lease token | 32-character string `demo-lease-000000000000000000001` | One per claim or expired validated-proposal reclaim, emitted before the matching worker ID; decimal suffix plus one. | Suffix returns to `000000000000000000001`. |
| Worker ID | string `demo-worker-00000001` | One immediately after each lease token, suffix plus one. | Suffix returns to `00000001`. |
| Session seed | integer `1` | One per new Session, plus one after emission; values must remain within the current 63-bit seed boundary. | Returns to `1`. |

Generator families have independent counters. Within Session creation the
current call order is logical clock, Session ID, seed and scenario-start event
ID. Within Narrative work the current application call sites remain ordered;
job precedes claim, every claim emits lease then worker, and persisted event
IDs follow the authoritative event tuple. No generator call may be driven by
set/dict iteration. Demo-generated values that occur in a response, including
Session and event IDs and logical timestamps, remain in comparison and are not
caller identities. Job, lease, worker and seed values remain private under
API-001. They are proved for each actual replay process by the test-only trace
below, not inferred from expected behavior and not delegated to an in-process
unit test.

#### Test-only private generator trace composition and IPC

The trace exists only in the future
`tests/e2e/test_demo_cross_process_replay.py` harness and its
`tests/e2e/support/demo_replay_child.py` child bootstrap. The bootstrap builds
the Demo services with trace-capable wrappers around the real generator and
clock injection seams. It is not `deviation_protocol.api.demo:app`, is not
imported by the normal Demo or production composition, and is never selected by
`scripts/start-demo.ps1` or `scripts/smoke-demo.ps1`. Normal Demo startup has no
trace channel. The trace adds no public or private HTTP/debug endpoint and
changes no API, DTO, schema or OpenAPI model. It writes no file and appears in
no page, response, normal application log, stdout log or stderr log.

Each child has its own dedicated pair of anonymous pipes created by the parent
harness: one trace pipe from child to parent and one control pipe from parent to
child. The parent retains that child's trace read endpoint and control write
endpoint; the child receives only that child's trace write endpoint and control
read endpoint. No child inherits the other child's endpoints or any unrelated
non-standard handle. Trace bytes never use the child's stdout or stderr streams,
which remain separately managed ordinary server output and are never parsed as
trace evidence. The parent starts a dedicated reader thread/task for that trace
read endpoint immediately after spawn and continuously drains bytes during the
HTTP replay; it must not defer reading until `STOP` or process exit and thereby
risk blocking the child on a full anonymous-pipe buffer.

This is executable on the repository's Windows/Python 3.12 target. On Windows,
the parent uses `os.pipe()`, converts only the child endpoints with
`msvcrt.get_osfhandle`, temporarily marks those two handles inheritable, and
starts the child with `subprocess.Popen(close_fds=True)` plus
`STARTUPINFO.lpAttributeList["handle_list"]` containing exactly those handles.
The numeric handle values are separate `--trace-write-handle` and
`--control-read-handle` child-bootstrap arguments passed by an argv list with
`shell=False`, not interpolated shell text. The child adopts them with
`msvcrt.open_osfhandle(handle, os.O_WRONLY | os.O_BINARY)` and
`msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)`, respectively. The
parent immediately restores non-inheritance and closes its copies of the child
endpoints after a successful spawn. A POSIX branch may use `pass_fds`, but the
acceptance cannot depend on that branch and must exercise the explicit Windows
handle-list path on Windows.

One shared trace state owns the global ordinal and per-category ordinals. Its
wrappers call the underlying deterministic seam, then immediately record the
actual returned value before returning it to application code. The same traced
clock instance is injected into `SessionService` and the turn orchestrator, and
the same traced event-ID instance is injected into Session creation and turn
orchestration. Separate traced wrappers cover Session ID, job ID, lease token,
worker ID and seed. The trace therefore observes consumption at the real seam;
the bootstrap, orchestrator and parent may not reconstruct or predict records
after the fact. Current code exposes no other random/UUID/time generator seam
consumed by the section H path, so the exact category enum is:

`CLOCK`, `SESSION_ID`, `EVENT_ID`, `JOB_ID`, `LEASE_TOKEN`, `WORKER_ID`, `SEED`.

#### Trace wire protocol

The child encodes the trace as UTF-8 JSON Lines named
`deviation-demo-generator-trace` version `1`. Every message is one strict JSON
object followed by exactly one LF byte; CR, blank lines, invalid UTF-8,
NaN/Infinity and a final unterminated message are forbidden. A generator record
has exactly these keys and no others:

```json
{"protocol":"deviation-demo-generator-trace","version":1,"record_type":"GENERATOR","global_ordinal":1,"category":"CLOCK","category_ordinal":1,"raw_value":"2000-01-01T00:00:00+00:00"}
```

`global_ordinal` and each `category_ordinal` start at integer `1` and advance by
exactly one. `raw_value` is a JSON string for clocks and IDs, but a JSON integer
for `SEED`; type coercion is forbidden. Clock values use exactly
`YYYY-MM-DDTHH:MM:SS+00:00`. A completion record has exactly:

```json
{"protocol":"deviation-demo-generator-trace","version":1,"record_type":"COMPLETE","record_count":105,"last_global_ordinal":105}
```

The completion record occurs once, after all 105 generator records and only
after the parent has completed the final authoritative View request and sent
the single `STOP\n` control frame. The parent flushes and closes its control
writer immediately after that frame; the child requires that exact frame
followed by EOF, closes its control reader, requests graceful server shutdown,
waits for successful lifespan completion, writes and flushes the completion
record, closes the trace writer and exits zero. The continuously running parent
reader drains each trace pipe independently through EOF and is joined before
accepting that child. On any path the parent closes only its own pipe endpoints
and terminates/reaps only the child process object it created.
Malformed JSON, a wrong protocol/version or key set, an unknown category,
duplicate/missing/extra/out-of-order ordinals, a wrong JSON type or value,
duplicate/missing completion, bytes after completion, trace EOF before
completion, failure to drain EOF, control-channel failure, early child exit,
nonzero child exit or failed graceful shutdown fails the replay. Trace records
contain no secret, environment value, request body or non-generator data.

#### Frozen canonical event basis

The section H path has 19 state-changing actions after Session creation. In
order, the persisted event counts are `1, 2, 1, 2, 1, 1, 1, 1, 1, 1, 5, 1, 3,
1, 1, 1, 1, 1, 1`; Session creation adds `ScenarioStarted`, for 28 event IDs.
The five Provider-backed actions are opening `CUSTOM`, clinical-recheck `TALK`,
records `EXPLORE`, audit `EXPLORE` and patient `OBSERVE`. Each consumes six
non-event clock calls plus one clock per persisted event, one job ID, one lease
and one worker ID. Local actions consume one clock per persisted event; the
final fourth core choice additionally consumes one clock and one job ID for the
committed local-template settlement job. Reads, caller identities and the
Provider itself consume none of these generator seams.

The complete expected stream is therefore 105 generator records: 59 `CLOCK`,
28 `EVENT_ID`, 6 `JOB_ID`, 5 `LEASE_TOKEN`, 5 `WORKER_ID`, 1 `SESSION_ID` and 1
`SEED`. The stage label in the table is explanatory and is not a trace field.

#### Frozen complete expected generator trace

| Global | Category | Category ordinal | Expected raw value | Triggering canonical stage |
| ---: | --- | ---: | --- | --- |
| 1 | CLOCK | 1 | `2000-01-01T00:00:00+00:00` | Session creation: `created_at` |
| 2 | SESSION_ID | 1 | `demo-session-00000001` | Session creation: new Session |
| 3 | SEED | 1 | `1` (JSON integer) | Session creation: `random_seed` |
| 4 | EVENT_ID | 1 | `demo-event-00000001` | Session creation: `ScenarioStarted` |
| 5 | CLOCK | 2 | `2000-01-01T00:00:01+00:00` | Opening `CUSTOM`: prepare job |
| 6 | JOB_ID | 1 | `demo-job-00000001` | Opening `CUSTOM`: Provider job |
| 7 | CLOCK | 3 | `2000-01-01T00:00:02+00:00` | Opening `CUSTOM`: claim |
| 8 | LEASE_TOKEN | 1 | `demo-lease-000000000000000000001` | Opening `CUSTOM`: lease |
| 9 | WORKER_ID | 1 | `demo-worker-00000001` | Opening `CUSTOM`: claim owner |
| 10 | CLOCK | 4 | `2000-01-01T00:00:03+00:00` | Opening `CUSTOM`: store proposal |
| 11 | CLOCK | 5 | `2000-01-01T00:00:04+00:00` | Opening `CUSTOM`: begin finalize |
| 12 | CLOCK | 6 | `2000-01-01T00:00:05+00:00` | Opening `CUSTOM`: pre-persist lease check |
| 13 | EVENT_ID | 2 | `demo-event-00000002` | Opening `CUSTOM`: event 1/1 |
| 14 | CLOCK | 7 | `2000-01-01T00:00:06+00:00` | Opening `CUSTOM`: event 1/1 time |
| 15 | CLOCK | 8 | `2000-01-01T00:00:07+00:00` | Opening `CUSTOM`: commit job |
| 16 | CLOCK | 9 | `2000-01-01T00:00:08+00:00` | Recheck `TALK`: prepare job |
| 17 | JOB_ID | 2 | `demo-job-00000002` | Recheck `TALK`: Provider job |
| 18 | CLOCK | 10 | `2000-01-01T00:00:09+00:00` | Recheck `TALK`: claim |
| 19 | LEASE_TOKEN | 2 | `demo-lease-000000000000000000002` | Recheck `TALK`: lease |
| 20 | WORKER_ID | 2 | `demo-worker-00000002` | Recheck `TALK`: claim owner |
| 21 | CLOCK | 11 | `2000-01-01T00:00:10+00:00` | Recheck `TALK`: store proposal |
| 22 | CLOCK | 12 | `2000-01-01T00:00:11+00:00` | Recheck `TALK`: begin finalize |
| 23 | CLOCK | 13 | `2000-01-01T00:00:12+00:00` | Recheck `TALK`: pre-persist lease check |
| 24 | EVENT_ID | 3 | `demo-event-00000003` | Recheck `TALK`: event 1/2 |
| 25 | CLOCK | 14 | `2000-01-01T00:00:13+00:00` | Recheck `TALK`: event 1/2 time |
| 26 | EVENT_ID | 4 | `demo-event-00000004` | Recheck `TALK`: event 2/2 |
| 27 | CLOCK | 15 | `2000-01-01T00:00:14+00:00` | Recheck `TALK`: event 2/2 time |
| 28 | CLOCK | 16 | `2000-01-01T00:00:15+00:00` | Recheck `TALK`: commit job |
| 29 | EVENT_ID | 5 | `demo-event-00000005` | Life `CONTINUE` 1: event 1/1 |
| 30 | CLOCK | 17 | `2000-01-01T00:00:16+00:00` | Life `CONTINUE` 1: event time |
| 31 | EVENT_ID | 6 | `demo-event-00000006` | Life `CONTINUE` 2: event 1/2 |
| 32 | CLOCK | 18 | `2000-01-01T00:00:17+00:00` | Life `CONTINUE` 2: event 1/2 time |
| 33 | EVENT_ID | 7 | `demo-event-00000007` | Life `CONTINUE` 2: event 2/2 |
| 34 | CLOCK | 19 | `2000-01-01T00:00:18+00:00` | Life `CONTINUE` 2: event 2/2 time |
| 35 | EVENT_ID | 8 | `demo-event-00000008` | Early-strategy `CHOOSE`: event |
| 36 | CLOCK | 20 | `2000-01-01T00:00:19+00:00` | Early-strategy `CHOOSE`: event time |
| 37 | EVENT_ID | 9 | `demo-event-00000009` | Escape `CONTINUE` 1: event |
| 38 | CLOCK | 21 | `2000-01-01T00:00:20+00:00` | Escape `CONTINUE` 1: event time |
| 39 | EVENT_ID | 10 | `demo-event-00000010` | Escape `CONTINUE` 2: event |
| 40 | CLOCK | 22 | `2000-01-01T00:00:21+00:00` | Escape `CONTINUE` 2: event time |
| 41 | EVENT_ID | 11 | `demo-event-00000011` | Investigation `CONTINUE`: event |
| 42 | CLOCK | 23 | `2000-01-01T00:00:22+00:00` | Investigation `CONTINUE`: event time |
| 43 | EVENT_ID | 12 | `demo-event-00000012` | Investigation-route `CHOOSE`: event |
| 44 | CLOCK | 24 | `2000-01-01T00:00:23+00:00` | Investigation-route `CHOOSE`: event time |
| 45 | CLOCK | 25 | `2000-01-01T00:00:24+00:00` | Records `EXPLORE`: prepare job |
| 46 | JOB_ID | 3 | `demo-job-00000003` | Records `EXPLORE`: Provider job |
| 47 | CLOCK | 26 | `2000-01-01T00:00:25+00:00` | Records `EXPLORE`: claim |
| 48 | LEASE_TOKEN | 3 | `demo-lease-000000000000000000003` | Records `EXPLORE`: lease |
| 49 | WORKER_ID | 3 | `demo-worker-00000003` | Records `EXPLORE`: claim owner |
| 50 | CLOCK | 27 | `2000-01-01T00:00:26+00:00` | Records `EXPLORE`: store proposal |
| 51 | CLOCK | 28 | `2000-01-01T00:00:27+00:00` | Records `EXPLORE`: begin finalize |
| 52 | CLOCK | 29 | `2000-01-01T00:00:28+00:00` | Records `EXPLORE`: pre-persist lease check |
| 53 | EVENT_ID | 13 | `demo-event-00000013` | Records `EXPLORE`: event 1/1 |
| 54 | CLOCK | 30 | `2000-01-01T00:00:29+00:00` | Records `EXPLORE`: event time |
| 55 | CLOCK | 31 | `2000-01-01T00:00:30+00:00` | Records `EXPLORE`: commit job |
| 56 | CLOCK | 32 | `2000-01-01T00:00:31+00:00` | Audit `EXPLORE`: prepare job |
| 57 | JOB_ID | 4 | `demo-job-00000004` | Audit `EXPLORE`: Provider job |
| 58 | CLOCK | 33 | `2000-01-01T00:00:32+00:00` | Audit `EXPLORE`: claim |
| 59 | LEASE_TOKEN | 4 | `demo-lease-000000000000000000004` | Audit `EXPLORE`: lease |
| 60 | WORKER_ID | 4 | `demo-worker-00000004` | Audit `EXPLORE`: claim owner |
| 61 | CLOCK | 34 | `2000-01-01T00:00:33+00:00` | Audit `EXPLORE`: store proposal |
| 62 | CLOCK | 35 | `2000-01-01T00:00:34+00:00` | Audit `EXPLORE`: begin finalize |
| 63 | CLOCK | 36 | `2000-01-01T00:00:35+00:00` | Audit `EXPLORE`: pre-persist lease check |
| 64 | EVENT_ID | 14 | `demo-event-00000014` | Audit `EXPLORE`: event 1/5 |
| 65 | CLOCK | 37 | `2000-01-01T00:00:36+00:00` | Audit `EXPLORE`: event 1/5 time |
| 66 | EVENT_ID | 15 | `demo-event-00000015` | Audit `EXPLORE`: event 2/5 |
| 67 | CLOCK | 38 | `2000-01-01T00:00:37+00:00` | Audit `EXPLORE`: event 2/5 time |
| 68 | EVENT_ID | 16 | `demo-event-00000016` | Audit `EXPLORE`: event 3/5 |
| 69 | CLOCK | 39 | `2000-01-01T00:00:38+00:00` | Audit `EXPLORE`: event 3/5 time |
| 70 | EVENT_ID | 17 | `demo-event-00000017` | Audit `EXPLORE`: event 4/5 |
| 71 | CLOCK | 40 | `2000-01-01T00:00:39+00:00` | Audit `EXPLORE`: event 4/5 time |
| 72 | EVENT_ID | 18 | `demo-event-00000018` | Audit `EXPLORE`: event 5/5 |
| 73 | CLOCK | 41 | `2000-01-01T00:00:40+00:00` | Audit `EXPLORE`: event 5/5 time |
| 74 | CLOCK | 42 | `2000-01-01T00:00:41+00:00` | Audit `EXPLORE`: commit job |
| 75 | EVENT_ID | 19 | `demo-event-00000019` | Investigation-evidence `CHOOSE`: event |
| 76 | CLOCK | 43 | `2000-01-01T00:00:42+00:00` | Investigation-evidence `CHOOSE`: event time |
| 77 | CLOCK | 44 | `2000-01-01T00:00:43+00:00` | Patient `OBSERVE`: prepare job |
| 78 | JOB_ID | 5 | `demo-job-00000005` | Patient `OBSERVE`: Provider job |
| 79 | CLOCK | 45 | `2000-01-01T00:00:44+00:00` | Patient `OBSERVE`: claim |
| 80 | LEASE_TOKEN | 5 | `demo-lease-000000000000000000005` | Patient `OBSERVE`: lease |
| 81 | WORKER_ID | 5 | `demo-worker-00000005` | Patient `OBSERVE`: claim owner |
| 82 | CLOCK | 46 | `2000-01-01T00:00:45+00:00` | Patient `OBSERVE`: store proposal |
| 83 | CLOCK | 47 | `2000-01-01T00:00:46+00:00` | Patient `OBSERVE`: begin finalize |
| 84 | CLOCK | 48 | `2000-01-01T00:00:47+00:00` | Patient `OBSERVE`: pre-persist lease check |
| 85 | EVENT_ID | 20 | `demo-event-00000020` | Patient `OBSERVE`: event 1/3 |
| 86 | CLOCK | 49 | `2000-01-01T00:00:48+00:00` | Patient `OBSERVE`: event 1/3 time |
| 87 | EVENT_ID | 21 | `demo-event-00000021` | Patient `OBSERVE`: event 2/3 |
| 88 | CLOCK | 50 | `2000-01-01T00:00:49+00:00` | Patient `OBSERVE`: event 2/3 time |
| 89 | EVENT_ID | 22 | `demo-event-00000022` | Patient `OBSERVE`: event 3/3 |
| 90 | CLOCK | 51 | `2000-01-01T00:00:50+00:00` | Patient `OBSERVE`: event 3/3 time |
| 91 | CLOCK | 52 | `2000-01-01T00:00:51+00:00` | Patient `OBSERVE`: commit job |
| 92 | EVENT_ID | 23 | `demo-event-00000023` | Truth `CONTINUE` 1: event |
| 93 | CLOCK | 53 | `2000-01-01T00:00:52+00:00` | Truth `CONTINUE` 1: event time |
| 94 | EVENT_ID | 24 | `demo-event-00000024` | Truth `CONTINUE` 2: event |
| 95 | CLOCK | 54 | `2000-01-01T00:00:53+00:00` | Truth `CONTINUE` 2: event time |
| 96 | EVENT_ID | 25 | `demo-event-00000025` | Core `CHOOSE` 1: event |
| 97 | CLOCK | 55 | `2000-01-01T00:00:54+00:00` | Core `CHOOSE` 1: event time |
| 98 | EVENT_ID | 26 | `demo-event-00000026` | Core `CHOOSE` 2: event |
| 99 | CLOCK | 56 | `2000-01-01T00:00:55+00:00` | Core `CHOOSE` 2: event time |
| 100 | EVENT_ID | 27 | `demo-event-00000027` | Core `CHOOSE` 3: event |
| 101 | CLOCK | 57 | `2000-01-01T00:00:56+00:00` | Core `CHOOSE` 3: event time |
| 102 | EVENT_ID | 28 | `demo-event-00000028` | Core `CHOOSE` 4 settlement: event |
| 103 | CLOCK | 58 | `2000-01-01T00:00:57+00:00` | Core `CHOOSE` 4 settlement: event time |
| 104 | CLOCK | 59 | `2000-01-01T00:00:58+00:00` | Core `CHOOSE` 4: local-template job time |
| 105 | JOB_ID | 6 | `demo-job-00000006` | Core `CHOOSE` 4: local-template settlement job |

For each child, the parsed 105-record generator sequence must equal this table
exactly and the two parsed child sequences must equal one another exactly. No
caller-identity normalization applies to trace data, and no API-private category
may be removed or ignored. HTTP status/body comparison and both trace
comparisons are conjunctive: all must pass. An extra, missing, reordered or
different generator call fails even if every HTTP response matches.

Every clean child starts at global ordinal 1, category ordinal 1 and the first
values above. The parent creates both pipes before starting that child, and each
child builds new storage, generator objects and trace state after process start.
The second replay cannot reuse the first child's app, module state, handles or
objects. The two processes retain `PYTHONHASHSEED=1` and `2`, respectively, and
remain clean single-worker OS processes.

The Demo clock is logical and deterministic; it does not read wall-clock time
for player-visible or persisted Demo values. The provider metadata is fixed:
`provider=deterministic-demo`, `model=deterministic-demo-v1`, no request ID,
`finish_reason=stop`, `attempts=1`, `latency_ms=0`, and no invented usage.

### Caller-owned identity whitelist and browser equivalence

The Web client continues to generate cryptographically opaque creation,
turn and request identities. Phase 3.2 must not make those identities
predictable, reuse them, or change their Phase 3.1c persistence semantics.
Consequently, two ordinary browser replays may differ only in these
caller-owned opaque identities and their exact direct echoes:

| Identity category | Request JSON path that establishes the value | Response JSON paths eligible for replacement | Required correspondence |
| --- | --- | --- | --- |
| Session-create request identity | `POST /v1/sessions`: `$.client_request_id` | None | Recorded only to preserve occurrence/equality relationships; the creation response does not echo it. |
| Action turn identity | `POST /v1/sessions/{session_id}/actions`: `$.turn_id` | None | One caller value per submitted action; no public response field directly echoes it. |
| Action request identity | `POST /v1/sessions/{session_id}/actions`: `$.client_request_id` | Action response `$.client_request_id`; request-status response `$.client_request_id`; and, only for `COMMITTED`, `$.response.client_request_id` | Every eligible response value must exactly equal the action identity observed for that request. The request-status URL path reuses that already observed value but adds no JSON identity category. |

No other path is whitelisted. In particular, URL/response `session_id` is a
server-generated Demo ID; `decision_id`, `choice_id`, target/item/skill IDs,
event/frame/fact IDs, clocks, state/status fields, prose, action payload,
memory and ending values are never normalized.

The comparison algorithm is frozen as follows:

1. Walk requests in replay order and record only the three exact request paths
   above. Maintain a global one-to-one raw-value-to-token map plus category
   membership. The first occurrence assigns a category-labelled ordinal token,
   such as `<CREATE_REQUEST:1>`, `<TURN:1>` or `<ACTION_REQUEST:1>`. Tokens are
   strings deliberately outside the current SafeId grammar, so no caller value
   can collide with them. A raw value later observed in another category keeps
   the same token so cross-category equality is preserved.
2. Walk response JSON without deleting fields or objects. Replace a scalar only
   at an exact whitelisted response path, only when it is a JSON string exactly
   equal to the caller value observed for that request and category. Never
   match by a broad field name or by substring.
3. Preserve field presence, JSON type, array order, occurrence count,
   repetitions and all equality/inequality relationships. Distinct raw input
   identities have distinct tokens and can never collapse to one token.
4. Canonically serialize and compare every response. A value mismatch at an
   unlisted path, an unmatched echo, a missing/extra field or occurrence, or a
   type/order change fails the replay.

An independent acceptance runs the same player behavior against two separate
fresh Demo backend processes while deliberately using different caller
identity sequences. After the algorithm above, all canonical gameplay
responses must be identical.

“Same player text” is not a new normalization rule. The existing Web request
contract `playerActionTextSchema` in `web/src/api/schemas.ts` trims action text;
the Python `StrictApiModel` in `src/deviation_protocol/api/schemas.py` applies
Pydantic `str_strip_whitespace`; and the Provider boundary
`NarrativePlayerIntent.normalize_player_text` in
`src/deviation_protocol/application/narrative_models.py` applies NFC,
collapses `\s+` to one space and strips. Browser-equivalence fixtures must use
identical parsed action fields at the relevant existing boundary. Phase 3.2
adds no further text normalization.

Determinism does not cover concurrent request scheduling, a different request
order, a non-empty Demo process, a changed content version, different player
input, OS process IDs, ports, logs, or Vite build metadata. No random choice,
wall clock, external response or unordered collection iteration may influence
the gameplay result.

## D. Demo-mode activation and isolation

The Demo is selected by composition root, not by a request field and not by a
silent fallback:

- The backend entry point is the dedicated future module
  `deviation_protocol.api.demo:app`, built by injecting Demo services into the
  existing `create_app(services=...)` factory.
- `deviation_protocol.api.main:app` remains the normal MySQL/DeepSeek
  composition. Missing DeepSeek configuration must continue to fail Narrative
  work; it must never select the deterministic Provider.
- No public API request, header, cookie, query parameter, scenario value or
  player input can change Provider or storage mode.
- `scripts/start-demo.ps1` launches only the dedicated Demo entry point and sets
  Vite mode `deterministic-demo` plus process environment
  `VITE_APP_MODE=deterministic-demo` for the Web child so the non-production,
  ephemeral label is visible. This client value is presentation only and
  grants no authority.
- The script creates sanitized child environments that omit
  `DATABASE_URL`, `TEST_DATABASE_URL`, `DEEPSEEK_API_KEY`, all other
  `DEEPSEEK_*` settings, and `RUN_LIVE_DEEPSEEK_TEST`, without reading or
  printing their values. Environment sanitization alone is not evidence that
  Vite did not read dotenv files.
- Phase 3.2b changes `web/vite.config.ts` so only Vite mode
  `deterministic-demo` resolves `envDir: false`: the planned conditional is
  equivalent to `envDir: mode === "deterministic-demo" ? false : undefined`.
  Vite 8.1.5's current contract types `envDir` as `string | false`, and its
  `getEnvFilesForMode` returns no `.env`, `.env.local`, `.env.<mode>` or
  `.env.<mode>.local` paths when false. All other modes retain the current
  default env-directory behavior.
- Both listeners bind to loopback only. Non-loopback binding, CORS expansion,
  TLS and hosting are not part of this phase.

Direct import and tests of the Demo composition must likewise avoid
`build_default_services()`, `create_engine()`, `DeepSeekSettings`,
`DeepSeekNarrativeProvider` and HTTP transports.

## E. Scope

### In scope

- A generic, versioned deterministic implementation of the existing
  `NarrativeProvider` Protocol.
- A demo-only, process-local transactional implementation of the existing
  UnitOfWork and Repository ports.
- A dedicated Demo API composition that reuses the current services,
  orchestrators, policies, catalogs, public routes and fixed development
  principal.
- One existing `death_certificate` scenario and the complete success route in
  section H.
- The one-command PowerShell launcher and concise local walkthrough.
- The separate bounded `scripts/smoke-demo.ps1` smoke and the Demo-only Vite
  `envDir: false` configuration/sentinel proof.
- A Web label that explicitly states local-only, temporary and non-production
  status.
- Automated tests for Provider purity, storage atomicity, public API
  determinism, the complete Web loop, mode isolation, denied external I/O and
  safe failure boundaries.
- Preservation tests for the Phase 3.1c same-tab and no-replay contract.

### Planned implementation file prediction

This is a future allowlist prediction, not evidence that files exist or were
changed in this planning repair. Phase 3.2a is expected to add the Demo
composition/provider/store under `src/deviation_protocol/`, their focused unit
tests, `tests/e2e/test_demo_cross_process_replay.py`, and its test-only
`tests/e2e/support/demo_replay_child.py` IPC/bootstrap support. Phase 3.2b is
expected to modify `web/vite.config.ts`, `web/package.json`, the minimum
existing Web presentation/test files, add
`web/vitest.scenario-validator.config.ts` and
`web/tools/validate-public-scenario-catalog.validation.ts`, and add
`scripts/start-demo.ps1` plus `scripts/smoke-demo.ps1` and their focused script
tests. The future `scripts/smoke-demo.ps1` owns the fail-closed Windows
`cmd.exe` resolution and unique `npm.cmd` resolution, bounded validator process
and exit-code propagation specified below; these are planned behavior, not
current files or capability. The helper imports the existing public Zod schema;
it does not add or copy a runtime contract. No API DTO/schema, Provider
Protocol, ORM or migration file is predicted to change.

### Out of scope

- A real LLM or external Provider integration, changes to DeepSeek behavior,
  prompt quality evaluation, or model-selection UI.
- Production deployment, domains, HTTPS, public CORS, containers, installers,
  services, multi-worker or multi-instance coordination, scalability or SLA.
- Guest identity, authentication, authorization, user isolation or abuse
  controls. The fixed `demo-dev-only` principal remains unsafe outside local
  development.
- Durable Demo persistence, SQLite, files, browser restart recovery, backend
  restart recovery, cross-tab recovery, general reconnection or scenario
  replay.
- Changes to the frozen Phase 3.1c `sessionStorage`, confirmed-202,
  authoritative-View, stale-View or no-action-replay semantics.
- External-playtest visual polish, broad accessibility redesign, animation,
  action/chat history or telemetry.
- New story content, memory systems, `scenario_run_id`, `DeviationEvaluator`,
  combat or other deferred gameplay systems.
- ORM, database schema or Alembic changes; seed rows, real user data, secrets,
  and production operational configuration.

## F. API, Provider, persistence and Web boundaries

### Public API

All existing paths, methods, status codes, DTOs, Zod schemas, OpenAPI models,
identity checks and action-identity rules remain unchanged. Phase 3.2 adds no
Demo endpoint, reset endpoint, state-write shortcut, mode field, Provider field
or internal debug projection. The Web continues to read only
`GET /v1/scenarios`, `POST /v1/sessions`, `GET /view`, `POST /actions`, and the
existing request-status endpoint.

### Provider

The Demo Provider is infrastructure implementing the existing application
Protocol. It is a pure function of a fully validated `NarrativeRequest` and has
no scenario-ID or story-copy branches. Version 1:

1. selects the first outcome candidate in the server-provided stable tuple;
2. selects that candidate's first allowed result;
3. includes exactly the first allowed entity ID when one exists, otherwise no
   entity reference;
4. emits no `npc_utterances` and no `continuity_notes`;
5. builds neutral candidate prose from a fixed Demo sentence and the candidate
   `safe_description`, repeating and code-point-clamping it deterministically
   to the Frame's declared length bounds; and
6. emits only the fixed metadata in section C.

The public orchestrator continues to own the pre-Provider no-outcome boundary;
it must not create or call a Provider when `allowed_narrative_outcomes` is
empty. Once a job has a non-empty validated request, the Demo Provider either
returns one strict proposal or raises exactly
`NarrativeProposalRejectedError`; it never substitutes another exception,
falls through to DeepSeek or chooses a later fallback. The proposal remains
untrusted and non-authoritative; the existing validator, outcome policy,
issuer and StoryDirector retain all authority. Current production outcome
templates, not Demo candidate prose, remain the accepted public narrative
where fixed semantics apply.

### Frozen deterministic failure outcomes

| Failure and exact trigger | Existing exception | Initial public result | Request-status result | Same identity and persistence result |
| --- | --- | --- | --- | --- |
| No legal outcome candidate before Provider call: `allowed_narrative_outcomes(...)` returns the empty tuple. | `NarrativeOutcomeUnavailableError` | HTTP 409, `error.error_code=NARRATIVE_OUTCOME_UNAVAILABLE`. | No job or turn-request record exists; status lookup is HTTP 404, `NARRATIVE_REQUEST_NOT_FOUND`, rather than a fabricated terminal status. | No automatic retry. A repeated POST with the same identity deterministically repeats the 409 with zero Provider calls; state, events, memory, response and version remain unchanged. |
| Length construction is impossible: the fixed repetition/clamping constructor cannot produce a strict payload whose text satisfies both the current `NarrativeFrame.min_length/max_length` and `NarrativeProposalPayload` bounds. | `NarrativeProposalRejectedError` | HTTP 503, `error.error_code=NARRATIVE_PROPOSAL_REJECTED`. | HTTP 200 with `status=FAILED`, `client_action=DO_NOT_RETRY`, `error_code=NARRATIVE_REQUEST_FAILED`, `retry_after_seconds=null`, `response=null`. | Retry is forbidden; a repeated POST with the same identity returns the same 503/code without a Provider call. The durable job remains `FAILED_TERMINAL` with internal `NARRATIVE_PROPOSAL_REJECTED`; no turn response exists. |
| Reference construction is impossible: the selected first candidate/result cannot produce references that are simultaneously a subset of its `allowed_entity_ids`, the proposal's top-level references and the current validator's public reference allowlist. | `NarrativeProposalRejectedError` | HTTP 503, `error.error_code=NARRATIVE_PROPOSAL_REJECTED`. | HTTP 200 with the same exact `FAILED`/`DO_NOT_RETRY` shape above. | The same durable terminal/idempotent result applies; there is no Provider retry or fallback. |

Every row is deterministic across fresh processes and repeated execution. All
rows require zero DeepSeek/external Provider calls and zero fallback. “Zero
partial writes” means no gameplay state, snapshot, accepted text, event,
memory, turn response or version mutation. For failures after job preparation,
the expected idempotency evidence is the atomically committed terminal job;
that record is not a partial gameplay write. Any failed UoW transition rolls
back as a unit, and the last committed View remains unchanged.

### Persistence

The Demo needs server-side persistence only for the backend process lifetime.
The new adapter implements all current session, snapshot, event receipt, turn
request and narrative-job ports with detached copies, per-session locks,
compare-and-swap behavior, idempotency uniqueness, fenced job replacement and
one atomic commit boundary. A UoW stages changes on isolated copies; commit
publishes the whole set under a commit lock, and exit/rollback publishes none.
Repository methods never commit.

The existing test MemoryStore is an oracle, not code to import from `tests/`.
Runtime code must live under an explicitly Demo-named infrastructure boundary
and keep dependencies directed toward application/domain. It is not a SQLite
fallback, does not implement the normal application entry point, writes no
disk file and never reads `DATABASE_URL`. The production SQLAlchemy/MySQL
adapter remains unchanged.

No database content, fixture row, seed command, ORM model or migration is
needed. Deterministic generator state is created in memory by the dedicated
composition root and reset only by restarting that process; no public reset
route is added.

### Web

The existing `PublicApiClient`, DTO schemas, action forms, foreground lock,
polling, authoritative View replacement and `sessionStorage` module remain the
functional boundary. Phase 3.2b adds only the explicit Demo presentation,
complete-path regression and Vite mode isolation. `web/vite.config.ts` (or its
equivalent) must select `envDir: false` only for Demo mode so Vite reads none of
`.env`, `.env.local`, `.env.deterministic-demo` or
`.env.deterministic-demo.local`; ordinary production/development semantics are
unchanged. The UI must not inspect Provider metadata or derive Demo mode from
narrative text.

The bounded smoke creates exactly one unique `VITE_*` sentinel in
`web/.env.deterministic-demo.local` using an atomic create-new operation
(PowerShell/.NET `FileMode.CreateNew` or equivalent). If that path already
exists it fails closed without reading, printing, copying or overwriting it. In
a `finally` block it removes only the sentinel file it created. It starts Demo
Web and proves the unique value is absent from resolved
Vite configuration, served client modules, the rendered page and observable
proxy/API responses. It also creates one unique script-owned temporary
workspace, writes the Demo-mode Vite build only to a build subdirectory there,
proves the sentinel is absent from that client bundle, and deletes the workspace
in `finally`; it never uses or overwrites the normal `web/dist`. The same
workspace owns the public-scenario response file described below. It never
reads, copies or prints any real repository dotenv content.

### Bounded startup/proxy smoke

Phase 3.2b adds a separate finite entry point:

```powershell
pwsh -NoProfile -File .\scripts\smoke-demo.ps1
```

`scripts/smoke-demo.ps1` defaults `-TimeoutSeconds` to 60 and accepts an
explicit integer override in the bounded range 10 through 300. It is distinct
from the Ctrl+C long-running `scripts/start-demo.ps1`. The smoke automatically
starts one Demo backend and one Demo Vite child, waits under the single total
timeout, then requests the actual public scenarios API through
`http://127.0.0.1:<web-port>/api/v1/scenarios`, never directly from the backend.
It must verify HTTP 200, a JSON response body, full validation by the current
`publicScenarioCatalogSchema` from `web/src/api/schemas.ts`, the exact Demo-mode
label on the Web page, and the dotenv sentinel absence described above. Merely
parsing JSON, checking the top-level type, checking for `scenarios`, or checking
for a non-empty array is insufficient. Direct schema reuse validates every
current nested `publicScenarioDescriptionSchema` and
`publicPlayableCharacterSchema` field, type, collection bound and the default-
character-membership refinement; the smoke must not replace it with a weaker
PowerShell subset.

Phase 3.2b adds the future Web-owned files
`web/vitest.scenario-validator.config.ts` and
`web/tools/validate-public-scenario-catalog.validation.ts`, plus the
`validate:scenario-catalog` script in `web/package.json`. The dedicated Vitest
config uses Node environment, sets `envDir: false`, and includes only that
validation module. The module registers exactly one Vitest test, imports
`publicScenarioCatalogSchema` directly from
`web/src/api/schemas.ts`, reads the proxy response from the absolute path in
`DEVIATION_DEMO_SCENARIO_RESPONSE_FILE`, decodes with
`new TextDecoder("utf-8", { fatal: true })`, performs `JSON.parse`, and requires
`publicScenarioCatalogSchema.safeParse(parsed).success === true`. A missing or
invalid path, invalid UTF-8, invalid JSON or failed Zod result fails the Vitest
run without printing the response body.

The smoke writes the exact proxy response bytes to a unique create-new file
inside its already script-owned temporary workspace. The file path is absolute
and the smoke passes it only as
`ProcessStartInfo.Environment["DEVIATION_DEMO_SCENARIO_RESPONSE_FILE"]`; neither
the response bytes nor that path is present in an executable name, argument or
shell command. The package script runs
`vitest run --config vitest.scenario-validator.config.ts` against the existing
`web/node_modules`. The smoke performs no `npx`, package download, dependency
installation or network access. This helper changes no runtime schema and
cannot drift into a second contract because it imports the production Web
schema object itself.

#### Frozen Windows validator process

The validator has exactly one Windows launch path. The smoke reads `ComSpec`
from the current process with
`[Environment]::GetEnvironmentVariable("ComSpec", [EnvironmentVariableTarget]::Process)`
and has no fallback to a bare
`cmd.exe`, a shell association, PowerShell or `node.exe`. Before use, the value
must be non-null, non-empty and non-whitespace; satisfy
`[IO.Path]::IsPathFullyQualified`; resolve through a literal `FileInfo` lookup
to an existing leaf; and have a case-insensitive leaf name of exactly
`cmd.exe`. Any read, normalization or validation exception fails closed. The
validated `FileInfo.FullName` is the absolute value assigned to
`ProcessStartInfo.FileName`.

Before creating the validator process, the smoke enumerates all Application
results for exactly `npm.cmd` with this frozen PowerShell command-discovery
call, not a constructed shell string:

```powershell
$npmCommands = @(
    Get-Command -Name "npm.cmd" -CommandType Application -All -ErrorAction Stop
)
```

The smoke must require `$npmCommands.Count -eq 1` before selecting
`$npmCommands[0]`. Zero results, multiple results or any resolution exception
fails closed. Only that unique result continues to the existing checks: it must
report `CommandType=Application`, expose a non-empty fully qualified path,
resolve through a literal `FileInfo` lookup to an existing leaf, have extension
`.cmd`, and have a case-insensitive leaf name of exactly `npm.cmd`. A
non-Application, relative, non-file, wrong-suffix or exceptional validation
result also fails closed. That unique result's absolute `FileInfo.FullName` is
retained as `$npmCmdPath`; the child invokes that exact absolute file and never
performs a second PATH lookup. Thus preflight cannot validate one shim and then
run another because PATH changed.

The only dynamic command-string component is that validated `$npmCmdPath`.
Although Windows spaces are allowed and the path is always quoted, the smoke
also rejects any control character or any of `"`, `%`, `!`, `^`, `&`, `|`,
`<`, `>`, `(` or `)` in the resolved path. This fail-closed restriction
prevents quote termination, environment or delayed expansion, escaping,
redirection, command chaining and grouping. The operation following the path
is the immutable literal ` run validate:scenario-catalog`; no response data,
temporary path, environment value or other caller-controlled value can enter
it.

The `ProcessStartInfo` fields are frozen as follows:

- `FileName` is the validated absolute `cmd.exe` path above;
- `UseShellExecute` is `false`;
- `WorkingDirectory` is the `DirectoryInfo.FullName` obtained by applying
  `[IO.Path]::GetFullPath` to `Join-Path $PSScriptRoot "..\web"`, after
  requiring that result to be fully qualified and an existing directory;
- `Environment["DEVIATION_DEMO_SCENARIO_RESPONSE_FILE"]` is the script-owned
  absolute response-file path;
- `RedirectStandardOutput` and `RedirectStandardError` are `true`; and
- `Arguments` is constructed exactly as
  `'/d /s /c ""' + $npmCmdPath + '" run validate:scenario-catalog"'`.

The validator invocation is consequently the raw equivalent of:

```text
<absolute cmd.exe> /d /s /c ""<absolute npm.cmd>" run validate:scenario-catalog"
```

`/d` disables `cmd.exe` AutoRun commands, `/s` applies the documented outer-
quote handling, and `/c` executes the fixed command and exits. The outer quote
pair belongs to `/s /c`; the inner pair quotes the absolute `npm.cmd` path,
including when it contains spaces. `ProcessStartInfo.ArgumentList` must remain
empty: on the supported Windows PowerShell/.NET path its argv escaping changes
the embedded quotes required by `cmd.exe /s /c`. `ProcessStartInfo.Arguments`
is therefore the one frozen mechanism, not an implementation-time choice.
`npm.cmd` is interpreted only by this validated `cmd.exe`; it is never assigned
to `FileName`, and neither `UseShellExecute=true` nor PowerShell file
association behavior is permitted.

#### Validator output, exit and cleanup

The parent redirects both validator streams only so it can continuously drain
them. It installs separate asynchronous stdout and stderr handlers before
start, calls `BeginOutputReadLine()` and `BeginErrorReadLine()` immediately
after a successful start, and drains both streams through their EOF signals
while waiting for the process. Non-null stdout lines are relayed to
`[Console]::Out` and stderr lines to `[Console]::Error`; handlers do not use
`Write-Output`, and all incidental .NET return values are discarded. This
preserves real-time diagnostics without adding child text to any PowerShell
function's structured success output. The implementation must not redirect
either stream and then synchronously block in `WaitForExit()` without the
continuous readers.

Stdout and stderr are diagnostics only. They are never parsed or searched to
decide whether schema validation succeeded. After the child has exited and
both redirected streams have reached EOF, the child's `ExitCode` is the sole
validator-success authority. The `/c` string contains exactly the one
`npm.cmd run validate:scenario-catalog` batch invocation and no following
command that could replace its status, so this `cmd.exe` process code is the
propagated package-script/validator code; only `ExitCode=0` succeeds. A
resolution or validation failure, null process result, start exception,
nonzero exit, premature or abnormal exit, inability to observe stream EOF,
inability to wait or obtain `ExitCode`, or expiration of the smoke's remaining
total deadline makes the smoke nonzero.

The smoke records the validator `Process` object only after it successfully
starts. On validator timeout it calls `Kill($true)` only on that still-owned
object, waits for termination and stream EOF, and reaps/disposes it; it never
kills by an unverified discovered PID. The backend and Web retain their
separately frozen ownership rules. Success, validation failure, start failure,
timeout, abnormal exit and all exceptions flow through the same `finally`
cleanup for the create-new response file, owned temporary workspace, sentinel
and every process object actually created. Ownership uncertainty forbids
deletion or termination of an unknown object, and any required cleanup failure
still makes the smoke nonzero.

Overall smoke success returns exit code 0. An unreliable `cmd.exe` or `npm.cmd`
resolution, validator start/timeout/nonzero/ExitCode failure, non-200 response,
invalid UTF-8, invalid JSON, `publicScenarioCatalogSchema` failure, Demo-label,
readiness, proxy, sentinel, cleanup or ownership failure, backend/Web child
early exit, or overall smoke timeout returns nonzero. Before launch, an
occupied required port fails closed. The script records the exact process
objects/PIDs it creates and, on success, failure and timeout, terminates only
its owned backend/Web process trees in `finally`; it never kills a process it
did not create. If process-tree ownership cannot be proved, it fails closed
rather than terminating an unrelated process. `start-demo.ps1` remains only
the manual long-running walkthrough launcher and cannot satisfy this smoke
requirement.

## G. Security and failure handling

- All authority rules in AUTH-001, STATE-001, API-001, SCENE-001, MODEL-001,
  MODEL-002 and PLAY-001 remain active. Deterministic output is still untrusted
  Provider output until the normal policies accept it.
- The Provider and store accept no executable expressions, scripts, dynamic
  imports, arbitrary state payloads or player-selected outcome values.
- A Demo startup must succeed with all database/DeepSeek variables absent. A
  test must deny non-loopback socket access and prove the complete path still
  ends successfully.
- If Provider construction or generation fails, the existing safe public error
  envelope is used. No raw request, candidate, internal ID, stack trace,
  Provider metadata or environment value becomes public.
- If the in-memory UoW fails before commit, state, events, memory, response,
  job and version all remain at the prior committed value. Duplicate request
  and CAS behavior match the existing port contract.
- Demo Narrative handling may normally complete synchronously, but HTTP 202 and
  request-status semantics are not removed or redefined. No failure, reload or
  restart path automatically posts, retries or regenerates an action identity.
- After backend restart, an old Session is missing. The client follows the
  existing 404 invalidation path; it does not reconstruct state or replay the
  last action.
- Startup logs and errors identify the mode as Demo and ephemeral, but never
  print environment values or imply production readiness.

## H. Minimum scenario and complete play path

No new scenario content is required. The frozen path reuses
`death_certificate` / `death-certificate-1.1.0` with
`character.death_certificate.investigator` and follows only current public
affordances:

1. Create the Session and submit `CUSTOM`: `我有规律地移动手指，发出可复核的生命信号`.
2. Submit `TALK`: `请协调员复核我的连续回应和生命体征`.
3. Submit the advertised `CONTINUE` actions until the early strategy decision,
   then select the first displayed choice.
4. Continue through disposal escape to the investigation decision and select
   the first displayed choice, which opens the records route through trusted
   scenario content.
5. In the records room submit `EXPLORE`:
   `沿记录与档案审计路径核对签发时间`.
6. Submit `EXPLORE`: `核对日志时间顺序以及规程反馈`, then select the first
   displayed investigation choice.
7. In the observation level submit `OBSERVE`:
   `复核地下患者的生命体征与连续监测历史`.
8. Submit advertised `CONTINUE` actions through self-fulfilling truth, then
   select the first displayed choice in each of the four rapid core decisions.
9. Read a new authoritative View and verify `scenario_status=ENDED`,
   `ending_status=RESOLVED`, ending `protocol_broken`, completed scenario
   memory, and `action_affordances.mode=ENDED` with no controls.

“Until” in steps 3 and 8 means follow the current authoritative affordance on
each refreshed View; it does not authorize automatic CONTINUE or hard-coded
phase inspection in the Web client. The automated canonical replay records the
exact expected number and order of requests so a content/cadence change fails
review instead of silently changing the Demo.

## I. Test matrix

| Area | Required automated evidence |
| --- | --- |
| Provider purity | Two identical validated requests return identical strict proposals and fixed metadata; no time, randomness, environment, filesystem or transport access; no scenario/content-ID branches. |
| Provider selection/error | Stable first-candidate/first-result/reference behavior and deterministic Unicode-code-point length clamping; every row in the frozen failure table asserts its one exception, HTTP result, status result, terminal/idempotency record, unchanged View/state, zero fallback and zero external Provider calls. |
| Demo composition isolation | Import/build succeeds without database or DeepSeek variables; normal `main:app` does not select Demo; Demo build does not call database engine/settings/DeepSeek constructors or read `.env`. |
| In-memory contract | Initial create/replay conflict, ownership, detached reads, per-session locking, event sequence/receipt binding, turn idempotency, narrative-job CAS/fencing, recent text ordering, rollback and optimistic conflict match current ports. Every mutation has a regression test. |
| Exact cross-process determinism | `tests/e2e/test_demo_cross_process_replay.py` starts two clean, single-worker backend OS processes with `PYTHONHASHSEED=1` and `2`, empty stores and reset generators; each test-only child bootstrap reports actual seam consumption over its own explicitly inherited IPC pipes. The command asserts every canonical HTTP status/body, each strict 105-record trace against the frozen table, both traces against each other, completion/EOF and child/control lifecycle. HTTP or trace failure is fatal; two in-process app/ASGI transports are insufficient. |
| Caller-identity equivalence | A second two-process replay uses different create/action identity sequences, applies only the exact whitelist and bijective token algorithm in section C, and requires every normalized canonical gameplay response to match. Internal Session/event IDs and clocks remain compared. |
| Complete API path | Use only public endpoints from scenario discovery and Session creation through every action and final `/view`; assert the expected Provider call count, clocks, versions, memory, ending, no hidden fields and no post-ending mutation. |
| No external I/O | Complete the public path with non-loopback sockets denied and database/DeepSeek constructors trapped; assert zero calls and no credentials required. Loopback ASGI/test transport is allowed. |
| Web complete loop | One React/MSW regression drives the real App controls from create through all canonical affordance transitions to an ENDED View, verifies the Demo banner, and asserts every POST body comes only from the displayed affordance. |
| Vite dotenv isolation | Demo mode resolves `envDir: false` while ordinary modes retain current behavior. The fail-closed sentinel acceptance proves a unique `VITE_*` value in the smoke-created `.env.deterministic-demo.local` reaches neither Vite configuration, client modules/bundle, page nor observable response, and cleanup removes only that file. |
| Startup/proxy | `pwsh -NoProfile -File .\scripts\smoke-demo.ps1` starts its own sanitized backend/Web children, enforces the 60-second default total timeout, reaches the scenarios API only through the Vite proxy, requires HTTP 200 and exact response bytes in an owned create-new file, and passes only that absolute path through the validator environment. On Windows it fail-closed resolves an absolute `cmd.exe` from process `ComSpec`, enumerates all Application `npm.cmd` results and requires `$npmCommands.Count -eq 1`; zero, multiple or exceptional resolutions are fatal. It then starts exactly that unique validated absolute `FileInfo.FullName` through `cmd.exe /d /s /c` with the frozen `Arguments`, absolute Web working directory and no dynamic response data in the command. Asynchronous handlers continuously drain diagnostic stdout/stderr; only validator `ExitCode=0` proves direct `publicScenarioCatalogSchema` success. Invalid UTF-8/JSON/schema, command resolution/start/timeout/nonzero/ExitCode failure, label/sentinel/lifecycle failure or owned cleanup failure is nonzero, and timeout termination is limited to process trees the smoke created. |
| Recovery preservation | Existing Phase 3.1c suite remains unchanged and passing; added coverage proves same-tab reload works while the Demo process lives and backend restart produces safe 404 invalidation with zero action POSTs. |
| Failure boundary | Provider failure, malformed public input, stale/duplicate identities, storage rollback and ended-session action rejection keep the last committed View/state and expose only existing public errors. |
| Mode labeling | Demo launch always shows local-only/temporary/non-production wording; normal Web builds do not falsely claim the deterministic Provider is active. |

The Web full-loop test may use MSW because the cross-process public-HTTP replay
separately proves backend behavior. Phase 3.2 does not add Playwright or another
browser automation framework. The startup/proxy smoke plus the frozen manual
walkthrough are the integration evidence between those two automated
boundaries.

## J. Completion conditions

Phase 3.2 may be marked complete only when all of the following are true:

1. Phase 3.2a is implemented, verified and independently approved before Phase
   3.2b can be claimed complete; 3.2b is then separately implemented, verified
   and independently approved. An unapproved 3.2a cannot run in parallel with
   a 3.2b completion claim.
2. The single launch command works from a clean supported checkout with
   existing dependencies and no database/DeepSeek settings, key or secret.
3. The dedicated Demo composition is the only way to select Demo Provider and
   storage; the normal application never falls back to either.
4. The canonical browser walkthrough reaches the frozen RESOLVED ending using
   only current public affordances and authoritative View refreshes.
5. The exact command in section K passes the two independent backend OS-process
   replays, including different fixed hash seeds, per-response canonical
   comparison, caller-identity whitelist acceptance, and each child's actual
   test-only IPC trace. Each trace exactly matches the frozen 105-record table,
   both traces match one another, and completion/EOF/control/child lifecycle is
   valid. Any HTTP, trace or lifecycle difference is fatal. Two apps in one
   Python process do not satisfy it.
6. Automated evidence proves zero database, DeepSeek and non-loopback network
   access across the core path.
7. Transaction, idempotency, ownership, authority, hidden-data and rollback
   boundaries remain enforced in the in-memory adapter.
8. The Web unmistakably identifies local, temporary, non-production Demo mode.
9. Demo Vite uses `envDir: false`, the fail-closed dotenv sentinel proof passes,
   and ordinary production/development Vite semantics remain unchanged.
10. The exact bounded smoke command in section K passes readiness, HTTP 200 and
    JSON for the public API through the proxy, direct
    `publicScenarioCatalogSchema` validation through the frozen local Vitest
    helper, Demo label, sentinel absence, timeout and owned-process-tree cleanup
    checks. On Windows, this additionally requires the unique fail-closed
    absolute `ComSpec` `cmd.exe` plus all-results Application `npm.cmd`
    discovery with `$npmCommands.Count -eq 1`; zero, multiple or exceptional
    resolutions are fatal. The exact `cmd.exe /d /s /c` `Arguments` command
    above must then use that unique result's validated absolute
    `FileInfo.FullName`, with continuously drained validator diagnostics and a
    retrievable validator `ExitCode=0`; the long-running launcher is not used as
    smoke.
11. Same-tab recovery and every no-replay rule from Phase 3.1c remain unchanged
   and passing.
12. No scenario content, public API/DTO/schema, ORM model, database schema or
    Alembic migration changes are present.
13. The commands in section K pass, the manual walkthrough is recorded as
    successful, and an independent read-only audit returns `APPROVED` with no
    unresolved Critical, Major or Minor findings.

## K. Verification commands for the future implementation

Normal implementation and review use no live Provider or MySQL. From the
repository root:

```powershell
.\scripts\verify.ps1 -Mode Offline

.\.venv\Scripts\python.exe -m pytest -q tests/e2e/test_demo_cross_process_replay.py

pwsh -NoProfile -File .\scripts\smoke-demo.ps1

Set-Location .\web
npm run lint
npm run typecheck
npm run test:run
npm run build
Set-Location ..

git diff --check
git status --short
git diff --name-only
git diff --cached --name-only
```

The cross-process test above is the unique executable canonical replay command;
it must spawn the two backend OS processes itself and return nonzero for any
HTTP status/canonical JSON difference, either child trace differing from the
frozen sequence, the child traces differing from one another, malformed or
incomplete trace data, or child/IPC lifecycle failure. The smoke command above
is the unique bounded startup/proxy/sentinel/schema-validation command. On
Windows it must use the frozen absolute `ComSpec` `cmd.exe`, enumerate all
Application `npm.cmd` results, require `$npmCommands.Count -eq 1`, and use only
that result's validated absolute `FileInfo.FullName` in the raw `/d /s /c`
`Arguments`; it never performs another PATH lookup. The absolute Web working
directory, response-file environment entry, asynchronous stdout/stderr drains
and validator `ExitCode` authority remain as described above. It returns
nonzero for zero, multiple or exceptional `npm.cmd` resolution, any other
`cmd.exe`/`npm.cmd` validation failure, validator
start/timeout/nonzero/ExitCode, non-200, invalid UTF-8, non-JSON,
`publicScenarioCatalogSchema`, helper, label, sentinel, ownership, cleanup,
early-child or overall-timeout failures. The reviewer then runs the documented
manual path separately with the long-running launcher:

```powershell
pwsh -NoProfile -File .\scripts\start-demo.ps1
```

No live DeepSeek command, `DATABASE_URL`, `TEST_DATABASE_URL`, online Alembic
upgrade or MySQL verification is required for this phase. Offline verification
must still run compileall, unit/integration tests that do not require MySQL,
dependency checks, offline Alembic heads/history and Git checks as currently
defined by the repository workflow.

## L. Explicitly deferred

- Any production or remotely reachable Provider mode.
- Durable Demo data, reset/admin endpoints, shared sessions, multiple users,
  multi-process storage and external playtest hosting.
- Authentication, authorization, abuse prevention, privacy controls and real
  user-data handling.
- General reconnection, cross-tab/browser-restart/backend-restart recovery and
  changes to confirmed-pending recovery.
- Browser automation framework adoption, external-playtest UI polish,
  telemetry, accessibility redesign and distribution packaging.
- More scenarios, new plot/content, scenario replay, memory rebuild/compaction,
  cross-scenario NPC identity, `DeviationEvaluator`, combat, worker/queue and
  distributed orchestration.
- Performance, load, scalability, availability and SLA claims.

## M. Guardrail impact

Guardrail impact: **None**. This planning task confirms no new defect and does
not add or update a reusable guardrail. Future implementation is governed by
existing ENV-001, ENV-002, DB-001, AUTH-001, STATE-001, API-001, SCENE-001,
MODEL-001, MODEL-002 and PLAY-001. Any confirmed implementation defect that
creates or changes a reusable rule must update the matching guardrail and add a
regression in that implementation change.
