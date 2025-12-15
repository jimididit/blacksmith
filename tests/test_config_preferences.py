"""Tests for configuration preferences system."""

import pytest

from blacksmith.config.preferences import PreferredManagerOrder
from blacksmith.utils.os_detector import detect_os


def test_default_preferences_windows():
    """Test default preferences for Windows."""
    prefs = PreferredManagerOrder()
    order = prefs.get_preferred_order("windows")
    assert isinstance(order, list)
    assert "winget" in order
    assert "chocolatey" in order
    assert "scoop" in order
    # Check order
    assert order.index("winget") < order.index("chocolatey")
    assert order.index("chocolatey") < order.index("scoop")


def test_default_preferences_linux():
    """Test default preferences for Linux."""
    prefs = PreferredManagerOrder()
    order = prefs.get_preferred_order("linux")
    assert isinstance(order, list)
    assert "apt" in order
    assert "pacman" in order
    assert "yum" in order


def test_custom_preferences():
    """Test custom preferences override."""
    custom = {
        "windows": ["scoop", "winget"],
        "linux": ["flatpak", "apt"]
    }
    prefs = PreferredManagerOrder(custom_preferences=custom)
    
    windows_order = prefs.get_preferred_order("windows")
    assert windows_order == ["scoop", "winget"]
    
    linux_order = prefs.get_preferred_order("linux")
    assert linux_order == ["flatpak", "apt"]


def test_get_preferred_order_auto_detect():
    """Test that get_preferred_order auto-detects OS if not provided."""
    prefs = PreferredManagerOrder()
    order = prefs.get_preferred_order()
    assert isinstance(order, list)
    assert len(order) > 0


def test_find_best_manager():
    """Test finding best manager for a package."""
    from blacksmith.package_managers.base import PackageManager
    from unittest.mock import Mock
    
    # Create mock managers
    winget = Mock(spec=PackageManager)
    winget.name = "winget"
    choco = Mock(spec=PackageManager)
    choco.name = "chocolatey"
    
    available_managers = [winget, choco]
    
    # Package with both managers
    package_managers = {
        "winget": "Git.Git",
        "chocolatey": "git"
    }
    
    # Test with default preferences (winget preferred)
    prefs = PreferredManagerOrder()
    result = prefs.find_best_manager(package_managers, available_managers, os_name="windows")
    
    assert result is not None
    mgr, pkg_id = result
    assert mgr.name == "winget"
    assert pkg_id == "Git.Git"


def test_find_best_manager_fallback():
    """Test manager fallback when preferred is not available."""
    from blacksmith.package_managers.base import PackageManager
    from unittest.mock import Mock
    
    # Only chocolatey available
    choco = Mock(spec=PackageManager)
    choco.name = "chocolatey"
    available_managers = [choco]
    
    # Package with both managers
    package_managers = {
        "winget": "Git.Git",
        "chocolatey": "git"
    }
    
    prefs = PreferredManagerOrder()
    result = prefs.find_best_manager(package_managers, available_managers, os_name="windows")
    
    # Should fallback to chocolatey since winget not available
    assert result is not None
    mgr, pkg_id = result
    assert mgr.name == "chocolatey"
    assert pkg_id == "git"


def test_find_best_manager_empty_package_id():
    """Test that empty package IDs are skipped."""
    from blacksmith.package_managers.base import PackageManager
    from unittest.mock import Mock
    
    winget = Mock(spec=PackageManager)
    winget.name = "winget"
    available_managers = [winget]
    
    # Package with empty ID for winget
    package_managers = {
        "winget": "",
        "chocolatey": "git"
    }
    
    prefs = PreferredManagerOrder()
    result = prefs.find_best_manager(package_managers, available_managers, os_name="windows")
    
    # Should return None since winget has empty ID and chocolatey not available
    assert result is None


def test_get_managers_in_order():
    """Test getting managers sorted by preference."""
    from blacksmith.package_managers.base import PackageManager
    from unittest.mock import Mock
    
    # Create managers in wrong order
    choco = Mock(spec=PackageManager)
    choco.name = "chocolatey"
    winget = Mock(spec=PackageManager)
    winget.name = "winget"
    available_managers = [choco, winget]  # Wrong order
    
    prefs = PreferredManagerOrder()
    ordered = prefs.get_managers_in_order(available_managers, os_name="windows")
    
    # Should be ordered by preference (winget first)
    assert len(ordered) == 2
    assert ordered[0].name == "winget"
    assert ordered[1].name == "chocolatey"


def test_get_managers_in_order_with_filter():
    """Test filtering managers by managers_supported."""
    from blacksmith.package_managers.base import PackageManager
    from unittest.mock import Mock
    
    winget = Mock(spec=PackageManager)
    winget.name = "winget"
    choco = Mock(spec=PackageManager)
    choco.name = "chocolatey"
    scoop = Mock(spec=PackageManager)
    scoop.name = "scoop"
    available_managers = [winget, choco, scoop]
    
    prefs = PreferredManagerOrder()
    # Filter to only winget and chocolatey
    ordered = prefs.get_managers_in_order(
        available_managers,
        os_name="windows",
        managers_supported=["winget", "chocolatey"]
    )
    
    assert len(ordered) == 2
    assert all(mgr.name in ["winget", "chocolatey"] for mgr in ordered)
    assert not any(mgr.name == "scoop" for mgr in ordered)

