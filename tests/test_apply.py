"""Tests for idempotent apply mode (L2)."""

from unittest.mock import Mock, patch

from blacksmith.cli import install_packages
from blacksmith.package_managers.results import InstallRunResult, PackageStatus


def _mock_mgr(name: str = "apt"):
    mgr = Mock()
    mgr.name = name
    mgr.is_installed = Mock(return_value=False)
    mgr.install = Mock(return_value=True)
    mgr.update_package = Mock(return_value=True)
    return mgr


def _progress_mock(mock_progress):
    progress = Mock()
    progress.__enter__ = Mock(return_value=progress)
    progress.__exit__ = Mock(return_value=False)
    progress.add_task = Mock(return_value=1)
    progress.update = Mock()
    mock_progress.return_value = progress


def test_exit_code_apply_semantics():
    assert InstallRunResult(ok=True, changed=0).exit_code_apply() == 0
    assert InstallRunResult(ok=True, changed=2).exit_code_apply() == 2
    assert InstallRunResult(ok=False, failed=1).exit_code_apply() == 1
    assert InstallRunResult(ok=False, cancelled=True).exit_code_apply() == 1


@patch("blacksmith.cli.create_progress")
@patch("blacksmith.cli.show_installation_summary", return_value=True)
@patch("blacksmith.cli.detect_available_managers")
@patch("blacksmith.cli.find_manager_for_package")
@patch("blacksmith.cli.detect_os", return_value="linux")
def test_apply_skips_already_installed(
    _os, mock_find, mock_detect, _summary, mock_progress
):
    mgr = _mock_mgr()
    mgr.is_installed = Mock(return_value=True)
    mock_detect.return_value = [mgr]
    mock_find.return_value = (mgr, "git")
    _progress_mock(mock_progress)

    result = install_packages(
        {"name": "t", "packages": [{"name": "Git", "managers": {"apt": "git"}}]},
        show_summary=True,
        assume_yes=True,
        apply_mode=True,
    )
    assert result.ok is True
    assert result.changed == 0
    assert result.skipped == 1
    assert result.exit_code_apply() == 0
    mgr.install.assert_not_called()


@patch("blacksmith.cli.create_progress")
@patch("blacksmith.cli.show_installation_summary", return_value=True)
@patch("blacksmith.cli.detect_available_managers")
@patch("blacksmith.cli.find_manager_for_package")
@patch("blacksmith.cli.detect_os", return_value="linux")
def test_apply_installs_and_verifies(
    _os, mock_find, mock_detect, _summary, mock_progress
):
    mgr = _mock_mgr()
    # First check: missing; after install: present
    mgr.is_installed = Mock(side_effect=[False, True])
    mock_detect.return_value = [mgr]
    mock_find.return_value = (mgr, "git")
    _progress_mock(mock_progress)

    result = install_packages(
        {"name": "t", "packages": [{"name": "Git", "managers": {"apt": "git"}}]},
        show_summary=True,
        assume_yes=True,
        apply_mode=True,
    )
    assert result.ok is True
    assert result.changed == 1
    assert result.exit_code_apply() == 2
    mgr.install.assert_called_once_with(["git"])
    assert result.outcomes[0].status == PackageStatus.OK


@patch("blacksmith.cli.create_progress")
@patch("blacksmith.cli.show_installation_summary", return_value=True)
@patch("blacksmith.cli.detect_available_managers")
@patch("blacksmith.cli.find_manager_for_package")
@patch("blacksmith.cli.detect_os", return_value="linux")
def test_apply_verify_failure(
    _os, mock_find, mock_detect, _summary, mock_progress
):
    mgr = _mock_mgr()
    # Missing before and after install
    mgr.is_installed = Mock(return_value=False)
    mgr.install = Mock(return_value=True)
    mock_detect.return_value = [mgr]
    mock_find.return_value = (mgr, "git")
    _progress_mock(mock_progress)

    result = install_packages(
        {"name": "t", "packages": [{"name": "Git", "managers": {"apt": "git"}}]},
        show_summary=True,
        assume_yes=True,
        apply_mode=True,
    )
    assert result.ok is False
    assert result.failed == 1
    assert result.exit_code_apply() == 1
    assert result.outcomes[0].message == "post-install verify failed"


@patch("blacksmith.cli.create_progress")
@patch("blacksmith.cli.show_installation_summary", return_value=True)
@patch("blacksmith.cli.detect_available_managers")
@patch("blacksmith.cli.find_manager_for_package")
@patch("blacksmith.cli.detect_os", return_value="linux")
def test_apply_missing_manager_is_failure(
    _os, mock_find, mock_detect, _summary, mock_progress
):
    mgr = _mock_mgr()
    mock_detect.return_value = [mgr]
    mock_find.return_value = None
    _progress_mock(mock_progress)

    result = install_packages(
        {"name": "t", "packages": [{"name": "Git", "managers": {"apt": "git"}}]},
        show_summary=True,
        assume_yes=True,
        apply_mode=True,
    )
    assert result.ok is False
    assert result.failed == 1
    assert result.exit_code_apply() == 1
