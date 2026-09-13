"""Path validation for destructive uninstall operations."""

from __future__ import annotations

import sys
from pathlib import Path

VENV_DIRNAME = ".blacksmith-venv"

# Allowed executable basenames produced by pip/entry_points installs
_ALLOWED_EXE_NAMES = {
    "blacksmith",
    "blacksmith.exe",
    "blacksmith-script.py",
}


def expected_venv_path() -> Path:
    """Canonical Blacksmith venv path under the user home directory."""
    return (Path.home() / VENV_DIRNAME).resolve()


def assert_safe_blacksmith_venv(path: Path | str) -> Path:
    """
    Resolve and verify a path is exactly the expected ~/.blacksmith-venv.

    Raises:
        ValueError: if the path is not the expected venv directory
    """
    resolved = Path(path).expanduser().resolve()
    expected = expected_venv_path()
    if resolved != expected:
        raise ValueError(
            f"Refusing to delete unexpected venv path: {resolved} "
            f"(expected {expected})"
        )
    return resolved


def assert_safe_blacksmith_executable(path: Path | str) -> Path:
    """
    Resolve and verify a path looks like the Blacksmith CLI executable.

    Must be named blacksmith* and live under the user home or the active
    Python prefix (covers venv / --user installs).

    Raises:
        ValueError: if the path is outside allowed roots or has a bad name
    """
    resolved = Path(path).expanduser().resolve()
    name = resolved.name.lower()
    if name not in _ALLOWED_EXE_NAMES and not name.startswith("blacksmith"):
        raise ValueError(f"Refusing to delete unexpected executable name: {resolved.name}")

    allowed_roots = [Path.home().resolve(), Path(sys.prefix).resolve()]
    # Also allow the directory of the running interpreter (Scripts / bin)
    try:
        allowed_roots.append(Path(sys.executable).resolve().parent)
        allowed_roots.append(Path(sys.executable).resolve().parent.parent)
    except OSError:
        pass

    for root in allowed_roots:
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue

    raise ValueError(
        f"Refusing to delete executable outside allowed roots: {resolved}"
    )
