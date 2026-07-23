from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import threading
import time
from typing import Any, BinaryIO, Callable

import httpx
import pytest


REPOSITORY_ROOT = Path(__file__).parents[2]
PROJECT_PYTHON = REPOSITORY_ROOT / ".venv" / "Scripts" / "python.exe"
CHILD_BOOTSTRAP = (
    REPOSITORY_ROOT / "tests" / "e2e" / "support" / "demo_replay_child.py"
)
TRACE_PROTOCOL = "deviation-demo-generator-trace"
TRACE_VERSION = 1
TRACE_CATEGORIES = frozenset(
    {
        "CLOCK",
        "SESSION_ID",
        "EVENT_ID",
        "JOB_ID",
        "LEASE_TOKEN",
        "WORKER_ID",
        "SEED",
    }
)
GENERATOR_KEYS = frozenset(
    {
        "protocol",
        "version",
        "record_type",
        "global_ordinal",
        "category",
        "category_ordinal",
        "raw_value",
    }
)
COMPLETE_KEYS = frozenset(
    {
        "protocol",
        "version",
        "record_type",
        "record_count",
        "last_global_ordinal",
    }
)
ACTION_PATH = re.compile(r"^/v1/sessions/[^/]+/actions$")
REQUEST_STATUS_PATH = re.compile(r"^/v1/sessions/[^/]+/requests/[^/]+$")
EXPECTED_EXACT_REPLAY_SHA256 = (
    "383fd47b7ab72128ba630fbbe0b513f13f80504ba4aecc969d32ca3dd6d0394b"
)
EXPECTED_NORMALIZED_REPLAY_SHA256 = (
    "3bf5810a398cbf29c2f63ea89695c702404a5256f467a58177f77888f3b76210"
)


@dataclass(frozen=True, slots=True)
class ActionStep:
    action_type: str
    choice_id: str | None = None
    description: str | None = None


CANONICAL_ACTIONS = (
    ActionStep("CHOOSE", choice_id="death_certificate.action.move_fingers_rhythmically"),
    ActionStep("CUSTOM", description="请协调员复核我的连续回应和生命体征"),
    ActionStep("CONTINUE"),
    ActionStep("CONTINUE"),
    ActionStep("CHOOSE", choice_id="death_certificate.action.prove_vitals"),
    ActionStep("CONTINUE"),
    ActionStep("CONTINUE"),
    ActionStep("CONTINUE"),
    ActionStep("CHOOSE", choice_id="death_certificate.action.inspect_archive"),
    ActionStep("EXPLORE", description="沿记录与档案审计路径核对签发时间"),
    ActionStep("EXPLORE", description="核对日志时间顺序以及规程反馈"),
    ActionStep("CHOOSE", choice_id="death_certificate.action.open_observation"),
    ActionStep("OBSERVE", description="复核地下患者的生命体征与连续监测历史"),
    ActionStep("CONTINUE"),
    ActionStep("CONTINUE"),
    ActionStep("CHOOSE", choice_id="death_certificate.action.pause_protocol"),
    ActionStep("CHOOSE", choice_id="death_certificate.action.ask_coordinator"),
    ActionStep("CHOOSE", choice_id="death_certificate.action.public_override"),
    ActionStep("CHOOSE", choice_id="death_certificate.action.final_suspend"),
)
ACTION_EVENT_COUNTS = (1, 2, 1, 2, 1, 1, 1, 1, 1, 1, 4, 2, 2, 1, 1, 1, 1, 1, 1)
PROVIDER_ACTIONS = frozenset({2, 10, 11, 13})
PUBLIC_CLOCKS_AFTER_ACTION = (
    (0, 0),
    (1, 0),
    (2, 1),
    (3, 2),
    (4, 2),
    (4, 3),
    (4, 4),
    (4, 5),
    (4, 6),
    (4, 7),
    (4, 8),
    (4, 9),
    (4, 10),
    (4, 11),
    (4, 12),
    (4, 12),
    (4, 12),
    (4, 12),
    (4, 12),
)


@dataclass(frozen=True, slots=True)
class ReplayResult:
    transcript: tuple[dict[str, Any], ...]
    trace: tuple[dict[str, Any], ...]
    stdout: bytes
    stderr: bytes
    hash_seed: str


