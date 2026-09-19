import json
from unittest.mock import patch

import pytest

from blacksmith.gallery.index import get_entry, load_index, parse_index
from blacksmith.gallery.schema import GalleryError


def test_parse_index_minimal():
    idx = parse_index(
        {
            "version": 1,
            "entries": [
                {
                    "id": "dfir-triage",
                    "title": "DFIR triage",
                    "description": "desc",
                    "url": "https://example.com/a.yaml",
                    "os": ["linux"],
                    "tags": ["dfir"],
                    "provenance": "official",
                }
            ],
        }
    )
    assert idx.version == 1
    assert idx.entries[0].id == "dfir-triage"
    assert idx.entries[0].signature_url is None


def test_parse_index_rejects_bad_id():
    with pytest.raises(GalleryError):
        parse_index(
            {
                "version": 1,
                "entries": [
                    {
                        "id": "BAD ID",
                        "title": "t",
                        "description": "d",
                        "url": "https://example.com/a.yaml",
                        "os": [],
                        "tags": [],
                        "provenance": "official",
                    }
                ],
            }
        )


def test_parse_index_rejects_http_url():
    with pytest.raises(GalleryError):
        parse_index(
            {
                "version": 1,
                "entries": [
                    {
                        "id": "x",
                        "title": "t",
                        "description": "d",
                        "url": "http://example.com/a.yaml",
                        "os": [],
                        "tags": [],
                        "provenance": "official",
                    }
                ],
            }
        )


def test_load_index_uses_bundled_when_no_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "blacksmith.gallery.paths.user_config_dir",
        lambda: tmp_path,
    )
    idx = load_index(refresh=False)
    assert idx.version == 1
    assert isinstance(idx.entries, list)


def test_get_entry_unknown():
    idx = parse_index({"version": 1, "entries": []})
    with pytest.raises(GalleryError) as ei:
        get_entry(idx, "missing")
    assert ei.value.code == "not_found"


def test_refresh_writes_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "blacksmith.gallery.paths.user_config_dir",
        lambda: tmp_path,
    )
    body = json.dumps(
        {
            "version": 1,
            "entries": [
                {
                    "id": "web-assess",
                    "title": "Web",
                    "description": "d",
                    "url": "https://example.com/w.yaml",
                    "os": ["linux"],
                    "tags": ["web"],
                    "provenance": "official",
                }
            ],
        }
    ).encode("utf-8")

    with patch(
        "blacksmith.gallery.index.fetch_https_bytes",
        return_value=(body, "abc", "https://raw.githubusercontent.com/x"),
    ):
        idx = load_index(refresh=True)

    assert idx.entries[0].id == "web-assess"
    cache = tmp_path / "gallery" / "index.json"
    assert cache.is_file()
    assert "web-assess" in cache.read_text(encoding="utf-8")


def test_refresh_fail_closed_preserves_cache_on_bad_remote(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "blacksmith.gallery.paths.user_config_dir",
        lambda: tmp_path,
    )
    cache = tmp_path / "gallery" / "index.json"
    cache.parent.mkdir(parents=True)
    good_body = json.dumps(
        {
            "version": 1,
            "entries": [
                {
                    "id": "cached-set",
                    "title": "Cached",
                    "description": "d",
                    "url": "https://example.com/c.yaml",
                    "os": ["linux"],
                    "tags": [],
                    "provenance": "official",
                }
            ],
        }
    )
    cache.write_text(good_body, encoding="utf-8")
    original = cache.read_text(encoding="utf-8")

    with patch(
        "blacksmith.gallery.index.fetch_https_bytes",
        return_value=(b"not-json", "abc", "https://raw.githubusercontent.com/x"),
    ):
        with pytest.raises(GalleryError):
            load_index(refresh=True)

    assert cache.read_text(encoding="utf-8") == original


def test_refresh_fail_closed_preserves_cache_on_schema_error(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "blacksmith.gallery.paths.user_config_dir",
        lambda: tmp_path,
    )
    cache = tmp_path / "gallery" / "index.json"
    cache.parent.mkdir(parents=True)
    good_body = json.dumps({"version": 1, "entries": []})
    cache.write_text(good_body, encoding="utf-8")
    original = cache.read_text(encoding="utf-8")

    bad_body = json.dumps(
        {
            "version": 1,
            "entries": [
                {
                    "id": "INVALID ID",
                    "title": "t",
                    "description": "d",
                    "url": "https://example.com/a.yaml",
                    "os": [],
                    "tags": [],
                    "provenance": "official",
                }
            ],
        }
    ).encode("utf-8")

    with patch(
        "blacksmith.gallery.index.fetch_https_bytes",
        return_value=(bad_body, "abc", "https://raw.githubusercontent.com/x"),
    ):
        with pytest.raises(GalleryError):
            load_index(refresh=True)

    assert cache.read_text(encoding="utf-8") == original
