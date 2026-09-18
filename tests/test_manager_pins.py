from unittest.mock import Mock, patch
from blacksmith.package_managers.apt import AptManager
from blacksmith.package_managers.chocolatey import ChocolateyManager
from blacksmith.package_managers.scoop import ScoopManager
from blacksmith.package_managers.snap import SnapManager


def _ok(stdout="", stderr=""):
    return Mock(returncode=0, stdout=stdout, stderr=stderr)


def test_default_managers_do_not_support_pins():
    assert ScoopManager().supports_version_pins() is False
    assert SnapManager().supports_version_pins() is False
    assert ScoopManager().get_installed_version("git") is None


@patch("blacksmith.package_managers.chocolatey.subprocess.run")
def test_choco_install_pinned_argv(mock_run):
    mock_run.return_value = _ok()
    assert ChocolateyManager().install(["git|2.40.0"]) is True
    assert mock_run.call_args.args[0] == [
        "choco", "install", "-y", "git", "--version", "2.40.0",
    ]
    assert mock_run.call_args.kwargs.get("shell", False) is False


@patch("blacksmith.package_managers.chocolatey.subprocess.run")
def test_choco_get_installed_version_limit_output(mock_run):
    mock_run.return_value = _ok(stdout="git|2.40.0\n")
    assert ChocolateyManager().get_installed_version("git") == "2.40.0"
    assert ChocolateyManager().supports_version_pins() is True


@patch("blacksmith.package_managers.apt.subprocess.run")
def test_apt_install_pinned_argv(mock_run):
    mock_run.side_effect = [_ok(), _ok()]
    assert AptManager().install(["nmap|7.94"]) is True
    assert mock_run.call_args_list[1].args[0] == [
        "sudo", "apt", "install", "-y", "nmap=7.94",
    ]


@patch("blacksmith.package_managers.apt.subprocess.run")
def test_apt_get_installed_version(mock_run):
    mock_run.return_value = _ok(stdout="7.94-1")
    assert AptManager().get_installed_version("nmap") == "7.94-1"
