"""Edge case tests for POST /questions/generate/from-file endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from question_agent.main import app

BASE = "http://test"


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        yield c


class TestFromFileHttpMethods:
    @pytest.mark.asyncio
    async def test_get_returns_405(self, client: AsyncClient) -> None:
        resp = await client.get(f"{BASE}/questions/generate/from-file")
        assert resp.status_code == 405

    @pytest.mark.asyncio
    async def test_put_returns_405(self, client: AsyncClient) -> None:
        resp = await client.put(f"{BASE}/questions/generate/from-file")
        assert resp.status_code == 405

    @pytest.mark.asyncio
    async def test_delete_returns_405(self, client: AsyncClient) -> None:
        resp = await client.delete(f"{BASE}/questions/generate/from-file")
        assert resp.status_code == 405


class TestFromFileEdgeCases:
    @pytest.mark.asyncio
    async def test_whitespace_only_text(self, client: AsyncClient) -> None:
        resp = await client.post(
            f"{BASE}/questions/generate/from-file",
            files={"file": ("blank.txt", b"   \n  \n  ", "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["questions"] == []
        assert data["generation_stats"]["total"] == 0

    @pytest.mark.asyncio
    async def test_single_line_no_chapters(self, client: AsyncClient) -> None:
        resp = await client.post(
            f"{BASE}/questions/generate/from-file",
            files={"file": ("single.txt", b"Just one line of text", "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data.get("chapters"), (list, type(None)))

    @pytest.mark.asyncio
    async def test_filename_with_spaces(self, client: AsyncClient) -> None:
        resp = await client.post(
            f"{BASE}/questions/generate/from-file",
            files={"file": ("my file.txt", b"Some content", "text/plain")},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_filename_with_unicode(self, client: AsyncClient) -> None:
        resp = await client.post(
            f"{BASE}/questions/generate/from-file",
            files={"file": ("教材文件.txt", b"Some content", "text/plain")},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_legacy_doc_rejected(self, client: AsyncClient) -> None:
        resp = await client.post(
            f"{BASE}/questions/generate/from-file",
            files={"file": ("legacy.doc", b"\xd0\xcf\x11\xe0", "application/msword")},
        )
        assert resp.status_code == 422
