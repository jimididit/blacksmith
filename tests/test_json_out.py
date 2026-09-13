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
