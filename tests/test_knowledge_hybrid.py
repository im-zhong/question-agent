"""Tests for hybrid knowledge point extraction engine."""

import json
from typing import Any

import pytest

from question_agent.knowledge.hybrid import (
    _dedup_by_range,
    _ranges_overlap,
    extract_knowledge_points_hybrid,
)
from question_agent.knowledge.models import ChapterWindow, KnowledgePoint, KnowledgeTag


def _make_kp(
    kp_id: int = 0,
    name: str = "test",
    method: str = "rule",
    confidence: float = 0.7,
    start: int = 0,
    end: int = 1,
) -> KnowledgePoint:
    return KnowledgePoint(
        id=kp_id,
        name=name,
        description=name,
        tags=[KnowledgeTag(value=name, category="concept")],
        confidence=confidence,
        method=method,
        source_line_start=start,
        source_line_end=end,
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


def _make_window(
    text: str = "加速度是指速度变化量与时间的比值。",
    line_start: int = 0,
    line_end: int = 1,
) -> ChapterWindow:
    return ChapterWindow(
        chapter_id="ch_0",
        chapter_title="Ch1",
        text=text,
        line_start=line_start,
        line_end=line_end,
    )


_LLM_RESPONSE = {
    "knowledge_points": [
        {
            "name": "匀变速直线运动",
            "description": "物体做匀变速直线运动",
            "tags": [{"value": "运动", "category": "concept"}],
            "source_line_start": 2,
            "source_line_end": 4,
        }
    ]
}


class TestRangesOverlap:
    def test_no_overlap(self) -> None:
        assert not _ranges_overlap(0, 2, 3, 5)

    def test_partial_overlap_above_threshold(self) -> None:
        # Range 0-4 and 2-5: overlap=2, smaller=3, 2/3=0.67 > 0.5
        assert _ranges_overlap(0, 4, 2, 5)
        # Range 0-4 and 1-5: overlap=3, smaller=4, 3/4=0.75 > 0.5
        assert _ranges_overlap(0, 4, 1, 5)

    def test_complete_containment(self) -> None:
        assert _ranges_overlap(0, 10, 2, 5)

    def test_same_range(self) -> None:
        assert _ranges_overlap(0, 5, 0, 5)


class TestDedupByRange:
    def test_no_overlap_keeps_all(self) -> None:
        rule = [_make_kp(start=0, end=2)]
        llm = [_make_kp(start=5, end=7, method="llm")]
        result = _dedup_by_range(rule, llm)
        assert len(result) == 2

    def test_overlap_keeps_higher_confidence(self) -> None:
        rule = [_make_kp(start=0, end=5, confidence=0.7)]
        llm = [_make_kp(start=1, end=5, confidence=0.85, method="llm")]
        result = _dedup_by_range(rule, llm)
        assert len(result) == 1
        assert result[0].method == "llm"

    def test_overlap_rule_wins_when_higher(self) -> None:
        rule = [_make_kp(start=0, end=5, confidence=0.95, method="rule")]
        llm = [_make_kp(start=1, end=5, confidence=0.85, method="llm")]
        result = _dedup_by_range(rule, llm)
        assert len(result) == 1
        assert result[0].method == "rule"


class TestExtractKnowledgePointsHybrid:
    def test_both_empty_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("question_agent.chapters.llm.settings.glm_api_key", "")
        paragraphs = [{"text": "普通文本没有标记词"}]
        windows = [_make_window(text="普通文本没有标记词")]
        result = extract_knowledge_points_hybrid(windows, paragraphs)
        assert result["detection_method"] == "none"
        assert result["knowledge_points"] == []
        assert result["rule_count"] == 0
        assert result["llm_count"] == 0

    def test_llm_unavailable_degrades_to_rule_only(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("question_agent.chapters.llm.settings.glm_api_key", "")
        paragraphs = [{"text": "加速度是指速度变化量与时间的比值。"}]
        windows = [_make_window()]
        result = extract_knowledge_points_hybrid(windows, paragraphs)
        assert result["detection_method"] == "rule_only"
        assert result["rule_count"] > 0
        assert result["llm_count"] == 0

    def test_rule_only_when_llm_returns_none(self) -> None:
        client = _make_mock_client(response_data=None)
        paragraphs = [{"text": "加速度是指速度变化量与时间的比值。"}]
        windows = [_make_window()]
        result = extract_knowledge_points_hybrid(windows, paragraphs, llm_client=client)
        assert result["detection_method"] == "rule_only"
        assert result["rule_count"] > 0

    def test_hybrid_merge(self) -> None:
        client = _make_mock_client(response_data=_LLM_RESPONSE)
        paragraphs = [{"text": "加速度是指速度变化量与时间的比值。公式：v = v₀ + at"}]
        windows = [_make_window(text="加速度是指速度变化量与时间的比值。公式：v = v₀ + at")]
        result = extract_knowledge_points_hybrid(windows, paragraphs, llm_client=client)
        assert result["detection_method"] == "hybrid"
        assert result["rule_count"] > 0
        assert result["llm_count"] > 0

    def test_ids_renumbered(self) -> None:
        paragraphs = [{"text": "加速度是指速度变化量与时间的比值。"}]
        windows = [_make_window()]
        result = extract_knowledge_points_hybrid(windows, paragraphs)
        ids = [kp.id for kp in result["knowledge_points"]]
        assert ids == list(range(len(ids)))

    def test_llm_only_when_no_rule_markers(self) -> None:
        client = _make_mock_client(response_data=_LLM_RESPONSE)
        paragraphs = [{"text": "普通文本没有任何标记词"}]
        windows = [_make_window(text="普通文本没有任何标记词")]
        result = extract_knowledge_points_hybrid(windows, paragraphs, llm_client=client)
        assert result["detection_method"] == "llm_only"
        assert result["rule_count"] == 0
        assert result["llm_count"] > 0
