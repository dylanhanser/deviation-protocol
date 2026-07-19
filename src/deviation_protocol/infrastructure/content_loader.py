from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from deviation_protocol.domain.content import ContentCatalog


class ContentPackLoadError(ValueError):
    """A JSON content pack could not be decoded or validated."""


MAX_CONTENT_PACK_BYTES = 2_000_000
MAX_CONTENT_PACK_DEPTH = 32


class JsonContentCatalogLoader:
    def __init__(
        self,
        path: str | Path,
        *,
        expected_content_version: str | None = None,
    ) -> None:
        self._path = Path(path)
        self._expected_content_version = expected_content_version

    def load(self) -> ContentCatalog:
        try:
            if self._path.stat().st_size > MAX_CONTENT_PACK_BYTES:
                raise ValueError("content pack exceeds the configured file-size limit")
            with self._path.open("r", encoding="utf-8") as stream:
                payload = json.load(
                    stream,
                    object_pairs_hook=_reject_duplicate_object_keys,
                    parse_constant=_reject_non_standard_number,
                )
            _reject_excessive_json_depth(payload)
            catalog = ContentCatalog.model_validate(payload)
            if (
                self._expected_content_version is not None
                and catalog.content_version != self._expected_content_version
            ):
                raise ValueError(
                    f"unsupported content_version {catalog.content_version!r}; "
                    f"expected {self._expected_content_version!r}"
                )
            return catalog
        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            ValidationError,
            TypeError,
            ValueError,
            RecursionError,
        ) as exc:
            raise ContentPackLoadError(
                f"invalid content pack {self._path.name!r}: {exc}"
            ) from exc


def _reject_duplicate_object_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key {key!r}")
        result[key] = value
    return result


def _reject_non_standard_number(value: str) -> object:
    raise ValueError(f"non-standard JSON number {value!r} is not allowed")


def _reject_excessive_json_depth(value: object) -> None:
    pending: list[tuple[object, int]] = [(value, 0)]
    while pending:
        item, depth = pending.pop()
        if depth > MAX_CONTENT_PACK_DEPTH:
            raise ValueError("content pack exceeds the configured nesting-depth limit")
        if isinstance(item, dict):
            pending.extend((nested, depth + 1) for nested in item.values())
        elif isinstance(item, list):
            pending.extend((nested, depth + 1) for nested in item)
