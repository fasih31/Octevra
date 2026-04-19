# 🧠 Orkavia AI-OS Nexus

> **© 2026 Fasih ur Rehman. All Rights Reserved.**

A dual-mode AI Operating System — public knowledge assistant + private AI OS with IoT integration, consent-based encrypted memory, and hybrid search.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)

---

## Overview

Orkavia AI-OS Nexus is a self-contained, privacy-first AI platform operating in two modes:

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
- **Audit Log**: Append-only, privacy-respecting audit trail for all critical actions
- **IoT**: JSON ingestion, triggers, fake sensor generator
- **Dataset**: Self-growing local dataset (50+ seed entries, logs all interactions)
- **Frontend**: Accessible dark-theme SPA dashboard (chat, memory, sensors, reports, admin, audit)

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
| GET | `/admin/audit` | Audit log (recent events) |
| GET | `/admin/audit/compliance` | Compliance stats summary |

Full docs: `http://localhost:8000/docs`

## Configuration

All secrets and tuneable settings are read from environment variables. No hardcoded secrets exist.

| Variable | Default | Description |
|----------|---------|-------------|
| `CORS_ORIGINS` | `http://localhost:8000,http://127.0.0.1:8000` | Comma-separated allowed CORS origins |

## Testing

```bash
pytest tests/ -v
```

## Docker

```bash
docker-compose up --build
```

## Privacy & Data Retention

- Memory encrypted with AES-256 (Fernet) per user
- PBKDF2-HMAC-SHA256 key derivation (100k iterations)
- GDPR: right to erasure (`DELETE /memory/{user_id}`) + data portability (`GET /memory/{user_id}/export`)
- 100% local — no data leaves your server
- Audit logs stored in `data/audit.db` — retained indefinitely by default; configure backups/deletion per your retention policy

## Security & Compliance

### Security hardening (v2.0)
- **Security HTTP headers** on every response: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection: 1; mode=block`, `Referrer-Policy: strict-origin-when-cross-origin`, `Content-Security-Policy` (same-origin, no external resources), `Permissions-Policy` (camera/mic/geo disabled)
- **Tightened CORS**: wildcard `*` removed; explicit origin allow-list via `CORS_ORIGINS` env var; credentials disabled
- **Input validation**: all API models use Pydantic v2 with min/max length constraints; query strings validated before processing
- **Output encoding**: all dynamic content in the SPA is rendered with `escapeHtml()` — no `innerHTML` with user-controlled raw strings
- **Rate limiting**: per-user in-memory rate limiter in the safety layer (60 req/min default)
- **No hardcoded secrets**: encryption keys derived at runtime from user IDs via PBKDF2; no API keys in source
- **Cache key security**: SHA-256 cache keys (no MD5)

### Audit & compliance
- **Append-only audit log** (`data/audit.db`) for: memory store/delete/export, safety overrides, admin purge, dataset export
- **Sensitive field masking**: fields like `content`, `token`, `key` are masked before writing to audit log
- **Compliance endpoint** (`GET /admin/audit/compliance`): returns aggregate event counts + retention policy — no payloads exposed
- **Audit viewer** in UI: Audit section with event filter, compliance summary cards

### Security test coverage
- XSS regression: all frontend dynamic rendering uses `escapeHtml()`
- Invalid input tests: empty query, invalid mode, missing fields → 422 validation errors
- Admin endpoint tests: health, stats, audit, compliance, safety override, purge
- Memory security: per-user isolation, NONE mode stores nothing

---

*Orkavia AI-OS Nexus is proprietary software. See `LICENSE` for terms.*
*© 2026 Fasih ur Rehman. All Rights Reserved.*
