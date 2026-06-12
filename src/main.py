from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

from alembic.config import Config as AlembicConfig
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import delete

from alembic import command as alembic_command
from src.admin.router import router as admin_router
from src.api.router import router as api_router
from src.config import settings
from src.database import async_session
from src.models.download import DownloadRecord
from src.models.page_event import PageEvent
from src.models.telemetry import TelemetryEvent
from src.portal.router import router as portal_router

logger = logging.getLogger(__name__)


async def run_migrations() -> None:
    """Run Alembic migrations on startup."""
    alembic_cfg = AlembicConfig("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)

    def _upgrade():
        alembic_command.upgrade(alembic_cfg, "head")

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _upgrade)
    logger.info("Database migrations complete")


async def _cleanup_old_data() -> None:
    """Background task: periodically delete expired records to bound DB size."""
    while True:
        await asyncio.sleep(3600)  # every hour
        try:
            async with async_session() as db:
                cutoff_30 = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=30)
                r1 = await db.execute(delete(TelemetryEvent).where(TelemetryEvent.created_at < cutoff_30))
                r2 = await db.execute(delete(PageEvent).where(PageEvent.created_at < cutoff_30))
                cutoff_90 = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=90)
                r3 = await db.execute(delete(DownloadRecord).where(DownloadRecord.downloaded_at < cutoff_90))
                await db.commit()
                total = (r1.rowcount or 0) + (r2.rowcount or 0) + (r3.rowcount or 0)
                if total > 0:
                    logger.info(
                        "Data cleanup: deleted %d old records (telemetry=%d, page=%d, download=%d)",
                        total,
                        r1.rowcount or 0,
                        r2.rowcount or 0,
                        r3.rowcount or 0,
                    )
        except Exception:
            logger.exception("Data cleanup failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_migrations()
    cleanup_task = asyncio.create_task(_cleanup_old_data())
    yield
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


def create_app() -> FastAPI:
    app = FastAPI(title="codex-switch-server", version="0.1.0", lifespan=lifespan)

    @app.middleware("http")
    async def no_cache_html(request, call_next):
        response = await call_next(request)
        ct = response.headers.get("content-type", "")
        if "text/html" in ct:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    app.mount("/static", StaticFiles(directory="src/static"), name="static")
    app.include_router(portal_router)
    app.include_router(api_router)
    app.include_router(admin_router)

    return app


app = create_app()