class _DrainThread:
    def __init__(self, stream: BinaryIO, *, name: str) -> None:
        self._stream = stream
        self._chunks: list[bytes] = []
        self._error: BaseException | None = None
        self._thread = threading.Thread(target=self._run, name=name, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def join(self, timeout: float) -> bytes:
        self._thread.join(timeout)
        if self._thread.is_alive():
            raise RuntimeError("pipe reader did not drain EOF")
        if self._error is not None:
            raise RuntimeError("pipe reader failed") from self._error
        return b"".join(self._chunks)

    def _run(self) -> None:
        try:
            while True:
                chunk = self._stream.read(65536)
                if not chunk:
                    return
                self._chunks.append(chunk)
        except BaseException as exc:
            self._error = exc
        finally:
            self._stream.close()


class DemoBackendChild:
    def __init__(
        self,
        *,
        hash_seed: str,
        identity_family: str = "same",
        timeout_seconds: int | float = 60,
        private_mutation: str | None = None,
        fault_mode: str | None = None,
    ) -> None:
        if hash_seed not in {"1", "2"}:
            raise ValueError("replay hash seed must be 1 or 2")
        if identity_family not in {"same", "browser-a", "browser-b"}:
            raise ValueError("replay identity family is not frozen")
        self.timeout_seconds = validate_timeout(timeout_seconds)
        self.hash_seed = hash_seed
        self.identity_family = identity_family
        self.private_mutation = private_mutation
        self.fault_mode = fault_mode
        self.port = _reserve_loopback_port()
        self._deadline = time.monotonic() + self.timeout_seconds
        self._process: subprocess.Popen[bytes] | None = None
        self._control: BinaryIO | None = None
        self._trace_drain: _DrainThread | None = None
        self._stdout_drain: _DrainThread | None = None
        self._stderr_drain: _DrainThread | None = None
        self._stop_sent = False
        self._terminate_grace_seconds = 5

    def start(self) -> None:
        if self._process is not None:
            raise RuntimeError("replay child was already started")
        trace_read, trace_write = os.pipe()
        control_read, control_write = os.pipe()
        child_descriptors = (trace_write, control_read)
        parent_descriptors = (trace_read, control_write)
        process: subprocess.Popen[bytes] | None = None
        inheritance_restorers: list[Callable[[], None]] = []
        try:
            environment = _sanitized_child_environment(self.hash_seed)
            command = [
                str(PROJECT_PYTHON),
                str(CHILD_BOOTSTRAP),
                "--port",
                str(self.port),
                "--identity-family",
                self.identity_family,
            ]
            if self.private_mutation is not None:
                command.extend(("--private-mutation", self.private_mutation))
            if self.fault_mode is not None:
                command.extend(("--fault-mode", self.fault_mode))
            popen_options: dict[str, Any] = {}
            if os.name == "nt":
                import msvcrt

                child_handles = tuple(
                    msvcrt.get_osfhandle(descriptor) for descriptor in child_descriptors
                )
                for handle in child_handles:
                    previous = os.get_handle_inheritable(handle)
                    os.set_handle_inheritable(handle, True)
                    inheritance_restorers.append(
                        lambda handle=handle, previous=previous: os.set_handle_inheritable(
                            handle, previous
                        )
                    )
                startup_info = subprocess.STARTUPINFO()
                startup_info.lpAttributeList = {"handle_list": list(child_handles)}
                command.extend(
                    (
                        "--trace-write-handle",
                        str(child_handles[0]),
                        "--control-read-handle",
                        str(child_handles[1]),
                    )
                )
                popen_options["startupinfo"] = startup_info
                popen_options["creationflags"] = subprocess.CREATE_NO_WINDOW
            else:
                for descriptor in child_descriptors:
                    previous = os.get_inheritable(descriptor)
                    os.set_inheritable(descriptor, True)
                    inheritance_restorers.append(
                        lambda descriptor=descriptor, previous=previous: os.set_inheritable(
                            descriptor, previous
                        )
                    )
                command.extend(
                    (
                        "--trace-write-handle",
                        str(trace_write),
                        "--control-read-handle",
                        str(control_read),
                    )
                )
                popen_options["pass_fds"] = child_descriptors
            process = subprocess.Popen(
                command,
                cwd=REPOSITORY_ROOT,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                close_fds=True,
                shell=False,
                **popen_options,
            )
            self._process = process
        finally:
            for restore in reversed(inheritance_restorers):
                restore()
            for descriptor in child_descriptors:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            if process is None:
                for descriptor in parent_descriptors:
                    try:
                        os.close(descriptor)
                    except OSError:
                        pass
        assert process is not None
        assert process.stdout is not None and process.stderr is not None
        self._control = os.fdopen(control_write, "wb", buffering=0)
        self._trace_drain = _DrainThread(
            os.fdopen(trace_read, "rb", buffering=0), name=f"trace-{process.pid}"
        )
        self._stdout_drain = _DrainThread(process.stdout, name=f"stdout-{process.pid}")
        self._stderr_drain = _DrainThread(process.stderr, name=f"stderr-{process.pid}")
        self._trace_drain.start()
        self._stdout_drain.start()
        self._stderr_drain.start()
        self._wait_until_ready()

    def stop_and_collect(self) -> tuple[tuple[dict[str, Any], ...], bytes, bytes]:
        process = self._owned_process()
        if self._control is None or self._stop_sent:
            raise RuntimeError("replay control pipe is unavailable")
        self._control.write(b"STOP\n")
        self._control.flush()
        self._control.close()
        self._control = None
        self._stop_sent = True
        try:
            exit_code = process.wait(timeout=self._remaining())
        except subprocess.TimeoutExpired:
            self._terminate_owned(process)
            raise TimeoutError("replay child exceeded its owned timeout") from None
        trace_bytes, stdout, stderr = self._join_drains()
        _require_successful_exit(exit_code, stderr)
        return _parse_trace(trace_bytes), stdout, stderr

    def cleanup(self) -> None:
        process = self._process
        if self._control is not None:
            self._control.close()
            self._control = None
        if process is not None and process.poll() is None:
            self._terminate_owned(process)
        if process is not None:
            try:
                self._join_drains()
            except RuntimeError:
                pass

    def _wait_until_ready(self) -> None:
        process = self._owned_process()
        url = f"http://127.0.0.1:{self.port}/health"
        with httpx.Client(timeout=0.5, trust_env=False) as client:
            while True:
                if process.poll() is not None:
                    _, _, stderr = self._join_drains()
                    raise RuntimeError(
                        f"replay child exited before readiness ({stderr!r})"
                    )
                try:
                    response = client.get(url)
                    if response.status_code == 200 and response.json() == {
                        "status": "ok",
                        "phase": "3.0",
                    }:
                        return
                except (httpx.HTTPError, ValueError):
                    pass
                if self._remaining() <= 0:
                    self._terminate_owned(process)
                    raise TimeoutError("replay child readiness timed out")
                time.sleep(0.02)

    def _join_drains(self) -> tuple[bytes, bytes, bytes]:
        if (
            self._trace_drain is None
            or self._stdout_drain is None
            or self._stderr_drain is None
        ):
            raise RuntimeError("replay pipe drains were not started")
        return (
            self._trace_drain.join(max(self._remaining(), 0.1)),
            self._stdout_drain.join(max(self._remaining(), 0.1)),
            self._stderr_drain.join(max(self._remaining(), 0.1)),
        )

    def _owned_process(self) -> subprocess.Popen[bytes]:
        if self._process is None:
            raise RuntimeError("replay child is not owned by this runner")
        return self._process

    def _terminate_owned(self, process: subprocess.Popen[bytes]) -> None:
        if process is not self._process:
            raise RuntimeError("refusing to terminate an unowned process")
        if process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=self._terminate_grace_seconds)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=self._terminate_grace_seconds)

    def _remaining(self) -> float:
        return max(self._deadline - time.monotonic(), 0.0)


def validate_timeout(value: int | float) -> float:
    if type(value) not in (int, float) or not 10 <= value <= 300:
        raise ValueError("replay timeout must be between 10 and 300 seconds")
    return float(value)


def _reserve_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _sanitized_child_environment(hash_seed: str) -> dict[str, str]:
    forbidden_exact = {
        "DATABASE_URL",
        "TEST_DATABASE_URL",
        "DEEPSEEK_API_KEY",
        "RUN_LIVE_DEEPSEEK_TEST",
    }
    environment = {
        key: value
        for key, value in os.environ.items()
        if key.upper() not in forbidden_exact
        and not key.upper().startswith("DEEPSEEK_")
    }
    environment["PYTHONHASHSEED"] = hash_seed
    environment["NO_PROXY"] = "127.0.0.1,localhost"
    environment["no_proxy"] = "127.0.0.1,localhost"
    return environment


def _require_successful_exit(exit_code: int, stderr: bytes) -> None:
    if type(exit_code) is not int or exit_code != 0:
        raise RuntimeError(f"replay child exited nonzero ({exit_code}); stderr={stderr!r}")


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant is forbidden: {value}")


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _parse_trace(data: bytes) -> tuple[dict[str, Any], ...]:
    if not data or not data.endswith(b"\n") or b"\r" in data:
        raise ValueError("trace must be non-empty LF-terminated JSONL without CR")
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("trace is not strict UTF-8") from exc
    lines = text.split("\n")
    if lines[-1] != "" or any(line == "" for line in lines[:-1]):
        raise ValueError("trace contains a blank or unterminated record")
    messages: list[dict[str, Any]] = []
    for line in lines[:-1]:
        value = json.loads(
            line,
            parse_constant=_reject_json_constant,
            object_pairs_hook=_unique_json_object,
        )
        if not isinstance(value, dict):
            raise ValueError("trace record is not an object")
        messages.append(value)
    if not messages or set(messages[-1]) != COMPLETE_KEYS:
        raise ValueError("trace completion record is missing or misplaced")
    completion = messages[-1]
    records = messages[:-1]
    if any(message.get("record_type") == "COMPLETE" for message in records):
        raise ValueError("trace completion is duplicated")
    category_ordinals: Counter[str] = Counter()
    for expected_global, record in enumerate(records, start=1):
        if set(record) != GENERATOR_KEYS:
            raise ValueError("generator trace key set differs")
        category = record["category"]
        if (
            record["protocol"] != TRACE_PROTOCOL
            or type(record["version"]) is not int
            or record["version"] != TRACE_VERSION
            or record["record_type"] != "GENERATOR"
            or type(record["global_ordinal"]) is not int
            or record["global_ordinal"] != expected_global
            or type(category) is not str
            or category not in TRACE_CATEGORIES
        ):
            raise ValueError("generator trace envelope or global order differs")
        category_ordinals[category] += 1
        if (
            type(record["category_ordinal"]) is not int
            or record["category_ordinal"] != category_ordinals[category]
            or (category == "SEED" and type(record["raw_value"]) is not int)
            or (category != "SEED" and type(record["raw_value"]) is not str)
        ):
            raise ValueError("generator category order or raw type differs")
    if (
        completion["protocol"] != TRACE_PROTOCOL
        or type(completion["version"]) is not int
        or completion["version"] != TRACE_VERSION
        or completion["record_type"] != "COMPLETE"
        or type(completion["record_count"]) is not int
        or completion["record_count"] != len(records)
        or type(completion["last_global_ordinal"]) is not int
        or completion["last_global_ordinal"] != len(records)
    ):
        raise ValueError("trace completion values differ")
    expected = _expected_generator_trace()
    if records != list(expected):
        raise ValueError("actual generator trace differs from semantically derived trace")
    return tuple(records)


