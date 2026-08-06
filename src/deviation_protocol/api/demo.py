from __future__ import annotations

from contextlib import asynccontextmanager
import os

from deviation_protocol.api.demo_composition import (
    DynamicDemoConfigurationError,
    build_demo_runtime,
    build_dynamic_demo_runtime,
)
from deviation_protocol.api.main import create_app


_mode = os.environ.get("DEVIATION_DEMO_MODE", "deterministic")
if _mode == "deterministic":
    _runtime = build_demo_runtime()
elif _mode == "dynamic-narrative":
    _runtime = build_dynamic_demo_runtime()
else:
    raise DynamicDemoConfigurationError()

app = create_app(services=_runtime.services)
_base_lifespan = app.router.lifespan_context


@asynccontextmanager
async def _demo_lifespan(application):
    primary: BaseException | None = None
    try:
        async with _base_lifespan(application):
            yield
    except BaseException as exc:
        primary = exc
    cleanup: BaseException | None = None
    try:
        await _runtime.aclose()
    except BaseException as exc:
        cleanup = exc
    if primary is not None and cleanup is not None:
        raise BaseExceptionGroup(
            "Dynamic Demo lifespan cleanup failed", (primary, cleanup)
        )
    if primary is not None:
        raise primary
    if cleanup is not None:
        raise cleanup


app.router.lifespan_context = _demo_lifespan
