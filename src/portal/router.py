from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from starlette.templating import Jinja2Templates

router = APIRouter()
_tpl_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_tpl_dir))


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html")


@router.get("/download", response_class=HTMLResponse)
async def download(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "download.html")


@router.get("/guide", response_class=HTMLResponse)
async def guide(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "guide.html")
