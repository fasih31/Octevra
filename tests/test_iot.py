"""Tests for IoT sensor API, fake sensor generator, and domain rules."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from ai_os_nexus.iot.sensor_api import SensorManager
from ai_os_nexus.iot.fake_sensors import FakeSensorGenerator
from ai_os_nexus.iot.rules.irrigation_rules import should_irrigate, emergency_shutoff
from ai_os_nexus.iot.rules.hospital_rules import check_vitals, escalation_level


# ---------------------------------------------------------------------------
# SensorManager
# ---------------------------------------------------------------------------

def make_sensor_mgr(tmp_path: Path) -> SensorManager:
    return SensorManager(db_path=tmp_path / "test_sensors.db")


def test_sensor_ingest_and_latest(tmp_path):
    sm = make_sensor_mgr(tmp_path)
    sm.ingest("soil-001", {"moisture": 45.5, "temperature": 22.0})
    reading = sm.get_latest("soil-001")
    assert reading is not None
    assert reading.sensor_id == "soil-001"
    assert reading.data["moisture"] == 45.5


def test_sensor_history(tmp_path):
    sm = make_sensor_mgr(tmp_path)
    for i in range(5):
        sm.ingest("temp-001", {"temperature": 20 + i})
        time.sleep(0.01)
    history = sm.get_history("temp-001", hours=1)
    assert len(history) == 5


def test_sensor_list(tmp_path):
    sm = make_sensor_mgr(tmp_path)
    sm.ingest("s1", {"v": 1})
    sm.ingest("s2", {"v": 2})
    sm.ingest("s3", {"v": 3})
    sensors = sm.list_sensors()
    assert "s1" in sensors
    assert "s2" in sensors
    assert "s3" in sensors


def test_sensor_latest_none(tmp_path):
    sm = make_sensor_mgr(tmp_path)
    reading = sm.get_latest("nonexistent-sensor")
    assert reading is None


def test_sensor_trigger_fires(tmp_path):
    sm = make_sensor_mgr(tmp_path)
    fired_events = []

    rule_id = sm.register_trigger(
        sensor_id="pressure-001",
        field="pressure",
        operator="gt",
        threshold=8.0,
        action="EMERGENCY_SHUTOFF",
        callback=lambda e: fired_events.append(e),
    )
    assert rule_id != ""

    # Normal reading — should not fire
    sm.ingest("pressure-001", {"pressure": 3.5})
    assert len(fired_events) == 0

    # Over threshold — should fire
    sm.ingest("pressure-001", {"pressure": 9.5})
    assert len(fired_events) == 1
    assert fired_events[0]["action"] == "EMERGENCY_SHUTOFF"


def test_sensor_trigger_lt(tmp_path):
    sm = make_sensor_mgr(tmp_path)
    fired = []
    sm.register_trigger("moisture-001", "moisture", "lt", 30.0, "IRRIGATE", lambda e: fired.append(e))
    sm.ingest("moisture-001", {"moisture": 45.0})  # No trigger
    assert len(fired) == 0
    sm.ingest("moisture-001", {"moisture": 20.0})  # Trigger
    assert len(fired) == 1


def test_sensor_stats(tmp_path):
    sm = make_sensor_mgr(tmp_path)
    sm.ingest("stats-sensor", {"value": 1})
    sm.ingest("stats-sensor", {"value": 2})
    stats = sm.get_stats()
    assert stats["total_readings"] >= 2


# ---------------------------------------------------------------------------
# FakeSensorGenerator
# ---------------------------------------------------------------------------

def test_fake_irrigation(tmp_path):
    gen = FakeSensorGenerator(seed=42)
    dp = gen.generate_irrigation_data("irr-test")
    assert dp.sensor_id == "irr-test"
    data = dp.data
    assert "soil_moisture" in data
    assert "temperature" in data
    assert "rain_probability" in data
    assert 0 <= data["rain_probability"] <= 1


def test_fake_hospital():
    gen = FakeSensorGenerator(seed=99)
    dp = gen.generate_hospital_data("hosp-test")
    data = dp.data
    assert "heart_rate" in data
    assert "oxygen" in data
    assert "bp_systolic" in data
    assert 0 < data["heart_rate"] < 300  # Reasonable range


def test_fake_industrial():
    gen = FakeSensorGenerator(seed=7)
    dp = gen.generate_industrial_data("ind-test")
    data = dp.data
    assert "pressure" in data
    assert "temperature" in data
    assert "vibration" in data


def test_fake_anomaly_rate():
    """With anomaly_rate=1.0, all readings should be anomalies."""
    gen = FakeSensorGenerator(anomaly_rate=1.0, seed=0)
    for _ in range(10):
        dp = gen.generate_irrigation_data()
        assert dp.is_anomaly is True


def test_fake_no_anomaly():
    """With anomaly_rate=0.0, no readings should be anomalies."""
    gen = FakeSensorGenerator(anomaly_rate=0.0, seed=0)
    for _ in range(10):
        dp = gen.generate_hospital_data()
        assert dp.is_anomaly is False


def test_fake_batch_generate():
    gen = FakeSensorGenerator(seed=1)
    batch = gen.batch_generate("irrigation", count=5, sensor_id="batch-001")
    assert len(batch) == 5
    assert all(dp.sensor_id == "batch-001" for dp in batch)


# ---------------------------------------------------------------------------
# Irrigation Rules
# ---------------------------------------------------------------------------

def test_should_irrigate_dry_soil():
    d = should_irrigate(soil_moisture=25, temperature=28, rain_probability=0.1)
    assert d.action == "IRRIGATE"
    assert d.confidence > 0.7
    assert d.domain == "irrigation"


def test_should_not_irrigate_wet_soil():
    d = should_irrigate(soil_moisture=80, temperature=20, rain_probability=0.2)
    assert d.action == "NO_IRRIGATE"
    assert d.confidence > 0.8


def test_should_defer_high_rain():
    d = should_irrigate(soil_moisture=40, temperature=25, rain_probability=0.85)
    assert d.action in ("DEFER", "NO_IRRIGATE")


def test_emergency_shutoff_high_pressure():
    result = emergency_shutoff(pressure=9.5, flow_rate=10.0)
    assert result is True


def test_emergency_shutoff_high_flow():
    result = emergency_shutoff(pressure=3.0, flow_rate=60.0)
    assert result is True


def test_no_emergency_normal():
    result = emergency_shutoff(pressure=3.0, flow_rate=15.0)
    assert result is False


def test_should_irrigate_emergency_shutoff():
    d = should_irrigate(soil_moisture=30, temperature=25, rain_probability=0.1, pressure=10.0)
    assert d.action == "EMERGENCY_SHUTOFF"


# ---------------------------------------------------------------------------
# Hospital Rules
# ---------------------------------------------------------------------------

def test_normal_vitals():
    alert = check_vitals(
        heart_rate=75, bp_systolic=118, bp_diastolic=76,
        oxygen=97.5, temperature=36.8, respiratory_rate=16
    )
    assert alert.alert_type == "NORMAL"
    assert escalation_level(alert) == "normal"


def test_critical_low_oxygen():
    alert = check_vitals(
        heart_rate=90, bp_systolic=115, bp_diastolic=75,
        oxygen=88.0, temperature=36.8
    )
    assert alert.alert_type == "CRITICAL"
    assert escalation_level(alert) == "critical"
    assert any("HYPOXIA" in f for f in alert.flags)


def test_critical_tachycardia():
    alert = check_vitals(
        heart_rate=180, bp_systolic=115, bp_diastolic=75,
        oxygen=97.0, temperature=37.0
    )
    assert alert.alert_type == "CRITICAL"
    assert any("HEART_RATE" in f for f in alert.flags)


def test_critical_hypertensive_crisis():
    alert = check_vitals(
        heart_rate=85, bp_systolic=185, bp_diastolic=122,
        oxygen=97.0, temperature=37.0
    )
    assert alert.alert_type == "CRITICAL"
    assert any("HYPERTENSIVE" in f for f in alert.flags)


def test_critical_hypothermia():
    alert = check_vitals(
        heart_rate=50, bp_systolic=100, bp_diastolic=65,
        oxygen=93.0, temperature=33.5
    )
    assert alert.alert_type == "CRITICAL"
    assert any("HYPOTHERMIA" in f for f in alert.flags)


def test_warning_high_bp():
    alert = check_vitals(
        heart_rate=75, bp_systolic=145, bp_diastolic=92,
        oxygen=97.0, temperature=37.0
    )
    assert alert.alert_type == "WARNING"
    assert escalation_level(alert) == "warning"


def test_escalation_level_mapping():
    for t, expected in [("NORMAL", "normal"), ("WARNING", "warning"), ("CRITICAL", "critical")]:
        from ai_os_nexus.iot.rules.hospital_rules import Alert
        a = Alert(patient_id="p1", alert_type=t, message="test", vitals={})
        assert escalation_level(a) == expected
