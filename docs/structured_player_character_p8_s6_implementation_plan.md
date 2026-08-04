# Structured Player Character P8-S6 Cross-surface Evidence and Final Phase 8 Closure Implementation Plan

Status: **Implementation plan approved and frozen. The exact pre-freeze
candidate was independently reviewed and approved. P8-S6 has not begun, no
P8-S6 closure evidence has been collected, and Phase 8 remains incomplete.**

Task identity:
`STRUCTURED_PLAYER_CHARACTER_P8_S6_IMPLEMENTATION_PLAN_AUTHORING`.

Approval-record task identity:
`STRUCTURED_PLAYER_CHARACTER_P8_S6_IMPLEMENTATION_PLAN_APPROVAL_RECORD_AND_FREEZE`.

Independent-review task identity:
`STRUCTURED_PLAYER_CHARACTER_P8_S6_IMPLEMENTATION_PLAN_POST_E05_CORRECTION_AUTHORITY_CORRECTED_REVIEW`.

The exact independent-review verdict recorded for this plan is:

```text
STRUCTURED_PLAYER_CHARACTER_P8_S6_IMPLEMENTATION_PLAN_REVIEW_APPROVED
```

That verdict applies only to the exact pre-freeze candidate: 49,236 raw bytes,
749 lines, and SHA-256
`e3fe93302b579e59c5e933fac15fad2cbf42073953ed0e9aea1afdccccbb39d0`.
The independent reviewer did not review the later post-freeze complete-file
identity. The only semantic additions or status changes after review are this
approval/freeze record, the status transition above, and the synchronized next
action below. The post-freeze identity is recorded outside this file to avoid a
self-referential checksum.

This document plans only P8-S6. Recording and freezing the independently
approved plan does not execute, stage, commit, publish, or complete P8-S6.
Plan approval is not implementation authorization. P8-S6 remains unstarted, no
P8-S6 closure evidence has been collected, and Phase 8 remains incomplete.

## 1. Controlling repository authority

The later implementation must read these current files completely before any
evidence run or edit:

- [repository instructions](../AGENTS.md);
- [Codex workflow](engineering/codex_workflow.md);
- [engineering guardrails](engineering/guardrails.md);
- [roadmap](../PLANS.md);
- [architecture](architecture.md);
- [public client contract](public_client_contract.md);
- [Run protocol](run_protocol.md);
- [Structured Player Character contract](structured_player_character_contract.md);
- [Structured Player Character implementation plan](structured_player_character_implementation_plan.md);
- [Phase 8 Run/playable-loop plan](structured_player_character_run_playable_loop_plan.md); and
- the published [P8-S5 implementation plan](structured_player_character_p8_s5_implementation_plan.md).

It must also inspect the published P8-S2, P8-S3, and P8-S4 plans and the
accepted P8-S1 through P8-S5 implementation/test surfaces named below. Git
history is supporting evidence only. Current published authority and current
executable behavior control over historical summaries.

Authority precedence is:

1. repository instructions and reusable guardrails;
2. current public, architecture, Run, and Structured Player Character
   contracts;
3. the published Phase 8 plan;
4. the published slice plans for ownership and accepted evidence detail; and
5. history and handoff reports as corroboration.

Any material contradiction at levels 1 through 4 is a stop condition. P8-S6
must not resolve a contradiction by silently choosing a new contract.

## 2. Published baseline and opening preflight

The plan-authoring baseline was `main` at
`acb16774e980a48e7a3d3066f764029be6708398`, subject
`docs(player-character): synchronize P8-S5 publication status`, sole parent
`2ce56a757beed8a3989d38453da3b6d80342ca05`, with local `main` and local
`origin/main` aligned at `0/0`. The worktree and index were clean and this plan
path was absent from the worktree, index, and `HEAD` before creation.

The later P8-S6 execution task must start from the separately reviewed and
user-published plan commit, not from this untracked approved and frozen plan.
Before any evidence run it must confirm:

- repository root `D:\deviation-protocol` and branch `main`;
- `HEAD`, local `main`, and local `origin/main` equal the plan-publication
  identity named by the execution authorization, with `0/0` ahead/behind;
- an empty tracked diff, empty index, no ordinary untracked path, no active Git
  operation, and no relevant Git lock;
- this plan is tracked, its SHA-256 equals the independently reviewed identity,
  and it has not changed after review;
- every earlier frozen slice plan remains byte-identical; and
- no fetch, pull, push, or other remote operation is needed.

The preflight records the literal branch, refs, subject, parent, ahead/behind,
status inventories, plan hash, active-operation paths, and relevant locks. A
mismatch stops before tests or documentation edits. It must not be repaired by
reset, restore, clean, stash, rebase, merge, or another Git mutation.

## 3. Starting-state reconciliation

Current authority establishes:

- P8-S1 eligible-character discovery is complete and published at
  `95ffe4019e2a69967dfae1fee2a1ecba4a628381`;
- P8-S2 atomic internal Run entry is complete and published at
  `70815b181624e5475d2d978bef0db1ed3b22324e`;
- P8-S3 normal public Run-entry composition and its real-MySQL vertical proof
  are complete and published at
  `ac07a5fe267adfb0281ec2658b2fcbd0085f6eb1`;
- P8-S4 deterministic Demo parity is complete and published at
  `187d41ba3035c8d717c2fb2578a805402255d979`, with its publication-status
  synchronization published at
  `60938260b3e63fffbe849a9a6de8863b7f429897`;
- P8-S5's exact three-production/five-test Web implementation is complete and
  published at `2ce56a757beed8a3989d38453da3b6d80342ca05`;
- P8-S5 publication-status synchronization is published at the authoring
  baseline `acb16774e980a48e7a3d3066f764029be6708398`;
