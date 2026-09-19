import hashlib
import json
from pathlib import Path
from unittest.mock import Mock, patch

from click.testing import CliRunner

from blacksmith.audit.log import audit_disabled, filter_auditable, record_audit
from blacksmith.audit.paths import default_audit_log_path, user_config_dir
from blacksmith.audit.read import load_events
from blacksmith.cli import (
    cli,
    maybe_record_install_audit,
    record_self_uninstall_audit,
)
from blacksmith.package_managers.results import (
    InstallRunResult,
    PackageOutcome,
    PackageStatus,
)


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


def test_record_audit_hashes_config_file(tmp_path, monkeypatch):
    log = tmp_path / "audit.jsonl"
    monkeypatch.setattr(
        "blacksmith.audit.log.default_audit_log_path", lambda: log
    )
    config = tmp_path / "set.yaml"
    config.write_text("name: t\npackages: []\n", encoding="utf-8")
    expected = hashlib.sha256(config.read_bytes()).hexdigest()

    record_audit(
        command="install",
        outcomes=[PackageOutcome("git", "git", "apt", "install", PackageStatus.OK)],
        exit_code=0,
        config_path=str(config),
    )

    run = json.loads(log.read_text(encoding="utf-8").splitlines()[0])
    assert run["config_path"] == str(config)
    assert run["config_hash"] == expected


def test_record_audit_config_hash_override(tmp_path, monkeypatch):
    log = tmp_path / "audit.jsonl"
    monkeypatch.setattr(
        "blacksmith.audit.log.default_audit_log_path", lambda: log
    )
    digest = "ab" * 32
    record_audit(
        command="install",
        outcomes=[PackageOutcome("git", "git", "apt", "install", PackageStatus.OK)],
        exit_code=0,
        config_path="https://example.com/set.yaml",
        config_hash=digest,
    )
    run = json.loads(log.read_text(encoding="utf-8").splitlines()[0])
    assert run["config_path"] == "https://example.com/set.yaml"
    assert run["config_hash"] == digest


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


def test_record_audit_fail_open_on_path_error(monkeypatch):
    def boom():
        raise RuntimeError("no home dir")

    monkeypatch.setattr("blacksmith.audit.log.default_audit_log_path", boom)
    warnings = []

    run_id = record_audit(
        command="install",
        outcomes=[PackageOutcome("a", "a", "apt", "install", PackageStatus.OK)],
        exit_code=0,
        warn=warnings.append,
    )

    assert run_id is None
    assert "no home dir" in warnings[0]


def test_record_audit_fail_open_on_serialization_error(tmp_path, monkeypatch):
    log = tmp_path / "audit.jsonl"
    monkeypatch.setattr("blacksmith.audit.log.default_audit_log_path", lambda: log)
    warnings = []

    run_id = record_audit(
        command="install",
        outcomes=[PackageOutcome("a", "a", "apt", "install", PackageStatus.OK)],
        exit_code="not-an-int",
        warn=warnings.append,
    )

    assert run_id is None
    assert warnings
    assert not log.exists()


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


def _ok_result():
    return InstallRunResult(
        ok=True,
        outcomes=[PackageOutcome("git", "git", "apt", "install", PackageStatus.OK)],
        changed=1,
    )


def test_maybe_record_install_audit_forwards_fields():
    result = _ok_result()
    with patch("blacksmith.cli.record_audit") as mocked:
        maybe_record_install_audit(
            command="install",
            result=result,
            exit_code=0,
            config={"name": "minimal"},
            config_source="sets/minimal.yaml",
            dry_run=False,
            no_audit=False,
        )

    kwargs = mocked.call_args.kwargs
    assert kwargs["command"] == "install"
    assert kwargs["outcomes"] == result.outcomes
    assert kwargs["exit_code"] == 0
    assert kwargs["set_name"] == "minimal"
    assert kwargs["config_path"] == "sets/minimal.yaml"
    assert kwargs["dry_run"] is False
    assert kwargs["no_audit"] is False
    assert kwargs.get("config_hash") is None
    assert callable(kwargs["warn"])


