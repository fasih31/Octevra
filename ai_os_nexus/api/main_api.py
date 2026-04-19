"""
Main FastAPI application for AI-OS Nexus.
Serves the REST API and static frontend.
Start with: uvicorn ai_os_nexus.api.main_api:app --reload
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ai_os_nexus.api.endpoints import ask, memory, sensor, report, admin
from ai_os_nexus.dataset.dataset_manager import DatasetManager
from ai_os_nexus.dataset.seed_data import seed_dataset
from ai_os_nexus.core.tri_index_search import TriIndexSearch

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

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
    title="AI-OS Nexus",
    description=(
        "A dual-mode AI operating system — public knowledge assistant + "
        "private AI OS with IoT integration, consent-based memory, and hybrid search."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Request ID middleware
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

