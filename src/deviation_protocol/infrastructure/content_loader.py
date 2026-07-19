from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from deviation_protocol.domain.content import ContentCatalog


class ContentPackLoadError(ValueError):
    """A JSON content pack could not be decoded or validated."""


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
            with self._path.open("r", encoding="utf-8") as stream:
                payload = json.load(stream)
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
        except (OSError, UnicodeError, json.JSONDecodeError, ValidationError, ValueError) as exc:
            raise ContentPackLoadError(
                f"invalid content pack {self._path.name!r}: {exc}"
            ) from exc
