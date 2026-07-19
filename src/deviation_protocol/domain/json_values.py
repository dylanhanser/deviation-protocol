from __future__ import annotations

from collections.abc import Mapping
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

    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} contains a non-finite float")
        return value
    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for key, nested in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path} JSON object keys must be strings")
            frozen[key] = freeze_json_value(nested, path=f"{path}.{key}")
        return FrozenJsonDict(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(
            freeze_json_value(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        )
    raise TypeError(f"{path} contains a non-JSON value of type {type(value).__name__}")


def freeze_json_object(value: Mapping[str, Any], *, path: str) -> FrozenJsonDict:
    frozen = freeze_json_value(value, path=path)
    if not isinstance(frozen, FrozenJsonDict):  # pragma: no cover - type guard
        raise TypeError(f"{path} must be a JSON object")
    return frozen
