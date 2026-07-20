# Codex Workflow

This document defines how Codex implementation and review sessions should be
run for this repository.

Technical safety rules are recorded in
`docs/engineering/guardrails.md`.

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
3. run the required baseline tests;
4. implement only the authorized phase;
5. add regression tests for every confirmed defect or state mutation;
6. run the required final verification;
7. report modified and untracked files;
8. stop without staging, committing, or pushing unless explicitly authorized.

Do not begin the next phase during the current phase's implementation or
review.

Do not perform unrelated cleanup or refactoring.

## Independent review session

Use a new session for independent review.

A review session must:

- read the complete current diff, including untracked files;
- verify that implementation claims match actual code and tests;
- reproduce deterministic defects before fixing them;
- make only minimal in-scope fixes;
- add regression tests for each confirmed fix;
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

## Environment startup

On Windows:

1. start from PowerShell 7+ using `pwsh`;
2. enter the repository;
3. run:

    .\scripts\doctor.ps1 -Strict

4. use only:

    .\.venv\Scripts\python.exe

Do not use system Python, bare `python`, or global packages.

If `.venv` is missing or broken, stop and report it.

Chinese text must be read and written as UTF-8.

## Offline and database modes

When a task explicitly prohibits database or model access, use:

    .\scripts\doctor.ps1 -Strict -RequireOffline
    .\scripts\verify.ps1 -Mode Offline

If these modes are not yet implemented, stop and report the missing tooling
instead of running Full or MySQL verification with inherited environment
variables.

Offline work must not receive:

* `TEST_DATABASE_URL`;
* `DATABASE_URL`;
* `DEEPSEEK_API_KEY`;
* `RUN_LIVE_DEEPSEEK_TEST`.

Do not print their values.

MySQL integration tests may run only after safely confirming:

    driver: mysql+asyncmy
    database: deviation_protocol_test

Never display the complete URL.

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

## Baseline and final verification

Use the repository scripts rather than reconstructing validation commands in
every session.

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

### Code regression

Add or update a regression test.

### Reusable engineering or safety rule

Add or update an entry in:

    docs/engineering/guardrails.md

### Codex session, environment, review, or Git workflow failure

Update this file.

### Unresolved confirmed defect

Report it explicitly as a blocker. Create an external tracked issue only when
the user authorizes it.

### Speculation or unconfirmed concern

Do not add it to the repository.

Every implementation and review report must include:

Guardrail impact:
    - Added: <guardrail IDs>
    - Updated: <guardrail IDs>
    - None

`None` is appropriate only when no confirmed issue created or changed a
reusable rule.

## Git handoff

Codex does not stage, commit, or push unless explicitly authorized.

Before user commit:

1. inspect `git status --short`;
2. inspect all untracked files;
3. stage only reviewed paths;
4. run:

    git diff --cached --check
    git diff --cached --stat
    git status --short

5. confirm no unrelated files are staged.

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
