"""User and packaged trust-store path helpers."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Optional, Sequence


def user_trusted_keys_dir() -> Path:
    """Directory for user-added minisign public keys (*.pub)."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home())
        return (base / "blacksmith" / "trusted_keys").resolve()
    # Linux / macOS: XDG-style under ~/.config
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return (Path(xdg) / "blacksmith" / "trusted_keys").resolve()
    return (Path.home() / ".config" / "blacksmith" / "trusted_keys").resolve()


def bundled_keys_dir() -> Path:
    """Packaged blacksmith/keys directory (may be empty until official .pub added)."""
    return (Path(__file__).resolve().parent.parent / "keys").resolve()


def iter_trusted_pubkeys(
    extra: Optional[Sequence[Path]] = None,
) -> List[Path]:
    """
    Collect *.pub paths: bundled keys, user trusted_keys, then extras.

    Order is stable; duplicates (same resolve path) are skipped.
    """
    found: List[Path] = []
    seen = set()

    def _add(path: Path) -> None:
        try:
            resolved = path.expanduser().resolve()
        except OSError:
            return
        if not resolved.is_file():
            return
        if resolved.suffix.lower() != ".pub":
            return
        key = str(resolved)
        if key in seen:
            return
        seen.add(key)
        found.append(resolved)

    bundled = bundled_keys_dir()
    if bundled.is_dir():
        for path in sorted(bundled.glob("*.pub")):
            _add(path)

    user_dir = user_trusted_keys_dir()
    if user_dir.is_dir():
        for path in sorted(user_dir.glob("*.pub")):
            _add(path)

    if extra:
        for path in extra:
            _add(Path(path))

    return found
