from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from blacksmith.trust.fetch import fetch_https_bytes

from blacksmith.gallery.paths import (
    DEFAULT_INDEX_URL,
    bundled_index_path,
    cached_index_path,
)
from blacksmith.gallery.schema import (
    GalleryError,
    GalleryEntry,
    GalleryIndex,
    parse_index as _parse_index,
)

parse_index = _parse_index


def _read_index_file(path: Path) -> GalleryIndex:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GalleryError(f"failed to read index: {path}") from exc
    if not isinstance(raw, dict):
        raise GalleryError("index must be a JSON object", code="invalid_schema")
    return parse_index(raw)


def _write_cache_atomic(path: Path, body: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(body)
        os.replace(tmp_path, path)
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def load_index(*, refresh: bool = False) -> GalleryIndex:
    cache = cached_index_path()

    if refresh:
        body, _digest, _final_url = fetch_https_bytes(DEFAULT_INDEX_URL)
        try:
            raw: Any = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise GalleryError("remote index is not valid JSON") from exc
        if not isinstance(raw, dict):
            raise GalleryError("index must be a JSON object", code="invalid_schema")
        index = parse_index(raw)
        _write_cache_atomic(cache, body)
        return index

    if cache.is_file():
        return _read_index_file(cache)

    return _read_index_file(bundled_index_path())


def get_entry(index: GalleryIndex, entry_id: str) -> GalleryEntry:
    for entry in index.entries:
        if entry.id == entry_id:
            return entry
    raise GalleryError(f"unknown gallery entry: {entry_id!r}", code="not_found")
