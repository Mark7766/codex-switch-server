from __future__ import annotations

import re
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from src.utils.cos_storage import CosStorage

router = APIRouter(prefix="/files", tags=["files"])

# Only allow safe filenames: alphanumeric, dot, dash, underscore
_SAFE_FILENAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")


@router.get("/{filename}")
async def download_file(filename: str) -> RedirectResponse:
    """Download a static file, COS Guangzhou first, local nginx fallback.

    COS key: ``files/{filename}``.
    """
    # Security: reject path traversal and unsafe filenames
    if not _SAFE_FILENAME_RE.match(filename) or ".." in filename:
        raise HTTPException(status_code=404, detail="File not found")

    cos_key = f"files/{filename}"

    # 1. COS → Guangzhou fast download (302 redirect)
    cos = CosStorage()
    if cos.exists(cos_key):
        headers = {}
        if filename:
            headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(filename)}"
        return RedirectResponse(url=cos.public_url(cos_key), status_code=302, headers=headers)

    # 2. Fallback: nginx serves /static/files/{filename} directly (sendfile, zero-copy)
    return RedirectResponse(url=f"/static/files/{filename}", status_code=302)
