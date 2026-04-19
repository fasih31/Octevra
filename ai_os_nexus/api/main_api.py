"""
Main FastAPI application for Orkavia AI-OS Nexus.
Serves the REST API and static frontend.
Start with: uvicorn ai_os_nexus.api.main_api:app --reload

© 2026 Fasih ur Rehman. All Rights Reserved.
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ai_os_nexus.api.endpoints import ask, memory, sensor, report, admin, decide
from ai_os_nexus.dataset.dataset_manager import DatasetManager
from ai_os_nexus.dataset.seed_data import seed_dataset
from ai_os_nexus.core.tri_index_search import TriIndexSearch

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CORS configuration — read allowed origins from environment.
# Default is localhost for development; override via CORS_ORIGINS env var
# (comma-separated list of origins, e.g. "https://app.example.com").
# ---------------------------------------------------------------------------
_raw_origins = os.environ.get("CORS_ORIGINS", "*")
ALLOWED_ORIGINS: list[str] = [o.strip() for o in _raw_origins.split(",") if o.strip()]

# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AI-OS Nexus starting up...")
    Path("data").mkdir(exist_ok=True)

    try:
        ds = DatasetManager()
        seeded = seed_dataset(ds)
        if seeded:
            logger.info("Seeded %d entries into knowledge base", seeded)

        search = TriIndexSearch()
        entries = ds.export_dataset(category="knowledge")
        for entry in entries[:200]:
            search.index_document(
                doc_id=entry["id"],
                text=entry["content"],
                metadata=entry.get("metadata", {}),
            )
        logger.info("Indexed %d knowledge entries into tri-index search", len(entries[:200]))
    except Exception as exc:
        logger.error("Startup error: %s", exc)

    logger.info("AI-OS Nexus is ready! API: http://localhost:8000/docs")
    yield
    logger.info("AI-OS Nexus shutting down...")


# ---------------------------------------------------------------------------
# App definition
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Orkavia AI-OS Nexus",
    description=(
        "Orkavia AI-OS Nexus — a dual-mode AI operating system: public knowledge "
        "assistant + private AI OS with IoT integration, consent-based memory, and "
        "hybrid search. © 2026 Fasih ur Rehman. All Rights Reserved."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Request-ID"],
)

# ---------------------------------------------------------------------------
# Security headers middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add security-hardening HTTP headers to every response."""
    response: Response = await call_next(request)
    # Prevent MIME-type sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Basic XSS protection header (legacy browsers)
    response.headers["X-XSS-Protection"] = "1; mode=block"
    # Strict referrer policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Content Security Policy — allow framing for Replit preview
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src *; "
        "frame-ancestors *;"
    )
    # Permissions policy — disable unnecessary browser features
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(), payment=()"
    )
    return response


# ---------------------------------------------------------------------------
# Request ID + latency middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    t0 = time.time()
    response: Response = await call_next(request)
    latency = (time.time() - t0) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Latency-Ms"] = str(round(latency, 2))
    return response

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(ask.router)
app.include_router(memory.router)
app.include_router(sensor.router)
app.include_router(report.router)
app.include_router(admin.router)
app.include_router(decide.router)

# ---------------------------------------------------------------------------
# Static frontend
# ---------------------------------------------------------------------------

FRONTEND_DIR = Path(__file__).parent.parent.parent / "ai_os_nexus" / "frontend"
if not FRONTEND_DIR.exists():
    FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
    logger.info("Serving frontend from %s", FRONTEND_DIR)


@app.get("/", include_in_schema=False)
async def serve_frontend():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return JSONResponse({"message": "AI-OS Nexus API is running. Visit /docs for API documentation."})

