"""Edge case tests for POST /questions/generate endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from question_agent.main import app

BASE = "http://test"


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        yield c


class TestQuestionsGenerateEdgeCases:
    @pytest.mark.asyncio
    async def test_missing_body_returns_422(self, client: AsyncClient) -> None:
        resp = await client.post(f"{BASE}/questions/generate")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_body_returns_422(self, client: AsyncClient) -> None:
        resp = await client.post(f"{BASE}/questions/generate", json={})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_knowledge_points_not_array_returns_422(self, client: AsyncClient) -> None:
        resp = await client.post(
            f"{BASE}/questions/generate", json={"knowledge_points": "not_array"}
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_required_name_field_returns_422(self, client: AsyncClient) -> None:
        resp = await client.post(
            f"{BASE}/questions/generate",
            json={"knowledge_points": [{"description": "no name", "tags": []}]},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_unicode_emoji_in_name(self, client: AsyncClient) -> None:
        resp = await client.post(
            f"{BASE}/questions/generate",
            json={
                "knowledge_points": [
                    {"name": "量子力学⚛️", "description": "描述微观粒子", "tags": []}
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["questions"][0]["knowledge_point_name"] == "量子力学⚛️"

    @pytest.mark.asyncio
    async def test_very_long_name(self, client: AsyncClient) -> None:
        long_name = "知识点" * 500  # ~1500 chars
        resp = await client.post(
            f"{BASE}/questions/generate",
            json={
                "knowledge_points": [
                    {"name": long_name, "description": "long name test", "tags": []}
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["questions"][0]["knowledge_point_name"] == long_name

    @pytest.mark.asyncio
    async def test_html_in_name_not_injected(self, client: AsyncClient) -> None:
        html_name = "<script>alert('xss')</script>"
        resp = await client.post(
            f"{BASE}/questions/generate",
            json={
                "knowledge_points": [
                    {"name": html_name, "description": "xss test", "tags": []}
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        # JSON response preserves the string literally, no HTML rendering
        assert data["questions"][0]["knowledge_point_name"] == html_name

    @pytest.mark.asyncio
    async def test_many_knowledge_points(self, client: AsyncClient) -> None:
        many = [
            {"name": f"知识点{i}", "description": f"描述{i}", "tags": []}
            for i in range(50)
        ]
        resp = await client.post(
            f"{BASE}/questions/generate",
            json={"knowledge_points": many},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["questions"]) == 50

    @pytest.mark.asyncio
    async def test_all_category_types(self, client: AsyncClient) -> None:
        categories = ["concept", "formula", "procedure", "fact", "principle"]
        kps = [
            {"name": f"kp_{c}", "description": f"desc_{c}", "tags": [{"value": c, "category": c}]}
            for c in categories
        ]
        resp = await client.post(
            f"{BASE}/questions/generate",
            json={"knowledge_points": kps},
        )
        assert resp.status_code == 200
        data = resp.json()
        types = [q["question_type"] for q in data["questions"]]
        assert "definition" in types
        assert "calculation" in types
        assert "procedure" in types
        assert "recall" in types
        assert "analysis" in types

    @pytest.mark.asyncio
    async def test_invalid_category_uses_default(self, client: AsyncClient) -> None:
        resp = await client.post(
            f"{BASE}/questions/generate",
            json={
                "knowledge_points": [
                    {
                        "name": "test",
                        "description": "desc",
                        "tags": [{"value": "x", "category": "invalid_category"}],
                    }
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        # Invalid category falls back to "definition" via _category_to_question_type
        assert data["questions"][0]["question_type"] == "definition"

    @pytest.mark.asyncio
    async def test_tags_with_multiple_entries(self, client: AsyncClient) -> None:
        resp = await client.post(
            f"{BASE}/questions/generate",
            json={
                "knowledge_points": [
                    {
                        "name": "牛顿定律",
                        "description": "力与运动",
                        "tags": [
                            {"value": "牛顿定律", "category": "formula"},
                            {"value": "牛顿定律", "category": "principle"},
                        ],
                    }
                ]
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        # First tag determines question type
        assert data["questions"][0]["question_type"] == "calculation"


class TestQuestionsGenerateHttpMethods:
    @pytest.mark.asyncio
    async def test_get_returns_405(self, client: AsyncClient) -> None:
        resp = await client.get(f"{BASE}/questions/generate")
        assert resp.status_code == 405

    @pytest.mark.asyncio
    async def test_put_returns_405(self, client: AsyncClient) -> None:
        resp = await client.put(f"{BASE}/questions/generate", json={"knowledge_points": []})
        assert resp.status_code == 405

    @pytest.mark.asyncio
    async def test_delete_returns_405(self, client: AsyncClient) -> None:
        resp = await client.delete(f"{BASE}/questions/generate")
        assert resp.status_code == 405
