"""Structured outcomes for package install/update operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, List, Optional


class PackageStatus(str, Enum):
    OK = "ok"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PackageOutcome:
    """Result of one package action."""

    package_name: str
    package_id: str
    manager: str
    action: str  # install | reinstall | update | skip
    status: PackageStatus
    message: Optional[str] = None


@dataclass
class InstallRunResult:
    """Aggregate result of an install or apply run."""

    ok: bool
    outcomes: List[PackageOutcome] = field(default_factory=list)
    changed: int = 0
    skipped: int = 0
    failed: int = 0
    cancelled: bool = False
    back: bool = False

    def exit_code_install(self) -> int:
        """Legacy install semantics: 0 success, 1 failure/cancel."""
        if self.back:
            return 0
        if self.cancelled:
            return 1
        return 0 if self.ok else 1

    def exit_code_apply(self) -> int:
        """
        Apply semantics:
        0 = already compliant (no changes, no failures)
        2 = changed at least one package, no failures
        1 = failures or cancelled
        """
        if self.back:
            return 0
        if self.cancelled or self.failed or not self.ok:
            return 1
        if self.changed:
            return 2
        return 0


def summarize_outcomes(outcomes: Iterable[PackageOutcome]) -> dict:
    """Count outcomes by status."""
    summary = {"ok": 0, "failed": 0, "skipped": 0}
    for outcome in outcomes:
        if outcome.status == PackageStatus.OK:
            summary["ok"] += 1
        elif outcome.status == PackageStatus.FAILED:
            summary["failed"] += 1
        elif outcome.status == PackageStatus.SKIPPED:
            summary["skipped"] += 1
    return summary
