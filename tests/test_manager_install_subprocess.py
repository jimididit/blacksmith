"""Mocked subprocess tests for package manager install paths (X5)."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
import subprocess

from blacksmith.package_managers.apt import AptManager
from blacksmith.package_managers.brew import BrewManager
from blacksmith.package_managers.chocolatey import ChocolateyManager
from blacksmith.package_managers.flatpak import FlatpakManager
from blacksmith.package_managers.pacman import PacmanManager
from blacksmith.package_managers.scoop import ScoopManager
from blacksmith.package_managers.snap import SnapManager
from blacksmith.package_managers.winget import WingetManager
from blacksmith.package_managers.yum import YumManager


def _ok(stdout: str = "", stderr: str = "") -> Mock:
    return Mock(returncode=0, stdout=stdout, stderr=stderr)


def _fail(stdout: str = "", stderr: str = "boom") -> Mock:
    return Mock(returncode=1, stdout=stdout, stderr=stderr)


def _assert_no_shell(mock_run: Mock) -> None:
    assert mock_run.called
    for call in mock_run.call_args_list:
        kwargs = call.kwargs
        # Default shell is False when omitted; explicit True is forbidden.
        assert kwargs.get("shell", False) is False


def test_install_empty_list_is_noop_without_subprocess():
    with patch("blacksmith.package_managers.apt.subprocess.run") as mock_run:
        assert AptManager().install([]) is True
        mock_run.assert_not_called()


@patch("blacksmith.package_managers.apt.subprocess.run")
def test_apt_install_argv_and_shell_false(mock_run):
    mock_run.side_effect = [_ok(), _ok()]
    assert AptManager().install(["git"]) is True
    _assert_no_shell(mock_run)
    assert mock_run.call_args_list[0].args[0] == ["sudo", "apt", "update"]
    assert mock_run.call_args_list[1].args[0] == [
        "sudo", "apt", "install", "-y", "git",
    ]


@patch("blacksmith.package_managers.apt.subprocess.run")
def test_apt_install_fails_on_nonzero(mock_run):
    mock_run.side_effect = [_ok(), _fail()]
    assert AptManager().install(["git"]) is False


@patch("blacksmith.package_managers.apt.subprocess.run")
def test_apt_install_timeout(mock_run):
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="apt", timeout=1)
    assert AptManager().install(["git"]) is False


@patch("blacksmith.package_managers.pacman.subprocess.run")
def test_pacman_install_argv_and_shell_false(mock_run):
    mock_run.return_value = _ok()
    assert PacmanManager().install(["git"]) is True
    _assert_no_shell(mock_run)
    assert mock_run.call_args.args[0] == [
        "sudo", "pacman", "-S", "--noconfirm", "git",
    ]


@patch("blacksmith.package_managers.pacman.subprocess.run")
def test_pacman_install_fails_on_nonzero(mock_run):
    mock_run.return_value = _fail()
    assert PacmanManager().install(["git"]) is False


@patch("blacksmith.package_managers.yum.YumManager._check_dnf", return_value=True)
@patch("blacksmith.package_managers.yum.YumManager._check_yum", return_value=False)
@patch("blacksmith.package_managers.yum.subprocess.run")
def test_yum_dnf_install_argv_and_shell_false(mock_run, _yum, _dnf):
    mock_run.return_value = _ok()
    mgr = YumManager()
    assert mgr.command == "dnf"
    assert mgr.install(["git"]) is True
    _assert_no_shell(mock_run)
    assert mock_run.call_args.args[0] == ["sudo", "dnf", "install", "-y", "git"]


@patch("blacksmith.package_managers.yum.YumManager._check_dnf", return_value=False)
@patch("blacksmith.package_managers.yum.YumManager._check_yum", return_value=True)
@patch("blacksmith.package_managers.yum.subprocess.run")
def test_yum_install_uses_yum_when_no_dnf(mock_run, _yum, _dnf):
    mock_run.return_value = _ok()
    mgr = YumManager()
    assert mgr.command == "yum"
    assert mgr.install(["git"]) is True
    assert mock_run.call_args.args[0][1] == "yum"


@patch("blacksmith.package_managers.yum.YumManager._check_dnf", return_value=True)
@patch("blacksmith.package_managers.yum.YumManager._check_yum", return_value=False)
@patch("blacksmith.package_managers.yum.subprocess.run")
def test_yum_install_timeout(mock_run, _yum, _dnf):
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="dnf", timeout=1)
    assert YumManager().install(["git"]) is False


@patch("blacksmith.package_managers.snap.subprocess.run")
def test_snap_install_argv_and_shell_false(mock_run):
    mock_run.return_value = _ok()
    assert SnapManager().install(["code"]) is True
    _assert_no_shell(mock_run)
    assert mock_run.call_args.args[0] == ["sudo", "snap", "install", "code"]


@patch("blacksmith.package_managers.snap.subprocess.run")
def test_snap_install_fails_on_nonzero(mock_run):
    mock_run.return_value = _fail()
    assert SnapManager().install(["code"]) is False


@patch("blacksmith.package_managers.flatpak.subprocess.run")
def test_flatpak_install_argv_and_shell_false(mock_run):
    mock_run.return_value = _ok()
    assert FlatpakManager().install(["org.gimp.GIMP"]) is True
    _assert_no_shell(mock_run)
    assert mock_run.call_args.args[0] == [
        "flatpak", "install", "-y", "flathub", "org.gimp.GIMP",
    ]


@patch("blacksmith.package_managers.flatpak.subprocess.run")
def test_flatpak_install_fails_on_nonzero(mock_run):
    mock_run.return_value = _fail()
    assert FlatpakManager().install(["org.gimp.GIMP"]) is False


@patch("blacksmith.package_managers.chocolatey.subprocess.run")
def test_chocolatey_install_argv_and_shell_false(mock_run):
    mock_run.return_value = _ok()
    assert ChocolateyManager().install(["git"]) is True
    _assert_no_shell(mock_run)
    assert mock_run.call_args.args[0] == ["choco", "install", "-y", "git"]


@patch("blacksmith.package_managers.chocolatey.subprocess.run")
def test_chocolatey_install_fails_on_nonzero(mock_run):
    mock_run.return_value = _fail()
    assert ChocolateyManager().install(["git"]) is False


@patch("blacksmith.package_managers.scoop.subprocess.run")
def test_scoop_install_argv_and_shell_false(mock_run):
    mock_run.return_value = _ok()
    assert ScoopManager().install(["git"]) is True
    _assert_no_shell(mock_run)
    assert mock_run.call_args.args[0] == ["scoop", "install", "git"]


@patch("blacksmith.package_managers.scoop.subprocess.run")
def test_scoop_install_fails_on_nonzero(mock_run):
    mock_run.return_value = _fail()
    assert ScoopManager().install(["git"]) is False


@patch("blacksmith.package_managers.winget.subprocess.run")
def test_winget_install_argv_and_shell_false(mock_run):
    pkg = "Git.Git"
    mock_run.side_effect = [
        _ok(stdout=f"Name Id\nGit {pkg}\n"),  # search verify
        _ok(),  # install
    ]
    assert WingetManager().install([pkg]) is True
    _assert_no_shell(mock_run)
    assert mock_run.call_args_list[0].args[0] == [
        "winget", "search", "--exact", "--id", pkg,
    ]
    assert mock_run.call_args_list[1].args[0] == [
        "winget",
        "install",
        "--accept-package-agreements",
        "--accept-source-agreements",
        pkg,
    ]


@patch("blacksmith.package_managers.winget.subprocess.run")
def test_winget_install_fails_when_package_missing(mock_run):
    mock_run.return_value = _fail(stdout="No package found")
    assert WingetManager().install(["Missing.Pkg"]) is False


@patch("blacksmith.package_managers.winget.subprocess.run")
def test_winget_install_timeout(mock_run):
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="winget", timeout=1)
    assert WingetManager().install(["Git.Git"]) is False


@patch("blacksmith.package_managers.brew.subprocess.run")
def test_brew_install_argv_and_shell_false(mock_run):
    mock_run.return_value = _ok()
    assert BrewManager().install(["git"]) is True
    _assert_no_shell(mock_run)
    assert mock_run.call_args.args[0] == ["brew", "install", "git"]


@patch("blacksmith.package_managers.brew.subprocess.run")
def test_brew_install_fails_on_nonzero(mock_run):
    mock_run.return_value = _fail()
    assert BrewManager().install(["git"]) is False


@patch("blacksmith.package_managers.brew.subprocess.run")
def test_brew_install_timeout(mock_run):
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="brew", timeout=1)
    assert BrewManager().install(["git"]) is False


@patch("blacksmith.package_managers.brew.subprocess.run")
def test_brew_install_empty_noop(mock_run):
    assert BrewManager().install([]) is True
    mock_run.assert_not_called()


@pytest.mark.parametrize(
    "module_path,cls,expected_prefix",
    [
        ("blacksmith.package_managers.apt", AptManager, ["sudo", "apt"]),
        ("blacksmith.package_managers.pacman", PacmanManager, ["sudo", "pacman"]),
        ("blacksmith.package_managers.snap", SnapManager, ["sudo", "snap"]),
        ("blacksmith.package_managers.flatpak", FlatpakManager, ["flatpak"]),
        ("blacksmith.package_managers.chocolatey", ChocolateyManager, ["choco"]),
        ("blacksmith.package_managers.scoop", ScoopManager, ["scoop"]),
        ("blacksmith.package_managers.brew", BrewManager, ["brew"]),
    ],
)
def test_install_never_sets_shell_true(module_path, cls, expected_prefix):
    with patch(f"{module_path}.subprocess.run") as mock_run:
        mock_run.return_value = _ok(stdout="pkg exists")
        if cls is AptManager:
            mock_run.side_effect = [_ok(), _ok()]
        mgr = cls()
        pkg = "git" if cls is not FlatpakManager else "org.example.App"
        if cls is WingetManager:
            return
        assert mgr.install([pkg]) in (True, False)
        _assert_no_shell(mock_run)
        first_cmd = mock_run.call_args_list[0].args[0]
        assert first_cmd[: len(expected_prefix)] == expected_prefix or (
            cls is AptManager and first_cmd == ["sudo", "apt", "update"]
        )
