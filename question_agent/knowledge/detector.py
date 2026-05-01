"""Rule-based knowledge point detection via marker word matching.

Provides zero-cost initial screening for knowledge points using keyword
patterns like "定义", "是指", "公式", "定理", "第一步" etc.
This is a supplementary detector — limited coverage, used as fallback
when GLM-5 is unavailable.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from question_agent.knowledge.models import KnowledgePoint, KnowledgeTag

_TagCategory = Literal["concept", "formula", "procedure", "fact", "principle"]

_RULE_CONFIDENCE = 0.7

# Marker patterns: (regex, category, tag_value_extractor)
# Each pattern maps to a knowledge point category.
_MARKER_PATTERNS: list[tuple[str, _TagCategory]] = [
    # Concept markers: definitions and terminology
    (r"(?:定义[是为：:]|是指|称为|叫做|指的是)", "concept"),
    (r"(?:又称|也叫|简称为)", "concept"),
    # Formula markers: formulas, theorems, equations
    (r"(?:公式[是为：:]|定理[是为：:]|定律[是为：:]|方程[是为：:])", "formula"),
    (r"(?:公式：|定理：|定律：|方程：)", "formula"),
    # Procedure markers: step-by-step processes
    (r"(?:第[一二三四五六七八九十\d]+步)", "procedure"),
    (r"(?:步骤[一二三四五六七八九十\d]+|步骤[是为：:])", "procedure"),
    # Fact markers: factual statements
    (r"(?:事实[是为：:]|数据[是为：:]|约为|大约[是为])", "fact"),
    # Principle markers: underlying principles
    (r"(?:原理[是为：:]|规律[是为：:]|机制[是为：:])", "principle"),
]


def _extract_name(text: str, match: re.Match[str], category: _TagCategory) -> str:
    """Extract a short name for the knowledge point from the matched text."""
    # Use the sentence portion around the marker as the name
    start = max(0, match.start() - 15)
    end = min(len(text), match.end() + 30)
    name = text[start:end].strip()
    # Truncate at sentence boundaries
    for sep in ["。", "；", "，", ".", ";", ","]:
        idx = name.find(sep)
        if idx > 0:
            name = name[:idx]
    if len(name) > 60:
        name = name[:57] + "..."
    return name


def detect_knowledge_points_rule(
    paragraphs: list[dict[str, Any]],
) -> list[KnowledgePoint]:
    """Detect knowledge points using rule-based marker word matching.

    Args:
        paragraphs: List of paragraph dicts with "text" key.

    Returns:
        List of KnowledgePoint with method="rule" and confidence=0.7.
        Empty list if no markers found.
    """
    if not paragraphs:
        return []

    results: list[KnowledgePoint] = []
    kp_id = 0

    for line_idx, para in enumerate(paragraphs):
        text = (para.get("text") or "").strip()
        if not text:
            continue

        seen_categories: set[str] = set()

        for pattern, category in _MARKER_PATTERNS:
            if category in seen_categories:
                continue

            match = re.search(pattern, text)
            if match:
                seen_categories.add(category)
                name = _extract_name(text, match, category)
                results.append(
                    KnowledgePoint(
                        id=kp_id,
                        name=name,
                        description=text,
                        tags=[KnowledgeTag(value=name, category=category)],
                        confidence=_RULE_CONFIDENCE,
                        method="rule",
                        source_line_start=line_idx,
                        source_line_end=line_idx + 1,
                    )
                )
                kp_id += 1

    return results
