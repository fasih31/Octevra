"""
/sensor endpoints — ingest sensor data, query latest readings, manage triggers.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ai_os_nexus.iot.sensor_api import SensorManager
from ai_os_nexus.dataset.dataset_manager import DatasetManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sensor", tags=["sensor"])

_sensors = SensorManager()
_dataset = DatasetManager()


class IngestRequest(BaseModel):
    sensor_id: str = Field(..., min_length=1, max_length=128)
    data: dict[str, Any]
    timestamp: Optional[float] = None
    source: str = Field("api", max_length=64)


class TriggerRequest(BaseModel):
    sensor_id: str
    field: str
    operator: str = Field(..., pattern="^(gt|lt|gte|lte|eq)$")
    threshold: float
    action: str


class SensorReadingOut(BaseModel):
    sensor_id: str
    timestamp: float
    data: dict[str, Any]
    source: str


@router.post("/ingest", status_code=201)
async def ingest_sensor(body: IngestRequest):
    """Ingest a sensor reading into the system."""
    reading_id = _sensors.ingest(
        sensor_id=body.sensor_id,
        data=body.data,
        timestamp=body.timestamp,
        source=body.source,
    )
    # Log to dataset
    import json
    _dataset.add_entry(
        category="sensor_log",
        content=f"Sensor {body.sensor_id}: {json.dumps(body.data)}",
        source=f"sensor:{body.sensor_id}",
        metadata={"sensor_id": body.sensor_id, "source": body.source},
    )
    return {"reading_id": reading_id, "sensor_id": body.sensor_id, "status": "ingested"}


@router.get("/{sensor_id}/latest", response_model=Optional[SensorReadingOut])
async def get_latest(sensor_id: str):
    """Get the most recent reading for a sensor."""
    reading = _sensors.get_latest(sensor_id)
    if not reading:
        raise HTTPException(status_code=404, detail=f"No data found for sensor '{sensor_id}'")
    return SensorReadingOut(
        sensor_id=reading.sensor_id,
        timestamp=reading.timestamp,
        data=reading.data,
        source=reading.source,
    )


@router.get("/{sensor_id}/history")
async def get_history(sensor_id: str, hours: float = 24):
    """Get historical readings for a sensor (default: last 24 hours)."""
    if hours > 720:
        hours = 720  # max 30 days
    readings = _sensors.get_history(sensor_id, hours=hours)
    return {
        "sensor_id": sensor_id,
        "hours": hours,
        "count": len(readings),
        "readings": [
            {"timestamp": r.timestamp, "data": r.data, "source": r.source}
            for r in readings
        ],
    }


@router.get("/")
async def list_sensors():
    """List all known sensor IDs."""
    return {"sensors": _sensors.list_sensors(), "stats": _sensors.get_stats()}


@router.get("/latest-all")
async def get_all_latest():
    """Return the latest reading for every known sensor (dashboard view)."""
    sensor_ids = _sensors.list_sensors()
    sensors = []
    for sid in sensor_ids:
        reading = _sensors.get_latest(sid)
        if reading:
            sensors.append({
                "sensor_id": reading.sensor_id,
                "sensor_type": reading.data.get("sensor_type", reading.source),
                "timestamp": reading.timestamp,
                **reading.data,
            })
    return {"count": len(sensors), "sensors": sensors}


@router.post("/trigger", status_code=201)
async def register_trigger(body: TriggerRequest):
    """Register an alert trigger for a sensor field."""
    rule_id = _sensors.register_trigger(
        sensor_id=body.sensor_id,
        field=body.field,
        operator=body.operator,
        threshold=body.threshold,
        action=body.action,
    )
    return {"rule_id": rule_id, "message": "Trigger registered", "trigger": body.model_dump()}
