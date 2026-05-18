"""Edge case tests for knowledge base deletion."""

import pytest
from httpx import ASGITransport, AsyncClient

from question_agent.kb.database import close_db, create_kb, delete_kb, init_db
from question_agent.kb.models import KnowledgeBaseCreate
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


async def test_delete_nonexistent_kb_returns_404(client: AsyncClient) -> None:
    resp = await client.delete("/v1/knowledge-bases/nonexistent_id")
    assert resp.status_code == 404


async def test_delete_kb_twice_second_returns_404(client: AsyncClient) -> None:
    create_resp = await client.post("/v1/knowledge-bases", json={"name": "Temp KB"})
    kb_id = create_resp.json()["id"]

    first = await client.delete(f"/v1/knowledge-bases/{kb_id}")
    assert first.status_code == 204

    second = await client.delete(f"/v1/knowledge-bases/{kb_id}")
    assert second.status_code == 404


async def test_delete_kb_removes_from_list(client: AsyncClient) -> None:
    create_resp = await client.post("/v1/knowledge-bases", json={"name": "To Delete"})
    kb_id = create_resp.json()["id"]

    await client.delete(f"/v1/knowledge-bases/{kb_id}")

    list_resp = await client.get("/v1/knowledge-bases")
    kbs = list_resp.json()
    assert all(kb["id"] != kb_id for kb in kbs)


async def test_delete_kb_cascades_documents(client: AsyncClient) -> None:
    create_resp = await client.post("/v1/knowledge-bases", json={"name": "Cascade"})
    kb_id = create_resp.json()["id"]

    # After deletion, documents endpoint should 404 for this kb
    await client.delete(f"/v1/knowledge-bases/{kb_id}")

    docs_resp = await client.get(f"/v1/knowledge-bases/{kb_id}/documents")
    assert docs_resp.status_code == 404


async def test_delete_kb_db_function_returns_false_for_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("question_agent.kb.database.settings.kb_db_path", tmp_path / "test_fn.db")
    await init_db()
    try:
        result = await delete_kb("does_not_exist")
        assert result is False
    finally:
        await close_db()


async def test_delete_kb_db_function_returns_true_for_existing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("question_agent.kb.database.settings.kb_db_path", tmp_path / "test_fn2.db")
    await init_db()
    try:
        kb = await create_kb(KnowledgeBaseCreate(name="Delete Me"))
        result = await delete_kb(kb.id)
        assert result is True
    finally:
        await close_db()


async def test_delete_does_not_affect_other_kbs(client: AsyncClient) -> None:
    r1 = await client.post("/v1/knowledge-bases", json={"name": "Keep"})
    r2 = await client.post("/v1/knowledge-bases", json={"name": "Remove"})
    keep_id = r1.json()["id"]
    remove_id = r2.json()["id"]

    await client.delete(f"/v1/knowledge-bases/{remove_id}")

    list_resp = await client.get("/v1/knowledge-bases")
    kbs = list_resp.json()
    ids = [kb["id"] for kb in kbs]
    assert keep_id in ids
    assert remove_id not in ids
