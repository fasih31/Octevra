"""
Decision Engine — AI reasoning + rule-based hybrid.
Supports irrigation, hospital, industrial, and general domains.
Confidence < 0.7 → flag for review; < 0.4 → reject with safe fallback.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

CONFIDENCE_REVIEW = 0.7
CONFIDENCE_REJECT = 0.4


@dataclass
class Decision:
    action: str
    confidence: float              # 0.0 – 1.0
    reasoning: str
    requires_human_approval: bool
    safety_flags: list[str] = field(default_factory=list)
    domain: str = "general"
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Built-in domain rule sets
# ---------------------------------------------------------------------------

def _irrigation_rules(context: dict) -> Decision:
    """Rule-based irrigation decision."""
    moisture = context.get("soil_moisture", 50.0)
    temp = context.get("temperature", 25.0)
    rain_prob = context.get("rain_probability", 0.0)
    pressure = context.get("pressure", 3.0)
    flags = []

    # Safety check
    if pressure > 8.0:
        return Decision(
            action="EMERGENCY_SHUTOFF",
            confidence=0.99,
            reasoning=f"Pressure {pressure} bar exceeds safe limit (8 bar). Emergency shutoff.",
            requires_human_approval=False,
            safety_flags=["HIGH_PRESSURE"],
            domain="irrigation",
        )

    if moisture < 35 and rain_prob < 0.4 and temp < 40:
        confidence = 0.9 - (rain_prob * 0.3)
        action = "IRRIGATE"
        reasoning = (
            f"Soil moisture {moisture}% below threshold (35%). "
            f"Rain probability {rain_prob*100:.0f}%. Temperature {temp}°C. "
            "Irrigation recommended."
        )
    elif moisture > 70:
        confidence = 0.95
        action = "NO_IRRIGATE"
        reasoning = f"Soil moisture {moisture}% is sufficient. No irrigation needed."
    elif rain_prob > 0.7:
        confidence = 0.85
        action = "NO_IRRIGATE"
        reasoning = f"High rain probability ({rain_prob*100:.0f}%). Defer irrigation."
        flags.append("HIGH_RAIN_PROBABILITY")
    else:
        confidence = 0.55
        action = "MONITOR"
        reasoning = "Borderline conditions. Continue monitoring."

    return Decision(
        action=action,
        confidence=confidence,
        reasoning=reasoning,
        requires_human_approval=confidence < CONFIDENCE_REVIEW,
        safety_flags=flags,
        domain="irrigation",
    )


def _hospital_rules(context: dict) -> Decision:
    """Rule-based hospital monitoring decision."""
    hr = context.get("heart_rate", 75)
    spo2 = context.get("oxygen", 98)
    bp_sys = context.get("bp_systolic", 120)
    bp_dia = context.get("bp_diastolic", 80)
    temp = context.get("temperature", 36.5)
    flags = []

    critical = []
    warning = []

    if spo2 < 90:
        critical.append(f"SpO₂ critically low: {spo2}%")
    elif spo2 < 94:
        warning.append(f"SpO₂ low: {spo2}%")

    if hr < 40 or hr > 150:
        critical.append(f"Heart rate critical: {hr} bpm")
    elif hr < 50 or hr > 120:
        warning.append(f"Heart rate abnormal: {hr} bpm")

    if bp_sys > 180 or bp_dia > 120:
        critical.append(f"Hypertensive crisis: {bp_sys}/{bp_dia} mmHg")
    elif bp_sys < 90 or bp_dia < 60:
        critical.append(f"Hypotension: {bp_sys}/{bp_dia} mmHg")

    if temp > 39.5:
        warning.append(f"High fever: {temp}°C")
    elif temp < 35.0:
        critical.append(f"Hypothermia: {temp}°C")

    if critical:
        flags.extend(critical)
        return Decision(
            action="CRITICAL_ALERT",
            confidence=0.97,
            reasoning="Critical vitals detected: " + "; ".join(critical),
            requires_human_approval=True,
            safety_flags=flags,
            domain="hospital",
        )
    if warning:
        flags.extend(warning)
        return Decision(
            action="WARNING_ALERT",
            confidence=0.85,
            reasoning="Warning vitals: " + "; ".join(warning),
            requires_human_approval=True,
            safety_flags=flags,
            domain="hospital",
        )

    return Decision(
        action="NORMAL",
        confidence=0.98,
        reasoning="All vitals within normal ranges.",
        requires_human_approval=False,
        domain="hospital",
    )


def _industrial_rules(context: dict) -> Decision:
    """Rule-based industrial automation decision."""
    pressure = context.get("pressure", 5.0)
    temp = context.get("temperature", 50.0)
    vibration = context.get("vibration", 0.5)
    flow_rate = context.get("flow_rate", 100.0)
    flags = []

    if pressure > 15.0 or temp > 150.0:
        flags.append("CRITICAL_THRESHOLD_EXCEEDED")
        return Decision(
            action="EMERGENCY_SHUTDOWN",
            confidence=0.99,
            reasoning=f"Critical: pressure={pressure} bar, temperature={temp}°C. Safety shutdown.",
            requires_human_approval=False,
            safety_flags=flags,
            domain="industrial",
        )

    if vibration > 3.0:
        flags.append("HIGH_VIBRATION")
        return Decision(
            action="MAINTENANCE_REQUIRED",
            confidence=0.88,
            reasoning=f"Vibration {vibration} mm/s exceeds safe limit. Inspect bearings.",
            requires_human_approval=True,
            safety_flags=flags,
            domain="industrial",
        )

    return Decision(
        action="NORMAL_OPERATION",
        confidence=0.92,
        reasoning="All industrial sensors within operating parameters.",
        requires_human_approval=False,
        domain="industrial",
    )


def _general_rules(context: dict) -> Decision:
    query = str(context.get("query", ""))
    return Decision(
        action="RESPOND",
        confidence=0.8,
        reasoning=f"General query processing: '{query[:80]}'",
        requires_human_approval=False,
        domain="general",
    )


# ---------------------------------------------------------------------------
# DecisionEngine
# ---------------------------------------------------------------------------

class DecisionEngine:
    """
    Evaluates context against registered domain rules,
    applies confidence thresholds, and logs decisions.
    """

    def __init__(self) -> None:
        self._rules: dict[str, list[Callable[[dict], Decision]]] = {
            "irrigation": [_irrigation_rules],
            "hospital": [_hospital_rules],
            "industrial": [_industrial_rules],
            "general": [_general_rules],
        }
        self._history: list[Decision] = []

    # ------------------------------------------------------------------
    def register_rule(self, domain: str, fn: Callable[[dict], Decision]) -> None:
        """Register a custom rule function for a domain."""
        self._rules.setdefault(domain, []).append(fn)

    # ------------------------------------------------------------------
    def decide(self, context: dict) -> Decision:
        """
        Evaluate context, pick the domain, run rules, apply thresholds.
        Returns a Decision with safe fallback for low-confidence scenarios.
        """
        domain = str(context.get("domain", "general")).lower()
        rule_fns = self._rules.get(domain, self._rules["general"])

        decisions: list[Decision] = []
        for fn in rule_fns:
            try:
                d = fn(context)
                decisions.append(d)
            except Exception as exc:
                logger.error("Rule %s failed: %s", fn.__name__, exc)

        if not decisions:
            decision = self._safe_fallback(context)
        else:
            # Take highest-confidence decision
            decision = max(decisions, key=lambda d: d.confidence)

        decision = self._apply_thresholds(decision)
        self._history.append(decision)
        logger.info(
            "Decision: action=%s confidence=%.2f domain=%s",
            decision.action, decision.confidence, decision.domain,
        )
        return decision

    # ------------------------------------------------------------------
    def _apply_thresholds(self, d: Decision) -> Decision:
        if d.confidence < CONFIDENCE_REJECT:
            logger.warning(
                "Low confidence %.2f for action %s — rejecting with safe fallback",
                d.confidence, d.action,
            )
            return self._safe_fallback({"original_action": d.action, "domain": d.domain})
        if d.confidence < CONFIDENCE_REVIEW:
            d.requires_human_approval = True
            if "LOW_CONFIDENCE" not in d.safety_flags:
                d.safety_flags.append("LOW_CONFIDENCE")
        return d

    @staticmethod
    def _safe_fallback(context: dict) -> Decision:
        return Decision(
            action="NO_ACTION",
            confidence=0.1,
            reasoning=(
                "Insufficient confidence to act. Human review required. "
                f"Context keys: {list(context.keys())}"
            ),
            requires_human_approval=True,
            safety_flags=["SAFE_FALLBACK"],
            domain=str(context.get("domain", "general")),
        )

    # ------------------------------------------------------------------
    def evaluate_rules(self, domain: str, context: dict) -> list[Decision]:
        """Run all rules for a domain and return all decisions (useful for audit)."""
        rule_fns = self._rules.get(domain, [])
        return [fn(context) for fn in rule_fns]

    def ai_reason(self, query: str, context: dict | None = None) -> str:
        """Simple rule-augmented reasoning summary."""
        ctx = context or {}
        ctx["query"] = query
        ctx.setdefault("domain", "general")
        d = self.decide(ctx)
        return (
            f"Action: {d.action} | Confidence: {d.confidence:.0%} | "
            f"Reasoning: {d.reasoning} | Human approval: {d.requires_human_approval}"
        )

    def get_history(self, limit: int = 20) -> list[Decision]:
        return self._history[-limit:]