def test_maybe_record_install_audit_writes_lines(tmp_path, monkeypatch):
    log = tmp_path / "audit.jsonl"
    monkeypatch.setattr("blacksmith.audit.log.default_audit_log_path", lambda: log)

    maybe_record_install_audit(
        command="apply",
        result=_ok_result(),
        exit_code=2,
        config={"name": "minimal"},
        config_source=None,
        dry_run=False,
        no_audit=False,
    )

    lines = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["command"] == "apply"
    assert json.loads(lines[0])["exit"] == 2
    assert json.loads(lines[1])["name"] == "git"


def test_maybe_record_install_audit_no_audit_writes_nothing(tmp_path, monkeypatch):
    log = tmp_path / "audit.jsonl"
    monkeypatch.setattr("blacksmith.audit.log.default_audit_log_path", lambda: log)

    maybe_record_install_audit(
        command="install",
        result=_ok_result(),
        exit_code=0,
        config={"name": "minimal"},
        config_source=None,
        dry_run=False,
        no_audit=True,
    )

    assert not log.exists()


def test_maybe_record_install_audit_handles_missing_config():
    with patch("blacksmith.cli.record_audit") as mocked:
        maybe_record_install_audit(
            command="install",
            result=_ok_result(),
            exit_code=0,
            config=None,
            config_source=None,
            dry_run=False,
            no_audit=False,
        )

    assert mocked.call_args.kwargs["set_name"] is None


def test_install_command_records_audit():
    result = _ok_result()
    runner = CliRunner()
    with patch("blacksmith.cli.install_packages", return_value=result), patch(
        "blacksmith.cli.load_set", return_value={"name": "minimal", "packages": []}
    ), patch("blacksmith.cli.record_audit", return_value="abc") as mocked:
        invoked = runner.invoke(cli, ["install", "minimal", "--yes"])

    assert invoked.exit_code == 0
    kwargs = mocked.call_args.kwargs
    assert kwargs["command"] == "install"
    assert kwargs["exit_code"] == 0
    assert kwargs["set_name"] == "minimal"
    assert kwargs["no_audit"] is False
    assert kwargs["dry_run"] is False


def test_install_no_audit_flag_forwarded():
    runner = CliRunner()
    with patch("blacksmith.cli.install_packages", return_value=_ok_result()), patch(
        "blacksmith.cli.load_set", return_value={"name": "minimal", "packages": []}
    ), patch("blacksmith.cli.record_audit") as mocked:
        runner.invoke(cli, ["install", "minimal", "--yes", "--no-audit"])

    assert mocked.call_args.kwargs["no_audit"] is True


def test_install_dry_run_forwarded():
    runner = CliRunner()
    with patch("blacksmith.cli.install_packages", return_value=_ok_result()), patch(
        "blacksmith.cli.load_set", return_value={"name": "minimal", "packages": []}
    ), patch("blacksmith.cli.record_audit") as mocked:
        runner.invoke(cli, ["install", "minimal", "--yes", "--dry-run"])

    assert mocked.call_args.kwargs["dry_run"] is True


def test_apply_command_records_audit_with_apply_exit_code():
    runner = CliRunner()
    with patch("blacksmith.cli.install_packages", return_value=_ok_result()), patch(
        "blacksmith.cli.load_set", return_value={"name": "minimal", "packages": []}
    ), patch("blacksmith.cli.record_audit") as mocked:
        invoked = runner.invoke(cli, ["apply", "minimal", "--yes"])

    assert invoked.exit_code == 2
    kwargs = mocked.call_args.kwargs
    assert kwargs["command"] == "apply"
    assert kwargs["exit_code"] == 2
    assert kwargs["set_name"] == "minimal"


def test_apply_no_audit_flag_forwarded():
    runner = CliRunner()
    with patch("blacksmith.cli.install_packages", return_value=_ok_result()), patch(
        "blacksmith.cli.load_set", return_value={"name": "minimal", "packages": []}
    ), patch("blacksmith.cli.record_audit") as mocked:
        runner.invoke(cli, ["apply", "minimal", "--yes", "--no-audit"])

    assert mocked.call_args.kwargs["no_audit"] is True


