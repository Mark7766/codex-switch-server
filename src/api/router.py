from __future__ import annotations

from fastapi import APIRouter

from src.api.v1.admin_api import router as admin_api_router
from src.api.v1.analytics import router as analytics_router
from src.api.v1.files import router as files_router
from src.api.v1.packages import router as packages_router
from src.api.v1.plugins import router as plugins_router
from src.api.v1.telemetry import router as telemetry_router
from src.api.v1.update import router as update_router
from src.api.v1.updates import router as updates_router

router = APIRouter(prefix="/api/v1")
router.include_router(update_router)
router.include_router(updates_router)
router.include_router(packages_router)
router.include_router(files_router)
router.include_router(plugins_router)
router.include_router(telemetry_router)
router.include_router(analytics_router)
router.include_router(admin_api_router)
