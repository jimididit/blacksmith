from unittest.mock import Mock, patch
from blacksmith.package_managers.apt import AptManager
from blacksmith.package_managers.brew import BrewManager
from blacksmith.package_managers.chocolatey import ChocolateyManager
from blacksmith.package_managers.scoop import ScoopManager
from blacksmith.package_managers.snap import SnapManager
from blacksmith.package_managers.winget import WingetManager
from blacksmith.package_managers.yum import YumManager


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


@patch("blacksmith.package_managers.yum.subprocess.run")
def test_yum_install_pinned_argv(mock_run):
    mock_run.return_value = _ok()
    mgr = YumManager()
    mgr.command = "dnf"
    assert mgr.install(["nmap|7.94"]) is True
    assert mock_run.call_args.args[0] == [
        "sudo", "dnf", "install", "-y", "nmap-7.94",
    ]


@patch("blacksmith.package_managers.yum.subprocess.run")
def test_yum_get_installed_version(mock_run):
    mock_run.return_value = _ok(stdout="7.94-1.fc40")
    assert YumManager().get_installed_version("nmap") == "7.94-1.fc40"


@patch("blacksmith.package_managers.winget.subprocess.run")
def test_winget_install_pinned_argv(mock_run):
    mock_run.side_effect = [
        _ok(stdout="Git.Git"),  # search hit
        _ok(),
    ]
    assert WingetManager().install(["Git.Git|2.40.0"]) is True
    cmd = mock_run.call_args_list[1].args[0]
    assert cmd[0] == "winget" and "install" in cmd
    assert "--version" in cmd and "2.40.0" in cmd
    assert "Git.Git" in cmd


@patch("blacksmith.package_managers.winget.subprocess.run")
def test_winget_get_installed_version_parses_table(mock_run):
    mock_run.return_value = _ok(
        stdout=(
            "Name   Id       Version   Source\n"
            "----   --       -------   ------\n"
            "Git    Git.Git  2.40.0    winget\n"
        )
    )
    ver = WingetManager().get_installed_version("Git.Git")
    assert ver == "2.40.0"


@patch("blacksmith.package_managers.brew.subprocess.run")
def test_brew_install_pinned_argv(mock_run):
    mock_run.return_value = _ok()
    assert BrewManager().install(["go|1.21"]) is True
    assert mock_run.call_args.args[0] == ["brew", "install", "go@1.21"]


@patch("blacksmith.package_managers.brew.subprocess.run")
def test_brew_get_installed_version(mock_run):
    mock_run.return_value = _ok(stdout="go 1.21.5\n")
    assert BrewManager().get_installed_version("go") == "1.21.5"


@patch("blacksmith.package_managers.brew.subprocess.run")
def test_brew_get_installed_version_versioned_formula(mock_run):
    mock_run.return_value = _ok(stdout="go@1.21 1.21.5\n")
    assert BrewManager().get_installed_version("go@1.21") == "1.21.5"
