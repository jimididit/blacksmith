"""Test version pin semantics in plan and install."""

from unittest.mock import Mock, patch
from blacksmith.cli import build_install_plan, install_packages
from blacksmith.package_managers.results import PackageStatus


def _mgr(name="apt", pins=True):
    """Create a mock manager with version pin support."""
    m = Mock()
    m.name = name
    m.supports_version_pins = Mock(return_value=pins)
    m.is_installed = Mock(return_value=False)
    m.get_installed_version = Mock(return_value=None)
    m.install = Mock(return_value=True)
    return m


@patch("blacksmith.cli.find_manager_for_package")
def test_plan_pin_unsupported(mock_find):
    """Pinned package + unsupported manager → unavailable/pin_unsupported."""
    mgr = _mgr(name="scoop", pins=False)
    mock_find.return_value = (mgr, "git|2.40.0")
    plan = build_install_plan(
        {"packages": [{"name": "Git", "managers": {"scoop": "git|2.40.0"}}]},
        [mgr],
        check_installed=True,
    )
    assert plan[0].action == "unavailable"
    assert plan[0].message == "pin_unsupported"


@patch("blacksmith.cli.find_manager_for_package")
def test_plan_version_match_skips(mock_find):
    """Pinned + matching installed version → skip."""
    mgr = _mgr()
    mgr.get_installed_version = Mock(return_value="2.40.0")
    mock_find.return_value = (mgr, "git|2.40.0")
    plan = build_install_plan(
        {"packages": [{"name": "Git", "managers": {"apt": "git|2.40.0"}}]},
        [mgr],
        check_installed=True,
    )
    assert plan[0].action == "skip"
    assert plan[0].message == "already installed"


@patch("blacksmith.cli.find_manager_for_package")
def test_plan_version_mismatch_fails(mock_find):
    """Pinned + version mismatch → unavailable/version_mismatch."""
    mgr = _mgr()
    mgr.get_installed_version = Mock(return_value="2.39.0")
    mock_find.return_value = (mgr, "git|2.40.0")
    plan = build_install_plan(
        {"packages": [{"name": "Git", "managers": {"apt": "git|2.40.0"}}]},
        [mgr],
        check_installed=True,
    )
    assert plan[0].action == "unavailable"
    assert plan[0].message == "version_mismatch"


@patch("blacksmith.cli.find_manager_for_package")
def test_plan_version_unknown(mock_find):
    """Pinned + present but version unknown → unavailable/version_unknown."""
    mgr = _mgr()
    mgr.get_installed_version = Mock(return_value=None)
    mgr.is_installed = Mock(return_value=True)
    mock_find.return_value = (mgr, "git|2.40.0")
    plan = build_install_plan(
        {"packages": [{"name": "Git", "managers": {"apt": "git|2.40.0"}}]},
        [mgr],
        check_installed=True,
    )
    assert plan[0].action == "unavailable"
    assert plan[0].message == "version_unknown"


@patch("blacksmith.cli.find_manager_for_package")
def test_plan_pinned_not_installed_proceeds(mock_find):
    """Pinned + not installed → install."""
    mgr = _mgr()
    mgr.get_installed_version = Mock(return_value=None)
    mgr.is_installed = Mock(return_value=False)
    mock_find.return_value = (mgr, "git|2.40.0")
    plan = build_install_plan(
        {"packages": [{"name": "Git", "managers": {"apt": "git|2.40.0"}}]},
        [mgr],
        check_installed=True,
    )
    assert plan[0].action == "install"


@patch("blacksmith.cli.find_manager_for_package")
def test_plan_unpinned_still_uses_bare_presence(mock_find):
    """Unpinned package still uses is_installed(name)."""
    mgr = _mgr()
    mgr.is_installed = Mock(return_value=True)
    mock_find.return_value = (mgr, "git")
    plan = build_install_plan(
        {"packages": [{"name": "Git", "managers": {"apt": "git"}}]},
        [mgr],
        check_installed=True,
    )
    assert plan[0].action == "skip"
    assert plan[0].message == "already installed"
    mgr.get_installed_version.assert_not_called()