def test_install_survives_unexpected_audit_error():
    runner = CliRunner()
    with patch("blacksmith.cli.install_packages", return_value=_ok_result()), patch(
        "blacksmith.cli.load_set", return_value={"name": "minimal", "packages": []}
    ), patch("blacksmith.cli.record_audit", side_effect=RuntimeError("no home dir")):
        invoked = runner.invoke(cli, ["install", "minimal", "--yes"])

    assert invoked.exit_code == 0
    assert "Audit log write failed" in invoked.output


def test_record_self_uninstall_audit_writes_lines(tmp_path, monkeypatch):
    log = tmp_path / "audit.jsonl"
    monkeypatch.setattr("blacksmith.audit.log.default_audit_log_path", lambda: log)

    record_self_uninstall_audit(
        manager="pipx",
        status=PackageStatus.OK,
        exit_code=0,
        no_audit=False,
    )

    lines = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    run = json.loads(lines[0])
    pkg = json.loads(lines[1])
    assert run["command"] == "uninstall"
    assert run["exit"] == 0
    assert pkg["name"] == "jdi-blacksmith"
    assert pkg["manager"] == "pipx"
    assert pkg["action"] == "uninstall"
    assert pkg["status"] == "ok"


def test_record_self_uninstall_audit_uses_resolved_package(tmp_path, monkeypatch):
    log = tmp_path / "audit.jsonl"
    monkeypatch.setattr("blacksmith.audit.log.default_audit_log_path", lambda: log)

    record_self_uninstall_audit(
        manager="pipx",
        status=PackageStatus.FAILED,
        exit_code=1,
        no_audit=False,
        package="blacksmith",
    )

    pkg = json.loads(log.read_text(encoding="utf-8").strip().splitlines()[1])
    assert pkg["name"] == "blacksmith"
    assert pkg["id"] == "blacksmith"
    assert pkg["status"] == "failed"


def test_uninstall_survives_unexpected_audit_error():
    with patch(
        "blacksmith.cli.record_audit", side_effect=RuntimeError("no home dir")
    ), patch("blacksmith.cli.print_warning") as warned:
        record_self_uninstall_audit(
            manager="pipx",
            status=PackageStatus.OK,
            exit_code=0,
            no_audit=False,
        )

    assert "Audit log write failed" in warned.call_args.args[0]


def test_install_audit_failure_does_not_change_exit_code():
    runner = CliRunner()
    failed = InstallRunResult(
        ok=False,
        outcomes=[PackageOutcome("git", "git", "apt", "install", PackageStatus.FAILED)],
        failed=1,
    )
    with patch("blacksmith.cli.install_packages", return_value=failed), patch(
        "blacksmith.cli.load_set", return_value={"name": "minimal", "packages": []}
    ), patch("blacksmith.cli.record_audit", return_value=None) as mocked:
        invoked = runner.invoke(cli, ["install", "minimal", "--yes"])

    assert invoked.exit_code == 1
    assert mocked.call_args.kwargs["exit_code"] == 1


@patch("blacksmith.cli.record_audit")
@patch("blacksmith.cli.install_packages")
@patch("blacksmith.cli.show_installation_summary", return_value=True)
@patch("blacksmith.cli.load_set", return_value={"name": "minimal", "packages": []})
@patch("blacksmith.cli.show_sets_menu", return_value="minimal")
@patch("blacksmith.cli.detect_available_managers", return_value=[])
@patch("blacksmith.cli.show_welcome")
def test_interactive_menu_install_records_audit(
    _welcome, _managers, _menu, _load, _summary, mock_install, mocked
):
    mock_install.return_value = _ok_result()
    runner = CliRunner()

    with patch("blacksmith.cli.questionary.select") as select:
        select.return_value.ask.return_value = "exit"
        runner.invoke(cli, [])

    kwargs = mocked.call_args.kwargs
    assert kwargs["command"] == "install"
    assert kwargs["set_name"] == "minimal"
    assert kwargs["exit_code"] == 0


PIPX_CMDS = [["/usr/bin/pipx", "uninstall", "jdi-blacksmith"]]


