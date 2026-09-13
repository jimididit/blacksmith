"""Read recent events from the local audit JSONL file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional, Tuple

from blacksmith.audit.paths import default_audit_log_path


def load_events(
    path: Optional[Path] = None,
    last: int = 50,
) -> Tuple[List[dict], int]:
    """Return recent events in chronological order and the corrupt-line count."""
    audit_path = path or default_audit_log_path()
    last = max(last, 0)
    if not audit_path.is_file():
        return [], 0

    try:
        text = audit_path.read_text(encoding="utf-8")
    except OSError:
        return [], 0

    events: List[dict] = []
    corrupt = 0
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            corrupt += 1
            continue
        if isinstance(event, dict):
            events.append(event)

    if last == 0:
        return [], corrupt
    return events[-last:], corrupt
