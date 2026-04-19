# 🧠 AI-OS Nexus

> A dual-mode AI Operating System — public knowledge assistant + private AI OS with IoT integration, consent-based memory, and hybrid search.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)

---

## Overview

AI-OS Nexus is a self-contained, privacy-first AI platform operating in two modes:

| Mode | Description |
|------|-------------|
| **🌐 Public** | ChatGPT-like assistant. No memory by default. Knowledge base only. |
| **🔒 Private** | Full AI OS. Encrypted per-user memory, IoT sensors, automation. |

All data stored locally in SQLite. Zero external dataset dependencies.

## Quick Start

```bash
pip install -r requirements.txt
uvicorn ai_os_nexus.api.main_api:app --reload
# Open http://localhost:8000
```

## Architecture

- **LLM Core**: Abstract interface + MockLLM (keyword-driven, no API key needed)
- **Tri-Index Search**: Semantic (TF-IDF) 50% + Keyword (FTS5) 30% + Memory 20%
- **Memory**: Fernet AES-256 encrypted, per-user, consent-gated, TTL expiry
- **Consent Engine**: Granular per-operation consent with expiry
- **Decision Engine**: Multi-domain rules (irrigation/hospital/industrial/general)
- **Safety Layer**: Medical approval gates, rate limiting, admin overrides
- **IoT**: JSON ingestion, triggers, fake sensor generator
- **Dataset**: Self-growing local dataset (50+ seed entries, logs all interactions)
- **Frontend**: Dark-theme SPA dashboard (chat, memory, sensors, reports, admin)

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/ask` | AI query (public or private mode) |
| GET/POST/DELETE | `/memory/{user_id}` | Memory management |
| POST | `/sensor/ingest` | Ingest sensor data |
| GET | `/sensor/{id}/latest` | Latest sensor reading |
| POST | `/report/generate` | Generate AI report |
| GET | `/admin/health` | System health |
| GET | `/admin/stats` | System statistics |

Full docs: `http://localhost:8000/docs`

## Testing

```bash
pytest tests/ -v
```

## Docker

```bash
docker-compose up --build
```

## Privacy

- Memory encrypted with AES-256 (Fernet) per user
- PBKDF2-HMAC-SHA256 key derivation (100k iterations)
- GDPR: right to erasure + data portability
- 100% local — no data leaves your server
