"""Tests for minisign sign_set helper and blacksmith sign CLI."""

from pathlib import Path
from unittest.mock import Mock, patch

from click.testing import CliRunner

from blacksmith.cli import cli
from blacksmith.trust.sign import sign_set
from blacksmith.trust.verify import default_signature_path


def test_default_signature_path_used_when_no_output():
    assert default_signature_path(Path("lab.yaml")) == Path("lab.yaml.minisig")


@patch("blacksmith.trust.sign.shutil.which", return_value=None)
def test_sign_missing_minisign(_which, tmp_path):
    cfg = tmp_path / "set.yaml"
    cfg.write_text("name: t\npackages: []\n", encoding="utf-8")
    result = sign_set(cfg)
    assert result.ok is False
    assert "minisign not found" in result.message


def test_sign_missing_config(tmp_path):
    result = sign_set(tmp_path / "nope.yaml")
    assert result.ok is False
    assert "not found" in result.message.lower()


def test_sign_missing_secret_key(tmp_path):
    cfg = tmp_path / "set.yaml"
    cfg.write_text("name: t\npackages: []\n", encoding="utf-8")
    result = sign_set(cfg, secret_key=tmp_path / "missing.key")
    assert result.ok is False
    assert "Secret key not found" in result.message


@patch("blacksmith.trust.sign.shutil.which", return_value="/usr/bin/minisign")
@patch("blacksmith.trust.sign.subprocess.run")
def test_sign_success_default_sig_path(mock_run, _which, tmp_path):
    cfg = tmp_path / "set.yaml"
    cfg.write_text("name: t\npackages: []\n", encoding="utf-8")
    sig = tmp_path / "set.yaml.minisig"

    def _fake_run(cmd, **kwargs):
        assert kwargs.get("shell") is False
        assert cmd[0] == "/usr/bin/minisign"
        assert cmd[1] == "-Sm"
        assert str(cfg.resolve()) in cmd
        assert "-x" in cmd
        assert str(sig.resolve()) in cmd
        assert "-s" not in cmd
        sig.write_text("sig\n", encoding="utf-8")
        return Mock(returncode=0)

    mock_run.side_effect = _fake_run
    result = sign_set(cfg)
    assert result.ok is True
    assert result.signature_path == sig.resolve()
    assert "Signed" in result.message


@patch("blacksmith.trust.sign.shutil.which", return_value="/usr/bin/minisign")
@patch("blacksmith.trust.sign.subprocess.run")
def test_sign_with_secret_key_and_custom_output(mock_run, _which, tmp_path):
    cfg = tmp_path / "set.yaml"
    cfg.write_text("name: t\npackages: []\n", encoding="utf-8")
    key = tmp_path / "minisign.key"
    key.write_text("key\n", encoding="utf-8")
    out = tmp_path / "custom.minisig"

    def _fake_run(cmd, **kwargs):
        assert "-s" in cmd
        assert str(key.resolve()) in cmd
        assert str(out.resolve()) in cmd
        out.write_text("sig\n", encoding="utf-8")
        return Mock(returncode=0)

    mock_run.side_effect = _fake_run
    result = sign_set(cfg, signature_path=out, secret_key=key)
    assert result.ok is True
    assert result.signature_path == out.resolve()


@patch("blacksmith.trust.sign.shutil.which", return_value="/usr/bin/minisign")
@patch("blacksmith.trust.sign.subprocess.run")
def test_sign_nonzero_exit(mock_run, _which, tmp_path):
    cfg = tmp_path / "set.yaml"
    cfg.write_text("name: t\npackages: []\n", encoding="utf-8")
    mock_run.return_value = Mock(returncode=1)
    result = sign_set(cfg)
    assert result.ok is False
    assert "exit 1" in result.message


@patch("blacksmith.cli.sign_set")
def test_cli_sign_success(mock_sign, tmp_path):
    cfg = tmp_path / "set.yaml"
    cfg.write_text("name: t\npackages: []\n", encoding="utf-8")
    sig = tmp_path / "set.yaml.minisig"
    mock_sign.return_value = Mock(
        ok=True, message=f"Signed {cfg.name} -> {sig}", signature_path=sig
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["sign", str(cfg)])
    assert result.exit_code == 0, result.output
    assert "Signed" in result.output
    mock_sign.assert_called_once()


@patch("blacksmith.cli.sign_set")
def test_cli_sign_fails_closed(mock_sign, tmp_path):
    cfg = tmp_path / "set.yaml"
    cfg.write_text("name: t\npackages: []\n", encoding="utf-8")
    mock_sign.return_value = Mock(ok=False, message="minisign not found", signature_path=None)
    runner = CliRunner()
    result = runner.invoke(cli, ["sign", str(cfg)])
    assert result.exit_code == 1
    assert "minisign not found" in result.output


def test_cli_sign_json_unsupported(tmp_path):
    cfg = tmp_path / "set.yaml"
    cfg.write_text("name: t\npackages: []\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "sign", str(cfg)])
    assert result.exit_code == 2
