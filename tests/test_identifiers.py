"""Tests for package ID / search query allowlists."""

from blacksmith.utils.identifiers import (
    is_safe_package_id,
    is_safe_search_query,
    validate_package_id,
    validate_search_query,
)
from blacksmith.config.validator import validate_config


def test_safe_builtin_style_ids():
    for pkg_id in [
        "git",
        "Git.Git",
        "com.visualstudio.Code",
        "testssl.sh",
        "python3-pip",
        "burp-suite-free-edition",
        "pkg|1.2.3",
    ]:
        ok, err = validate_package_id(pkg_id)
        assert ok, err


def test_rejects_shell_metacharacters():
    for pkg_id in [
        "git & calc",
        "git;whoami",
        "git|whoami",
        "pkg|not-a-version",
        "git$(whoami)",
        "git`whoami`",
        "-y",
        "--force",
        " git",
    ]:
        assert not is_safe_package_id(pkg_id)


def test_validate_config_rejects_unsafe_package_id():
    config = {
        "name": "Bad",
        "packages": [
            {
                "name": "evil",
                "managers": {"winget": "Git.Git & calc.exe"},
            }
        ],
    }
    ok, error = validate_config(config)
    assert not ok
    assert error is not None
    assert "unsafe" in error.lower() or "disallowed" in error.lower()


def test_search_query_allows_spaces_rejects_meta():
    assert is_safe_search_query("visual studio")
    ok, _ = validate_search_query("git")
    assert ok
    assert not is_safe_search_query("git; rm -rf /")
    assert not is_safe_search_query("-query")
