import json
from unittest.mock import patch

from click.testing import CliRunner

from blacksmith.cli import cli
from blacksmith.gallery.schema import GalleryEntry, GalleryIndex


def _index_one():
    return GalleryIndex(
        version=1,
        entries=[
            GalleryEntry(
                id="dfir-triage",
                title="DFIR triage",
                description="desc",
                url="https://example.com/dfir.yaml",
                signature_url=None,
                os=["linux", "windows"],
                tags=["dfir"],
                provenance="official",
            )
        ],
    )


@patch("blacksmith.cli.load_index", return_value=_index_one())
def test_gallery_list(mock_load):
    runner = CliRunner()
    result = runner.invoke(cli, ["gallery", "list"])
    assert result.exit_code == 0, result.output
    assert "dfir-triage" in result.output
    mock_load.assert_called_once_with(refresh=False)


@patch("blacksmith.cli.load_index", return_value=_index_one())
def test_gallery_info(mock_load):
    runner = CliRunner()
    result = runner.invoke(cli, ["gallery", "info", "dfir-triage"])
    assert result.exit_code == 0
    assert "https://example.com/dfir.yaml" in result.output
    mock_load.assert_called_once_with(refresh=False)


@patch("blacksmith.cli.load_index", return_value=_index_one())
def test_gallery_info_refresh(mock_load):
    runner = CliRunner()
    result = runner.invoke(cli, ["gallery", "info", "dfir-triage", "--refresh"])
    assert result.exit_code == 0, result.output
    mock_load.assert_called_once_with(refresh=True)


@patch("blacksmith.cli.load_index", return_value=_index_one())
def test_gallery_info_unknown(mock_load):
    runner = CliRunner()
    result = runner.invoke(cli, ["gallery", "info", "nope"])
    assert result.exit_code == 1
    assert "not found" in result.output.lower() or "Unknown" in result.output


@patch("blacksmith.cli.load_index", return_value=_index_one())
@patch("blacksmith.cli.install_packages")
@patch("blacksmith.cli.load_custom_config")
@patch("blacksmith.cli.fetch_set_url")
def test_gallery_install_uses_entry_url(
    mock_fetch, mock_load_cfg, mock_install_pkgs, mock_load_idx, tmp_path
):
    from blacksmith.package_managers.results import InstallRunResult
    from blacksmith.trust.fetch import FetchedSet

    path = tmp_path / "r.yaml"
    path.write_text("name: r\npackages: []\n", encoding="utf-8")
    mock_fetch.return_value = FetchedSet(
        path=path, final_url="https://example.com/dfir.yaml", sha256="ab" * 32
    )
    mock_load_cfg.return_value = {"name": "r", "packages": []}
    mock_install_pkgs.return_value = InstallRunResult(
        ok=True, outcomes=[], changed=0, skipped=0, failed=0, dry_run=True
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["gallery", "install", "dfir-triage", "--yes", "--dry-run"],
    )
    assert result.exit_code == 0, result.output
    assert mock_fetch.call_args.args[0] == "https://example.com/dfir.yaml"


@patch("blacksmith.cli.load_index", return_value=_index_one())
def test_gallery_list_json(mock_load):
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "gallery", "list"])
    assert result.exit_code == 0
    body = json.loads(result.stdout.strip())
    assert body["ok"] is True
    assert body["data"]["entries"][0]["id"] == "dfir-triage"


@patch("blacksmith.cli.load_index", return_value=_index_one())
@patch("blacksmith.cli.install_packages")
@patch("blacksmith.cli.load_custom_config")
@patch("blacksmith.cli.fetch_set_url")
def test_gallery_apply_uses_entry_url(
    mock_fetch, mock_load_cfg, mock_install_pkgs, mock_load_idx, tmp_path
):
    from blacksmith.package_managers.results import InstallRunResult
    from blacksmith.trust.fetch import FetchedSet

    path = tmp_path / "r.yaml"
    path.write_text("name: r\npackages: []\n", encoding="utf-8")
    mock_fetch.return_value = FetchedSet(
        path=path, final_url="https://example.com/dfir.yaml", sha256="ab" * 32
    )
    mock_load_cfg.return_value = {"name": "r", "packages": []}
    mock_install_pkgs.return_value = InstallRunResult(
        ok=True, outcomes=[], changed=0, skipped=0, failed=0, dry_run=True
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["gallery", "apply", "dfir-triage", "--yes", "--dry-run"],
    )
    assert result.exit_code == 0, result.output
    assert mock_fetch.call_args.args[0] == "https://example.com/dfir.yaml"


@patch("blacksmith.cli.load_index", return_value=_index_one())
@patch("blacksmith.cli.cleanup_fetched")
@patch("blacksmith.cli.fetch_set_url")
def test_gallery_validate_uses_entry_url(
    mock_fetch, mock_cleanup, mock_load_idx, tmp_path
):
    from blacksmith.trust.fetch import FetchedSet

    path = tmp_path / "r.yaml"
    path.write_text("name: r\npackages: []\n", encoding="utf-8")
    fetched = FetchedSet(
        path=path, final_url="https://example.com/dfir.yaml", sha256="ab" * 32
    )
    mock_fetch.return_value = fetched

    runner = CliRunner()
    result = runner.invoke(cli, ["gallery", "validate", "dfir-triage"])
    assert result.exit_code == 0, result.output
    assert mock_fetch.call_args.args[0] == "https://example.com/dfir.yaml"
    mock_cleanup.assert_called_once_with(fetched)
