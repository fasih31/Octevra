"""
Fake Sensor Generator — realistic IoT data with occasional anomalies.
Used for demos, testing, and seeding the sensor dataset.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SensorDataPoint:
    sensor_id: str
    data: dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    is_anomaly: bool = False


class FakeSensorGenerator:
    """Generates realistic sensor data with configurable anomaly rate."""

    def __init__(self, anomaly_rate: float = 0.05, seed: int | None = None) -> None:
        self._anomaly_rate = anomaly_rate
        if seed is not None:
            random.seed(seed)

    def _is_anomaly(self) -> bool:
        return random.random() < self._anomaly_rate

    # ------------------------------------------------------------------
    def generate_irrigation_data(self, sensor_id: str = "irr-001") -> SensorDataPoint:
        """Realistic soil/weather sensor data for irrigation control."""
        anomaly = self._is_anomaly()
        if anomaly:
            # Simulate a faulty pressure sensor or drought condition
            return SensorDataPoint(
                sensor_id=sensor_id,
                data={
                    "soil_moisture": round(random.uniform(5, 20), 2),   # Critically low
                    "temperature": round(random.uniform(38, 45), 2),    # Heat wave
                    "rain_probability": round(random.uniform(0, 0.05), 3),
                    "pressure": round(random.uniform(9, 12), 2),        # Over-pressure
                    "flow_rate": round(random.uniform(55, 80), 2),      # Excessive flow
                    "humidity": round(random.uniform(10, 25), 2),
                    "wind_speed": round(random.uniform(0, 5), 2),
                    "battery_level": round(random.uniform(10, 30), 2),
                },
                is_anomaly=True,
            )
        # Normal reading
        t = time.time()
        # Simulate diurnal temperature cycle
        hour = (t % 86400) / 3600
        temp_base = 22 + 8 * math.sin((hour - 6) * math.pi / 12)
        return SensorDataPoint(
            sensor_id=sensor_id,
            data={
                "soil_moisture": round(random.gauss(45, 10), 2),
                "temperature": round(temp_base + random.gauss(0, 1.5), 2),
                "rain_probability": round(random.uniform(0.1, 0.6), 3),
                "pressure": round(random.gauss(3.5, 0.3), 2),
                "flow_rate": round(random.gauss(15, 3), 2),
                "humidity": round(random.gauss(55, 10), 2),
                "wind_speed": round(random.gauss(8, 3), 2),
                "battery_level": round(random.uniform(60, 100), 2),
            },
        )

    # ------------------------------------------------------------------
    def generate_hospital_data(self, sensor_id: str = "hosp-001") -> SensorDataPoint:
        """Patient vital signs from a bedside monitor."""
        anomaly = self._is_anomaly()
        if anomaly:
            anomaly_type = random.choice(["hypoxia", "tachycardia", "hypertension", "hypothermia"])
            if anomaly_type == "hypoxia":
                data = {
                    "heart_rate": random.randint(90, 120),
                    "bp_systolic": random.randint(90, 110),
                    "bp_diastolic": random.randint(60, 75),
                    "oxygen": round(random.uniform(82, 89), 1),   # Critically low
                    "temperature": round(random.gauss(36.8, 0.3), 1),
                    "respiratory_rate": random.randint(24, 32),
                    "alert_type": "HYPOXIA",
                }
            elif anomaly_type == "tachycardia":
                data = {
                    "heart_rate": random.randint(150, 200),        # Critical
                    "bp_systolic": random.randint(90, 130),
                    "bp_diastolic": random.randint(50, 80),
                    "oxygen": round(random.uniform(92, 97), 1),
                    "temperature": round(random.gauss(37.2, 0.5), 1),
                    "respiratory_rate": random.randint(20, 28),
                    "alert_type": "TACHYCARDIA",
                }
            elif anomaly_type == "hypertension":
                data = {
                    "heart_rate": random.randint(80, 100),
                    "bp_systolic": random.randint(180, 220),       # Critical
                    "bp_diastolic": random.randint(120, 140),
                    "oxygen": round(random.uniform(93, 98), 1),
                    "temperature": round(random.gauss(37.0, 0.4), 1),
                    "respiratory_rate": random.randint(16, 22),
                    "alert_type": "HYPERTENSIVE_CRISIS",
                }
            else:  # hypothermia
                data = {
                    "heart_rate": random.randint(45, 55),
                    "bp_systolic": random.randint(90, 110),
                    "bp_diastolic": random.randint(60, 70),
                    "oxygen": round(random.uniform(90, 95), 1),
                    "temperature": round(random.uniform(33.0, 34.5), 1),  # Critical
                    "respiratory_rate": random.randint(8, 12),
                    "alert_type": "HYPOTHERMIA",
                }
            return SensorDataPoint(sensor_id=sensor_id, data=data, is_anomaly=True)

        # Normal vitals
        return SensorDataPoint(
            sensor_id=sensor_id,
            data={
                "heart_rate": random.randint(62, 90),
                "bp_systolic": random.randint(110, 130),
                "bp_diastolic": random.randint(70, 85),
                "oxygen": round(random.uniform(96, 99.5), 1),
                "temperature": round(random.gauss(36.8, 0.3), 1),
                "respiratory_rate": random.randint(14, 18),
                "alert_type": "NORMAL",
            },
        )

    # ------------------------------------------------------------------
    def generate_industrial_data(self, sensor_id: str = "ind-001") -> SensorDataPoint:
        """Industrial machinery sensor readings."""
        anomaly = self._is_anomaly()
        if anomaly:
            return SensorDataPoint(
                sensor_id=sensor_id,
                data={
                    "pressure": round(random.uniform(14, 18), 2),      # Over limit
                    "temperature": round(random.uniform(140, 175), 2), # Overheating
                    "vibration": round(random.uniform(3.5, 6.0), 3),   # Excessive
                    "flow_rate": round(random.uniform(150, 200), 2),
                    "rpm": random.randint(3500, 4500),
                    "current_draw": round(random.uniform(45, 60), 2),
                    "status": "FAULT",
                },
                is_anomaly=True,
            )
        return SensorDataPoint(
            sensor_id=sensor_id,
            data={
                "pressure": round(random.gauss(5.5, 0.8), 2),
                "temperature": round(random.gauss(65, 8), 2),
                "vibration": round(random.gauss(0.8, 0.2), 3),
                "flow_rate": round(random.gauss(95, 10), 2),
                "rpm": random.randint(2800, 3200),
                "current_draw": round(random.gauss(28, 3), 2),
                "status": "OK",
            },
        )

    # ------------------------------------------------------------------
    def batch_generate(
        self,
        sensor_type: str,
        count: int = 10,
        sensor_id: str | None = None,
    ) -> list[SensorDataPoint]:
        """Generate multiple readings of the same type."""
        generators = {
            "irrigation": self.generate_irrigation_data,
            "hospital": self.generate_hospital_data,
            "industrial": self.generate_industrial_data,
        }
        gen = generators.get(sensor_type, self.generate_industrial_data)
        kwargs = {"sensor_id": sensor_id} if sensor_id else {}
        return [gen(**kwargs) for _ in range(count)]
