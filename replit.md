# Orkavia AI-OS Nexus

A privacy-focused, dual-mode AI Operating System that functions as both a public knowledge assistant and a private AI system with IoT integration.

## Project Overview

- **Public Mode**: ChatGPT-like assistant with no memory retention
- **Private Mode**: Full AI OS with encrypted per-user memory, IoT sensors, and automation
- **Key Features**: Tri-Index Search (semantic + keyword + memory), IoT sensor integration, AES-256 encrypted memory, consent-based data handling

## Tech Stack

- **Backend**: Python 3.12 + FastAPI
- **Frontend**: Single-page application (HTML/CSS/vanilla JS)
- **Database**: SQLite (local storage)
- **Encryption**: cryptography (Fernet AES-256), PBKDF2-HMAC-SHA256
- **Server**: Uvicorn (dev) / Gunicorn (prod)

## Project Layout

```
ai_os_nexus/
  api/           - FastAPI routes and main app entry (main_api.py)
  core/          - LLM, search, memory, consent, safety logic
  dataset/       - Data management and seeding
  frontend/      - Web UI (index.html, css/, js/)
  iot/           - IoT sensor simulation and rule engines
  knowledge_base/ - Knowledge storage
data/            - Runtime SQLite DBs and audit logs (auto-created)
runtime/         - YAML configuration files
tests/           - pytest test suite
```

## Running the App

The app runs via the "Start application" workflow:
```
uvicorn ai_os_nexus.api.main_api:app --host 0.0.0.0 --port 5000 --reload
```

## Key Configuration

- Port: **5000** (webview)
- CORS: Allows all origins (configurable via `CORS_ORIGINS` env var)
- Security headers modified to allow iframe embedding in Replit preview
- API docs available at `/docs`

## Dependencies

Managed via `requirements.txt` with pip. Key packages:
- fastapi, uvicorn, pydantic v2, cryptography, numpy, httpx, pyyaml
