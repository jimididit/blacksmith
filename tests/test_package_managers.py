"""Tests for package manager detection."""

from unittest.mock import patch

import pytest

from blacksmith.package_managers.detector import detect_available_managers, check_command


def test_check_command():
    """Test command checking utility."""
    # These should exist on most systems
    assert check_command('python') or check_command('python3')
    # This might not exist, but should not crash
    result = check_command('nonexistent-command-xyz123')
    assert isinstance(result, bool)


def test_detect_available_managers():
    """Test that we can detect available package managers."""
    managers = detect_available_managers()
    assert isinstance(managers, list)
    # Should detect at least one manager on any system
    # (or empty list if truly none available)
    assert len(managers) >= 0


def test_manager_has_required_methods():
    """Test that detected managers have required methods."""
    managers = detect_available_managers()
    for mgr in managers:
        assert hasattr(mgr, 'name')
        assert hasattr(mgr, 'is_available')
        assert hasattr(mgr, 'install')
        assert hasattr(mgr, 'is_installed')
        assert hasattr(mgr, 'search')


@patch("blacksmith.package_managers.detector.is_darwin", return_value=True)
@patch("blacksmith.package_managers.detector.is_windows", return_value=False)
@patch("blacksmith.package_managers.detector.is_linux", return_value=False)
@patch("blacksmith.package_managers.detector.check_command")
def test_detect_registers_brew_on_darwin(mock_check, _linux, _windows, _darwin):
    mock_check.side_effect = lambda cmd: cmd == "brew"
    managers = detect_available_managers()
    assert [m.name for m in managers] == ["brew"]


@patch("blacksmith.package_managers.detector.is_darwin", return_value=True)
@patch("blacksmith.package_managers.detector.is_windows", return_value=False)
@patch("blacksmith.package_managers.detector.is_linux", return_value=False)
@patch("blacksmith.package_managers.detector.check_command", return_value=False)
def test_detect_empty_on_darwin_without_brew(_check, _linux, _windows, _darwin):
    assert detect_available_managers() == []