@patch("blacksmith.cli.record_audit")
@patch("rich.prompt.Confirm.ask", return_value=True)
@patch("subprocess.run", return_value=Mock(returncode=0, stdout="", stderr=""))
@patch("shutil.which", return_value="/home/u/.local/bin/blacksmith")
@patch("blacksmith.utils.pipx.should_use_pipx_uninstall", return_value=True)
@patch("blacksmith.utils.pipx.pipx_package_name", return_value="jdi-blacksmith")
@patch("blacksmith.utils.pipx.pipx_uninstall_commands", return_value=PIPX_CMDS)
def test_uninstall_records_audit_on_pipx_success(
    _cmds, _pkg, _should, _which, _run, _confirm, mocked
):
    runner = CliRunner()

    invoked = runner.invoke(cli, ["uninstall", "--yes"])

    assert invoked.exit_code == 0, invoked.output
    kwargs = mocked.call_args.kwargs
    assert kwargs["command"] == "uninstall"
    outcome = kwargs["outcomes"][0]
    assert outcome.package_name == "jdi-blacksmith"
    assert outcome.manager == "pipx"
    assert outcome.action == "uninstall"
    assert outcome.status == PackageStatus.OK
    assert kwargs["exit_code"] == 0
    assert kwargs["no_audit"] is False


@patch("blacksmith.cli.record_audit")
@patch("rich.prompt.Confirm.ask", return_value=True)
@patch("blacksmith.utils.deferred_delete.schedule_pip_uninstall", return_value=False)
@patch("subprocess.run", return_value=Mock(returncode=1, stdout="", stderr="boom"))
@patch("shutil.which", return_value="/home/u/.local/bin/blacksmith")
@patch("blacksmith.utils.pipx.should_use_pipx_uninstall", return_value=True)
@patch("blacksmith.utils.pipx.pipx_package_name", return_value="jdi-blacksmith")
@patch("blacksmith.utils.pipx.pipx_uninstall_commands", return_value=PIPX_CMDS)
def test_uninstall_records_failed_when_pipx_uninstall_fails(
    _cmds, _pkg, _should, _which, _run, _schedule, _confirm, mocked
):
    runner = CliRunner()

    invoked = runner.invoke(cli, ["uninstall", "--yes"])

    assert invoked.exit_code == 1
    kwargs = mocked.call_args.kwargs
    outcome = kwargs["outcomes"][0]
    assert outcome.manager == "pipx"
    assert outcome.status == PackageStatus.FAILED
    assert kwargs["exit_code"] == 1


@patch("blacksmith.cli.record_audit")
@patch("rich.prompt.Confirm.ask", return_value=True)
@patch("subprocess.run", return_value=Mock(returncode=0, stdout="", stderr=""))
@patch("shutil.which", return_value="/home/u/.local/bin/blacksmith")
@patch("blacksmith.utils.pipx.should_use_pipx_uninstall", return_value=True)
@patch("blacksmith.utils.pipx.pipx_package_name", return_value="jdi-blacksmith")
@patch("blacksmith.utils.pipx.pipx_uninstall_commands", return_value=PIPX_CMDS)
def test_uninstall_no_audit_flag_forwarded(
    _cmds, _pkg, _should, _which, _run, _confirm, mocked
):
    runner = CliRunner()

    runner.invoke(cli, ["uninstall", "--yes", "--no-audit"])

    assert mocked.call_args.kwargs["no_audit"] is True


@patch("blacksmith.cli.record_audit")
@patch("rich.prompt.Confirm.ask", return_value=True)
@patch("blacksmith.utils.deferred_delete.schedule_pip_uninstall", return_value=True)
@patch("subprocess.run", return_value=Mock(returncode=1, stdout="", stderr="busy"))
@patch("shutil.which", return_value="/home/u/.local/bin/blacksmith")
@patch("blacksmith.utils.pipx.should_use_pipx_uninstall", return_value=True)
@patch("blacksmith.utils.pipx.pipx_package_name", return_value="jdi-blacksmith")
@patch("blacksmith.utils.pipx.pipx_uninstall_commands", return_value=PIPX_CMDS)
def test_uninstall_deferred_schedule_records_failed_audit(
    _cmds, _pkg, _should, _which, _run, _schedule, _confirm, mocked
):
    """In-process uninstall failed, so the attempt is recorded as failed."""
    runner = CliRunner()

    invoked = runner.invoke(cli, ["uninstall", "--yes"])

    assert invoked.exit_code == 0, invoked.output
    kwargs = mocked.call_args.kwargs
    assert kwargs["command"] == "uninstall"
    outcome = kwargs["outcomes"][0]
    assert outcome.manager == "pipx"
    assert outcome.action == "uninstall"
    assert outcome.status == PackageStatus.FAILED
    assert kwargs["exit_code"] == 0


