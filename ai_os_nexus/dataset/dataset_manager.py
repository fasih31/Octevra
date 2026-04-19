"""
Custom Dataset Engine — self-contained SQLite + vector store.
Logs all system interactions. No external dataset dependencies.
Categories: knowledge, conversation, sensor_log, decision_log, user_feedback
"""

from __future__ import annotations

import json
import logging
import math
import re
import sqlite3
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)

DB_PATH = Path("data/dataset.db")

VALID_CATEGORIES = frozenset([
    "knowledge", "conversation", "sensor_log", "decision_log", "user_feedback"
])


@dataclass
class DatasetEntry:
    id: str
    category: str
    content: str
    source: str
    metadata: dict[str, Any]
    created_at: float
    embedding: Optional[list[float]] = None


# ---------------------------------------------------------------------------
# Simple TF-IDF vectorizer (no sklearn dependency)
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _build_tfidf(corpus: list[tuple[str, str]]) -> tuple[dict, dict, dict[str, np.ndarray]]:
    """Returns (vocab, idf, doc_vectors)."""
    tokenized = {doc_id: _tokenize(text) for doc_id, text in corpus}
    all_tokens: set[str] = set()
    for tokens in tokenized.values():
        all_tokens.update(tokens)
    vocab = {t: i for i, t in enumerate(sorted(all_tokens))}

    N = len(tokenized)
    doc_freq: dict[str, int] = defaultdict(int)
    for tokens in tokenized.values():
        for t in set(tokens):
            doc_freq[t] += 1
    idf = {t: math.log((N + 1) / (df + 1)) + 1 for t, df in doc_freq.items()}

    vectors: dict[str, np.ndarray] = {}
    for doc_id, tokens in tokenized.items():
        vec = np.zeros(len(vocab))
        counts: dict[str, int] = defaultdict(int)
        for t in tokens:
            counts[t] += 1
        for t, cnt in counts.items():
            if t in vocab:
                tf = cnt / max(len(tokens), 1)
                vec[vocab[t]] = tf * idf.get(t, 1.0)
        norm = np.linalg.norm(vec)
        vectors[doc_id] = vec / norm if norm > 0 else vec
    return vocab, idf, vectors


