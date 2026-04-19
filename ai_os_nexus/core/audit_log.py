"""
Audit Log — append-only, privacy-respecting audit trail for critical actions.

Logs: safety overrides, memory ops (store/delete/export), consent changes,
      admin actions, and any custom events registered by callers.

Design principles:
- Append-only SQLite table (no UPDATE/DELETE queries).
- Sensitive field values are masked before persistence.
- Provides aggregate compliance stats without leaking payloads.
"""

from __future__ import annotations

import logging
import sqlite3
import time
import uuid
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DB_PATH = Path("data/audit.db")

# Fields whose values must be masked in the log
_SENSITIVE_FIELDS = frozenset(
    {
        "content",
        "password",
        "token",
        "secret",
        "key",
        "api_key",
        "authorization",
        "query",
    }
)


class AuditEvent(str, Enum):
    # Memory operations
    MEMORY_STORE = "memory.store"
    MEMORY_DELETE = "memory.delete"
    MEMORY_DELETE_ALL = "memory.delete_all"
    MEMORY_EXPORT = "memory.export"
    # Consent
    CONSENT_GRANT = "consent.grant"
    CONSENT_REVOKE = "consent.revoke"
    CONSENT_CHECK = "consent.check"
    # Safety / admin
    SAFETY_OVERRIDE = "safety.override"
    SAFETY_BLOCKED = "safety.blocked"
    ADMIN_PURGE = "admin.purge_expired"
    ADMIN_EXPORT_DATASET = "admin.export_dataset"
    # General
    API_ASK = "api.ask"
    API_ERROR = "api.error"


def _mask(metadata: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow copy of *metadata* with sensitive values masked."""
    masked: dict[str, Any] = {}
    for k, v in metadata.items():
        if k.lower() in _SENSITIVE_FIELDS:
            # Keep length hint, hide value
            length = len(str(v)) if v is not None else 0
            masked[k] = f"[REDACTED len={length}]"
        else:
            masked[k] = v
    return masked


class AuditLog:
    """Thread-safe, append-only audit log backed by SQLite."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._setup()

    def _setup(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_log (
                    id         TEXT PRIMARY KEY,
                    event      TEXT NOT NULL,
                    actor      TEXT NOT NULL,
                    target     TEXT,
                    status     TEXT NOT NULL,
                    detail     TEXT,
                    timestamp  REAL NOT NULL
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_event ON audit_log(event)"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_log(actor)"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(timestamp)"
            )

    # ------------------------------------------------------------------
    def log(
        self,
        event: AuditEvent | str,
        actor: str,
        *,
        target: str | None = None,
        status: str = "ok",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Append one audit record.

        Parameters
        ----------
        event:    AuditEvent constant or free-form string.
        actor:    Who performed the action (user_id, admin_id, 'system').
        target:   The resource being acted on (memory_id, sensor_id, …).
        status:   'ok', 'blocked', 'error', 'override', etc.
        metadata: Additional context — sensitive fields are auto-masked.

        Returns the generated audit record ID.
        """
        record_id = str(uuid.uuid4())
        safe_meta: dict[str, Any] = _mask(metadata or {})
        import json

        detail = json.dumps(safe_meta, default=str) if safe_meta else None

        with self._conn:
            self._conn.execute(
                """
                INSERT INTO audit_log (id, event, actor, target, status, detail, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    event.value if hasattr(event, "value") else str(event),
                    str(actor),
                    target,
                    status,
                    detail,
                    time.time(),
                ),
            )
        logger.info(
            "AUDIT event=%s actor=%s target=%s status=%s",
            event.value if hasattr(event, "value") else event,
            actor,
            target,
            status,
        )
        return record_id

    # ------------------------------------------------------------------
    def recent(self, limit: int = 50, event_filter: str | None = None) -> list[dict]:
        """Return recent audit records, newest first."""
        if event_filter:
            cur = self._conn.execute(
                "SELECT id, event, actor, target, status, detail, timestamp "
                "FROM audit_log WHERE event = ? ORDER BY timestamp DESC LIMIT ?",
                (event_filter, limit),
            )
        else:
            cur = self._conn.execute(
                "SELECT id, event, actor, target, status, detail, timestamp "
                "FROM audit_log ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
        rows = cur.fetchall()
        return [
            {
                "id": r[0],
                "event": r[1],
                "actor": r[2],
                "target": r[3],
                "status": r[4],
                "detail": r[5],
                "timestamp": r[6],
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    def compliance_stats(self) -> dict[str, Any]:
        """
        Return aggregate compliance statistics — counts only, no payloads.
        Safe to expose via an admin/compliance endpoint.
        """
        cur = self._conn.execute(
            "SELECT event, COUNT(*) FROM audit_log GROUP BY event ORDER BY COUNT(*) DESC"
        )
        by_event = {row[0]: row[1] for row in cur.fetchall()}

        cur2 = self._conn.execute("SELECT COUNT(*) FROM audit_log")
        total = cur2.fetchone()[0]

        # Oldest and newest timestamps
        cur3 = self._conn.execute(
            "SELECT MIN(timestamp), MAX(timestamp) FROM audit_log"
        )
        ts_min, ts_max = cur3.fetchone()

        # Count events in last 24 h
        cutoff = time.time() - 86400
        cur4 = self._conn.execute(
            "SELECT COUNT(*) FROM audit_log WHERE timestamp >= ?", (cutoff,)
        )
        last_24h = cur4.fetchone()[0]

        return {
            "total_events": total,
            "events_last_24h": last_24h,
            "by_event": by_event,
            "oldest_event_ts": ts_min,
            "newest_event_ts": ts_max,
            "retention_policy": "Audit logs are retained indefinitely. "
            "Configure data/audit.db backup per your retention policy.",
        }


# Module-level singleton — share across the app
_default_audit_log: AuditLog | None = None


def get_audit_log() -> AuditLog:
    """Return the module-level default AuditLog instance."""
    global _default_audit_log
    if _default_audit_log is None:
        _default_audit_log = AuditLog()
    return _default_audit_log
