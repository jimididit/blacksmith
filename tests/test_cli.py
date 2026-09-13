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


def test_cli_module_does_not_shadow_builtin_list():
    """Click command must not replace the builtin list() used inside cli.py."""
    import blacksmith.cli as cli_mod

    assert list([1, 2, 3]) == [1, 2, 3]
    assert hasattr(cli_mod, "list_sets")
    assert "list" in cli_mod.cli.commands