def _expected_generator_trace() -> tuple[dict[str, Any], ...]:
    records: list[dict[str, Any]] = []
    category_ordinals: Counter[str] = Counter()

    def emit(category: str) -> None:
        category_ordinals[category] += 1
        ordinal = category_ordinals[category]
        if category == "CLOCK":
            raw_value: str | int = (
                datetime(2000, 1, 1, tzinfo=timezone.utc)
                + timedelta(seconds=ordinal - 1)
            ).isoformat()
        elif category == "SEED":
            raw_value = ordinal
        else:
            prefix, width = {
                "SESSION_ID": ("demo-session-", 8),
                "EVENT_ID": ("demo-event-", 8),
                "JOB_ID": ("demo-job-", 8),
                "LEASE_TOKEN": ("demo-lease-", 21),
                "WORKER_ID": ("demo-worker-", 8),
            }[category]
            raw_value = f"{prefix}{ordinal:0{width}d}"
        records.append(
            {
                "protocol": TRACE_PROTOCOL,
                "version": TRACE_VERSION,
                "record_type": "GENERATOR",
                "global_ordinal": len(records) + 1,
                "category": category,
                "category_ordinal": ordinal,
                "raw_value": raw_value,
            }
        )

    emit("CLOCK")
    emit("SESSION_ID")
    emit("SEED")
    emit("EVENT_ID")
    for action_number, event_count in enumerate(ACTION_EVENT_COUNTS, start=1):
        if action_number in PROVIDER_ACTIONS:
            emit("CLOCK")
            emit("JOB_ID")
            emit("CLOCK")
            emit("LEASE_TOKEN")
            emit("WORKER_ID")
            emit("CLOCK")
            emit("CLOCK")
            emit("CLOCK")
        for _ in range(event_count):
            emit("EVENT_ID")
            emit("CLOCK")
        if action_number in PROVIDER_ACTIONS:
            emit("CLOCK")
        if action_number == len(ACTION_EVENT_COUNTS):
            emit("CLOCK")
            emit("JOB_ID")
    return tuple(records)


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _difference_paths(left: Any, right: Any, *, path: str = "$") -> tuple[str, ...]:
    if type(left) is not type(right):
        return (path,)
    if isinstance(left, dict):
        if set(left) != set(right):
            return (path + ".<keys>",)
        differences: list[str] = []
        for key in sorted(left):
            differences.extend(
                _difference_paths(left[key], right[key], path=f"{path}.{key}")
            )
        return tuple(differences)
    if isinstance(left, (list, tuple)):
        if len(left) != len(right):
            return (path + ".<length>",)
        differences = []
        for index, (left_item, right_item) in enumerate(zip(left, right, strict=True)):
            differences.extend(
                _difference_paths(left_item, right_item, path=f"{path}[{index}]")
            )
        return tuple(differences)
    return () if left == right else (path,)


def _record_exchange(
    transcript: list[dict[str, Any]],
    *,
    method: str,
    path: str,
    request_body: dict[str, Any] | None,
    response: httpx.Response,
    expected_status: int,
) -> dict[str, Any]:
    if response.status_code != expected_status:
        raise AssertionError(
            f"{method} {path} returned {response.status_code}: {response.text}"
        )
    try:
        response_body = response.json()
    except ValueError as exc:
        raise AssertionError(f"{method} {path} did not return JSON") from exc
    transcript.append(
        {
            "method": method,
            "path": path,
            "request": deepcopy(request_body),
            "status": response.status_code,
            "response": response_body,
        }
    )
    return response_body


def _identity(family: str, category: str, ordinal: int | None = None) -> str:
    suffix = "" if ordinal is None else f"-{ordinal:02d}"
    return f"opaque-{family}-{category}{suffix}"


def _drive_public_path(child: DemoBackendChild, *, identity_family: str) -> tuple[dict[str, Any], ...]:
    transcript: list[dict[str, Any]] = []
    base_url = f"http://127.0.0.1:{child.port}"
    with httpx.Client(base_url=base_url, timeout=5, trust_env=False) as client:
        catalog = _record_exchange(
            transcript,
            method="GET",
            path="/v1/scenarios",
            request_body=None,
            response=client.get("/v1/scenarios"),
            expected_status=200,
        )
        scenario = next(
            item for item in catalog["scenarios"] if item["scenario_id"] == "death_certificate"
        )
        create_body = {
            "client_request_id": _identity(identity_family, "create"),
            "character_definition_id": scenario["default_character_definition_id"],
            "scenario_id": scenario["scenario_id"],
        }
        created = _record_exchange(
            transcript,
            method="POST",
            path="/v1/sessions",
            request_body=create_body,
            response=client.post("/v1/sessions", json=create_body),
            expected_status=201,
        )
        session_id = created["session_id"]
        assert session_id == "demo-session-00000001"
        view_path = f"/v1/sessions/{session_id}/view"
        action_path = f"/v1/sessions/{session_id}/actions"
        initial_view = _record_exchange(
            transcript,
            method="GET",
            path=view_path,
            request_body=None,
            response=client.get(view_path),
            expected_status=200,
        )
        assert initial_view["metadata"]["state_version"] == 0
        assert initial_view["action_affordances"]["mode"] == "DECISION"

        resulting_versions: list[int] = []
        for ordinal, step in enumerate(CANONICAL_ACTIONS, start=1):
            authoritative = _record_exchange(
                transcript,
                method="GET",
                path=view_path,
                request_body=None,
                response=client.get(view_path),
                expected_status=200,
            )
            assert authoritative["metadata"]["state_version"] == ordinal - 1
            affordances = authoritative["action_affordances"]
            body: dict[str, Any] = {
                "turn_id": _identity(identity_family, "turn", ordinal),
                "client_request_id": _identity(identity_family, "action", ordinal),
                "action_type": step.action_type,
            }
            if step.action_type == "CHOOSE":
                assert affordances["mode"] == "DECISION"
                assert step.choice_id in {
                    choice["choice_id"] for choice in affordances["choices"]
                }
                body["decision_id"] = affordances["decision_id"]
                body["choice_id"] = step.choice_id
            else:
                assert affordances["mode"] == "FREE_ACTIONS"
                advertised = next(
                    action
                    for action in affordances["actions"]
                    if action["action_type"] == step.action_type
                )
                assert advertised["target_required"] is False
                if step.description is not None:
                    assert advertised["input_kind"] == "DESCRIPTION"
                    assert advertised["max_input_length"] == 150
                    body["description"] = step.description
                else:
                    assert step.action_type == "CONTINUE"
                    assert advertised["input_kind"] == "NONE"
                    assert "max_input_length" not in advertised
            action_response = _record_exchange(
                transcript,
                method="POST",
                path=action_path,
                request_body=body,
                response=client.post(action_path, json=body),
                expected_status=200,
            )
            assert action_response["client_request_id"] == body["client_request_id"]
            assert action_response["resulting_state_version"] == ordinal
            resulting_versions.append(action_response["resulting_state_version"])
            refreshed = _record_exchange(
                transcript,
                method="GET",
                path=view_path,
                request_body=None,
                response=client.get(view_path),
                expected_status=200,
            )
            assert refreshed["metadata"]["state_version"] == ordinal
            refreshed_clocks = {
                item["clock_id"]: item["value"]
                for item in refreshed["public_clocks"]
            }
            assert (
                refreshed_clocks["disposal_protocol"],
                refreshed_clocks["predicted_death_deadline"],
            ) == PUBLIC_CLOCKS_AFTER_ACTION[ordinal - 1]

        assert resulting_versions == list(range(1, 20))
        final_view = transcript[-1]["response"]
        assert final_view["scenario_status"] == "ENDED"
        assert final_view["ending_status"] == "RESOLVED"
        assert final_view["ending_id"] == "death_certificate.ending.protocol_broken"
        assert final_view["action_affordances"] == {
            "mode": "ENDED",
            "actions": [],
            "choices": [],
        }
        public_clocks = {
            item["clock_id"]: item["value"] for item in final_view["public_clocks"]
        }
        assert public_clocks == {
            "disposal_protocol": 4,
            "predicted_death_deadline": 12,
        }
        memory = final_view["player_memory"]
        assert len(memory["scenarios"]) == 1
        assert memory["scenarios"][0]["status"] == "COMPLETED"
        assert len(memory["npcs"]) == 2
        assert len(memory["significant_experiences"]) == 2
        assert len(memory["known_public_facts"]) == 11
        assert len(final_view["recent_narrative_texts"]) == 5
    return tuple(transcript)


