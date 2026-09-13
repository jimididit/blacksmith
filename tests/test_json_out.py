import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from blacksmith.cli import cli
from blacksmith.json_out import (
    SCHEMA_VERSION,
    envelope_error,
    envelope_ok,
    outcome_to_dict,
    run_result_data,
)
from blacksmith.package_managers.results import InstallRunResult, PackageOutcome, PackageStatus


def test_envelope_ok_apply_exit_2():
    env = envelope_ok("apply", 2, {"dry_run": False}, apply_ok_exits=True)
    assert env["schema_version"] == SCHEMA_VERSION
    assert env["ok"] is True
    assert env["exit"] == 2
    assert "error" not in env
    assert env["data"]["dry_run"] is False


def test_envelope_error_omits_data():
    env = envelope_error("create", 2, "json_unsupported", "JSON not supported for create")
    assert env["ok"] is False
    assert env["error"]["code"] == "json_unsupported"
    assert "data" not in env


def test_run_result_data_serializes_outcomes():
    result = InstallRunResult(
        ok=True,
        changed=1,
        skipped=1,
        failed=0,
        outcomes=[
            PackageOutcome("git", "git", "apt", "install", PackageStatus.OK),
            PackageOutcome("curl", "curl", "apt", "skip", PackageStatus.SKIPPED),
        ],
    )
    data = run_result_data(
        dry_run=True, set_name="minimal", config_path=None, result=result
    )
    assert data["dry_run"] is True
    assert data["set"] == "minimal"
    assert data["summary"]["changed"] == 1
    assert len(data["outcomes"]) == 2
    assert data["outcomes"][1]["status"] == "skipped"


def _parse_cli_json(result):
    return json.loads(result.output.strip().splitlines()[-1])


@pytest.mark.parametrize(
    ("command", "args"),
    [
        ("create", []),
        ("export", []),
        ("uninstall", []),
        ("audit", []),
    ],
)
def test_json_unsupported_commands_fail_closed(command, args):
    result = CliRunner().invoke(cli, ["--json", command, *args])

    assert result.exit_code == 2
    body = _parse_cli_json(result)
    assert body["ok"] is False
    assert body["exit"] == 2
    assert body["error"]["code"] == "json_unsupported"
    assert body["command"] == command


def test_json_validate_is_unsupported(tmp_path):
    config = tmp_path / "set.yaml"
    config.write_text("name: example\npackages: []\n", encoding="utf-8")

    result = CliRunner().invoke(cli, ["--json", "validate", str(config)])

    assert result.exit_code == 2
    body = _parse_cli_json(result)
    assert body["error"]["code"] == "json_unsupported"
    assert body["command"] == "validate"


def test_json_bare_cli_no_interactive():
    result = CliRunner().invoke(cli, ["--json"])

    assert result.exit_code == 2
    body = _parse_cli_json(result)
    assert body["ok"] is False
    assert body["error"]["code"] == "json_unsupported"
    assert body["command"] == "interactive"


def test_json_list_includes_minimal():
    result = CliRunner().invoke(cli, ["--json", "list"])

    assert result.exit_code == 0
    body = _parse_cli_json(result)
    assert body["ok"] is True
    minimal = next(item for item in body["data"]["sets"] if item["name"] == "minimal")
    assert set(minimal) == {
        "name",
        "description",
        "package_count",
        "target_os",
        "managers_supported",
    }


def test_json_list_stdout_is_single_json_object():
    result = CliRunner().invoke(cli, ["--json", "list"])

    assert result.exit_code == 0
    body = json.loads(result.output.strip())
    assert body["command"] == "list"


def test_json_info_minimal_has_packages():
    result = CliRunner().invoke(cli, ["--json", "info", "minimal"])

    assert result.exit_code == 0
    body = _parse_cli_json(result)
    assert body["command"] == "info"
    assert body["data"]["config_path"] is None
    assert isinstance(body["data"]["packages"], list)
    assert len(body["data"]["packages"]) >= 1
    assert set(body["data"]["packages"][0]) == {"name", "managers"}


