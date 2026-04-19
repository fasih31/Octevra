# Orkavia AI-OS Nexus

A privacy-focused, dual-mode AI Operating System that functions as both a public knowledge assistant and a private AI system with IoT integration, decision automation, and full audit compliance.

**Author**: Fasih ur Rehman · © 2026 All Rights Reserved.

## Project Overview

- **Public Mode**: Stateless AI chat with tri-index knowledge search
- **Private Mode**: Full AI OS with AES-256 encrypted per-user memory, consent engine, IoT automation, and GDPR audit log
- **Decision Engine**: AI + rule-based hybrid decisions for irrigation, hospital, and industrial domains
- **Safety Layer**: Rate limiting, risk scoring, human-approval gating, override logging

## Tech Stack

- **Backend**: Python 3.12 + FastAPI
- **Frontend**: Single-page application (HTML/CSS/vanilla JS) — no build step
- **Database**: SQLite (automatic, local)
- **Encryption**: cryptography (Fernet AES-256), PBKDF2-HMAC-SHA256
- **Server**: Uvicorn with `--reload`

## Project Layout

```
ai_os_nexus/
  api/
    main_api.py        - FastAPI entry, middleware, static serving, router registration
    endpoints/
      ask.py           - /ask — chat with tri-index search + memory
      decide.py        - /decide, /sensor/simulate, /sensor/live-stream, /decide/history
      memory.py        - /memory — CRUD for encrypted user memories
      sensor.py        - /sensor — ingest, latest, history, latest-all, triggers
      report.py        - /report — AI-generated domain reports
      admin.py         - /admin — health, stats, audit, compliance, safety override
  core/
    decision_engine.py - Hybrid AI+rule engine (irrigation/hospital/industrial/general)
    safety_layer.py    - Rate limiter, risk scoring, human-approval, override log
    tri_index_search.py- Semantic + keyword + memory tri-index search
    memory_manager.py  - AES-256 encrypted per-user memory with consent tagging
    audit_log.py       - Append-only compliance audit log
    consent_engine.py  - GDPR-aligned consent management
  dataset/             - DatasetManager + seed data (58 knowledge entries)
  frontend/
    index.html         - SPA entry point with 7 sections
    css/styles.css     - Full design system (dark theme, tokens, responsive)
    js/app.js          - Router, chat, decision, sensors, memory, reports, admin, audit
  iot/
    fake_sensors.py    - Realistic sensor simulation (irrigation/hospital/industrial)
    sensor_api.py      - SensorManager: ingest, latest, history, trigger rules
  knowledge_base/      - Knowledge storage
data/                  - SQLite DBs and audit logs (auto-created at runtime)
runtime/               - YAML configuration
tests/                 - pytest suite
```

## Running the App

Via the "Start application" workflow:
```
uvicorn ai_os_nexus.api.main_api:app --host 0.0.0.0 --port 5000 --reload
```

## API Reference (Key Endpoints)

| Method | Path | Purpose |
|--------|------|---------|
| POST | /ask | Chat query with mode/memory/consent |
| POST | /decide | Run Decision Engine for a domain |
| POST | /sensor/simulate | Generate fake sensor data + decisions |
| GET  | /sensor/live-stream | SSE stream of real-time sensor + decisions |
| GET  | /decide/history | Recent decisions from in-memory history |
| GET  | /sensor/latest-all | Latest reading for all known sensors |
| GET  | /sensor/{id}/latest | Latest reading for specific sensor |
| POST | /sensor/ingest | Ingest raw sensor reading |
| GET  | /memory/{user_id} | List user's encrypted memories |
| DELETE | /memory/{user_id} | Delete all user memories |
| POST | /report/generate | Generate AI domain report |
| GET  | /admin/health | System health check |
| GET  | /admin/stats | Usage statistics |
| GET  | /admin/audit | Audit log with optional event filter |
| GET  | /admin/audit/compliance | Compliance summary stats |
| POST | /admin/safety/override | Admin override for blocked action |
| DELETE | /admin/memory/expired | Purge expired memory entries |

## Frontend Sections

1. **Chat** — Dual-mode AI chat (public/private), memory consent, quick-start chips
2. **Decision Engine** — JSON context editor, domain selector, result card with confidence bar, live simulation, SSE streaming, decision history
3. **Sensors** — Demo injection, auto-refresh grid, status badges (normal/warning/critical), decision strips
4. **Memory Vault** — Per-user encrypted memory list, stats, export (JSON), delete
5. **Reports** — AI-generated domain reports with section rendering and history
6. **Admin** — Health check, stats, dataset info, safety override, maintenance
7. **Audit** — Filtered audit log, compliance summary dashboard

## Key Configuration

- Port: **5000**
- CORS: All origins (override via `CORS_ORIGINS` env var)
- CSP / X-Frame-Options relaxed for Replit preview iframe
- API docs: `/docs`

## Dependencies

Managed via `requirements.txt`:
- fastapi, uvicorn, pydantic v2, cryptography, numpy, httpx, pyyaml, python-multipart
