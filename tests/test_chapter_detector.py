"""Tests for rule-based chapter heading detector."""

from question_agent.chapters import ChapterHeading, detect_chapters


def test_pattern_chinese_chapter():
    """'第一章 引言' detected as level=1, method=pattern."""
    paragraphs = [{"text": "第一章 引言"}]
    result = detect_chapters(paragraphs)
    assert len(result) == 1
    assert result[0].level == 1
    assert result[0].title == "第一章 引言"
    assert result[0].method == "pattern"
    assert result[0].confidence == 0.9


def test_pattern_dotted_decimal_level2():
    """'1.1 背景' detected as level=2."""
    paragraphs = [{"text": "1.1 背景"}]
    result = detect_chapters(paragraphs)
    assert len(result) == 1
    assert result[0].level == 2
    assert result[0].title == "1.1 背景"
    assert result[0].method == "pattern"


def test_pattern_dotted_decimal_level3():
    """'1.1.1 细节' detected as level=3."""
    paragraphs = [{"text": "1.1.1 细节"}]
    result = detect_chapters(paragraphs)
    assert len(result) == 1
    assert result[0].level == 3


def test_pattern_chinese_paren():
    """'(一) 概述' detected as level=1."""
    paragraphs = [{"text": "(一) 概述"}]
    result = detect_chapters(paragraphs)
    assert len(result) == 1
    assert result[0].level == 1
    assert result[0].method == "pattern"


def test_pattern_fullwidth_paren():
    """'（三）方法' detected as level=1."""
    paragraphs = [{"text": "（三）方法"}]
    result = detect_chapters(paragraphs)
    assert len(result) == 1
    assert result[0].level == 1


def test_pattern_chinese_dun():
    """'一、引言' detected as level=1."""
    paragraphs = [{"text": "一、引言"}]
    result = detect_chapters(paragraphs)
    assert len(result) == 1
    assert result[0].level == 1


def test_pattern_section_symbol():
    """'§1 概述' detected as level=1, '§2.3 细节' as level=2."""
    paragraphs = [{"text": "§1 概述"}, {"text": "§2.3 细节"}]
    result = detect_chapters(paragraphs)
    assert len(result) == 2
    assert result[0].level == 1
    assert result[1].level == 2


def test_pattern_chinese_section():
    """'第一节 背景' detected as level=2."""
    paragraphs = [{"text": "第一节 背景"}]
    result = detect_chapters(paragraphs)
    assert len(result) == 1
    assert result[0].level == 2


def test_style_heading_map():
    """DOCX style_name=Heading 2 maps to level=2, confidence 0.95."""
    paragraphs = [
        {"text": "Section Title", "style_name": "Heading 2"},
    ]
    result = detect_chapters(paragraphs)
    assert len(result) == 1
    assert result[0].level == 2
    assert result[0].title == "Section Title"
    assert result[0].method == "style"
    assert result[0].confidence == 0.95


def test_style_heading_all_levels():
    """Heading 1/2/3 all map correctly."""
    paragraphs = [
        {"text": "A", "style_name": "Heading 1"},
        {"text": "B", "style_name": "Heading 2"},
        {"text": "C", "style_name": "Heading 3"},
    ]
    result = detect_chapters(paragraphs)
    assert result[0].level == 1
    assert result[1].level == 2
    assert result[2].level == 3


def test_style_normal_ignored():
    """Normal style (or no style) is not detected."""
    paragraphs = [
        {"text": "Normal text", "style_name": "Normal"},
        {"text": "No style at all"},
    ]
    result = detect_chapters(paragraphs)
    assert len(result) == 0


def test_font_large_bold():
    """font_size >= 16pt + is_bold -> candidate level=1, confidence 0.6."""
    paragraphs = [
        {"text": "Big Bold Title", "font_size": 18.0, "is_bold": True},
    ]
    result = detect_chapters(paragraphs)
    assert len(result) == 1
    assert result[0].level == 1
    assert result[0].method == "font"
    assert result[0].confidence == 0.6


def test_font_small_bold_ignored():
    """font_size < 16pt even if bold -> not detected."""
    paragraphs = [
        {"text": "Small Bold", "font_size": 14.0, "is_bold": True},
    ]
    result = detect_chapters(paragraphs)
    assert len(result) == 0