class DatasetManager:
    """Manages the self-growing local knowledge dataset."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._setup()
        self._vector_cache: Optional[dict] = None
        self._cache_dirty = True

    def _setup(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS dataset (
                    id           TEXT PRIMARY KEY,
                    category     TEXT NOT NULL,
                    content      TEXT NOT NULL,
                    source       TEXT NOT NULL,
                    metadata_json TEXT DEFAULT '{}',
                    created_at   REAL NOT NULL
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ds_category ON dataset(category)"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ds_created ON dataset(created_at)"
            )
            # FTS for keyword search
            self._conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS dataset_fts
                USING fts5(id UNINDEXED, content, category UNINDEXED, tokenize='porter ascii')
                """
            )

    # ------------------------------------------------------------------
    def add_entry(
        self,
        category: str,
        content: str,
        source: str = "system",
        metadata: dict | None = None,
    ) -> str:
        """Add a new entry to the dataset. Returns entry ID."""
        if category not in VALID_CATEGORIES:
            logger.warning("Unknown category '%s', defaulting to 'knowledge'", category)
            category = "knowledge"

        entry_id = str(uuid.uuid4())
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO dataset (id, category, content, source, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (entry_id, category, content, source, json.dumps(metadata or {}), time.time()),
            )
            self._conn.execute(
                "INSERT INTO dataset_fts (id, content, category) VALUES (?, ?, ?)",
                (entry_id, content, category),
            )
        self._cache_dirty = True
        logger.debug("Dataset entry %s added (category=%s)", entry_id, category)
        return entry_id

    # ------------------------------------------------------------------
    def search(
        self,
        query: str,
        category: Optional[str] = None,
        top_k: int = 10,
    ) -> list[DatasetEntry]:
        """Hybrid TF-IDF + FTS search."""
        # Keyword search via FTS
        safe_q = re.sub(r"[^a-zA-Z0-9\s]", " ", query)
        fts_ids: set[str] = set()
        if safe_q.strip():
            try:
                where = "WHERE dataset_fts MATCH ?"
                params: list = [safe_q]
                if category:
                    # FTS5 doesn't support WHERE on UNINDEXED columns easily, filter after
                    pass
                cur = self._conn.execute(
                    f"SELECT id FROM dataset_fts {where} LIMIT ?",
                    (*params, top_k * 3),
                )
                fts_ids = {row[0] for row in cur.fetchall()}
            except sqlite3.OperationalError as e:
                logger.debug("FTS error: %s", e)

        # Get all docs for TF-IDF
        if category:
            cur = self._conn.execute(
                "SELECT id, category, content, source, metadata_json, created_at "
                "FROM dataset WHERE category = ? ORDER BY created_at DESC LIMIT 500",
                (category,),
            )
        else:
            cur = self._conn.execute(
                "SELECT id, category, content, source, metadata_json, created_at "
                "FROM dataset ORDER BY created_at DESC LIMIT 500"
            )
        rows = cur.fetchall()
        if not rows:
            return []

        corpus = [(r[0], r[2]) for r in rows]
        if len(corpus) < 2:
            # Skip TF-IDF for tiny corpus
            entries = []
            for row in rows[:top_k]:
                entries.append(DatasetEntry(
                    id=row[0], category=row[1], content=row[2],
                    source=row[3], metadata=json.loads(row[4] or "{}"), created_at=row[5],
                ))
            return entries

        vocab, idf, doc_vectors = _build_tfidf(corpus)
        q_tokens = _tokenize(query)
        q_vec = np.zeros(len(vocab))
        counts: dict[str, int] = defaultdict(int)
        for t in q_tokens:
            counts[t] += 1
        for t, cnt in counts.items():
            if t in vocab:
                tf = cnt / max(len(q_tokens), 1)
                q_vec[vocab[t]] = tf * idf.get(t, 1.0)
        norm = np.linalg.norm(q_vec)
        if norm > 0:
            q_vec = q_vec / norm

        row_map = {r[0]: r for r in rows}
        scored: list[tuple[str, float]] = []
        for doc_id, vec in doc_vectors.items():
            denom = np.linalg.norm(q_vec) * np.linalg.norm(vec)
            cos = float(np.dot(q_vec, vec) / denom) if denom > 0 else 0.0
            fts_bonus = 0.3 if doc_id in fts_ids else 0.0
            scored.append((doc_id, cos + fts_bonus))

        scored.sort(key=lambda x: x[1], reverse=True)
        results: list[DatasetEntry] = []
        for doc_id, score in scored[:top_k]:
            if score <= 0:
                continue
            row = row_map[doc_id]
            results.append(DatasetEntry(
                id=row[0], category=row[1], content=row[2],
                source=row[3], metadata=json.loads(row[4] or "{}"), created_at=row[5],
            ))
        return results

    # ------------------------------------------------------------------
    def get_stats(self) -> dict:
        cur = self._conn.execute(
            "SELECT category, COUNT(*) FROM dataset GROUP BY category"
        )
        by_category = dict(cur.fetchall())
        total = sum(by_category.values())
        cur2 = self._conn.execute("SELECT MIN(created_at), MAX(created_at) FROM dataset")
        row = cur2.fetchone()
        return {
            "total_entries": total,
            "by_category": by_category,
            "earliest": row[0],
            "latest": row[1],
        }

    def export_dataset(self, category: Optional[str] = None) -> list[dict]:
        if category:
            cur = self._conn.execute(
                "SELECT id, category, content, source, metadata_json, created_at "
                "FROM dataset WHERE category = ? ORDER BY created_at",
                (category,),
            )
        else:
            cur = self._conn.execute(
                "SELECT id, category, content, source, metadata_json, created_at "
                "FROM dataset ORDER BY created_at"
            )
        return [
            {
                "id": r[0], "category": r[1], "content": r[2],
                "source": r[3], "metadata": json.loads(r[4] or "{}"), "created_at": r[5],
            }
            for r in cur.fetchall()
        ]

    def import_dataset(self, entries: list[dict]) -> int:
        """Bulk import entries. Returns number imported."""
        count = 0
        for entry in entries:
            try:
                self.add_entry(
                    category=entry.get("category", "knowledge"),
                    content=entry["content"],
                    source=entry.get("source", "import"),
                    metadata=entry.get("metadata", {}),
                )
                count += 1
            except Exception as exc:
                logger.warning("Import error for entry: %s", exc)
        return count

    def count(self, category: Optional[str] = None) -> int:
        if category:
            cur = self._conn.execute(
                "SELECT COUNT(*) FROM dataset WHERE category = ?", (category,)
            )
        else:
            cur = self._conn.execute("SELECT COUNT(*) FROM dataset")
        return cur.fetchone()[0]
