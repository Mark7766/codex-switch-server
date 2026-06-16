from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ensure all models are imported so Base.metadata knows about them
import src.models.client_registry  # noqa: F401
import src.models.download  # noqa: F401
import src.models.page_event  # noqa: F401
import src.models.referral  # noqa: F401
import src.models.release  # noqa: F401
import src.models.telemetry  # noqa: F401
from src.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session


async def backfill_null_package_names() -> None:
    """Backfill download_records with NULL package_name to 'codex-switch'.

    Old records were created before the package_name field was populated.
    """
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "UPDATE download_records SET package_name = 'codex-switch' "
                "WHERE package_name IS NULL OR package_name = ''"
            )
        )
