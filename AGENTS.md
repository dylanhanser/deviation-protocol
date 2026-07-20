# Repository constraints

## Windows development environment

- On Windows, prefer PowerShell 7+ (`pwsh`) for project commands. Use Windows PowerShell 5.1 only when a legacy tool explicitly requires it.
- Prefer a normal `pwsh` session so the current-user UTF-8 profile is loaded. If a non-profile shell must print or read Chinese text, explicitly set Console input/output encoding and `$OutputEncoding` to UTF-8 first.
- Use `.\.venv\Scripts\python.exe` explicitly for all project Python commands.
- Run tests with `.\.venv\Scripts\python.exe -m pytest`.
- Run compilation checks with `.\.venv\Scripts\python.exe -m compileall -q src tests alembic`.
- Do not use bare `python`, `python3`, or the system Python installation on Windows.
- Do not install project dependencies globally.
- If `.venv` is missing or broken, stop and report it instead of silently recreating it.

## Security and persistence

- Never read, commit, or print secrets from `.env`.
- Keep `RUN_LIVE_DEEPSEEK_TEST` disabled for normal development, testing, review, CI, and Codex runs. A real model call requires explicit user opt-in.
- For tasks explicitly marked offline or no-database, run `.\scripts\verify.ps1 -Mode Offline`; it launches a sanitized child process and runs strict offline diagnostics there. If Offline mode is unavailable, stop and report it instead of running Full or MySQL verification.
- Use `.\scripts\doctor.ps1 -Strict -RequireOffline` only when intentionally verifying that the current process environment is already clean.
- Use MySQL 8 with SQLAlchemy `AsyncSession` and `asyncmy`; never add a SQLite fallback.
- When database models change, check the matching Alembic migration.

## Architecture and game authority

- Read `docs/engineering/guardrails.md` before changing persistence, trusted authority, narrative orchestration, scenario tooling, or verification workflows.
- Keep dependencies directed toward the domain. `domain` must not depend on `infrastructure`.
- Implement player-action constraints as independent policy classes.
- Never allow model output to rewrite fixed story facts.
- Treat user-provided fiction as style-only reference material; never copy its plot, names, prose, equipment, skills, or distinctive setting elements into production content.
- Ordinary creative player actions must remain normal narrative actions. They must not produce anomaly candidates unless a future trusted deviation evaluator explicitly authorizes that route.
- Add tests for every state mutation.

## Verification and issue recording

- After changes, run the full tests, `compileall`, and relevant Alembic checks.
- Add a regression test for every confirmed defect.
- When a confirmed defect establishes or changes a reusable engineering or safety rule, update `docs/engineering/guardrails.md` in the same change.
- When a confirmed failure concerns Codex sessions, environment setup, review procedure, or Git handoff, update `docs/engineering/codex_workflow.md`.
- Do not add speculative, unconfirmed, or purely one-off observations to the guardrail documents.
- Every final implementation or review report must include a `Guardrail impact` section listing added or updated guardrail IDs, or explicitly stating `None`.

See `docs/architecture.md` for detailed design boundaries.

See `docs/engineering/codex_workflow.md` for implementation, review, environment, and Git handoff workflow.
