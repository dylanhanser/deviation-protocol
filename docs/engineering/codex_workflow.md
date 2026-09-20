# Codex Workflow

This document defines how Codex implementation and review sessions should be
run for this repository.

Technical safety rules are recorded in
`docs/engineering/guardrails.md`.

## Playable-loop-first delivery

Prioritize an end-to-end playable flow: entry/creation -> core play ->
persistence -> reload/recovery -> ending, followed by real user feedback.
Use the published roadmap for feature ownership; this priority creates no new
slice or implementation authorization. Distinguish component implementation,
demonstrated integrated play, limited user-trial readiness, and broader release
readiness using the evidence definitions in [PLANS.md](../../PLANS.md#status-language).
Never infer a later readiness level from an earlier one.

After the playable milestone and before wider release, hold a stabilization
checkpoint: reassess deferred findings against actual exposure and feedback,
resolve release blockers, and record repair, containment, or further deferral
decisions. Do not promise every optional improvement.

### Prospective amendment and S3 applicability

This user-authorized amendment governs prospective review disposition,
non-blocking deferral, verification scheduling/reuse, and handoff, including
upcoming implementation of the [published S3 plan](../phase_3_3_s3_persistence_legacy_native_compatibility_plan.md).
It supersedes conflicting process wording in earlier plans for those purposes
only; historical reviews and exact candidate approvals are not rewritten or
transferred to changed content. Frozen candidate-time lifecycle wording is
history; current publication status belongs in PLANS.md and run_protocol.md.

S3's schema, ownership, transaction safety, reconstruction, migration behavior,
36-ID/56-block vector coverage, and exact implementation scope remain in force.
All required S3 technical evidence, including section 14's named suites and
checks, remains due. Scheduling or valid reuse must never turn missing evidence
into a claimed pass. There is no automatic waiver of real-MySQL, concurrency,
or data-preservation proofs. A change to a specific frozen technical requirement
must be explicit and impact-assessed, never hidden behind generic workflow text.
The existing S3 implementation success token remains the sole token when its
gate becomes operative; no new approval stage is introduced.

## One phase per session

Use a fresh Codex session for each implementation phase.

Do not continue major architecture work in a session that already contains a
large amount of unrelated design, implementation, or audit history.

A new session must read:

- `AGENTS.md`;
- relevant architecture and feature documentation;
- current `git status`;
- current diff;
- affected source and tests.

Do not paste every previous prompt into the new session. The repository is the
authoritative source of current implementation state.

## Choose reasoning strength by task risk

Use reasoning strength according to the task:

- Documentation, formatting, and mechanical edits: medium.
- Bounded development tools and isolated features: medium to high.
- Architecture, persistence, authority, scenario runtime, or Provider work:
  high.
- Independent transaction, permission, billing, or security review: the
  highest appropriate reasoning level in a fresh session.

Fast Mode should remain disabled for architecture, persistence, authority,
billing, security, and independent review tasks.

If a high-risk implementation was accidentally performed at a low reasoning
level, complete a fresh independent high-strength review before committing.

Do not let the implementation session act as the only reviewer of its own
high-risk changes.

## Implementation session

An implementation session must:

1. read repository constraints and relevant documentation;
2. confirm the expected working-tree state;
3. establish baseline evidence under the proportionate verification policy below;
4. implement only the authorized phase;
5. add meaningful regression coverage for each fixed code defect and tests for
   every state mutation;
6. run the required final verification;
7. report modified and untracked files;
8. stop without staging or committing unless explicitly authorized; never push.

Do not begin the next phase during the current phase's implementation or
review.

Do not perform unrelated cleanup or refactoring.

Fix an opportunistic defect only when directly related to the task, small in
scope, low in regression risk, meaningfully verifiable at low cost, and adding
no public contract, schema, or feature. Otherwise record eligible work in the
deferred-findings register. Unrelated pre-existing non-blocking findings do not
stop the current task: record them and continue within authorized scope.

## Independent review session

Retain fresh independent review in a new session for material implementation,
persistence, security, and authority changes.

A review session must:

- read the complete current diff, including untracked files;
- verify that implementation claims match actual code and tests;
- reproduce deterministic defects before fixing them;
- make only minimal in-scope fixes;
- add meaningful regression coverage for each fixed code defect;
- report remaining limitations accurately;
- avoid expanding into the next feature phase;
- avoid `git add`, commit, or push.

Review prompts must distinguish between:

- code guarantees;
- test evidence;
- documented assumptions;
- guarantees the system cannot provide.

A large passing test count does not replace architecture, authority, or
transaction-boundary review.

After correction, focus independent re-review on the findings, their direct
dependencies, and regressions caused by the correction. Preserve prior evidence
where it remains applicable. Report newly discovered concrete blockers; style
preferences and speculative improvements do not become blockers.

## Findings and milestone disposition

A finding blocks the relevant milestone when evidence shows any of these:

- The required playable flow cannot complete or recover.
- Security, privacy, ownership, or trusted authority can be violated.
- Stored state can be corrupted, lost, or incorrectly cross-bound.
- Migration or transaction behavior can cause irreversible damage.
- An exposed required feature produces materially wrong outcomes.
- Essential evidence is missing for one of these risks.

State concrete impact and a reachable path or applicable operational condition;
severity labels alone do not decide disposition. Investigate plausible serious
risks enough to classify them: absence of evidence does not establish safety.

A confirmed finding may be deferred only when impact and exposure are understood,
none of the blocking criteria applies at the stated milestone, necessary
containment/workarounds are specified, and a repair or reassessment milestone
and responsible role are recorded in the canonical
[deferred-findings register](deferred_findings.md). If reachability or impact
expands, or containment fails, reassess and escalate to a blocker when required.

Approval may include documented deferred findings. It permits only the stated
development milestone, not automatic production release. Required technical
acceptance evidence remains due; deferral is not a waiver of a frozen contract.

## Pending-plan baseline invalidation

Whenever `HEAD`, the intended implementation base, or a recorded remote
baseline changes while a plan is pending, assess whether the change is relevant
before further review, approval, staging, or commit. A relevant change requires
reassessment and, where necessary, update of the implementation baseline, plan
status, approval-bound hashes and gate, candidate path inventory, staged or
commit scope, and safest next step. An irrelevant change does not automatically
invalidate the plan.

If a relevant changed baseline makes any recorded fact stale, all locked
candidate hashes and prior approvals are invalid. Update the candidate, assign
new hashes, and obtain a fresh independent review. Preserving an old candidate
hash never takes priority over factual accuracy.

## Approval-token consistency

Every approval-gated candidate must define exactly one operative success
token. Historical, superseded, example, prohibited, and failure tokens must
be explicitly non-operative; competing operative success tokens are prohibited.

The report may separately state disposition `APPROVED` or
`APPROVED_WITH_DEFERRED_FINDINGS`. Both successful dispositions must satisfy the
candidate's stated success condition and emit its same exact operative success
token. These disposition labels are not alternative operative tokens. Before
review, ensure the candidate/protocol supports both dispositions under this
policy without weakening its technical acceptance requirements.

Approval applies only to the exact complete candidate and exact hashes reviewed.
Any byte change to an approval-bound candidate file invalidates prior approval;
a corrected candidate needs new hashes and a fresh independent review. Approval
of one subset or older version cannot authorize another subset or newer version.
Historical review records may be retained as history, but a historical approval
cannot satisfy the gate for a later corrected or expanded candidate.

Before issuing a review prompt, compare the candidate's required approval token
and condition with every successful verdict the review protocol can return. The
exact required token must be reachable through either successful disposition. Do
not begin a review while the candidate contains an obsolete, unreachable, or
differently named operative approval token.

Use this non-circular sequence for approval-gated documentation: (1) freeze the
exact candidate and hashes; (2) conduct the independent read-only review; (3)
obtain the required approval verdict; (4) obtain separate authorization for
staging and commit; (5) verify staged and committed bytes and scope; (6)
hand off to the user for manual push; (7) confirm the new clean pushed
baseline; and (8) only then begin separately authorized implementation. A
correction task is not the approval review. Do not commit before approval, or
implement before the documentation is pushed and the new clean baseline is
confirmed.

### Manifest-locked dirty aggregate-candidate exception

The clean-published-baseline sequence above remains the ordinary rule. One
narrow exception is available only for an authority correction layered over an
already-existing implementation candidate that must be intentionally preserved
unstaged. It is not available merely because a worktree is dirty.

The exception applies only when a specific authority records all of these
preconditions:

1. cleanup, discard, restore, stash, premature staging, and premature
   implementation commit are prohibited because the existing implementation
   candidate must remain byte-exact;
2. the authority correction must be layered over that same aggregate candidate;
3. committing only the authority documents cannot create a clean worktree, and
   committing the aggregate candidate would bypass named deterministic,
   separately authorized Live, freeze, Gate, and independent-review boundaries;
4. repository and branch identity, `HEAD`, local `origin/main`, ahead/behind,
   the exact dirty-path inventory, every dirty path's SHA-256, complete-diff
   byte size and SHA-256, empty index, absence of untracked paths and conflicts,
   and absence of active Git operations identify the complete starting state;
5. an exact authority-document budget, protected-path hashes, allowed
   implementation-delta paths, allowed inventory transitions, and final
   aggregate inventory are explicit; and
6. the authority correction receives its own fresh independent read-only
   approval before implementation.

When all preconditions hold, the approved starting manifest is a narrowly
authorized substitute for the ordinary pre-implementation documentation-
publication and clean-baseline gate for that exact aggregate candidate only. It
is not a Git-clean baseline and creates no general permission to implement in a
dirty worktree. The authority documents are not separately staged, committed,
or pushed. A correction that receives findings is corrected within its exact
document budget and independently re-reviewed; only an approving re-review may
lock the resulting complete dirty-candidate manifest.

Before every later task, verify the applicable starting or successor manifest,
including all Git identities, path inventories, per-path hashes, complete-diff
size/hash, index, untracked/conflict state, and active-operation state. Verify
that protected paths remain exact and that each changed or newly dirty path is
an expressly allowed transition. Any unexplained identity, path, hash, or
inventory drift blocks the task; it must not be normalized through cleanup or
absorbed as unrelated work. The manifest itself authorizes no implementation,
validation, Live traffic, staging, commit, push, or unrelated edit.

After independent authority approval, the remaining sequence is: separately
authorize the exact implementation delta; complete deterministic verification;
separately authorize any required Live evidence; freeze the complete aggregate
candidate; complete every formal Gate and independent implementation review;
then, and only under separate authorization, stage the complete approved
aggregate candidate and create one intentional aggregate commit. The user
performs the manual push. This exception waives none of those downstream gates
and permits no unrelated dirty-worktree expansion.

## Environment startup

For tasks requiring project runtime verification on Windows (documentation-only
work uses document checks without startup scripts):

1. start from PowerShell 7+ using `pwsh`;
2. enter the repository;
3. for authorized non-offline runtime work, run the command below; for offline
   work, follow Offline and database modes instead:

    .\scripts\doctor.ps1 -Strict

4. use only:

    .\.venv\Scripts\python.exe

Do not use system Python, bare `python`, or global packages.

If `.venv` is missing or broken, stop and report it.

Chinese text must be read and written as UTF-8.
External evidence wrappers must also configure their own stdout/stderr encoding,
not only the subprocess environment. During S7-1 verification, an otherwise
UTF-8 child produced a Vitest symbol that failed the wrapper's Windows legacy
encoder before exit-status recording. Configure UTF-8 before streaming, retain
the interrupted record, and rerun only the affected command when no trustworthy
completion record exists. Do not interpret a wrapper failure as a test verdict.

## Offline and database modes

When runtime verification is required and the task prohibits database or model
access, use the sanitized child process launched by:

    .\scripts\verify.ps1 -Mode Offline

Use `.\scripts\doctor.ps1 -Strict -RequireOffline` only to verify intentionally
that the current process is already clean. Do not run the general startup
doctor first for an offline task. Documentation-only checks require neither
script; they must not read secrets or invoke database or Provider code.

If required Offline mode is unavailable, stop and report the missing tooling
instead of running Full or MySQL verification with inherited environment
variables.

Offline runtime verification must not receive:

* `TEST_DATABASE_URL`;
* `DATABASE_URL`;
* `DEEPSEEK_API_KEY`;
* `RUN_LIVE_DEEPSEEK_TEST`.

Do not print their values.

MySQL integration tests may run only after safely confirming:

    driver: mysql+asyncmy
    database: deviation_protocol_test

Never display the complete URL.

Before combining schema-changing test groups, inspect each group's migration
target and shared runtime fixture, not just its test name or the current
Alembic head. A historical migration's direct amendment can conflict with a
shared fixture that now deploys a later schema. S7-4 verification confirmed
this when historical 008 tests used the current 010 runtime fixture: teardown
refused the mismatched CHECKs and later groups inherited that failure. Run
compatible groups sequentially with explicit preconditions; use verified
applicable historical evidence for unchanged migration internals. If a group
fails restoration, stop schema-changing testing, record actual rows and
constraints, inspect and repair only the known failed prefix, and verify the
recorded initial state before starting another group. Preserve failed logs;
never count a later passing group as making the earlier run pass.

On Windows, pytest can reach 100% test progress and then fail its final cleanup
of the shared temporary-directory link `pytest-current`. S7-2 verification
repeatedly observed sandbox `WinError 5` at that boundary. Progress dots do not
establish a successful verification: retain the raw log and nonzero exit, then
rerun the exact operation outside the sandbox under the repository escalation
rule. Do not relabel the interrupted run as a canonical pass or delete unrelated
pytest temporary directories. If the same operation fails outside the sandbox,
diagnose its OS permissions or file locks normally. S7-4 reproduced denial of
that shared temporary root outside the sandbox; the affected script tests passed
with a new task-owned `--basetemp`. Verify that the resolved replacement path is
inside the task workspace and does not already exist before using it. Preserve
the failed command and identify the successful affected-test replacement; do not
remove another session's temporary directories or silently relabel the broad run.
Reconcile exact affected node outcomes as well as command exits: S7-4 replacement
commands covered 211 passes and one existing Windows symlink-privilege skip, not
212 passes. Preserve the skipped node, reason and unexercised assertion; do not
add overlapping selection totals.

A sandbox network failure does not prove that a provider key is invalid.

## Live Provider calls

Normal implementation, review, CI, Quick, Full, MySQL, Security, and Offline
verification must not call DeepSeek.

A live call requires:

* explicit user authorization;
* the dedicated live-test flag;
* a known maximum number of requests;
* retry disabled unless specifically authorized;
* removal of the live flag after the test.

Never ask the user to paste a key into chat.

Never print Authorization headers, keys, complete Provider responses containing
sensitive data, or complete database URLs.

## Live-evidence preflight

Before any manually operated, networked, paid, quota-consuming, or non-repeatable
Live diagnostic begins, the responsible task must:

1. enumerate every datum required for pass/fail adjudication;
2. identify each datum's authoritative source;
3. identify the privacy-safe evidence surface through which each datum will be
   collected;
4. prove with deterministic fake/offline evidence that zero, absence, invalid
   data, and ordinary nonzero values are distinguishable where applicable;
5. confirm that the operator can actually access every required evidence
   surface before paid traffic begins; and
6. stop before Live traffic if any required datum lacks an authorized observable
   surface.

Do not substitute an unrelated UI total, narrative inference, raw protected log,
secret-bearing output, Provider request count for an application-result field,
manual guess, or retrospective reconstruction after a non-repeatable action.

## Baseline and final verification

Choose verification by demonstrated impact and the applicable technical contract:

| Change or milestone | Required verification |
| --- | --- |
| Documentation only | Relevant document checks, links, complete diff, tracked/new-file whitespace, UTF-8/LF, final newline, and scope; no project runtime verification by default |
| Code | Focused behavioral tests and affected regressions; meaningful coverage for fixed code defects and state mutations |
| Persistence, schema, or concurrency | Relevant real-MySQL, transaction, migration, and failure-path proof |
| Shared or broad changes | Broaden regression coverage according to demonstrated impact |
| Playable or release milestone | Integrated end-to-end proof and appropriate comprehensive verification |

Reuse evidence only while relevant code, dependencies, environment assumptions,
and test scope remain applicable; state the original result and why reuse is
valid. Do not rerun expensive unchanged suites merely because prose changed.
Do not silently skip a specifically required technical test, substitute SQLite
or mocks for required real-MySQL evidence, or rely on future CI to omit necessary
local verification. Missing required evidence remains missing until supplied.

Use repository scripts for applicable runtime verification rather than
reconstructing them in every session.

Typical commands are:

    .\scripts\verify.ps1 -Mode Quick
    .\scripts\verify.ps1 -Mode Full
    .\scripts\verify.ps1 -Mode MySQL
    .\scripts\verify.ps1 -Mode Security
    .\scripts\verify.ps1 -Mode Offline

Use only the modes authorized by the task.

If verification cannot run safely, report the exact missing prerequisite and
stop. Do not silently substitute a weaker environment or interpreter.

Verification runners must stream output from commands that are not explicitly
marked for safe parsing. On failure, preserve the native command's diagnostic
output and first traceback; do not replace it with only a stage-level exit-code
message.

## Context and prompt discipline

Keep one prompt focused on one bounded phase.

A prompt should state:

* allowed scope;
* prohibited scope;
* trust and persistence boundaries;
* required tests;
* whether database or Provider access is allowed;
* whether Git writes are allowed;
* final report requirements.

Do not resend a complete previous prompt when only a focused audit or small
follow-up is required.

If the Codex window becomes slow because of long context, finish the current
safe checkpoint and start a new session that reads the repository state.

## Confirmed-issue classification

Before handoff, classify every confirmed issue:

### Fixed code defect

Add or update meaningful regression coverage. Deferral alone requires no fix
or artificial test.

### Reusable engineering or safety rule

Add or update an entry in:

    docs/engineering/guardrails.md

### Codex session, environment, review, or Git workflow failure

Update this file.

### Unresolved confirmed defect

Classify it under Findings and milestone disposition above. Report blockers;
record eligible non-blocking findings in the canonical deferred-findings
register and continue. Create an external tracked issue only when authorized.

### Speculation or unconfirmed concern

Do not record it as confirmed debt or a guardrail. Investigate plausible serious
risks enough to classify them and report essential evidence gaps.

Every implementation and review report must include:

Guardrail impact:
    - Added: <guardrail IDs>
    - Updated: <guardrail IDs>
    - None

`None` is appropriate only when no confirmed issue created or changed a
reusable rule.

## Canonical documentation-synchronization checklist

Complete this checklist before an independent audit, before describing a phase
as complete, and before requesting authorization to commit:

1. Identify every code, behavior, interface, test, and phase-status change.
2. Identify the canonical document that owns each changed fact or decision.
3. Update implementation documentation during the same work round.
4. Keep code, tests, `PLANS.md`, phase documentation, and applicable guardrails
   consistent.
5. Record new constraints, decisions, limitations, and verification evidence.
6. Use PLANS.md status language, including its separate component, integrated
   play, limited-trial, and broader-release evidence levels.
7. Check whether a confirmed failure requires a guardrail update.
8. Do not add speculative guardrails without a confirmed failure and an
   enforcement mechanism.
9. Check documentation coverage before independent audit.
10. Do not describe a phase as complete while required documentation is
    missing.
11. Run applicable documentation validation and Git diff checks.
12. Verify that no unrelated file entered the change inventory.
13. Request commit authorization only after implementation, tests, and
    documentation agree.
14. Commit only with explicit user authorization for that exact commit
    operation.
15. Never push; the user performs every push manually.

Do not create separate lifecycle-closeout tasks by default. Synchronize current
status in the next relevant authorized documentation change; preserve historical
approvals and frozen candidate bytes.

## Git handoff

Codex does not stage unless explicitly authorized. Codex may create a local
commit only when the user explicitly authorizes that exact commit operation.
Codex never pushes; the user performs every push manually.

For an explicitly authorized staging/commit operation:

1. inspect `git status --short`;
2. inspect all untracked files;
3. stage only reviewed paths;
4. run:

    git diff --cached --check
    git diff --cached --stat
    git status --short

5. confirm no unrelated files are staged.

The committing session must also verify committed bytes and scope against the
reviewed candidate. A separate independent post-commit audit is not required
by default; this does not remove pre-commit independent review requirements.

Never commit:

* `.env`;
* credentials;
* complete URLs;
* reference fiction;
* audit transcripts;
* generated scenario drafts;
* `__pycache__`;
* `.pyc`;
* local test output;
* editor or operating-system caches.

When an ignored generated file is visible, use `git check-ignore` before
deciding whether it belongs in the commit.

## Handoff report

A final implementation or review report should contain:

1. outcome;
2. modified and new files;
3. actual data or transaction flow when relevant;
4. confirmed defects and fixes;
5. test and verification results;
6. database, Provider, and network access performed;
7. migrations or schema impact;
8. remaining limitations;
9. Guardrail impact;
10. final Git status;
11. whether the change is ready for independent review or commit.

Do not claim guarantees that were not demonstrated by code or tests.
