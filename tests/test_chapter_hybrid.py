"""Tests for hybrid chapter detection engine."""

from question_agent.chapters import ChapterHeading, detect_chapters_hybrid


def test_rule_high_confidence_kept():
    """High-confidence (>=0.8) rule headings are kept."""
    paragraphs = [
        {"text": "第一章 引言"},
        {"text": "正文内容"},
        {"text": "1.1 背景"},
    ]
    result = detect_chapters_hybrid(paragraphs)
    assert result["detection_method"] in ("hybrid", "rule_only")
    assert len(result["headings"]) >= 2
    rule_headings = [h for h in result["headings"] if h.method != "llm"]
    assert len(rule_headings) >= 2


def test_llm_fills_low_confidence_gaps():
    """Low-confidence font detections are replaced by LLM results when available."""
    paragraphs = [
        {"text": "Module 1: Intro", "font_size": 16.0, "is_bold": True},
        {"text": "Some body text"},
        {"text": "Module 2: Methods", "font_size": 16.0, "is_bold": True},
        {"text": "More body text"},
    ]
    result = detect_chapters_hybrid(paragraphs)
    assert len(result["headings"]) >= 2


def test_llm_unavailable_degrade_to_rule_only(monkeypatch):
    """When LLM is unavailable, return pure rule results with rule_only method."""

    def mock_return_none(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "question_agent.chapters.hybrid.detect_chapters_llm",
        mock_return_none,
    )
    paragraphs = [
        {"text": "第一章 标题"},
        {"text": "内容"},
    ]
    result = detect_chapters_hybrid(paragraphs)
    assert result["detection_method"] == "rule_only"
    assert result["llm_count"] == 0
    assert len(result["headings"]) == 1


def test_empty_paragraphs():
    """Empty paragraphs return empty lists, no errors."""
    result = detect_chapters_hybrid([])
    assert result["headings"] == []
    assert result["rule_count"] == 0


def test_no_rule_matches_llm_can_still_detect():
    """Even when rule detector finds nothing, LLM can detect non-standard headings.
    This is the purpose of the hybrid engine — rules cover 80%, LLM fills gaps."""
    paragraphs = [
        {"text": "Chapter 1: Introduction"},
        {"text": "Some body content."},
    ]
    result = detect_chapters_hybrid(paragraphs)
    # LLM should detect this as a heading even though rules don't match
    assert result["detection_method"] == "hybrid"
    assert result["llm_count"] >= 1


def test_sorted_by_line_index():
    """Headings are sorted by line_index."""
    paragraphs = [
        {"text": "First paragraph"},
        {"text": "第二章 标题"},
        {"text": "Middle paragraph"},
        {"text": "第一章 标题"},
    ]
    result = detect_chapters_hybrid(paragraphs)
    indices = [h.line_index for h in result["headings"]]
    assert indices == sorted(indices)


def test_hybrid_does_not_crash_with_llm_live():
    """Integration test: hybrid engine runs with real LLM, returns headings."""
    paragraphs = [
        {"text": "Module 1: Overview"},
        {"text": "Introduction text here."},
        {"text": "1.1 Background"},
        {"text": "More details here."},
        {"text": "Module 2: Methods"},
    ]
    result = detect_chapters_hybrid(paragraphs)
    assert result["detection_method"] == "hybrid"
    assert len(result["headings"]) >= 3  # Module 1 (llm), 1.1 (pattern), Module 2 (llm)
    assert result["rule_count"] >= 1
    assert result["llm_count"] >= 1


def test_detection_stats():
    """Result includes rule_count and llm_count."""
    paragraphs = [
        {"text": "第一章 开始"},
        {"text": "正文"},
    ]
    result = detect_chapters_hybrid(paragraphs)
    assert "rule_count" in result
    assert "llm_count" in result
    assert "detection_method" in result
    assert isinstance(result["headings"][0], ChapterHeading)
