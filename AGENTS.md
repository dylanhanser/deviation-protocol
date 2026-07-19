# Repository constraints

- Use Python 3.12.
- On Windows, use `.\.venv\Scripts\python.exe` explicitly for all project Python commands.
- Run tests with `.\.venv\Scripts\python.exe -m pytest`.
- Run compilation checks with `.\.venv\Scripts\python.exe -m compileall -q src tests alembic`.
- Do not use bare `python`, `python3`, or the system Python installation on Windows.
- Do not install project dependencies globally.
- If `.venv` is missing or broken, stop and report it instead of silently recreating it.
- Use MySQL 8 with SQLAlchemy `AsyncSession` and `asyncmy`; never add a SQLite fallback.
- Keep dependencies directed toward the domain. `domain` must not depend on `infrastructure`.
- Implement player-action constraints as independent policy classes.
- Never allow model output to rewrite fixed story facts.
- Add tests for every state mutation.
- Never read, commit, or print secrets from `.env`.
- When database models change, check the matching Alembic migration.
- After changes, run the full tests, `compileall`, and relevant Alembic checks.

See `docs/architecture.md` for the detailed design boundaries.
