"""
Irrigation Rules — decision logic for automated irrigation systems.
Integrates with DecisionEngine and SafetyLayer.
"""

from __future__ import annotations

from ai_os_nexus.core.decision_engine import Decision


def should_irrigate(
    soil_moisture: float,
    temperature: float,
    rain_probability: float,
    pressure: float = 3.5,
    flow_rate: float = 15.0,
) -> Decision:
    """
    Determine whether to irrigate based on sensor readings.
    
    Args:
        soil_moisture: Percentage (0–100)
        temperature: Celsius
        rain_probability: 0.0–1.0
        pressure: Bar
        flow_rate: L/min
    
    Returns:
        Decision with action, confidence, and reasoning.
    """
    flags: list[str] = []

    # Safety first
    if pressure > 8.0:
        return Decision(
            action="EMERGENCY_SHUTOFF",
            confidence=0.99,
            reasoning=f"Pressure {pressure:.1f} bar exceeds 8 bar safety limit. Emergency shutoff required.",
            requires_human_approval=False,
            safety_flags=["HIGH_PRESSURE"],
            domain="irrigation",
        )

    if flow_rate > 50.0:
        flags.append("HIGH_FLOW")
        return Decision(
            action="SHUTOFF",
            confidence=0.95,
            reasoning=f"Flow rate {flow_rate:.1f} L/min is abnormally high. Possible leak. Shutoff recommended.",
            requires_human_approval=True,
            safety_flags=flags,
            domain="irrigation",
        )

    # Decision logic
    evapotranspiration_factor = 1.0 + max(0, (temperature - 25) * 0.02)
    effective_threshold = 35 * evapotranspiration_factor

    if soil_moisture < effective_threshold and rain_probability < 0.5:
        confidence = 0.85 + min(0.1, (effective_threshold - soil_moisture) / 100)
        confidence -= rain_probability * 0.2
        return Decision(
            action="IRRIGATE",
            confidence=round(confidence, 3),
            reasoning=(
                f"Soil moisture {soil_moisture:.1f}% below threshold "
                f"({effective_threshold:.1f}% adjusted for {temperature:.1f}°C). "
                f"Rain probability {rain_probability*100:.0f}%. Irrigation recommended."
            ),
            requires_human_approval=confidence < 0.7,
            safety_flags=flags,
            domain="irrigation",
        )

    if rain_probability >= 0.7:
        return Decision(
            action="DEFER",
            confidence=0.9,
            reasoning=f"Rain probability {rain_probability*100:.0f}% — deferring irrigation.",
            requires_human_approval=False,
            safety_flags=flags,
            domain="irrigation",
        )

    if soil_moisture >= 70:
        return Decision(
            action="NO_IRRIGATE",
            confidence=0.95,
            reasoning=f"Soil moisture {soil_moisture:.1f}% is adequate. No irrigation needed.",
            requires_human_approval=False,
            safety_flags=flags,
            domain="irrigation",
        )

    return Decision(
        action="MONITOR",
        confidence=0.6,
        reasoning=(
            f"Borderline conditions: moisture={soil_moisture:.1f}%, "
            f"temp={temperature:.1f}°C, rain={rain_probability*100:.0f}%. "
            "Continue monitoring."
        ),
        requires_human_approval=True,
        safety_flags=flags,
        domain="irrigation",
    )


def emergency_shutoff(pressure: float, flow_rate: float) -> bool:
    """
    Determine if an emergency shutoff is required.
    
    Returns True if shutoff should be triggered immediately.
    """
    if pressure > 8.0:
        return True
    if flow_rate > 50.0:
        return True
    # Combined anomaly
    if pressure > 6.0 and flow_rate > 35.0:
        return True
    return False
