"""
/report endpoints — generate and retrieve AI-powered reports.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ai_os_nexus.core.llm_core import LLMFactory
from ai_os_nexus.core.tri_index_search import TriIndexSearch
from ai_os_nexus.dataset.dataset_manager import DatasetManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/report", tags=["report"])

_llm = LLMFactory.create("mock")
_search = TriIndexSearch()
_dataset = DatasetManager()

# In-memory report store (production: persist to DB)
_reports: dict[str, dict] = {}


class ReportRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=512)
    report_type: str = Field("general", pattern="^(general|brd|irrigation|hospital|industrial|technical)$")
    context: Optional[dict[str, Any]] = None
    user_id: Optional[str] = None


class ReportOut(BaseModel):
    report_id: str
    topic: str
    report_type: str
    content: str
    sections: list[dict]
    created_at: float
    latency_ms: float


def _format_report(topic: str, report_type: str, llm_response: str, context: dict) -> dict:
    """Structure the report into sections."""
    sections = [
        {"title": "Executive Summary", "content": f"Report on: {topic}"},
        {"title": "Analysis", "content": llm_response},
        {"title": "Context", "content": str(context) if context else "No additional context provided"},
        {"title": "Recommendations", "content": _generate_recommendations(report_type, topic)},
        {"title": "Generated At", "content": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())},
    ]
    return sections


def _generate_recommendations(report_type: str, topic: str) -> str:
    recs = {
        "irrigation": (
            "1. Implement soil moisture-based scheduling to reduce water waste by 30–50%.\n"
            "2. Install pressure regulation valves to maintain optimal 2–4 bar range.\n"
            "3. Integrate weather forecast data to avoid irrigation before expected rain.\n"
            "4. Schedule irrigation during off-peak hours (early morning) to minimise evaporation."
        ),
        "hospital": (
            "1. Establish escalation protocols for vitals outside normal ranges.\n"
            "2. Implement continuous monitoring with automatic alerts for critical values.\n"
            "3. Conduct regular calibration of monitoring equipment.\n"
            "4. Ensure backup power for all life-critical monitoring systems."
        ),
        "industrial": (
            "1. Implement predictive maintenance using vibration and temperature trends.\n"
            "2. Set up automated shutoff for pressure/temperature threshold breaches.\n"
            "3. Schedule regular lubrication and bearing replacement per OEM specs.\n"
            "4. Maintain detailed sensor log history for regulatory compliance."
        ),
        "general": (
            f"1. Review current practices related to {topic}.\n"
            "2. Collect baseline metrics to measure improvement.\n"
            "3. Implement monitoring and alerting for key performance indicators.\n"
            "4. Schedule regular reviews of this report and update recommendations."
        ),
    }
    return recs.get(report_type, recs["general"])


@router.post("/generate", response_model=ReportOut, status_code=201)
async def generate_report(body: ReportRequest):
    """Generate an AI-powered report on a topic."""
    t0 = time.time()
    report_id = str(uuid.uuid4())

    # Gather context from search
    results = _search.search(body.topic, top_k=5)
    dataset_results = _dataset.search(body.topic, top_k=3)

    context_text = "\n".join([r.text for r in results] + [dr.content for dr in dataset_results])

    prompt = (
        f"Generate a professional {body.report_type} report on: {body.topic}\n\n"
        f"Context from knowledge base:\n{context_text[:2000]}\n\n"
        "Provide a comprehensive analysis with key findings and actionable insights."
    )

    content = await _llm.generate(prompt, context_text[:1000])
    sections = _format_report(body.topic, body.report_type, content, body.context or {})

    latency = (time.time() - t0) * 1000
    report = {
        "report_id": report_id,
        "topic": body.topic,
        "report_type": body.report_type,
        "content": content,
        "sections": sections,
        "created_at": time.time(),
        "latency_ms": round(latency, 2),
    }
    _reports[report_id] = report

    # Log to dataset
    _dataset.add_entry(
        category="decision_log",
        content=f"Report '{body.report_type}' on '{body.topic}': {content[:500]}",
        source="report_generator",
        metadata={"report_id": report_id, "topic": body.topic},
    )

    return ReportOut(**report)


@router.get("/{report_id}", response_model=ReportOut)
async def get_report(report_id: str):
    """Retrieve a previously generated report by ID."""
    report = _reports.get(report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found")
    return ReportOut(**report)


@router.get("/")
async def list_reports():
    """List all generated reports."""
    return {
        "count": len(_reports),
        "reports": [
            {"report_id": rid, "topic": r["topic"], "type": r["report_type"], "created_at": r["created_at"]}
            for rid, r in _reports.items()
        ],
    }
