"""Hybrid knowledge point extraction engine.

Merges rule-based (detector.py) and LLM-based (llm.py) knowledge point
extraction, deduplicating by source_line overlap and preferring higher
confidence results.
"""

from __future__ import annotations

from typing import Any

from question_agent.knowledge.detector import detect_knowledge_points_rule
from question_agent.knowledge.llm import extract_knowledge_points_llm
from question_agent.knowledge.models import ChapterWindow, KnowledgePoint

_OVERLAP_THRESHOLD = 0.5


def _ranges_overlap(
    start1: int,
    end1: int,
    start2: int,
    end2: int,
) -> bool:
    """Check if two line ranges overlap by more than 50% of the smaller range."""
    if start1 >= end2 or start2 >= end1:
        return False
    overlap_start = max(start1, start2)
    overlap_end = min(end1, end2)
    overlap_len = overlap_end - overlap_start
    smaller_len = min(end1 - start1, end2 - start2)
    if smaller_len == 0:
        return False
    return overlap_len / smaller_len > _OVERLAP_THRESHOLD


def _dedup_by_range(
    rule_points: list[KnowledgePoint],
    llm_points: list[KnowledgePoint],
) -> list[KnowledgePoint]:
    """Deduplicate knowledge points by source_line range overlap.

    When rule and LLM detect the same knowledge point (overlapping ranges),
    keep the one with higher confidence. Non-overlapping results are all kept.
    """
    result: list[KnowledgePoint] = []
    llm_consumed: set[int] = set()

    for rp in rule_points:
        dominated = False
        for j, lp in enumerate(llm_points):
            if _ranges_overlap(
                rp.source_line_start,
                rp.source_line_end,
                lp.source_line_start,
                lp.source_line_end,
            ):
                if lp.confidence > rp.confidence:
                    # LLM wins — skip rule point, LLM point added later
                    dominated = True
                else:
                    # Rule wins — mark LLM point as consumed
                    llm_consumed.add(j)
                break
        if not dominated:
            result.append(rp)

    # Add LLM results not consumed by rule wins
    for j, lp in enumerate(llm_points):
        if j not in llm_consumed:
            result.append(lp)

    return result


def _renumber(points: list[KnowledgePoint]) -> list[KnowledgePoint]:
    """Re-assign sequential IDs after dedup."""
    return [
        KnowledgePoint(
            id=i,
            name=p.name,
            description=p.description,
            tags=p.tags,
            confidence=p.confidence,
            method=p.method,
            source_line_start=p.source_line_start,
            source_line_end=p.source_line_end,
        )
        for i, p in enumerate(points)
    ]


def extract_knowledge_points_hybrid(
    windows: list[ChapterWindow],
    paragraphs: list[dict[str, Any]],
    llm_client: Any = None,
) -> dict[str, Any]:
    """Merge rule-based and LLM-based knowledge point extraction.

    Strategy:
    1. Run rule detector on all paragraphs (always, zero-cost)
    2. Run LLM extractor on each window (may return None if unavailable)
    3. Dedup: overlapping ranges → keep higher confidence
    4. If LLM unavailable, degrade to rule_only

    Args:
        windows: List of ChapterWindow from build_chapter_windows().
        paragraphs: Flat list of paragraph dicts.
        llm_client: Optional pre-configured ZhipuAiClient.

    Returns:
        dict with keys:
            knowledge_points: list[KnowledgePoint]
            detection_method: "hybrid" | "rule_only" | "llm_only" | "none"
            rule_count: int
            llm_count: int
    """
    # Rule detection — always runs
    rule_points = detect_knowledge_points_rule(paragraphs)

    # LLM detection — per window
    all_llm_points: list[KnowledgePoint] = []
    llm_available = False
    start_id = 0

    for window in windows:
        llm_result = extract_knowledge_points_llm(window, client=llm_client, start_id=start_id)
        if llm_result is not None:
            llm_available = True
            all_llm_points.extend(llm_result)
            start_id += len(llm_result)

    # Determine merge strategy
    if not llm_available:
        if not rule_points:
            return {
                "knowledge_points": [],
                "detection_method": "none",
                "rule_count": 0,
                "llm_count": 0,
            }
        return {
            "knowledge_points": _renumber(rule_points),
            "detection_method": "rule_only",
            "rule_count": len(rule_points),
            "llm_count": 0,
        }

    if not rule_points:
        return {
            "knowledge_points": _renumber(all_llm_points),
            "detection_method": "llm_only",
            "rule_count": 0,
            "llm_count": len(all_llm_points),
        }

    # Merge and dedup
    merged = _dedup_by_range(rule_points, all_llm_points)
    merged = _renumber(merged)

    rule_count = sum(1 for p in merged if p.method == "rule")
    llm_count = sum(1 for p in merged if p.method == "llm")

    return {
        "knowledge_points": merged,
        "detection_method": "hybrid",
        "rule_count": rule_count,
        "llm_count": llm_count,
    }
