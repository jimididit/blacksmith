"""Human-mode info lists all packages (not a 5-item sample)."""

from __future__ import annotations

import re
from pathlib import Path

from click.testing import CliRunner

from blacksmith.cli import cli

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _runner() -> CliRunner:
    return CliRunner()


def _plain(text: str) -> str:
    return _ANSI_RE.sub("", text)


def test_info_lists_all_packages(tmp_path: Path):
    cfg = tmp_path / "many.yaml"
    lines = [
        'name: "many"',
        'description: "test"',
        "packages:",
    ]
    for i in range(8):
        lines.append(f'  - name: pkg{i}')
        lines.append("    managers:")
        lines.append(f'      apt: "pkg{i}"')
    cfg.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = _runner().invoke(cli, ["info", "--file", str(cfg), "--no-pager"])
    assert result.exit_code == 0, result.output
    out = _plain(result.output)
    assert "Sample Packages" not in out
    assert "Package list:" in out
    for i in range(8):
        assert f"pkg{i}" in out
    assert "and 3 more" not in out


def test_info_limit_truncates_with_hint(tmp_path: Path):
    cfg = tmp_path / "many.yaml"
    lines = ['name: "many"', "packages:"]
    for i in range(8):
        lines.append(f'  - name: pkg{i}')
        lines.append("    managers:")
        lines.append(f'      apt: "pkg{i}"')
    cfg.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = _runner().invoke(
        cli, ["info", "--file", str(cfg), "--limit", "3", "--no-pager"]
    )
    assert result.exit_code == 0, result.output
    out = _plain(result.output)
    assert "pkg0" in out
    assert "pkg2" in out
    assert "pkg7" not in out
    assert "and 5 more" in out
