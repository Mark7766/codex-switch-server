from __future__ import annotations

from fastapi import APIRouter

from src.api.v1.packages import router as packages_router
from src.api.v1.telemetry import router as telemetry_router
from src.api.v1.update import router as update_router

router = APIRouter(prefix="/api/v1")
router.include_router(update_router)
router.include_router(packages_router)
router.include_router(telemetry_router)
