from __future__ import annotations

from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Deviation Protocol", version="0.1.0")

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        # Deliberately does not open a DB connection. Readiness checks can be added
        # separately when deployment requirements are known.
        return {"status": "ok", "phase": "foundation"}

    return app


app = create_app()
