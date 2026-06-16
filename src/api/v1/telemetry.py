from __future__ import annotations

import hashlib

from fastapi import APIRouter, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import _db_dep
from src.schemas.release import APIResponse
from src.schemas.telemetry import IngestResult, TelemetryPayload
from src.services.telemetry import TelemetryService

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.post("/events", response_model=APIResponse[IngestResult])
async def ingest_events(
    payload: TelemetryPayload,
    request: Request,
    db: AsyncSession = _db_dep,
) -> APIResponse[IngestResult]:
    ip = request.client.host if request.client else ""
    ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:64] if ip else ""
    svc = TelemetryService(db)
    result = await svc.ingest(payload, ip_hash=ip_hash)

    # Auto-register new clients on first app_start
    from sqlalchemy import insert

    from src.models.client_registry import ClientRegistry

    try:
        await db.execute(insert(ClientRegistry).values(client_id=payload.client_id).prefix_with("OR IGNORE"))
        await db.commit()
    except Exception:
        pass

    return APIResponse(data=result)