- P8-S6 has not begun and Phase 8 remains incomplete; and
- Phase 6, Phase 7, the Structured Player Character programme, and the overall
  project remain incomplete.

P8-S6 closes only Phase 8 after fresh accepted evidence. It does not reopen or
redesign P8-S1 through P8-S5 and does not reinterpret their published commits
as a mutable candidate.

## 4. Purpose, outcome, and fixed boundary

P8-S6 has exactly two responsibilities:

1. rerun and reconcile the accepted cross-surface evidence owned by P8-S1
   through P8-S5; and
2. only after every required result is satisfactory, make the smallest
   materially necessary documentation/status closure within the established
   seven-owner maximum.

P8-S6 adds no production behavior, test, fixture, migration, dependency,
configuration, deployment behavior, generated asset, or duplicate evidence
owner. It changes no public contract or lifecycle protocol. It performs no
deferred Phase 6 or Phase 7 work.

If existing authority or executable behavior requires a non-documentation
change, this plan has reached a stop condition. P8-S6 must report the exact
evidence and return the correction to separately authorized planning and
review; it must not absorb the repair.

## 5. Cross-surface journey being reconciled

P8-S6 proves the already implemented primary journey, without adding a new
journey:

```text
scenario discovery
-> eligible Player Character selection or minimal creation
-> Run entry
-> validated Session recovery storage
-> authoritative Session View loading
-> action submission
-> request-status recovery where required
-> authoritative committed View
-> existing terminal handling
```

The proof preserves all of these established facts:

- the Web client consumes the existing public Player Character create,
  eligible-discovery, and Run-entry contracts;
- the primary Web journey does not call the legacy Session-create route;
- the legacy Session-create route remains available for its existing uses;
- a successful Run entry validates and stores the returned Session recovery
  record before requesting the authoritative View;
- safe same-tab recovery uses View and request-status GETs and never replays
  Run entry;
- the confirmed asynchronous lifecycle is exactly
  `202 -> PENDING -> COMMITTED -> authoritative View`;
- action submission retains the established request identity, idempotency,
  exact-replay, and no-automatic-resubmission semantics;
- uncertain creation, entry, action, or status outcomes retain the approved
  explicit manual-retry boundary;
- one foreground mutation remains single-flight;
- abort/generation checks prevent stale asynchronous completions from storing
  a Session, selecting a character, clearing a newer attempt, committing a
  View, or unlocking newer state;
- terminal Session/View behavior and the still-active, immutably bound Run
  behavior remain intact; and
- URLs and browser storage retain the existing privacy boundary: no Player
  Character, Run, View, error, mutation body, or idempotency key becomes URL or
  durable browser authority, and `sessionStorage` contains only the validated
  Session recovery record.

The real-MySQL vertical and the deterministic Demo/Web journeys are
complementary. One may not be substituted for the other.

## 6. Change and path budgets

| Category | P8-S6 budget |
| --- | ---: |
| Production paths | 0 |
| Test and fixture paths | 0 |
| Migration paths | 0 |
| Dependency and lock-file paths | 0 |
| Configuration paths | 0 |
| Deployment and release paths | 0 |
| Documentation closure paths | Materially necessary subset of the seven-owner maximum |

The eligible documentation owners are exactly:

1. `PLANS.md`;
2. `docs/architecture.md`;
3. `docs/public_client_contract.md`;
4. `docs/run_protocol.md`;
5. `docs/structured_player_character_contract.md`;
6. `docs/structured_player_character_implementation_plan.md`; and
7. `docs/structured_player_character_run_playable_loop_plan.md`.

Seven is a maximum, not a required edit count or target. Each owner is
inspected independently against the evidence that actually passed. An owner
may change only when successful P8-S6 evidence or the conditional Phase 8
closure makes one of its owned facts materially stale. No owner changes merely
to repeat a commit hash, test count, or completion marker. Unchanged eligible
owners remain byte-identical.

An eighth closure document is not authorized. A need for one stops P8-S6 for
separate authority. This plan, once separately reviewed and published, remains
unchanged and is not part of the later implementation candidate. Earlier
slice plans likewise remain unchanged.

## 7. Earlier-slice evidence ownership

- **P8-S1** owns bounded eligible-character repository, application, public
  API/OpenAPI, composition, and real-MySQL read-only evidence.
- **P8-S2** owns composite admission, Run revisions 1/2/3, immutable binding,
  participation, initial Session state, transaction, replay, locking,
  rollback, and persistence reconstruction evidence.
- **P8-S3** owns the normal `POST /v1/runs` public adapter/composition and the
  focused real-MySQL public entry-to-terminal vertical in
  `tests/integration/test_mysql_run_entry_playthrough.py`.
- **P8-S4** owns deterministic process-local Demo persistence/composition,
  generator consumption, public create/discover/enter/View behavior, and the
  cross-process canonical action journey.
- **P8-S5** owns the Web runtime schemas/client methods and rendered
  create-or-reuse/select/enter/storage/View/action/status/recovery/terminal
  behavior.
- **P8-S6** owns only the fresh coordinated rerun, reconciliation, final
  evidence ledger, and conditional Phase 8 documentation closure.

P8-S6 may rerun and cite P8-S3's real-MySQL vertical but must not rename,
rewrite, duplicate, or transfer that ownership. A missing required proof stops
the slice; it does not authorize a new P8-S6 test.

## 8. Environment prerequisites and network boundary

Before focused evidence:

- run in a normal PowerShell 7+ session from the repository root;
- require the existing `.\.venv\Scripts\python.exe`, Python 3.12, and pytest;
  stop if the venv is absent or broken and do not recreate it;
- require the existing Node/npm installation and `web/node_modules`; do not
  install or update packages;
