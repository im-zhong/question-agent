"""GLM-5 knowledge point extraction via zai-sdk.

Identifies concept definitions, formulas, procedures, facts, and principles
from chapter text windows using semantic LLM analysis.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, ValidationError

from question_agent.chapters.llm import _create_client
from question_agent.config import settings
from question_agent.knowledge.models import ChapterWindow, KnowledgePoint, KnowledgeTag

logger = logging.getLogger(__name__)

_TIMEOUT = 30.0
_TEMPERATURE = 0.1
_MAX_TOKENS = 3000

_SYSTEM_PROMPT = """\
You are a knowledge point extraction engine for textbook content. Your task \
is to identify and extract knowledge points from the given text.

Knowledge point categories:
1. concept — definitions and terminology (e.g. "加速度是指速度变化量与...的比值")
2. formula — formulas, theorems, and equations (e.g. "F = ma", "v = v₀ + at")
3. procedure — step-by-step processes and methods (e.g. "第一步...第二步...")
4. fact — factual statements and data (e.g. "光速约为3×10⁸ m/s")
5. principle — underlying principles and laws (e.g. "牛顿第二定律揭示了力与...的关系")

Rules:
1. Identify BOTH explicitly marked AND implicit knowledge points.
2. Each knowledge point must have accurate source_line_start and source_line_end \
referencing the line range in the input text.
3. A knowledge point can have multiple tags (e.g. "牛顿定律" is both concept and principle).
4. Return ONLY valid JSON — no commentary, no markdown fences.

Output JSON schema:
{"knowledge_points": [{"name": "...", "description": "...", \
"tags": [{"value": "...", "category": "concept"}], "source_line_start": 0, \
"source_line_end": 2}]}
"""


class _LlmKnowledgePointResult(BaseModel):
    name: str
    description: str
    tags: list[KnowledgeTag]
    source_line_start: int
    source_line_end: int


class _KnowledgePointsResponse(BaseModel):
    knowledge_points: list[_LlmKnowledgePointResult]


def _build_user_prompt(window: ChapterWindow) -> str:
    """Build a user prompt from a chapter window."""
    lines = [
        f"Chapter: {window.chapter_title}",
        f"Line range: {window.line_start}-{window.line_end}",
        "",
        window.text,
    ]
    return "\n".join(lines)


def _parse_response(
    raw: str, window: ChapterWindow, start_id: int = 0
) -> list[KnowledgePoint] | None:
    """Parse GLM-5 JSON response into KnowledgePoint list."""
    text = raw.strip()
    # Strip markdown fences if present (defensive)
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        data = json.loads(text)
        parsed = _KnowledgePointsResponse.model_validate(data)
    except (json.JSONDecodeError, ValidationError):
        logger.warning("GLM-5 returned invalid JSON for knowledge points: %.200s", raw)
        return None

    results: list[KnowledgePoint] = []
    for i, r in enumerate(parsed.knowledge_points):
        results.append(
            KnowledgePoint(
                id=start_id + i,
                name=r.name,
                description=r.description,
                tags=r.tags,
                confidence=0.85,
                method="llm",
                source_line_start=r.source_line_start,
                source_line_end=r.source_line_end,
            )
        )
    return results


def extract_knowledge_points_llm(
    window: ChapterWindow,
    client: Any = None,
    start_id: int = 0,
) -> list[KnowledgePoint] | None:
    """Use GLM-5 to extract knowledge points from a chapter window.

    Args:
        window: ChapterWindow containing the text to analyze.
        client: Optional pre-configured ZhipuAiClient (for testing).
        start_id: Starting ID for knowledge points (for multi-window numbering).

    Returns:
        List of KnowledgePoint, or None if GLM-5 is unavailable or fails.
    """
    if not window.text.strip():
        return None

    if client is None:
        client = _create_client()

    if client is None:
        return None

    try:
        response = client.chat.completions.create(
            model=settings.glm_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(window)},
            ],
            temperature=_TEMPERATURE,
            max_tokens=_MAX_TOKENS,
            response_format={"type": "json_object"},
            timeout=_TIMEOUT,
        )
    except Exception as e:
        logger.warning("GLM-5 API call failed for knowledge points: %s", e)
        return None

    content = response.choices[0].message.content if response.choices else ""
    if not content:
        return None

    return _parse_response(content, window, start_id)