def test_font_large_not_bold_ignored():
    """font_size >= 16 but not bold -> not detected."""
    paragraphs = [
        {"text": "Large Normal", "font_size": 18.0, "is_bold": False},
    ]
    result = detect_chapters(paragraphs)
    assert len(result) == 0


def test_dedup_font_only():
    """Font-based consecutive same-level headings are dedup-ed (line-wrap false positives).
    Pattern-based headings at the same level are NOT dedup-ed — they're distinct titles."""
    paragraphs = [
        {"text": "Big Title Line 1", "font_size": 18.0, "is_bold": True},
        {"text": "Big Title Line 2", "font_size": 18.0, "is_bold": True},
        {"text": "1.1 Sub"},
        {"text": "Another Big", "font_size": 18.0, "is_bold": True},
    ]
    result = detect_chapters(paragraphs)
    # Font lines 0,1 dedup-ed → keep 0. Line 2 is pattern. Line 3 font but not consecutive.
    assert len(result) == 3
    assert result[0].method == "font"
    assert result[1].method == "pattern"
    assert result[2].method == "font"


def test_pattern_no_dedup():
    """Pattern-detected headings at same level are not dedup-ed."""
    paragraphs = [
        {"text": "1. Title A"},
        {"text": "2. Title B"},
    ]
    result = detect_chapters(paragraphs)
    assert len(result) == 2


def test_style_wins_over_pattern():
    """When style and pattern both match, higher confidence (style) wins."""
    paragraphs = [
        {"text": "1. Introduction", "style_name": "Heading 1"},
    ]
    result = detect_chapters(paragraphs)
    assert len(result) == 1
    assert result[0].method == "style"  # 0.95 > 0.9
    assert result[0].confidence == 0.95


def test_font_wins_over_nothing():
    """Font detection works with pattern if both present, style wins if available."""
    paragraphs = [
        {"text": "Big Chapter", "font_size": 16.0, "is_bold": True, "style_name": "Heading 1"},
    ]
    result = detect_chapters(paragraphs)
    assert len(result) == 1
    assert result[0].method == "style"  # 0.95 > 0.6 and > 0.9


def test_pure_text_pattern_only():
    """Plain text (no font/style info) only uses pattern detection."""
    paragraphs = [
        {"text": "第一章 开始"},
        {"text": "普通正文"},
        {"text": "1.1 背景"},
    ]
    result = detect_chapters(paragraphs)
    assert len(result) == 2
    assert result[0].level == 1
    assert result[0].method == "pattern"
    assert result[1].level == 2
    assert result[1].method == "pattern"


def test_empty_paragraphs():
    """Empty input returns empty list."""
    assert detect_chapters([]) == []


def test_no_matches():
    """Paragraphs with no heading signals return empty list."""
    paragraphs = [
        {"text": "Just some normal text here."},
        {"text": "More text, nothing special."},
    ]
    assert detect_chapters(paragraphs) == []


def test_returns_pydantic_models():
    """detect_chapters returns list of ChapterHeading."""
    paragraphs = [{"text": "第一章 标题"}]
    result = detect_chapters(paragraphs)
    assert isinstance(result, list)
    assert isinstance(result[0], ChapterHeading)
    assert result[0].model_dump() == {
        "line_index": 0,
        "level": 1,
        "title": "第一章 标题",
        "confidence": 0.9,
        "method": "pattern",
    }


def test_line_index_correct():
    """line_index reflects the paragraph position."""
    paragraphs = [
        {"text": "ignored"},
        {"text": "第一章 标题"},
    ]
    result = detect_chapters(paragraphs)
    assert result[0].line_index == 1


def test_chapter_number_variants():
    """Various Chinese chapter numbers: 十, 十一, 二十, 一百."""
    paragraphs = [
        {"text": "第十章 结尾"},
        {"text": "第十一章 开始"},
        {"text": "第二十章 中间"},
    ]
    result = detect_chapters(paragraphs)
    assert len(result) == 3
    assert all(r.level == 1 for r in result)


def test_whitespace_insensitive():
    """Leading whitespace in text doesn't affect detection."""
    paragraphs = [{"text": "  1.1 背景  "}]
    result = detect_chapters(paragraphs)
    assert len(result) == 1
    assert result[0].level == 2
    assert result[0].title.startswith("1.1")
