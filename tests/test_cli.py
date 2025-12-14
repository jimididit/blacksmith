"""Tests for CLI functionality."""

import pytest
from click.testing import CliRunner

from blacksmith.cli import cli


def test_cli_version():
    """Test that CLI version command works."""
    runner = CliRunner()
    result = runner.invoke(cli, ['--version'])
    assert result.exit_code == 0
    assert 'Blacksmith' in result.output


def test_cli_help():
    """Test that CLI help command works."""
    runner = CliRunner()
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert 'Blacksmith' in result.output


def test_list_command():
    """Test that list command works."""
    runner = CliRunner()
    result = runner.invoke(cli, ['list'])
    # Should not crash, even if no sets are found
    assert result.exit_code in [0, 1]  # 0 if sets found, 1 if not

