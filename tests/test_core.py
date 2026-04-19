"""Tests for core modules: LLM, memory, and consent engine."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import pytest

from ai_os_nexus.core.llm_core import MockLLM, LLMFactory, OpenAICompatibleLLM
from ai_os_nexus.core.memory_manager import MemoryManager, MemoryMode
from ai_os_nexus.core.consent_engine import ConsentEngine


# ---------------------------------------------------------------------------
# LLM Core
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mock_llm_greeting():
    llm = MockLLM()
    resp = await llm.generate("Hello there, how are you?")
    assert "Nexus" in resp or "hello" in resp.lower() or "assist" in resp.lower()


@pytest.mark.asyncio
async def test_mock_llm_irrigation():
    llm = MockLLM()
    resp = await llm.generate("What should I do about soil moisture?")
    assert "irrig" in resp.lower() or "moisture" in resp.lower() or "soil" in resp.lower()


@pytest.mark.asyncio
async def test_mock_llm_hospital():
    llm = MockLLM()
    resp = await llm.generate("What are normal blood pressure ranges?")
    assert "blood" in resp.lower() or "mmhg" in resp.lower() or "vitals" in resp.lower()


@pytest.mark.asyncio
async def test_mock_llm_code():
    llm = MockLLM()
    resp = await llm.generate("How do I write a Python function?")
    assert "python" in resp.lower() or "code" in resp.lower() or "function" in resp.lower()


@pytest.mark.asyncio
async def test_mock_llm_general():
    llm = MockLLM()
    resp = await llm.generate("What is the capital of France?")
    assert len(resp) > 10  # Should return some response


@pytest.mark.asyncio
async def test_mock_llm_with_context():
    llm = MockLLM()
    resp = await llm.generate("Explain this", context="Solar energy is renewable.")
    assert len(resp) > 0


def test_mock_llm_model_name():
    llm = MockLLM()
    assert "mock" in llm.model_name()


def test_llm_factory_mock():
    llm = LLMFactory.create("mock")
    assert isinstance(llm, MockLLM)


def test_llm_factory_unknown_falls_back():
    llm = LLMFactory.create("some-unknown-model-xyz")
    assert isinstance(llm, MockLLM)


def test_llm_factory_register():
    LLMFactory.register("my-custom-model", MockLLM)
    llm = LLMFactory.create("my-custom-model")
    assert isinstance(llm, MockLLM)


# ---------------------------------------------------------------------------
# Memory Manager
# ---------------------------------------------------------------------------

def make_memory(tmp_path: Path) -> MemoryManager:
    return MemoryManager(db_path=tmp_path / "test_memory.db")


def test_memory_store_retrieve(tmp_path):
    mm = make_memory(tmp_path)
    uid = "user-core-test-001"
    mid = mm.store(uid, "Test memory content", MemoryMode.PRIVATE)
    assert mid != ""

    entries = mm.retrieve(uid)
    assert len(entries) == 1
    assert entries[0].content == "Test memory content"
    assert entries[0].mode == MemoryMode.PRIVATE


def test_memory_encryption_isolation(tmp_path):
    """User A cannot read User B's memories."""
    mm = make_memory(tmp_path)
    mm.store("user-A", "Secret for A", MemoryMode.PRIVATE)
    mm.store("user-B", "Secret for B", MemoryMode.PRIVATE)

    a_memories = mm.retrieve("user-A")
    b_memories = mm.retrieve("user-B")

    assert all(e.content == "Secret for A" for e in a_memories)
    assert all(e.content == "Secret for B" for e in b_memories)
    assert len(a_memories) == 1
    assert len(b_memories) == 1


def test_memory_ttl_expiry(tmp_path):
    mm = make_memory(tmp_path)
    uid = "ttl-user"
    # Store with 1-second TTL
    mm.store(uid, "Expires soon", MemoryMode.PRIVATE, ttl_seconds=1)
    assert len(mm.retrieve(uid)) == 1

    # Wait for expiry
    time.sleep(1.1)
    entries = mm.retrieve(uid)
    assert len(entries) == 0