def test_json_info_needs_args():
    result = CliRunner().invoke(cli, ["--json", "info"])

    assert result.exit_code == 2
    assert _parse_cli_json(result)["error"]["code"] == "needs_args"


def test_json_search_needs_query():
    result = CliRunner().invoke(cli, ["--json", "search"])

    assert result.exit_code == 2
    assert _parse_cli_json(result)["error"]["code"] == "needs_args"


def test_json_search_invalid_query():
    result = CliRunner().invoke(cli, ["--json", "search", ";rm -rf"])

    assert result.exit_code != 0
    assert _parse_cli_json(result)["error"]["code"] == "invalid_query"


def test_json_search_results_mocked():
    class FakeManager:
        name = "apt"

        def search(self, query, limit=10):
            assert query == "git"
            assert limit == 5
            return [{"name": "git", "id": "git", "description": "vcs"}]

    with patch(
        "blacksmith.cli.detect_available_managers", return_value=[FakeManager()]
    ):
        result = CliRunner().invoke(cli, ["--json", "search", "git", "--limit", "5"])

    assert result.exit_code == 0
    body = json.loads(result.output.strip())
    assert body["data"] == {
        "query": "git",
        "limit": 5,
        "results": [
            {
                "manager": "apt",
                "packages": [{"name": "git", "id": "git", "description": "vcs"}],
            }
        ],
        "notes": [],
    }


def test_json_search_empty_results_are_success():
    class FakeManager:
        name = "apt"

        def search(self, query, limit=10):
            return []

    with patch(
        "blacksmith.cli.detect_available_managers", return_value=[FakeManager()]
    ):
        result = CliRunner().invoke(cli, ["--json", "search", "unknown"])

    assert result.exit_code == 0
    body = json.loads(result.output.strip())
    assert body["ok"] is True
    assert body["data"]["results"] == []


def test_json_search_no_managers():
    with patch("blacksmith.cli.detect_available_managers", return_value=[]):
        result = CliRunner().invoke(cli, ["--json", "search", "git"])

    assert result.exit_code == 1
    assert _parse_cli_json(result)["error"]["code"] == "no_managers"


MINIMAL_CONFIG = {"name": "minimal", "packages": [{"name": "git"}]}


def _skipped_result():
    return InstallRunResult(
        ok=True,
        changed=0,
        skipped=1,
        outcomes=[PackageOutcome("git", "git", "apt", "skip", PackageStatus.SKIPPED)],
    )


def _changed_result():
    return InstallRunResult(
        ok=True,
        changed=1,
        outcomes=[PackageOutcome("git", "git", "apt", "install", PackageStatus.OK)],
    )


@pytest.mark.parametrize("command", ["install", "apply"])
def test_json_mutate_needs_args(command):
    with patch("blacksmith.cli.install_packages") as mock_install:
        result = CliRunner().invoke(cli, ["--json", command])

    assert result.exit_code == 2
    body = _parse_cli_json(result)
    assert body["command"] == command
    assert body["error"]["code"] == "needs_args"
    assert "--file" in body["error"]["message"]
    mock_install.assert_not_called()


@pytest.mark.parametrize("command", ["install", "apply"])
def test_json_mutate_requires_yes(command):
    with patch("blacksmith.cli.install_packages") as mock_install:
        result = CliRunner().invoke(cli, ["--json", command, "minimal"])

    assert result.exit_code == 2
    body = _parse_cli_json(result)
    assert body["error"]["code"] == "needs_args"
    assert "--yes" in body["error"]["message"]
    mock_install.assert_not_called()


