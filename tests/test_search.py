"""Tests for the Tri-Index Search Engine."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_os_nexus.core.tri_index_search import (
    SemanticSearch,
    KeywordSearch,
    MemoryTemporalSearch,
    TriIndexSearch,
)


# ---------------------------------------------------------------------------
# SemanticSearch
# ---------------------------------------------------------------------------

def test_semantic_search_basic():
    ss = SemanticSearch()
    ss.add("doc1", "The quick brown fox jumps over the lazy dog")
    ss.add("doc2", "Machine learning is a subset of artificial intelligence")
    ss.add("doc3", "Irrigation systems control water distribution for crops")

    results = ss.search("artificial intelligence and machine learning")
    assert len(results) > 0
    assert results[0].doc_id == "doc2"


def test_semantic_search_empty():
    ss = SemanticSearch()
    results = ss.search("anything")
    assert results == []


def test_semantic_search_remove():
    ss = SemanticSearch()
    ss.add("doc1", "Python is a programming language")
    ss.add("doc2", "Java is a programming language")
    ss.remove("doc1")
    results = ss.search("Python programming")
    assert all(r.doc_id != "doc1" for r in results)


def test_semantic_search_scores_between_0_1():
    ss = SemanticSearch()
    ss.add("d1", "water irrigation soil moisture crops")
    ss.add("d2", "hospital patient heart rate blood pressure")
    results = ss.search("soil moisture for agriculture")
    for r in results:
        assert 0.0 <= r.score <= 1.0


def test_semantic_search_top_k():
    ss = SemanticSearch()
    for i in range(20):
        ss.add(f"doc{i}", f"Document {i} contains some text about topic {i}")
    results = ss.search("document text", top_k=5)
    assert len(results) <= 5


# ---------------------------------------------------------------------------
# KeywordSearch
# ---------------------------------------------------------------------------

def test_keyword_search_basic(tmp_path):
    ks = KeywordSearch(db_path=tmp_path / "kw_test.db")
    ks.add("k1", "soil moisture irrigation water")
    ks.add("k2", "hospital heart rate blood oxygen")
    ks.add("k3", "industrial pressure vibration temperature")

    results = ks.search("soil moisture")
    assert any(r.doc_id == "k1" for r in results)


def test_keyword_search_no_match(tmp_path):
    ks = KeywordSearch(db_path=tmp_path / "kw_test2.db")
    ks.add("k1", "hello world")
    results = ks.search("xyznomatch12345")
    assert results == []


def test_keyword_search_remove(tmp_path):
    ks = KeywordSearch(db_path=tmp_path / "kw_test3.db")
    ks.add("d1", "remove this document please")
    ks.remove("d1")
    results = ks.search("remove document")
    assert all(r.doc_id != "d1" for r in results)


def test_keyword_search_scores_positive(tmp_path):
    ks = KeywordSearch(db_path=tmp_path / "kw_test4.db")
    ks.add("d1", "python fastapi pydantic uvicorn")
    results = ks.search("fastapi uvicorn")
    for r in results:
        assert r.score > 0


# ---------------------------------------------------------------------------
# MemoryTemporalSearch
# ---------------------------------------------------------------------------

def test_memory_temporal_search(tmp_path):
    mts = MemoryTemporalSearch(db_path=tmp_path / "mt_test.db")
    mts.add("m1", "user-001", "Discussed irrigation scheduling for wheat crops")
    mts.add("m2", "user-001", "Asked about Python async programming")
    mts.add("m3", "user-002", "Different user different content")

    results = mts.search("irrigation crops", user_id="user-001")
    assert len(results) >= 1
    assert results[0].doc_id in ("m1", "m2")
    # Should only return user-001 memories
    assert all(r.doc_id != "m3" for r in results)


def test_memory_temporal_isolation(tmp_path):
    mts = MemoryTemporalSearch(db_path=tmp_path / "mt_test2.db")
    mts.add("a1", "alice", "Alice's private memory")
    mts.add("b1", "bob", "Bob's private memory")

    alice_results = mts.search("private memory", user_id="alice")
    assert all(r.doc_id == "a1" for r in alice_results)


# ---------------------------------------------------------------------------
# TriIndexSearch — integrated
# ---------------------------------------------------------------------------

def test_tri_index_basic(tmp_path):
    ts = TriIndexSearch(db_path=tmp_path / "tri_test.db")
    ts.index_document("t1", "machine learning artificial intelligence neural networks")
    ts.index_document("t2", "irrigation soil moisture water crops agriculture")
    ts.index_document("t3", "hospital patient vital signs blood pressure oxygen")

    results = ts.search("artificial intelligence ML")
    assert len(results) > 0
    # t1 should rank highest
    assert results[0].doc_id == "t1"


def test_tri_index_with_user_memory(tmp_path):
    ts = TriIndexSearch(db_path=tmp_path / "tri_test2.db")
    user_id = "mem-test-user"
    ts.index_document("d1", "Python programming best practices", user_id=user_id)
    ts.index_document("d2", "JavaScript frontend development", user_id=user_id)
    ts.index_document("d3", "Database SQL queries optimisation", user_id="other-user")

    results = ts.search("Python programming", user_id=user_id)
    assert len(results) > 0
    assert results[0].doc_id == "d1"


def test_tri_index_cache(tmp_path):
    ts = TriIndexSearch(db_path=tmp_path / "tri_cache.db")
    ts.index_document("c1", "cache test document content here")

    # First call
    r1 = ts.search("cache test document")
    # Second call — should use cache
    r2 = ts.search("cache test document")
    assert r1[0].doc_id == r2[0].doc_id


def test_tri_index_score_range(tmp_path):
    ts = TriIndexSearch(db_path=tmp_path / "tri_score.db")
    ts.index_document("s1", "water irrigation soil moisture crops field")
    ts.index_document("s2", "hospital vital signs patient monitoring ICU")
    ts.index_document("s3", "industrial factory automation PLC SCADA")

    results = ts.search("water irrigation crops")
    for r in results:
        assert r.score >= 0


def test_tri_index_remove(tmp_path):
    ts = TriIndexSearch(db_path=tmp_path / "tri_remove.db")
    ts.index_document("r1", "this document will be removed")
    ts.index_document("r2", "this document will remain in the index")
    ts.remove_document("r1")

    results = ts.search("document removed index")
    assert all(r.doc_id != "r1" for r in results)


def test_tri_index_empty_query(tmp_path):
    ts = TriIndexSearch(db_path=tmp_path / "tri_empty.db")
    ts.index_document("e1", "some content here")
    results = ts.search("")
    assert isinstance(results, list)  # Should not crash


def test_tri_index_top_k(tmp_path):
    ts = TriIndexSearch(db_path=tmp_path / "tri_topk.db")
    for i in range(15):
        ts.index_document(f"doc{i}", f"content item number {i} with text about topics")
    results = ts.search("content item number", top_k=5)
    assert len(results) <= 5
