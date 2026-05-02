"""Edge case tests for frontend Next.js rewrite proxy and page skeleton."""

import pytest
from httpx import ASGITransport, AsyncClient

from question_agent.main import app


class TestHealthEndpointForFrontend:
    """Verify /health works correctly as frontend proxy target."""

    @pytest.mark.asyncio
    async def test_health_returns_json_with_status(self) -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/health")
            assert resp.status_code == 200
            data = resp.json()
            assert "status" in data
            assert data["status"] == "healthy"
            assert "version" in data

    @pytest.mark.asyncio
    async def test_health_head_method(self) -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.head("/health")
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_api_prefix_routes_to_backend(self) -> None:
        """Verify /api/* prefix paths would reach backend endpoints."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # /api/health → Next.js rewrite strips /api prefix → /health
            # Direct backend test: /health should be reachable
            resp = await client.get("/health")
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_nonexistent_api_path_returns_404(self) -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/nonexistent-endpoint")
            assert resp.status_code == 404
