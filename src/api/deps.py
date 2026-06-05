from __future__ import annotations

from fastapi import Cookie, Depends, HTTPException, Request
from itsdangerous import BadSignature, URLSafeTimedSerializer

from src.config import settings
from src.database import get_db

_db_dep = Depends(get_db)


def _get_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.admin_token, salt="admin-session")


async def verify_admin_token(request: Request, admin_session: str | None = Cookie(default=None)) -> bool:
    if not admin_session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        s = _get_serializer()
        s.loads(admin_session)
    except BadSignature:
        raise HTTPException(status_code=401, detail="Invalid session") from None
    return True
