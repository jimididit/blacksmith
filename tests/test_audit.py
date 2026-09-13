import json
from pathlib import Path

from click.testing import CliRunner

from blacksmith.audit.log import audit_disabled, filter_auditable, record_audit
from blacksmith.audit.paths import default_audit_log_path, user_config_dir
from blacksmith.audit.read import load_events
from blacksmith.cli import cli
from blacksmith.package_managers.results import PackageOutcome, PackageStatus


def test_user_config_dir_linux(monkeypatch, tmp_path):
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    assert user_config_dir() == (tmp_path / "xdg" / "blacksmith").resolve()
    assert default_audit_log_path() == (
        tmp_path / "xdg" / "blacksmith" / "audit.jsonl"
    ).resolve()


def test_user_config_dir_windows(monkeypatch, tmp_path):
    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    assert user_config_dir() == (tmp_path / "appdata" / "blacksmith").resolve()


def test_audit_disabled_env(monkeypatch):
    monkeypatch.delenv("BLACKSMITH_NO_AUDIT", raising=False)
    assert audit_disabled(False) is False
    monkeypatch.setenv("BLACKSMITH_NO_AUDIT", "1")
    assert audit_disabled(False) is True
    monkeypatch.setenv("BLACKSMITH_NO_AUDIT", "True")
    assert audit_disabled(False) is True


def test_filter_auditable_skips_skipped():
    outcomes = [
        PackageOutcome("a", "a", "apt", "install", PackageStatus.OK),
        PackageOutcome("b", "b", "apt", "skip", PackageStatus.SKIPPED),
        PackageOutcome("c", "c", "apt", "install", PackageStatus.FAILED),
    ]
    got = filter_auditable(outcomes)
    assert [o.package_name for o in got] == ["a", "c"]


def test_record_audit_writes_run_and_packages(tmp_path, monkeypatch):
    log = tmp_path / "audit.jsonl"
    monkeypatch.setattr(
        "blacksmith.audit.log.default_audit_log_path", lambda: log
    )
    outcomes = [
        PackageOutcome("git", "git", "apt", "install", PackageStatus.OK),
        PackageOutcome("curl", "curl", "apt", "skip", PackageStatus.SKIPPED),
    ]
    run_id = record_audit(
        command="install",
        outcomes=outcomes,
        exit_code=0,
        set_name="minimal",
        config_path=None,
    )
    assert run_id
    lines = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    run = json.loads(lines[0])
    pkg = json.loads(lines[1])
    assert run["type"] == "run"
    assert run["command"] == "install"
    assert run["set"] == "minimal"
    assert run["run_id"] == run_id
    assert pkg["type"] == "package"
    assert pkg["name"] == "git"
    assert pkg["status"] == "ok"


def test_record_audit_noop_when_all_skipped(tmp_path, monkeypatch):
    log = tmp_path / "audit.jsonl"
    monkeypatch.setattr(
        "blacksmith.audit.log.default_audit_log_path", lambda: log
    )
    assert (
        record_audit(
            command="apply",
            outcomes=[
                PackageOutcome("a", "a", "apt", "skip", PackageStatus.SKIPPED)
            ],
            exit_code=0,
        )
        is None
    )
    assert not log.exists()


def test_record_audit_skips_dry_run(tmp_path, monkeypatch):
    log = tmp_path / "audit.jsonl"
    monkeypatch.setattr(
        "blacksmith.audit.log.default_audit_log_path", lambda: log
    )
    assert (
        record_audit(
            command="install",
            outcomes=[
                PackageOutcome("a", "a", "apt", "install", PackageStatus.OK)
            ],
            exit_code=0,
            dry_run=True,
        )
        is None
    )
    assert not log.exists()


def test_record_audit_fail_open(tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    warnings = []
    run_id = record_audit(
        command="install",
        outcomes=[
            PackageOutcome("a", "a", "apt", "install", PackageStatus.OK)
        ],
        exit_code=0,
        log_path=blocker / "audit.jsonl",
        warn=warnings.append,
    )
    assert run_id is None
    assert warnings


def test_load_events_last_n_and_corrupt(tmp_path):
    log = tmp_path / "audit.jsonl"
    rows = [
        {
            "type": "run",
            "ts": "2026-01-01T00:00:00Z",
            "run_id": "1",
            "command": "install",
            "exit": 0,
        },
        {
            "type": "package",
            "ts": "2026-01-01T00:00:00Z",
            "run_id": "1",
            "name": "git",
            "action": "install",
            "status": "ok",
        },
        "NOT_JSON",
        {
            "type": "run",
            "ts": "2026-01-02T00:00:00Z",
            "run_id": "2",
            "command": "apply",
            "exit": 2,
        },
    ]
    with log.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write((row if isinstance(row, str) else json.dumps(row)) + "\n")

    events, corrupt = load_events(path=log, last=2)

    assert corrupt == 1
    assert len(events) == 2
    assert events[0]["run_id"] == "1"
    assert events[0]["type"] == "package"
    assert events[1]["run_id"] == "2"


def test_cli_audit_empty(monkeypatch, tmp_path):
    log = tmp_path / "audit.jsonl"
    monkeypatch.setattr(
        "blacksmith.audit.read.default_audit_log_path", lambda: log
    )
    runner = CliRunner()

    result = runner.invoke(cli, ["audit"])

    assert result.exit_code == 0
    assert "No audit events" in result.output
