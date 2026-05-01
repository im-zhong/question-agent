"""Tests for GLM-5 knowledge point extraction."""

import json
from typing import Any

import pytest

from question_agent.knowledge.llm import (
    _build_user_prompt,
    _parse_response,
    extract_knowledge_points_llm,
)
from question_agent.knowledge.models import ChapterWindow

_MOCK_PHYSICS_RESPONSE = {
    "knowledge_points": [
        {
            "name": "牛顿第二定律",
            "description": "F=ma，描述了力、质量和加速度之间的关系",
            "tags": [
                {"value": "牛顿定律", "category": "concept"},
                {"value": "F=ma", "category": "formula"},
            ],
            "source_line_start": 0,
            "source_line_end": 1,
        },
        {
            "name": "加速度的定义",
            "description": "速度变化量与发生这一变化所用时间的比值",
            "tags": [{"value": "加速度", "category": "concept"}],
            "source_line_start": 1,
            "source_line_end": 2,
        },
    ]
}


def _make_window(
    text: str = "牛顿第二定律 F=ma。加速度的定义：速度变化量与时间的比值。",
    line_start: int = 0,
    line_end: int = 5,
) -> ChapterWindow:
    return ChapterWindow(
        chapter_id="ch_0",
        chapter_title="力学基础",
        text=text,
        line_start=line_start,
        line_end=line_end,
    )


def _make_mock_client(response_data: dict[str, Any] | None = None) -> Any:
    """Create a mock ZhipuAiClient for testing."""

    class MockMessage:
        def __init__(self, content: str) -> None:
            self.content = content

    class MockChoice:
        def __init__(self, content: str) -> None:
            self.message = MockMessage(content)

    class MockResponse:
        def __init__(self, content: str) -> None:
            self.choices = [MockChoice(content)]

    class MockCompletions:
        @staticmethod
        def create(**kwargs: object) -> MockResponse:
            if response_data is not None:
                content = json.dumps(response_data)
            else:
                content = "invalid"
            return MockResponse(content)

    class MockChat:
        completions = MockCompletions()  # type: ignore[assignment]

    class MockClient:
        chat = MockChat()  # type: ignore[assignment]

    return MockClient()


class TestBuildUserPrompt:
    def test_includes_chapter_title(self) -> None:
        window = _make_window()
        prompt = _build_user_prompt(window)
        assert "力学基础" in prompt

    def test_includes_line_range(self) -> None:
        window = _make_window(line_start=3, line_end=8)
        prompt = _build_user_prompt(window)
        assert "3-8" in prompt

    def test_includes_text(self) -> None:
        window = _make_window(text="Test content here")
        prompt = _build_user_prompt(window)
        assert "Test content here" in prompt


class TestParseResponse:
    def test_valid_json(self) -> None:
        raw = json.dumps(
            {
                "knowledge_points": [
                    {
                        "name": "牛顿第二定律",
                        "description": "F=ma",
                        "tags": [{"value": "牛顿", "category": "concept"}],
                        "source_line_start": 0,
                        "source_line_end": 2,
                    }
                ]
            }
        )
        window = _make_window()
        result = _parse_response(raw, window)
        assert result is not None
        assert len(result) == 1
        assert result[0].name == "牛顿第二定律"
        assert result[0].method == "llm"
        assert result[0].confidence == 0.85
        assert result[0].id == 0

    def test_start_id_offset(self) -> None:
        raw = json.dumps(
            {
                "knowledge_points": [
                    {
                        "name": "test",
                        "description": "test desc",
                        "tags": [{"value": "t", "category": "fact"}],
                        "source_line_start": 0,
                        "source_line_end": 1,
                    }
                ]
            }
        )
        window = _make_window()
        result = _parse_response(raw, window, start_id=5)
        assert result is not None
        assert result[0].id == 5

    def test_markdown_fenced_json(self) -> None:
        inner = json.dumps(
            {
                "knowledge_points": [
                    {
                        "name": "test",
                        "description": "d",
                        "tags": [{"value": "t", "category": "fact"}],
                        "source_line_start": 0,
                        "source_line_end": 1,
                    }
                ]
            }
        )
        raw = f"```json\n{inner}\n```"
        window = _make_window()
        result = _parse_response(raw, window)
        assert result is not None
        assert len(result) == 1

    def test_invalid_json_returns_none(self) -> None:
        window = _make_window()
        result = _parse_response("not json at all", window)
        assert result is None

    def test_empty_string_returns_none(self) -> None:
        window = _make_window()
        result = _parse_response("", window)
        assert result is None

    def test_missing_knowledge_points_key_returns_none(self) -> None:
        raw = json.dumps({"wrong_key": []})
        window = _make_window()
        result = _parse_response(raw, window)
        assert result is None


class TestExtractKnowledgePointsLlm:
    def test_empty_window_returns_none(self) -> None:
        window = _make_window(text="   ")
        result = extract_knowledge_points_llm(window)
        assert result is None

    def test_no_api_key_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("question_agent.chapters.llm.settings.glm_api_key", "")
        window = _make_window()
        result = extract_knowledge_points_llm(window)
        assert result is None

    def test_mock_llm_returns_knowledge_points(self) -> None:
        client = _make_mock_client(response_data=_MOCK_PHYSICS_RESPONSE)
        window = _make_window()
        result = extract_knowledge_points_llm(window, client=client)
        assert result is not None
        assert len(result) >= 2
        categories = {tag.category for kp in result for tag in kp.tags}
        assert "concept" in categories or "formula" in categories

    def test_mock_llm_invalid_json_returns_none(self) -> None:
        client = _make_mock_client(response_data=None)  # returns "invalid"
        window = _make_window()
        result = extract_knowledge_points_llm(window, client=client)
        assert result is None


class TestLiveApi:
    def test_returns_knowledge_points_from_physics_text(self) -> None:
        """Live GLM-5 API call — skipped if no API key."""
        from question_agent.chapters.llm import _create_client

        client = _create_client()
        if client is None:
            pytest.skip("GLM_API_KEY not configured")

        window = ChapterWindow(
            chapter_id="ch_0",
            chapter_title="牛顿力学",
            text=(
                "牛顿第二定律 F=ma，描述了力、质量和加速度之间的关系。\n"
                "加速度的定义：速度变化量与发生这一变化所用时间的比值。\n"
                "匀变速直线运动公式：v = v₀ + at"
            ),
            line_start=0,
            line_end=3,
        )
        result = extract_knowledge_points_llm(window, client=client)
        if result is None:
            pytest.skip("GLM-5 returned no result (timeout or error)")
        assert len(result) >= 2
        categories = {tag.category for kp in result for tag in kp.tags}
        assert "concept" in categories or "formula" in categories
