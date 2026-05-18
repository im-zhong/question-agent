"""Additional edge case tests for KB deletion — cascade with knowledge points."""

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


async def test_delete_kb_cascades_knowledge_points(client: AsyncClient) -> None:
    """Deleting a KB should remove its knowledge points."""
    create_resp = await client.post("/v1/knowledge-bases", json={"name": "Cascade KP"})
    kb_id = create_resp.json()["id"]

    # Upload a document to create knowledge points
    text = "第一章 力学\n牛顿第二定律描述了力等于质量乘以加速度。"
    upload_resp = await client.post(
        f"/v1/knowledge-bases/{kb_id}/documents",
        files={"file": ("physics.txt", text.encode(), "text/plain")},
    )
    assert upload_resp.status_code == 201
    kp_count = upload_resp.json()["knowledge_point_count"]
    assert kp_count > 0

    # Delete the KB
    resp = await client.delete(f"/v1/knowledge-bases/{kb_id}")
    assert resp.status_code == 204

    # Knowledge points endpoint should 404 for deleted KB
    kps_resp = await client.get(f"/v1/knowledge-bases/{kb_id}/knowledge-points")
    assert kps_resp.status_code == 404


async def test_delete_kb_with_special_chars_name(client: AsyncClient) -> None:
    """Deleting a KB with unicode/emoji name should work."""
    create_resp = await client.post("/v1/knowledge-bases", json={"name": "📚 数学题库 🎓"})
    kb_id = create_resp.json()["id"]
    assert create_resp.status_code == 201

    resp = await client.delete(f"/v1/knowledge-bases/{kb_id}")
    assert resp.status_code == 204
