"""
Memory Manager — Fernet-encrypted, per-user, consent-gated, TTL-aware.
All memory is stored in local SQLite. Private memory never crosses user boundaries.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

DB_PATH = Path("data/memory.db")
MASTER_SECRET = os.environ.get("NEXUS_MASTER_SECRET", "nexus-default-secret-change-in-prod")


class MemoryMode(str, Enum):
    NONE = "NONE"             # Not stored
    PRIVATE = "PRIVATE"       # Encrypted per user, never shared
    ANON_LEARN = "ANON_LEARN" # Anonymised, used for learning
    PUBLIC = "PUBLIC"         # Shared knowledge base


@dataclass
class MemoryEntry:
    id: str
    user_id: str
    content: str           # decrypted
    mode: MemoryMode
    created_at: float
    expires_at: Optional[float]
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Key derivation
# ---------------------------------------------------------------------------

def _derive_key(user_id: str) -> bytes:
    """Derive a per-user Fernet key using PBKDF2-HMAC-SHA256."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=user_id.encode("utf-8")[:16].ljust(16, b"\x00"),
        iterations=100_000,
    )
    raw = kdf.derive(MASTER_SECRET.encode("utf-8"))
    return base64.urlsafe_b64encode(raw)


def _get_fernet(user_id: str) -> Fernet:
    return Fernet(_derive_key(user_id))


# ---------------------------------------------------------------------------
# MemoryManager
# ---------------------------------------------------------------------------

class MemoryManager:
    """Manages encrypted per-user memories in SQLite."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._setup()

    def _setup(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id                TEXT PRIMARY KEY,
                    user_id           TEXT NOT NULL,
                    encrypted_content BLOB NOT NULL,
                    mode              TEXT NOT NULL,
                    created_at        REAL NOT NULL,
                    expires_at        REAL,
                    metadata_json     TEXT DEFAULT '{}'
                )
                """
            )
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_user ON memories(user_id)")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_mode ON memories(mode)")

    # ------------------------------------------------------------------
    def store(
        self,
        user_id: str,
        content: str,
        mode: MemoryMode,
        ttl_seconds: Optional[int] = None,
        metadata: dict | None = None,
    ) -> str:
        """Encrypt and store a memory. Returns the memory ID."""
        if mode == MemoryMode.NONE:
            return ""

        fernet = _get_fernet(user_id)
        encrypted = fernet.encrypt(content.encode("utf-8"))
        mem_id = str(uuid.uuid4())
        expires_at = time.time() + ttl_seconds if ttl_seconds else None

        with self._conn:
            self._conn.execute(
                """
                INSERT INTO memories
                    (id, user_id, encrypted_content, mode, created_at, expires_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mem_id,
                    user_id,
                    encrypted,
                    mode.value,
                    time.time(),
                    expires_at,
                    json.dumps(metadata or {}),
                ),
            )
        logger.debug("Stored memory %s for user %s (mode=%s)", mem_id, user_id, mode)
        return mem_id

    # ------------------------------------------------------------------
    def retrieve(
        self,
        user_id: str,
        mode: MemoryMode | None = None,
        limit: int = 50,
    ) -> list[MemoryEntry]:
        """Retrieve decrypted memories for a user."""
        fernet = _get_fernet(user_id)
        now = time.time()

        if mode:
            cur = self._conn.execute(
                """
                SELECT id, user_id, encrypted_content, mode, created_at, expires_at, metadata_json
                FROM memories
                WHERE user_id = ? AND mode = ?
                  AND (expires_at IS NULL OR expires_at > ?)
                ORDER BY created_at DESC LIMIT ?
                """,
                (user_id, mode.value, now, limit),
            )
        else:
            cur = self._conn.execute(
                """
                SELECT id, user_id, encrypted_content, mode, created_at, expires_at, metadata_json
                FROM memories
                WHERE user_id = ?
                  AND (expires_at IS NULL OR expires_at > ?)
                ORDER BY created_at DESC LIMIT ?
                """,
                (user_id, now, limit),
            )

        entries: list[MemoryEntry] = []
        for row in cur.fetchall():
            mem_id, uid, enc, mode_val, created, expires, meta_json = row
            try:
                content = fernet.decrypt(enc).decode("utf-8")
            except Exception:
                logger.warning("Failed to decrypt memory %s", mem_id)
                continue
            entries.append(
                MemoryEntry(
                    id=mem_id,
                    user_id=uid,
                    content=content,
                    mode=MemoryMode(mode_val),
                    created_at=created,
                    expires_at=expires,
                    metadata=json.loads(meta_json or "{}"),
                )
            )
        return entries

    # ------------------------------------------------------------------
    def delete_expired(self) -> int:
        """Remove all expired memories. Returns count deleted."""
        now = time.time()
        with self._conn:
            cur = self._conn.execute(
                "DELETE FROM memories WHERE expires_at IS NOT NULL AND expires_at <= ?",
                (now,),
            )
        logger.info("Deleted %d expired memories", cur.rowcount)
        return cur.rowcount

    def delete_user_data(self, user_id: str) -> int:
        """Hard-delete all memories for a user (GDPR right-to-erasure)."""
        with self._conn:
            cur = self._conn.execute("DELETE FROM memories WHERE user_id = ?", (user_id,))
        logger.info("Deleted %d memories for user %s", cur.rowcount, user_id)
        return cur.rowcount

    def delete_memory(self, memory_id: str, user_id: str) -> bool:
        """Delete a specific memory, enforcing user ownership."""
        with self._conn:
            cur = self._conn.execute(
                "DELETE FROM memories WHERE id = ? AND user_id = ?",
                (memory_id, user_id),
            )
        return cur.rowcount > 0

    # ------------------------------------------------------------------
    def export_user_data(self, user_id: str) -> list[dict]:
        """Export all decrypted memories for a user (GDPR data portability)."""
        entries = self.retrieve(user_id, limit=10_000)
        return [
            {
                "id": e.id,
                "content": e.content,
                "mode": e.mode.value,
                "created_at": e.created_at,
                "expires_at": e.expires_at,
                "metadata": e.metadata,
            }
            for e in entries
        ]

    def count(self, user_id: str) -> int:
        cur = self._conn.execute(
            "SELECT COUNT(*) FROM memories WHERE user_id = ?", (user_id,)
        )
        return cur.fetchone()[0]
