"""Tests for minisign trust discovery and verification."""

from pathlib import Path
from unittest.mock import Mock, patch

from click.testing import CliRunner

from blacksmith.cli import cli
from blacksmith.trust.paths import iter_trusted_pubkeys, user_trusted_keys_dir
from blacksmith.trust.verify import default_signature_path, verify_set_signature


def test_default_signature_path():
    assert default_signature_path(Path("sets/lab.yaml")) == Path("sets/lab.yaml.minisig")


def test_user_trusted_keys_dir_linux(monkeypatch, tmp_path):
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    assert user_trusted_keys_dir() == (tmp_path / "xdg" / "blacksmith" / "trusted_keys").resolve()


def test_iter_trusted_pubkeys_order(tmp_path, monkeypatch):
    bundled = tmp_path / "bundled"
    bundled.mkdir()
    (bundled / "official.pub").write_text("pub-a\n", encoding="utf-8")
    user = tmp_path / "userkeys"
    user.mkdir()
    (user / "mine.pub").write_text("pub-b\n", encoding="utf-8")
    extra = tmp_path / "extra.pub"
    extra.write_text("pub-c\n", encoding="utf-8")

    monkeypatch.setattr(
        "blacksmith.trust.paths.bundled_keys_dir", lambda: bundled
    )
    monkeypatch.setattr(
        "blacksmith.trust.paths.user_trusted_keys_dir", lambda: user
    )

    keys = iter_trusted_pubkeys(extra=[extra])
    names = [p.name for p in keys]
    assert names == ["official.pub", "mine.pub", "extra.pub"]


def test_verify_missing_signature(tmp_path):
    cfg = tmp_path / "set.yaml"
    cfg.write_text("name: t\npackages: []\n", encoding="utf-8")
    result = verify_set_signature(cfg)
    assert result.ok is False
    assert "Signature file not found" in result.message


@patch("blacksmith.trust.verify.shutil.which", return_value=None)
def test_verify_missing_minisign(_which, tmp_path):
    cfg = tmp_path / "set.yaml"
    cfg.write_text("name: t\npackages: []\n", encoding="utf-8")
    sig = tmp_path / "set.yaml.minisig"
    sig.write_text("sig\n", encoding="utf-8")
    result = verify_set_signature(cfg)
    assert result.ok is False
    assert "minisign not found" in result.message


@patch("blacksmith.trust.verify.iter_trusted_pubkeys", return_value=[])
@patch("blacksmith.trust.verify.shutil.which", return_value="/usr/bin/minisign")
def test_verify_no_keys(_which, _keys, tmp_path):
    cfg = tmp_path / "set.yaml"
    cfg.write_text("name: t\npackages: []\n", encoding="utf-8")
    (tmp_path / "set.yaml.minisig").write_text("sig\n", encoding="utf-8")
    result = verify_set_signature(cfg)
    assert result.ok is False
    assert "No trusted public keys" in result.message


@patch("blacksmith.trust.verify.subprocess.run")
@patch("blacksmith.trust.verify.iter_trusted_pubkeys")
@patch("blacksmith.trust.verify.shutil.which", return_value="/usr/bin/minisign")
def test_verify_success_first_key(_which, mock_keys, mock_run, tmp_path):
    pub = tmp_path / "a.pub"
    pub.write_text("pub\n", encoding="utf-8")
    mock_keys.return_value = [pub]
    mock_run.return_value = Mock(returncode=0, stdout="OK", stderr="")

    cfg = tmp_path / "set.yaml"
    cfg.write_text("name: t\npackages: []\n", encoding="utf-8")
    (tmp_path / "set.yaml.minisig").write_text("sig\n", encoding="utf-8")

    result = verify_set_signature(cfg)
    assert result.ok is True
    assert result.pubkey_used == pub.resolve()
    cmd = mock_run.call_args.args[0]
    assert cmd[0] == "/usr/bin/minisign"
    assert cmd[1] == "-Vm"
    assert mock_run.call_args.kwargs.get("shell") is False


@patch("blacksmith.trust.verify.subprocess.run")
@patch("blacksmith.trust.verify.iter_trusted_pubkeys")
@patch("blacksmith.trust.verify.shutil.which", return_value="/usr/bin/minisign")
def test_verify_tries_next_key(_which, mock_keys, mock_run, tmp_path):
    pub_a = tmp_path / "a.pub"
    pub_b = tmp_path / "b.pub"
    pub_a.write_text("a\n", encoding="utf-8")
    pub_b.write_text("b\n", encoding="utf-8")
    mock_keys.return_value = [pub_a, pub_b]
    mock_run.side_effect = [
        Mock(returncode=1, stdout="", stderr="bad"),
        Mock(returncode=0, stdout="OK", stderr=""),
    ]

    cfg = tmp_path / "set.yaml"
    cfg.write_text("name: t\npackages: []\n", encoding="utf-8")
    (tmp_path / "set.yaml.minisig").write_text("sig\n", encoding="utf-8")

    result = verify_set_signature(cfg)
    assert result.ok is True
    assert result.pubkey_used == pub_b.resolve()
    assert mock_run.call_count == 2


def test_install_require_signature_without_file():
    runner = CliRunner()
    result = runner.invoke(cli, ["install", "minimal", "--require-signature"])
    assert result.exit_code == 1
    assert "--require-signature only applies with --file" in result.output


@patch("blacksmith.cli.load_custom_config")
@patch("blacksmith.trust.verify.verify_set_signature")
def test_install_require_signature_fails_closed(mock_verify, mock_load):
    mock_verify.return_value = Mock(ok=False, message="bad sig")
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("set.yaml").write_text("name: t\npackages: []\n", encoding="utf-8")
        result = runner.invoke(
            cli, ["install", "--file", "set.yaml", "--require-signature", "--yes"]
        )
    assert result.exit_code == 1
    assert "bad sig" in result.output
    mock_load.assert_not_called()
