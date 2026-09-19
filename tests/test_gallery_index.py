import json
from unittest.mock import patch

import pytest

from blacksmith.gallery.index import get_entry, load_index, parse_index
from blacksmith.gallery.schema import GalleryError
from blacksmith.trust.fetch import FetchError


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


def test_load_index_falls_back_to_bundled_on_invalid_utf8_cache(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        "blacksmith.gallery.paths.user_config_dir",
        lambda: tmp_path,
    )
    cache = tmp_path / "gallery" / "index.json"
    cache.parent.mkdir(parents=True)
    cache.write_bytes(b"\xff")

    idx = load_index(refresh=False)

    assert idx.version == 1
    assert "dfir-triage" in {entry.id for entry in idx.entries}


def test_bundled_seed_entries_are_valid_sets(tmp_path, monkeypatch):
    from blacksmith.config.loader import load_custom_config
    from blacksmith.config.validator import validate_config
    from blacksmith.gallery.paths import bundled_index_path

    monkeypatch.setattr(
        "blacksmith.gallery.paths.user_config_dir",
        lambda: tmp_path,
    )
    idx = load_index(refresh=False)
    assert len(idx.entries) >= 3
    ids = {entry.id for entry in idx.entries}
    assert "dfir-triage" in ids
    assert "web-assessment" in ids
    assert "network-recon" in ids
    for entry in idx.entries:
        assert entry.url.startswith("https://")
        local = bundled_index_path().parent / "sets" / f"{entry.id}.yaml"
        assert local.is_file(), local
        config = load_custom_config(str(local))
        ok, error = validate_config(config)
        assert ok, error


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


def test_refresh_wraps_fetch_error(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "blacksmith.gallery.paths.user_config_dir",
        lambda: tmp_path,
    )

    with patch(
        "blacksmith.gallery.index.fetch_https_bytes",
        side_effect=FetchError("fetch timed out"),
    ):
        with pytest.raises(GalleryError) as exc_info:
            load_index(refresh=True)

    assert exc_info.value.code == "gallery_refresh_failed"
    assert "fetch timed out" in str(exc_info.value)


def test_refresh_preserves_cache_on_invalid_utf8(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "blacksmith.gallery.paths.user_config_dir",
        lambda: tmp_path,
    )
    cache = tmp_path / "gallery" / "index.json"
    cache.parent.mkdir(parents=True)
    original = json.dumps({"version": 1, "entries": []})
    cache.write_text(original, encoding="utf-8")

    with patch(
        "blacksmith.gallery.index.fetch_https_bytes",
        return_value=(b"\xff", "abc", "https://raw.githubusercontent.com/x"),
    ):
        with pytest.raises(GalleryError) as exc_info:
            load_index(refresh=True)

    assert exc_info.value.code == "gallery_refresh_failed"
    assert cache.read_text(encoding="utf-8") == original


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
