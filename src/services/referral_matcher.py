from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from sqlalchemy import select

from src.database import async_session
from src.models.client_registry import ClientRegistry
from src.models.page_event import PageEvent
from src.models.referral import Referral
from src.models.telemetry import TelemetryEvent

logger = logging.getLogger(__name__)

_WINDOW_DAYS = 7  # Match page_events within 7 days before first app_start


async def _run_referral_match() -> None:
    """Background task: match new installs to referrers via IP + time window."""
    while True:
        await asyncio.sleep(3600)  # every hour
        try:
            async with async_session() as db:
                # Find clients not yet in referrals (as invitee)
                existing_subq = select(Referral.invitee_client_id)
                rows = await db.execute(
                    select(ClientRegistry.client_id, ClientRegistry.id)
                    .where(ClientRegistry.client_id.notin_(existing_subq))
                    .limit(100)
                )
                new_clients = rows.all()
                if not new_clients:
                    continue

                matched = 0
                for client_id, _reg_id in new_clients:
                    # Find earliest app_start for this client
                    first_event = await db.scalar(
                        select(TelemetryEvent)
                        .where(
                            TelemetryEvent.client_id == client_id,
                            TelemetryEvent.event_type == "app_start",
                        )
                        .order_by(TelemetryEvent.created_at.asc())
                        .limit(1)
                    )
                    if not first_event or not first_event.ip_hash:
                        continue

                    # Look back WINDOW_DAYS for a page_event with matching IP and ref
                    cutoff = first_event.created_at - timedelta(days=_WINDOW_DAYS)
                    page = await db.scalar(
                        select(PageEvent)
                        .where(
                            PageEvent.page == "/guide",
                            PageEvent.ref.isnot(None),
                            PageEvent.ip_hash == first_event.ip_hash,
                            PageEvent.created_at >= cutoff,
                            PageEvent.created_at <= first_event.created_at,
                        )
                        .order_by(PageEvent.created_at.desc())
                        .limit(1)
                    )
                    if not page or not page.ref:
                        continue

                    # Record referral
                    referral = Referral(
                        inviter_client_id=page.ref,
                        invitee_client_id=client_id,
                        ip_hash=first_event.ip_hash,
                        matched_page_event_id=page.id,
                        platform=first_event.platform,
                        arch=first_event.arch,
                    )
                    db.add(referral)
                    matched += 1

                await db.commit()
                if matched:
                    logger.info("Referral match: %d new clients, %d matched", len(new_clients), matched)
        except Exception:
            logger.exception("Referral matcher failed")


async def start_referral_matcher() -> asyncio.Task | None:
    """Start the referral matcher background task. Returns the task for cleanup."""
    return asyncio.create_task(_run_referral_match())