def test_json_install_dry_run_mocked():
    with patch(
        "blacksmith.cli.install_packages", return_value=_skipped_result()
    ) as mock_install, patch(
        "blacksmith.cli.load_set", return_value=MINIMAL_CONFIG
    ), patch(
        "blacksmith.cli.record_audit"
    ) as mock_audit:
        result = CliRunner().invoke(
            cli, ["--json", "install", "minimal", "--yes", "--dry-run"]
        )

    assert result.exit_code == 0
    body = _parse_cli_json(result)
    assert body["command"] == "install"
    assert body["ok"] is True
    assert body["data"]["dry_run"] is True
    assert body["data"]["set"] == "minimal"
    assert body["data"]["config_path"] is None
    assert body["data"]["summary"]["skipped"] == 1
    assert body["data"]["outcomes"][0]["status"] == "skipped"
    assert mock_install.call_args.kwargs["show_summary"] is False
    mock_audit.assert_called_once()


def test_json_install_stdout_is_single_json_object():
    def noisy_install(*args, **kwargs):
        from blacksmith.cli import print_info, print_success

        print_info("detected package managers")
        print_success("Installed git")
        return _changed_result()

    with patch("blacksmith.cli.install_packages", side_effect=noisy_install), patch(
        "blacksmith.cli.load_set", return_value=MINIMAL_CONFIG
    ), patch("blacksmith.cli.record_audit"):
        result = CliRunner().invoke(cli, ["--json", "install", "minimal", "--yes"])

    assert result.exit_code == 0
    body = json.loads(result.output.strip())
    assert body["command"] == "install"


def test_human_mode_still_prints_after_json_run():
    runner = CliRunner()
    json_result = runner.invoke(cli, ["--json", "list"])
    human_result = runner.invoke(cli, ["list"])

    assert json_result.exit_code == 0
    assert human_result.exit_code == 0
    assert "minimal" in human_result.output


def test_json_install_set_not_found():
    result = CliRunner().invoke(cli, ["--json", "install", "does-not-exist", "--yes"])

    assert result.exit_code == 1
    # Loader warnings must not pollute the payload stream.
    body = json.loads(result.stdout.strip())
    assert body["ok"] is False
    assert body["error"]["code"] == "not_found"


def test_logger_output_goes_to_stderr():
    from blacksmith.utils.logger import setup_logger

    logger = setup_logger("blacksmith.tests.stderr")

    assert logger.handlers[0].console.stderr is True


def test_json_install_invalid_config(tmp_path):
    config = tmp_path / "set.yaml"
    config.write_text("name: broken\n", encoding="utf-8")

    with patch("blacksmith.cli.load_custom_config", return_value=None):
        result = CliRunner().invoke(
            cli, ["--json", "install", "--file", str(config), "--yes"]
        )

    assert result.exit_code == 1
    assert _parse_cli_json(result)["error"]["code"] == "invalid_config"


def test_json_install_failed_run():
    failed = InstallRunResult(
        ok=False,
        failed=1,
        outcomes=[
            PackageOutcome("git", "git", "apt", "install", PackageStatus.FAILED),
        ],
    )
    with patch("blacksmith.cli.install_packages", return_value=failed), patch(
        "blacksmith.cli.load_set", return_value=MINIMAL_CONFIG
    ), patch("blacksmith.cli.record_audit"):
        result = CliRunner().invoke(cli, ["--json", "install", "minimal", "--yes"])

    assert result.exit_code == 1
    body = _parse_cli_json(result)
    assert body["ok"] is False
    assert "data" not in body
    assert body["error"]["code"] == "install_failed"
    assert "git" in body["error"]["message"]


def test_json_install_cancelled_run():
    cancelled = InstallRunResult(ok=False, cancelled=True)
    with patch("blacksmith.cli.install_packages", return_value=cancelled), patch(
        "blacksmith.cli.load_set", return_value=MINIMAL_CONFIG
    ), patch("blacksmith.cli.record_audit"):
        result = CliRunner().invoke(cli, ["--json", "install", "minimal", "--yes"])

    assert result.exit_code == 1
    assert _parse_cli_json(result)["error"]["code"] == "cancelled"


