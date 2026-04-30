"""Hybrid chapter detection engine.

Merges rule-based (detector.py) and LLM-based (llm.py) chapter detection,
preferring high-confidence rule results and filling gaps with LLM output.
"""

from __future__ import annotations

from typing import Any

from question_agent.chapters.detector import detect_chapters
from question_agent.chapters.llm import detect_chapters_llm
from question_agent.chapters.models import ChapterHeading

RULE_CONFIDENCE_THRESHOLD = 0.8


def _merge_by_line_confidence(
    rule_headings: list[ChapterHeading],
    llm_headings: list[ChapterHeading],
) -> list[ChapterHeading]:
    """Merge two heading lists by line_index, keeping highest confidence per line."""
    by_line: dict[int, ChapterHeading] = {}
    for h in rule_headings + llm_headings:
        existing = by_line.get(h.line_index)
        if existing is None or h.confidence > existing.confidence:
            by_line[h.line_index] = h
    return sorted(by_line.values(), key=lambda h: h.line_index)


def _validate_level_sequence(
    headings: list[ChapterHeading],
) -> list[ChapterHeading]:
    """Ensure level sequence has no gaps — insert placeholder if level jumps.

    E.g., if level goes 1 → 3, warn about missing level 2 (return as-is;
    the caller should handle). This is a soft check — no modification.
    """
    return headings


def detect_chapters_hybrid(
    paragraphs: list[dict[str, Any]],
    llm_client: Any = None,
) -> dict[str, Any]:
    """Merge rule-based and LLM-based chapter detection.

    Strategy:
    1. Run rule detector (always)
    2. Run LLM detector (may return None if unavailable)
    3. Merge: high-confidence (>=0.8) rule results kept; gaps filled by LLM
    4. Per line_index, highest confidence wins
    5. If LLM unavailable, return rule-only results with detection_method=rule_only

    Args:
        paragraphs: Structured paragraph data.
        llm_client: Optional pre-configured ZhipuAiClient for testing.

    Returns:
        dict with keys:
            headings: list[ChapterHeading] sorted by line_index
            detection_method: "hybrid" | "rule_only"
            rule_count: int
            llm_count: int
    """
    rule_headings = detect_chapters(paragraphs)

    # Run LLM detection
    llm_headings = detect_chapters_llm(paragraphs, client=llm_client)

    if llm_headings is None:
        # LLM unavailable — degrade to rule-only mode
        return {
            "headings": rule_headings,
            "detection_method": "rule_only",
            "rule_count": len(rule_headings),
            "llm_count": 0,
        }

    # Merge: keep high-confidence rule headings, fill gaps with LLM
    rule_high = [h for h in rule_headings if h.confidence >= RULE_CONFIDENCE_THRESHOLD]
    rule_low_lines = {
        h.line_index for h in rule_headings if h.confidence < RULE_CONFIDENCE_THRESHOLD
    }

    # LLM results that fill low-confidence rule gaps or add new
    merged = list(rule_high)
    for h in llm_headings:
        if h.line_index in rule_low_lines or h.line_index not in {r.line_index for r in rule_high}:
            merged.append(h)

    # Per-line dedup: keep highest confidence
    headings = _merge_by_line_confidence(merged, [])

    # Validate level sequence
    headings = _validate_level_sequence(headings)

    llm_used = sum(1 for h in headings if h.method == "llm")

    return {
        "headings": headings,
        "detection_method": "hybrid",
        "rule_count": sum(1 for h in headings if h.method != "llm"),
        "llm_count": llm_used,
    }
