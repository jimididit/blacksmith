from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, List, Optional

_ID_RE = re.compile(r"^[a-z0-9-]+$")


class GalleryError(Exception):
    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


@dataclass
class GalleryEntry:
    id: str
    title: str
    description: str
    url: str
    signature_url: Optional[str]
    os: List[str]
    tags: List[str]
    provenance: str


@dataclass
class GalleryIndex:
    version: int
    entries: List[GalleryEntry]


def _require_str(data: dict, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise GalleryError(f"entry missing or invalid {key!r}", code="invalid_schema")
    return value.strip()


def _require_str_list(data: dict, key: str) -> List[str]:
    value = data.get(key)
    if not isinstance(value, list):
        raise GalleryError(f"entry missing or invalid {key!r}", code="invalid_schema")
    out: List[str] = []
    for item in value:
        if not isinstance(item, str):
            raise GalleryError(f"entry {key!r} must be strings", code="invalid_schema")
        out.append(item)
    return out


def _parse_https_url(value: str, *, field: str) -> str:
    url = value.strip()
    if not url.startswith("https://"):
        raise GalleryError(f"{field} must use HTTPS", code="invalid_schema")
    return url


def _parse_entry(raw: Any) -> GalleryEntry:
    if not isinstance(raw, dict):
        raise GalleryError("entry must be an object", code="invalid_schema")

    entry_id = _require_str(raw, "id")
    if not _ID_RE.match(entry_id):
        raise GalleryError(f"invalid entry id: {entry_id!r}", code="invalid_schema")

    title = _require_str(raw, "title")
    description = _require_str(raw, "description")
    url = _parse_https_url(_require_str(raw, "url"), field="url")

    signature_url: Optional[str] = None
    if "signature_url" in raw and raw["signature_url"] is not None:
        if not isinstance(raw["signature_url"], str):
            raise GalleryError("signature_url must be a string", code="invalid_schema")
        signature_url = _parse_https_url(raw["signature_url"], field="signature_url")

    os_list = _require_str_list(raw, "os")
    tags = _require_str_list(raw, "tags")

    provenance = "official"
    if "provenance" in raw and raw["provenance"] is not None:
        if not isinstance(raw["provenance"], str) or not raw["provenance"].strip():
            raise GalleryError("provenance must be a non-empty string", code="invalid_schema")
        provenance = raw["provenance"].strip()

    return GalleryEntry(
        id=entry_id,
        title=title,
        description=description,
        url=url,
        signature_url=signature_url,
        os=os_list,
        tags=tags,
        provenance=provenance,
    )


def parse_index(data: dict) -> GalleryIndex:
    if not isinstance(data, dict):
        raise GalleryError("index must be an object", code="invalid_schema")

    version = data.get("version")
    if version != 1:
        raise GalleryError("unsupported index version", code="invalid_schema")

    raw_entries = data.get("entries")
    if not isinstance(raw_entries, list):
        raise GalleryError("entries must be a list", code="invalid_schema")

    entries: List[GalleryEntry] = []
    seen: set[str] = set()
    for raw in raw_entries:
        entry = _parse_entry(raw)
        if entry.id in seen:
            raise GalleryError(f"duplicate entry id: {entry.id!r}", code="invalid_schema")
        seen.add(entry.id)
        entries.append(entry)

    return GalleryIndex(version=1, entries=entries)
