"""Tests for Click help Examples epilog sections."""

import pytest
from click.testing import CliRunner

from blacksmith.cli import cli
from blacksmith.utils.cli_examples import examples_epilog


def test_examples_epilog_format():
    text = examples_epilog("blacksmith list", "blacksmith install minimal --yes")
    assert "Examples:" in text
    assert "\b\n" in text
    assert "  blacksmith list\n" in text
    assert "  blacksmith install minimal --yes\n" in text


def test_examples_epilog_requires_lines():
    with pytest.raises(ValueError):
        examples_epilog()


@pytest.mark.parametrize(
    "args",
    [
        ["--help"],
        ["list", "--help"],
        ["audit", "--help"],
        ["install", "--help"],
        ["apply", "--help"],
        ["export", "--help"],
        ["info", "--help"],
        ["validate", "--help"],
        ["search", "--help"],
        ["create", "--help"],
        ["sign", "--help"],
        ["uninstall", "--help"],
    ],
)
def test_help_includes_examples_section(args):
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 0, result.output
    assert "Examples:" in result.output
    assert "blacksmith " in result.output
    # Lines must stay separate (Click must not collapse the epilog).
    lines = [ln.strip() for ln in result.output.splitlines() if "blacksmith " in ln]
    assert len(lines) >= 1
    assert all(ln.startswith("blacksmith ") for ln in lines)
