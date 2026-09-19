"""Human-mode info lists all packages (not a 5-item sample)."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from blacksmith.cli import cli


def _runner() -> CliRunner:
    return CliRunner()


def test_info_lists_all_packages(tmp_path: Path):
    cfg = tmp_path / "many.yaml"
    lines = [
        'name: "many"',
        'description: "test"',
        "packages:",
    ]
    for i in range(8):
        lines.append(f'  - name: pkg{i}')
        lines.append(f"    managers:")
        lines.append(f'      apt: "pkg{i}"')
    cfg.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = _runner().invoke(cli, ["info", "--file", str(cfg), "--no-pager"])
    assert result.exit_code == 0, result.output
    assert "Sample Packages" not in result.output
    assert "Package list:" in result.output
    for i in range(8):
        assert f"pkg{i}" in result.output
    assert "and 3 more" not in result.output


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
    assert "pkg0" in result.output
    assert "pkg2" in result.output
    assert "pkg7" not in result.output
    assert "and 5 more" in result.output