def _run_replay(
    *,
    hash_seed: str,
    identity_family: str,
    fault_mode: str | None = None,
) -> ReplayResult:
    child = DemoBackendChild(
        hash_seed=hash_seed,
        identity_family=identity_family,
        fault_mode=fault_mode,
    )
    try:
        child.start()
        transcript = _drive_public_path(child, identity_family=identity_family)
        trace, stdout, stderr = child.stop_and_collect()
    finally:
        child.cleanup()
    _assert_private_surfaces_absent(transcript, stdout, stderr)
    assert stdout == b""
    assert stderr == b""
    _assert_frozen_replay_output(
        transcript,
        identity_family=identity_family,
        exact_identity=identity_family == "same",
    )
    return ReplayResult(
        transcript=transcript,
        trace=trace,
        stdout=stdout,
        stderr=stderr,
        hash_seed=hash_seed,
    )


def _assert_private_surfaces_absent(
    transcript: tuple[dict[str, Any], ...], stdout: bytes, stderr: bytes
) -> None:
    public_bytes = _canonical_json(transcript).lower()
    diagnostic_bytes = (stdout + stderr).lower()
    for marker in (
        b"deviation-demo-generator-trace",
        b"demo-job-",
        b"demo-lease-",
        b"demo-worker-",
        b"security_alert",
        b"underground_patient_stability",
        b"deterministic-demo-v1",
        b"provider_progress",
        b"lease_owner",
        b"state_fingerprint",
        b"validated_proposal_digest",
    ):
        assert marker not in public_bytes
        assert marker not in diagnostic_bytes


def _normalize_caller_identities(
    transcript: tuple[dict[str, Any], ...]
) -> tuple[dict[str, Any], ...]:
    normalized = deepcopy(list(transcript))
    raw_to_token: dict[str, str] = {}
    category_counts: Counter[str] = Counter()
    action_request_values: dict[str, str] = {}

    def assign(raw: Any, category: str) -> str:
        if type(raw) is not str:
            raise ValueError("caller identity is not a JSON string")
        token = raw_to_token.get(raw)
        if token is None:
            category_counts[category] += 1
            token = f"<{category}:{category_counts[category]}>"
            raw_to_token[raw] = token
        return token

    for exchange in normalized:
        request = exchange["request"]
        method = exchange["method"]
        path = exchange["path"]
        if method == "POST" and path == "/v1/sessions":
            request["client_request_id"] = assign(
                request["client_request_id"], "CREATE_REQUEST"
            )
        elif method == "POST" and ACTION_PATH.fullmatch(path):
            raw_request = request["client_request_id"]
            request["turn_id"] = assign(request["turn_id"], "TURN")
            request["client_request_id"] = assign(
                raw_request, "ACTION_REQUEST"
            )
            action_request_values[path + "\0" + str(len(action_request_values))] = raw_request

    action_index = 0
    observed_action_values: dict[str, str] = {}
    for exchange in normalized:
        method = exchange["method"]
        path = exchange["path"]
        response = exchange["response"]
        if method == "POST" and ACTION_PATH.fullmatch(path):
            key = list(action_request_values)[action_index]
            raw = action_request_values[key]
            action_index += 1
            if response.get("client_request_id") != raw:
                raise ValueError("action response identity echo differs")
            response["client_request_id"] = raw_to_token[raw]
            observed_action_values[raw] = raw_to_token[raw]
        elif method == "GET" and REQUEST_STATUS_PATH.fullmatch(path):
            raw = response.get("client_request_id")
            if raw not in observed_action_values:
                raise ValueError("request-status identity was not established")
            response["client_request_id"] = observed_action_values[raw]
            if response.get("status") == "COMMITTED":
                nested = response.get("response")
                if not isinstance(nested, dict) or nested.get("client_request_id") != raw:
                    raise ValueError("nested committed identity echo differs")
                nested["client_request_id"] = observed_action_values[raw]
    return tuple(normalized)


def _assert_frozen_replay_output(
    transcript: tuple[dict[str, Any], ...],
    *,
    identity_family: str,
    exact_identity: bool,
) -> None:
    _assert_independent_replay_source(transcript, identity_family)
    assert len(transcript) == 60
    normalized_digest = hashlib.sha256(
        _canonical_json(_normalize_caller_identities(transcript))
    ).hexdigest()
    exact_digest = hashlib.sha256(_canonical_json(transcript)).hexdigest()
    assert normalized_digest == EXPECTED_NORMALIZED_REPLAY_SHA256
    if exact_identity:
        assert exact_digest == EXPECTED_EXACT_REPLAY_SHA256


def _assert_independent_replay_source(
    transcript: tuple[dict[str, Any], ...], identity_family: str
) -> None:
    """Readable frozen section-H source for the full transcript digest."""

    assert identity_family in {"same", "browser-a", "browser-b"}
    expected_envelope_fields = {"method", "path", "request", "status", "response"}
    expected_sequence: list[tuple[str, str, int]] = [
        ("GET", "/v1/scenarios", 200),
        ("POST", "/v1/sessions", 201),
        ("GET", "/v1/sessions/demo-session-00000001/view", 200),
    ]
    for _ in CANONICAL_ACTIONS:
        expected_sequence.extend(
            (
                ("GET", "/v1/sessions/demo-session-00000001/view", 200),
                ("POST", "/v1/sessions/demo-session-00000001/actions", 200),
                ("GET", "/v1/sessions/demo-session-00000001/view", 200),
            )
        )
    assert len(transcript) == len(expected_sequence) == 60
    for exchange, (method, path, status) in zip(
        transcript, expected_sequence, strict=True
    ):
        assert set(exchange) == expected_envelope_fields
        assert (exchange["method"], exchange["path"], exchange["status"]) == (
            method,
            path,
            status,
        )
        assert isinstance(exchange["response"], dict)

    create_request = transcript[1]["request"]
    assert create_request == {
        "client_request_id": f"opaque-{identity_family}-create",
        "character_definition_id": "character.death_certificate.investigator",
        "scenario_id": "death_certificate",
    }
    action_exchanges = [
        exchange
        for exchange in transcript
        if exchange["method"] == "POST" and ACTION_PATH.fullmatch(exchange["path"])
    ]
    assert len(action_exchanges) == len(CANONICAL_ACTIONS) == 19
    for ordinal, (exchange, step) in enumerate(
        zip(action_exchanges, CANONICAL_ACTIONS, strict=True), start=1
    ):
        request = exchange["request"]
        assert request["turn_id"] == _identity(identity_family, "turn", ordinal)
        assert request["client_request_id"] == _identity(
            identity_family, "action", ordinal
        )
        assert request["action_type"] == step.action_type
        expected_fields = {"turn_id", "client_request_id", "action_type"}
        if step.choice_id is not None:
            expected_fields.update(("decision_id", "choice_id"))
            assert request["choice_id"] == step.choice_id
        if step.description is not None:
            expected_fields.add("description")
            assert request["description"] == step.description
        assert set(request) == expected_fields
        assert exchange["response"]["client_request_id"] == request[
            "client_request_id"
        ]
        assert exchange["response"]["resulting_state_version"] == ordinal

    final_output = transcript[-1]["response"]
    assert set(final_output) == {
        "metadata",
        "narrative_frame",
        "player_state",
        "player_memory",
        "presentation",
        "action_affordances",
        "scenario_status",
        "ending_status",
        "public_clocks",
        "recent_narrative_texts",
        "ending_id",
    }
    assert final_output["metadata"]["state_version"] == 19
    assert final_output["scenario_status"] == "ENDED"
    assert final_output["ending_status"] == "RESOLVED"
    assert final_output["ending_id"] == "death_certificate.ending.protocol_broken"
    assert len(final_output["recent_narrative_texts"]) == 5


