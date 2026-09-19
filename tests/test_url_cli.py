"""CLI tests for install/apply/validate --url (L5.0)."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

from click.testing import CliRunner

from blacksmith.cli import cli
from blacksmith.package_managers.results import InstallRunResult, PackageStatus
from blacksmith.trust.fetch import FetchedSet


def _ok_result():
    return InstallRunResult(
        ok=True,
        outcomes=[],
        changed=0,
        skipped=0,
        failed=0,
        dry_run=True,
    )


def _fetched(tmp_path: Path, url: str = "https://example.com/a.yaml") -> FetchedSet:
    path = tmp_path / "remote.yaml"
    path.write_text(
        "name: remote\npackages: []\n",
        encoding="utf-8",
    )
    return FetchedSet(
        path=path,
        final_url=url,
        sha256="abcd" * 16,
        signature_path=None,
    )


@patch("blacksmith.cli.cleanup_fetched")
@patch("blacksmith.cli.install_packages")
@patch("blacksmith.cli.load_custom_config")
@patch("blacksmith.cli.fetch_set_url")
def test_install_url_dry_run_succeeds(
    mock_fetch, mock_load, mock_install, mock_cleanup, tmp_path
):
    fetched = _fetched(tmp_path)
    mock_fetch.return_value = fetched
    mock_load.return_value = {"name": "remote", "packages": []}
    mock_install.return_value = _ok_result()

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["install", "--url", "https://example.com/a.yaml", "--dry-run", "--yes"],
    )

    assert result.exit_code == 0, result.output
    mock_fetch.assert_called_once()
    mock_load.assert_called_once_with(str(fetched.path))
    mock_install.assert_called_once()
    assert mock_install.call_args.kwargs["config_source"].startswith("https://")
    mock_cleanup.assert_called_once_with(fetched)


@patch("blacksmith.cli.fetch_set_url")
def test_install_url_and_file_mutual_exclusion(mock_fetch, tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("set.yaml").write_text("name: t\npackages: []\n", encoding="utf-8")
        result = runner.invoke(
            cli,
            [
                "install",
                "--url",
                "https://example.com/a.yaml",
                "--file",
                "set.yaml",
                "--yes",
            ],
        )
    assert result.exit_code == 2
    assert "exactly one" in result.output.lower() or "mutually" in result.output.lower()
    mock_fetch.assert_not_called()


@patch("blacksmith.cli.fetch_set_url")
def test_install_set_name_and_url_mutual_exclusion(mock_fetch):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["install", "minimal", "--url", "https://example.com/a.yaml", "--yes"],
    )
    assert result.exit_code == 2
    assert "exactly one" in result.output.lower() or "mutually" in result.output.lower()
    mock_fetch.assert_not_called()


@patch("blacksmith.cli.cleanup_fetched")
@patch("blacksmith.cli.load_custom_config")
@patch("blacksmith.trust.verify.verify_set_signature")
@patch("blacksmith.cli.fetch_set_url")
def test_install_url_require_signature_fails_closed(
    mock_fetch, mock_verify, mock_load, mock_cleanup, tmp_path
):
    fetched = _fetched(tmp_path)
    mock_fetch.return_value = fetched
    mock_verify.return_value = Mock(ok=False, message="bad remote sig")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "install",
            "--url",
            "https://example.com/a.yaml",
            "--require-signature",
            "--yes",
        ],
    )

    assert result.exit_code == 1
    assert "bad remote sig" in result.output
    mock_load.assert_not_called()
    mock_cleanup.assert_called_once_with(fetched)


def test_require_signature_without_file_or_url_updated_message():
    runner = CliRunner()
    result = runner.invoke(cli, ["install", "minimal", "--require-signature"])
    assert result.exit_code == 1
    assert "--require-signature only applies with --file or --url" in result.output


@patch("blacksmith.cli.cleanup_fetched")
@patch("blacksmith.cli.fetch_set_url")
def test_validate_url_succeeds(mock_fetch, mock_cleanup, tmp_path):
    fetched = _fetched(tmp_path)
    fetched.path.write_text(
        "name: remote\npackages: []\n",
        encoding="utf-8",
    )
    mock_fetch.return_value = fetched

    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--url", "https://example.com/a.yaml"])

    assert result.exit_code == 0, result.output
    assert "valid" in result.output.lower()
    assert "https://example.com/a.yaml" in result.output
    mock_fetch.assert_called_once()
    assert mock_fetch.call_args.kwargs.get("fetch_sidecar") is False
    mock_cleanup.assert_called_once_with(fetched)


@patch("blacksmith.cli.fetch_set_url")
def test_validate_url_and_path_mutual_exclusion(mock_fetch, tmp_path):
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("set.yaml").write_text("name: t\npackages: []\n", encoding="utf-8")
        result = runner.invoke(
            cli,
            ["validate", "set.yaml", "--url", "https://example.com/a.yaml"],
        )
    assert result.exit_code == 2
    assert "exactly one" in result.output.lower()
    mock_fetch.assert_not_called()


@patch("blacksmith.cli.cleanup_fetched")
@patch("blacksmith.cli.install_packages")
@patch("blacksmith.cli.load_custom_config")
@patch("blacksmith.cli.fetch_set_url")
def test_apply_url_dry_run_succeeds(
    mock_fetch, mock_load, mock_install, mock_cleanup, tmp_path
):
    fetched = _fetched(tmp_path)
    mock_fetch.return_value = fetched
    mock_load.return_value = {"name": "remote", "packages": []}
    mock_install.return_value = _ok_result()

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["apply", "--url", "https://example.com/a.yaml", "--dry-run", "--yes"],
    )

    assert result.exit_code == 0, result.output
    mock_fetch.assert_called_once()
    mock_load.assert_called_once_with(str(fetched.path))
    mock_install.assert_called_once()
    assert mock_install.call_args.kwargs["config_source"].startswith("https://")
    mock_cleanup.assert_called_once_with(fetched)


def test_install_url_http_json_invalid_url():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--json",
            "install",
            "--url",
            "http://example.com/a.yaml",
            "--yes",
        ],
    )

    assert result.exit_code == 1
    body = json.loads(result.stdout.strip())
    assert body["ok"] is False
    assert body["error"]["code"] == "invalid_url"
    assert "HTTPS" in body["error"]["message"]


def test_install_url_blocked_host_json_invalid_url():
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--json",
            "install",
            "--url",
            "https://127.0.0.1/a.yaml",
            "--yes",
        ],
    )

    assert result.exit_code == 1
    body = json.loads(result.stdout.strip())
    assert body["error"]["code"] == "invalid_url"
