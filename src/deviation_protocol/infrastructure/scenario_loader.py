from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from deviation_protocol.domain.scenario import ScenarioCatalog


class ScenarioPackLoadError(ValueError):
    """A versioned scenario JSON package failed strict decoding or validation."""


MAX_SCENARIO_PACK_BYTES = 2_000_000


class JsonScenarioCatalogLoader:
    def __init__(
        self,
        path: str | Path,
        *,
        expected_content_version: str | None = None,
    ) -> None:
        self._path = Path(path)
        self._expected_content_version = expected_content_version

    def load(self) -> ScenarioCatalog:
        try:
            if self._path.stat().st_size > MAX_SCENARIO_PACK_BYTES:
                raise ValueError("scenario pack exceeds the configured file-size limit")
            with self._path.open("r", encoding="utf-8") as stream:
                payload = json.load(
                    stream,
                    object_pairs_hook=_reject_duplicate_object_keys,
                    parse_constant=_reject_non_standard_number,
                )
            catalog = ScenarioCatalog.model_validate(payload)
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
            raise ScenarioPackLoadError(
                f"invalid scenario pack {self._path.name!r}: {exc}"
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