def _trace_wire(records: tuple[dict[str, Any], ...] | None = None) -> bytes:
    actual = records or _expected_generator_trace()
    completion = {
        "protocol": TRACE_PROTOCOL,
        "version": TRACE_VERSION,
        "record_type": "COMPLETE",
        "record_count": len(actual),
        "last_global_ordinal": len(actual),
    }
    return b"".join(_canonical_json(record) + b"\n" for record in (*actual, completion))


def _load_child_bootstrap_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "_deviation_demo_replay_child_contract", CHILD_BOOTSTRAP
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load replay child contract")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_expected_trace_is_derived_from_canonical_lifecycle() -> None:
    expected = _expected_generator_trace()
    counts = Counter(record["category"] for record in expected)

    assert len(CANONICAL_ACTIONS) == 19
    assert sum(ACTION_EVENT_COUNTS) + 1 == 27
    assert len(PROVIDER_ACTIONS) == 4
    assert counts == {
        "CLOCK": 52,
        "EVENT_ID": 27,
        "JOB_ID": 5,
        "LEASE_TOKEN": 4,
        "WORKER_ID": 4,
        "SESSION_ID": 1,
        "SEED": 1,
    }
    assert len(expected) == sum(counts.values()) == 94
    assert [record["global_ordinal"] for record in expected] == list(range(1, 95))
    assert [
        record["raw_value"] for record in expected if record["category"] == "CLOCK"
    ] == [
        (datetime(2000, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=index)).isoformat()
        for index in range(52)
    ]
    assert _parse_trace(_trace_wire()) == expected


@pytest.mark.parametrize(
    "mutate",
    (
        lambda lines: lines[:10] + lines[11:],
        lambda lines: lines[:10] + [lines[10]] + lines[10:],
        lambda lines: lines[:10] + [lines[11], lines[10]] + lines[12:],
        lambda lines: lines[:-1] + [lines[0], lines[-1]],
        lambda lines: lines[:-1],
        lambda lines: lines + [lines[-1]],
    ),
    ids=("missing", "duplicate", "reordered", "extra", "missing-sentinel", "duplicate-sentinel"),
)
def test_trace_parser_rejects_missing_duplicate_reordered_extra_and_sentinel_faults(
    mutate: Callable[[list[bytes]], list[bytes]],
) -> None:
    lines = _trace_wire().splitlines(keepends=True)
    with pytest.raises(ValueError):
        _parse_trace(b"".join(mutate(lines)))


@pytest.mark.parametrize(
    "wire",
    (
        b'{"protocol":}\n',
        b'{"protocol":"deviation-demo-generator-trace","protocol":"duplicate"}\n',
        _trace_wire().replace(b"\n", b"\r\n", 1),
        _trace_wire()[:-1],
        b"\xff\n",
        b"[]\n",
        b"\n",
        b"",
    ),
    ids=(
        "malformed-json",
        "duplicate-key",
        "crlf",
        "unterminated",
        "invalid-utf8",
        "non-object",
        "blank",
        "empty",
    ),
)
def test_trace_parser_rejects_malformed_wire_data(wire: bytes) -> None:
    with pytest.raises((ValueError, json.JSONDecodeError)):
        _parse_trace(wire)


@pytest.mark.parametrize("constant", (b"NaN", b"Infinity", b"-Infinity"))
def test_trace_parser_rejects_every_non_finite_json_value(
    constant: bytes,
) -> None:
    wire = _trace_wire().replace(
        b'"raw_value":"2000-01-01T00:00:00+00:00"',
        b'"raw_value":' + constant,
        1,
    )
    with pytest.raises(ValueError, match="non-finite"):
        _parse_trace(wire)


@pytest.mark.parametrize(
    "mutate",
    (
        lambda value: {key: item for key, item in value.items() if key != "record_count"},
        lambda value: {**value, "extra": 1},
        lambda value: {**value, "protocol": "wrong"},
        lambda value: {**value, "version": 2},
        lambda value: {**value, "version": True},
        lambda value: {**value, "record_type": "GENERATOR"},
        lambda value: {**value, "record_count": True},
        lambda value: {**value, "record_count": -1},
        lambda value: {**value, "record_count": "94"},
        lambda value: {**value, "last_global_ordinal": 93},
        lambda value: {**value, "last_global_ordinal": True},
        lambda value: {**value, "last_global_ordinal": "94"},
    ),
    ids=(
        "missing-field",
        "extra-field",
        "wrong-protocol",
        "wrong-version",
        "boolean-version",
        "wrong-type",
        "boolean-count",
        "negative-count",
        "string-count",
        "wrong-last-ordinal",
        "boolean-last-ordinal",
        "string-last-ordinal",
    ),
)
def test_trace_parser_rejects_malformed_completion_fields(
    mutate: Callable[[dict[str, Any]], dict[str, Any]],
) -> None:
    records = _expected_generator_trace()
    completion = mutate(
        {
            "protocol": TRACE_PROTOCOL,
            "version": TRACE_VERSION,
            "record_type": "COMPLETE",
            "record_count": len(records),
            "last_global_ordinal": len(records),
        }
    )
    wire = b"".join(
        _canonical_json(record) + b"\n" for record in records
    ) + _canonical_json(completion) + b"\n"
    with pytest.raises(ValueError):
        _parse_trace(wire)


def test_trace_parser_rejects_records_or_bytes_after_completion() -> None:
    trailing_record = _canonical_json(_expected_generator_trace()[0]) + b"\n"
    with pytest.raises(ValueError, match="completion"):
        _parse_trace(_trace_wire() + trailing_record)
    with pytest.raises((ValueError, json.JSONDecodeError)):
        _parse_trace(_trace_wire() + b"trailing-bytes\n")


@pytest.mark.parametrize(
    "wire",
    (
        _trace_wire()[:-10],
        _trace_wire().rsplit(b"\n", 2)[0] + b'\n{"protocol":\n',
        _trace_wire()[:-1] + b" ",
    ),
    ids=("abnormal-eof", "truncated-json", "non-lf-terminated"),
)
def test_trace_parser_rejects_truncation_and_abnormal_eof(wire: bytes) -> None:
    with pytest.raises((ValueError, json.JSONDecodeError)):
        _parse_trace(wire)


