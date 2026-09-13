"""Tests for package install outcomes and fail-fast batch behavior."""

from unittest.mock import Mock, patch

import pytest

from blacksmith.package_managers.results import (
    PackageOutcome,
    PackageStatus,
    summarize_outcomes,
)
from blacksmith.cli import install_packages


def test_summarize_outcomes_counts():
    outcomes = [
        PackageOutcome("a", "a", "apt", "install", PackageStatus.OK),
        PackageOutcome("b", "b", "apt", "install", PackageStatus.FAILED),
        PackageOutcome("c", "c", "apt", "skip", PackageStatus.SKIPPED),
        PackageOutcome("d", "d", "apt", "update", PackageStatus.OK),
    ]
    assert summarize_outcomes(outcomes) == {"ok": 2, "failed": 1, "skipped": 1}


def _mock_mgr(name: str, install_side_effect=None):
    mgr = Mock()
    mgr.name = name
    mgr.is_installed = Mock(return_value=False)
    if install_side_effect is None:
        mgr.install = Mock(return_value=True)
    else:
        mgr.install = Mock(side_effect=install_side_effect)
    mgr.update_package = Mock(return_value=True)
    return mgr


def _config_three_pkgs():
    return {
        "name": "test",
        "packages": [
            {"name": "one", "managers": {"apt": "one"}},
            {"name": "two", "managers": {"apt": "two"}},
            {"name": "three", "managers": {"apt": "three"}},
        ],
    }


@patch("blacksmith.cli.create_progress")
@patch("blacksmith.cli.show_installation_summary", return_value=True)
@patch("blacksmith.cli.detect_available_managers")
@patch("blacksmith.cli.find_manager_for_package")
@patch("blacksmith.cli.detect_os", return_value="linux")
def test_best_effort_installs_all_packages(
    _os, mock_find, mock_detect, _summary, mock_progress
):
    mgr = _mock_mgr("apt", install_side_effect=[True, False, True])
    mock_detect.return_value = [mgr]
    mock_find.side_effect = [
        (mgr, "one"),
        (mgr, "two"),
        (mgr, "three"),
    ]
    progress = Mock()
    progress.__enter__ = Mock(return_value=progress)
    progress.__exit__ = Mock(return_value=False)
    progress.add_task = Mock(return_value=1)
    progress.update = Mock()
    mock_progress.return_value = progress

    result = install_packages(_config_three_pkgs(), show_summary=True, assume_yes=True)
    assert result.ok is False
    assert mgr.install.call_count == 3
    assert mgr.install.call_args_list[0].args[0] == ["one"]
    assert mgr.install.call_args_list[1].args[0] == ["two"]
    assert mgr.install.call_args_list[2].args[0] == ["three"]


@patch("blacksmith.cli.create_progress")
@patch("blacksmith.cli.show_installation_summary", return_value=True)
@patch("blacksmith.cli.detect_available_managers")
@patch("blacksmith.cli.find_manager_for_package")
@patch("blacksmith.cli.detect_os", return_value="linux")
def test_fail_fast_stops_after_first_failure(
    _os, mock_find, mock_detect, _summary, mock_progress
):
    mgr = _mock_mgr("apt", install_side_effect=[True, False, True])
    mock_detect.return_value = [mgr]
    mock_find.side_effect = [
        (mgr, "one"),
        (mgr, "two"),
        (mgr, "three"),
    ]
    progress = Mock()
    progress.__enter__ = Mock(return_value=progress)
    progress.__exit__ = Mock(return_value=False)
    progress.add_task = Mock(return_value=1)
    progress.update = Mock()
    mock_progress.return_value = progress

    result = install_packages(
        _config_three_pkgs(),
        show_summary=True,
        assume_yes=True,
        fail_fast=True,
    )
    assert result.ok is False
    assert mgr.install.call_count == 2
    called_ids = [c.args[0][0] for c in mgr.install.call_args_list]
    assert called_ids == ["one", "two"]
