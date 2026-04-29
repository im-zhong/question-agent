"""Smoke tests — verify the running server is healthy and all API docs are accessible."""

import httpx
import pytest

BASE = "http://localhost:8000"


@pytest.mark.asyncio
async def test_health_returns_200():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE}/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "version" in data


@pytest.mark.asyncio
async def test_docs_accessible():
    """Swagger UI should be reachable (debug mode must be on)."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE}/docs")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_redoc_accessible():
    """ReDoc should be reachable (debug mode must be on)."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE}/redoc")
        assert resp.status_code == 200
