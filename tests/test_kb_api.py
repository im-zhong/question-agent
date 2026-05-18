"""Tests for knowledge base API endpoints."""

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


async def test_create_kb_returns_201(client: AsyncClient) -> None:
    resp = await client.post("/v1/knowledge-bases", json={"name": "数学知识库"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "数学知识库"
    assert "id" in data
    assert data["document_count"] == 0


async def test_create_kb_empty_name_returns_422(client: AsyncClient) -> None:
    resp = await client.post("/v1/knowledge-bases", json={"name": ""})
    assert resp.status_code == 422


async def test_create_kb_with_optional_fields(client: AsyncClient) -> None:
    resp = await client.post(
        "/v1/knowledge-bases",
        json={"name": "物理", "description": "高中物理", "subject": "物理", "grade_level": "高中"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["subject"] == "物理"
    assert data["grade_level"] == "高中"


async def test_list_kbs_returns_list(client: AsyncClient) -> None:
    await client.post("/v1/knowledge-bases", json={"name": "KB1"})
    resp = await client.get("/v1/knowledge-bases")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


async def test_list_kbs_ordered_by_created_desc(client: AsyncClient) -> None:
    await client.post("/v1/knowledge-bases", json={"name": "First"})
    await client.post("/v1/knowledge-bases", json={"name": "Second"})
    resp = await client.get("/v1/knowledge-bases")
    data = resp.json()
    assert data[0]["name"] == "Second"


async def test_create_kb_location_header(client: AsyncClient) -> None:
    resp = await client.post("/v1/knowledge-bases", json={"name": "WithLocation"})
    assert "location" in resp.headers
    assert "/v1/knowledge-bases/" in resp.headers["location"]


async def test_delete_kb_returns_204(client: AsyncClient) -> None:
    create_resp = await client.post("/v1/knowledge-bases", json={"name": "ToDelete"})
    kb_id = create_resp.json()["id"]
    resp = await client.delete(f"/v1/knowledge-bases/{kb_id}")
    assert resp.status_code == 204


async def test_delete_nonexistent_kb_returns_404(client: AsyncClient) -> None:
    resp = await client.delete("/v1/knowledge-bases/nonexistent")
    assert resp.status_code == 404
