from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_app_starts_and_returns_200_on_root(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_app_returns_404_on_nonexistent(client: AsyncClient):
    response = await client.get("/nonexistent")
    assert response.status_code == 404