@patch("blacksmith.cli.record_audit")
@patch("rich.prompt.Confirm.ask", return_value=True)
@patch("blacksmith.utils.deferred_delete.schedule_pip_uninstall", return_value=True)
@patch("subprocess.run", return_value=Mock(returncode=1, stdout="", stderr="locked"))
@patch("shutil.which", return_value="/usr/bin/blacksmith")
@patch("blacksmith.utils.pipx.should_use_pipx_uninstall", return_value=False)
def test_uninstall_pip_deferred_schedule_records_failed_audit(
    _should, _which, _run, _schedule, _confirm, mocked
):
    """Deferred pip retry still records the failed in-process attempt."""
    runner = CliRunner()

    invoked = runner.invoke(cli, ["uninstall", "--yes"])

    assert invoked.exit_code == 0, invoked.output
    kwargs = mocked.call_args.kwargs
    outcome = kwargs["outcomes"][0]
    assert outcome.manager == "pip"
    assert outcome.action == "uninstall"
    assert outcome.status == PackageStatus.FAILED
    assert kwargs["exit_code"] == 0


def test_uninstall_cancel_does_not_record_audit():
    runner = CliRunner()
    with patch("blacksmith.utils.tty.stdin_is_tty", return_value=True), patch(
        "rich.prompt.Confirm.ask", return_value=False
    ), patch("blacksmith.cli.record_audit") as mocked:
        invoked = runner.invoke(cli, ["uninstall"])

    assert invoked.exit_code == 0
    assert "cancelled" in invoked.output.lower()
    mocked.assert_not_called()


def test_uninstall_records_audit_on_pip_success():
    runner = CliRunner()
    with patch("blacksmith.utils.pipx.should_use_pipx_uninstall", return_value=False), patch(
        "shutil.which", return_value="/usr/bin/blacksmith"
    ), patch(
        "subprocess.run", return_value=Mock(returncode=0, stdout="", stderr="")
    ), patch(
        "blacksmith.utils.safe_paths.expected_venv_path", return_value=Path("/nope/venv")
    ), patch(
        "blacksmith.utils.deferred_delete.remove_venv_now"
    ), patch(
        "blacksmith.utils.deferred_delete.remove_file_now"
    ), patch(
        "blacksmith.cli.record_audit"
    ) as mocked:
        invoked = runner.invoke(cli, ["uninstall", "--yes"])

    assert invoked.exit_code == 0, invoked.output
    outcome = mocked.call_args.kwargs["outcomes"][0]
    assert outcome.manager == "pip"
    assert outcome.action == "uninstall"
    assert outcome.status == PackageStatus.OK


@patch("blacksmith.cli.record_audit")
@patch("rich.prompt.Confirm.ask", return_value=True)
@patch("blacksmith.utils.deferred_delete.schedule_pip_uninstall", return_value=False)
@patch("subprocess.run", return_value=Mock(returncode=1, stdout="", stderr="denied"))
@patch("shutil.which", return_value="/usr/bin/blacksmith")
@patch("blacksmith.utils.pipx.should_use_pipx_uninstall", return_value=False)
def test_uninstall_records_failed_when_pip_uninstall_fails(
    _should, _which, _run, _schedule, _confirm, mocked
):
    runner = CliRunner()

    invoked = runner.invoke(cli, ["uninstall", "--yes"])

    assert "Could not automatically uninstall" in invoked.output
    outcome = mocked.call_args.kwargs["outcomes"][0]
    assert outcome.manager == "pip"
    assert outcome.status == PackageStatus.FAILED
