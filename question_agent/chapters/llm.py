"""GLM-5 chapter semantic recognition via zai-sdk.

Handles non-standard numbering systems (e.g., §2.3, Module 3, Unit 5)
that the rule-based detector cannot match.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, ValidationError

from question_agent.chapters.models import ChapterHeading
from question_agent.config import settings

logger = logging.getLogger(__name__)

_TIMEOUT = 30.0
_TEMPERATURE = 0.1
_MAX_TOKENS = 2000

_SYSTEM_PROMPT = """\
You are a textbook structure analyzer. Your task is to identify chapter \
and section headings from a list of paragraphs and determine their \
hierarchy levels.

Rules:
1. A heading is a short line that introduces a new topic or section.
2. Level 1 = chapter-level, Level 2 = section, Level 3 = subsection.
3. Non-standard numbering (e.g. "§2.3", "Module 3", "Unit 5", \
"Topic A") should still be recognized as headings.
4. Return ONLY valid JSON — no commentary, no markdown fences.

Output JSON schema:
{"chapters": [{"title": "...", "level": 1, "start_index": 0, "end_index": 5}]}

- title: the heading text (without trailing whitespace)
- level: 1, 2, or 3
- start_index: index of the heading paragraph in the input list
- end_index: index of the last paragraph belonging to this section \
(exclusive, or same as next heading's start_index)
"""


class LlmChapterResult(BaseModel):
    title: str
    level: int
    start_index: int
    end_index: int


class _ChaptersResponse(BaseModel):
    chapters: list[LlmChapterResult]


def _build_user_prompt(paragraphs: list[dict[str, Any]]) -> str:
    """Build a user prompt from structured paragraph data."""
    lines: list[str] = []
    for i, p in enumerate(paragraphs):
        text = p.get("text", "")
        style = p.get("style_name", "")
        extra = f" [style={style}]" if style else ""
        lines.append(f"[{i}]{extra} {text}")
    return "\n".join(lines)


def _parse_response(raw: str) -> list[LlmChapterResult] | None:
    """Parse GLM-5 JSON response into LlmChapterResult list."""
    text = raw.strip()
    # Strip markdown fences if present (defensive)
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```) and last line (```)
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        data = json.loads(text)
        parsed = _ChaptersResponse.model_validate(data)
        return parsed.chapters
    except (json.JSONDecodeError, ValidationError):
        logger.warning("GLM-5 returned invalid JSON: %.200s", raw)
        return None


def _create_client() -> Any:
    """Create ZhipuAiClient from settings. Returns None if API key is missing."""
    try:
        from zai import ZhipuAiClient
    except ImportError:
        logger.warning("zai-sdk not installed")
        return None

    if not settings.glm_api_key:
        logger.warning("GLM_API_KEY not configured — chapter LLM detection disabled")
        return None

    return ZhipuAiClient(api_key=settings.glm_api_key)


def detect_chapters_llm(
    paragraphs: list[dict[str, Any]],
    client: Any = None,
) -> list[ChapterHeading] | None:
    """Use GLM-5 to detect chapter headings semantically.

    Handles non-standard numbering systems that rule-based detection misses.

    Args:
        paragraphs: Structured paragraph data from /extract?mode=structured.
        client: Optional pre-configured ZhipuAiClient (for testing).

    Returns:
        List of ChapterHeading, or None if GLM-5 is unavailable or fails.
    """
    if not paragraphs:
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
                {"role": "user", "content": _build_user_prompt(paragraphs)},
            ],
            temperature=_TEMPERATURE,
            max_tokens=_MAX_TOKENS,
            response_format={"type": "json_object"},
            timeout=_TIMEOUT,
        )
    except Exception as e:
        logger.warning("GLM-5 API call failed: %s", e)
        return None

    content = response.choices[0].message.content if response.choices else ""
    if not content:
        return None

    results = _parse_response(content)
    if results is None:
        return None

    return [
        ChapterHeading(
            line_index=r.start_index,
            level=r.level,
            title=r.title,
            confidence=0.85,
            method="llm",
        )
        for r in results
    ]
