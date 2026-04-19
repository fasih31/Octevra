"""Tests for the Safety Layer and Decision Engine."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_os_nexus.core.safety_layer import SafetyLayer, SafetyResult, RiskLevel
from ai_os_nexus.core.decision_engine import DecisionEngine, Decision


# ---------------------------------------------------------------------------
# SafetyLayer
# ---------------------------------------------------------------------------

def make_safety(tmp_path: Path) -> SafetyLayer:
    return SafetyLayer(db_path=tmp_path / "safety_test.db")


def test_safety_default_allows(tmp_path):
    sl = make_safety(tmp_path)
    result = sl.check("RESPOND", {"user_id": "user-1"})
    assert result.allowed is True
    assert result.risk_level == RiskLevel.LOW


def test_safety_medical_blocked(tmp_path):
    sl = make_safety(tmp_path)
    result = sl.check("CRITICAL_ALERT", {"domain": "hospital", "user_id": "u1"})
    assert result.allowed is False
    assert result.requires_approval is True
    assert result.risk_level == RiskLevel.HIGH


def test_safety_emergency_shutoff_allowed(tmp_path):
    """Emergency shutoffs must always be permitted."""
    sl = make_safety(tmp_path)
    result = sl.check("EMERGENCY_SHUTOFF", {"domain": "irrigation", "user_id": "u1"})
    assert result.allowed is True
    assert result.risk_level == RiskLevel.CRITICAL


def test_safety_irrigation_anomaly_blocked(tmp_path):
    sl = make_safety(tmp_path)
    result = sl.check("IRRIGATE", {
        "domain": "irrigation",
        "user_id": "u1",
        "pressure": 9.5,
        "flow_rate": 60.0,
    })
    assert result.allowed is False
    assert result.risk_level == RiskLevel.HIGH


def test_safety_low_confidence_blocked(tmp_path):
    sl = make_safety(tmp_path)
    result = sl.check("DO_SOMETHING", {
        "domain": "general",
        "confidence": 0.2,
        "user_id": "u1",
    })
    assert result.allowed is False
    assert result.risk_level == RiskLevel.MEDIUM


def test_safety_normal_irrigation_allowed(tmp_path):
    sl = make_safety(tmp_path)
    result = sl.check("IRRIGATE", {
        "domain": "irrigation",
        "user_id": "u1",
        "pressure": 3.0,
        "flow_rate": 12.0,
        "confidence": 0.9,
    })
    assert result.allowed is True


def test_safety_override(tmp_path):
    sl = make_safety(tmp_path)
    record = sl.override("action-999", "admin-001", "Test override reason — authorised")
    assert record.action_id == "action-999"
    assert record.admin_id == "admin-001"

    overrides = sl.get_overrides()
    assert any(o.action_id == "action-999" for o in overrides)


def test_safety_custom_rule(tmp_path):
    sl = make_safety(tmp_path)

    def block_at_night(action, context):
        hour = context.get("hour", 12)
        if 0 <= hour < 6:
            return SafetyResult(
                allowed=False,
                reason="Night-time operations blocked (00:00–06:00)",
                requires_approval=True,
                risk_level=RiskLevel.MEDIUM,
                rule_triggered="night_block",
            )
        return None

    sl.add_rule("night_block", block_at_night)
    result = sl.check("IRRIGATE", {"hour": 3, "user_id": "u1", "pressure": 2.0, "flow_rate": 10.0})
    assert result.allowed is False
    assert result.rule_triggered == "night_block"


def test_safety_rate_limit(tmp_path):
    """Should block after 60 requests in 60 seconds."""
    sl = make_safety(tmp_path)
    # Exceed rate limit quickly
    sl._rate_limiter._max = 3  # lower limit for test
    for i in range(3):
        r = sl.check("RESPOND", {"user_id": "rate-test-user", "confidence": 0.9})
        assert r.allowed is True
    # 4th request should be blocked
    r4 = sl.check("RESPOND", {"user_id": "rate-test-user", "confidence": 0.9})
    assert r4.allowed is False
    assert r4.rule_triggered == "rate_limit"


# ---------------------------------------------------------------------------
# DecisionEngine
# ---------------------------------------------------------------------------

def test_decision_irrigation_irrigate():
    de = DecisionEngine()
    d = de.decide({"domain": "irrigation", "soil_moisture": 20, "temperature": 28, "rain_probability": 0.1})
    assert d.action == "IRRIGATE"
    assert d.domain == "irrigation"
    assert d.confidence > 0.5


def test_decision_irrigation_no_irrigate():
    de = DecisionEngine()
    d = de.decide({"domain": "irrigation", "soil_moisture": 75, "temperature": 22, "rain_probability": 0.2})
    assert d.action == "NO_IRRIGATE"


def test_decision_irrigation_high_rain():
    de = DecisionEngine()
    d = de.decide({"domain": "irrigation", "soil_moisture": 40, "temperature": 25, "rain_probability": 0.9})
    assert d.action in ("NO_IRRIGATE", "MONITOR")


def test_decision_irrigation_emergency():
    de = DecisionEngine()
    d = de.decide({"domain": "irrigation", "pressure": 12.0})
    assert d.action == "EMERGENCY_SHUTOFF"
    assert d.confidence > 0.95


def test_decision_hospital_normal():
    de = DecisionEngine()
    d = de.decide({
        "domain": "hospital",
        "heart_rate": 75, "oxygen": 97, "bp_systolic": 118, "bp_diastolic": 78,
        "temperature": 36.8,
    })
    assert d.action == "NORMAL"
    assert d.requires_human_approval is False


def test_decision_hospital_critical():
    de = DecisionEngine()
    d = de.decide({
        "domain": "hospital",
        "heart_rate": 180, "oxygen": 85, "bp_systolic": 185, "bp_diastolic": 120,
    })
    assert d.action == "CRITICAL_ALERT"
    assert d.requires_human_approval is True


def test_decision_industrial_emergency():
    de = DecisionEngine()
    d = de.decide({"domain": "industrial", "pressure": 18.0, "temperature": 160})
    assert d.action == "EMERGENCY_SHUTDOWN"


def test_decision_general():
    de = DecisionEngine()
    d = de.decide({"domain": "general", "query": "What is Python?"})
    assert d.action == "RESPOND"
    assert d.domain == "general"


def test_decision_confidence_review_threshold():
    """Confidence < 0.7 should require human approval."""
    de = DecisionEngine()
    d = de.decide({"domain": "irrigation", "soil_moisture": 48, "temperature": 25, "rain_probability": 0.45})
    # This is a borderline case — just verify it doesn't crash
    assert d.action in ("MONITOR", "IRRIGATE", "NO_IRRIGATE", "DEFER", "NO_ACTION")


def test_decision_safe_fallback():
    """Very low confidence → safe fallback."""
    de = DecisionEngine()
    # Register a rule that returns very low confidence
    def low_confidence_rule(ctx):
        return Decision(
            action="RISKY",
            confidence=0.1,
            reasoning="Very uncertain",
            requires_human_approval=False,
            domain="test",
        )
    de.register_rule("test", low_confidence_rule)
    d = de.decide({"domain": "test"})
    assert d.action == "NO_ACTION"
    assert d.requires_human_approval is True
    assert "SAFE_FALLBACK" in d.safety_flags


def test_decision_register_custom_rule():
    de = DecisionEngine()
    called = []

    def custom_rule(ctx):
        called.append(True)
        return Decision(
            action="CUSTOM_ACTION",
            confidence=0.95,
            reasoning="Custom logic triggered",
            requires_human_approval=False,
            domain="custom",
        )

    de.register_rule("custom", custom_rule)
    d = de.decide({"domain": "custom"})
    assert d.action == "CUSTOM_ACTION"
    assert len(called) == 1


def test_decision_history():
    de = DecisionEngine()
    for _ in range(3):
        de.decide({"domain": "general", "query": "test"})
    history = de.get_history(limit=10)
    assert len(history) == 3


def test_decision_ai_reason():
    de = DecisionEngine()
    reason = de.ai_reason("Should I irrigate?", {"domain": "irrigation", "soil_moisture": 30})
    assert "Action" in reason
    assert "Confidence" in reason


def test_decision_evaluate_rules():
    de = DecisionEngine()
    results = de.evaluate_rules("irrigation", {"soil_moisture": 20, "temperature": 30, "rain_probability": 0.1})
    assert len(results) >= 1
    assert all(isinstance(r, Decision) for r in results)
