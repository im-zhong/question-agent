"""Edge case tests for KB document upload validation — format, size, path safety."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from question_agent.kb.database import close_db, init_db
from question_agent.main import app


@pytest.fixture
async def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncClient:
    monkeypatch.setattr("question_agent.kb.database.settings.kb_db_path", tmp_path / "kb.db")
    monkeypatch.setattr("question_agent.config.settings.kb_db_path", tmp_path / "kb.db")
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await close_db()


async def _create_kb(client: AsyncClient) -> str:
    resp = await client.post("/v1/knowledge-bases", json={"name": "Validation Test KB"})
    assert resp.status_code == 201
    return resp.json()["id"]


class TestUnsupportedFormat:
    async def test_csv_returns_422(self, client: AsyncClient) -> None:
        kb_id = await _create_kb(client)
        files = {"file": ("data.csv", b"a,b,c", "text/csv")}
        resp = await client.post(f"/v1/knowledge-bases/{kb_id}/documents", files=files)
        assert resp.status_code == 422

    async def test_legacy_doc_returns_422(self, client: AsyncClient) -> None:
        kb_id = await _create_kb(client)
        files = {"file": ("legacy.doc", b"old", "application/msword")}
        resp = await client.post(f"/v1/knowledge-bases/{kb_id}/documents", files=files)
        assert resp.status_code == 422


class TestFileSizeLimit:
    async def test_over_50mb_returns_413(self, client: AsyncClient) -> None:
        kb_id = await _create_kb(client)
        big_content = b"x" * (50 * 1024 * 1024 + 1)
        files = {"file": ("big.txt", big_content, "text/plain")}
        resp = await client.post(f"/v1/knowledge-bases/{kb_id}/documents", files=files)
        assert resp.status_code == 413


class TestPathTraversalSafety:
    async def test_path_traversal_filename_saves_safely(self, client: AsyncClient) -> None:
        kb_id = await _create_kb(client)
        files = {"file": ("../../../etc/passwd.txt", b"safe", "text/plain")}
        resp = await client.post(f"/v1/knowledge-bases/{kb_id}/documents", files=files)
        assert resp.status_code == 201
        doc = resp.json()["document"]
        assert doc["filename"] == "../../../etc/passwd.txt"

    async def test_path_traversal_saves_in_kb_dir(
        self, client: AsyncClient, tmp_path: Path
    ) -> None:
        kb_id = await _create_kb(client)
        files = {"file": ("../../escape.txt", b"data", "text/plain")}
        resp = await client.post(f"/v1/knowledge-bases/{kb_id}/documents", files=files)
        assert resp.status_code == 201
        doc = resp.json()["document"]
        file_path = Path(doc["file_path"])
        assert kb_id in str(file_path)
        assert file_path.exists()
        assert file_path.read_bytes() == b"data"


class TestKbNotFound:
    async def test_upload_to_nonexistent_kb_returns_404(self, client: AsyncClient) -> None:
        files = {"file": ("test.txt", b"hello", "text/plain")}
        resp = await client.post("/v1/knowledge-bases/nonexistent/documents", files=files)
        assert resp.status_code == 404

    async def test_get_documents_nonexistent_kb_returns_404(self, client: AsyncClient) -> None:
        resp = await client.get("/v1/knowledge-bases/nonexistent/documents")
        assert resp.status_code == 404

    async def test_get_kps_nonexistent_kb_returns_404(self, client: AsyncClient) -> None:
        resp = await client.get("/v1/knowledge-bases/nonexistent/knowledge-points")
        assert resp.status_code == 404
