"""CLI tests for trust scan + --strict-trust (L4.4)."""

import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from blacksmith.cli import cli
from blacksmith.package_managers.results import InstallRunResult
from blacksmith.trust.fetch import FetchedSet
from blacksmith.trust.scan import Finding, ScanResult


def _ok_result():
    return InstallRunResult(
        ok=True,
        outcomes=[],
        changed=0,
        skipped=0,
        failed=0,
        dry_run=True,
    )


def _finding_result():
    return ScanResult(
        findings=[
            Finding(code="oversized", message="Set lists 99 packages (threshold 80)"),
        ]
    )


def _clean_result():
    return ScanResult(findings=[])


def _fetched(tmp_path: Path, url: str = "https://example.com/a.yaml") -> FetchedSet:
    path = tmp_path / "remote.yaml"
    path.write_text("name: remote\npackages: []\n", encoding="utf-8")
    return FetchedSet(
        path=path,
        final_url=url,
        sha256="abcd" * 16,
        signature_path=None,
    )


def _write_set(path: Path) -> None:
    path.write_text("name: t\npackages: []\n", encoding="utf-8")


@patch("blacksmith.cli.install_packages")
@patch("blacksmith.cli.scan_set")
def test_install_file_findings_warn_and_continue(mock_scan, mock_install):
    mock_scan.return_value = _finding_result()
    mock_install.return_value = _ok_result()

    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_set(Path("set.yaml"))
        result = runner.invoke(
            cli, ["install", "--file", "set.yaml", "--dry-run", "--yes"]
        )

    assert result.exit_code == 0, result.output
    assert "oversized" in result.output or "99 packages" in result.output
    assert "safe" not in result.output.lower()
    mock_install.assert_called_once()
    mock_scan.assert_called_once()


@patch("blacksmith.cli.install_packages")
@patch("blacksmith.cli.scan_set")
def test_install_file_strict_trust_fails_closed(mock_scan, mock_install):
    mock_scan.return_value = _finding_result()

    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_set(Path("set.yaml"))
        result = runner.invoke(
            cli,
            [
                "install",
                "--file",
                "set.yaml",
                "--strict-trust",
                "--dry-run",
                "--yes",
            ],
        )

    assert result.exit_code == 1
    assert "trust" in result.output.lower() or "oversized" in result.output
    assert "safe" not in result.output.lower()
    mock_install.assert_not_called()


@patch("blacksmith.cli.cleanup_fetched")
@patch("blacksmith.cli.install_packages")
@patch("blacksmith.cli.load_custom_config")
@patch("blacksmith.cli.scan_set")
@patch("blacksmith.cli.fetch_set_url")
def test_install_url_findings_fail_closed_without_strict(
    mock_fetch, mock_scan, mock_load, mock_install, mock_cleanup, tmp_path
):
    fetched = _fetched(tmp_path)
    mock_fetch.return_value = fetched
    mock_load.return_value = {"name": "remote", "packages": []}
    mock_scan.return_value = _finding_result()

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["install", "--url", "https://example.com/a.yaml", "--dry-run", "--yes"],
    )

    assert result.exit_code == 1
    assert "oversized" in result.output or "trust" in result.output.lower()
    assert "safe" not in result.output.lower()
    mock_install.assert_not_called()
    mock_cleanup.assert_called_once_with(fetched)


@patch("blacksmith.cli.install_packages")
@patch("blacksmith.cli.scan_set")
def test_install_file_strict_trust_json_trust_scan_failed(mock_scan, mock_install):
    mock_scan.return_value = _finding_result()

    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_set(Path("set.yaml"))
        result = runner.invoke(
            cli,
            [
                "--json",
                "install",
                "--file",
                "set.yaml",
                "--strict-trust",
                "--yes",
            ],
        )

    assert result.exit_code == 1
    body = json.loads(result.stdout.strip())
    assert body["ok"] is False
    assert body["error"]["code"] == "trust_scan_failed"
    findings = body["error"].get("data", {}).get("findings") or body.get("data", {}).get(
        "findings"
    )
    assert findings
    assert findings[0]["code"] == "oversized"
    assert "safe" not in json.dumps(body).lower()
    mock_install.assert_not_called()


@patch("blacksmith.cli.install_packages")
@patch("blacksmith.cli.load_set")
@patch("blacksmith.cli.scan_set")
def test_install_builtin_set_skips_scan(mock_scan, mock_load, mock_install):
    mock_load.return_value = {"name": "minimal", "packages": []}
    mock_install.return_value = _ok_result()

    runner = CliRunner()
    result = runner.invoke(cli, ["install", "minimal", "--dry-run", "--yes"])

    assert result.exit_code == 0, result.output
    mock_scan.assert_not_called()
    mock_install.assert_called_once()


@patch("blacksmith.cli.scan_set")
def test_validate_file_findings_warn_and_continue(mock_scan):
    mock_scan.return_value = _finding_result()

    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_set(Path("set.yaml"))
        result = runner.invoke(cli, ["validate", "set.yaml"])

    assert result.exit_code == 0, result.output
    assert "valid" in result.output.lower()
    assert "99 packages" in result.output or "oversized" in result.output
    assert "safe" not in result.output.lower()


@patch("blacksmith.cli.scan_set")
def test_validate_file_strict_trust_fails_closed(mock_scan):
    mock_scan.return_value = _finding_result()

    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_set(Path("set.yaml"))
        result = runner.invoke(cli, ["validate", "set.yaml", "--strict-trust"])

    assert result.exit_code == 1
    assert "safe" not in result.output.lower()


@patch("blacksmith.cli.cleanup_fetched")
@patch("blacksmith.cli.scan_set")
@patch("blacksmith.cli.fetch_set_url")
def test_validate_url_findings_fail_closed(mock_fetch, mock_scan, mock_cleanup, tmp_path):
    fetched = _fetched(tmp_path)
    mock_fetch.return_value = fetched
    mock_scan.return_value = _finding_result()

    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--url", "https://example.com/a.yaml"])

    assert result.exit_code == 1
    assert "safe" not in result.output.lower()
    mock_cleanup.assert_called_once_with(fetched)


@patch("blacksmith.cli.install_packages")
@patch("blacksmith.cli.scan_set")
def test_install_file_clean_scan_no_safe_badge(mock_scan, mock_install):
    mock_scan.return_value = _clean_result()
    mock_install.return_value = _ok_result()

    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_set(Path("set.yaml"))
        result = runner.invoke(
            cli, ["install", "--file", "set.yaml", "--dry-run", "--yes"]
        )

    assert result.exit_code == 0, result.output
    assert "safe" not in result.output.lower()
    assert "trusted" not in result.output.lower()
    mock_install.assert_called_once()
