"""Unit tests for HTTPS fetch of remote set YAML."""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from blacksmith.trust.fetch import (
    FetchError,
    FetchedSet,
    _HTTPSOnlyRedirectHandler,
    cleanup_fetched,
    fetch_set_url,
    is_blocked_host,
    validate_https_url,
)


class TestValidateHttpsUrl:
    def test_rejects_http(self):
        with pytest.raises(FetchError) as excinfo:
            validate_https_url("http://example.com/set.yaml")
        assert excinfo.value.code == "invalid_url"

    def test_rejects_empty(self):
        with pytest.raises(FetchError):
            validate_https_url("")

    def test_rejects_ftp(self):
        with pytest.raises(FetchError) as excinfo:
            validate_https_url("ftp://example.com/set.yaml")
        assert excinfo.value.code == "invalid_url"

    def test_accepts_https(self):
        assert validate_https_url("https://example.com/sets/lab.yaml") == (
            "https://example.com/sets/lab.yaml"
        )


class TestHTTPSOnlyRedirectHandler:
    def test_rejects_redirect_to_blocked_host(self):
        handler = _HTTPSOnlyRedirectHandler()
        with pytest.raises(FetchError, match="not allowed"):
            handler.redirect_request(
                None, None, 302, "Found", {}, "https://10.0.0.1/set.yaml"
            )


class TestIsBlockedHost:
    @pytest.mark.parametrize(
        "host",
        ["127.0.0.1", "localhost", "10.0.0.1", "192.168.1.1", "169.254.1.1"],
    )
    def test_blocked_literals(self, host):
        assert is_blocked_host(host) is True

    def test_public_host_ok(self):
        assert is_blocked_host("example.com") is False


def _mock_response(body: bytes, url: str) -> MagicMock:
    resp = MagicMock()
    consumed = {"done": False}

    def read(size=-1):
        if consumed["done"]:
            return b""
        consumed["done"] = True
        return body

    resp.read = read
    resp.__enter__ = lambda self: self
    resp.__exit__ = lambda *args: None
    resp.url = url
    return resp


