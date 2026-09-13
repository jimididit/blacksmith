import json

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
