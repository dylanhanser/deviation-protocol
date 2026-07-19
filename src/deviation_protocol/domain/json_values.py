from __future__ import annotations

from collections.abc import Mapping
import json
import math
from typing import Any


class FrozenJsonDict(dict[str, Any]):
    """A JSON-serializable dict whose contents cannot be changed after creation."""

    @staticmethod
    def _immutable(*_: object, **__: object) -> None:
        raise TypeError("frozen JSON objects cannot be modified")

    __delitem__ = _immutable
    __ior__ = _immutable
    __setitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable


def freeze_json_value(value: Any, *, path: str = "value") -> Any:
    """Validate and detach a value into an immutable MySQL-JSON-safe shape."""

    return _freeze_json_value(value, path=path)


def freeze_bounded_json_value(
    value: Any,
    *,
    path: str = "value",
    allow_floats: bool = False,
    max_depth: int = 8,
    max_collection_items: int = 64,
    max_string_length: int = 4_000,
) -> Any:
    """Freeze untrusted scenario JSON with explicit complexity limits."""

    if max_depth < 0 or max_collection_items < 1 or max_string_length < 1:
        raise ValueError("JSON complexity limits must be positive")
    return _freeze_json_value(
        value,
        path=path,
        allow_floats=allow_floats,
        max_depth=max_depth,
        max_collection_items=max_collection_items,
        max_string_length=max_string_length,
    )


def json_values_equal(left: Any, right: Any) -> bool:
    """Compare JSON values without Python's bool/int equality ambiguity."""

    return _canonical_json(left) == _canonical_json(right)


def canonical_json_key(value: Any) -> str:
    """Return a stable key for duplicate checks and deterministic ordering."""

    return json.dumps(
        _canonical_json(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _freeze_json_value(
    value: Any,
    *,
    path: str,
    allow_floats: bool = True,
    max_depth: int | None = None,
    max_collection_items: int | None = None,
    max_string_length: int | None = None,
    depth: int = 0,
) -> Any:
    if max_depth is not None and depth > max_depth:
        raise ValueError(f"{path} exceeds the maximum JSON nesting depth")

    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, str):
        if max_string_length is not None and len(value) > max_string_length:
            raise ValueError(f"{path} contains an oversized string")
        return value
    if isinstance(value, float):
        if not allow_floats:
            raise TypeError(f"{path} contains a float; scenario state requires integers")
        if not math.isfinite(value):
            raise ValueError(f"{path} contains a non-finite float")
        return value
    if isinstance(value, Mapping):
        if max_collection_items is not None and len(value) > max_collection_items:
            raise ValueError(f"{path} contains too many object members")
        frozen: dict[str, Any] = {}
        for key, nested in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path} JSON object keys must be strings")
            if max_string_length is not None and len(key) > max_string_length:
                raise ValueError(f"{path} contains an oversized object key")
            frozen[key] = _freeze_json_value(
                nested,
                path=f"{path}.{key}",
                allow_floats=allow_floats,
                max_depth=max_depth,
                max_collection_items=max_collection_items,
                max_string_length=max_string_length,
                depth=depth + 1,
            )
        return FrozenJsonDict(frozen)
    if isinstance(value, (list, tuple)):
        if max_collection_items is not None and len(value) > max_collection_items:
            raise ValueError(f"{path} contains too many array items")
        return tuple(
            _freeze_json_value(
                item,
                path=f"{path}[{index}]",
                allow_floats=allow_floats,
                max_depth=max_depth,
                max_collection_items=max_collection_items,
                max_string_length=max_string_length,
                depth=depth + 1,
            )
            for index, item in enumerate(value)
        )
    raise TypeError(f"{path} contains a non-JSON value of type {type(value).__name__}")


def _canonical_json(value: Any) -> Any:
    if value is None:
        return ["null", None]
    if isinstance(value, bool):
        return ["bool", value]
    if isinstance(value, int):
        return ["int", value]
    if isinstance(value, float):
        return ["float", value]
    if isinstance(value, str):
        return ["str", value]
    if isinstance(value, Mapping):
        return [
            "object",
            [[key, _canonical_json(value[key])] for key in sorted(value)],
        ]
    if isinstance(value, (list, tuple)):
        return ["array", [_canonical_json(item) for item in value]]
    raise TypeError(f"value contains a non-JSON value of type {type(value).__name__}")


def freeze_json_object(value: Mapping[str, Any], *, path: str) -> FrozenJsonDict:
    frozen = freeze_json_value(value, path=path)
    if not isinstance(frozen, FrozenJsonDict):  # pragma: no cover - type guard
        raise TypeError(f"{path} must be a JSON object")
    return frozen
