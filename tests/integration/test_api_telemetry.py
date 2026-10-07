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
    # v3.0.0 起 client_id 变为可选，空对象已是合法 payload；这里改用**真正畸形**的事件体
    # （events 里的元素缺 event_type / timestamp）来保持「畸形输入 → 422」的断言。
    resp = await client.post("/api/v1/telemetry/events", json={"events": [{"properties": {}}]})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_ingest_without_client_id_returns_200(client: AsyncClient):
    """v3.0.0 客户端不再上报 client_id —— 必须 200（修复前是 422，事件被静默丢弃）。"""
    payload = {
        "app_version": "3.0.0",
        "platform": "darwin",
        "arch": "arm64",
        "os_version": "15.0",
        "events": [
            {
                "event_type": "config_write",
                "timestamp": "2026-10-07T10:00:00Z",
                "properties": {"fields_changed": ["codex"]},
            },
            {"event_type": "tool_install", "timestamp": "2026-10-07T10:01:00Z", "properties": {"tool": "codex"}},
        ],
    }
    resp = await client.post("/api/v1/telemetry/events", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["accepted"] == 2
    assert data["data"]["rejected"] == 0


@pytest.mark.asyncio
async def test_ingest_without_client_id_does_not_register_empty_client(client: AsyncClient, db_session):
    """空 client_id 不得写进 client_registry（否则表里会出现 '' 脏数据）。"""
    from sqlalchemy import func, select

    from src.models.client_registry import ClientRegistry

    payload = {
        "app_version": "3.0.0",
        "events": [{"event_type": "tool_install", "timestamp": "2026-10-07T10:02:00Z"}],
    }
    resp = await client.post("/api/v1/telemetry/events", json=payload)
    assert resp.status_code == 200

    empty_rows = await db_session.scalar(
        select(func.count()).select_from(ClientRegistry).where(ClientRegistry.client_id == "")
    )
    assert empty_rows == 0


@pytest.mark.asyncio
async def test_ingest_legacy_client_still_registers(client: AsyncClient, db_session):
    """老客户端仍带 client_id —— 自动注册行为与升级前一致。"""
    from sqlalchemy import func, select

    from src.models.client_registry import ClientRegistry

    payload = {
        "client_id": "legacy-client-1",
        "app_version": "2.3.0",
        "events": [{"event_type": "app_start", "timestamp": "2026-10-07T10:03:00Z"}],
    }
    resp = await client.post("/api/v1/telemetry/events", json=payload)
    assert resp.status_code == 200
    assert resp.json()["data"]["accepted"] == 1

    registered = await db_session.scalar(
        select(func.count()).select_from(ClientRegistry).where(ClientRegistry.client_id == "legacy-client-1")
    )
    assert registered == 1


@pytest.mark.asyncio
async def test_ingest_model_call_aggregated(client: AsyncClient):
    """model_call with count>1 is accepted and count is stored."""
    payload = {
        "client_id": "agg1",
        "app_version": "1.6.0",
        "platform": "macos",
        "events": [
            {
                "event_type": "model_call",
                "timestamp": "2026-06-12T10:00:00Z",
                "count": 47,
                "period_start": 1718163000,
                "period_end": 1718163300,
            }
        ],
    }
    resp = await client.post("/api/v1/telemetry/events", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["accepted"] == 1
    assert data["data"]["rejected"] == 0


@pytest.mark.asyncio
async def test_ingest_model_call_no_dedup(client: AsyncClient):
    """model_call is not deduped — same event sent twice is accepted twice."""
    payload = {
        "client_id": "nodup1",
        "events": [{"event_type": "model_call", "timestamp": "2026-06-12T10:05:00Z"}],
    }
    resp1 = await client.post("/api/v1/telemetry/events", json=payload)
    resp2 = await client.post("/api/v1/telemetry/events", json=payload)
    assert resp1.json()["data"]["accepted"] == 1
    assert resp2.json()["data"]["accepted"] == 1  # not rejected


@pytest.mark.asyncio
async def test_ingest_backward_compat_no_count(client: AsyncClient):
    """Events without count field (old clients) default to count=1."""
    payload = {
        "client_id": "old1",
        "events": [{"event_type": "proxy_start", "timestamp": "2026-06-12T10:10:00Z"}],
    }
    resp = await client.post("/api/v1/telemetry/events", json=payload)
    assert resp.status_code == 200
    assert resp.json()["data"]["accepted"] == 1
