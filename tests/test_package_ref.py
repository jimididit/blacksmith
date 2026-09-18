# tests/test_package_ref.py
from blacksmith.utils.package_ref import parse_package_ref, versions_equal


def test_parse_bare():
    assert parse_package_ref("git") == ("git", None)


def test_parse_pinned():
    assert parse_package_ref("git|2.40.0") == ("git", "2.40.0")


def test_parse_only_first_pipe():
    assert parse_package_ref("foo|1.0|extra") == ("foo", "1.0|extra")


def test_versions_equal_strips_leading_v():
    assert versions_equal("v1.2.3", "1.2.3") is True
    assert versions_equal("V1.2.3", "1.2.3") is True
    assert versions_equal("1.2.3", "1.2.4") is False
    assert versions_equal("1.2.3", "1.2.3") is True
