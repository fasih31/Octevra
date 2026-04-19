"""
/admin endpoints — system health, stats, safety overrides, maintenance,
and compliance/audit reporting.

© 2026 Fasih ur Rehman. All Rights Reserved.
"""

from __future__ import annotations

import logging
import os
import platform
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ai_os_nexus.core.audit_log import AuditEvent, get_audit_log
from ai_os_nexus.core.memory_manager import MemoryManager
from ai_os_nexus.core.safety_layer import SafetyLayer
from ai_os_nexus.dataset.dataset_manager import DatasetManager
from ai_os_nexus.iot.sensor_api import SensorManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

_memory = MemoryManager()
_safety = SafetyLayer()
_dataset = DatasetManager()
_sensors = SensorManager()
_audit = get_audit_log()

_start_time = time.time()


class SafetyOverrideRequest(BaseModel):
    action_id: str = Field(..., min_length=1)
    admin_id: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=10)


@router.get("/health")
async def health():
    """System health check — returns uptime, version, and component status."""
    uptime = time.time() - _start_time
    return {
        "status": "healthy",
        "product": "Orkavia AI-OS Nexus",
        "version": "2.0.0",
        "copyright": "© 2026 Fasih ur Rehman. All Rights Reserved.",
        "uptime_seconds": round(uptime, 2),
        "uptime_human": _format_uptime(uptime),
        "platform": platform.system(),
        "python_version": platform.python_version(),
        "timestamp": time.time(),
        "components": {
            "memory_manager": "ok",
            "safety_layer": "ok",
            "dataset": "ok",
            "sensor_api": "ok",
            "audit_log": "ok",
        },
    }


@router.get("/stats")
async def stats():
    """System-wide statistics."""
    sensor_stats = _sensors.get_stats()
    dataset_stats = _dataset.get_stats()
    return {
        "timestamp": time.time(),
        "sensors": sensor_stats,
        "dataset": dataset_stats,
        "safety_overrides": len(_safety.get_overrides()),
    }


@router.post("/safety/override")
async def safety_override(body: SafetyOverrideRequest):
    """Admin override for a blocked safety action."""
    record = _safety.override(
        action_id=body.action_id,
        admin_id=body.admin_id,
        reason=body.reason,
    )
    _audit.log(
        AuditEvent.SAFETY_OVERRIDE,
        actor=body.admin_id,
        target=body.action_id,
        status="override",
        metadata={"reason": body.reason},
    )
    logger.warning(
        "Safety override: action=%s admin=%s reason=%s",
        body.action_id, body.admin_id, body.reason
    )
    return {
        "overridden": True,
        "action_id": record.action_id,
        "admin_id": record.admin_id,
        "timestamp": record.timestamp,
    }


@router.get("/safety/overrides")
async def list_overrides():
    """List recent safety overrides."""
    overrides = _safety.get_overrides(limit=50)
    return {
        "count": len(overrides),
        "overrides": [
            {
                "action_id": o.action_id,
                "admin_id": o.admin_id,
                "reason": o.reason,
                "timestamp": o.timestamp,
            }
            for o in overrides
        ],
    }


@router.delete("/memory/expired")
async def purge_expired_memories():
    """Delete all expired memory entries."""
    count = _memory.delete_expired()
    _audit.log(
        AuditEvent.ADMIN_PURGE,
        actor="system",
        status="ok",
        metadata={"deleted_count": count},
    )
    return {"deleted": count, "message": f"Purged {count} expired memory entries"}


@router.get("/dataset/stats")
async def dataset_stats():
    """Dataset statistics and entry counts by category."""
    return _dataset.get_stats()


@router.get("/dataset/export")
async def export_dataset(category: str | None = None):
    """Export dataset entries (optionally filtered by category)."""
    _audit.log(
        AuditEvent.ADMIN_EXPORT_DATASET,
        actor="admin",
        status="ok",
        metadata={"category": category or "all"},
    )
    data = _dataset.export_dataset(category=category)
    return {
        "category": category or "all",
        "count": len(data),
        "entries": data,
    }


@router.get("/audit")
async def audit_recent(limit: int = 50, event: str | None = None):
    """
    Recent audit log entries.

    Returns up to *limit* recent records (max 200), newest first.
    Sensitive field values are already masked in the store — payloads are safe.
    Optionally filter by *event* type (e.g. 'memory.store').
    """
    limit = min(limit, 200)
    records = _audit.recent(limit=limit, event_filter=event)
    return {
        "count": len(records),
        "limit": limit,
        "event_filter": event,
        "records": records,
    }


@router.get("/audit/compliance")
async def audit_compliance():
    """
    Compliance/audit summary — aggregate counts and retention info.
    No sensitive payloads are returned.
    """
    stats = _audit.compliance_stats()
    return {
        "product": "Orkavia AI-OS Nexus",
        "copyright": "© 2026 Fasih ur Rehman. All Rights Reserved.",
        "generated_at": time.time(),
        **stats,
    }


def _format_uptime(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}h {m}m {s}s"
    if m > 0:
        return f"{m}m {s}s"
    return f"{s}s"
