"""
IoT Sensor API — ingests, stores, and queries sensor data.
Supports trigger rules for real-time automation.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

DB_PATH = Path("data/sensors.db")


@dataclass
class SensorReading:
    sensor_id: str
    timestamp: float
    data: dict[str, Any]
    source: str = "api"


@dataclass
class TriggerRule:
    rule_id: str
    sensor_id: str
    field: str
    operator: str   # "gt", "lt", "eq", "gte", "lte"
    threshold: float
    action: str
    callback: Optional[Callable] = None


# ---------------------------------------------------------------------------
# SensorManager
# ---------------------------------------------------------------------------

class SensorManager:
    """Manages sensor data ingestion, storage, and trigger evaluation."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._triggers: list[TriggerRule] = []
        self._setup()

    def _setup(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sensor_readings (
                    id        TEXT PRIMARY KEY,
                    sensor_id TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    data_json TEXT NOT NULL,
                    source    TEXT NOT NULL DEFAULT 'api'
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sensor_id ON sensor_readings(sensor_id)"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sensor_ts ON sensor_readings(timestamp)"
            )

    # ------------------------------------------------------------------
    def ingest(
        self,
        sensor_id: str,
        data: dict[str, Any],
        timestamp: float | None = None,
        source: str = "api",
    ) -> str:
        """Store a sensor reading. Returns the row ID."""
        reading_id = str(uuid.uuid4())
        ts = timestamp or time.time()
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO sensor_readings (id, sensor_id, timestamp, data_json, source)
                VALUES (?, ?, ?, ?, ?)
                """,
                (reading_id, sensor_id, ts, json.dumps(data), source),
            )
        logger.debug("Ingested sensor %s at %.0f", sensor_id, ts)
        self.check_triggers(sensor_id, data)
        return reading_id

    def get_latest(self, sensor_id: str) -> Optional[SensorReading]:
        """Get the most recent reading for a sensor."""
        cur = self._conn.execute(
            """
            SELECT sensor_id, timestamp, data_json, source
            FROM sensor_readings
            WHERE sensor_id = ?
            ORDER BY timestamp DESC LIMIT 1
            """,
            (sensor_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return SensorReading(
            sensor_id=row[0],
            timestamp=row[1],
            data=json.loads(row[2]),
            source=row[3],
        )

    def get_history(self, sensor_id: str, hours: float = 24) -> list[SensorReading]:
        """Get readings for a sensor in the last N hours."""
        since = time.time() - hours * 3600
        cur = self._conn.execute(
            """
            SELECT sensor_id, timestamp, data_json, source
            FROM sensor_readings
            WHERE sensor_id = ? AND timestamp >= ?
            ORDER BY timestamp ASC
            """,
            (sensor_id, since),
        )
        return [
            SensorReading(sensor_id=r[0], timestamp=r[1], data=json.loads(r[2]), source=r[3])
            for r in cur.fetchall()
        ]

    def list_sensors(self) -> list[str]:
        """Return a list of all known sensor IDs."""
        cur = self._conn.execute(
            "SELECT DISTINCT sensor_id FROM sensor_readings ORDER BY sensor_id"
        )
        return [row[0] for row in cur.fetchall()]

    # ------------------------------------------------------------------
    def register_trigger(
        self,
        sensor_id: str,
        field: str,
        operator: str,
        threshold: float,
        action: str,
        callback: Callable | None = None,
    ) -> str:
        """Register an alert trigger. Returns rule_id."""
        rule_id = str(uuid.uuid4())
        self._triggers.append(
            TriggerRule(
                rule_id=rule_id,
                sensor_id=sensor_id,
                field=field,
                operator=operator,
                threshold=threshold,
                action=action,
                callback=callback,
            )
        )
        logger.info("Trigger registered: %s %s %s %s → %s", sensor_id, field, operator, threshold, action)
        return rule_id

    def check_triggers(self, sensor_id: str, data: dict) -> list[dict]:
        """Evaluate all triggers for a sensor reading. Returns fired triggers."""
        fired = []
        ops = {
            "gt": lambda v, t: v > t,
            "lt": lambda v, t: v < t,
            "gte": lambda v, t: v >= t,
            "lte": lambda v, t: v <= t,
            "eq": lambda v, t: v == t,
        }
        for rule in self._triggers:
            if rule.sensor_id not in (sensor_id, "*"):
                continue
            value = data.get(rule.field)
            if value is None:
                continue
            try:
                fn = ops.get(rule.operator)
                if fn and fn(float(value), rule.threshold):
                    fired_event = {
                        "rule_id": rule.rule_id,
                        "sensor_id": sensor_id,
                        "field": rule.field,
                        "value": value,
                        "action": rule.action,
                        "timestamp": time.time(),
                    }
                    fired.append(fired_event)
                    logger.warning("Trigger fired: %s → %s", rule.rule_id, rule.action)
                    if rule.callback:
                        try:
                            rule.callback(fired_event)
                        except Exception as exc:
                            logger.error("Trigger callback error: %s", exc)
            except (TypeError, ValueError) as exc:
                logger.debug("Trigger eval error: %s", exc)
        return fired

    def get_stats(self) -> dict:
        cur = self._conn.execute(
            "SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM sensor_readings"
        )
        row = cur.fetchone()
        return {
            "total_readings": row[0],
            "earliest": row[1],
            "latest": row[2],
            "sensor_count": len(self.list_sensors()),
            "trigger_count": len(self._triggers),
        }
