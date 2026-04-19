"""
LLM Core Layer — Abstract interface, MockLLM, OpenAI-compatible stub, factory.
Supports swappable model backends with a unified async interface.
"""

from __future__ import annotations

import asyncio
import logging
import re
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class BaseLLM(ABC):
    """Abstract base for all LLM backends."""

    @abstractmethod
    async def generate(self, prompt: str, context: str = "") -> str:
        """Generate a response given a prompt and optional context."""
        ...

    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier string."""
        ...


# ---------------------------------------------------------------------------
# MockLLM — template-based responses, no external dependencies
# ---------------------------------------------------------------------------

class MockLLM(BaseLLM):
    """
    Keyword-driven template responder.
    Covers: greetings, irrigation, hospital/medical, code/programming,
    science, industrial, dataset, memory, general fallback.
    """

    def model_name(self) -> str:
        return "mock-llm-v1"

    async def generate(self, prompt: str, context: str = "") -> str:
        await asyncio.sleep(0)          # yield to event loop
        combined = (prompt + " " + context).lower()
        return self._route(combined, prompt)

    # ------------------------------------------------------------------
    def _route(self, text: str, original: str) -> str:
        if self._match(text, ["hello", "hi ", "hey", "greet", "good morning", "good evening"]):
            return self._greeting()
        if self._match(text, ["irrigat", "soil moisture", "water crop", "rain", "drip", "sprinkl"]):
            return self._irrigation(text)
        if self._match(text, ["heart rate", "blood pressure", "oxygen", "spo2", "vitals", "patient",
                              "hospital", "bp", "pulse", "triage", "icu", "ecg"]):
            return self._hospital(text)
        if self._match(text, ["code", "python", "function", "class", "algorithm", "debug",
                              "javascript", "typescript", "sql", "api", "rest"]):
            return self._code(text)
        if self._match(text, ["science", "physics", "chemistry", "biology", "quantum",
                              "atom", "molecule", "gravity", "energy", "force"]):
            return self._science(text)
        if self._match(text, ["industrial", "factory", "machine", "sensor", "pressure",
                              "temperature", "flow rate", "valve", "pump", "plc"]):
            return self._industrial(text)
        if self._match(text, ["memory", "remember", "forget", "stored", "private", "consent"]):
            return self._memory(text)
        if self._match(text, ["dataset", "data", "train", "model", "ml", "ai", "neural"]):
            return self._dataset(text)
        return self._general(original)

    @staticmethod
    def _match(text: str, keywords: list[str]) -> bool:
        return any(kw in text for kw in keywords)

    # ------------------------------------------------------------------
    @staticmethod
    def _greeting() -> str:
        return (
            "Hello! I'm AI-OS Nexus — your intelligent operating system assistant. "
            "I can help you with general knowledge, IoT/sensor data analysis, "
            "irrigation control, hospital monitoring, and much more. "
            "How can I assist you today?"
        )

    @staticmethod
    def _irrigation(text: str) -> str:
        if "emergency" in text or "shutoff" in text:
            return (
                "🚨 Emergency irrigation protocol activated. "
                "Triggering immediate shutoff. Check pressure sensors and flow meters. "
                "Inspect for pipe leaks or blockages before restarting the system."
            )
        return (
            "🌱 Irrigation Analysis:\n"
            "• Optimal soil moisture: 40–60% for most crops.\n"
            "• Irrigate when moisture drops below 35%.\n"
            "• Avoid irrigation if rain probability > 70% in the next 6 hours.\n"
            "• Temperature above 35°C increases evapotranspiration — increase watering frequency.\n"
            "• Drip irrigation reduces water waste by up to 50% vs. flood irrigation.\n"
            "Current sensor data will be cross-checked with these thresholds automatically."
        )

    @staticmethod
    def _hospital(text: str) -> str:
        if "critical" in text or "emergency" in text or "alert" in text:
            return (
                "🔴 CRITICAL ALERT: Immediate clinical intervention required.\n"
                "Notify attending physician and nursing staff NOW.\n"
                "Standard emergency protocol: ABCDE assessment — Airway, Breathing, "
                "Circulation, Disability, Exposure. Log all vitals every 5 minutes."
            )
        return (
            "🏥 Medical Vitals Reference:\n"
            "• Heart Rate: 60–100 bpm (normal adult)\n"
            "• Blood Pressure: 90/60 – 120/80 mmHg (normal)\n"
            "• SpO₂: ≥ 95% (normal), < 90% = critical\n"
            "• Temperature: 36.1–37.2°C (normal)\n"
            "• Respiratory Rate: 12–20 breaths/min (adult)\n"
            "All readings are being monitored in real-time. Alerts trigger automatically "
            "when values deviate from safe ranges."
        )

    @staticmethod
    def _code(text: str) -> str:
        return (
            "💻 I can assist with software development tasks:\n"
            "• Code review and debugging\n"
            "• Algorithm design and complexity analysis\n"
            "• API design (REST, GraphQL, WebSocket)\n"
            "• Database schema and query optimisation\n"
            "• Python, JavaScript, TypeScript, SQL, and more\n\n"
            "Please share your specific code question or paste the snippet you need help with."
        )

    @staticmethod
    def _science(text: str) -> str:
        return (
            "🔬 Science Knowledge Base:\n"
            "This system has access to structured scientific knowledge covering "
            "physics, chemistry, biology, and environmental science.\n\n"
            "• Physics: mechanics, thermodynamics, electromagnetism, quantum theory\n"
            "• Chemistry: periodic table, reactions, stoichiometry, organic chemistry\n"
            "• Biology: cell biology, genetics, ecology, human physiology\n\n"
            "Ask a specific question for a detailed answer."
        )

    @staticmethod
    def _industrial(text: str) -> str:
        return (
            "🏭 Industrial Monitoring:\n"
            "• Normal operating temperature range: 15–80°C (varies by machine)\n"
            "• Pressure thresholds are equipment-specific — check manufacturer specs\n"
            "• Flow rate anomalies > 20% from baseline trigger automatic alerts\n"
            "• Vibration readings outside ±2σ indicate bearing or alignment issues\n"
            "• PLC status codes and I/O states are logged every 30 seconds\n"
            "Sensor data is being collected and anomalies will trigger safety rules."
        )

    @staticmethod
    def _memory(text: str) -> str:
        return (
            "🔒 Memory System:\n"
            "Your data is managed with full privacy controls:\n"
            "• NONE — nothing stored, completely stateless\n"
            "• PRIVATE — encrypted, only you can access it\n"
            "• ANON_LEARN — anonymised and used to improve responses\n"
            "• PUBLIC — contributed to the shared knowledge base\n\n"
            "All private memory is AES-256 encrypted with a key derived from your user ID. "
            "You can view, export, or delete your data at any time."
        )

    @staticmethod
    def _dataset(text: str) -> str:
        return (
            "📦 Dataset Engine:\n"
            "AI-OS Nexus stores all knowledge in a self-contained local dataset:\n"
            "• Every conversation is logged and used for improvement\n"
            "• Sensor readings are time-series indexed\n"
            "• Decisions and reasoning are stored for audit trails\n"
            "• Zero external dataset dependencies — 100% locally managed\n\n"
            "The system continuously learns from interactions while respecting privacy boundaries."
        )

    @staticmethod
    def _general(prompt: str) -> str:
        trimmed = prompt[:120] + ("..." if len(prompt) > 120 else "")
        return (
            f"I've received your query: \"{trimmed}\"\n\n"
            "AI-OS Nexus is processing this using the Tri-Index hybrid search engine "
            "(semantic + keyword + temporal memory). "
            "Based on the available knowledge base, here is the most relevant response:\n\n"
            "The system is designed to provide accurate, context-aware answers. "
            "For best results, try to be specific about your domain "
            "(e.g., irrigation, medical, industrial, programming) "
            "or ask follow-up questions to refine the response."
        )


# ---------------------------------------------------------------------------
# OpenAI-Compatible LLM Stub
# ---------------------------------------------------------------------------

class OpenAICompatibleLLM(BaseLLM):
    """
    Stub for any OpenAI-compatible REST API (OpenAI, Ollama, LM Studio, etc.).
    Set OPENAI_API_KEY and OPENAI_BASE_URL in environment.
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-3.5-turbo",
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    def model_name(self) -> str:
        return self._model

    async def generate(self, prompt: str, context: str = "") -> str:
        try:
            import httpx
        except ImportError:
            logger.error("httpx not installed — cannot use OpenAICompatibleLLM")
            raise RuntimeError("httpx required for OpenAICompatibleLLM")

        messages = []
        if context:
            messages.append({"role": "system", "content": context})
        messages.append({"role": "user", "content": prompt})

        payload = {"model": self._model, "messages": messages}
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------
# LLM Factory
# ---------------------------------------------------------------------------

class LLMFactory:
    """Creates LLM instances by model name."""

    _registry: dict[str, type[BaseLLM]] = {
        "mock": MockLLM,
        "mock-llm": MockLLM,
        "openai": OpenAICompatibleLLM,
        "gpt-3.5-turbo": OpenAICompatibleLLM,
        "gpt-4": OpenAICompatibleLLM,
    }

    @classmethod
    def register(cls, name: str, klass: type[BaseLLM]) -> None:
        """Register a custom LLM backend."""
        cls._registry[name.lower()] = klass

    @classmethod
    def create(cls, model_name: str = "mock", **kwargs) -> BaseLLM:
        """Instantiate an LLM by name."""
        key = model_name.lower()
        klass = cls._registry.get(key)
        if klass is None:
            logger.warning("Unknown model '%s', falling back to MockLLM", model_name)
            klass = MockLLM
        if klass is MockLLM:
            return MockLLM()
        return klass(**kwargs)
