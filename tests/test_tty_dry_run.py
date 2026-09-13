"""Tests for TTY guards and dry-run planning."""

from unittest.mock import Mock, patch

from blacksmith.utils.tty import require_tty_or_yes, stdin_is_tty
from blacksmith.cli import install_packages, show_installation_summary


def test_require_tty_or_yes_allows_yes_and_dry_run(monkeypatch):
    monkeypatch.setattr("blacksmith.utils.tty.stdin_is_tty", lambda: False)
    ok, err = require_tty_or_yes(True, dry_run=False)
    assert ok and err is None
    ok, err = require_tty_or_yes(False, dry_run=True)
    assert ok and err is None


def test_require_tty_or_yes_blocks_non_tty_without_yes(monkeypatch):
    monkeypatch.setattr("blacksmith.utils.tty.stdin_is_tty", lambda: False)
    ok, err = require_tty_or_yes(False, dry_run=False)
    assert not ok
    assert err is not None
    assert "--yes" in err


@patch("blacksmith.cli.detect_available_managers")
@patch("blacksmith.cli.detect_os", return_value="linux")
def test_install_packages_rejects_non_tty_without_yes(_os, mock_detect, monkeypatch):
    monkeypatch.setattr("blacksmith.utils.tty.stdin_is_tty", lambda: False)
    mgr = Mock()
    mgr.name = "apt"
    mock_detect.return_value = [mgr]
    result = install_packages(
        {"name": "t", "packages": []},
        show_summary=False,
        assume_yes=False,
        dry_run=False,
    )
    assert result.ok is False


@patch("blacksmith.cli.find_manager_for_package")
def test_dry_run_summary_includes_action_plan(mock_find, capsys):
    mgr = Mock()
    mgr.name = "apt"
    mgr.is_installed = Mock(return_value=False)
    mock_find.return_value = (mgr, "git")

    result = show_installation_summary(
        {
            "name": "Dev",
            "packages": [{"name": "Git", "managers": {"apt": "git"}}],
        },
        available_managers=[mgr],
        dry_run=True,
    )
    assert result == "dry_run"
    out = capsys.readouterr().out
    assert "install: Git via apt (git)" in out or "Dry-run plan" in out
    assert mgr.install.called is False
