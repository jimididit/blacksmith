"""HTTPS fetch of remote set YAML into temporary files."""

from __future__ import annotations

import hashlib
import ipaddress
import socket
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

DEFAULT_TIMEOUT_S = 30
DEFAULT_MAX_BYTES = 1_048_576

_READ_CHUNK = 8192


@dataclass
class FetchedSet:
    path: Path
    final_url: str
    sha256: str
    signature_path: Optional[Path] = None
    signature_is_temp: bool = False


class FetchError(Exception):
    """User-facing fetch / URL validation failure."""

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


def validate_https_url(url: str) -> str:
    """Return normalized URL or raise FetchError."""
    if url is None:
        raise FetchError("URL is required", code="invalid_url")
    normalized = url.strip()
    if not normalized:
        raise FetchError("URL is required", code="invalid_url")
    parsed = urlparse(normalized)
    if parsed.scheme.lower() != "https":
        raise FetchError("URL must use HTTPS", code="invalid_url")
    if not parsed.netloc:
        raise FetchError("URL must include a host", code="invalid_url")
    return normalized


def is_blocked_host(hostname: str) -> bool:
    """True for localhost / loopback / link-local / RFC1918 literal hosts."""
    if not hostname:
        return True
    host = hostname.strip().lower()
    if host == "localhost":
        return True
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return False
    if addr.is_loopback:
        return True
    if addr.is_link_local:
        return True
    if addr.is_private:
        return True
    return False


def _reject_blocked_url(url: str) -> None:
    """Raise FetchError if URL is not HTTPS or host is blocked."""
    validate_https_url(url)
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if is_blocked_host(host):
        raise FetchError("URL host is not allowed", code="invalid_url")


class _HTTPSOnlyRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urlparse(newurl)
        if parsed.scheme.lower() != "https":
            raise FetchError(
                "redirect to non-HTTPS URL rejected", code="invalid_url"
            )
        host = parsed.hostname or ""
        if is_blocked_host(host):
            raise FetchError("URL host is not allowed", code="invalid_url")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def urlopen(request: Request, timeout: Optional[float] = None):
    """Open HTTPS requests; patched in unit tests."""
    opener = build_opener(_HTTPSOnlyRedirectHandler())
    return opener.open(request, timeout=timeout)


def _read_limited_response(resp, max_bytes: int) -> Tuple[bytes, str]:
    hasher = hashlib.sha256()
    parts = []
    total = 0
    while True:
        chunk = resp.read(_READ_CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise FetchError("response exceeds size limit")
        hasher.update(chunk)
        parts.append(chunk)
    return b"".join(parts), hasher.hexdigest()


def _fetch_bytes(
    url: str,
    *,
    timeout_s: int,
    max_bytes: int,
) -> Tuple[bytes, str, str]:
    """Return body, sha256 hex, final URL after redirects."""
    _reject_blocked_url(url)

    request = Request(url, headers={"User-Agent": "blacksmith/1.0"})
    try:
        with urlopen(request, timeout=timeout_s) as resp:
            final_url = getattr(resp, "url", None) or url
            _reject_blocked_url(final_url)
            body, digest = _read_limited_response(resp, max_bytes)
            return body, digest, final_url
    except HTTPError as exc:
        location = exc.headers.get("Location") if exc.headers else None
        if location:
            loc_parsed = urlparse(location)
            if loc_parsed.scheme.lower() != "https":
                raise FetchError(
                    "redirect to non-HTTPS URL rejected", code="invalid_url"
                ) from exc
            if is_blocked_host(loc_parsed.hostname or ""):
                raise FetchError(
                    "URL host is not allowed", code="invalid_url"
                ) from exc
        raise FetchError(
            f"fetch failed: HTTP {exc.code}", code=f"http_{exc.code}"
        ) from exc
    except FetchError:
        raise
    except URLError as exc:
        raise FetchError(f"fetch failed: {exc.reason}") from exc
    except socket.timeout as exc:
        raise FetchError("fetch timed out") from exc


def _write_temp(body: bytes, suffix: str) -> Path:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        tmp.write(body)
    finally:
        tmp.close()
    return Path(tmp.name)


def _maybe_fetch_signature(
    signature_url_or_path: Optional[str],
    final_url: str,
    *,
    fetch_sidecar: bool,
    timeout_s: int,
    max_bytes: int,
) -> Tuple[Optional[Path], bool]:
    """Return (signature_path, is_temp). Local paths are not owned temps."""
    if signature_url_or_path:
        spec = signature_url_or_path.strip()
        if not spec:
            return None, False
        parsed = urlparse(spec)
        if parsed.scheme.lower() == "https":
            body, _, _ = _fetch_bytes(
                spec, timeout_s=timeout_s, max_bytes=max_bytes
            )
            return _write_temp(body, ".minisig"), True
        path = Path(spec).expanduser()
        if path.is_file():
            return path.resolve(), False
        raise FetchError("signature path not found")

    if not fetch_sidecar:
        return None, False

    sidecar_url = final_url + ".minisig"
    try:
        body, _, _ = _fetch_bytes(
            sidecar_url, timeout_s=timeout_s, max_bytes=max_bytes
        )
    except FetchError:
        # Optional sidecar: any failure means "no signature" (verify fails
        # closed later when --require-signature is set).
        return None, False
    return _write_temp(body, ".minisig"), True


def fetch_set_url(
    url: str,
    *,
    signature_url_or_path: Optional[str] = None,
    fetch_sidecar: bool = True,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> FetchedSet:
    """HTTPS GET YAML to temp; optional sidecar or explicit signature."""
    body, digest, final_url = _fetch_bytes(
        url, timeout_s=timeout_s, max_bytes=max_bytes
    )
    yaml_path = _write_temp(body, ".yaml")
    try:
        signature_path, signature_is_temp = _maybe_fetch_signature(
            signature_url_or_path,
            final_url,
            fetch_sidecar=fetch_sidecar,
            timeout_s=timeout_s,
            max_bytes=max_bytes,
        )
    except Exception:
        try:
            yaml_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return FetchedSet(
        path=yaml_path,
        final_url=final_url,
        sha256=digest,
        signature_path=signature_path,
        signature_is_temp=signature_is_temp,
    )


def cleanup_fetched(fetched: FetchedSet) -> None:
    """Unlink owned temp YAML and signature; never delete user signature paths."""
    try:
        Path(fetched.path).unlink(missing_ok=True)
    except OSError:
        pass
    if fetched.signature_path is None or not fetched.signature_is_temp:
        return
    try:
        Path(fetched.signature_path).unlink(missing_ok=True)
    except OSError:
        pass