- keep `RUN_LIVE_DEEPSEEK_TEST` absent or disabled;
- for real-MySQL selections, MySQL verification, and any database-bearing Full
  verification,
  require the designated reachable MySQL 8 test service identified by the
  process `TEST_DATABASE_URL`, which the repository verifier validates as
  driver `mysql+asyncmy` and database `deviation_protocol_test`; its endpoint
  may be loopback or non-loopback, and this designated test database is the
  sole permitted runtime service that may be non-loopback; do not contact any
  other database, and never print or expose the URL or credentials or copy
  them into documentation;
- for the bounded Demo smoke, require free loopback ports 8000 and 5173 and an
  available Windows `cmd.exe`/`npm.cmd` as checked by the existing script; and
- prohibit live Provider credentials and calls, production databases and
  production services, every unrelated non-loopback or external service,
  Internet dependencies, dependency downloads, package installation or
  updates, remote Git access, telemetry, and unrelated network access.

The canonical Offline verifier starts a sanitized child that removes database,
Provider, and live-test variables. MySQL evidence therefore runs separately.
Full verification may use the already validated test database environment, but
it never enables the opt-in Provider test. A prerequisite failure is recorded
as a blocker, not as a skip or weaker substitute.

## 9. Exact command catalogue for P8-S6 execution

All commands run from the repository root. Record selected, passed, skipped,
failed, and deselected counts exactly as emitted; the historical totals are not
acceptance thresholds.

### C01 — P8-S1 focused unit/API/composition

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_player_character_read.py tests/unit/test_player_character_repositories.py tests/unit/test_player_character_api.py tests/unit/test_run_composition.py
```

### C02 — P8-S1 focused real-MySQL public evidence

```powershell
.\.venv\Scripts\python.exe -m pytest tests/integration/test_mysql_player_character_api.py
```

### C03 — P8-S2 focused unit/service/persistence evidence

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_run.py tests/unit/test_run_operations.py tests/unit/test_run_service.py tests/unit/test_run_entry_service.py tests/unit/test_session_service.py tests/unit/test_run_persistence.py tests/unit/test_run_repositories.py
```

### C04 — P8-S2 focused real-MySQL persistence evidence

```powershell
.\.venv\Scripts\python.exe -m pytest tests/integration/test_mysql_run.py tests/integration/test_mysql_player_character_run_binding.py
```

### C05 — P8-S3 focused Run-entry API

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_run_entry_api.py
```

### C06 — P8-S3 focused normal composition

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_run_composition.py
```

### C07 — P8-S3 focused general API/OpenAPI contract

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_api.py tests/unit/test_phase_3_0_public_client_contract.py
```

### C08 — P8-S3-owned real-MySQL public entry-to-terminal vertical

```powershell
.\.venv\Scripts\python.exe -m pytest tests/integration/test_mysql_run_entry_playthrough.py
```

### C09 — P8-S4 focused deterministic Demo evidence

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_demo_persistence.py tests/unit/test_demo_composition.py tests/unit/test_run_composition.py tests/unit/test_player_character_api.py tests/e2e/test_demo_cross_process_replay.py
```

The cross-process owner invokes
`tests/e2e/support/demo_replay_child.py`. The historical conditional predicate
for a direct `tests/unit/test_demo_scripts.py` focused selection did not
activate because P8-S4 changed no launcher or smoke contract; canonical pytest
still collects that file. P8-S6 does not manufacture a new predicate.

### C10 — P8-S5 focused Web contract and complete rendered journey

```powershell
npm --prefix web run test:run -- src/api/client.test.ts src/App.test.tsx src/App.action-loop.test.tsx src/App.recovery.test.tsx
```

### C11 — complete Web test suite

```powershell
npm --prefix web run test:run
```

### C12-C14 — Web static and production-build gates

```powershell
npm --prefix web run typecheck
npm --prefix web run lint
npm --prefix web run build
```

### C15 — existing bounded loopback-only Demo smoke

```powershell
.\scripts\smoke-demo.ps1 -TimeoutSeconds 60
```

This is supporting startup/proxy/schema/presentation/build evidence. It is
applicable to final cross-surface reconciliation because it runs the existing
Demo backend and Web presentation on loopback. It does not replace C08, C09,
C10, or C11 and is not evidence of production deployment or external access.

### C16-C18 — compilation and Alembic metadata stability

```powershell
.\.venv\Scripts\python.exe -m compileall -q src tests alembic
.\.venv\Scripts\python.exe -m alembic heads
.\.venv\Scripts\python.exe -m alembic history
```

### C19-C21 — canonical repository suites

```powershell
.\scripts\verify.ps1 -Mode Offline
.\scripts\verify.ps1 -Mode MySQL
.\scripts\verify.ps1 -Mode Full
```

### C22 — tracked diff whitespace validation

```powershell
git diff --check
```

### C23 — eligible-owner and unauthorized-path inventory

```powershell
git diff --name-only
git diff --cached --name-only
git ls-files --others --exclude-standard
git status --short
```

The first list must be a materially necessary subset of the seven eligible
owners. The other three lists must show no staged path, no ordinary untracked
path, and no unauthorized path.

### C24 — documentation link-target validation

Run this read-only PowerShell check over only the owners selected by C23:

```powershell
$closurePaths = @(git diff --name-only)
$broken = @()
foreach ($path in $closurePaths) {
    $directory = Split-Path -Parent $path
    if ([string]::IsNullOrEmpty($directory)) { $directory = '.' }
    $text = Get-Content -Raw -LiteralPath $path
    foreach ($match in [regex]::Matches($text, '(?<!!)\[[^\]]+\]\((?<target>[^)]+)\)')) {
        $target = $match.Groups['target'].Value.Trim().Trim('<', '>')
        if ($target -match '^(https?:|mailto:)' -or $target.StartsWith('#')) { continue }
        $local = [Uri]::UnescapeDataString(($target -split '#', 2)[0])
        if (-not (Test-Path -LiteralPath (Join-Path $directory $local))) {
            $broken += "${path}: $target"
        }
    }
}
if ($broken.Count -ne 0) { $broken; throw 'Broken local Markdown link target.' }
```

