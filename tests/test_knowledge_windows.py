"""Tests for knowledge point models and chapter window builder."""

from typing import Literal

import pytest

from question_agent.chapters.tree import ChapterNode
from question_agent.knowledge.models import ChapterWindow, KnowledgePoint, KnowledgeTag
from question_agent.knowledge.windows import build_chapter_windows

_TagCategory = Literal["concept", "formula", "procedure", "fact", "principle"]
VALID_CATEGORIES: list[_TagCategory] = ["concept", "formula", "procedure", "fact", "principle"]


def _make_node(
    node_id: str = "ch_0",
    title: str = "Chapter 1",
    start_line: int = 0,
    end_line: int = 3,
) -> ChapterNode:
    """Create a ChapterNode for testing without requiring a ChapterHeading."""
    node = ChapterNode.__new__(ChapterNode)
    node.id = node_id
    node.level = 1
    node.title = title
    node.start_line = start_line
    node.end_line = end_line
    node.page_range = None
    node.children = []
    node._heading = None  # type: ignore[assignment]
    return node


class TestKnowledgeTag:
    def test_valid_categories(self) -> None:
        for cat in VALID_CATEGORIES:
            tag = KnowledgeTag(value="test", category=cat)
            assert tag.category == cat

    def test_invalid_category_raises(self) -> None:
        with pytest.raises(Exception):
            KnowledgeTag(value="test", category="invalid")  # type: ignore[arg-type]


class TestKnowledgePoint:
    def test_instantiation(self) -> None:
        kp = KnowledgePoint(
            id=1,
            name="Newton's Second Law",
            description="F = ma",
            tags=[KnowledgeTag(value="Newton", category="concept")],
            confidence=0.85,
            method="llm",
            source_line_start=0,
            source_line_end=5,
        )
        assert kp.id == 1
        assert kp.name == "Newton's Second Law"
        assert len(kp.tags) == 1
        assert kp.tags[0].category == "concept"

    def test_confidence_out_of_range_raises(self) -> None:
        with pytest.raises(Exception):
            KnowledgePoint(
                id=1,
                name="test",
                description="test",
                tags=[],
                confidence=1.5,
                method="llm",
                source_line_start=0,
                source_line_end=1,
            )

    def test_negative_confidence_raises(self) -> None:
        with pytest.raises(Exception):
            KnowledgePoint(
                id=1,
                name="test",
                description="test",
                tags=[],
                confidence=-0.1,
                method="llm",
                source_line_start=0,
                source_line_end=1,
            )

    def test_reversed_line_range_raises(self) -> None:
        with pytest.raises(Exception):
            KnowledgePoint(
                id=1,
                name="test",
                description="test",
                tags=[],
                confidence=0.5,
                method="rule",
                source_line_start=5,
                source_line_end=2,
            )


class TestChapterWindow:
    def test_instantiation(self) -> None:
        w = ChapterWindow(
            chapter_id="ch_0",
            chapter_title="Chapter 1",
            text="Some text",
            line_start=0,
            line_end=3,
        )
        assert w.chapter_id == "ch_0"
        assert w.text == "Some text"


