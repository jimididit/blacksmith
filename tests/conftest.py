"""Shared pytest fixtures."""

import pytest


@pytest.fixture(autouse=True)
def _sandbox_audit_log(monkeypatch, tmp_path):
    """Keep audit writes inside tmp_path so tests never touch the real log."""
    monkeypatch.setattr(
        "blacksmith.audit.log.default_audit_log_path",
        lambda: tmp_path / "audit-sandbox" / "audit.jsonl",
    )
