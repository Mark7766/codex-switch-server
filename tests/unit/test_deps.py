from __future__ import annotations

import pytest
from fastapi import HTTPException

from src.api.deps import _get_serializer, verify_admin_token


@pytest.mark.asyncio
async def test_verify_admin_token_no_cookie():
    with pytest.raises(HTTPException) as exc:
        await verify_admin_token(request=None, admin_session=None)  # type: ignore[arg-type]
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_verify_admin_token_invalid():
    with pytest.raises(HTTPException) as exc:
        await verify_admin_token(request=None, admin_session="bad-token")  # type: ignore[arg-type]
    assert exc.value.status_code == 401


def test_get_serializer_returns_valid_object():
    s = _get_serializer()
    token = s.dumps("admin")
    loaded = s.loads(token)
    assert loaded == "admin"
