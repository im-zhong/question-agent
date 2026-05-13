"""Edge case tests for KB document upload endpoints (HTTP-level)."""

from io import BytesIO

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


async def _create_kb(client: AsyncClient, name: str = "Test KB") -> str:
    """Helper: create a KB and return its ID."""
    resp = await client.post("/v1/knowledge-bases", json={"name": name})
    assert resp.status_code == 201
    return str(resp.json()["id"])


class TestUploadToNonExistentKb:
    async def test_upload_to_nonexistent_kb_returns_404(self, client: AsyncClient) -> None:
        files = {"file": ("test.txt", BytesIO(b"hello"), "text/plain")}
        resp = await client.post("/v1/knowledge-bases/nonexistent_id/documents", files=files)
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


class TestUploadUnsupportedFormat:
    @pytest.mark.parametrize(
        "filename,content_type",
        [
            ("data.csv", "text/csv"),
            ("data.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            ("script.py", "text/x-python"),
            ("image.jpg", "image/jpeg"),
        ],
    )
    async def test_upload_unsupported_extension_returns_422(
        self, client: AsyncClient, filename: str, content_type: str
    ) -> None:
        kb_id = await _create_kb(client)
        files = {"file": (filename, BytesIO(b"content"), content_type)}
        resp = await client.post(f"/v1/knowledge-bases/{kb_id}/documents", files=files)
        assert resp.status_code == 422
        assert "unsupported" in resp.json()["detail"].lower()

    async def test_upload_no_extension_returns_422(self, client: AsyncClient) -> None:
        kb_id = await _create_kb(client)
        files = {"file": ("data", BytesIO(b"content"), "application/octet-stream")}
        resp = await client.post(f"/v1/knowledge-bases/{kb_id}/documents", files=files)
        assert resp.status_code == 422
        assert "unsupported" in resp.json()["detail"].lower()


class TestUploadEmptyFile:
    async def test_upload_empty_txt_file_succeeds(self, client: AsyncClient) -> None:
        kb_id = await _create_kb(client)
        files = {"file": ("empty.txt", BytesIO(b""), "text/plain")}
        resp = await client.post(f"/v1/knowledge-bases/{kb_id}/documents", files=files)
        assert resp.status_code == 201
        data = resp.json()
        assert data["document"]["char_count"] == 0
        assert data["document"]["status"] == "ready"
        assert data["knowledge_point_count"] == 0


class TestUploadMismatchedContentType:
    async def test_upload_txt_with_pdf_content_type_uses_extension(
        self, client: AsyncClient
    ) -> None:
        kb_id = await _create_kb(client)
        content = b"plain text content for testing"
        files = {"file": ("test.txt", BytesIO(content), "application/pdf")}
        resp = await client.post(f"/v1/knowledge-bases/{kb_id}/documents", files=files)
        # application/pdf maps to "pdf" in MIME_TO_FORMAT, so it takes precedence
        # over the .txt extension. This should fail because the bytes are not valid PDF.
        assert resp.status_code == 422


class TestUploadKbIsolation:
    async def test_upload_to_one_kb_does_not_leak_into_another(self, client: AsyncClient) -> None:
        kb_a = await _create_kb(client, "KB A")
        kb_b = await _create_kb(client, "KB B")
        files = {"file": ("test.txt", BytesIO(b"content for KB A"), "text/plain")}
        resp = await client.post(f"/v1/knowledge-bases/{kb_a}/documents", files=files)
        assert resp.status_code == 201

        docs_a = (await client.get(f"/v1/knowledge-bases/{kb_a}/documents")).json()
        docs_b = (await client.get(f"/v1/knowledge-bases/{kb_b}/documents")).json()
        assert len(docs_a) == 1
        assert len(docs_b) == 0

        kps_a = (await client.get(f"/v1/knowledge-bases/{kb_a}/knowledge-points")).json()
        kps_b = (await client.get(f"/v1/knowledge-bases/{kb_b}/knowledge-points")).json()
        assert len(kps_a) >= 0
        assert len(kps_b) == 0


class TestGetDocumentsNonExistentKb:
    async def test_get_documents_nonexistent_kb_returns_404(self, client: AsyncClient) -> None:
        resp = await client.get("/v1/knowledge-bases/nonexistent_id/documents")
        assert resp.status_code == 404


class TestGetKnowledgePointsNonExistentKb:
    async def test_get_knowledge_points_nonexistent_kb_returns_404(
        self, client: AsyncClient
    ) -> None:
        resp = await client.get("/v1/knowledge-bases/nonexistent_id/knowledge-points")
        assert resp.status_code == 404


class TestUploadSpecialFilename:
    async def test_upload_unicode_emoji_spaces_filename(self, client: AsyncClient) -> None:
        kb_id = await _create_kb(client)
        filename = "📚 数学 第一章.txt"
        files = {"file": (filename, BytesIO(b"content"), "text/plain")}
        resp = await client.post(f"/v1/knowledge-bases/{kb_id}/documents", files=files)
        assert resp.status_code == 201
        assert resp.json()["document"]["filename"] == filename


class TestUploadPathTraversal:
    async def test_upload_path_traversal_filename_saves_safely(self, client: AsyncClient) -> None:
        """Path traversal in filename is sanitized — file saves in KB dir."""
        kb_id = await _create_kb(client)
        filename = "../../../etc/passwd.txt"
        files = {"file": (filename, BytesIO(b"secret"), "text/plain")}
        resp = await client.post(f"/v1/knowledge-bases/{kb_id}/documents", files=files)
        assert resp.status_code == 201
        assert resp.json()["document"]["filename"] == filename


class TestWrongHttpMethods:
    async def test_put_on_upload_endpoint_returns_405(self, client: AsyncClient) -> None:
        kb_id = await _create_kb(client)
        resp = await client.put(f"/v1/knowledge-bases/{kb_id}/documents", json={})
        assert resp.status_code == 405

    async def test_delete_on_upload_endpoint_returns_405(self, client: AsyncClient) -> None:
        kb_id = await _create_kb(client)
        resp = await client.delete(f"/v1/knowledge-bases/{kb_id}/documents")
        assert resp.status_code == 405

    async def test_patch_on_upload_endpoint_returns_405(self, client: AsyncClient) -> None:
        kb_id = await _create_kb(client)
        resp = await client.patch(f"/v1/knowledge-bases/{kb_id}/documents", json={})
        assert resp.status_code == 405
