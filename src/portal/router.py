from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from starlette.templating import Jinja2Templates

from src.config import settings
from src.database import async_session
from src.models.page_event import PageEvent

router = APIRouter()
_tpl_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_tpl_dir))

# ICP/PSB filing numbers available in all portal templates
templates.env.globals["icp_filing_number"] = settings.icp_filing_number
templates.env.globals["psb_filing_number"] = settings.psb_filing_number


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html")


@router.get("/download", response_class=HTMLResponse)
async def download(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "download.html")


@router.get("/guide", response_class=HTMLResponse)
async def guide(request: Request) -> HTMLResponse:
    ref = request.query_params.get("ref")
    if ref:
        ip = request.client.host if request.client else ""
        ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:64] if ip else ""
        ua = request.headers.get("user-agent", "")[:256]
        asyncio.create_task(_record_guide_ref(ref, ip_hash, ua))
    return templates.TemplateResponse(request, "guide.html")


async def _record_guide_ref(ref: str, ip_hash: str, user_agent: str) -> None:
    """Record a referral-guided page view without blocking the response."""
    try:
        async with async_session() as db:
            raw = f"{ip_hash}{user_agent}"
            visitor_id = hashlib.sha256(raw.encode()).hexdigest()[:16]
            db.add(
                PageEvent(
                    event_type="click",  # not pageview to avoid double-counting PV from portal.js
                    page="/guide",
                    ip_hash=ip_hash,
                    user_agent=user_agent,
                    ref=ref,
                    visitor_id=visitor_id,
                )
            )
            await db.commit()
    except Exception:
        pass  # fire-and-forget, best effort