def test_json_apply_exit_2_ok_true():
    with patch(
        "blacksmith.cli.install_packages", return_value=_changed_result()
    ) as mock_install, patch(
        "blacksmith.cli.load_set", return_value=MINIMAL_CONFIG
    ), patch(
        "blacksmith.cli.record_audit"
    ):
        result = CliRunner().invoke(cli, ["--json", "apply", "minimal", "--yes"])

    assert result.exit_code == 2
    body = _parse_cli_json(result)
    assert body["command"] == "apply"
    assert body["ok"] is True
    assert body["exit"] == 2
    assert body["data"]["summary"]["changed"] == 1
    assert mock_install.call_args.kwargs["show_summary"] is False


def test_json_apply_already_compliant_exit_0():
    with patch(
        "blacksmith.cli.install_packages", return_value=_skipped_result()
    ), patch("blacksmith.cli.load_set", return_value=MINIMAL_CONFIG), patch(
        "blacksmith.cli.record_audit"
    ):
        result = CliRunner().invoke(cli, ["--json", "apply", "minimal", "--yes"])

    assert result.exit_code == 0
    body = _parse_cli_json(result)
    assert body["ok"] is True
    assert body["data"]["summary"]["skipped"] == 1


def test_json_apply_failed_run():
    failed = InstallRunResult(
        ok=False,
        failed=1,
        outcomes=[
            PackageOutcome("git", "git", "apt", "install", PackageStatus.FAILED),
        ],
    )
    with patch("blacksmith.cli.install_packages", return_value=failed), patch(
        "blacksmith.cli.load_set", return_value=MINIMAL_CONFIG
    ), patch("blacksmith.cli.record_audit"):
        result = CliRunner().invoke(cli, ["--json", "apply", "minimal", "--yes"])

    assert result.exit_code == 1
    body = _parse_cli_json(result)
    assert body["ok"] is False
    assert body["error"]["code"] == "install_failed"


@pytest.mark.parametrize("command", ["install", "apply"])
def test_json_mutate_signature_failure(command, tmp_path):
    config = tmp_path / "set.yaml"
    config.write_text("name: t\npackages: []\n", encoding="utf-8")

    with patch(
        "blacksmith.trust.verify.verify_set_signature",
        return_value=SimpleNamespace(ok=False, message="bad sig"),
    ), patch("blacksmith.cli.install_packages") as mock_install, patch(
        "blacksmith.cli.load_custom_config"
    ) as mock_load:
        result = CliRunner().invoke(
            cli,
            [
                "--json",
                command,
                "--file",
                str(config),
                "--require-signature",
                "--yes",
            ],
        )

    assert result.exit_code == 1
    body = _parse_cli_json(result)
    assert body["command"] == command
    assert body["error"]["code"] == "signature_failed"
    assert body["error"]["message"] == "bad sig"
    mock_load.assert_not_called()
    mock_install.assert_not_called()


@pytest.mark.parametrize("command", ["install", "apply"])
def test_json_mutate_require_signature_without_file(command):
    result = CliRunner().invoke(
        cli, ["--json", command, "minimal", "--require-signature", "--yes"]
    )

    assert result.exit_code == 2
    body = _parse_cli_json(result)
    assert body["error"]["code"] == "needs_args"
    assert "--file" in body["error"]["message"]


def test_json_install_file_reports_config_path(tmp_path):
    config = tmp_path / "set.yaml"
    config.write_text("name: custom\npackages: []\n", encoding="utf-8")

    with patch(
        "blacksmith.cli.install_packages", return_value=_changed_result()
    ), patch("blacksmith.cli.record_audit"):
        result = CliRunner().invoke(
            cli, ["--json", "install", "--file", str(config), "--yes"]
        )

    assert result.exit_code == 0
    body = _parse_cli_json(result)
    assert body["data"]["config_path"] == str(config)
    assert body["data"]["set"] == "custom"
