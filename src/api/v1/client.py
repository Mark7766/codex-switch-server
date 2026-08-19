from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import _db_dep
from src.models.client_registry import ClientRegistry
from src.models.referral import Referral
from src.models.telemetry import TelemetryEvent

router = APIRouter(prefix="/client", tags=["client"])

# Community stats cache
_community_cache: dict | None = None
_community_cache_time: float = 0
_COMMUNITY_CACHE_TTL = 3600  # 1 hour


@router.get("/community")
async def community_stats(db: AsyncSession = _db_dep) -> dict:
    """Return community count for sidebar display: '和 X 位开发者一起使用'."""
    global _community_cache, _community_cache_time

    now = time.time()
    if _community_cache and (now - _community_cache_time) < _COMMUNITY_CACHE_TTL:
        return _community_cache

    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=30)
    active = await db.scalar(
        select(func.count(func.distinct(TelemetryEvent.client_id))).where(
            TelemetryEvent.created_at >= cutoff, TelemetryEvent.client_id != ""
        )
    )
    # v2.0.0: 累计注册客户端数（侧边栏「和 X 位朋友一起使用」显示该口径）
    total_clients = await db.scalar(select(func.count()).select_from(ClientRegistry)) or 0

    _community_cache = {
        "code": 0,
        "data": {"active_users": active or 0, "total_clients": total_clients},
    }
    _community_cache_time = now
    return _community_cache


@router.get("/{client_id}/profile")
async def client_profile(client_id: str, db: AsyncSession = _db_dep) -> dict:
    """Return client identity: number, early member tag, join date, invite count."""
    reg = await db.scalar(select(ClientRegistry).where(ClientRegistry.client_id == client_id))

    if not reg:
        # Auto-register: insert if not exists
        reg = ClientRegistry(client_id=client_id)
        db.add(reg)
        await db.flush()

    # Joined date: earliest app_start
    joined = await db.scalar(select(func.min(TelemetryEvent.created_at)).where(TelemetryEvent.client_id == client_id))

    # Early member: first used Codex Switch before v1.11.0 shipped
    v111_ship_date = datetime(2026, 6, 17).replace(tzinfo=None)
    is_early = bool(joined and joined < v111_ship_date)

    # Invite count
    invite_count = await db.scalar(
        select(func.count()).select_from(Referral).where(Referral.inviter_client_id == client_id)
    )
    invite_count = invite_count or 0

    return {
        "code": 0,
        "data": {
            "client_number": reg.id,
            "is_early_member": is_early,
            "joined_date": str(joined)[:10] if joined else "",
            "invite_count": invite_count,
        },
    }
