"""
/decide endpoint — expose the Decision Engine and sensor simulation.
Runs domain rules (irrigation / hospital / industrial) against provided
context and returns a structured Decision with confidence scoring.

Also provides /sensor/simulate for live demo data injection.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ai_os_nexus.core.decision_engine import DecisionEngine
from ai_os_nexus.core.safety_layer import SafetyLayer
from ai_os_nexus.iot.fake_sensors import FakeSensorGenerator
from ai_os_nexus.iot.sensor_api import SensorManager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["decide"])

_engine  = DecisionEngine()
_safety  = SafetyLayer()
_sensors = SensorManager()
_gen     = FakeSensorGenerator(anomaly_rate=0.15)


# ── Models ────────────────────────────────────────────────────────────────

class DecideRequest(BaseModel):
    domain: str  = Field(..., pattern="^(irrigation|hospital|industrial|general)$")
    context: dict[str, Any] = Field(default_factory=dict)
    apply_safety: bool = Field(True, description="Run safety layer validation after decision")


class DecideResponse(BaseModel):
    domain: str
    action: str
    confidence: float
    reasoning: str
    requires_human_approval: bool
    safety_flags: list[str]
    safety_allowed: bool
    safety_reason: str
    risk_level: str
    latency_ms: float
    timestamp: float


class SimulateRequest(BaseModel):
    sensor_type: str = Field(..., pattern="^(irrigation|hospital|industrial)$")
    sensor_id:   Optional[str] = None
    count:       int  = Field(1, ge=1, le=20)
    with_decision: bool = True


# ── Routes ────────────────────────────────────────────────────────────────

@router.post("/decide", response_model=DecideResponse)
async def decide(body: DecideRequest):
    """
    Run the Decision Engine for a given domain and sensor context.
    Returns the recommended action with confidence, reasoning, and safety check.
    """
    t0 = time.time()
    ctx = dict(body.context)
    ctx["domain"] = body.domain

    decision = _engine.decide(ctx)

    safety_allowed = True
    safety_reason  = "No safety checks required"
    risk_level     = "LOW"

    if body.apply_safety:
        result = _safety.check(
            action=decision.action,
            context={**ctx, "confidence": decision.confidence},
        )
        safety_allowed = result.allowed
        safety_reason  = result.reason
        risk_level     = result.risk_level.value

    latency = (time.time() - t0) * 1000
    return DecideResponse(
        domain=decision.domain,
        action=decision.action,
        confidence=round(decision.confidence, 4),
        reasoning=decision.reasoning,
        requires_human_approval=decision.requires_human_approval,
        safety_flags=decision.safety_flags,
        safety_allowed=safety_allowed,
        safety_reason=safety_reason,
        risk_level=risk_level,
        latency_ms=round(latency, 2),
        timestamp=time.time(),
    )


@router.post("/sensor/simulate")
async def simulate_sensors(body: SimulateRequest):
    """
    Generate realistic fake sensor readings and (optionally) run the decision engine.
    Automatically ingests the data into the sensor store.
    """
    generators = {
        "irrigation": _gen.generate_irrigation_data,
        "hospital":   _gen.generate_hospital_data,
        "industrial": _gen.generate_industrial_data,
    }
    gen_fn = generators[body.sensor_type]

    sensor_id = body.sensor_id or f"{body.sensor_type[:3]}-{int(time.time()) % 1000:03d}"
    results = []

    for _ in range(body.count):
        point = gen_fn(sensor_id=sensor_id)

        # Persist to sensor store
        reading_id = _sensors.ingest(
            sensor_id=point.sensor_id,
            data=point.data,
            source="simulate",
        )

        entry: dict[str, Any] = {
            "reading_id": reading_id,
            "sensor_id": point.sensor_id,
            "data": point.data,
            "is_anomaly": point.is_anomaly,
            "timestamp": point.timestamp,
        }

        if body.with_decision:
            ctx = dict(point.data)
            ctx["domain"] = body.sensor_type
            decision = _engine.decide(ctx)
            safety   = _safety.check(
                action=decision.action,
                context={**ctx, "confidence": decision.confidence},
            )
            entry["decision"] = {
                "action": decision.action,
                "confidence": round(decision.confidence, 4),
                "reasoning": decision.reasoning,
                "requires_human_approval": decision.requires_human_approval,
                "safety_flags": decision.safety_flags,
                "safety_allowed": safety.allowed,
                "risk_level": safety.risk_level.value,
            }

        results.append(entry)

    return {
        "sensor_type": body.sensor_type,
        "sensor_id": sensor_id,
        "count": len(results),
        "results": results,
    }


@router.get("/sensor/live-stream")
async def live_stream(sensor_type: str = "irrigation", interval_ms: int = 2000):
    """
    SSE endpoint — streams simulated sensor readings + decisions in real time.
    Connect with EventSource('/sensor/live-stream?sensor_type=hospital').
    """
    import asyncio
    import json

    sensor_type = sensor_type if sensor_type in ("irrigation", "hospital", "industrial") else "irrigation"
    generators  = {
        "irrigation": _gen.generate_irrigation_data,
        "hospital":   _gen.generate_hospital_data,
        "industrial": _gen.generate_industrial_data,
    }
    gen_fn    = generators[sensor_type]
    sensor_id = f"{sensor_type[:3]}-live"
    interval  = max(500, min(interval_ms, 10_000)) / 1000

    async def event_generator():
        for _ in range(60):          # max 60 events per connection
            point   = gen_fn(sensor_id=sensor_id)
            ctx     = dict(point.data)
            ctx["domain"] = sensor_type
            decision = _engine.decide(ctx)
            safety   = _safety.check(
                action=decision.action,
                context={**ctx, "confidence": decision.confidence},
            )

            payload = {
                "sensor_id":  point.sensor_id,
                "data":       point.data,
                "is_anomaly": point.is_anomaly,
                "timestamp":  time.time(),
                "decision": {
                    "action":     decision.action,
                    "confidence": round(decision.confidence, 4),
                    "reasoning":  decision.reasoning,
                    "requires_human_approval": decision.requires_human_approval,
                    "safety_flags": decision.safety_flags,
                    "safety_allowed": safety.allowed,
                    "risk_level":   safety.risk_level.value,
                },
            }
            yield f"data: {json.dumps(payload)}\n\n"
            await asyncio.sleep(interval)
        yield "data: {\"__done__\": true}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/decide/history")
async def decision_history(limit: int = 20):
    """Return recent decisions from the engine's in-memory history."""
    limit = min(limit, 100)
    history = _engine.get_history(limit)
    return {
        "count": len(history),
        "decisions": [
            {
                "action":   d.action,
                "confidence": d.confidence,
                "reasoning": d.reasoning,
                "domain":   d.domain,
                "requires_human_approval": d.requires_human_approval,
                "safety_flags": d.safety_flags,
                "timestamp": d.timestamp,
            }
            for d in history
        ],
    }
