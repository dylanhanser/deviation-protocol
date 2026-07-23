from __future__ import annotations

from deviation_protocol.api.demo_composition import build_demo_runtime
from deviation_protocol.api.main import create_app


_runtime = build_demo_runtime()
app = create_app(services=_runtime.services)
