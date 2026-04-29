"""Tests for the health check endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from question_agent.main import app


@pytest.mark.asyncio
async def test_health_check() -> None:
    """The /health endpoint returns 200 with status=healthy."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
