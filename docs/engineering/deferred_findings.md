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
