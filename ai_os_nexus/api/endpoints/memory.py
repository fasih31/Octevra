"""
/memory endpoints — view, create, delete, and export user memories.
All operations enforce per-user isolation.

© 2026 Fasih ur Rehman. All Rights Reserved.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ai_os_nexus.core.audit_log import AuditEvent, get_audit_log
from ai_os_nexus.core.memory_manager import MemoryManager, MemoryMode
from ai_os_nexus.core.consent_engine import ConsentEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory", tags=["memory"])

_memory = MemoryManager()
_consent = ConsentEngine()
_audit = get_audit_log()


class StoreMemoryRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1, max_length=8192)
    mode: str = Field("PRIVATE", pattern="^(NONE|PRIVATE|ANON_LEARN|PUBLIC)$")
    ttl_seconds: Optional[int] = Field(None, ge=60, le=86400 * 365)
    metadata: dict = Field(default_factory=dict)


class MemoryEntryOut(BaseModel):
    id: str
    user_id: str
    content: str
    mode: str
    created_at: float
    expires_at: Optional[float]
    metadata: dict


@router.get("/{user_id}", response_model=list[MemoryEntryOut])
async def get_memories(user_id: str, mode: Optional[str] = None, limit: int = 50):
    """Retrieve all memories for a user."""
    if limit > 200:
        limit = 200
    mem_mode = MemoryMode(mode) if mode else None
    entries = _memory.retrieve(user_id, mode=mem_mode, limit=limit)
    return [
        MemoryEntryOut(
            id=e.id, user_id=e.user_id, content=e.content,
            mode=e.mode.value, created_at=e.created_at,
            expires_at=e.expires_at, metadata=e.metadata,
        )
        for e in entries
    ]


@router.post("", status_code=201)
async def store_memory(body: StoreMemoryRequest):
    """Manually store a memory entry."""
    if body.mode == "NONE":
        return {"memory_id": None, "stored": False, "message": "Mode NONE — nothing stored"}

    # Auto-grant consent for demo; production would verify user consent explicitly
    op = f"memory.write.{body.mode.lower()}"
    if not _consent.check_consent(body.user_id, op):
        _consent.grant_consent(body.user_id, op)

    memory_id = _memory.store(
        user_id=body.user_id,
        content=body.content,
        mode=MemoryMode(body.mode),
        ttl_seconds=body.ttl_seconds,
        metadata=body.metadata,
    )
    _audit.log(
        AuditEvent.MEMORY_STORE,
        actor=body.user_id,
        target=memory_id,
        status="ok",
        metadata={"mode": body.mode, "content": body.content},
    )
    return {"memory_id": memory_id, "stored": True, "message": "Memory stored successfully"}


@router.delete("/{user_id}")
async def delete_user_memories(user_id: str):
    """Delete ALL memories for a user (GDPR right to erasure)."""
    count = _memory.delete_user_data(user_id)
    _audit.log(
        AuditEvent.MEMORY_DELETE_ALL,
        actor=user_id,
        target=user_id,
        status="ok",
        metadata={"deleted_count": count},
    )
    return {"deleted": count, "user_id": user_id, "message": f"Deleted {count} memory entries"}


@router.delete("/{user_id}/{memory_id}")
async def delete_single_memory(user_id: str, memory_id: str):
    """Delete a specific memory entry."""
    deleted = _memory.delete_memory(memory_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found or access denied")
    _audit.log(
        AuditEvent.MEMORY_DELETE,
        actor=user_id,
        target=memory_id,
        status="ok",
    )
    return {"deleted": True, "memory_id": memory_id}


@router.get("/{user_id}/export")
async def export_memories(user_id: str):
    """Export all memories for a user (GDPR data portability)."""
    data = _memory.export_user_data(user_id)
    _audit.log(
        AuditEvent.MEMORY_EXPORT,
        actor=user_id,
        target=user_id,
        status="ok",
        metadata={"exported_count": len(data)},
    )
    return {"user_id": user_id, "count": len(data), "memories": data}
