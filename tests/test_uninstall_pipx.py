"""Tests for uninstall preferring pipx when detected."""

from unittest.mock import Mock, patch

from click.testing import CliRunner

from blacksmith.cli import cli


@patch("rich.prompt.Confirm.ask", return_value=True)
@patch("subprocess.run")
@patch("shutil.which")
@patch("blacksmith.utils.pipx.should_use_pipx_uninstall", return_value=True)
@patch("blacksmith.utils.pipx.pipx_package_name", return_value="jdi-blacksmith")
@patch(
    "blacksmith.utils.pipx.pipx_uninstall_commands",
    return_value=[["/usr/bin/pipx", "uninstall", "jdi-blacksmith"]],
)
def test_uninstall_uses_pipx_when_detected(
    _cmds, _pkg, _should, mock_which, mock_run, _confirm
):
    mock_which.side_effect = lambda name: (
        "/home/u/.local/bin/blacksmith" if name == "blacksmith" else None
    )
    mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

    runner = CliRunner()
    result = runner.invoke(cli, ["uninstall", "--yes"])
    assert result.exit_code == 0, result.output
    assert mock_run.call_count == 1
    assert mock_run.call_args.args[0] == ["/usr/bin/pipx", "uninstall", "jdi-blacksmith"]
    assert "Successfully uninstalled" in result.output


@patch("rich.prompt.Confirm.ask", return_value=True)
@patch("subprocess.run")
@patch("shutil.which")
@patch("blacksmith.utils.pipx.should_use_pipx_uninstall", return_value=False)
def test_uninstall_skips_pipx_when_not_detected(_should, mock_which, mock_run, _confirm):
    mock_which.side_effect = lambda name: (
        "/usr/bin/blacksmith" if name == "blacksmith" else None
    )
    mock_run.return_value = Mock(returncode=1, stdout="", stderr="not installed")

    runner = CliRunner()
    runner.invoke(cli, ["uninstall", "--yes"])
    for call in mock_run.call_args_list:
        cmd = call.args[0]
        assert "pipx" not in str(cmd[0])
        assert "-m" not in cmd or "pipx" not in cmd


@patch("blacksmith.utils.deferred_delete.schedule_pip_uninstall", return_value=True)
@patch("subprocess.run")
@patch("shutil.which")
@patch("blacksmith.utils.pipx.should_use_pipx_uninstall", return_value=True)
@patch("blacksmith.utils.pipx.pipx_package_name", return_value="jdi-blacksmith")
@patch(
    "blacksmith.utils.pipx.pipx_uninstall_commands",
    return_value=[["/usr/bin/pipx", "uninstall", "jdi-blacksmith"]],
)
def test_uninstall_pipx_does_not_fall_through_to_pip(
    _cmds, _pkg, _should, mock_which, mock_run, mock_schedule
):
    """pipx installs must not be 'fixed' with raw pip uninstall."""
    mock_which.return_value = "/home/u/.local/bin/blacksmith"
    mock_run.return_value = Mock(returncode=1, stdout="", stderr="busy")

    runner = CliRunner()
    result = runner.invoke(cli, ["uninstall", "--yes"])
    assert result.exit_code == 0, result.output
    mock_schedule.assert_called()
    for call in mock_run.call_args_list:
        assert call.args[0][0] == "/usr/bin/pipx" or "pipx" in call.args[0]
