from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from alembic.config import Config as AlembicConfig
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from alembic import command as alembic_command
from src.admin.router import router as admin_router
from src.api.router import router as api_router
from src.config import settings
from src.portal.router import router as portal_router

logger = logging.getLogger(__name__)


async def run_migrations() -> None:
    """Run Alembic migrations on startup."""
    import asyncio

    alembic_cfg = AlembicConfig("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)

    def _upgrade():
        alembic_command.upgrade(alembic_cfg, "head")

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _upgrade)
    logger.info("Database migrations complete")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_migrations()
    yield


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
