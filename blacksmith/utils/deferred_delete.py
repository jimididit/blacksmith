"""Schedule file/dir deletion after process exit without shell path interpolation."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

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
