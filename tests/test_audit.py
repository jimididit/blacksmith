from pathlib import Path

from blacksmith.audit.paths import default_audit_log_path, user_config_dir


def test_user_config_dir_linux(monkeypatch, tmp_path):
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    assert user_config_dir() == (tmp_path / "xdg" / "blacksmith").resolve()
    assert default_audit_log_path() == (
        tmp_path / "xdg" / "blacksmith" / "audit.jsonl"
    ).resolve()


def test_user_config_dir_windows(monkeypatch, tmp_path):
    monkeypatch.setattr("sys.platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    assert user_config_dir() == (tmp_path / "appdata" / "blacksmith").resolve()
