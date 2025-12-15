"""Tests for YAML schema validation with new fields."""

import pytest
import tempfile
from pathlib import Path

from blacksmith.config.parser import parse_config, load_yaml
from blacksmith.config.validator import validate_config


def test_validate_target_os_string():
    """Test validation of target_os as string."""
    config = {
        "name": "Test Set",
        "packages": [
            {
                "name": "git",
                "managers": {"apt": "git", "winget": "Git.Git"}
            }
        ],
        "target_os": "windows"
    }
    is_valid, error = validate_config(config)
    assert is_valid, f"Validation failed: {error}"


def test_validate_target_os_list():
    """Test validation of target_os as list."""
    config = {
        "name": "Test Set",
        "packages": [
            {
                "name": "git",
                "managers": {"apt": "git", "winget": "Git.Git"}
            }
        ],
        "target_os": ["windows", "linux"]
    }
    is_valid, error = validate_config(config)
    assert is_valid, f"Validation failed: {error}"


def test_validate_invalid_target_os():
    """Test validation rejects invalid target_os."""
    config = {
        "name": "Test Set",
        "packages": [
            {
                "name": "git",
                "managers": {"apt": "git"}
            }
        ],
        "target_os": "invalid_os"
    }
    is_valid, error = validate_config(config)
    assert not is_valid
    assert "target_os" in error.lower()


def test_validate_preferred_managers():
    """Test validation of preferred_managers."""
    config = {
        "name": "Test Set",
        "packages": [
            {
                "name": "git",
                "managers": {"apt": "git", "winget": "Git.Git"}
            }
        ],
        "preferred_managers": {
            "windows": ["winget", "chocolatey"],
            "linux": ["apt", "pacman"]
        }
    }
    is_valid, error = validate_config(config)
    assert is_valid, f"Validation failed: {error}"


def test_validate_invalid_preferred_managers():
    """Test validation rejects invalid manager in preferred_managers."""
    config = {
        "name": "Test Set",
        "packages": [
            {
                "name": "git",
                "managers": {"apt": "git"}
            }
        ],
        "preferred_managers": {
            "windows": ["invalid_manager"]
        }
    }
    is_valid, error = validate_config(config)
    assert not is_valid
    assert "invalid_manager" in error.lower()


def test_validate_managers_supported():
    """Test validation of managers_supported."""
    config = {
        "name": "Test Set",
        "packages": [
            {
                "name": "git",
                "managers": {"apt": "git", "winget": "Git.Git"}
            }
        ],
        "managers_supported": ["winget", "chocolatey", "apt"]
    }
    is_valid, error = validate_config(config)
    assert is_valid, f"Validation failed: {error}"


def test_parse_config_with_new_fields():
    """Test parsing config with new optional fields."""
    config_data = {
        "name": "Test Set",
        "description": "Test description",
        "packages": [
            {
                "name": "git",
                "managers": {"apt": "git", "winget": "Git.Git"}
            }
        ],
        "target_os": ["windows", "linux"],
        "preferred_managers": {
            "windows": ["winget", "chocolatey"],
            "linux": ["apt", "pacman"]
        },
        "managers_supported": ["winget", "apt"]
    }
    
    parsed = parse_config(config_data)
    
    assert parsed["name"] == "Test Set"
    assert parsed["target_os"] == ["windows", "linux"]
    assert "windows" in parsed["preferred_managers"]
    assert parsed["managers_supported"] == ["winget", "apt"]


def test_parse_config_backward_compatible():
    """Test that parsing works without new fields (backward compatibility)."""
    config_data = {
        "name": "Test Set",
        "description": "Test description",
        "packages": [
            {
                "name": "git",
                "managers": {"apt": "git", "winget": "Git.Git"}
            }
        ]
    }
    
    parsed = parse_config(config_data)
    
    assert parsed["name"] == "Test Set"
    assert parsed["target_os"] is None
    assert parsed["preferred_managers"] is None
    assert parsed["managers_supported"] is None


def test_parse_config_normalizes_os_names():
    """Test that parse_config normalizes OS names to lowercase."""
    config_data = {
        "name": "Test Set",
        "packages": [],
        "target_os": ["Windows", "Linux"]
    }
    
    parsed = parse_config(config_data)
    assert parsed["target_os"] == ["windows", "linux"]


def test_parse_config_normalizes_manager_names():
    """Test that parse_config normalizes manager names to lowercase."""
    config_data = {
        "name": "Test Set",
        "packages": [],
        "preferred_managers": {
            "Windows": ["Winget", "Chocolatey"]
        },
        "managers_supported": ["Winget", "Apt"]
    }
    
    parsed = parse_config(config_data)
    assert parsed["preferred_managers"]["windows"] == ["winget", "chocolatey"]
    assert parsed["managers_supported"] == ["winget", "apt"]

