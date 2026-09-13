"""Trust-boundary regressions for subprocess usage."""

from pathlib import Path
import re

import pytest

PACKAGE_MANAGERS_DIR = Path(__file__).resolve().parents[1] / "blacksmith" / "package_managers"


def test_package_managers_forbid_shell_true():
    """Package manager modules must not use shell=True (N1 / TB-001)."""
    offenders = []
    pattern = re.compile(r"shell\s*=\s*True")
    for path in PACKAGE_MANAGERS_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), start=1):
            if pattern.search(line):
                offenders.append(f"{path.name}:{i}: {line.strip()}")
    assert not offenders, "shell=True found in package_managers:\n" + "\n".join(offenders)


def test_windows_managers_importable():
    from blacksmith.package_managers.winget import WingetManager
    from blacksmith.package_managers.chocolatey import ChocolateyManager
    from blacksmith.package_managers.scoop import ScoopManager

    assert WingetManager().name == "winget"
    assert ChocolateyManager().name == "chocolatey"
    assert ScoopManager().name == "scoop"
