"""Tests for POST /questions/generate/from-file endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from question_agent.main import app

BASE = "http://test"

SAMPLE_TEXT = (
    "第一章 力学\n牛顿第二定律描述了力等于质量乘以加速度。\n"
    "加速度是速度变化量与时间的比值。\n"
    "第二章 电磁学\n欧姆定律表明电流等于电压除以电阻。"
)


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        yield c


class TestQuestionsGenerateFromFile:
    @pytest.mark.asyncio
    async def test_from_file_returns_full_response(self, client: AsyncClient) -> None:
        resp = await client.post(
            f"{BASE}/questions/generate/from-file",
            files={"file": ("sample.txt", SAMPLE_TEXT.encode(), "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "format" in data
        assert "chapters" in data
        assert "knowledge_points" in data
        assert "questions" in data
        assert "generation_stats" in data

    @pytest.mark.asyncio
    async def test_from_file_format_detected(self, client: AsyncClient) -> None:
        resp = await client.post(
            f"{BASE}/questions/generate/from-file",
            files={"file": ("sample.txt", SAMPLE_TEXT.encode(), "text/plain")},
        )
        data = resp.json()
        assert data["format"] == "text"

    @pytest.mark.asyncio
    async def test_from_file_questions_structure(self, client: AsyncClient) -> None:
        resp = await client.post(
            f"{BASE}/questions/generate/from-file",
            files={"file": ("sample.txt", SAMPLE_TEXT.encode(), "text/plain")},
        )
        data = resp.json()
        for q in data["questions"]:
            assert "id" in q
            assert "stem_text" in q
            assert "options" in q
            assert len(q["options"]) == 4
            assert "knowledge_point_name" in q
            assert "question_type" in q
            assert "status" in q

    @pytest.mark.asyncio
    async def test_from_file_generation_stats(self, client: AsyncClient) -> None:
        resp = await client.post(
            f"{BASE}/questions/generate/from-file",
            files={"file": ("sample.txt", SAMPLE_TEXT.encode(), "text/plain")},
        )
        data = resp.json()
        stats = data["generation_stats"]
        assert stats["total"] == len(data["questions"])
        assert stats["successful"] + stats["failed"] == stats["total"]

    @pytest.mark.asyncio
    async def test_from_file_empty_text(self, client: AsyncClient) -> None:
        resp = await client.post(
            f"{BASE}/questions/generate/from-file",
            files={"file": ("empty.txt", b"", "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["questions"] == []
        assert data["generation_stats"]["total"] == 0

    @pytest.mark.asyncio
    async def test_from_file_unsupported_format(self, client: AsyncClient) -> None:
        resp = await client.post(
            f"{BASE}/questions/generate/from-file",
            files={"file": ("test.jpg", b"\xff\xd8\xff\xe0", "image/jpeg")},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_from_file_knowledge_points_present(self, client: AsyncClient) -> None:
        resp = await client.post(
            f"{BASE}/questions/generate/from-file",
            files={"file": ("sample.txt", SAMPLE_TEXT.encode(), "text/plain")},
        )
        data = resp.json()
        assert isinstance(data["knowledge_points"], list)

    @pytest.mark.asyncio
    async def test_from_file_no_file_returns_422(self, client: AsyncClient) -> None:
        resp = await client.post(f"{BASE}/questions/generate/from-file")
        assert resp.status_code == 422


class TestFromFileExistingEndpointsUnchanged:
    @pytest.mark.asyncio
    async def test_health_still_works(self, client: AsyncClient) -> None:
        resp = await client.get(f"{BASE}/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_extract_still_works(self, client: AsyncClient) -> None:
        resp = await client.post(
            f"{BASE}/extract",
            files={"file": ("test.txt", b"Hello", "text/plain")},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_knowledge_still_works(self, client: AsyncClient) -> None:
        resp = await client.post(
            f"{BASE}/knowledge",
            files={"file": ("test.txt", b"Hello world", "text/plain")},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_questions_generate_still_works(self, client: AsyncClient) -> None:
        resp = await client.post(
            f"{BASE}/questions/generate",
            json={
                "knowledge_points": [
                    {
                        "name": "牛顿第二定律",
                        "description": "力等于质量乘以加速度",
                        "tags": [{"value": "牛顿第二定律", "category": "formula"}],
                    }
                ]
            },
        )
        assert resp.status_code == 200
