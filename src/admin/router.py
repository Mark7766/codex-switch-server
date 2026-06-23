from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.templating import Jinja2Templates

from src.api.deps import _db_dep, verify_admin_token
from src.config import settings
from src.services.analytics import AnalyticsService
from src.services.package_manager import PackageManager
from src.services.release_sync import ReleaseSyncService
from src.services.telemetry import TelemetryService
from src.utils.cos_storage import CosStorage

router = APIRouter(prefix="/admin")
_tpl_dir = __file__.rsplit("/", 1)[0] + "/templates"
templates = Jinja2Templates(directory=_tpl_dir)

# ICP/PSB filing numbers available in all admin templates
templates.env.globals["icp_filing_number"] = settings.icp_filing_number
templates.env.globals["psb_filing_number"] = settings.psb_filing_number


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

    mgr = PackageManager()
    pkgs = await mgr.list_packages()

    # Split event types: config operations (exclude model_call) vs stream data
    config_types = [t for t in telem_stats.event_type_counts if t.event_type != "model_call"]

    analytics_svc = AnalyticsService(db)
    uv_stats = await analytics_svc.get_uv_stats()

    # Growth stats for referral tab
    from sqlalchemy import func
    from sqlalchemy import select as sa_select

    from src.models.client_registry import ClientRegistry
    from src.models.page_event import PageEvent
    from src.models.referral import Referral
    from src.models.telemetry import TelemetryEvent

    # Core funnel
    guide_clicks = await db.scalar(sa_select(func.count()).where(PageEvent.ref.isnot(None))) or 0
    referral_installs = await db.scalar(sa_select(func.count()).select_from(Referral)) or 0
    conversion = f"{round(referral_installs / guide_clicks * 100)}%" if guide_clicks > 0 else "—"

    # Organic installs: total clients not in referrals
    total_clients = await db.scalar(sa_select(func.count()).select_from(ClientRegistry)) or 0
    organic_installs = total_clients - referral_installs

    # Share copy clicks from telemetry
    share_clicks = await db.scalar(sa_select(func.count()).where(TelemetryEvent.event_type == "share_copy_click")) or 0

    # Match rate: referrals / guide visits with ref
    match_rate = f"{round(referral_installs / guide_clicks * 100)}%" if guide_clicks > 0 else "—"

    # Active inviter rate
    total_inviters = await db.scalar(sa_select(func.count(func.distinct(Referral.inviter_client_id)))) or 0
    all_clients_with_ref = (
        await db.scalar(sa_select(func.count(func.distinct(PageEvent.ref))).where(PageEvent.ref.isnot(None))) or 1
    )
    active_rate = f"{round(total_inviters / all_clients_with_ref * 100)}%" if all_clients_with_ref > 0 else "—"

    # Top inviters
    top_rows = await db.execute(
        sa_select(Referral.inviter_client_id, func.count().label("cnt"))
        .group_by(Referral.inviter_client_id)
        .order_by(func.count().desc())
        .limit(20)
    )
    top_inviters = [{"client_id": r[0], "count": r[1]} for r in top_rows.all()]

    growth = {
        "share_clicks": share_clicks,
        "guide_clicks": guide_clicks,
        "referral_installs": referral_installs,
        "organic_installs": organic_installs,
        "conversion_rate": conversion,
        "match_rate": match_rate,
        "active_inviter_rate": active_rate,
        "top_inviters": top_inviters,
    }

    ctx = {
        "growth": growth,
        "download_stats": dl_stats,
        "telemetry": telem_stats,
        "uv_stats": uv_stats,
        "packages": pkgs,
        "config_types_json": json.dumps([t.model_dump() for t in config_types]),
        "type_counts_json": json.dumps([t.model_dump() for t in telem_stats.event_type_counts]),
        "trend_json": json.dumps([t.model_dump() for t in telem_stats.daily_trend]),
        "model_call_trend_json": json.dumps([t.model_dump() for t in telem_stats.model_call_trend]),
        "config_trend_json": json.dumps([t.model_dump() for t in telem_stats.config_trend]),
    }
    return templates.TemplateResponse(request, "dashboard.html", ctx)


@router.get("/packages", response_class=HTMLResponse, dependencies=[Depends(verify_admin_token)])
async def packages_page(request: Request) -> HTMLResponse:
    mgr = PackageManager()
    pkgs = await mgr.list_packages()
    return templates.TemplateResponse(request, "packages.html", {"request": request, "packages": pkgs})


@router.post("/packages/upload", dependencies=[Depends(verify_admin_token)])
async def upload_package(
    name: str = Form(...),
    display_name: str = Form(...),
    version: str = Form(...),
    platform: str = Form(...),
    arch: str = Form("x64"),
    description: str = Form(""),
    file: UploadFile = Form(...),
) -> RedirectResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)

    try:
        mgr = PackageManager()
        await mgr.add_package(
            name=name.strip(),
            display_name=display_name.strip(),
            version=version.strip(),
            platform=platform.strip(),
            arch=arch.strip(),
            description=description.strip(),
            local_file=tmp_path,
            original_filename=file.filename.strip() if file.filename else "",
        )

        # Upload to COS for fast China downloads
        # COS key: packages/{name}/latest/{platform}-{arch}.{ext} (deterministic, matches download)
        filename_clean = file.filename.strip() if file.filename else ""
        if filename_clean:
            cos = CosStorage()
            ext = filename_clean.rsplit(".", 1)[-1] if "." in filename_clean else "bin"
            cos_key = f"packages/{name.strip()}/latest/{platform.strip()}-{arch.strip()}.{ext}"
            content_disp = f"attachment; filename*=UTF-8''{quote(filename_clean)}"
            await cos.put(tmp_path, cos_key, content_disposition=content_disp)
    finally:
        tmp_path.unlink(missing_ok=True)

    return RedirectResponse(url="/admin/packages", status_code=302)


@router.post("/packages/delete", dependencies=[Depends(verify_admin_token)])
async def delete_package(name: str = Form(...), platform: str = Form(""), arch: str = Form("")) -> RedirectResponse:
    mgr = PackageManager()
    await mgr.delete_package(name, platform, arch)
    return RedirectResponse(url="/admin/packages", status_code=302)
