"""Edge case tests for knowledge base API endpoints (HTTP-level)."""

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


class TestKbApiHttpMethods:
    async def test_put_knowledge_bases_returns_405(self, client: AsyncClient) -> None:
        resp = await client.put("/v1/knowledge-bases", json={"name": "test"})
        assert resp.status_code == 405

    async def test_delete_knowledge_bases_returns_405(self, client: AsyncClient) -> None:
        resp = await client.delete("/v1/knowledge-bases")
        assert resp.status_code == 405

    async def test_patch_knowledge_bases_returns_405(self, client: AsyncClient) -> None:
        resp = await client.patch("/v1/knowledge-bases", json={"name": "test"})
        assert resp.status_code == 405


class TestKbApiInputBoundary:
    async def test_create_missing_name_returns_422(self, client: AsyncClient) -> None:
        resp = await client.post("/v1/knowledge-bases", json={})
        assert resp.status_code == 422

    async def test_create_whitespace_only_name_accepted(self, client: AsyncClient) -> None:
        resp = await client.post("/v1/knowledge-bases", json={"name": "   "})
        assert resp.status_code == 201

    async def test_create_name_too_long_returns_422(self, client: AsyncClient) -> None:
        resp = await client.post("/v1/knowledge-bases", json={"name": "x" * 201})
        assert resp.status_code == 422

    async def test_create_unicode_emoji_name_succeeds(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/v1/knowledge-bases",
            json={"name": "📚 数学题库 🎓"},
        )
        assert resp.status_code == 201
        assert "📚" in resp.json()["name"]

    async def test_create_null_description_succeeds(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/v1/knowledge-bases",
            json={"name": "Test", "description": None},
        )
        assert resp.status_code == 201

    async def test_create_extra_fields_ignored(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/v1/knowledge-bases",
            json={"name": "Test", "unknown_field": "value"},
        )
        assert resp.status_code == 201


class TestKbApiContentType:
    async def test_create_without_content_type_returns_422(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/v1/knowledge-bases",
            content=b'{"name": "test"}',
        )
        assert resp.status_code == 422

    async def test_list_accepts_any_method_params(self, client: AsyncClient) -> None:
        resp = await client.get("/v1/knowledge-bases")
        assert resp.status_code == 200
