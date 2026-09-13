"""Append-only audit JSONL writer."""

from __future__ import annotations

import getpass
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable, List, Optional

from blacksmith.audit.paths import default_audit_log_path
from blacksmith.package_managers.results import PackageOutcome, PackageStatus

MUTATE_ACTIONS = frozenset({"install", "reinstall", "update", "uninstall"})
_TRUTHY = frozenset({"1", "true", "yes"})


def audit_disabled(no_audit: bool = False) -> bool:
    if no_audit:
        return True
    raw = os.environ.get("BLACKSMITH_NO_AUDIT", "").strip().lower()
    return raw in _TRUTHY


def filter_auditable(outcomes: Iterable[PackageOutcome]) -> List[PackageOutcome]:
    out: List[PackageOutcome] = []
    for outcome in outcomes:
        if outcome.action not in MUTATE_ACTIONS:
            continue
        if outcome.status not in (PackageStatus.OK, PackageStatus.FAILED):
            continue
        out.append(outcome)
    return out


def file_sha256(path: Path) -> Optional[str]:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def _username() -> str:
    try:
        return getpass.getuser()
    except Exception:
        return "unknown"


def record_audit(
    *,
    command: str,
    outcomes: Iterable[PackageOutcome],
    exit_code: int,
    set_name: Optional[str] = None,
    config_path: Optional[str] = None,
    dry_run: bool = False,
    no_audit: bool = False,
    log_path: Optional[Path] = None,
    warn: Optional[Callable[[str], None]] = None,
) -> Optional[str]:
    """Append run and package lines if warranted. Return run ID or None."""
    if dry_run or audit_disabled(no_audit):
        return None
    auditable = filter_auditable(outcomes)
    if not auditable:
        return None

    run_id = uuid.uuid4().hex

    # Path resolution, serialization, and the write all fail open: a broken
    # audit log must never change the exit code of a mutate command.
    try:
        path = log_path or default_audit_log_path()
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        config_hash = file_sha256(Path(config_path)) if config_path else None

        run_obj = {
            "type": "run",
            "ts": timestamp,
            "run_id": run_id,
            "command": command,
            "set": set_name,
            "config_path": config_path,
            "config_hash": config_hash,
            "user": _username(),
            "exit": int(exit_code),
        }
        lines = [json.dumps(run_obj, separators=(",", ":"))]
        for outcome in auditable:
            lines.append(
                json.dumps(
                    {
                        "type": "package",
                        "ts": timestamp,
                        "run_id": run_id,
                        "name": outcome.package_name,
                        "id": outcome.package_id,
                        "manager": outcome.manager,
                        "action": outcome.action,
                        "status": (
                            outcome.status.value
                            if isinstance(outcome.status, PackageStatus)
                            else str(outcome.status)
                        ),
                        "exit": None,
                    },
                    separators=(",", ":"),
                )
            )

        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as file:
            file.write("\n".join(lines) + "\n")
            file.flush()
    except (OSError, TypeError, ValueError, RuntimeError) as exc:
        if warn:
            warn(f"Audit log write failed: {exc}")
        return None
    return run_id
