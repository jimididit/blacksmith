"""Integration tests for full workflows."""

import pytest
import tempfile
from pathlib import Path

from blacksmith.config.loader import load_set, load_custom_config
from blacksmith.config.preferences import PreferredManagerOrder
from blacksmith.package_managers.detector import find_manager_for_package, detect_available_managers


def test_create_to_install_workflow():
    """Test that a created config can be loaded and used for installation."""
    # Simulate a created config
    created_config = {
        "name": "Test Workflow Set",
        "description": "Created for testing",
        "target_os": ["windows", "linux"],
        "preferred_managers": {
            "windows": ["winget", "chocolatey"],
            "linux": ["apt", "pacman"]
        },
        "managers_supported": ["winget", "chocolatey", "apt", "pacman"],
        "packages": [
            {
                "name": "git",
                "managers": {
                    "winget": "Git.Git",
                    "chocolatey": "git",
                    "apt": "git",
                    "pacman": "git"
                }
            }
        ]
    }
    
    # Save to temp file
    import yaml
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(created_config, f)
        temp_path = f.name
    
    try:
        # Load it back
        loaded_config = load_custom_config(temp_path)
        assert loaded_config is not None
        assert loaded_config["name"] == "Test Workflow Set"
        assert loaded_config["target_os"] == ["windows", "linux"]
        
        # Test that preferences work
        prefs = PreferredManagerOrder(custom_preferences=loaded_config.get("preferred_managers"))
        available_managers = detect_available_managers()
        
        # Try to find manager for package
        for pkg in loaded_config["packages"]:
            result = find_manager_for_package(
                pkg,
                available_managers,
                preferred_order=prefs,
                managers_supported=loaded_config.get("managers_supported")
            )
            # Result might be None if managers not available, but shouldn't crash
            assert result is None or isinstance(result, tuple)
    finally:
        Path(temp_path).unlink()


def test_cross_platform_set_creation():
    """Test creating and validating a cross-platform set."""
    cross_platform_config = {
        "name": "Cross-Platform Set",
        "description": "Works on Windows and Linux",
        "target_os": ["windows", "linux"],
        "preferred_managers": {
            "windows": ["winget", "chocolatey", "scoop"],
            "linux": ["apt", "pacman", "flatpak"]
        },
        "packages": [
            {
                "name": "git",
                "managers": {
                    "winget": "Git.Git",
                    "chocolatey": "git",
                    "apt": "git",
                    "pacman": "git"
                }
            },
            {
                "name": "curl",
                "managers": {
                    "winget": "cURL.cURL",
                    "chocolatey": "curl",
                    "apt": "curl",
                    "pacman": "curl"
                }
            }
        ]
    }
    
    # Validate structure
    from blacksmith.config.validator import validate_config
    is_valid, error = validate_config(cross_platform_config)
    assert is_valid, f"Validation failed: {error}"
    
    # Test parsing
    from blacksmith.config.parser import parse_config
    parsed = parse_config(cross_platform_config)
    assert parsed["target_os"] == ["windows", "linux"]
    assert "windows" in parsed["preferred_managers"]
    assert "linux" in parsed["preferred_managers"]


def test_export_import_workflow():
    """Test export then validate exported format."""
    config = {
        "name": "Export Test",
        "packages": [
            {
                "name": "git",
                "managers": {
                    "winget": "Git.Git",
                    "chocolatey": "git",
                    "apt": "git"
                }
            }
        ]
    }
    
    # Test Winget export
    from blacksmith.export import WingetExporter
    exporter = WingetExporter(config)
    output = exporter.export()
    
    # Should be valid JSON
    import json
    data = json.loads(output)
    assert isinstance(data, list)
    assert len(data) > 0
    
    # Test Chocolatey export
    from blacksmith.export import ChocolateyExporter
    choco_exporter = ChocolateyExporter(config)
    choco_output = choco_exporter.export()
    
    # Should be valid XML
    import xml.etree.ElementTree as ET
    root = ET.fromstring(choco_output.split('\n', 1)[1])
    assert root.tag == "packages"


def test_manager_fallback_logic():
    """Test that manager fallback works correctly."""
    from blacksmith.package_managers.base import PackageManager
    from unittest.mock import Mock
    
    # Create mock managers
    winget = Mock(spec=PackageManager)
    winget.name = "winget"
    choco = Mock(spec=PackageManager)
    choco.name = "chocolatey"
    
    package_config = {
        "name": "git",
        "managers": {
            "winget": "Git.Git",
            "chocolatey": "git"
        }
    }
    
    # Test with both available (should prefer winget)
    prefs = PreferredManagerOrder()
    result = find_manager_for_package(
        package_config,
        [winget, choco],
        preferred_order=prefs,
        managers_supported=None
    )
    assert result is not None
    assert result[0].name == "winget"
    
    # Test with only chocolatey available (should fallback)
    result = find_manager_for_package(
        package_config,
        [choco],
        preferred_order=prefs,
        managers_supported=None
    )
    assert result is not None
    assert result[0].name == "chocolatey"


def test_os_compatibility_checking():
    """Test OS compatibility checking logic."""
    from blacksmith.utils.os_detector import detect_os
    
    current_os = detect_os().lower()
    if current_os == "darwin":
        current_os = "macos"
    
    # Config targeting current OS
    compatible_config = {
        "name": "Compatible",
        "packages": [],
        "target_os": [current_os]
    }
    
    # Config targeting different OS
    incompatible_config = {
        "name": "Incompatible",
        "packages": [],
        "target_os": ["windows" if current_os != "windows" else "linux"]
    }
    
    from blacksmith.config.parser import parse_config
    from blacksmith.utils.ui import format_os_status
    
    # Test compatible
    parsed = parse_config(compatible_config)
    status, color = format_os_status(parsed["target_os"], current_os)
    assert "Compatible" in status
    assert color == "#44FFD1"
    
    # Test incompatible
    parsed = parse_config(incompatible_config)
    status, color = format_os_status(parsed["target_os"], current_os)
    assert "Not compatible" in status
    assert color == "#FF6B6B"

