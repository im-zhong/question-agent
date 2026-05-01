"""GLM-5 question generation via zai-sdk.

Generates structured question stems with 4 simplified options from
knowledge point inputs using semantic LLM analysis.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, ValidationError

from question_agent.chapters.llm import _create_client
from question_agent.config import settings
from question_agent.questions.models import QuestionOption, QuestionStem, QuestionType

logger = logging.getLogger(__name__)

_TIMEOUT = 30.0
_TEMPERATURE = 0.7
_MAX_TOKENS = 2000

_SYSTEM_PROMPT = """\
You are a question generation engine for educational content. Given a \
knowledge point, generate a multiple-choice question stem with 4 options.

Rules:
1. The question must be directly relevant to the knowledge point's name \
and description.
2. Generate exactly 4 options labeled A, B, C, D.
3. At this stage, options are simplified placeholders — they should be \
plausible but do NOT need to be carefully designed distractors.
4. The question type should match the knowledge category:
   - concept → definition/understanding question
   - formula → application/calculation question
   - procedure → step/operation question
   - fact → recall question
   - principle → analysis/derivation question
5. Return ONLY valid JSON — no commentary, no markdown fences.

Output JSON schema:
{"stem_text": "...", "options": [{"label": "A", "text": "..."}, \
{"label": "B", "text": "..."}, {"label": "C", "text": "..."}, \
{"label": "D", "text": "..."}]}
"""


class _LlmQuestionResult(BaseModel):
    stem_text: str
    options: list[QuestionOption]


def _build_user_prompt(
    name: str, description: str, tags: list[dict[str, str]] | None = None
) -> str:
    """Build a user prompt from a knowledge point."""
    parts = [f"Knowledge point name: {name}", f"Description: {description}"]
    if tags:
        tag_strs = [f"{t['value']}({t['category']})" for t in tags]
        parts.append(f"Tags: {', '.join(tag_strs)}")
    return "\n".join(parts)


def _parse_response(raw: str) -> _LlmQuestionResult | None:
    """Parse GLM-5 JSON response into question result."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        data = json.loads(text)
        return _LlmQuestionResult.model_validate(data)
    except (json.JSONDecodeError, ValidationError):
        logger.warning("GLM-5 returned invalid JSON for question generation: %.200s", raw)
        return None


def generate_question_llm(
    name: str,
    description: str,
    tags: list[dict[str, str]] | None = None,
    client: Any = None,
) -> QuestionStem | None:
    """Use GLM-5 to generate a question from a knowledge point.

    Args:
        name: Knowledge point name.
        description: Knowledge point description.
        tags: Optional tag list with value and category fields.
        client: Optional pre-configured ZhipuAiClient (for testing).

    Returns:
        QuestionStem with LLM-generated content, or None if unavailable.
    """
    if not name.strip():
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
                {"role": "user", "content": _build_user_prompt(name, description, tags)},
            ],
            temperature=_TEMPERATURE,
            max_tokens=_MAX_TOKENS,
            response_format={"type": "json_object"},
            timeout=_TIMEOUT,
        )
    except Exception as e:
        logger.warning("GLM-5 API call failed for question generation: %s", e)
        return None

    content = response.choices[0].message.content if response.choices else ""
    if not content:
        return None

    result = _parse_response(content)
    if result is None:
        return None

    # Determine question type from primary tag
    category = tags[0]["category"] if tags else "concept"
    qtype = category_to_question_type(category)

    return QuestionStem(
        id=0,  # caller assigns IDs
        stem_text=result.stem_text,
        options=result.options,
        knowledge_point_name=name,
        question_type=qtype,
    )


def category_to_question_type(category: str) -> QuestionType:
    mapping: dict[str, QuestionType] = {
        "concept": "definition",
        "formula": "calculation",
        "procedure": "procedure",
        "fact": "recall",
        "principle": "analysis",
    }
    return mapping.get(category, "definition")
