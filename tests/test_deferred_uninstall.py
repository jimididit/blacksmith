"""Tests for Windows-friendly uninstall helpers."""

from pathlib import Path
from unittest.mock import patch

import pytest

from blacksmith.utils.deferred_delete import (
    schedule_pip_uninstall,
    sibling_pip_uninstall_cmds,
    try_unlock_windows_executable,
)


def test_sibling_pip_uninstall_cmds_finds_pip_exe(tmp_path):
    scripts = tmp_path / "Scripts"
    scripts.mkdir()
    (scripts / "blacksmith.exe").write_bytes(b"x")
    pip = scripts / "pip.exe"
    pip.write_bytes(b"x")
    cmds = sibling_pip_uninstall_cmds(scripts / "blacksmith.exe")
    assert cmds
    assert cmds[0][0] == str(pip.resolve())
    assert cmds[0][1:] == ["uninstall", "jdi-blacksmith", "-y"]


def test_sibling_pip_uninstall_cmds_empty_without_path():
    assert sibling_pip_uninstall_cmds(None) == []


def test_try_unlock_windows_executable_renames(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "blacksmith.utils.deferred_delete._is_windows", lambda: True
    )
    exe = tmp_path / "blacksmith.exe"
    exe.write_bytes(b"mz")
    backup = try_unlock_windows_executable(exe)
    assert backup is not None
    assert backup.name == "blacksmith.exe.old"
    assert backup.exists()
    assert not exe.exists()


def test_try_unlock_noop_on_posix(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "blacksmith.utils.deferred_delete._is_windows", lambda: False
    )
    exe = tmp_path / "blacksmith"
    exe.write_text("x", encoding="utf-8")
    assert try_unlock_windows_executable(exe) is None
    assert exe.exists()


def test_schedule_pip_uninstall_rejects_unsafe_cmd():
    assert schedule_pip_uninstall(["pip", "install", "evil"]) is False
    assert schedule_pip_uninstall([]) is False


@patch("blacksmith.utils.deferred_delete.subprocess.Popen")
def test_schedule_pip_uninstall_spawns(mock_popen, tmp_path):
    pip = tmp_path / "pip.exe"
    pip.write_bytes(b"x")
    assert schedule_pip_uninstall([str(pip), "uninstall", "jdi-blacksmith", "-y"]) is True
    mock_popen.assert_called_once()
    spawned = mock_popen.call_args.args[0]
    assert spawned[-3:] == ["uninstall", "jdi-blacksmith", "-y"]
