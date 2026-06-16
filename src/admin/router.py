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

    from src.models.page_event import PageEvent
    from src.models.referral import Referral

    total_clicks = await db.scalar(sa_select(func.count()).where(PageEvent.ref.isnot(None))) or 0
    total_installs = await db.scalar(sa_select(func.count()).select_from(Referral)) or 0
    conversion = f"{round(total_installs / total_clicks * 100)}%" if total_clicks > 0 else "—"

    top_rows = await db.execute(
        sa_select(Referral.inviter_client_id, func.count().label("cnt"))
        .group_by(Referral.inviter_client_id)
        .order_by(func.count().desc())
        .limit(20)
    )
    top_inviters = [{"client_id": r[0], "count": r[1]} for r in top_rows.all()]

    growth = {
        "total_clicks": total_clicks,
        "total_installs": total_installs,
        "conversion_rate": conversion,
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
