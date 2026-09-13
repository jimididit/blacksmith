"""Stable JSON envelopes for blacksmith --json."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

import click

SCHEMA_VERSION = 1
JSON_COMMANDS = frozenset({"list", "info", "search", "install", "apply"})


def is_json_mode(ctx: Optional[click.Context] = None) -> bool:
    if ctx is None:
        ctx = click.get_current_context(silent=True)
    if ctx is None:
        return False
    obj = ctx.ensure_object(dict)
    return bool(obj.get("json"))


def _ok_flag(exit_code: int, apply_ok_exits: bool) -> bool:
    if exit_code == 0:
        return True
    if apply_ok_exits and exit_code == 2:
        return True
    return False


def envelope_ok(
    command: str,
    exit_code: int,
    data: Dict[str, Any],
    apply_ok_exits: bool = False,
) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "command": command,
        "ok": _ok_flag(exit_code, apply_ok_exits),
        "exit": int(exit_code),
        "data": data,
    }


def envelope_error(
    command: str, exit_code: int, code: str, message: str
) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "command": command,
        "ok": False,
        "exit": int(exit_code),
        "error": {"code": code, "message": message},
    }


def _dump(obj: Dict[str, Any]) -> None:
    click.echo(json.dumps(obj, ensure_ascii=False))


def emit_ok(
    *,
    command: str,
    exit_code: int,
    data: Dict[str, Any],
    apply_ok_exits: bool = False,
) -> None:
    _dump(envelope_ok(command, exit_code, data, apply_ok_exits=apply_ok_exits))


def emit_error(*, command: str, exit_code: int, code: str, message: str) -> None:
    _dump(envelope_error(command, exit_code, code, message))


def outcome_to_dict(outcome: Any) -> Dict[str, Any]:
    status = outcome.status
    status_val = status.value if hasattr(status, "value") else str(status)
    return {
        "name": outcome.package_name,
        "id": outcome.package_id,
        "manager": outcome.manager,
        "action": outcome.action,
        "status": status_val,
        "message": outcome.message,
    }


def run_result_data(
    *,
    dry_run: bool,
    set_name: Optional[str],
    config_path: Optional[str],
    result: Any,
) -> Dict[str, Any]:
    return {
        "dry_run": bool(dry_run),
        "set": set_name,
        "config_path": config_path,
        "summary": {
            "ok": bool(result.ok),
            "changed": int(result.changed),
            "skipped": int(result.skipped),
            "failed": int(result.failed),
            "cancelled": bool(result.cancelled),
        },
        "outcomes": [outcome_to_dict(o) for o in result.outcomes],
    }
