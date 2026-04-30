"""Rule-based chapter heading detector.

Consumes structured paragraph data (from /extract?mode=structured) and detects
chapter/section titles using three strategies:
  1. Pattern matching (Chinese/English numbering)
  2. DOCX style mapping (Heading 1/2/3)
  3. Font heuristic (large + bold)
"""

from __future__ import annotations

import re
from typing import Any

from question_agent.chapters.models import ChapterHeading

# Ordered by specificity — longer/more specific patterns first
_PATTERNS: list[tuple[str, int]] = [
    # Dotted decimal: 1.1.1 -> level 3, 1.1 -> level 2, 1. -> level 1
    (r"^\s*\d+\.\d+\.\d+\s+", 3),
    (r"^\s*\d+\.\d+\s+", 2),
    (r"^\s*\d+\.\s+", 1),
    # Chinese chapter/section: 第一章, 第二节
    (r"^\s*第[一二三四五六七八九十百千零]+章", 1),
    (r"^\s*第[一二三四五六七八九十百千零]+节", 2),
    # Chinese paren numbering: (一), （三）
    (r"^\s*[（(][一二三四五六七八九十零]+[）)]", 1),
    # Chinese dun-numbering: 一、, 二、
    (r"^\s*[一二三四五六七八九十零]+、", 1),
    # Section symbol: §1, §2.3
    (r"^\s*§\d+\.\d+", 2),
    (r"^\s*§\d+", 1),
]

_STYLE_MAP: dict[str, int] = {
    "Heading 1": 1,
    "Heading 2": 2,
    "Heading 3": 3,
}

STYLE_CONFIDENCE = 0.95
PATTERN_CONFIDENCE = 0.9
FONT_CONFIDENCE = 0.6
FONT_SIZE_THRESHOLD = 16


def _detect_by_pattern(text: str, line_index: int) -> list[ChapterHeading]:
    """Detect chapter headings by numbering pattern."""
    results: list[ChapterHeading] = []
    for regex, level in _PATTERNS:
        if re.match(regex, text):
            results.append(
                ChapterHeading(
                    line_index=line_index,
                    level=level,
                    title=text.strip(),
                    confidence=PATTERN_CONFIDENCE,
                    method="pattern",
                )
            )
            break  # first match wins (most specific)
    return results


def _detect_by_style(para: dict[str, Any], line_index: int) -> list[ChapterHeading]:
    """Detect chapter headings from DOCX paragraph style."""
    style_name = para.get("style_name")
    if not style_name or style_name not in _STYLE_MAP:
        return []
    return [
        ChapterHeading(
            line_index=line_index,
            level=_STYLE_MAP[style_name],
            title=para.get("text", "").strip(),
            confidence=STYLE_CONFIDENCE,
            method="style",
        )
    ]


def _detect_by_font(para: dict[str, Any], line_index: int) -> list[ChapterHeading]:
    """Detect chapter heading candidates by font size + bold."""
    font_size = para.get("font_size")
    is_bold = para.get("is_bold")
    if font_size is None or is_bold is None:
        return []
    if font_size >= FONT_SIZE_THRESHOLD and is_bold:
        return [
            ChapterHeading(
                line_index=line_index,
                level=1,
                title=para.get("text", "").strip(),
                confidence=FONT_CONFIDENCE,
                method="font",
            )
        ]
    return []


def _dedup_font_candidates(headings: list[ChapterHeading]) -> list[ChapterHeading]:
    """Remove consecutive font-detected headings at the same level (line-wrapping
    false positives). Pattern and style detections are trusted and never deduped."""
    if not headings:
        return []
    result = [headings[0]]
    for h in headings[1:]:
        prev = result[-1]
        # Only dedup font-based detections — they are the most likely false positives
        if (
            prev.method == "font"
            and h.method == "font"
            and h.level == prev.level
            and h.line_index == prev.line_index + 1
        ):
            continue
        result.append(h)
    return result


def _merge_by_line(
    candidates: list[ChapterHeading],
) -> list[ChapterHeading]:
    """Merge detections from all strategies. Per line_index, keep highest confidence."""
    by_line: dict[int, ChapterHeading] = {}
    for c in candidates:
        existing = by_line.get(c.line_index)
        if existing is None or c.confidence > existing.confidence:
            by_line[c.line_index] = c
    # Sort by line_index
    return sorted(by_line.values(), key=lambda h: h.line_index)


def detect_chapters(paragraphs: list[dict[str, Any]]) -> list[ChapterHeading]:
    """Detect chapter headings from structured paragraph data.

    Args:
        paragraphs: List of dicts from /extract?mode=structured.
                    Each has text plus optional font_size, is_bold, x0, style_name.

    Returns:
        List of ChapterHeading sorted by line_index.
    """
    candidates: list[ChapterHeading] = []

    for i, para in enumerate(paragraphs):
        text = para.get("text", "").strip()
        if not text:
            continue

        candidates.extend(_detect_by_style(para, i))
        candidates.extend(_detect_by_pattern(text, i))
        candidates.extend(_detect_by_font(para, i))

    merged = _merge_by_line(candidates)
    return _dedup_font_candidates(merged)
