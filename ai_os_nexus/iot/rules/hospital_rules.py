"""
Hospital Rules — vital signs monitoring and alert generation.
Used by the IoT decision pipeline for patient safety.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Alert:
    patient_id: str
    alert_type: str           # "NORMAL", "WARNING", "CRITICAL"
    message: str
    vitals: dict
    flags: list[str] = field(default_factory=list)
    recommended_action: str = ""


def check_vitals(
    heart_rate: float,
    bp_systolic: float,
    bp_diastolic: float,
    oxygen: float,
    temperature: float = 36.8,
    respiratory_rate: float = 16.0,
    patient_id: str = "unknown",
) -> Alert:
    """
    Evaluate patient vitals and return an Alert.
    
    Normal ranges (adult):
    - Heart rate: 60–100 bpm
    - BP: 90/60 – 120/80 mmHg
    - SpO₂: ≥ 95%
    - Temperature: 36.1–37.2°C
    - Respiratory rate: 12–20 breaths/min
    """
    critical_flags: list[str] = []
    warning_flags: list[str] = []
    vitals = {
        "heart_rate": heart_rate,
        "bp_systolic": bp_systolic,
        "bp_diastolic": bp_diastolic,
        "oxygen": oxygen,
        "temperature": temperature,
        "respiratory_rate": respiratory_rate,
    }

    # SpO₂
    if oxygen < 90:
        critical_flags.append(f"CRITICAL_HYPOXIA: SpO₂={oxygen}%")
    elif oxygen < 94:
        warning_flags.append(f"LOW_OXYGEN: SpO₂={oxygen}%")

    # Heart rate
    if heart_rate < 40 or heart_rate > 150:
        critical_flags.append(f"CRITICAL_HEART_RATE: {heart_rate} bpm")
    elif heart_rate < 50 or heart_rate > 120:
        warning_flags.append(f"ABNORMAL_HEART_RATE: {heart_rate} bpm")

    # Blood pressure — hypertensive crisis
    if bp_systolic >= 180 or bp_diastolic >= 120:
        critical_flags.append(f"HYPERTENSIVE_CRISIS: {bp_systolic}/{bp_diastolic} mmHg")
    elif bp_systolic < 90 or bp_diastolic < 60:
        critical_flags.append(f"HYPOTENSION: {bp_systolic}/{bp_diastolic} mmHg")
    elif bp_systolic >= 140 or bp_diastolic >= 90:
        warning_flags.append(f"STAGE2_HYPERTENSION: {bp_systolic}/{bp_diastolic} mmHg")

    # Temperature
    if temperature < 35.0:
        critical_flags.append(f"HYPOTHERMIA: {temperature}°C")
    elif temperature >= 40.0:
        critical_flags.append(f"HYPERPYREXIA: {temperature}°C")
    elif temperature >= 38.5:
        warning_flags.append(f"HIGH_FEVER: {temperature}°C")

    # Respiratory rate
    if respiratory_rate < 8 or respiratory_rate > 30:
        critical_flags.append(f"CRITICAL_RESP_RATE: {respiratory_rate}/min")
    elif respiratory_rate < 12 or respiratory_rate > 25:
        warning_flags.append(f"ABNORMAL_RESP_RATE: {respiratory_rate}/min")

    # Determine alert level
    if critical_flags:
        return Alert(
            patient_id=patient_id,
            alert_type="CRITICAL",
            message="Critical vital signs detected: " + "; ".join(critical_flags),
            vitals=vitals,
            flags=critical_flags + warning_flags,
            recommended_action="IMMEDIATE_CLINICAL_INTERVENTION",
        )

    if warning_flags:
        return Alert(
            patient_id=patient_id,
            alert_type="WARNING",
            message="Abnormal vital signs: " + "; ".join(warning_flags),
            vitals=vitals,
            flags=warning_flags,
            recommended_action="NOTIFY_NURSE_REVIEW_VITALS",
        )

    return Alert(
        patient_id=patient_id,
        alert_type="NORMAL",
        message="All vitals within normal ranges.",
        vitals=vitals,
        flags=[],
        recommended_action="CONTINUE_ROUTINE_MONITORING",
    )


def escalation_level(alert: Alert) -> str:
    """
    Return a human-readable escalation level string.
    
    Returns:
        "normal" | "warning" | "critical"
    """
    mapping = {
        "NORMAL": "normal",
        "WARNING": "warning",
        "CRITICAL": "critical",
    }
    return mapping.get(alert.alert_type, "normal")