def test_trace_parser_rejects_ordinal_and_timestamp_discontinuity() -> None:
    for field, value in (
        ("global_ordinal", 5),
        ("category_ordinal", 2),
        ("raw_value", "2000-01-01T00:00:09+00:00"),
    ):
        records = list(deepcopy(_expected_generator_trace()))
        records[0][field] = value
        with pytest.raises(ValueError):
            _parse_trace(_trace_wire(tuple(records)))


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("category", "EVENT_ID"),
        ("category", "UNKNOWN"),
        ("protocol", "wrong"),
        ("record_type", "COMPLETE"),
        ("version", 2),
        ("version", True),
        ("global_ordinal", True),
        ("category_ordinal", True),
        ("raw_value", 1),
    ),
    ids=(
        "category-discontinuity",
        "unknown-category",
        "wrong-protocol",
        "wrong-record-type",
        "wrong-version",
        "boolean-version",
        "boolean-global-ordinal",
        "boolean-category-ordinal",
        "wrong-clock-type",
    ),
)
def test_trace_parser_rejects_generator_envelope_and_type_discontinuity(
    field: str, value: Any
) -> None:
    records = list(deepcopy(_expected_generator_trace()))
    records[0][field] = value
    with pytest.raises(ValueError):
        _parse_trace(_trace_wire(tuple(records)))


@pytest.mark.parametrize("value", (9, 301, True, "60"))
def test_timeout_range_is_fail_closed(value: Any) -> None:
    with pytest.raises(ValueError):
        validate_timeout(value)
    assert validate_timeout(10) == 10
    assert validate_timeout(60) == 60
    assert validate_timeout(300) == 300


def test_runner_constructor_and_unstarted_operations_are_fail_closed() -> None:
    for hash_seed in ("0", "3", "", 1, None):
        with pytest.raises(ValueError, match="hash seed"):
            DemoBackendChild(hash_seed=hash_seed)  # type: ignore[arg-type]

    runner = DemoBackendChild(hash_seed="1")
    with pytest.raises(RuntimeError, match="not owned"):
        runner._owned_process()
    with pytest.raises(RuntimeError, match="drains were not started"):
        runner._join_drains()

    _require_successful_exit(0, b"")
    for invalid_exit in (None, True, 0.0, "0"):
        with pytest.raises(RuntimeError, match="nonzero"):
            _require_successful_exit(invalid_exit, b"")  # type: ignore[arg-type]


def test_pipe_drain_failures_are_reported_and_blocked_reader_can_finish() -> None:
    class FailingStream:
        def __init__(self) -> None:
            self.closed = False

        def read(self, size: int) -> bytes:
            del size
            raise OSError("forced read failure")

        def close(self) -> None:
            self.closed = True

    failing_stream = FailingStream()
    failing = _DrainThread(failing_stream, name="failing-drain")  # type: ignore[arg-type]
    failing.start()
    with pytest.raises(RuntimeError, match="pipe reader failed"):
        failing.join(1)
    assert failing_stream.closed

    release = threading.Event()

    class BlockingStream(io.BytesIO):
        def read(self, size: int = -1) -> bytes:
            release.wait()
            return super().read(size)

    blocked = _DrainThread(BlockingStream(b"done"), name="blocked-drain")
    blocked.start()
    with pytest.raises(RuntimeError, match="did not drain EOF"):
        blocked.join(0.01)
    release.set()
    assert blocked.join(1) == b"done"


def test_elapsed_child_deadline_reaches_zero() -> None:
    runner = DemoBackendChild(hash_seed="1", timeout_seconds=10)
    runner._deadline = time.monotonic() - 1
    assert runner._remaining() == 0


def test_nonzero_child_exit_and_process_ownership_are_fail_closed() -> None:
    with pytest.raises(RuntimeError, match="nonzero"):
        _require_successful_exit(7, b"owned diagnostic")

    runner = DemoBackendChild(hash_seed="1")
    foreign = object()
    with pytest.raises(RuntimeError, match="unowned"):
        runner._terminate_owned(foreign)  # type: ignore[arg-type]

    class TimedOutOwnedProcess:
        def __init__(self) -> None:
            self.calls: list[str] = []
            self.alive = True

        def poll(self) -> int | None:
            return None if self.alive else 0

        def terminate(self) -> None:
            self.calls.append("terminate")

        def wait(self, timeout: float) -> int:
            self.calls.append(f"wait-{timeout}")
            if self.alive and "kill" not in self.calls:
                raise subprocess.TimeoutExpired("owned-child", timeout)
            self.alive = False
            return 0

        def kill(self) -> None:
            self.calls.append("kill")

    owned = TimedOutOwnedProcess()
    runner._process = owned  # type: ignore[assignment]
    runner._terminate_owned(owned)  # type: ignore[arg-type]
    assert owned.calls == ["terminate", "wait-5", "kill", "wait-5"]
    assert owned.poll() == 0


def test_actual_stubborn_child_reaches_kill_is_reaped_and_leaves_foreign_child_alive() -> None:
    options: dict[str, Any] = {}
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NO_WINDOW
    command = [
        str(PROJECT_PYTHON),
        "-c",
        "import threading; threading.Event().wait()",
    ]
    owned_process = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        **options,
    )
    foreign_process = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        **options,
    )

    class StubbornOwnedProcess:
        def __init__(self, process: subprocess.Popen[bytes]) -> None:
            self.process = process
            self.terminate_called = False
            self.kill_called = False

        def poll(self) -> int | None:
            return self.process.poll()

        def terminate(self) -> None:
            # Reviewer-controlled refusal: keep the real child alive so the
            # runner's real wait times out and its kill branch must execute.
            self.terminate_called = True

        def wait(self, timeout: float) -> int:
            return self.process.wait(timeout=timeout)

        def kill(self) -> None:
            self.kill_called = True
            self.process.kill()

    owned = StubbornOwnedProcess(owned_process)
    runner = DemoBackendChild(hash_seed="1")
    runner._terminate_grace_seconds = 0.2
    runner._process = owned  # type: ignore[assignment]
    try:
        runner._terminate_owned(owned)  # type: ignore[arg-type]
        assert owned.terminate_called
        assert owned.kill_called
        assert owned_process.poll() is not None
        assert owned_process.returncode is not None
        assert foreign_process.poll() is None
        with pytest.raises(RuntimeError, match="unowned"):
            runner._terminate_owned(foreign_process)
        assert foreign_process.poll() is None
    finally:
        if owned_process.poll() is None:
            owned_process.kill()
            owned_process.wait(timeout=5)
        if foreign_process.poll() is None:
            foreign_process.terminate()
            try:
                foreign_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                foreign_process.kill()
                foreign_process.wait(timeout=5)
    assert owned_process.poll() is not None
    assert foreign_process.poll() is not None


@pytest.mark.parametrize(
    ("fault_mode", "expected_text"),
    (
        ("early-exit-zero", "exited before readiness"),
        ("none-progress-trace-write", "exited before readiness"),
        ("zero-progress-trace-write", "exited before readiness"),
    ),
)
def test_actual_child_early_and_zero_progress_exits_are_rejected_and_reaped(
    fault_mode: str, expected_text: str
) -> None:
    child = DemoBackendChild(hash_seed="1", fault_mode=fault_mode)
    try:
        with pytest.raises(RuntimeError, match=expected_text):
            child.start()
        process = child._owned_process()
        assert process.poll() is not None
    finally:
        child.cleanup()


def test_actual_faulting_child_drains_large_stdout_and_stderr_before_nonzero_exit() -> None:
    child = DemoBackendChild(
        hash_seed="1", fault_mode="diagnostic-nonzero"
    )
    try:
        with pytest.raises(RuntimeError, match="exited before readiness"):
            child.start()
        process = child._owned_process()
        assert process.poll() == 7
        assert child._stdout_drain is not None
        assert child._stderr_drain is not None
        stdout = child._stdout_drain.join(1)
        stderr = child._stderr_drain.join(1)
        assert len(stdout) > 64_000
        assert len(stderr) > 64_000
        assert b"faulting-child-stdout" in stdout
        assert b"faulting-child-stderr" in stderr
    finally:
        child.cleanup()


