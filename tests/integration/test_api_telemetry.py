from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ingest_valid_events(client: AsyncClient):
    payload = {
        "client_id": "client1",
        "app_version": "1.4.0",
        "platform": "macos",
        "arch": "arm64",
        "events": [
            {"event_type": "proxy_start", "timestamp": "2026-06-05T10:00:00Z", "properties": {"port": 11435}},
            {"event_type": "model_call", "timestamp": "2026-06-05T10:01:00Z", "properties": {"model": "deepseek"}},
        ],
    }
    resp = await client.post("/api/v1/telemetry/events", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["accepted"] == 2
    assert data["data"]["rejected"] == 0


@pytest.mark.asyncio
async def test_ingest_duplicate_rejected(client: AsyncClient):
    payload = {
        "client_id": "dup1",
        "app_version": "1.4.0",
        "platform": "macos",
        "arch": "arm64",
        "events": [{"event_type": "proxy_start", "timestamp": "2026-06-05T10:00:00Z", "properties": {}}],
    }
    resp1 = await client.post("/api/v1/telemetry/events", json=payload)
    resp2 = await client.post("/api/v1/telemetry/events", json=payload)
    assert resp1.json()["data"]["accepted"] == 1
    assert resp2.json()["data"]["rejected"] == 1


@pytest.mark.asyncio
async def test_ingest_invalid_event_type_rejected(client: AsyncClient):
    payload = {
        "client_id": "c1",
        "events": [{"event_type": "unknown_event", "timestamp": "2026-06-05T10:00:00Z", "properties": {}}],
    }
    resp = await client.post("/api/v1/telemetry/events", json=payload)
    data = resp.json()
    assert data["data"]["accepted"] == 0
    assert data["data"]["rejected"] == 1


@pytest.mark.asyncio
async def test_ingest_empty_payload(client: AsyncClient):
    resp = await client.post("/api/v1/telemetry/events", json={"client_id": "c1", "events": []})
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["accepted"] == 0


@pytest.mark.asyncio
async def test_ingest_missing_required_fields_returns_422(client: AsyncClient):
    resp = await client.post("/api/v1/telemetry/events", json={"bad": "data"})
    assert resp.status_code == 422
