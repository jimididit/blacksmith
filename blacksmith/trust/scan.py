"""Offline heuristics scan for custom/remote package sets (L4.4).

Advisory only — never implies the set is safe or trusted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

# Bundled denylist (lowercase package IDs). Empty in v1; tests may inject via scan_set().
_DENYLIST: FrozenSet[str] = frozenset()

# H2: distinct managers used across the set without managers_supported declared.
_MANAGER_MIX_THRESHOLD = 6

# H3: lightweight junk / mismatch thresholds.
_JUNK_MIN_ID_LEN = 32
_JUNK_PURE_ALNUM_MIN_LEN = 40
_NAME_ID_LENGTH_RATIO = 4


@dataclass(frozen=True)
class Finding:
    code: str
    message: str


@dataclass
class ScanResult:
    findings: List[Finding] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.findings


def scan_set(
    config: Dict[str, Any],
    *,
    max_packages: int = 80,
    denylist: Optional[FrozenSet[str]] = None,
) -> ScanResult:
    """Run offline heuristics on a parsed set config dict."""
    findings: List[Finding] = []
    packages = config.get("packages") or []
    if not isinstance(packages, list):
        packages = []

    _check_oversized(packages, max_packages, findings)
    _check_denylist(packages, denylist if denylist is not None else _DENYLIST, findings)
    _check_manager_mix(config, packages, findings)
    _check_duplicate_names(packages, findings)
    _check_junk_ids(packages, findings)

    return ScanResult(findings=findings)


def _check_oversized(packages: List[Any], max_packages: int, findings: List[Finding]) -> None:
    count = len(packages)
    if count > max_packages:
        findings.append(
            Finding(
                code="oversized",
                message=(
                    f"Set lists {count} packages (threshold {max_packages}); "
                    "large sets increase supply-chain exposure."
                ),
            )
        )


def _check_denylist(
    packages: List[Any],
    denylist: FrozenSet[str],
    findings: List[Finding],
) -> None:
    if not denylist:
        return
    hits: Set[str] = set()
    for package in packages:
        if not isinstance(package, dict):
            continue
        managers = package.get("managers") or {}
        if not isinstance(managers, dict):
            continue
        for pkg_id in managers.values():
            if isinstance(pkg_id, str) and pkg_id.lower() in denylist:
                hits.add(pkg_id)
    for pkg_id in sorted(hits):
        findings.append(
            Finding(
                code="denylist",
                message=f"Package ID matches denylist entry: {pkg_id}",
            )
        )


def _check_manager_mix(
    config: Dict[str, Any],
    packages: List[Any],
    findings: List[Finding],
) -> None:
    supported = config.get("managers_supported")
    if supported:
        return

    managers_used: Set[str] = set()
    for package in packages:
        if not isinstance(package, dict):
            continue
        mgrs = package.get("managers") or {}
        if not isinstance(mgrs, dict):
            continue
        for mgr_name in mgrs:
            if isinstance(mgr_name, str):
                managers_used.add(mgr_name.lower())

    if len(managers_used) > _MANAGER_MIX_THRESHOLD:
        findings.append(
            Finding(
                code="manager_mix",
                message=(
                    f"Set uses {len(managers_used)} distinct package managers "
                    f"without managers_supported (threshold {_MANAGER_MIX_THRESHOLD}); "
                    "may be an unfocused kitchen-sink dump."
                ),
            )
        )


def _check_duplicate_names(packages: List[Any], findings: List[Finding]) -> None:
    by_name: Dict[str, List[Tuple[Tuple[Tuple[str, str], ...], str]]] = {}
    for package in packages:
        if not isinstance(package, dict):
            continue
        name = package.get("name")
        if not isinstance(name, str):
            continue
        managers = package.get("managers") or {}
        if not isinstance(managers, dict):
            continue
        signature = tuple(
            sorted(
                (str(k).lower(), str(v))
                for k, v in managers.items()
                if isinstance(k, str) and isinstance(v, str)
            )
        )
        key = name.strip().lower()
        by_name.setdefault(key, []).append((signature, name))

    for key, entries in by_name.items():
        signatures = {sig for sig, _ in entries}
        if len(signatures) <= 1:
            continue
        display = entries[0][1]
        findings.append(
            Finding(
                code="duplicate",
                message=(
                    f"Duplicate package name {display!r} with conflicting manager IDs "
                    "across entries."
                ),
            )
        )


def _check_junk_ids(packages: List[Any], findings: List[Finding]) -> None:
    flagged: Set[str] = set()
    for package in packages:
        if not isinstance(package, dict):
            continue
        name = package.get("name")
        display_name = name if isinstance(name, str) else ""
        managers = package.get("managers") or {}
        if not isinstance(managers, dict):
            continue
        for mgr_name, pkg_id in managers.items():
            if not isinstance(pkg_id, str):
                continue
            if not _looks_like_junk_id(pkg_id, display_name):
                continue
            label = f"{display_name or 'unknown'} ({mgr_name}={pkg_id})"
            if label in flagged:
                continue
            flagged.add(label)
            findings.append(
                Finding(
                    code="junk_id",
                    message=(
                        f"Suspicious package ID shape for {label}; "
                        "verify the ID matches a real package."
                    ),
                )
            )


def _looks_like_junk_id(pkg_id: str, display_name: str) -> bool:
    base_id = pkg_id.split("|", 1)[0]
    if len(base_id) < _JUNK_MIN_ID_LEN:
        name_len = max(len(display_name.strip()), 1)
        if len(base_id) >= name_len * _NAME_ID_LENGTH_RATIO and len(base_id) >= 24:
            return True
        return False

    if len(base_id) >= _JUNK_PURE_ALNUM_MIN_LEN and re.fullmatch(
        r"[A-Za-z0-9]+", base_id
    ):
        return True

    name_len = max(len(display_name.strip()), 1)
    if len(base_id) >= name_len * _NAME_ID_LENGTH_RATIO and len(base_id) >= 24:
        if "." not in base_id and "/" not in base_id:
            return True
        if len(base_id) >= 40:
            return True

    return False
