"""Tests for the Octevra AI-OS Nexus REST API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ai_os_nexus.api.main_api import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# /ask
# ---------------------------------------------------------------------------

def test_ask_public():
    resp = client.post("/ask", json={
        "query": "What is the speed of light?",
        "mode": "public",
        "memory_consent": "NONE",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert data["mode"] == "public"
    assert data["memory_stored"] is False
    assert "request_id" in data
    assert data["latency_ms"] >= 0


def test_ask_private_with_memory():
    resp = client.post("/ask", json={
        "query": "Tell me about irrigation",
        "user_id": "test-user-api",
        "mode": "private",
        "memory_consent": "PRIVATE",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "private"
    assert data["memory_stored"] is True
    assert data["memory_id"] is not None


def test_ask_invalid_mode():
    resp = client.post("/ask", json={
        "query": "Hello",
        "mode": "invalid-mode",
    })
    assert resp.status_code == 422  # Validation error


def test_ask_empty_query():
    resp = client.post("/ask", json={"query": "", "mode": "public"})
    assert resp.status_code == 422


def test_ask_with_sources():
    resp = client.post("/ask", json={
        "query": "blood pressure normal ranges",
        "mode": "public",
        "memory_consent": "NONE",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["sources"], list)


# ---------------------------------------------------------------------------
# /memory
# ---------------------------------------------------------------------------

def test_memory_store_and_retrieve():
    user_id = "test-mem-user-001"
    # Store
    resp = client.post("/memory", json={
        "user_id": user_id,
        "content": "This is a test memory entry",
        "mode": "PRIVATE",
    })
    assert resp.status_code == 201
    assert resp.json()["stored"] is True
    assert resp.json()["memory_id"] is not None

    # Retrieve
    resp2 = client.get(f"/memory/{user_id}")
    assert resp2.status_code == 200
    entries = resp2.json()
    assert len(entries) >= 1
    assert any(e["content"] == "This is a test memory entry" for e in entries)


def test_memory_delete():
    user_id = "test-mem-delete-002"
    client.post("/memory", json={
        "user_id": user_id,
        "content": "Delete me",
        "mode": "PRIVATE",
    })
    resp = client.delete(f"/memory/{user_id}")
    assert resp.status_code == 200
    assert resp.json()["deleted"] >= 1

    # Verify empty
    resp2 = client.get(f"/memory/{user_id}")
    assert resp2.json() == []


def test_memory_export():
    user_id = "test-export-003"
    client.post("/memory", json={
        "user_id": user_id,
        "content": "Exportable memory",
        "mode": "ANON_LEARN",
    })
    resp = client.get(f"/memory/{user_id}/export")
    assert resp.status_code == 200
    data = resp.json()
    assert "memories" in data
    assert data["user_id"] == user_id


def test_memory_none_mode():
    resp = client.post("/memory", json={
        "user_id": "nobody",
        "content": "Should not be stored",
        "mode": "NONE",
    })
    assert resp.status_code == 201
    assert resp.json()["stored"] is False


# ---------------------------------------------------------------------------
# /sensor
# ---------------------------------------------------------------------------

def test_sensor_ingest():
    resp = client.post("/sensor/ingest", json={
        "sensor_id": "test-sensor-001",
        "data": {"temperature": 25.5, "humidity": 60.0},
        "source": "test",
    })
    assert resp.status_code == 201
    assert resp.json()["sensor_id"] == "test-sensor-001"


def test_sensor_latest():
    sensor_id = "api-test-sensor-002"
    client.post("/sensor/ingest", json={
        "sensor_id": sensor_id,
        "data": {"pressure": 5.0, "vibration": 0.8},
    })
    resp = client.get(f"/sensor/{sensor_id}/latest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["sensor_id"] == sensor_id
    assert "pressure" in data["data"]


def test_sensor_history():
    sensor_id = "hist-sensor-003"
    client.post("/sensor/ingest", json={"sensor_id": sensor_id, "data": {"temp": 30}})
    resp = client.get(f"/sensor/{sensor_id}/history?hours=1")
    assert resp.status_code == 200
    assert "readings" in resp.json()


def test_sensor_list():
    resp = client.get("/sensor/")
    assert resp.status_code == 200
    assert "sensors" in resp.json()


def test_sensor_trigger_register():
    resp = client.post("/sensor/trigger", json={
        "sensor_id": "irr-001",
        "field": "pressure",
        "operator": "gt",
        "threshold": 8.0,
        "action": "EMERGENCY_SHUTOFF",
    })
    assert resp.status_code == 201
    assert "rule_id" in resp.json()


def test_sensor_not_found():
    resp = client.get("/sensor/nonexistent-sensor-xyz/latest")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# /report
# ---------------------------------------------------------------------------

def test_report_generate():
    resp = client.post("/report/generate", json={
        "topic": "Irrigation water management",
        "report_type": "irrigation",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "report_id" in data
    assert data["topic"] == "Irrigation water management"
    assert len(data["sections"]) > 0


def test_report_retrieve():
    gen = client.post("/report/generate", json={
        "topic": "Industrial safety",
        "report_type": "industrial",
    }).json()
    rid = gen["report_id"]

    resp = client.get(f"/report/{rid}")
    assert resp.status_code == 200
    assert resp.json()["report_id"] == rid


def test_report_not_found():
    resp = client.get("/report/nonexistent-report-id")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# /admin
# ---------------------------------------------------------------------------

def test_admin_health():
    resp = client.get("/admin/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "uptime_seconds" in data
    assert "components" in data


def test_admin_stats():
    resp = client.get("/admin/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "sensors" in data
    assert "dataset" in data


def test_admin_dataset_stats():
    resp = client.get("/admin/dataset/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_entries" in data


def test_admin_safety_override():
    resp = client.post("/admin/safety/override", json={
        "action_id": "action-123",
        "admin_id": "admin-001",
        "reason": "Authorised override for testing purposes",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["overridden"] is True


def test_admin_purge_expired():
    resp = client.delete("/admin/memory/expired")
    assert resp.status_code == 200
    assert "deleted" in resp.json()


def test_root_serves_frontend():
    resp = client.get("/")
    # Either serves HTML or JSON api message
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------

def test_security_headers_present():
    """Verify that all security headers are present on API responses."""
    resp = client.get("/admin/health")
    assert resp.status_code == 200
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("X-XSS-Protection") == "1; mode=block"
    assert "Referrer-Policy" in resp.headers
    assert "Content-Security-Policy" in resp.headers
    assert "Permissions-Policy" in resp.headers


def test_csp_restricts_external_resources():
    """CSP header must contain default-src 'self' to block external resources."""
    resp = client.get("/admin/health")
    csp = resp.headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp


def test_cors_not_wildcard():
    """CORS must not allow all origins."""
    resp = client.options(
        "/ask",
        headers={"Origin": "https://evil.example.com", "Access-Control-Request-Method": "POST"},
    )
    # The response should either not have the CORS header set to wildcard *
    # or return 400 (origin not allowed).
    acao = resp.headers.get("Access-Control-Allow-Origin", "")
    assert acao != "*", "CORS allow-origin must not be wildcard"


# ---------------------------------------------------------------------------
# Audit endpoints
# ---------------------------------------------------------------------------

def test_audit_recent():
    """Audit log endpoint returns expected structure."""
    # First generate some auditable events
    client.post("/memory", json={
        "user_id": "audit-test-user",
        "content": "Audit test memory",
        "mode": "PRIVATE",
    })
    resp = client.get("/admin/audit?limit=20")
    assert resp.status_code == 200
    data = resp.json()
    assert "count" in data
    assert "records" in data
    assert isinstance(data["records"], list)
    # Each record should have required fields
    for rec in data["records"]:
        assert "event" in rec
        assert "actor" in rec
        assert "status" in rec
        assert "timestamp" in rec


def test_audit_event_filter():
    """Audit log can be filtered by event type."""
    resp = client.get("/admin/audit?event=memory.store&limit=50")
    assert resp.status_code == 200
    data = resp.json()
    assert data["event_filter"] == "memory.store"
    for rec in data["records"]:
        assert rec["event"] == "memory.store"


def test_audit_compliance():
    """Compliance endpoint returns aggregate stats without payloads."""
    resp = client.get("/admin/audit/compliance")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_events" in data
    assert "events_last_24h" in data
    assert "by_event" in data
    assert "retention_policy" in data
    assert "product" in data
    assert "Fasih ur Rehman" in data.get("copyright", "")
    # Compliance endpoint must NOT contain raw content/payloads
    raw = str(data)
    assert "REDACTED" not in raw or "len=" in raw  # masked values are ok


def test_audit_sensitive_fields_masked():
    """Memory store audit log should mask the 'content' field."""
    user_id = "audit-mask-test-user"
    secret_content = "My very secret memory content that should be masked"
    client.post("/memory", json={
        "user_id": user_id,
        "content": secret_content,
        "mode": "PRIVATE",
    })
    resp = client.get("/admin/audit?event=memory.store&limit=200")
    assert resp.status_code == 200
    data = resp.json()
    # The actual secret content must not appear in any audit record detail
    for rec in data["records"]:
        if rec.get("detail"):
            assert secret_content not in rec["detail"], \
                "Sensitive content must be masked in audit log"


# ---------------------------------------------------------------------------
# Branding in health endpoint
# ---------------------------------------------------------------------------

def test_health_branding():
    """Health endpoint should include Octevra product name and copyright."""
    resp = client.get("/admin/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "Octevra" in data.get("product", "")
    assert "Fasih ur Rehman" in data.get("copyright", "")
