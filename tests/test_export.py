"""Tests for export functionality."""

import pytest
import json
import xml.etree.ElementTree as ET
import tempfile
from pathlib import Path

from blacksmith.export import (
    WingetExporter, ChocolateyExporter, AptExporter,
    PacmanExporter, ScoopExporter
)


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return {
        "name": "Test Set",
        "description": "Test description",
        "packages": [
            {
                "name": "git",
                "managers": {
                    "winget": "Git.Git",
                    "chocolatey": "git",
                    "apt": "git",
                    "pacman": "git",
                    "scoop": "git"
                }
            },
            {
                "name": "curl",
                "managers": {
                    "winget": "cURL.cURL",
                    "chocolatey": "curl",
                    "apt": "curl"
                }
            },
            {
                "name": "vim",
                "managers": {
                    "apt": "vim",
                    "pacman": "vim"
                }
            }
        ]
    }


def test_winget_exporter(sample_config):
    """Test Winget JSON export."""
    exporter = WingetExporter(sample_config)
    output = exporter.export()
    
    # Should be valid JSON
    data = json.loads(output)
    assert isinstance(data, list)
    assert "Git.Git" in data
    assert "cURL.cURL" in data
    assert len(data) == 2  # Only winget packages


def test_winget_exporter_file(sample_config):
    """Test Winget export to file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name
    
    try:
        exporter = WingetExporter(sample_config)
        exporter.export(temp_path)
        
        # Verify file was created and contains valid JSON
        with open(temp_path, 'r') as f:
            data = json.load(f)
            assert isinstance(data, list)
    finally:
        Path(temp_path).unlink()


def test_chocolatey_exporter(sample_config):
    """Test Chocolatey packages.config export."""
    exporter = ChocolateyExporter(sample_config)
    output = exporter.export()
    
    # Should be valid XML
    assert '<?xml' in output
    assert '<packages>' in output
    assert '<package' in output
    
    # Parse XML
    root = ET.fromstring(output.split('\n', 1)[1])  # Skip XML declaration
    assert root.tag == "packages"
    
    packages = root.findall("package")
    assert len(packages) == 2  # Only chocolatey packages
    
    # Check package IDs
    pkg_ids = [pkg.get("id") for pkg in packages]
    assert "git" in pkg_ids
    assert "curl" in pkg_ids


def test_chocolatey_exporter_with_version(sample_config):
    """Test Chocolatey export with version info."""
    # Add version to package
    sample_config["packages"][0]["managers"]["chocolatey"] = "git|2.40.0"
    
    exporter = ChocolateyExporter(sample_config)
    output = exporter.export()
    
    root = ET.fromstring(output.split('\n', 1)[1])
    packages = root.findall("package")
    git_pkg = next((p for p in packages if p.get("id") == "git"), None)
    assert git_pkg is not None
    assert git_pkg.get("version") == "2.40.0"


def test_apt_exporter(sample_config):
    """Test Apt list export."""
    exporter = AptExporter(sample_config)
    output = exporter.export()
    
    # Should be plain text, one package per line
    lines = output.strip().split('\n')
    assert "git" in lines
    assert "curl" in lines
    assert "vim" in lines
    assert len(lines) == 3  # All apt packages


def test_pacman_exporter(sample_config):
    """Test Pacman list export."""
    exporter = PacmanExporter(sample_config)
    output = exporter.export()
    
    # Should be plain text, one package per line
    lines = output.strip().split('\n')
    assert "git" in lines
    assert "vim" in lines
    assert len(lines) == 2  # Only pacman packages


def test_scoop_exporter(sample_config):
    """Test Scoop JSON export."""
    exporter = ScoopExporter(sample_config)
    output = exporter.export()
    
    # Should be valid JSON array
    data = json.loads(output)
    assert isinstance(data, list)
    assert "git" in data
    assert len(data) == 1  # Only scoop packages


def test_exporter_filters_by_manager(sample_config):
    """Test that exporters only include packages for their manager."""
    # Test winget exporter
    winget_exporter = WingetExporter(sample_config)
    winget_packages = winget_exporter.filter_packages_by_manager("winget")
    assert len(winget_packages) == 2  # git and curl have winget entries
    
    # Test apt exporter
    apt_exporter = AptExporter(sample_config)
    apt_packages = apt_exporter.filter_packages_by_manager("apt")
    assert len(apt_packages) == 3  # git, curl, vim all have apt entries


def test_exporter_empty_package_id():
    """Test that exporters skip empty package IDs."""
    config = {
        "name": "Test",
        "packages": [
            {
                "name": "git",
                "managers": {
                    "winget": "Git.Git",
                    "chocolatey": ""  # Empty
                }
            }
        ]
    }
    
    winget_exporter = WingetExporter(config)
    output = winget_exporter.export()
    data = json.loads(output)
    assert "Git.Git" in data
    
    choco_exporter = ChocolateyExporter(config)
    output = choco_exporter.export()
    # Should not have any packages since chocolatey ID is empty
    root = ET.fromstring(output.split('\n', 1)[1])
    packages = root.findall("package")
    assert len(packages) == 0


def test_exporter_file_extensions():
    """Test that exporters return correct file extensions."""
    config = {"name": "Test", "packages": []}
    
    assert WingetExporter(config).get_file_extension() == ".json"
    assert ChocolateyExporter(config).get_file_extension() == ".config"
    assert AptExporter(config).get_file_extension() == ".txt"
    assert PacmanExporter(config).get_file_extension() == ".txt"
    assert ScoopExporter(config).get_file_extension() == ".json"

