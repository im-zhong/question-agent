"""Tests for POST /questions/generate endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from question_agent.main import app

BASE = "http://test"


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        yield c


def _sample_knowledge_points() -> dict:
    return {
        "knowledge_points": [
            {
                "name": "牛顿第二定律",
                "description": "力等于质量乘以加速度",
                "tags": [{"value": "牛顿第二定律", "category": "formula"}],
            },
            {
                "name": "加速度的定义",
                "description": "速度变化量与时间的比值",
                "tags": [{"value": "加速度", "category": "concept"}],
            },
        ]
    }


class TestQuestionsGenerate:
    @pytest.mark.asyncio
    async def test_generate_returns_questions(self, client: AsyncClient) -> None:
        resp = await client.post(
            f"{BASE}/questions/generate",
            json=_sample_knowledge_points(),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "questions" in data
        assert len(data["questions"]) == 2

    @pytest.mark.asyncio
    async def test_question_stem_structure(self, client: AsyncClient) -> None:
        resp = await client.post(
            f"{BASE}/questions/generate",
            json=_sample_knowledge_points(),
        )
        data = resp.json()
        q = data["questions"][0]
        assert "id" in q
        assert "stem_text" in q
        assert "options" in q
        assert len(q["options"]) == 4
        assert q["options"][0]["label"] == "A"
        assert q["options"][3]["label"] == "D"
        assert "knowledge_point_name" in q
        assert "question_type" in q
        assert "status" in q
        assert "metadata" in q

    @pytest.mark.asyncio
    async def test_knowledge_point_name_preserved(self, client: AsyncClient) -> None:
        resp = await client.post(
            f"{BASE}/questions/generate",
            json=_sample_knowledge_points(),
        )
        data = resp.json()
        assert data["questions"][0]["knowledge_point_name"] == "牛顿第二定律"
        assert data["questions"][1]["knowledge_point_name"] == "加速度的定义"

    @pytest.mark.asyncio
    async def test_category_maps_to_question_type(self, client: AsyncClient) -> None:
        resp = await client.post(
            f"{BASE}/questions/generate",
            json=_sample_knowledge_points(),
        )
        data = resp.json()
        assert data["questions"][0]["question_type"] == "calculation"
        assert data["questions"][1]["question_type"] == "definition"

    @pytest.mark.asyncio
    async def test_empty_knowledge_points(self, client: AsyncClient) -> None:
        resp = await client.post(
            f"{BASE}/questions/generate",
            json={"knowledge_points": []},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["questions"] == []

    @pytest.mark.asyncio
    async def test_no_tags_uses_default_type(self, client: AsyncClient) -> None:
        resp = await client.post(
            f"{BASE}/questions/generate",
            json={"knowledge_points": [{"name": "某知识点", "description": "无标签", "tags": []}]},
        )
        data = resp.json()
        assert data["questions"][0]["question_type"] == "definition"

    @pytest.mark.asyncio
    async def test_stem_text_is_relevant_to_knowledge_point(self, client: AsyncClient) -> None:
        resp = await client.post(
            f"{BASE}/questions/generate",
            json=_sample_knowledge_points(),
        )
        data = resp.json()
        for q in data["questions"]:
            assert len(q["stem_text"]) > 0

    @pytest.mark.asyncio
    async def test_generation_stats_present(self, client: AsyncClient) -> None:
        resp = await client.post(
            f"{BASE}/questions/generate",
            json=_sample_knowledge_points(),
        )
        data = resp.json()
        assert "generation_stats" in data
        stats = data["generation_stats"]
        assert stats["total"] == 2
        assert stats["successful"] + stats["failed"] == 2

    @pytest.mark.asyncio
    async def test_batch_three_plus_knowledge_points(self, client: AsyncClient) -> None:
        kps = {
            "knowledge_points": [
                {"name": f"知识点{i}", "description": f"描述{i}", "tags": []} for i in range(5)
            ]
        }
        resp = await client.post(f"{BASE}/questions/generate", json=kps)
        data = resp.json()
        assert len(data["questions"]) == 5
        assert data["generation_stats"]["total"] == 5

    @pytest.mark.asyncio
    async def test_status_field_present(self, client: AsyncClient) -> None:
        resp = await client.post(
            f"{BASE}/questions/generate",
            json=_sample_knowledge_points(),
        )
        data = resp.json()
        for q in data["questions"]:
            assert q["status"] in ("success", "failed")

    @pytest.mark.asyncio
    async def test_empty_batch_stats(self, client: AsyncClient) -> None:
        resp = await client.post(
            f"{BASE}/questions/generate",
            json={"knowledge_points": []},
        )
        data = resp.json()
        assert data["generation_stats"]["total"] == 0
        assert data["generation_stats"]["successful"] == 0
        assert data["generation_stats"]["failed"] == 0


class TestExistingEndpointsUnchanged:
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
    async def test_structure_still_works(self, client: AsyncClient) -> None:
        resp = await client.post(
            f"{BASE}/structure",
            files={"file": ("test.txt", b"Hello world", "text/plain")},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_knowledge_still_works(self, client: AsyncClient) -> None:
        resp = await client.post(
            f"{BASE}/knowledge",
            files={"file": ("test.txt", b"Hello world", "text/plain")},
        )
        assert resp.status_code == 200
