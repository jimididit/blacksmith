"""Tests for configuration loading and validation."""

import pytest
from pathlib import Path

from blacksmith.config.loader import load_set, list_available_sets
from blacksmith.config.validator import validate_config


def test_list_available_sets():
    """Test that we can list available sets."""
    sets = list_available_sets()
    assert isinstance(sets, list)
    # Should have at least minimal, development, cybersecurity
    assert len(sets) >= 3


def test_load_minimal_set():
    """Test loading the minimal set."""
    config = load_set('minimal')
    assert config is not None
    assert config.get('name') == 'Minimal Setup'
    assert 'packages' in config


def test_load_development_set():
    """Test loading the development set."""
    config = load_set('development')
    assert config is not None
    assert config.get('name') == 'Development Tools'
    assert 'packages' in config


def test_load_cybersecurity_set():
    """Test loading the cybersecurity set."""
    config = load_set('cybersecurity')
    assert config is not None
    assert config.get('name') == 'Cybersecurity Tools'
    assert 'packages' in config


def test_validate_config_structure():
    """Test that loaded configs are valid."""
    config = load_set('minimal')
    assert config is not None
    
    is_valid, error = validate_config(config)
    assert is_valid, f"Config validation failed: {error}"


def test_validate_config_with_new_fields():
    """Test validation with new optional fields."""
    config = {
        "name": "Test Set",
        "packages": [
            {
                "name": "git",
                "managers": {"apt": "git", "winget": "Git.Git"}
            }
        ],
        "target_os": ["windows", "linux"],
        "preferred_managers": {
            "windows": ["winget", "chocolatey"]
        },
        "managers_supported": ["winget", "apt"]
    }
    
    is_valid, error = validate_config(config)
    assert is_valid, f"Validation failed: {error}"

