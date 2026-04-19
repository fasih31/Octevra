"""
Safety Layer — validates actions before execution.
Built-in rules cover medical, irrigation, rate-limiting, and confidence thresholds.
Supports admin overrides with full audit trail.
"""

from __future__ import annotations

import logging
import sqlite3
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

DB_PATH = Path("data/safety.db")


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class SafetyResult:
    allowed: bool
    reason: str
    requires_approval: bool
    risk_level: RiskLevel
    rule_triggered: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class OverrideRecord:
    action_id: str
    admin_id: str
    reason: str
    timestamp: float


# ---------------------------------------------------------------------------
# Built-in safety rules
# ---------------------------------------------------------------------------

def _rule_medical_approval(action: str, context: dict) -> Optional[SafetyResult]:
    """Medical/hospital actions always require human approval."""
    domain = context.get("domain", "")
    if domain == "hospital" and action not in ("NORMAL", "RESPOND"):
        return SafetyResult(
            allowed=False,
            reason="Medical actions require explicit human approval before execution.",
            requires_approval=True,
            risk_level=RiskLevel.HIGH,
            rule_triggered="medical_approval",
        )
    return None


def _rule_irrigation_anomaly(action: str, context: dict) -> Optional[SafetyResult]:
    """Block irrigation if sensor readings are anomalous."""
    if action != "IRRIGATE":
        return None
    pressure = context.get("pressure", 3.0)
    flow_rate = context.get("flow_rate", 10.0)
    if pressure > 8.0 or flow_rate > 50.0:
        return SafetyResult(
            allowed=False,
            reason=f"Anomalous readings: pressure={pressure} bar, flow={flow_rate} L/min. "
                   "Irrigation blocked until sensors verify safe.",
            requires_approval=True,
            risk_level=RiskLevel.HIGH,
            rule_triggered="irrigation_anomaly",
        )
    return None


def _rule_confidence_threshold(action: str, context: dict) -> Optional[SafetyResult]:
    """Block actions with very low AI confidence."""
    confidence = context.get("confidence", 1.0)
    if confidence < 0.4:
        return SafetyResult(
            allowed=False,
            reason=f"AI confidence too low ({confidence:.0%}) to allow automated action.",
            requires_approval=True,
            risk_level=RiskLevel.MEDIUM,
            rule_triggered="confidence_threshold",
        )
    return None


def _rule_emergency_shutoff_allowed(action: str, context: dict) -> Optional[SafetyResult]:
    """Emergency shutoffs are always permitted."""
    if action in ("EMERGENCY_SHUTOFF", "EMERGENCY_SHUTDOWN"):
        return SafetyResult(
            allowed=True,
            reason="Emergency action — always permitted by safety layer.",
            requires_approval=False,
            risk_level=RiskLevel.CRITICAL,
            rule_triggered="emergency_always_allowed",
        )
    return None


DEFAULT_RULES: list[tuple[str, Callable]] = [
    ("emergency_always_allowed", _rule_emergency_shutoff_allowed),
    ("medical_approval", _rule_medical_approval),
    ("irrigation_anomaly", _rule_irrigation_anomaly),
    ("confidence_threshold", _rule_confidence_threshold),
]


# ---------------------------------------------------------------------------
# Rate limiter (in-memory, per user)
# ---------------------------------------------------------------------------

class _RateLimiter:
    def __init__(self, max_requests: int = 60, window: int = 60) -> None:
        self._max = max_requests
        self._window = window
        self._requests: dict[str, list[float]] = defaultdict(list)

    def check(self, user_id: str) -> bool:
        now = time.time()
        cutoff = now - self._window
        self._requests[user_id] = [t for t in self._requests[user_id] if t > cutoff]
        if len(self._requests[user_id]) >= self._max:
            return False
        self._requests[user_id].append(now)
        return True


# ---------------------------------------------------------------------------
# SafetyLayer
# ---------------------------------------------------------------------------

class SafetyLayer:
    """Validates actions through a pipeline of safety rules."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._setup()
        self._rules: list[tuple[str, Callable]] = list(DEFAULT_RULES)
        self._rate_limiter = _RateLimiter()

    def _setup(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS safety_overrides (
                    id          TEXT PRIMARY KEY,
                    action_id   TEXT NOT NULL,
                    admin_id    TEXT NOT NULL,
                    reason      TEXT NOT NULL,
                    timestamp   REAL NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS safety_log (
                    id          TEXT PRIMARY KEY,
                    action      TEXT NOT NULL,
                    allowed     INTEGER NOT NULL,
                    risk_level  TEXT NOT NULL,
                    reason      TEXT NOT NULL,
                    rule        TEXT NOT NULL,
                    user_id     TEXT,
                    timestamp   REAL NOT NULL
                )
                """
            )

    # ------------------------------------------------------------------
    def add_rule(self, name: str, rule_fn: Callable[[str, dict], Optional[SafetyResult]]) -> None:
        """Register a custom safety rule. Rules are checked in registration order."""
        self._rules.append((name, rule_fn))

    # ------------------------------------------------------------------
    def check(self, action: str, context: dict) -> SafetyResult:
        """
        Run all safety rules. First non-None result wins.
        If no rule triggers, defaults to ALLOWED / LOW risk.
        """
        user_id = context.get("user_id", "anonymous")

        # Rate limiting
        if not self._rate_limiter.check(user_id):
            result = SafetyResult(
                allowed=False,
                reason="Rate limit exceeded. Please wait before making more requests.",
                requires_approval=False,
                risk_level=RiskLevel.MEDIUM,
                rule_triggered="rate_limit",
            )
            self._log(action, result, user_id)
            return result

        # Run rules in order
        for name, rule_fn in self._rules:
            try:
                result = rule_fn(action, context)
                if result is not None:
                    self._log(action, result, user_id)
                    return result
            except Exception as exc:
                logger.error("Safety rule '%s' raised: %s", name, exc)

        # Default — allowed
        result = SafetyResult(
            allowed=True,
            reason="All safety rules passed.",
            requires_approval=False,
            risk_level=RiskLevel.LOW,
            rule_triggered="default",
        )
        self._log(action, result, user_id)
        return result

    # ------------------------------------------------------------------
    def override(self, action_id: str, admin_id: str, reason: str) -> OverrideRecord:
        """Admin override for a blocked action. Logged for audit."""
        record = OverrideRecord(
            action_id=action_id,
            admin_id=admin_id,
            reason=reason,
            timestamp=time.time(),
        )
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO safety_overrides (id, action_id, admin_id, reason, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), action_id, admin_id, reason, record.timestamp),
            )
        logger.warning("Safety override by admin %s for action %s: %s", admin_id, action_id, reason)
        return record

    def get_overrides(self, limit: int = 50) -> list[OverrideRecord]:
        cur = self._conn.execute(
            "SELECT action_id, admin_id, reason, timestamp FROM safety_overrides "
            "ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        return [OverrideRecord(*row) for row in cur.fetchall()]

    # ------------------------------------------------------------------
    def _log(self, action: str, result: SafetyResult, user_id: str) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO safety_log (id, action, allowed, risk_level, reason, rule, user_id, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()), action, int(result.allowed),
                    result.risk_level.value, result.reason,
                    result.rule_triggered, user_id, time.time(),
                ),
            )
