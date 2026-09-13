"""Tests for uninstall preferring pipx when detected."""

from unittest.mock import Mock, patch

from click.testing import CliRunner

from blacksmith.cli import cli


@patch("rich.prompt.Confirm.ask", return_value=True)
@patch("subprocess.run")
@patch("shutil.which")
@patch("blacksmith.utils.pipx.should_use_pipx_uninstall", return_value=True)
@patch("blacksmith.utils.pipx.pipx_package_name", return_value="jdi-blacksmith")
def test_uninstall_uses_pipx_when_detected(
    _pkg, _should, mock_which, mock_run, _confirm
):
    def which_side(name):
        if name == "blacksmith":
            return "/home/u/.local/bin/blacksmith"
        if name == "pipx":
            return "/usr/bin/pipx"
        return None

    mock_which.side_effect = which_side
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