def test_memory_delete_user(tmp_path):
    mm = make_memory(tmp_path)
    uid = "del-user"
    for i in range(3):
        mm.store(uid, f"Memory {i}", MemoryMode.PRIVATE)
    assert mm.count(uid) == 3
    deleted = mm.delete_user_data(uid)
    assert deleted == 3
    assert mm.count(uid) == 0


def test_memory_delete_single(tmp_path):
    mm = make_memory(tmp_path)
    uid = "single-del-user"
    mid = mm.store(uid, "Single memory", MemoryMode.PRIVATE)
    assert mm.delete_memory(mid, uid) is True
    assert mm.count(uid) == 0


def test_memory_delete_wrong_user(tmp_path):
    mm = make_memory(tmp_path)
    mid = mm.store("owner", "Protected", MemoryMode.PRIVATE)
    assert mm.delete_memory(mid, "attacker") is False  # Cannot delete another user's memory


def test_memory_none_mode(tmp_path):
    mm = make_memory(tmp_path)
    mid = mm.store("user-x", "Should not store", MemoryMode.NONE)
    assert mid == ""


def test_memory_export(tmp_path):
    mm = make_memory(tmp_path)
    uid = "export-user"
    mm.store(uid, "Exportable data", MemoryMode.PRIVATE)
    data = mm.export_user_data(uid)
    assert len(data) == 1
    assert data[0]["content"] == "Exportable data"


def test_memory_delete_expired(tmp_path):
    mm = make_memory(tmp_path)
    uid = "expire-test"
    mm.store(uid, "Will expire", MemoryMode.PRIVATE, ttl_seconds=1)
    time.sleep(1.1)
    deleted = mm.delete_expired()
    assert deleted >= 1


# ---------------------------------------------------------------------------
# Consent Engine
# ---------------------------------------------------------------------------

def make_consent(tmp_path: Path) -> ConsentEngine:
    return ConsentEngine(db_path=tmp_path / "test_consent.db")


def test_consent_request_and_grant(tmp_path):
    ce = make_consent(tmp_path)
    uid = "consent-user-001"
    op  = "memory.write.private"

    ce.request_consent(uid, op)
    assert ce.check_consent(uid, op) is False  # Not granted yet

    ce.grant_consent(uid, op)
    assert ce.check_consent(uid, op) is True


def test_consent_revoke(tmp_path):
    ce = make_consent(tmp_path)
    uid = "revoke-user"
    op  = "data.share"
    ce.grant_consent(uid, op)
    assert ce.check_consent(uid, op) is True

    ce.revoke_consent(uid, op)
    assert ce.check_consent(uid, op) is False


def test_consent_ensure_raises(tmp_path):
    ce = make_consent(tmp_path)
    uid = "no-consent-user"
    with pytest.raises(PermissionError):
        ce.ensure_consent(uid, "blocked.operation")


def test_consent_auto_grant_on_missing(tmp_path):
    ce = make_consent(tmp_path)
    uid = "auto-grant-user"
    # grant_consent creates record if missing
    result = ce.grant_consent(uid, "new.op")
    assert result is True
    assert ce.check_consent(uid, "new.op") is True


def test_consent_list(tmp_path):
    ce = make_consent(tmp_path)
    uid = "list-user"
    ce.grant_consent(uid, "op.1")
    ce.grant_consent(uid, "op.2")
    records = ce.list_consents(uid)
    assert len(records) == 2
    ops = {r.operation for r in records}
    assert "op.1" in ops
    assert "op.2" in ops


def test_consent_expiry(tmp_path):
    ce = make_consent(tmp_path)
    uid = "expire-user"
    ce.request_consent(uid, "temp.op", expires_in=1)
    ce.grant_consent(uid, "temp.op")
    assert ce.check_consent(uid, "temp.op") is True
    time.sleep(1.1)
    assert ce.check_consent(uid, "temp.op") is False
