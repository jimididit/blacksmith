"""Tests for installation logic with preferences."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from blacksmith.config.preferences import PreferredManagerOrder
from blacksmith.package_managers.detector import find_manager_for_package


@pytest.fixture
def mock_managers():
    """Create mock package managers."""
    winget = Mock()
    winget.name = "winget"
    winget.is_installed = Mock(return_value=False)
    
    choco = Mock()
    choco.name = "chocolatey"
    choco.is_installed = Mock(return_value=False)
    
    apt = Mock()
    apt.name = "apt"
    apt.is_installed = Mock(return_value=False)
    
    return [winget, choco, apt]


def test_find_manager_with_preferences(mock_managers):
    """Test finding manager using preferences."""
    package_config = {
        "name": "git",
        "managers": {
            "winget": "Git.Git",
            "chocolatey": "git",
            "apt": "git"
        }
    }
    
    # Create preferences (winget preferred)
    prefs = PreferredManagerOrder()
    
    result = find_manager_for_package(
        package_config,
        mock_managers,
        preferred_order=prefs,
        managers_supported=None
    )
    
    assert result is not None
    mgr, pkg_id = result
    assert mgr.name == "winget"
    assert pkg_id == "Git.Git"


def test_find_manager_fallback(mock_managers):
    """Test manager fallback when preferred not available."""
    package_config = {
        "name": "git",
        "managers": {
            "winget": "Git.Git",
            "chocolatey": "git"
        }
    }
    
    # Only chocolatey available
    available = [m for m in mock_managers if m.name == "chocolatey"]
    
    prefs = PreferredManagerOrder()
    result = find_manager_for_package(
        package_config,
        available,
        preferred_order=prefs,
        managers_supported=None
    )
    
    assert result is not None
    mgr, pkg_id = result
    assert mgr.name == "chocolatey"
    assert pkg_id == "git"


def test_find_manager_with_managers_supported_filter(mock_managers):
    """Test filtering by managers_supported."""
    package_config = {
        "name": "git",
        "managers": {
            "winget": "Git.Git",
            "chocolatey": "git",
            "apt": "git"
        }
    }
    
    prefs = PreferredManagerOrder()
    # Filter to only chocolatey
    result = find_manager_for_package(
        package_config,
        mock_managers,
        preferred_order=prefs,
        managers_supported=["chocolatey"]
    )
    
    assert result is not None
    mgr, pkg_id = result
    assert mgr.name == "chocolatey"
    assert pkg_id == "git"


def test_find_manager_no_match(mock_managers):
    """Test when no manager matches."""
    package_config = {
        "name": "git",
        "managers": {
            "scoop": "git"  # Scoop not in available managers
        }
    }
    
    prefs = PreferredManagerOrder()
    result = find_manager_for_package(
        package_config,
        mock_managers,
        preferred_order=prefs,
        managers_supported=None
    )
    
    assert result is None


def test_find_manager_empty_package_id(mock_managers):
    """Test that empty package IDs are skipped."""
    package_config = {
        "name": "git",
        "managers": {
            "winget": "",  # Empty
            "chocolatey": "git"
        }
    }
    
    prefs = PreferredManagerOrder()
    result = find_manager_for_package(
        package_config,
        mock_managers,
        preferred_order=prefs,
        managers_supported=None
    )
    
    # Should skip winget (empty) and use chocolatey
    assert result is not None
    mgr, pkg_id = result
    assert mgr.name == "chocolatey"
    assert pkg_id == "git"


def test_find_manager_without_preferences(mock_managers):
    """Test finding manager without preferences (backward compatibility)."""
    package_config = {
        "name": "git",
        "managers": {
            "apt": "git",
            "winget": "Git.Git"
        }
    }
    
    # No preferences - should use dict iteration order
    result = find_manager_for_package(
        package_config,
        mock_managers,
        preferred_order=None,
        managers_supported=None
    )
    
    assert result is not None
    mgr, pkg_id = result
    # Should find first available manager in dict order
    assert mgr.name in ["apt", "winget"]
    assert pkg_id in ["git", "Git.Git"]

