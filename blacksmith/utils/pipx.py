"""Detect pipx-managed installs for uninstall routing."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional


def is_pipx_prefix(prefix: Optional[Path | str] = None) -> bool:
    """
    True when prefix looks like a pipx app venv (.../pipx/venvs/<pkg>).

    Also true when prefix is under PIPX_HOME/venvs if that env var is set.
    """
    resolved = Path(prefix or sys.prefix).expanduser().resolve()
    parts = [p.lower() for p in resolved.parts]
    if "pipx" in parts and "venvs" in parts:
        return True

    pipx_home = os.environ.get("PIPX_HOME")
    if pipx_home:
        try:
            resolved.relative_to((Path(pipx_home).expanduser().resolve() / "venvs"))
            return True
        except ValueError:
            pass
    return False


def is_pipx_executable(path: Optional[Path | str]) -> bool:
    """True when a blacksmith executable path sits under a pipx layout."""
    if not path:
        return False
    resolved = Path(path).expanduser().resolve()
    parts = [p.lower() for p in resolved.parts]
    if "pipx" in parts:
        return True
    pipx_bin = os.environ.get("PIPX_BIN_DIR")
    if pipx_bin:
        try:
            resolved.relative_to(Path(pipx_bin).expanduser().resolve())
            return True
        except ValueError:
            pass
    return False


def pipx_package_name(prefix: Optional[Path | str] = None) -> Optional[str]:
    """
    Package/spec name for `pipx uninstall` from the venv directory name.

    Returns None when prefix is not a pipx venv.
    """
    if not is_pipx_prefix(prefix):
        return None
    name = Path(prefix or sys.prefix).expanduser().resolve().name
    return name or None


def should_use_pipx_uninstall(
    prefix: Optional[Path | str] = None,
    executable: Optional[Path | str] = None,
) -> bool:
    """Whether uninstall should prefer the pipx CLI."""
    return is_pipx_prefix(prefix) or is_pipx_executable(executable)
