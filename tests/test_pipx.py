"""Tests for pipx install detection helpers."""

from pathlib import Path
from unittest.mock import patch

from blacksmith.utils.pipx import (
    is_pipx_executable,
    is_pipx_prefix,
    pipx_package_name,
    pipx_uninstall_commands,
    read_shebang_interpreter,
    should_use_pipx_uninstall,
)


def test_is_pipx_prefix_detects_venvs_layout(tmp_path):
    prefix = tmp_path / ".local" / "share" / "pipx" / "venvs" / "jdi-blacksmith"
    prefix.mkdir(parents=True)
    assert is_pipx_prefix(prefix) is True
    assert pipx_package_name(prefix=prefix) == "jdi-blacksmith"


def test_is_pipx_prefix_false_for_normal_venv(tmp_path):
    prefix = tmp_path / ".blacksmith-venv"
    prefix.mkdir()
    assert is_pipx_prefix(prefix) is False
    assert pipx_package_name(prefix=prefix) is None


def test_is_pipx_prefix_respects_pipx_home(tmp_path, monkeypatch):
    home = tmp_path / "custom-pipx"
    venv = home / "venvs" / "jdi-blacksmith"
    venv.mkdir(parents=True)
    monkeypatch.setenv("PIPX_HOME", str(home))
    assert is_pipx_prefix(venv) is True


def test_is_pipx_executable_and_bin_dir(tmp_path, monkeypatch):
    bin_dir = tmp_path / "pipx-bin"
    bin_dir.mkdir()
    exe = bin_dir / "blacksmith"
    exe.write_text("x", encoding="utf-8")
    monkeypatch.setenv("PIPX_BIN_DIR", str(bin_dir))
    assert is_pipx_executable(exe) is True
    assert should_use_pipx_uninstall(prefix=tmp_path / "other", executable=exe) is True


def test_should_use_pipx_uninstall_from_prefix(tmp_path):
    prefix = tmp_path / "pipx" / "venvs" / "jdi-blacksmith"
    prefix.mkdir(parents=True)
    assert should_use_pipx_uninstall(prefix=prefix, executable=None) is True


def test_shebang_detects_pipx_shim(tmp_path):
    venv = tmp_path / ".local" / "share" / "pipx" / "venvs" / "jdi-blacksmith"
    py = venv / "bin" / "python"
    py.parent.mkdir(parents=True)
    py.write_text("#!/bin/true\n", encoding="utf-8")
    shim = tmp_path / ".local" / "bin" / "blacksmith"
    shim.parent.mkdir(parents=True)
    shim.write_text(f"#!{py}\n", encoding="utf-8")
    assert read_shebang_interpreter(shim) == str(py)
    assert is_pipx_executable(shim) is True
    assert pipx_package_name(executable=shim) == "jdi-blacksmith"


@patch("blacksmith.utils.pipx.shutil.which")
def test_pipx_uninstall_commands_include_path_and_module(mock_which, tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    mock_which.side_effect = lambda name: {
        "pipx": "/usr/bin/pipx",
        "python3": "/usr/bin/python3",
        "python": None,
    }.get(name)

    cmds = pipx_uninstall_commands("jdi-blacksmith")
    assert ["/usr/bin/pipx", "uninstall", "jdi-blacksmith"] in cmds
    assert ["/usr/bin/python3", "-m", "pipx", "uninstall", "jdi-blacksmith"] in cmds
