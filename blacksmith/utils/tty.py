"""TTY / non-interactive session helpers."""

from __future__ import annotations

import sys
from typing import Optional, Tuple


def stdin_is_tty() -> bool:
    """Return True if stdin is an interactive terminal."""
    try:
        return sys.stdin.isatty()
    except Exception:
        return False


def require_tty_or_yes(
    assume_yes: bool,
    *,
    dry_run: bool = False,
) -> Tuple[bool, Optional[str]]:
    """
    Non-interactive installs must pass --yes (or use --dry-run).

    Returns:
        (ok, error_message)
    """
    if dry_run or assume_yes or stdin_is_tty():
        return True, None
    return (
        False,
        "Non-interactive session detected. Re-run with --yes to confirm, "
        "or --dry-run to print the plan without installing.",
    )
