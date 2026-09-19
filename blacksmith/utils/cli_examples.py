"""Click help epilog helpers for consistent Examples sections."""

from __future__ import annotations


def examples_epilog(*lines: str) -> str:
    """Build a Click ``epilog`` block titled Examples.

    Each line should be a full invocation starting with ``blacksmith``.
    Uses Click's ``\\b`` marker so example lines are not rewrapped into one line.
    """
    if not lines:
        raise ValueError("examples_epilog requires at least one example line")
    body = "\n".join(f"  {line}" for line in lines)
    return f"Examples:\n\n\b\n{body}\n"
