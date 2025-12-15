"""Tests for backward compatibility with old YAML format."""

import pytest
import tempfile
from pathlib import Path

from blacksmith.config.loader import load_custom_config
from blacksmith.config.parser import parse_config
from blacksmith.config.validator import validate_config


def test_old_format_without_target_os():
    """Test that old format without target_os still works."""
    old_config = {
        "name": "Old Set",
        "description": "Old format set",
        "packages": [
            {
                "name": "git",
                "managers": {
                    "apt": "git",
                    "winget": "Git.Git"
                }
            }
        ]
    }
    
    # Should parse successfully
    parsed = parse_config(old_config)
    assert parsed["name"] == "Old Set"
    assert parsed["target_os"] is None
    assert parsed["preferred_managers"] is None
    assert parsed["managers_supported"] is None
    
    # Should validate successfully
    is_valid, error = validate_config(parsed)
    assert is_valid, f"Validation failed: {error}"


def test_old_format_single_manager():
    """Test old format with single manager per package."""
    old_config = {
        "name": "Old Set",
        "packages": [
            {
                "name": "git",
                "managers": {
                    "apt": "git"
                }
            },
            {
                "name": "curl",
                "managers": {
                    "winget": "cURL.cURL"
                }
            }
        ]
    }
    
    parsed = parse_config(old_config)
    is_valid, error = validate_config(parsed)
    assert is_valid, f"Validation failed: {error}"


def test_load_existing_sets():
    """Test that existing pre-made sets still load correctly."""
    from blacksmith.config.loader import load_set
    
    # These should all load without errors
    sets = ["minimal", "development", "cybersecurity"]
    
    for set_name in sets:
        config = load_set(set_name)
        assert config is not None, f"Failed to load {set_name}"
        assert "packages" in config
        assert len(config["packages"]) > 0
        
        # Should validate
        is_valid, error = validate_config(config)
        assert is_valid, f"{set_name} validation failed: {error}"


def test_yaml_file_backward_compatible():
    """Test loading old format YAML file."""
    old_yaml = """---
name: Old Format Set
description: Test backward compatibility
packages:
  - name: git
    managers:
      apt: git
      winget: Git.Git
  - name: curl
    managers:
      apt: curl
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(old_yaml)
        temp_path = f.name
    
    try:
        config = load_custom_config(temp_path)
        assert config is not None
        assert config["name"] == "Old Format Set"
        assert config["target_os"] is None  # Not in old format
        assert len(config["packages"]) == 2
    finally:
        Path(temp_path).unlink()


def test_mixed_format():
    """Test config with some new fields but not all."""
    mixed_config = {
        "name": "Mixed Set",
        "packages": [
            {
                "name": "git",
                "managers": {"apt": "git", "winget": "Git.Git"}
            }
        ],
        "target_os": ["windows", "linux"],
        # No preferred_managers or managers_supported
    }
    
    parsed = parse_config(mixed_config)
    assert parsed["target_os"] == ["windows", "linux"]
    assert parsed["preferred_managers"] is None
    assert parsed["managers_supported"] is None
    
    is_valid, error = validate_config(parsed)
    assert is_valid, f"Validation failed: {error}"


def test_case_insensitive_os_names():
    """Test that OS names are case-insensitive in parsing."""
    config = {
        "name": "Test",
        "packages": [],
        "target_os": ["Windows", "LINUX", "Darwin"]
    }
    
    parsed = parse_config(config)
    assert parsed["target_os"] == ["windows", "linux", "darwin"]


def test_case_insensitive_manager_names():
    """Test that manager names are case-insensitive."""
    config = {
        "name": "Test",
        "packages": [
            {
                "name": "git",
                "managers": {
                    "Winget": "Git.Git",
                    "CHOCOLATEY": "git",
                    "Apt": "git"
                }
            }
        ]
    }
    
    parsed = parse_config(config)
    is_valid, error = validate_config(parsed)
    assert is_valid, f"Validation failed: {error}"

