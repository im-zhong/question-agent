"""Smoke tests — verify the app is healthy and all API docs are accessible."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_200(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "version" in data


@pytest.mark.asyncio
async def test_docs_accessible(client: AsyncClient):
    """Swagger UI should be reachable (debug mode must be on)."""
    resp = await client.get("/docs")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_redoc_accessible(client: AsyncClient):
    """ReDoc should be reachable (debug mode must be on)."""
    resp = await client.get("/redoc")
    assert resp.status_code == 200
