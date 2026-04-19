"""
Tri-Index Search Engine
Combines semantic (TF-IDF cosine), keyword (SQLite FTS5), and
memory-temporal search with weighted scoring.
score = semantic*0.5 + keyword*0.3 + memory*0.2
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
import sqlite3
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)

DB_PATH = Path("data/tri_index.db")
CACHE_TTL = 60  # seconds


@dataclass
class SearchResult:
    doc_id: str
    text: str
    score: float
    source: str  # "semantic" | "keyword" | "memory" | "combined"
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer."""
    return re.findall(r"[a-z0-9]+", text.lower())


def _tfidf_vector(tokens: list[str], vocab: dict[str, int], idf: dict[str, float]) -> np.ndarray:
    vec = np.zeros(len(vocab))
    tf_counts: dict[str, int] = defaultdict(int)
    for t in tokens:
        tf_counts[t] += 1
    for t, cnt in tf_counts.items():
        if t in vocab:
            tf = cnt / max(len(tokens), 1)
            vec[vocab[t]] = tf * idf.get(t, 1.0)
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


# ---------------------------------------------------------------------------
# Semantic Search (TF-IDF)
# ---------------------------------------------------------------------------

class SemanticSearch:
    """Cosine similarity over TF-IDF vectors — no external model required."""

    def __init__(self) -> None:
        self._docs: dict[str, str] = {}          # doc_id -> raw text
        self._meta: dict[str, dict] = {}
        self._vocab: dict[str, int] = {}
        self._idf: dict[str, float] = {}
        self._vectors: dict[str, np.ndarray] = {}
        self._dirty = True

    # ------------------------------------------------------------------
    def add(self, doc_id: str, text: str, metadata: dict | None = None) -> None:
        self._docs[doc_id] = text
        self._meta[doc_id] = metadata or {}
        self._dirty = True

    def remove(self, doc_id: str) -> None:
        self._docs.pop(doc_id, None)
        self._meta.pop(doc_id, None)
        self._vectors.pop(doc_id, None)
        self._dirty = True

    # ------------------------------------------------------------------
    def _rebuild(self) -> None:
        if not self._docs:
            return
        tokenized: dict[str, list[str]] = {
            did: _tokenize(txt) for did, txt in self._docs.items()
        }
        # Build vocab
        all_tokens: set[str] = set()
        for tokens in tokenized.values():
            all_tokens.update(tokens)
        self._vocab = {t: i for i, t in enumerate(sorted(all_tokens))}

        # IDF
        N = len(tokenized)
        doc_freq: dict[str, int] = defaultdict(int)
        for tokens in tokenized.values():
            for t in set(tokens):
                doc_freq[t] += 1
        self._idf = {t: math.log((N + 1) / (df + 1)) + 1 for t, df in doc_freq.items()}

        # Vectors
        self._vectors = {
            did: _tfidf_vector(tokens, self._vocab, self._idf)
            for did, tokens in tokenized.items()
        }
        self._dirty = False

    # ------------------------------------------------------------------
    def search(self, query: str, top_k: int = 10) -> list[SearchResult]:
        if self._dirty:
            self._rebuild()
        if not self._vectors:
            return []
        q_tokens = _tokenize(query)
        q_vec = _tfidf_vector(q_tokens, self._vocab, self._idf)

        scores: list[tuple[str, float]] = [
            (did, _cosine(q_vec, vec)) for did, vec in self._vectors.items()
        ]
        scores.sort(key=lambda x: x[1], reverse=True)

        return [
            SearchResult(
                doc_id=did,
                text=self._docs[did],
                score=sc,
                source="semantic",
                metadata=self._meta.get(did, {}),
            )
            for did, sc in scores[:top_k]
            if sc > 0
        ]


# ---------------------------------------------------------------------------
# Keyword Search (SQLite FTS5)
# ---------------------------------------------------------------------------

class KeywordSearch:
    """Full-text search backed by SQLite FTS5."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._setup()

    def _setup(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS fts_docs
                USING fts5(doc_id UNINDEXED, text, metadata_json, tokenize='porter ascii')
                """
            )

    def add(self, doc_id: str, text: str, metadata: dict | None = None) -> None:
        import json
        with self._conn:
            self._conn.execute(
                "DELETE FROM fts_docs WHERE doc_id = ?", (doc_id,)
            )
            self._conn.execute(
                "INSERT INTO fts_docs(doc_id, text, metadata_json) VALUES (?, ?, ?)",
                (doc_id, text, json.dumps(metadata or {})),
            )

    def remove(self, doc_id: str) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM fts_docs WHERE doc_id = ?", (doc_id,))

    def search(self, query: str, top_k: int = 10) -> list[SearchResult]:
        import json
        # Escape FTS5 special chars
        safe_query = re.sub(r'[^a-zA-Z0-9\s]', ' ', query)
        if not safe_query.strip():
            return []
        try:
            cur = self._conn.execute(
                """
                SELECT doc_id, text, metadata_json,
                       bm25(fts_docs) AS score
                FROM fts_docs
                WHERE fts_docs MATCH ?
                ORDER BY score
                LIMIT ?
                """,
                (safe_query, top_k),
            )
            rows = cur.fetchall()
        except sqlite3.OperationalError as e:
            logger.warning("FTS search error: %s", e)
            return []

        results = []
        for doc_id, text, meta_json, raw_score in rows:
            # bm25 returns negative; normalise to [0, 1]
            score = 1.0 / (1.0 + abs(raw_score))
            results.append(
                SearchResult(
                    doc_id=doc_id,
                    text=text,
                    score=score,
                    source="keyword",
                    metadata=json.loads(meta_json or "{}"),
                )
            )
        return results