For every link containing a fragment, additionally compare that fragment to
the target document's rendered heading anchor. The currently eligible owners
contain fragment links to Phase 3.1c, Phase 6, Phase 7, and the canonical
documentation-synchronization checklist; those anchors must remain present.
This explicit anchor inspection is required even when C24 finds every file.

### C25 — documentation structure, fence, status, and hygiene validation

```powershell
$closurePaths = @(git diff --name-only)
foreach ($path in $closurePaths) {
    $lines = @(Get-Content -LiteralPath $path)
    $fences = @($lines | Where-Object { $_ -match '^\s*(```|~~~)' })
    if (($fences.Count % 2) -ne 0) { throw "Unbalanced fence: $path" }
}
rg -n "^(<<<<<<<|=======|>>>>>>>)|\b(TODO|TBD|FIXME|CHANGEME|PLACEHOLDER)\b" $closurePaths
rg -n "P8-S6|Phase 8|Phase 6|Phase 7|Structured Player Character|overall project" $closurePaths
```

For the first `rg`, exit 1 with no output means no marker/placeholder match and
is success; exit 0 requires investigation and exit 2 or greater is a command
failure. For the status search, exit 0 is expected and is not itself success:
inspect every hit for consistent state wording. Inspect headings outside
fences for exactly one level-1 title per document and no skipped level. Inspect
the complete diff of each selected owner, not only search hits.

No formatter or auto-fixer participates in C24-C25.

## 10. Phase 8 closure evidence matrix

Command IDs resolve to the literal commands in section 9. “Expected evidence”
always includes a zero command exit and actual counts recorded without a
predicted total. Any unexpected skip or count difference is investigated.

| ID and closure claim | Controlling authority | Existing implementation surface | Existing test/verification owner and exact command | Environment prerequisite | Expected evidence; failure meaning | Class | Documentation owner allowed to record the result |
| --- | --- | --- | --- | --- | --- | --- | --- |
| E01 — eligible owned Player Character discovery remains bounded, ordered, private, read-only, and usable by the journey | Public client contract; Phase 8 plan; P8-S1 published behavior | Player Character projection/service/repository/API and normal/Demo composition | P8-S1 owners, C01; real-MySQL owner, C02 | Standard local environment; MySQL prerequisite for C02 | Exact collection/DTO/OpenAPI, ownership, bound exclusion, 0/1/32/33 bounds, no write. Failure means a P8-S1 or cross-slice defect; stop | Focused | `docs/public_client_contract.md`; architecture only if its boundary became stale |
| E02 — atomic internal Run entry retains revisions 1/2/3, immutable character binding, participation, initial Session, replay, locking, rollback, and one commit | Run protocol; Structured Player Character contract; P8-S2 plan | Run-entry service, Run/Session/Player Character repositories and UoW | P8-S2 unit owners, C03; P8-S2 MySQL owners, C04 | Standard local; MySQL for C04 | Complete family commits/reloads or exact replay/no-write; races and failures leave no partial family. Failure returns to P8-S2 ownership; stop | Focused | `docs/run_protocol.md`; `docs/structured_player_character_contract.md` |
| E03 — normal public `POST /v1/runs` preserves the frozen DTO/error/OpenAPI/privacy boundary and calls entry authority at most once | Public client contract; architecture; P8-S3 plan | Run-entry API adapter and lazy normal composition | P8-S3 API, composition, and public-contract owners, C05-C07 | Standard local | Exact validation, result projection, non-enumeration, sanitization, cancellation, one service call, shared lazy UoW graph. Failure is an owning-slice defect; stop | Focused | `docs/public_client_contract.md`; `docs/architecture.md` |
| E04 — the production-backed public entry-to-terminal journey remains real and durable | Phase 8 plan; P8-S3 plan; Run protocol | Normal ASGI adapter, production services, SQLAlchemy/asyncmy persistence, scripted Provider | P8-S3-owned `tests/integration/test_mysql_run_entry_playthrough.py`, C08 | Valid MySQL 8 test database; scripted Provider only | Public scenario/character setup, `POST /v1/runs`, replay, initial View, genuine 202/PENDING/COMMITTED status, 19 View-driven actions, terminal View, persisted admission/gameplay cardinalities, still-active Run, exact cleanup. Failure is a P8-S3-owned or current regression; P8-S6 does not edit it | Focused and canonical vertical | Detailed ledger only in `docs/structured_player_character_run_playable_loop_plan.md`; contract facts in `docs/run_protocol.md` or `docs/public_client_contract.md` only if materially stale |
| E05 — deterministic Demo exposes the same existing public contracts over process-local authority without external I/O | Architecture; Phase 8 and P8-S4 plans | Demo repositories/UoW/composition/generators and public routes | P8-S4 focused owners, C09 | Standard local; child-process execution; no external network | Atomic publication/rollback, generator non-rewind, create/discover/enter/View, canonical 19-action terminal journey, deterministic restart loss/reset, preservation of the canonical deterministic in-process Provider path guarded by `CanonicalDemoProviderGuard` with exactly four completed calls, no external or live Provider access, no external Provider fallback, and no external I/O. Failure belongs to P8-S4/current code; stop | Focused | `docs/architecture.md`; detailed ledger in `docs/structured_player_character_run_playable_loop_plan.md` |
| E06 — Web schemas and client methods consume the existing Player Character and Run-entry contracts and never make legacy Session create the primary path | Public client contract; P8-S5 plan | `web/src/api/schemas.ts`, `web/src/api/client.ts`, `web/src/App.tsx` | P8-S5 focused Web owners, C10; complete Web suite, C11 | Existing Node/npm and `web/node_modules` | Exact URLs/headers/bodies/statuses/runtime validation, no automatic POST retry, primary path uses Run entry, legacy route remains. Failure belongs to P8-S5/current code; stop | Focused plus canonical Web | `docs/public_client_contract.md`; `docs/architecture.md` only for materially stale composition facts |
| E07 — complete rendered primary Web journey reaches the existing terminal View | Phase 8 plan; P8-S5 plan | App pre-play, Session handoff, existing action/status/View loop | `web/src/App.action-loop.test.tsx` through C10 and all Web tests through C11 | Existing Web environment | Scenario discovery, eligible selection or minimal creation, Run entry, recovery storage, authoritative View, every displayed action, 202 status recovery where applicable, terminal rendering. Failure means cross-surface closure is unsatisfactory; stop | Focused and canonical Web | `docs/structured_player_character_run_playable_loop_plan.md`; `PLANS.md` only for status after all evidence |
| E08 — recovery ordering, uncertainty, idempotency, single-flight, and stale-completion isolation remain exact | Public client contract; P8-S5 plan | App mutation attempts, recovery record, foreground operation and generation guards | `web/src/App.recovery.test.tsx`, `App.test.tsx`, and client tests through C10-C11 | Existing Web environment and browser-test storage mocks | Storage precedes View; reload recovery is GET-only; exact same key/body manual retry; tainted uncertainty retained; late results ignored; no durable pending mutation. Failure is a P8-S5/current regression; stop | Focused | `docs/public_client_contract.md`; detailed ledger in `docs/structured_player_character_run_playable_loop_plan.md` |
| E09 — canonical action lifecycle and terminal semantics agree across real MySQL, Demo, and Web | Run protocol; public client contract; Phase 8 plan | Existing action gateway/orchestration/status/View/terminal surfaces | C08, C09, C10, and C11 | MySQL plus standard local/Web prerequisites | `202 -> PENDING -> COMMITTED -> authoritative View`, no action replay, current affordance-driven actions, terminal no-action View, Run remains active/bound. A disagreement is a contract or owning-slice defect; stop | Cross-surface reconciliation | `docs/run_protocol.md`; `docs/public_client_contract.md`; detailed ledger in the Phase 8 plan |
| E10 — frontend types, lint policy, and production bundle remain valid | P8-S5 plan; `web/package.json` | Entire current Web project | C12-C14 | Existing Node/npm and dependencies; no install/network | Typecheck succeeds, lint has zero warnings, production build succeeds. Failure is a current Web defect or environment blocker; stop | Canonical Web quality | Detailed ledger in `docs/structured_player_character_run_playable_loop_plan.md` |
| E11 — bounded loopback Demo startup/proxy/schema/presentation/build remains operable | Phase 8 plan's applicable-smoke clause; existing smoke script | Existing Demo ASGI app, Vite proxy/client, scenario validator, owned temp build | `scripts/smoke-demo.ps1`, C15 | Free loopback ports, existing venv/node modules, process launch allowed | Script's complete success message, owned cleanup, no dotenv leak or non-loopback I/O. Failure is investigated; it cannot be waived by unit tests | Supporting | Architecture only if a materially stale operational boundary is found; otherwise detailed ledger in Phase 8 plan |
| E12 — Python compilation, schema metadata, migration history, and zero-migration boundary remain stable | Architecture; guardrails; Phase 8 plan | Current source/tests/Alembic graph and MySQL schema | C16-C18 and canonical C19-C21 | Standard local; MySQL prerequisite for C20 and database-bearing Full run | Compilation, one expected Alembic head/history, verifier parity, no migration diff. Failure or need for migration stops P8-S6 | Supporting plus canonical suite coverage | `docs/architecture.md`; detailed ledger in Phase 8 plan |
| E13 — canonical repository verification succeeds offline, against MySQL, and in Full mode | Phase 8 plan; verification workflow; `scripts/verify.ps1` | Entire tracked Python/test/migration surface | C19, C20, C21 | Sanitized Offline child; safe MySQL URL for MySQL; live Provider disabled | Every verifier stage succeeds and actual counts/skips are recorded. Any failure, unexpected skip, or count difference is investigated; unsatisfactory evidence stops edits | Canonical | Detailed ledger in `docs/structured_player_character_run_playable_loop_plan.md`; `PLANS.md` may summarize closure without duplicating counts mechanically |
| E14 — the designated MySQL 8 test database is the sole permitted runtime service that may be non-loopback; no live Provider, Provider credential, production database or service, deployment, or unrelated non-loopback or external service participates | Phase 8 exclusions; security instructions; all slice plans | Scripted/deterministic Provider seams; Offline child; loopback smoke; designated MySQL 8 test database | Environment preflight plus C08-C21 observations | `RUN_LIVE_DEEPSEEK_TEST` disabled; `TEST_DATABASE_URL` validates as `mysql+asyncmy` with database `deviation_protocol_test`; its endpoint may be loopback or non-loopback; Demo smoke remains loopback-only | The designated test database is the only contacted runtime service that may be non-loopback; zero live Provider calls and no unrelated external-network attempt, Internet dependency, download, installation, remote Git access, telemetry, or unrelated network access occurs; configured test-database credentials are not printed, copied into documentation, or exposed. Any other requirement/contact is a scope violation; stop | Canonical boundary | `docs/architecture.md` only if materially needed; otherwise detailed ledger in Phase 8 plan |
| E15 — final closure is documentation-only and internally consistent | Workflow; Phase 8 documentation authority | Selected subset of the seven existing owners | C22-C25 plus complete per-file diff inspection | All executable evidence E01-E14 satisfactory | Links/anchors/fences/headings/status/diff pass; only material owners change. Failure caused by closure prose may be corrected only in the selected subset before review; other failure stops | Canonical documentation closure | Each selected owner records only its own facts; the Phase 8 plan owns the detailed ledger |
| E16 — final Git scope and frozen authority are preserved | Repository instructions; workflow; this plan | Git worktree/index/refs and published plan files | C23 plus final ref/lock/operation/hash reconciliation | Clean aligned execution baseline; no remote operation | Diff is a subset of seven, index/untracked empty, plan and earlier plans unchanged, refs unchanged before commit. Any extra path or mutation stops without cleanup | Canonical handoff | `PLANS.md` owns roadmap state; exact Git identities belong in the final handoff unless a current owner materially requires them |

## 11. Deterministic P8-S6 execution order

1. **Repository and reviewed-plan preflight.** Perform section 2. Stop on any
   identity, cleanliness, lock, operation, or reviewed-hash mismatch.
2. **Authority and owner reconciliation.** Read all controlling authorities,
   inspect every eligible documentation owner independently, confirm the
   matrix still maps to existing tests/commands, and identify no edits yet.
3. **Environment prerequisites.** Validate PowerShell, venv, Node dependencies,
   safe MySQL test identity, disabled live Provider, loopback ports for smoke,
   and absence of a need for unrelated external access. Do not print secrets.
4. **Accepted focused evidence reruns.** Run C01 through C10 in order. The
   MySQL-dependent commands run only after the exact safe prerequisite passes.
5. **Complete client and supporting cross-surface evidence.** Run C11 through
   C15.
6. **Canonical suite reruns.** Run C16 through C21. Redundant compilation and
   Alembic commands are intentional explicit evidence alongside verifier-owned
   repetitions.
7. **Investigate every failure or count difference.** Preserve native output,
   classify the exact cause, and determine whether every required proof is
   satisfactory. A skip guard expected by one environment may not substitute
   for the separately required real-MySQL evidence.
8. **Stop before editing if evidence is incomplete.** Any unsatisfactory
   E01-E14 result ends P8-S6 with exact evidence and an unchanged worktree.
9. **Select the smallest documentation subset.** For each of the seven owners,
   state the specific stale fact caused by the successful evidence/conditional
   closure. Owners without such a fact remain byte-identical.
10. **Make only closure edits.** Edit the selected owners without touching this
    plan or any production/test/configuration/dependency/migration/deployment
    path. Do not add an eighth document.
11. **Inspect every document completely.** Read each complete selected file and
    its complete diff. Reconcile links, anchors, fences, headings, terms,
    evidence attribution, status, P6/P7, programme/project status, and
    publication wording.
12. **Post-edit verification.** Run C22-C25, then rerun C19-C21. Documentation
    edits do not permit weakening a previously passed executable gate.
13. **Exact-path reconciliation.** Run C23; compare the diff to the per-owner
    reasons from step 9; verify all zero-change categories, frozen plan hashes,
    refs, active operations, and locks.
14. **Independent implementation/closure review handoff.** Record complete
    selected-file hashes, byte counts, line counts, exact diff, evidence
    results, environment/network facts, and one review verdict that can
    actually satisfy the candidate's required condition. Any byte change after
    review invalidates the identities and requires a fresh review.
15. **Separately authorized staging and commit.** Only after exact-candidate
    independent approval and explicit user authorization, stage precisely the
    reviewed documentation subset, validate the index, and create the one
    authorized local closure commit. Review alone is not commit authority.
16. **User-controlled push.** Codex never pushes. The user publishes manually;
    final aligned refs and clean status are then confirmed without a new
    documentation slice.

Documentation must not claim successful P8-S6 closure before step 7 establishes
that all executable evidence is satisfactory.

## 12. Per-owner closure reconciliation

Each owner is inspected even if it remains unchanged:

- `PLANS.md` owns the Phase 8 roadmap transition, preservation of Phase 6/7,
  and programme/project incompleteness.
- `docs/architecture.md` owns implemented cross-surface composition,
  transaction/persistence separation, Demo versus MySQL evidence, and no-live-
  Provider architecture.
- `docs/public_client_contract.md` owns existing operations, DTO/error/privacy,
  primary versus legacy entry, recovery, and request-status semantics.
- `docs/run_protocol.md` owns Session-backed Run activation, authoritative View,
  action/status lifecycle, and the Run-still-active terminal boundary.
- `docs/structured_player_character_contract.md` owns eligible/binding/
  immutable-reference semantics and truthful downstream phase status.
- `docs/structured_player_character_implementation_plan.md` owns the Structured
  Player Character programme sequence and continued Phase 6/7 deferral.
- `docs/structured_player_character_run_playable_loop_plan.md` owns the detailed
  Phase 8 evidence ledger, slice closure, residual exclusions, and completion
  condition.

An edit needs a sentence-specific material reason. A count or commit identity
may be recorded where it is necessary evidence or provenance for that owner's
fact, but never solely to force that owner into the candidate.

## 13. Failure and correction boundary

P8-S6 expects no production or test correction. Stop with the exact command,
exit code, relevant native diagnostic, environment, affected claim, current
Git inventory, and owning slice when evidence reveals any of these:

- a production defect;
- a missing required test or discriminating assertion;
- an incorrect fixture;
- a schema, ORM, migration, or database-parity problem;
- a public-contract, lifecycle, or documentation-authority contradiction;
- an unsatisfied environment prerequisite;
- a need for an eighth documentation owner;
- a need for production, test, fixture, configuration, dependency, migration,
  deployment, generated, or frozen-plan changes; or
- a need to perform or reclassify Phase 6 or Phase 7 work.

P8-S6 must not repair, weaken, skip, quarantine, xfail, regenerate, rebaseline,
or expand around such a finding. A real correction requires a separately
authorized plan, implementation, evidence, and review in the owning scope.

A documentation defect introduced by the closure edits may be corrected before
independent review only when every corrected byte remains inside the already
selected eligible subset. Rerun every affected documentation check and the
required post-edit canonical gates. If correction needs a new owner, stop.

If a verification tool creates only its normal ignored output, record it and
leave it alone. If it changes an unauthorized tracked or ordinary untracked
path, stop and preserve the state; do not clean or absorb it.

## 14. Closure states and Phase 8 completion

These states are distinct and must not be collapsed:

1. **Evidence collected:** E01-E14 have satisfactory fresh results. No
   documentation closure or review is implied.
2. **P8-S6 implementation candidate complete:** the smallest eligible
   documentation subset truthfully records the evidence and conditional
   closure; C22-C25 and post-edit canonical gates pass; inventories are exact.
   The candidate is still unapproved, uncommitted, and unpublished.
3. **Independent P8-S6 review approved:** a fresh read-only reviewer accepts
   the exact candidate bytes and hashes. This grants no staging, commit, push,
   or publication authority.
4. **P8-S6 closure committed:** after separate explicit authorization, the
   reviewed documentation subset exists in one local commit. A local commit is
   not publication.
5. **P8-S6 closure published:** the user has pushed that exact commit and a
   later read-only check confirms clean aligned `main`, `HEAD`, local `main`,
   and local `origin/main` at `0/0`.
6. **Phase 8 complete:** all E01-E16 conditions have been satisfied and the
   exact closure commit is published. This becomes true at the same confirmed
   publication boundary as state 5, not at evidence collection, candidate
   completion, review, or local commit.

Successful Phase 8 closure does not complete Phase 6, Phase 7, the Structured
Player Character programme, or the overall project. Those four statuses remain
explicitly incomplete in every applicable owner and handoff.

## 15. Publication-status circularity

The documentation candidate cannot truthfully contain the hash or publication
fact of a commit that does not yet exist. It therefore records:

- actual evidence already collected;
- the exact candidate status and reviewed closure condition;
- that publication of the exact closure commit is the final condition for
  P8-S6 closure and Phase 8 completion; and
- the still-incomplete Phase 6, Phase 7, programme, and project states.

It does not invent a commit hash, speculative P8-S7, or unowned
post-publication synchronization slice. The final Git handoff report—not the
pre-commit documentation bytes—records the local closure commit identity, the
user-controlled publication confirmation, aligned refs, and the fact that the
conditional completion boundary was satisfied. No document must be edited
again merely to repeat that hash or publication marker.

## 16. Stable acceptance criteria

| ID | Individually testable acceptance criterion |
| --- | --- |
| P8S6-AC-01 | The execution preflight matches the separately authorized published-plan baseline, exact reviewed plan SHA-256, clean worktree/index, aligned refs, and no operation/lock; no remote operation occurs |
| P8S6-AC-02 | All current authorities and every eligible owner are read and reconciled before evidence or edits; no authority contradiction is unresolved |
| P8S6-AC-03 | P8-S1 focused unit/API/composition and real-MySQL eligible-discovery evidence passes through C01-C02 |
| P8S6-AC-04 | P8-S2 focused unit and real-MySQL atomic Run-entry/replay/persistence evidence passes through C03-C04 |
| P8S6-AC-05 | P8-S3 API, composition, public-contract, and privacy evidence passes through C05-C07 without changing its behavior or ownership |
| P8S6-AC-06 | The P8-S3-owned real-MySQL public entry-to-terminal vertical passes through C08 with genuine 202/PENDING/COMMITTED/View evidence, 19 authoritative actions, terminal persistence, still-active Run, and scoped cleanup |
| P8S6-AC-07 | P8-S4 focused deterministic Demo persistence/composition/cross-process evidence passes through C09 without external I/O or a new test owner |
| P8S6-AC-08 | P8-S5 focused Web evidence and the complete Web suite pass through C10-C11 |
| P8S6-AC-09 | The reconciled primary Web journey covers scenario discovery, eligible selection or minimal creation, Run entry, validated Session storage, authoritative View, action, status recovery, committed View, and terminal handling without primary use of legacy Session create |
| P8S6-AC-10 | Run-entry storage-before-View and safe GET-only recovery are demonstrated; safe recovery never replays Run entry |
| P8S6-AC-11 | Action and pre-play mutation idempotency, exact replay, uncertainty/manual retry, single-flight, cancellation, and stale-generation semantics remain intact |
| P8S6-AC-12 | Existing terminal behavior, active immutable Run binding, URL privacy, and Session-only browser recovery storage remain intact |
| P8S6-AC-13 | Web typecheck, zero-warning lint, and production build pass through C12-C14 without dependency or configuration changes |
| P8S6-AC-14 | The applicable bounded loopback Demo smoke passes through C15 and is treated only as supporting evidence |
| P8S6-AC-15 | Explicit compilation and Alembic heads/history checks pass through C16-C18 with no migration change |
| P8S6-AC-16 | Canonical Offline, MySQL, and Full verification all pass through C19-C21; actual counts and every skip/count difference are reconciled |
| P8S6-AC-17 | The `TEST_DATABASE_URL`-designated MySQL 8 test database, validated as `mysql+asyncmy` with database `deviation_protocol_test`, is the sole permitted runtime service that may be non-loopback, and its endpoint may be loopback or non-loopback; no live Provider or Provider credential, production database or service, deployment, release, unrelated non-loopback or external service, Internet dependency, download, installation, remote Git access, telemetry, or unrelated network access is required or contacted; test-database credentials are not printed, copied into documentation, or exposed; Demo smoke remains loopback-only and deterministic Demo/scripted-Provider evidence remains external-Provider-free |
| P8S6-AC-18 | Public Player Character, Run-entry, Session View/action/status, privacy, replay, and lifecycle contracts remain unchanged |
| P8S6-AC-19 | Production, test/fixture, migration, dependency/lock, configuration, deployment, generated, and frozen-plan path changes are all zero |
| P8S6-AC-20 | Every one of the seven eligible documentation owners is inspected independently; only a materially stale subset changes, seven remains the maximum rather than a target, and unchanged owners are byte-identical |
| P8S6-AC-21 | No eighth closure document is added, and this plan is absent from the implementation diff after its separate approval/publication |
| P8S6-AC-22 | Complete per-document diff inspection plus C22-C25 proves links, anchors, fences, headings, whitespace, status wording, and owner attribution are sound |
| P8S6-AC-23 | Evidence collection, candidate completion, independent approval, local commit, publication, and Phase 8 completion remain distinct as defined in section 14 |
| P8S6-AC-24 | Phase 8 is marked complete only after satisfactory evidence, truthful closure docs, exact-byte independent approval, separately authorized commit, user publication, and clean aligned confirmation |
| P8S6-AC-25 | Phase 6 and Phase 7 remain deferred and incomplete; the Structured Player Character programme and overall project remain incomplete |
| P8S6-AC-26 | Final inventories contain only the selected eligible documentation subset, an empty index before separate staging authority, no ordinary untracked path, unchanged refs before commit, no active operation/lock, and unchanged earlier plans |
| P8S6-AC-27 | A fresh independent review binds to exact hashes before any staging; staging and local commit require separate explicit authorization; the user alone pushes |
| P8S6-AC-28 | No speculative P8-S7, post-publication slice, future commit hash, or redundant post-publication documentation edit is required |

No criterion creates new behavior. A criterion that cannot be satisfied by the
existing surfaces and commands is a blocker, not authority to add code or
tests.

## 17. Independent review, commit, and publication gates

After candidate completion, the handoff must provide the reviewer:

- this plan's already published reviewed identity;
- baseline and current refs;
- every selected documentation path with line count, byte count, and SHA-256;
- complete diffs and C23 inventories;
- the E01-E16 result ledger with exact commands, counts, skips, failures, and
  environment prerequisites;
- confirmation that the validated `TEST_DATABASE_URL`-designated MySQL 8 test
  database was the only runtime service permitted to be non-loopback, whether
  its endpoint was loopback or non-loopback, that Demo smoke remained
  loopback-only, and that no live Provider or unrelated non-loopback/external
  service was contacted and no configured database credential was exposed;
- the documentation checklist and Guardrail impact; and
- a single explicit review success condition bound to those exact bytes.

The review is read-only. If any byte changes, discard the prior candidate
hashes and review result and repeat the applicable checks and review. Do not
stage during review.

Only a later user instruction explicitly authorizing the exact local commit may
authorize staging/commit. Before that commit, inspect the index with
`git diff --cached --check`, `git diff --cached --stat`, and
`git status --short`; only reviewed eligible documentation paths may be staged.
Hooks or other commit-time mutations invalidate the reviewed candidate unless
the resulting exact bytes are reverified and independently reviewed.

Codex never pushes this repository. The user performs every push. Publication
is established only by a later read-only aligned-ref/clean-state confirmation;
no remote Git contact occurs during P8-S6 evidence, documentation editing,
review, or local commit.

## 18. Explicit exclusions

P8-S6 does not authorize:

- any reopened P8-S1 through P8-S5 implementation or plan change;
- duplicate production behavior, test, fixture, or evidence ownership;
- new or changed API, DTO, OpenAPI, persistence, transaction, lifecycle,
  recovery, retry, storage, URL, privacy, terminal, or Provider behavior;
- a migration, ORM, schema, dependency, lock-file, configuration, generated,
  launcher, deployment, release, or production-environment change;
- live Provider or Provider credentials, production databases or production
  services, Internet dependencies, dependency downloads, package installation
  or updates, remote Git access, telemetry, or unrelated network access; the
  designated MySQL 8 test database identified by `TEST_DATABASE_URL` is the
  sole runtime service permitted to use a non-loopback endpoint and is not an
  unrelated external service, but only after exact `mysql+asyncmy` and
  `deviation_protocol_test` validation, and its configured credentials must
  not be printed, copied into documentation, or exposed;
- Phase 6 or Phase 7 implementation, reclassification, or completion;
- programme or project closeout;
- a new phase, P8-S7, or post-publication synchronization task;
- staging, committing, pushing, fetching, pulling, deployment, or release
  without their separately required authority; or
- unrelated cleanup, formatting, refactoring, documentation polish, or status
  normalization.

## 19. Plan-authoring versus execution evidence

The Offline verification and Markdown/Git checks used to validate this plan
are plan-authoring integrity evidence only. They do not execute the C01-C25
P8-S6 matrix, do not begin P8-S6, and cannot be cited as P8-S6 completion
evidence. The later authorized execution must produce fresh results in the
deterministic order above.

## 20. Unresolved decisions

**None within the current authority.**

The purpose, zero-change categories, seven-owner maximum, existing evidence
owners, exact commands, environment boundaries, stop rules, closure condition,
and publication handoff are fixed. A later contradiction stops the slice rather
than reopening one of those decisions.

## 21. Guardrail impact

None. This plan applies the existing repository guardrails and workflow. No
confirmed defect in this plan-authoring task creates or changes a reusable
engineering, safety, session, review, environment, or Git-handoff rule.

## 22. Exact next action after plan approval and freeze

Leave this approved and frozen plan as the sole untracked path. Do not stage,
commit, push, publish, or execute P8-S6. Return control to the user for a
separately authorized exact staging and local plan-commit task. The user alone
performs any later push, and P8-S6 implementation still requires separate
authorization from a clean, aligned, published-plan baseline.
