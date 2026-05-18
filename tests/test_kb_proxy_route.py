"""Test that KB endpoints are reachable after Vite proxy strips /api prefix.

The Vite dev proxy rewrites /api/v1/knowledge-bases -> /v1/knowledge-bases
(so it strips the /api prefix). The backend must serve on paths that work
after this rewrite, just like all other endpoints in main.py do.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from question_agent.kb.database import close_db, init_db
from question_agent.main import app


@pytest.fixture
async def client(tmp_path, monkeypatch) -> AsyncClient:
    """ASGI client with a temp KB database."""
    monkeypatch.setattr("question_agent.kb.database.settings.kb_db_path", tmp_path / "test_kb.db")
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await close_db()


async def test_create_kb_after_proxy_rewrite(client: AsyncClient) -> None:
    """After Vite proxy strips /api, POST /v1/knowledge-bases should work."""
    resp = await client.post("/v1/knowledge-bases", json={"name": "数学知识库"})
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"


async def test_list_kb_after_proxy_rewrite(client: AsyncClient) -> None:
    """After Vite proxy strips /api, GET /v1/knowledge-bases should work."""
    resp = await client.get("/v1/knowledge-bases")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
