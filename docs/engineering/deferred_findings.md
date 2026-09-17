# Deferred findings

This is the canonical register for confirmed non-blocking findings accepted
under the [workflow disposition policy](codex_workflow.md#findings-and-milestone-disposition).
Keep one concise entry per finding; link evidence instead of copying audit
transcripts. Never fabricate findings or record speculative improvements here.

Use stable IDs `DF-001`, `DF-002`, and so on; never recycle them. Each entry uses:

- **ID / status:** deferred, reassessment required, escalated blocker, or closed.
- **Affected feature/path:** exact affected surface.
- **Evidence:** confirmed reproduction or evidence reference.
- **User impact / exposure:** consequences and reachable/operational conditions.
- **Non-blocking rationale:** why the current named milestone can proceed.
- **Containment/workaround:** required measure, or explicitly not needed.
- **Repair/reassessment:** milestone and responsible role.
- **Closure evidence:** fix and verification reference when closed.

Reassess when reachability or impact expands or containment is lost, and at the
post-playable stabilization checkpoint before wider release. Retain closed IDs
and evidence; escalate blockers under the workflow policy.

## Current entries

The already-fixed S3 planning findings remain historical closures, not open debt.

### DF-001 — Locale-dependent PowerShell assertion

- **ID / status:** DF-001 / deferred.
- **Affected feature/path:** `tests/unit/test_demo_scripts.py:152`; no production
  S3 behavior or database constraint is affected.
- **Evidence:** S3 implementation verification on 2026-09-16 reached 345 passing
  unit tests before `test_smoke_rejects_timeout_values_outside_the_inclusive_bounds[9]`
  failed: PowerShell 7 correctly rejected 9, but its zh-CN error did not contain
  the English text `allowed range`. The test and script are unchanged from
  baseline `67a5d50197b580f6c9c1a407f17e14c0bde2b44c`.
- **User impact / exposure:** verification can report a false failure on a
  non-English Windows installation; the timeout guard still rejects the input.
- **Non-blocking rationale:** this is a test-message localization dependency,
  not a playable-flow, authority, security, persistence, or migration failure.
  Required S3 tests and exhaustive S2 counters are not waived.
- **Containment/workaround:** run verification subprocesses with
  `DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1` and
  `DOTNET_SYSTEM_GLOBALIZATION_PREDEFINED_CULTURES_ONLY=0` for deterministic
  PowerShell resource language. These are process-local settings, not changes
  to the user's Windows language, repository dependencies, or assertions.
- **Repair/reassessment:** verification-tooling maintainer, at the post-playable
  stabilization checkpoint before wider release; replace English-substring
  reliance with a language-independent assertion and rerun both locales.
- **Closure evidence:** none; the production guard works, but the locale-fragile
  assertion has not been changed within this S3 path budget.

### DF-002 — Partial discovery refresh after Demo startup race

- **ID / status:** DF-002 / reassessed and deferred for the S7-1 implementation candidate and bounded local
  playable milestone; no wider-release approval.
- **Affected feature/path:** Web setup discovery recovery in `web/src/App.tsx`;
  the observed “刷新可用选项” action refreshes entry options while scenario and
  character discovery error sections remain after the documented startup race.
- **Evidence:** U1 in the 2026-09-17 S6 local deterministic Demo browser report,
  tested at `2f144599af5977e871c7a3466c52896b6a36510c`; canonical locator and
  limitations are in [the S6 evidence record](../run_protocol.md#s6-publication-and-local-browser-evidence).
  Report artifacts `07-restart-transient.txt`, `07-missing-session.txt`,
  `08-cleared.txt`, `08-discovery-refresh-partial.txt`, `09-fresh-setup.txt` and
  `runtime-redacted.txt` record coupled backend/Web restart -> frontend ready
  before backend -> discovery/recovery 502 -> safe GET 404 -> explicit local
  clear -> partial options refresh -> successful full-page reload.
  S7-1 rendered acceptance (`web/src/App.test.tsx`, case “reassesses DF-002”)
  now injects independent entry-options and eligibility failures after terminal
  return to setup. Options refresh leaves the separate eligibility error visible;
  the existing explicit eligible-character GET retry restores that discovery.
  Confirmation stays disabled with empty selections and neither admission nor
  exit is dispatched. Terminal reload, exact exit retry and failed storage
  removal/retry also pass in that suite. The external `web-stable.log` record is
  linked from [S7-1 evidence](../run_protocol.md#p33-s7-1-implementation-candidate-evidence).
- **User impact / exposure:** one additional explicit page reload in that
  observed local startup ordering. No automatic mutation, lost durable data or
  unrecoverable gameplay block was observed. This does not establish impact for
  every network failure or a backend-only restart.
- **Non-blocking rationale:** the observed reload restores all discovery and
  explicit native setup; no workflow blocking, authority, privacy or integrity
  failure was demonstrated for this milestone. The workarounds and limited
  exposure permit the next plan review under existing deferral policy.
  Fresh rendered S7-1 evidence demonstrates recovery through the separate GET
  controls after return to setup; required recovery is not waived by the prior
  reload containment. The coupled browser startup timing has not been rerun.
- **Containment/workaround:** once the backend is ready and missing-Session
  recovery has been explicitly cleared, reload the page to refresh all discovery.
  Do not treat partial entry-options refresh as a complete discovery retry.
  Keep native confirmation disabled until explicit eligible selections succeed.
- **Repair/reassessment:** Web client maintainer; S7-1 return-to-setup reassessment
  is recorded above. Reassess again at the post-playable stabilization checkpoint before wider release,
  or sooner if reachability/impact expands or reload fails to restore the flow.
  Escalate if containment fails under the workflow's blocking criteria.
- **Closure evidence:** none; no general discovery-refresh fix or browser rerun
  accompanies this reassessment. Separate error sections and GET retries remain.
