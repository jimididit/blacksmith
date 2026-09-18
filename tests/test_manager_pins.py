from blacksmith.package_managers.scoop import ScoopManager
from blacksmith.package_managers.snap import SnapManager


def test_default_managers_do_not_support_pins():
    assert ScoopManager().supports_version_pins() is False
    assert SnapManager().supports_version_pins() is False
    assert ScoopManager().get_installed_version("git") is None
