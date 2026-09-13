"""Platform config directory and audit log path."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def user_config_dir() -> Path:
    """User Blacksmith config directory (parent of trusted_keys)."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home())
        return (base / "blacksmith").resolve()
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return (Path(xdg) / "blacksmith").resolve()
    return (Path.home() / ".config" / "blacksmith").resolve()


def default_audit_log_path() -> Path:
    return user_config_dir() / "audit.jsonl"