@patch("blacksmith.cli.create_progress")
@patch("blacksmith.cli.show_installation_summary", return_value=True)
@patch("blacksmith.cli.detect_available_managers")
@patch("blacksmith.cli.find_manager_for_package")
@patch("blacksmith.cli.detect_os", return_value="linux")
def test_apply_pin_mismatch_does_not_install(
    _os, mock_find, mock_detect, _summary, mock_progress
):
    """Apply with version mismatch fails without calling install."""
    mgr = _mgr()
    mgr.get_installed_version = Mock(return_value="1.0.0")
    mgr.is_installed = Mock(return_value=True)
    mock_detect.return_value = [mgr]
    mock_find.return_value = (mgr, "git|2.0.0")
    progress = Mock()
    progress.__enter__ = Mock(return_value=progress)
    progress.__exit__ = Mock(return_value=False)
    progress.add_task = Mock(return_value=1)
    progress.update = Mock()
    mock_progress.return_value = progress

    result = install_packages(
        {"name": "t", "packages": [{"name": "Git", "managers": {"apt": "git|2.0.0"}}]},
        assume_yes=True,
        apply_mode=True,
    )
    assert result.ok is False
    assert any(o.message == "version_mismatch" for o in result.outcomes)
    mgr.install.assert_not_called()


@patch("blacksmith.cli.create_progress")
@patch("blacksmith.cli.show_installation_summary", return_value=True)
@patch("blacksmith.cli.detect_available_managers")
@patch("blacksmith.cli.find_manager_for_package")
@patch("blacksmith.cli.detect_os", return_value="linux")
def test_apply_pin_unsupported_does_not_install(
    _os, mock_find, mock_detect, _summary, mock_progress
):
    """Apply with unsupported pin fails without calling install."""
    mgr = _mgr(name="scoop", pins=False)
    mock_detect.return_value = [mgr]
    mock_find.return_value = (mgr, "git|2.0.0")
    progress = Mock()
    progress.__enter__ = Mock(return_value=progress)
    progress.__exit__ = Mock(return_value=False)
    mock_progress.return_value = progress

    result = install_packages(
        {"name": "t", "packages": [{"name": "Git", "managers": {"scoop": "git|2.0.0"}}]},
        assume_yes=True,
        apply_mode=True,
    )
    assert result.ok is False
    assert any(o.message == "pin_unsupported" for o in result.outcomes)
    mgr.install.assert_not_called()


@patch("blacksmith.cli.create_progress")
@patch("blacksmith.cli.show_installation_summary", return_value=True)
@patch("blacksmith.cli.detect_available_managers")
@patch("blacksmith.cli.find_manager_for_package")
@patch("blacksmith.cli.detect_os", return_value="linux")
def test_install_pinned_post_verify_version(
    _os, mock_find, mock_detect, _summary, mock_progress
):
    """Install pinned package verifies version after install."""
    mgr = _mgr()
    mgr.get_installed_version = Mock(side_effect=[None, "2.0.0"])  # Before and after install
    mgr.is_installed = Mock(return_value=False)
    mock_detect.return_value = [mgr]
    mock_find.return_value = (mgr, "git|2.0.0")
    progress = Mock()
    progress.__enter__ = Mock(return_value=progress)
    progress.__exit__ = Mock(return_value=False)
    progress.add_task = Mock(return_value=1)
    progress.update = Mock()
    mock_progress.return_value = progress

    result = install_packages(
        {"name": "t", "packages": [{"name": "Git", "managers": {"apt": "git|2.0.0"}}]},
        assume_yes=True,
        apply_mode=True,
    )
    assert result.ok is True
    mgr.install.assert_called_once_with(["git|2.0.0"])
    assert mgr.get_installed_version.call_count == 2


@patch("blacksmith.cli.create_progress")
@patch("blacksmith.cli.show_installation_summary", return_value=True)
@patch("blacksmith.cli.detect_available_managers")
@patch("blacksmith.cli.find_manager_for_package")
@patch("blacksmith.cli.detect_os", return_value="linux")
def test_install_pinned_post_verify_fails_on_mismatch(
    _os, mock_find, mock_detect, _summary, mock_progress
):
    """Install pinned package fails if post-verify finds version mismatch."""
    mgr = _mgr()
    mgr.get_installed_version = Mock(side_effect=[None, "1.9.0"])  # Wrong version after install
    mgr.is_installed = Mock(return_value=False)
    mock_detect.return_value = [mgr]
    mock_find.return_value = (mgr, "git|2.0.0")
    progress = Mock()
    progress.__enter__ = Mock(return_value=progress)
    progress.__exit__ = Mock(return_value=False)
    progress.add_task = Mock(return_value=1)
    progress.update = Mock()
    mock_progress.return_value = progress

    result = install_packages(
        {"name": "t", "packages": [{"name": "Git", "managers": {"apt": "git|2.0.0"}}]},
        assume_yes=True,
        apply_mode=True,
    )
    assert result.ok is False
    mgr.install.assert_called_once()
    assert any(o.message == "version_mismatch" for o in result.outcomes)
