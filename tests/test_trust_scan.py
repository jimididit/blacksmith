"""Unit tests for offline trust heuristics scan (L4.4)."""

from blacksmith.trust.scan import Finding, ScanResult, scan_set


def _pkg(name: str, **managers: str) -> dict:
    return {"name": name, "managers": dict(managers)}


def _config(*packages: dict, **top) -> dict:
    cfg = {"name": "Test", "packages": list(packages)}
    cfg.update(top)
    return cfg


def test_scan_clean_minimal_config():
    cfg = _config(_pkg("git", apt="git", winget="Git.Git"))
    result = scan_set(cfg)
    assert result.ok
    assert result.findings == []


def test_oversized_package_count():
    packages = [_pkg(f"tool-{i}", apt=f"pkg-{i}") for i in range(81)]
    result = scan_set(_config(*packages), max_packages=80)
    assert not result.ok
    codes = {f.code for f in result.findings}
    assert "oversized" in codes


def test_oversized_respects_custom_threshold():
    packages = [_pkg(f"tool-{i}", apt=f"pkg-{i}") for i in range(11)]
    result = scan_set(_config(*packages), max_packages=10)
    assert any(f.code == "oversized" for f in result.findings)


def test_denylist_hit(monkeypatch):
    bad_id = "evil.example.package"
    cfg = _config(_pkg("bad", winget=bad_id))
    result = scan_set(cfg, denylist=frozenset({bad_id.lower()}))
    assert any(f.code == "denylist" for f in result.findings)
    assert bad_id in result.findings[0].message or "denylist" in result.findings[0].message.lower()


def test_denylist_case_insensitive():
    cfg = _config(_pkg("x", apt="Bad.ID"))
    result = scan_set(cfg, denylist=frozenset({"bad.id"}))
    assert any(f.code == "denylist" for f in result.findings)


def test_manager_mix_without_managers_supported():
    mgrs = ("apt", "pacman", "yum", "dnf", "winget", "chocolatey", "scoop")
    packages = [_pkg(f"p{i}", **{mgrs[i]: f"id{i}"}) for i in range(len(mgrs))]
    result = scan_set(_config(*packages))
    assert any(f.code == "manager_mix" for f in result.findings)


def test_manager_mix_skipped_when_managers_supported_declared():
    mgrs = ("apt", "pacman", "yum", "dnf", "winget", "chocolatey", "scoop")
    packages = [_pkg(f"p{i}", **{mgrs[i]: f"id{i}"}) for i in range(len(mgrs))]
    cfg = _config(*packages, managers_supported=list(mgrs))
    result = scan_set(cfg)
    assert not any(f.code == "manager_mix" for f in result.findings)


def test_duplicate_names_conflicting_ids():
    cfg = _config(
        _pkg("git", apt="git"),
        _pkg("git", apt="git-core"),
    )
    result = scan_set(cfg)
    assert any(f.code == "duplicate" for f in result.findings)


def test_duplicate_names_same_ids_ok():
    cfg = _config(
        _pkg("git", apt="git"),
        _pkg("git", apt="git"),
    )
    result = scan_set(cfg)
    assert not any(f.code == "duplicate" for f in result.findings)


def test_junk_id_smell_long_encoded_id():
    cfg = _config(
        _pkg("x", winget="a" * 40),
    )
    result = scan_set(cfg)
    assert any(f.code == "junk_id" for f in result.findings)


def test_junk_id_smell_name_id_length_mismatch():
    cfg = _config(
        _pkg("git", winget="Publisher.Very.Long.Package.Identifier.Name.Here"),
    )
    result = scan_set(cfg)
    assert any(f.code == "junk_id" for f in result.findings)


def test_scan_result_finding_types():
    assert isinstance(scan_set(_config(_pkg("a", apt="a"))), ScanResult)
    f = Finding(code="test", message="msg")
    assert f.code == "test"
