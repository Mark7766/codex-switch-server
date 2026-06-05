from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.templating import Jinja2Templates

from src.api.deps import _db_dep, verify_admin_token
from src.config import settings
from src.services.release_sync import ReleaseSyncService
from src.services.telemetry import TelemetryService

router = APIRouter(prefix="/admin")
_tpl_dir = __file__.rsplit("/", 1)[0] + "/templates"
templates = Jinja2Templates(directory=_tpl_dir)


def _make_session() -> str:
    s = URLSafeTimedSerializer(settings.admin_token, salt="admin-session")
    return s.dumps("admin")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "login.html")


@router.post("/login")
async def login(token: str = Form(...)) -> RedirectResponse:
    if token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Invalid token")
    resp = RedirectResponse(url="/admin", status_code=302)
    resp.set_cookie("admin_session", _make_session(), httponly=True, samesite="strict", max_age=86400)
    return resp


@router.get("", response_class=HTMLResponse, dependencies=[Depends(verify_admin_token)])
async def dashboard(request: Request, db: AsyncSession = _db_dep) -> HTMLResponse:
    dl_svc = ReleaseSyncService(db)
    dl_stats = await dl_svc.get_download_stats(range_days=30)

    telem_svc = TelemetryService(db)
    telem_stats = await telem_svc.get_stats(range_days=30)

    ctx = {
        "download_stats": dl_stats,
        "telemetry": telem_stats,
        "type_counts_json": json.dumps([t.model_dump() for t in telem_stats.event_type_counts]),
        "trend_json": json.dumps([t.model_dump() for t in telem_stats.daily_trend]),
    }
    return templates.TemplateResponse(request, "dashboard.html", ctx)
