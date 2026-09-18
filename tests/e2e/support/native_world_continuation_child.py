"""Normal deterministic Demo public ASGI transport, hosted in an isolated process.

The stdin bridge transports HTTP requests only; it cannot create or alter fixtures.
Private snapshot inspection is read-only and covers every dataclass/model field.
"""
from __future__ import annotations

import asyncio
from dataclasses import fields, is_dataclass
from datetime import datetime
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
from types import SimpleNamespace
from collections.abc import Mapping

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
ROOT = Path(__file__).parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
assert not any(os.environ.get(k) for k in ("DATABASE_URL", "TEST_DATABASE_URL", "DEEPSEEK_API_KEY", "RUN_LIVE_DEEPSEEK_TEST"))

def denied(*args, **kwargs):
    raise AssertionError("external network access forbidden in deterministic Demo evidence")

import httpx
from pydantic import BaseModel
from deviation_protocol.api.demo_composition import build_demo_runtime
from deviation_protocol.api.main import create_app
from tests.e2e.test_demo_cross_process_replay import CANONICAL_ACTIONS


def complete(value):
    if type(value) is SimpleNamespace:
        return {"type": "SimpleNamespace", "fields": complete(vars(value))}
    if isinstance(value, bytes):
        return {"bytes_hex": value.hex()}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, BaseModel):
        return {"type": type(value).__name__, "fields": complete(value.model_dump(mode="python"))}
    if is_dataclass(value):
        return {"type": type(value).__name__, "fields": {f.name: complete(getattr(value, f.name)) for f in fields(value)}}
    if isinstance(value, Mapping):
        return sorted([[complete(k), complete(v)] for k, v in value.items()], key=lambda pair: json.dumps(pair[0], sort_keys=True))
    if isinstance(value, (tuple, list)):
        return [complete(v) for v in value]
    if isinstance(value, (set, frozenset)):
        return sorted([complete(v) for v in value], key=lambda v: json.dumps(v, sort_keys=True))
    if value is None or type(value) in (str, int, bool, float):
        return value
    raise TypeError(type(value).__name__)


def emit(value):
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":")), flush=True)


async def main():
    # Windows creates the event loop's private socketpair before this coroutine.
    socket.socket.connect = denied
    socket.socket.connect_ex = denied
    socket.create_connection = denied
    runtime = build_demo_runtime()
    app = create_app(services=runtime.services)
    app.state.api_services = runtime.services
    emit({"ready": True, "actions": [{f.name: getattr(a, f.name) for f in fields(a)} for a in CANONICAL_ACTIONS]})
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://demo") as client:
        for line in sys.stdin:
            request = json.loads(line)
            if request.get("inspect"):
                snapshot = complete(runtime.store.snapshot())
                canonical = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                emit({"id": request["id"], "snapshot": snapshot, "sha256": hashlib.sha256(canonical.encode()).hexdigest()})
                continue
            response = await client.request(request["method"], request["path"], headers=request.get("headers"), content=request.get("body"))
            emit({"id": request["id"], "status": response.status_code, "body": response.json()})


if __name__ == "__main__":
    asyncio.run(main())
