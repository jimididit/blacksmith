"""Structured outcomes for package install/update operations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Optional


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
