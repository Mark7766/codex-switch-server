from __future__ import annotations

from fastapi import APIRouter

from src.api.v1.admin_api import router as admin_api_router
from src.api.v1.analytics import router as analytics_router
from src.api.v1.packages import router as packages_router
from src.api.v1.telemetry import router as telemetry_router
from src.api.v1.update import router as update_router

router = APIRouter(prefix="/api/v1")
router.include_router(update_router)
router.include_router(packages_router)
router.include_router(telemetry_router)
router.include_router(analytics_router)
router.include_router(admin_api_router)