class TestFetchSetUrl:
    @patch("blacksmith.trust.fetch.urlopen")
    def test_fetch_returns_path_hash_and_final_url(self, mock_urlopen, tmp_path):
        body = b"name: lab\npackages: []\n"
        final = "https://example.com/a.yaml"
        mock_urlopen.return_value = _mock_response(body, final)

        fetched = fetch_set_url(final, fetch_sidecar=False)

        try:
            assert fetched.final_url == final
            assert fetched.sha256 == hashlib.sha256(body).hexdigest()
            assert fetched.path.is_file()
            assert fetched.path.read_bytes() == body
            assert fetched.signature_path is None
        finally:
            cleanup_fetched(fetched)

    @patch("blacksmith.trust.fetch.urlopen")
    def test_size_limit_raises(self, mock_urlopen):
        body = b"x" * 10
        mock_urlopen.return_value = _mock_response(body, "https://example.com/a.yaml")

        with pytest.raises(FetchError, match="size"):
            fetch_set_url(
                "https://example.com/a.yaml",
                fetch_sidecar=False,
                max_bytes=5,
            )

    def test_rejects_blocked_initial_host(self):
        with pytest.raises(FetchError, match="not allowed") as excinfo:
            fetch_set_url("https://127.0.0.1/set.yaml", fetch_sidecar=False)
        assert excinfo.value.code == "invalid_url"

    @patch("blacksmith.trust.fetch.urlopen")
    def test_rejects_blocked_final_url_after_redirect(self, mock_urlopen):
        body = b"name: lab\npackages: []\n"
        mock_urlopen.return_value = _mock_response(
            body, "https://127.0.0.1/set.yaml"
        )

        with pytest.raises(FetchError, match="not allowed") as excinfo:
            fetch_set_url("https://example.com/set.yaml", fetch_sidecar=False)
        assert excinfo.value.code == "invalid_url"

    @patch("blacksmith.trust.fetch.urlopen")
    def test_redirect_to_http_raises(self, mock_urlopen):
        from urllib.error import HTTPError

        err = HTTPError(
            "https://example.com/a.yaml",
            302,
            "Found",
            {"Location": "http://evil.com/a.yaml"},
            None,
        )
        mock_urlopen.side_effect = err

        with pytest.raises(FetchError):
            fetch_set_url("https://example.com/a.yaml", fetch_sidecar=False)

    @patch("blacksmith.trust.fetch.urlopen")
    def test_sidecar_404_leaves_signature_none(self, mock_urlopen):
        from urllib.error import HTTPError

        body = b"name: t\npackages: []\n"
        final = "https://example.com/a.yaml"

        def urlopen_side_effect(req, timeout=None):
            url = req.full_url if hasattr(req, "full_url") else req.get_full_url()
            if url == final:
                return _mock_response(body, final)
            if url == final + ".minisig":
                raise HTTPError(url, 404, "Not Found", {}, None)
            raise AssertionError(f"unexpected url {url}")

        mock_urlopen.side_effect = urlopen_side_effect

        fetched = fetch_set_url(final, fetch_sidecar=True)
        try:
            assert fetched.signature_path is None
        finally:
            cleanup_fetched(fetched)

    @patch("blacksmith.trust.fetch.urlopen")
    def test_sidecar_500_soft_skips_when_optional(self, mock_urlopen):
        from urllib.error import HTTPError

        body = b"name: t\npackages: []\n"
        final = "https://example.com/a.yaml"

        def urlopen_side_effect(req, timeout=None):
            url = req.full_url if hasattr(req, "full_url") else req.get_full_url()
            if url == final:
                return _mock_response(body, final)
            if url == final + ".minisig":
                raise HTTPError(url, 500, "Internal Server Error", {}, None)
            raise AssertionError(f"unexpected url {url}")

        mock_urlopen.side_effect = urlopen_side_effect

        fetched = fetch_set_url(final, fetch_sidecar=True)
        try:
            assert fetched.signature_path is None
            assert fetched.path.is_file()
        finally:
            cleanup_fetched(fetched)

    @patch("blacksmith.trust.fetch.urlopen")
    def test_local_signature_survives_cleanup(self, mock_urlopen, tmp_path):
        body = b"name: t\npackages: []\n"
        final = "https://example.com/a.yaml"
        mock_urlopen.return_value = _mock_response(body, final)

        user_sig = tmp_path / "user.minisig"
        user_sig.write_bytes(b"untrusted-sig")

        fetched = fetch_set_url(
            final,
            signature_url_or_path=str(user_sig),
            fetch_sidecar=False,
        )
        assert fetched.signature_path == user_sig.resolve()
        assert fetched.signature_is_temp is False

        cleanup_fetched(fetched)

        assert not fetched.path.exists()
        assert user_sig.exists()

    @patch("blacksmith.trust.fetch.urlopen")
    def test_signature_failure_cleans_yaml_temp(self, mock_urlopen, tmp_path):
        from urllib.error import HTTPError

        body = b"name: t\npackages: []\n"
        final = "https://example.com/a.yaml"
        sig_url = "https://example.com/explicit.minisig"
        before = set(Path(tempfile.gettempdir()).glob("tmp*.yaml"))

        def urlopen_side_effect(req, timeout=None):
            url = req.full_url if hasattr(req, "full_url") else req.get_full_url()
            if url == final:
                return _mock_response(body, final)
            if url == sig_url:
                raise HTTPError(url, 500, "Internal Server Error", {}, None)
            raise AssertionError(f"unexpected url {url}")

        mock_urlopen.side_effect = urlopen_side_effect

        with pytest.raises(FetchError, match="HTTP 500"):
            fetch_set_url(
                final,
                signature_url_or_path=sig_url,
                fetch_sidecar=False,
            )

        after = set(Path(tempfile.gettempdir()).glob("tmp*.yaml"))
        leaked = after - before
        assert not leaked, f"YAML temp leaked: {leaked}"


class TestCleanupFetched:
    def test_removes_yaml_and_owned_signature(self, tmp_path):
        yaml_path = tmp_path / "set.yaml"
        sig_path = tmp_path / "set.yaml.minisig"
        yaml_path.write_bytes(b"yaml")
        sig_path.write_bytes(b"sig")

        fetched = FetchedSet(
            path=yaml_path,
            final_url="https://example.com/a.yaml",
            sha256="abc",
            signature_path=sig_path,
            signature_is_temp=True,
        )
        cleanup_fetched(fetched)

        assert not yaml_path.exists()
        assert not sig_path.exists()

    def test_preserves_user_owned_signature(self, tmp_path):
        yaml_path = tmp_path / "set.yaml"
        sig_path = tmp_path / "user.minisig"
        yaml_path.write_bytes(b"yaml")
        sig_path.write_bytes(b"sig")

        fetched = FetchedSet(
            path=yaml_path,
            final_url="https://example.com/a.yaml",
            sha256="abc",
            signature_path=sig_path,
            signature_is_temp=False,
        )
        cleanup_fetched(fetched)

        assert not yaml_path.exists()
        assert sig_path.exists()