def test_actual_child_readiness_timeout_terminates_and_reaps_only_the_owned_process() -> None:
    child = DemoBackendChild(hash_seed="1", fault_mode="hang-before-ready")
    child._deadline = time.monotonic() + 0.25
    try:
        with pytest.raises(TimeoutError, match="readiness"):
            child.start()
        process = child._owned_process()
        assert process.poll() is not None
    finally:
        child.cleanup()


def test_actual_child_stop_timeout_terminates_and_reaps_the_owned_process() -> None:
    child = DemoBackendChild(hash_seed="1", fault_mode="hang-after-stop")
    try:
        child.start()
        child._deadline = time.monotonic() + 0.25
        with pytest.raises(TimeoutError, match="owned timeout"):
            child.stop_and_collect()
        process = child._owned_process()
        assert process.poll() is not None
    finally:
        child.cleanup()


def test_actual_foreign_process_is_not_terminated_by_the_runner() -> None:
    options: dict[str, Any] = {}
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NO_WINDOW
    foreign = subprocess.Popen(
        [
            str(PROJECT_PYTHON),
            "-c",
            "import threading; threading.Event().wait()",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        **options,
    )
    runner = DemoBackendChild(hash_seed="1")
    try:
        with pytest.raises(RuntimeError, match="unowned"):
            runner._terminate_owned(foreign)
        assert foreign.poll() is None
    finally:
        if foreign.poll() is None:
            foreign.terminate()
            try:
                foreign.wait(timeout=5)
            except subprocess.TimeoutExpired:
                foreign.kill()
                foreign.wait(timeout=5)
    assert foreign.poll() is not None


@pytest.mark.parametrize(
    "control_bytes",
    (b"", b"STOP\nTRAILING", b"STOP\r\n"),
    ids=("eof-without-stop", "trailing-after-stop", "crlf-stop"),
)
def test_actual_child_rejects_stop_and_eof_protocol_violations(
    control_bytes: bytes,
) -> None:
    child = DemoBackendChild(hash_seed="1")
    try:
        child.start()
        assert child._control is not None
        if control_bytes:
            child._control.write(control_bytes)
            child._control.flush()
        child._control.close()
        child._control = None
        process = child._owned_process()
        exit_code = process.wait(timeout=5)
        trace, stdout, stderr = child._join_drains()
        assert exit_code != 0
        assert b"DEMO_REPLAY_CHILD_FAILED" in stderr
        assert b'"record_type":"COMPLETE"' not in trace
        assert stdout == b""
    finally:
        child.cleanup()


def test_actual_child_requires_eof_after_stop_and_is_reaped_on_timeout() -> None:
    child = DemoBackendChild(hash_seed="1")
    try:
        child.start()
        assert child._control is not None
        child._control.write(b"STOP\n")
        child._control.flush()
        process = child._owned_process()
        with pytest.raises(subprocess.TimeoutExpired):
            process.wait(timeout=0.25)
        child._terminate_owned(process)
        assert process.poll() is not None
    finally:
        child.cleanup()


@pytest.mark.parametrize(
    "fault_mode", ("partial-trace-write", "partial-trace-writes")
)
def test_actual_child_replays_with_partial_trace_pipe_writes(
    fault_mode: str,
) -> None:
    result = _run_replay(
        hash_seed="1",
        identity_family="same",
        fault_mode=fault_mode,
    )
    assert result.trace == _expected_generator_trace()
    assert result.stdout == b""
    assert result.stderr == b""


def test_actual_child_rejects_double_start_and_double_stop() -> None:
    child = DemoBackendChild(hash_seed="1")
    try:
        child.start()
        with pytest.raises(RuntimeError, match="already started"):
            child.start()
        transcript = _drive_public_path(child, identity_family="same")
        trace, stdout, stderr = child.stop_and_collect()
        assert trace == _expected_generator_trace()
        assert stdout == stderr == b""
        _assert_frozen_replay_output(
            transcript, identity_family="same", exact_identity=True
        )
        with pytest.raises(RuntimeError, match="control pipe is unavailable"):
            child.stop_and_collect()
        child._terminate_owned(child._owned_process())
    finally:
        child.cleanup()


def test_caller_identity_normalizer_rejects_unmatched_echo() -> None:
    transcript = (
        {
            "method": "POST",
            "path": "/v1/sessions/demo-session-00000001/actions",
            "request": {
                "turn_id": "turn-a",
                "client_request_id": "request-a",
                "action_type": "CONTINUE",
            },
            "status": 200,
            "response": {"client_request_id": "wrong"},
        },
    )
    with pytest.raises(ValueError, match="echo"):
        _normalize_caller_identities(transcript)

    unlisted = deepcopy(transcript[0])
    unlisted["response"]["client_request_id"] = "request-a"
    unlisted["response"]["unlisted_identity"] = "request-a"
    normalized = _normalize_caller_identities((unlisted,))
    assert normalized[0]["response"]["client_request_id"] == "<ACTION_REQUEST:1>"
    assert normalized[0]["response"]["unlisted_identity"] == "request-a"

    shared = deepcopy(unlisted)
    shared["request"]["turn_id"] = "shared-identity"
    shared["request"]["client_request_id"] = "shared-identity"
    shared["response"]["client_request_id"] = "shared-identity"
    shared["response"].pop("unlisted_identity")
    normalized_shared = _normalize_caller_identities((shared,))
    assert normalized_shared[0]["request"]["turn_id"] == "<TURN:1>"
    assert normalized_shared[0]["request"]["client_request_id"] == "<TURN:1>"
    assert normalized_shared[0]["response"]["client_request_id"] == "<TURN:1>"


def test_private_caller_equivalence_changes_only_direct_whitelisted_bindings() -> None:
    child_module = _load_child_bootstrap_module()
    raw = {
        "sessions": [
            {
                "store_session_id": "server-session",
                "value": {"creation_client_request_id": "create-raw"},
            }
        ],
        "creation_keys": [
            {
                "player_id": "player",
                "creation_client_request_id": "create-raw",
                "session_id": "server-session",
            }
        ],
        "turn_requests": [
            {
                "store_session_id": "server-session",
                "store_client_request_id": "request-raw",
                "value": {
                    "turn_id": "turn-raw",
                    "action_signature": "a" * 64,
                    "response": {
                        "client_request_id": "request-raw",
                        "action_signature": "a" * 64,
                    },
                },
            }
        ],
        "narrative_jobs": [
            {
                "store_job_id": "server-job",
                "value": {
                    "turn_id": "turn-raw",
                    "client_request_id": "request-raw",
                    "action_signature": "a" * 64,
                    "request_fingerprint": "b" * 64,
                    "narrative_request": {
                        "outcome_candidates": [{"outcome_token": "outcome.raw"}]
                    },
                    "validated_proposal_digest": "c" * 64,
                },
            }
        ],
        "events": [
            {
                "store_ordinal": 1,
                "value": {
                    "turn_id": "turn-raw",
                    "event_id": "server-event",
                    "payload": {"proposal_digest": "c" * 64},
                },
            }
        ],
        "snapshots": [{"state": {"unchanged": True}}],
        "provider_progress": [{"session_id": "server-session", "completed_calls": 1}],
    }

    normalized = child_module._caller_identity_equivalence_representation(raw)

    assert normalized["sessions"][0]["value"]["creation_client_request_id"] == (
        "<CREATE_REQUEST:1>"
    )
    assert normalized["turn_requests"][0]["store_client_request_id"] == (
        "<ACTION_REQUEST:1>"
    )
    assert normalized["turn_requests"][0]["value"]["turn_id"] == "<TURN:1>"
    assert normalized["turn_requests"][0]["value"]["response"][
        "client_request_id"
    ] == "<ACTION_REQUEST:1>"
    assert normalized["narrative_jobs"][0]["value"]["turn_id"] == "<TURN:1>"
    assert normalized["events"][0]["value"]["turn_id"] == "<TURN:1>"
    for path in (
        ("action_signature", "a" * 64),
        ("request_fingerprint", "b" * 64),
        ("validated_proposal_digest", "c" * 64),
    ):
        assert normalized["narrative_jobs"][0]["value"][path[0]] == path[1]
    assert normalized["narrative_jobs"][0]["value"]["narrative_request"] == raw[
        "narrative_jobs"
    ][0]["value"]["narrative_request"]
    assert normalized["events"][0]["value"]["payload"] == raw["events"][0][
        "value"
    ]["payload"]
    assert normalized["snapshots"] == raw["snapshots"]


def test_raw_private_evidence_is_schema_complete_and_has_no_normalizer_dependency() -> None:
    child_module = _load_child_bootstrap_module()
    child_module._assert_authoritative_field_manifests()
    raw_names = set(
        child_module._complete_raw_private_representation.__code__.co_names
    )
    assert "_caller_identity_equivalence_representation" not in raw_names
    assert set(child_module.EXPECTED_PRIVATE_COMPONENTS) == {
        "sessions",
        "snapshots",
        "creation_keys",
        "turn_requests",
        "narrative_jobs",
        "events",
        "provider_progress",
    }
    assert all(
        set(component_digests) == child_module.EXPECTED_PRIVATE_COMPONENTS
        for component_digests in (
            *child_module.EXPECTED_RAW_PRIVATE_COMPONENT_DIGESTS.values(),
            *child_module.EXPECTED_CALLER_EQUIVALENCE_COMPONENT_DIGESTS.values(),
        )
    )
    raw_a = child_module.EXPECTED_RAW_PRIVATE_COMPONENT_DIGESTS["browser-a"]
    raw_b = child_module.EXPECTED_RAW_PRIVATE_COMPONENT_DIGESTS["browser-b"]
    equivalence_a = child_module.EXPECTED_CALLER_EQUIVALENCE_COMPONENT_DIGESTS[
        "browser-a"
    ]
    equivalence_b = child_module.EXPECTED_CALLER_EQUIVALENCE_COMPONENT_DIGESTS[
        "browser-b"
    ]
    assert raw_a["sessions"] != raw_b["sessions"]
    assert raw_a["creation_keys"] != raw_b["creation_keys"]
    assert equivalence_a["sessions"] == equivalence_b["sessions"]
    assert equivalence_a["creation_keys"] == equivalence_b["creation_keys"]
    assert raw_a["snapshots"] == raw_b["snapshots"]


def test_frozen_replay_detects_every_exchange_and_final_output_field_family() -> None:
    baseline = _run_replay(hash_seed="1", identity_family="same").transcript

    def changed(value: Any) -> Any:
        if value is None:
            return {"tampered": True}
        if type(value) is bool:
            return not value
        if type(value) is int:
            return value + 1
        if type(value) is str:
            return value + "-tampered"
        if isinstance(value, list):
            return [*value, "tampered"]
        if isinstance(value, dict):
            return {**value, "tampered": True}
        raise AssertionError(f"unsupported transcript mutation type: {type(value)}")

    for field in ("method", "path", "request", "status", "response"):
        mutated = deepcopy(baseline)
        mutated[0][field] = changed(mutated[0][field])
        with pytest.raises(AssertionError):
            _assert_frozen_replay_output(
                mutated, identity_family="same", exact_identity=True
            )

    for field in tuple(baseline[-1]["response"]):
        mutated = deepcopy(baseline)
        mutated[-1]["response"][field] = changed(
            mutated[-1]["response"][field]
        )
        with pytest.raises(AssertionError):
            _assert_frozen_replay_output(
                mutated, identity_family="same", exact_identity=True
            )


def test_child_network_guard_blocks_non_loopback_without_transport_attempt() -> None:
    child_module = _load_child_bootstrap_module()
    restore = child_module._deny_non_loopback_connections()
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with pytest.raises(OSError, match="non-loopback"):
            connection.connect(("192.0.2.1", 9))
        with pytest.raises(OSError, match="non-loopback"):
            connection.sendto(b"blocked", ("192.0.2.1", 9))
        with pytest.raises(OSError, match="non-loopback"):
            socket.getaddrinfo("example.invalid", 443)
    finally:
        connection.close()
        restore()


@pytest.mark.parametrize(
    "mutation",
    (
        "hidden_fact",
        "evidence_entry",
        "event_payload",
        "job_field",
        "snapshot_field",
        "session_field",
        "session_creation",
        "session_update",
        "public_state",
        "snapshot_metadata",
        "creation_index",
        "turn_store_session",
        "turn_store_request",
        "turn_id",
        "turn_action_signature",
        "turn_response",
        "event_id",
        "event_sequence",
        "event_type",
        "event_subtype",
        "event_timestamp",
        "job_id",
        "job_status",
        "job_payload",
        "job_created_at",
        "job_updated_at",
        "job_lease_owner",
        "job_lease_token",
        "job_fencing",
        "job_lifecycle",
        "authority_progress",
    ),
)
def test_complete_private_expectation_rejects_every_mutated_field_family(
    mutation: str,
) -> None:
    child = DemoBackendChild(hash_seed="1", private_mutation=mutation)
    try:
        child.start()
        _drive_public_path(child, identity_family="same")
        with pytest.raises(RuntimeError, match="nonzero") as raised:
            child.stop_and_collect()
        assert b"DEMO_REPLAY_CHILD_FAILED" in str(raised.value).encode("utf-8")
    finally:
        child.cleanup()


def test_complete_backend_identity_family_and_hash_seed_factorial_matrix() -> None:
    exact_seed_1 = _run_replay(hash_seed="1", identity_family="same")
    exact_seed_2 = _run_replay(hash_seed="2", identity_family="same")
    browser_a_seed_1 = _run_replay(hash_seed="1", identity_family="browser-a")
    browser_a_seed_2 = _run_replay(hash_seed="2", identity_family="browser-a")
    browser_b_seed_1 = _run_replay(hash_seed="1", identity_family="browser-b")
    browser_b_seed_2 = _run_replay(hash_seed="2", identity_family="browser-b")

    exact_runs = (exact_seed_1, exact_seed_2)
    browser_runs = (
        browser_a_seed_1,
        browser_a_seed_2,
        browser_b_seed_1,
        browser_b_seed_2,
    )
    all_runs = (*exact_runs, *browser_runs)
    assert tuple(run.hash_seed for run in exact_runs) == ("1", "2")
    assert tuple(run.hash_seed for run in browser_runs) == ("1", "2", "1", "2")
    assert exact_seed_1.transcript == exact_seed_2.transcript
    assert browser_a_seed_1.transcript == browser_a_seed_2.transcript
    assert browser_b_seed_1.transcript == browser_b_seed_2.transcript
    assert all(run.trace == _expected_generator_trace() for run in all_runs)
    assert all(run.trace == exact_seed_1.trace for run in all_runs)
    assert all(run.stdout == b"" and run.stderr == b"" for run in all_runs)

    normalized_runs = tuple(
        _normalize_caller_identities(run.transcript) for run in all_runs
    )
    normalized_exact = normalized_runs[0]
    for normalized in normalized_runs[1:]:
        assert normalized == normalized_exact, _difference_paths(
            normalized_exact, normalized
        )
