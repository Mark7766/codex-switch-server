from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import _db_dep
from src.schemas.release import APIResponse
from src.schemas.telemetry import IngestResult, TelemetryPayload
from src.services.telemetry import TelemetryService

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.post("/events", response_model=APIResponse[IngestResult])
async def ingest_events(payload: TelemetryPayload, db: AsyncSession = _db_dep) -> APIResponse[IngestResult]:
    svc = TelemetryService(db)
    result = await svc.ingest(payload)
    return APIResponse(data=result)
