"""Detect pipx-managed installs and build uninstall command candidates."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import List, Optional, Sequence


def read_shebang_interpreter(path: Optional[Path | str]) -> Optional[str]:
    """Return interpreter path from a script shebang, if present."""
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            first = handle.readline().strip()
    except OSError:
        return None
    if not first.startswith("#!"):
        return None
    interp = first[2:].strip()
    if " " in interp:
        interp = interp.split()[0]
    return interp or None


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
    # ~/.local/bin/blacksmith shebang often points into pipx/venvs/...
    shebang = read_shebang_interpreter(resolved)
    if shebang and ("pipx" in Path(shebang).parts or is_pipx_prefix(Path(shebang).resolve().parent.parent)):
        return True
    return False


def pipx_package_name(
    prefix: Optional[Path | str] = None,
    executable: Optional[Path | str] = None,
) -> Optional[str]:
    """
    Package/spec name for `pipx uninstall`.

    Prefers the venv directory under .../pipx/venvs/<name>.
    """
    candidates: List[Path] = []
    if prefix:
        candidates.append(Path(prefix))
    candidates.append(Path(sys.prefix))
    if executable:
        shebang = read_shebang_interpreter(executable)
        if shebang:
            candidates.append(Path(shebang).resolve().parent.parent)
        candidates.append(Path(executable))

    for cand in candidates:
        try:
            parts = list(cand.expanduser().resolve().parts)
        except OSError:
            continue
        lower = [p.lower() for p in parts]
        if "venvs" in lower:
            idx = lower.index("venvs")
            if idx + 1 < len(parts):
                return parts[idx + 1]
        if is_pipx_prefix(cand):
            return cand.expanduser().resolve().name
    return None


def should_use_pipx_uninstall(
    prefix: Optional[Path | str] = None,
    executable: Optional[Path | str] = None,
) -> bool:
    """Whether uninstall should prefer the pipx CLI (and not raw pip)."""
    return (
        is_pipx_prefix(prefix)
        or is_pipx_executable(executable)
        or bool(pipx_package_name(prefix=prefix, executable=executable))
    )


def _dedupe_cmds(cmds: Sequence[Sequence[str]]) -> List[List[str]]:
    seen = set()
    out: List[List[str]] = []
    for cmd in cmds:
        key = tuple(cmd)
        if key in seen:
            continue
        seen.add(key)
        out.append(list(cmd))
    return out


def pipx_uninstall_commands(
    package: str = "jdi-blacksmith",
    extra_packages: Optional[Sequence[str]] = None,
) -> List[List[str]]:
    """
    Candidate argv lists for uninstalling via pipx.

    Tries PATH `pipx`, then `python -m pipx` with common interpreters.
    """
    packages = [package]
    if extra_packages:
        for name in extra_packages:
            if name and name not in packages:
                packages.append(name)

    bins: List[str] = []
    which = shutil.which("pipx")
    if which:
        bins.append(which)
    # Common user install location when PATH is incomplete (SSH / sudo -i)
    home_pipx = Path.home() / ".local" / "bin" / "pipx"
    if home_pipx.is_file():
        bins.append(str(home_pipx))

    pythons: List[str] = []
    for candidate in (
        shutil.which("python3"),
        shutil.which("python"),
        sys.executable,
    ):
        if candidate:
            pythons.append(candidate)

    cmds: List[List[str]] = []
    for pkg in packages:
        for pipx_bin in bins:
            cmds.append([pipx_bin, "uninstall", pkg])
        for py in pythons:
            cmds.append([py, "-m", "pipx", "uninstall", pkg])
    return _dedupe_cmds(cmds)
