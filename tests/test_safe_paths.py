"""Tests for uninstall path safety helpers."""

from pathlib import Path

import pytest

from blacksmith.utils.safe_paths import (
    assert_safe_blacksmith_executable,
    assert_safe_blacksmith_venv,
    expected_venv_path,
)
from blacksmith.utils.deferred_delete import (
    remove_executable_now,
    remove_venv_now,
)


def test_expected_venv_path_is_under_home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    assert expected_venv_path() == (tmp_path / ".blacksmith-venv").resolve()


def test_assert_safe_venv_accepts_exact_path(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    venv = tmp_path / ".blacksmith-venv"
    venv.mkdir()
    assert assert_safe_blacksmith_venv(venv) == venv.resolve()


def test_assert_safe_venv_rejects_other_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    other = tmp_path / "evil-venv"
    other.mkdir()
    with pytest.raises(ValueError, match="unexpected venv"):
        assert_safe_blacksmith_venv(other)


def test_assert_safe_executable_accepts_home_blacksmith(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr("sys.prefix", str(tmp_path / "prefix"))
    exe = tmp_path / ".local" / "bin" / "blacksmith"
    exe.parent.mkdir(parents=True)
    exe.write_text("#!/usr/bin/env python\n", encoding="utf-8")
    assert assert_safe_blacksmith_executable(exe) == exe.resolve()


def test_assert_safe_executable_rejects_bad_name(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    bad = tmp_path / "not-blacksmith"
    bad.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="unexpected executable name"):
        assert_safe_blacksmith_executable(bad)


def test_assert_safe_executable_rejects_outside_roots(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    outside = tmp_path / "outside" / "blacksmith"
    outside.parent.mkdir()
    outside.write_text("x", encoding="utf-8")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.setattr("sys.prefix", str(home / "prefix"))
    monkeypatch.setattr("sys.executable", str(home / "bin" / "python"))
    with pytest.raises(ValueError, match="outside allowed roots"):
        assert_safe_blacksmith_executable(outside)


def test_remove_venv_now_only_deletes_expected(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    venv = tmp_path / ".blacksmith-venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "bin" / "python").write_text("x", encoding="utf-8")
    remove_venv_now(venv)
    assert not venv.exists()


def test_remove_executable_now_deletes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr("sys.prefix", str(tmp_path))
    exe = tmp_path / "blacksmith"
    exe.write_text("x", encoding="utf-8")
    remove_executable_now(exe)
    assert not exe.exists()


def test_cleanup_script_has_no_path_interpolation():
    from blacksmith.utils import deferred_delete

    # Script body must not embed caller paths — only argv placeholders.
    assert "{path}" not in deferred_delete._CLEANUP_PY
    assert "sys.argv" in deferred_delete._CLEANUP_PY