# ---------------------------------------------------------------------------
# Memory Temporal Search
# ---------------------------------------------------------------------------

class MemoryTemporalSearch:
    """Search user memories by recency + text relevance."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._setup()

    def _setup(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_index (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_id     TEXT NOT NULL,
                    user_id    TEXT NOT NULL,
                    text       TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    metadata_json TEXT DEFAULT '{}'
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_mi_user ON memory_index(user_id)"
            )

    def add(self, doc_id: str, user_id: str, text: str, metadata: dict | None = None) -> None:
        import json
        with self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO memory_index
                    (doc_id, user_id, text, created_at, metadata_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (doc_id, user_id, text, time.time(), json.dumps(metadata or {})),
            )

    def remove(self, doc_id: str) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM memory_index WHERE doc_id = ?", (doc_id,))

    def search(self, query: str, user_id: str, top_k: int = 10) -> list[SearchResult]:
        import json
        cur = self._conn.execute(
            "SELECT doc_id, text, created_at, metadata_json FROM memory_index WHERE user_id = ?",
            (user_id,),
        )
        rows = cur.fetchall()
        if not rows:
            return []

        q_tokens = set(_tokenize(query))
        now = time.time()
        scored: list[tuple[str, str, float, dict]] = []

        for doc_id, text, created_at, meta_json in rows:
            tokens = set(_tokenize(text))
            overlap = len(q_tokens & tokens) / max(len(q_tokens | tokens), 1)
            # Recency decay: half-life 7 days
            age_days = (now - created_at) / 86400
            recency = math.exp(-0.1 * age_days)
            score = 0.6 * overlap + 0.4 * recency
            scored.append((doc_id, text, score, json.loads(meta_json or "{}")))

        scored.sort(key=lambda x: x[2], reverse=True)
        return [
            SearchResult(doc_id=d, text=t, score=s, source="memory", metadata=m)
            for d, t, s, m in scored[:top_k]
            if s > 0
        ]


# ---------------------------------------------------------------------------
# TriIndexSearch — unified engine
# ---------------------------------------------------------------------------

class TriIndexSearch:
    """
    Hybrid retrieval combining semantic (0.5), keyword (0.3), memory (0.2).
    Includes a TTL cache for repeated queries.
    """

    WEIGHTS = {"semantic": 0.5, "keyword": 0.3, "memory": 0.2}

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self._semantic = SemanticSearch()
        self._keyword = KeywordSearch(db_path)
        self._memory = MemoryTemporalSearch(db_path)
        self._cache: dict[str, tuple[float, list[SearchResult]]] = {}

    # ------------------------------------------------------------------
    def index_document(
        self,
        doc_id: str,
        text: str,
        metadata: dict | None = None,
        user_id: str | None = None,
    ) -> None:
        """Index a document in all three indices."""
        self._semantic.add(doc_id, text, metadata)
        self._keyword.add(doc_id, text, metadata)
        if user_id:
            self._memory.add(doc_id, user_id, text, metadata)
        # Invalidate cache entries containing this doc
        self._cache.clear()
        logger.debug("Indexed doc_id=%s", doc_id)

    def remove_document(self, doc_id: str) -> None:
        self._semantic.remove(doc_id)
        self._keyword.remove(doc_id)
        self._memory.remove(doc_id)
        self._cache.clear()

    # ------------------------------------------------------------------
    def search(
        self,
        query: str,
        user_id: str | None = None,
        top_k: int = 10,
    ) -> list[SearchResult]:
        """Merged hybrid search with TTL-cached results."""
        cache_key = hashlib.sha256(f"{query}|{user_id}|{top_k}".encode()).hexdigest()
        cached = self._cache.get(cache_key)
        if cached and (time.time() - cached[0]) < CACHE_TTL:
            return cached[1]

        sem_results = self._semantic.search(query, top_k=top_k * 2)
        kw_results = self._keyword.search(query, top_k=top_k * 2)
        mem_results = (
            self._memory.search(query, user_id, top_k=top_k * 2) if user_id else []
        )

        # Merge by doc_id, accumulate weighted scores
        merged: dict[str, dict] = {}
        for r in sem_results:
            merged.setdefault(r.doc_id, {"text": r.text, "meta": r.metadata, "score": 0.0})
            merged[r.doc_id]["score"] += self.WEIGHTS["semantic"] * r.score
        for r in kw_results:
            merged.setdefault(r.doc_id, {"text": r.text, "meta": r.metadata, "score": 0.0})
            merged[r.doc_id]["score"] += self.WEIGHTS["keyword"] * r.score
        for r in mem_results:
            merged.setdefault(r.doc_id, {"text": r.text, "meta": r.metadata, "score": 0.0})
            merged[r.doc_id]["score"] += self.WEIGHTS["memory"] * r.score

        results = [
            SearchResult(
                doc_id=did,
                text=info["text"],
                score=info["score"],
                source="combined",
                metadata=info["meta"],
            )
            for did, info in merged.items()
        ]
        results.sort(key=lambda x: x.score, reverse=True)
        top = results[:top_k]
        self._cache[cache_key] = (time.time(), top)
        return top
