"""Schedule file/dir deletion after process exit without shell path interpolation."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Sequence

from blacksmith.utils.safe_paths import (
    assert_safe_blacksmith_executable,
    assert_safe_blacksmith_venv,
)

# Path is passed as argv — never interpolated into the script body.
_CLEANUP_PY = '''\
import shutil
import sys
import time
from pathlib import Path

def main() -> None:
    time.sleep(2)
    kind = sys.argv[1]
    target = Path(sys.argv[2]).resolve()
    expected = Path(sys.argv[3]).resolve()
    if target != expected:
        raise SystemExit(2)
    if kind == "file":
        if target.is_file():
            target.unlink()
    elif kind == "dir":
        if target.is_dir():
            shutil.rmtree(target)
    try:
        Path(__file__).resolve().unlink()
    except OSError:
        pass

if __name__ == "__main__":
    main()
'''

# Delayed pip/pipx uninstall; command argv starts at sys.argv[1].
_PIP_UNINSTALL_PY = '''\
import subprocess
import sys
import time
from pathlib import Path

def main() -> None:
    time.sleep(2)
    cmd = sys.argv[1:]
    if not cmd or "uninstall" not in cmd:
        raise SystemExit(2)
    allowed = {"jdi-blacksmith", "blacksmith"}
    if not any(part in allowed for part in cmd):
        raise SystemExit(2)
    subprocess.run(cmd, check=False)
    try:
        Path(__file__).resolve().unlink()
    except OSError:
        pass

if __name__ == "__main__":
    main()
'''


def _write_cleanup_script() -> Path:
    fd, path = tempfile.mkstemp(suffix=".py", prefix="blacksmith_cleanup_", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(_CLEANUP_PY)
    return Path(path)


def _spawn_cleanup(script: Path, kind: str, target: Path) -> None:
    kwargs = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    subprocess.Popen(
        [sys.executable, str(script), kind, str(target), str(target)],
        **kwargs,
    )


def schedule_delete_file(path: Path | str) -> bool:
    """Validate then schedule deletion of a Blacksmith executable."""
    safe = assert_safe_blacksmith_executable(path)
    script = _write_cleanup_script()
    _spawn_cleanup(script, "file", safe)
    return True


def schedule_delete_venv(path: Path | str) -> bool:
    """Validate then schedule deletion of ~/.blacksmith-venv."""
    safe = assert_safe_blacksmith_venv(path)
    script = _write_cleanup_script()
    _spawn_cleanup(script, "dir", safe)
    return True


def schedule_pip_uninstall(cmd: Sequence[str]) -> bool:
    """
    Run a pip/pipx uninstall command shortly after this process exits.

    Used on Windows when the running blacksmith.exe locks in-process uninstall.
    """
    argv = [str(part) for part in cmd]
    if not argv or "uninstall" not in argv:
        return False
    allowed_pkgs = {"jdi-blacksmith", "blacksmith"}
    if not any(part in allowed_pkgs for part in argv):
        return False
    if not Path(argv[0]).exists():
        from shutil import which

        resolved = which(argv[0])
        if not resolved:
            return False
        argv[0] = resolved

    fd, path = tempfile.mkstemp(suffix=".py", prefix="blacksmith_pip_uninstall_", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(_PIP_UNINSTALL_PY)
    script = Path(path)
    kwargs = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    subprocess.Popen([sys.executable, str(script), *argv], **kwargs)
    return True


def sibling_pip_uninstall_cmds(
    blacksmith_path: Optional[Path | str],
    package: str = "jdi-blacksmith",
) -> List[List[str]]:
    """pip uninstall commands using pip.exe next to the blacksmith entry point."""
    if not blacksmith_path:
        return []
    scripts = Path(blacksmith_path).expanduser().resolve().parent
    names = ["pip.exe", "pip3.exe", "pip"]
    for child in sorted(scripts.glob("pip3*.exe")):
        if child.name not in names:
            names.append(child.name)
    cmds: List[List[str]] = []
    seen = set()
    for name in names:
        pip = scripts / name
        if not pip.is_file():
            continue
        key = str(pip.resolve())
        if key in seen:
            continue
        seen.add(key)
        cmds.append([str(pip), "uninstall", package, "-y"])
    return cmds


def _is_windows() -> bool:
    return os.name == "nt"


def try_unlock_windows_executable(path: Path | str) -> Optional[Path]:
    """
    Rename a locked Windows .exe so pip can replace/remove it.

    Returns the backup path when rename succeeds, else None.
    """
    if not _is_windows():
        return None
    target = Path(path).expanduser().resolve()
    if not target.is_file():
        return None
    backup = target.with_name(target.name + ".old")
    try:
        if backup.exists():
            backup.unlink()
        target.rename(backup)
        return backup
    except OSError:
        return None


def remove_venv_now(path: Path | str) -> Path:
    """Validate then immediately delete ~/.blacksmith-venv."""
    import shutil

    safe = assert_safe_blacksmith_venv(path)
    if safe.is_dir():
        shutil.rmtree(safe)
    return safe


def remove_executable_now(path: Path | str) -> Path:
    """Validate then immediately delete a Blacksmith executable."""
    safe = assert_safe_blacksmith_executable(path)
    if safe.is_file():
        safe.unlink()
    return safe


# Alias used by uninstall CLI
remove_file_now = remove_executable_now
