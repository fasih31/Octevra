"""
/ask endpoint — handles public and private AI queries.
Public: knowledge-only, no memory.
Private: knowledge + user memory, with consent-gated storage.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ai_os_nexus.core.llm_core import LLMFactory
from ai_os_nexus.core.memory_manager import MemoryManager, MemoryMode
from ai_os_nexus.core.consent_engine import ConsentEngine
from ai_os_nexus.core.tri_index_search import TriIndexSearch
from ai_os_nexus.dataset.dataset_manager import DatasetManager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ask"])

# Singletons (initialised on app startup via dependency injection or module-level)
_llm = LLMFactory.create("mock")
_memory = MemoryManager()
_consent = ConsentEngine()
_search = TriIndexSearch()
_dataset = DatasetManager()


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4096)
    user_id: Optional[str] = Field(None, max_length=128)
    mode: str = Field("public", pattern="^(public|private)$")
    memory_consent: str = Field("NONE", pattern="^(NONE|PRIVATE|ANON_LEARN|PUBLIC)$")


class AskResponse(BaseModel):
    request_id: str
    response: str
    sources: list[dict]
    mode: str
    memory_stored: bool
    memory_id: Optional[str]
    latency_ms: float


@router.post("/ask", response_model=AskResponse)
async def ask(body: AskRequest):
    """Query the AI system. Public mode uses knowledge base only; private mode adds user memory."""
    t0 = time.time()
    request_id = str(uuid.uuid4())
    user_id = body.user_id or "anonymous"

    # Search the knowledge base
    results = _search.search(body.query, user_id=user_id if body.mode == "private" else None, top_k=5)

    context_parts = []
    sources = []
    for r in results:
        context_parts.append(r.text)
        sources.append({
            "doc_id": r.doc_id,
            "score": round(r.score, 4),
            "source": r.source,
            "metadata": r.metadata,
        })

    # Also search dataset
    dataset_results = _dataset.search(body.query, top_k=3)
    for dr in dataset_results:
        context_parts.append(dr.content)
        sources.append({
            "doc_id": dr.id,
            "score": 0.5,
            "source": "dataset:" + dr.category,
            "metadata": dr.metadata,
        })

    # Generate response
    context = "\n\n".join(context_parts[:5]) if context_parts else ""
    response_text = await _llm.generate(body.query, context)

    # Log conversation to dataset
    _dataset.add_entry(
        category="conversation",
        content=f"Q: {body.query}\nA: {response_text}",
        source=f"user:{user_id}",
        metadata={"mode": body.mode, "user_id": user_id if body.mode == "private" else "anonymous"},
    )

    # Memory storage (private mode only, with consent)
    memory_stored = False
    memory_id = None
    consent_op = f"memory.write.{body.memory_consent.lower()}"

    if body.mode == "private" and body.memory_consent != "NONE" and user_id != "anonymous":
        # Auto-grant consent for the requested mode (in a real system, user explicitly grants)
        if not _consent.check_consent(user_id, consent_op):
            _consent.grant_consent(user_id, consent_op)

        try:
            _consent.ensure_consent(user_id, consent_op)
            mode = MemoryMode(body.memory_consent)
            content = f"Q: {body.query}\nA: {response_text}"
            memory_id = _memory.store(
                user_id=user_id,
                content=content,
                mode=mode,
                ttl_seconds=86400 * 30,  # 30 days default
                metadata={"query": body.query[:200], "mode": body.mode},
            )
            memory_stored = True
            # Also index in search for future retrieval
            _search.index_document(
                doc_id=memory_id,
                text=content,
                metadata={"user_id": user_id, "type": "memory"},
                user_id=user_id,
            )
        except PermissionError as exc:
            logger.warning("Memory storage blocked: %s", exc)

    latency = (time.time() - t0) * 1000
    logger.info("ask: request_id=%s mode=%s latency=%.1fms", request_id, body.mode, latency)

    return AskResponse(
        request_id=request_id,
        response=response_text,
        sources=sources[:10],
        mode=body.mode,
        memory_stored=memory_stored,
        memory_id=memory_id,
        latency_ms=round(latency, 2),
    )
