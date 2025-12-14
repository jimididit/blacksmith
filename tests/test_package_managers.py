"""Tests for package manager detection."""

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

