"""
Consent Engine — granular per-operation consent tracking backed by SQLite.
Must be checked before any memory write or data-sharing operation.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = Path("data/consent.db")


@dataclass
class ConsentRecord:
    id: str
    user_id: str
    operation: str       # e.g. "memory.write.private", "data.share.anon"
    granted: bool
    granted_at: Optional[float]
    revoked_at: Optional[float]
    expires_at: Optional[float]
    context: dict


class ConsentEngine:
    """Manages granular consent per user per operation."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._setup()

    def _setup(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS consents (
                    id          TEXT PRIMARY KEY,
                    user_id     TEXT NOT NULL,
                    operation   TEXT NOT NULL,
                    granted     INTEGER NOT NULL DEFAULT 0,
                    granted_at  REAL,
                    revoked_at  REAL,
                    expires_at  REAL,
                    context_json TEXT DEFAULT '{}'
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_consent_user ON consents(user_id)"
            )
            self._conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_consent_user_op ON consents(user_id, operation)"
            )

    # ------------------------------------------------------------------
    def request_consent(
        self,
        user_id: str,
        operation: str,
        context: dict | None = None,
        expires_in: int | None = None,
    ) -> str:
        """Create a pending consent record. Returns consent ID."""
        consent_id = str(uuid.uuid4())
        expires_at = time.time() + expires_in if expires_in else None
        with self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO consents
                    (id, user_id, operation, granted, granted_at, revoked_at, expires_at, context_json)
                VALUES (?, ?, ?, 0, NULL, NULL, ?, ?)
                """,
                (consent_id, user_id, operation, expires_at, json.dumps(context or {})),
            )
        logger.debug("Consent requested: %s / %s", user_id, operation)
        return consent_id

    def grant_consent(self, user_id: str, operation: str) -> bool:
        """Grant consent for a user/operation pair."""
        with self._conn:
            cur = self._conn.execute(
                """
                UPDATE consents
                SET granted = 1, granted_at = ?, revoked_at = NULL
                WHERE user_id = ? AND operation = ?
                """,
                (time.time(), user_id, operation),
            )
        if cur.rowcount == 0:
            # Auto-create if not previously requested
            self.request_consent(user_id, operation)
            return self.grant_consent(user_id, operation)
        logger.info("Consent granted: %s / %s", user_id, operation)
        return True

    def revoke_consent(self, user_id: str, operation: str) -> bool:
        """Revoke a previously granted consent."""
        with self._conn:
            cur = self._conn.execute(
                """
                UPDATE consents
                SET granted = 0, revoked_at = ?
                WHERE user_id = ? AND operation = ?
                """,
                (time.time(), user_id, operation),
            )
        logger.info("Consent revoked: %s / %s", user_id, operation)
        return cur.rowcount > 0

    def check_consent(self, user_id: str, operation: str) -> bool:
        """Check if consent is currently active for user/operation."""
        now = time.time()
        cur = self._conn.execute(
            """
            SELECT granted, expires_at FROM consents
            WHERE user_id = ? AND operation = ?
            """,
            (user_id, operation),
        )
        row = cur.fetchone()
        if not row:
            return False
        granted, expires_at = row
        if not granted:
            return False
        if expires_at and now > expires_at:
            # Auto-expire
            self.revoke_consent(user_id, operation)
            return False
        return True

    def list_consents(self, user_id: str) -> list[ConsentRecord]:
        cur = self._conn.execute(
            """
            SELECT id, user_id, operation, granted, granted_at, revoked_at, expires_at, context_json
            FROM consents WHERE user_id = ?
            """,
            (user_id,),
        )
        return [
            ConsentRecord(
                id=r[0], user_id=r[1], operation=r[2], granted=bool(r[3]),
                granted_at=r[4], revoked_at=r[5], expires_at=r[6],
                context=json.loads(r[7] or "{}"),
            )
            for r in cur.fetchall()
        ]

    def ensure_consent(self, user_id: str, operation: str) -> None:
        """
        Raise PermissionError if consent is not granted.
        Call this before any sensitive operation.
        """
        if not self.check_consent(user_id, operation):
            raise PermissionError(
                f"User '{user_id}' has not consented to operation '{operation}'. "
                "Please grant consent before proceeding."
            )
