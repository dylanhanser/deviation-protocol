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
- Use MySQL 8 with SQLAlchemy `AsyncSession` and `asyncmy`; never add a SQLite fallback.
- When database models change, check the matching Alembic migration.

## Architecture and game authority

- Keep dependencies directed toward the domain. `domain` must not depend on `infrastructure`.
- Implement player-action constraints as independent policy classes.
- Never allow model output to rewrite fixed story facts.
- Add tests for every state mutation.

## Verification

- After changes, run the full tests, `compileall`, and relevant Alembic checks.

See `docs/architecture.md` for the detailed design boundaries.