class TestBuildChapterWindows:
    def test_single_chapter_fits_one_window(self) -> None:
        node = _make_node(start_line=0, end_line=3)
        paragraphs = [
            {"text": "Paragraph one."},
            {"text": "Paragraph two."},
            {"text": "Paragraph three."},
        ]
        windows = build_chapter_windows([node], paragraphs)
        assert len(windows) == 1
        assert windows[0].chapter_title == "Chapter 1"
        assert "Paragraph one." in windows[0].text
        assert "Paragraph three." in windows[0].text

    def test_multiple_chapters_each_fits(self) -> None:
        node1 = _make_node(node_id="ch_0", title="Ch1", start_line=0, end_line=2)
        node2 = _make_node(node_id="ch_2", title="Ch2", start_line=2, end_line=4)
        paragraphs = [
            {"text": "A1"},
            {"text": "A2"},
            {"text": "B1"},
            {"text": "B2"},
        ]
        windows = build_chapter_windows([node1, node2], paragraphs)
        assert len(windows) == 2
        assert windows[0].chapter_title == "Ch1"
        assert windows[1].chapter_title == "Ch2"
        assert "A1" in windows[0].text
        assert "B1" in windows[1].text

    def test_large_chapter_split_into_multiple_windows(self) -> None:
        node = _make_node(start_line=0, end_line=6)
        paragraphs = [
            {"text": "A" * 1500},
            {"text": "B" * 1500},
            {"text": "C" * 1500},
            {"text": "D" * 100},
            {"text": "E" * 100},
            {"text": "F" * 100},
        ]
        windows = build_chapter_windows([node], paragraphs, max_chars=3000)
        assert len(windows) >= 2
        # All text should be covered across windows
        combined = "\n".join(w.text for w in windows)
        assert "A" * 10 in combined
        assert "D" * 10 in combined

    def test_split_windows_have_correct_line_ranges(self) -> None:
        node = _make_node(start_line=0, end_line=5)
        paragraphs = [
            {"text": "A" * 1200},
            {"text": "B" * 1200},
            {"text": "C" * 1200},
            {"text": "D" * 100},
            {"text": "E" * 100},
        ]
        windows = build_chapter_windows([node], paragraphs, max_chars=3000)
        # A(1200) + B(1200) + 1 newline = 2401 <= 3000
        # A+B + C(1200) + 2 newlines = 3602 > 3000 -> flush A+B first
        assert windows[0].line_start == 0
        assert windows[0].line_end == 2
        # Second window starts at paragraph 2 (C)
        assert windows[1].line_start == 2

    def test_single_paragraph_exceeds_max_chars(self) -> None:
        node = _make_node(start_line=0, end_line=1)
        paragraphs = [{"text": "X" * 5000}]
        windows = build_chapter_windows([node], paragraphs, max_chars=3000)
        assert len(windows) == 1
        assert len(windows[0].text) == 5000

    def test_empty_chapter_skipped(self) -> None:
        node = _make_node(start_line=0, end_line=2)
        paragraphs = [{"text": ""}, {"text": ""}]
        windows = build_chapter_windows([node], paragraphs)
        assert len(windows) == 0

    def test_empty_chapter_nodes_returns_empty(self) -> None:
        paragraphs = [{"text": "Hello"}]
        windows = build_chapter_windows([], paragraphs)
        assert windows == []

    def test_empty_paragraphs_returns_empty(self) -> None:
        node = _make_node(start_line=0, end_line=1)
        windows = build_chapter_windows([node], [])
        assert windows == []

    def test_both_empty_returns_empty(self) -> None:
        windows = build_chapter_windows([], [])
        assert windows == []

    def test_mixed_empty_and_nonempty_chapters(self) -> None:
        empty_node = _make_node(node_id="ch_0", title="Empty", start_line=0, end_line=2)
        filled_node = _make_node(node_id="ch_2", title="Filled", start_line=2, end_line=4)
        paragraphs = [
            {"text": ""},
            {"text": ""},
            {"text": "Content"},
            {"text": "More content"},
        ]
        windows = build_chapter_windows([empty_node, filled_node], paragraphs)
        assert len(windows) == 1
        assert windows[0].chapter_title == "Filled"

    def test_none_text_treated_as_empty(self) -> None:
        node = _make_node(start_line=0, end_line=2)
        paragraphs = [{"text": None}, {"text": "Content"}]  # type: ignore[dict-item]
        windows = build_chapter_windows([node], paragraphs)
        assert len(windows) == 1
        assert "Content" in windows[0].text

    def test_split_with_interleaved_empty_paragraphs(self) -> None:
        node = _make_node(start_line=0, end_line=6)
        paragraphs = [
            {"text": ""},
            {"text": "A" * 1500},
            {"text": ""},
            {"text": "B" * 1500},
            {"text": "C" * 100},
            {"text": ""},
        ]
        windows = build_chapter_windows([node], paragraphs, max_chars=3000)
        assert len(windows) >= 2
        for w in windows:
            assert w.line_start >= 0
            assert w.line_end > w.line_start

    def test_missing_text_key_treated_as_empty(self) -> None:
        node = _make_node(start_line=0, end_line=2)
        paragraphs = [{}, {"text": "Content"}]
        windows = build_chapter_windows([node], paragraphs)
        assert len(windows) == 1
        assert "Content" in windows[0].text

    def test_cjk_content_preserved(self) -> None:
        node = _make_node(start_line=0, end_line=3)
        paragraphs = [
            {"text": "牛顿第二定律"},
            {"text": "加速度的定义"},
            {"text": "匀变速直线运动公式"},
        ]
        windows = build_chapter_windows([node], paragraphs)
        assert len(windows) == 1
        assert "牛顿第二定律" in windows[0].text
        assert "匀变速直线运动公式" in windows[0].text

    def test_very_small_max_chars(self) -> None:
        node = _make_node(start_line=0, end_line=3)
        paragraphs = [
            {"text": "A"},
            {"text": "B"},
            {"text": "C"},
        ]
        windows = build_chapter_windows([node], paragraphs, max_chars=1)
        # Each paragraph exceeds max_chars=1 but gets its own window
        assert len(windows) == 3

    def test_single_paragraph_chapter(self) -> None:
        node = _make_node(start_line=0, end_line=1)
        paragraphs = [{"text": "Only paragraph"}]
        windows = build_chapter_windows([node], paragraphs)
        assert len(windows) == 1
        assert windows[0].text == "Only paragraph"
        assert windows[0].line_start == 0
        assert windows[0].line_end == 1

    def test_chapter_with_offset_start_line(self) -> None:
        node = _make_node(start_line=5, end_line=8)
        paragraphs = [
            {"text": "p0"},
            {"text": "p1"},
            {"text": "p2"},
            {"text": "p3"},
            {"text": "p4"},
            {"text": "p5"},
            {"text": "p6"},
            {"text": "p7"},
        ]
        windows = build_chapter_windows([node], paragraphs)
        assert len(windows) == 1
        assert windows[0].line_start == 5
        assert windows[0].line_end == 8
        assert "p5" in windows[0].text
        assert "p7" in windows[0].text

    def test_knowledge_point_boundary_line_range(self) -> None:
        kp = KnowledgePoint(
            id=1,
            name="test",
            description="test",
            tags=[],
            confidence=0.5,
            method="rule",
            source_line_start=3,
            source_line_end=3,
        )
        assert kp.source_line_start == kp.source_line_end
