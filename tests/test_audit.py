"""Tests for the audit_log core module."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from ai_os_nexus.core.audit_log import AuditEvent, AuditLog, _mask


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def audit(tmp_path: Path) -> AuditLog:
    """Return a fresh AuditLog backed by a temporary DB file."""
    return AuditLog(db_path=tmp_path / "test_audit.db")


# ---------------------------------------------------------------------------
# _mask utility
# ---------------------------------------------------------------------------

def test_mask_sensitive_fields():
    raw = {"content": "super secret", "mode": "PRIVATE", "key": "abc123"}
    masked = _mask(raw)
    assert masked["content"].startswith("[REDACTED")
    assert masked["key"].startswith("[REDACTED")
    assert masked["mode"] == "PRIVATE"


def test_mask_empty_dict():
    assert _mask({}) == {}


def test_mask_none_value():
    raw = {"content": None}
    masked = _mask(raw)
    assert masked["content"] == "[REDACTED len=0]"


# ---------------------------------------------------------------------------
# AuditLog.log
# ---------------------------------------------------------------------------

def test_log_returns_id(audit: AuditLog):
    rid = audit.log(AuditEvent.MEMORY_STORE, actor="user-1", target="mem-abc", status="ok")
    assert rid and len(rid) == 36  # UUID format


def test_log_stores_event(audit: AuditLog):
    audit.log(AuditEvent.SAFETY_OVERRIDE, actor="admin-1", target="act-xyz", status="override",
              metadata={"reason": "testing"})
    records = audit.recent(limit=10)
    assert len(records) == 1
    r = records[0]
    assert r["event"] == AuditEvent.SAFETY_OVERRIDE.value
    assert r["actor"] == "admin-1"
    assert r["target"] == "act-xyz"
    assert r["status"] == "override"


def test_log_masks_sensitive_metadata(audit: AuditLog):
    audit.log(
        AuditEvent.MEMORY_STORE, actor="user-2",
        metadata={"content": "very private data", "mode": "PRIVATE"}
    )
    records = audit.recent(limit=1)
    detail = records[0].get("detail", "")
    assert "very private data" not in detail
    assert "REDACTED" in detail


def test_log_non_sensitive_metadata_preserved(audit: AuditLog):
    audit.log(
        AuditEvent.MEMORY_STORE, actor="user-3",
        metadata={"mode": "PRIVATE", "exported_count": 5}
    )
    records = audit.recent(limit=1)
    detail = records[0].get("detail", "")
    assert "PRIVATE" in detail
    assert "5" in detail


# ---------------------------------------------------------------------------
# AuditLog.recent
# ---------------------------------------------------------------------------

def test_recent_returns_newest_first(audit: AuditLog):
    audit.log(AuditEvent.MEMORY_STORE, actor="u1", status="ok")
    time.sleep(0.01)
    audit.log(AuditEvent.MEMORY_DELETE, actor="u2", status="ok")
    records = audit.recent(limit=10)
    assert records[0]["event"] == AuditEvent.MEMORY_DELETE.value
    assert records[1]["event"] == AuditEvent.MEMORY_STORE.value


def test_recent_limit(audit: AuditLog):
    for i in range(10):
        audit.log(AuditEvent.API_ASK, actor=f"user-{i}", status="ok")
    records = audit.recent(limit=3)
    assert len(records) == 3


def test_recent_event_filter(audit: AuditLog):
    audit.log(AuditEvent.MEMORY_STORE, actor="u1", status="ok")
    audit.log(AuditEvent.MEMORY_DELETE, actor="u2", status="ok")
    audit.log(AuditEvent.MEMORY_STORE, actor="u3", status="ok")

    stores = audit.recent(limit=50, event_filter=AuditEvent.MEMORY_STORE.value)
    assert all(r["event"] == AuditEvent.MEMORY_STORE.value for r in stores)
    assert len(stores) == 2


# ---------------------------------------------------------------------------
# AuditLog.compliance_stats
# ---------------------------------------------------------------------------

def test_compliance_stats_empty(audit: AuditLog):
    stats = audit.compliance_stats()
    assert stats["total_events"] == 0
    assert stats["events_last_24h"] == 0
    assert stats["by_event"] == {}
    assert "retention_policy" in stats


def test_compliance_stats_with_events(audit: AuditLog):
    audit.log(AuditEvent.MEMORY_STORE, actor="u1", status="ok")
    audit.log(AuditEvent.MEMORY_STORE, actor="u2", status="ok")
    audit.log(AuditEvent.SAFETY_OVERRIDE, actor="admin", status="override")

    stats = audit.compliance_stats()
    assert stats["total_events"] == 3
    assert stats["events_last_24h"] == 3
    assert stats["by_event"][AuditEvent.MEMORY_STORE.value] == 2
    assert stats["by_event"][AuditEvent.SAFETY_OVERRIDE.value] == 1
