"""GLM-5 question generation via zai-sdk.

Generates structured question stems with 4 simplified options from
knowledge point inputs using semantic LLM analysis. Supports category-aware
prompt selection with few-shot examples per knowledge point type.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, ValidationError

from question_agent.chapters.llm import _create_client
from question_agent.config import settings
from question_agent.questions.models import (
    DifficultyLevel,
    QuestionOption,
    QuestionStem,
    QuestionType,
)
from question_agent.questions.prompts import select_prompt

logger = logging.getLogger(__name__)

_TIMEOUT = 30.0
_TEMPERATURE = 0.7
_MAX_TOKENS = 2000

_DIFFICULTY_INSTRUCTIONS: dict[DifficultyLevel, str] = {
    "basic": (
        "Difficulty: BASIC. Use straightforward scenarios, simple vocabulary, "
        "and direct application of the concept. Avoid multi-step reasoning."
    ),
    "intermediate": (
        "Difficulty: INTERMEDIATE. Use moderate scenarios requiring 1-2 steps "
        "of reasoning. Include some abstraction or combination of ideas."
    ),
    "advanced": (
        "Difficulty: ADVANCED. Use complex scenarios requiring multi-step "
        "reasoning, analysis, or synthesis. Include edge cases or require "
        "deeper understanding."
    ),
}


class _LlmQuestionResult(BaseModel):
    stem_text: str
    correct_answer: str | None = None
    reference_answer: str | None = None
    explanation: str | None = None
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
    difficulty: DifficultyLevel = "intermediate",
    question_type: str | None = None,
    client: Any = None,
) -> QuestionStem | None:
    """Use GLM-5 to generate a question from a knowledge point.

    Args:
        name: Knowledge point name.
        description: Knowledge point description.
        tags: Optional tag list with value and category fields.
        difficulty: Question difficulty level (basic/intermediate/advanced).
        question_type: Optional question type override (short_answer/essay for subjective).
        client: Optional pre-configured ZhipuAiClient (for testing).

    Returns:
        QuestionStem with LLM-generated content, or None if unavailable.
    """
    if not name.strip():
        logger.warning("generate_question_llm: empty name, returning None")
        return None

    if client is None:
        client = _create_client()

    if client is None:
        logger.warning("generate_question_llm: client creation failed (no API key?)")
        return None

    system_prompt = select_prompt(tags, question_type=question_type)
    difficulty_instruction = _DIFFICULTY_INSTRUCTIONS.get(difficulty, "")
    if difficulty_instruction:
        system_prompt = f"{system_prompt}\n\n{difficulty_instruction}"

    logger.info(
        "generate_question_llm: calling GLM-5 kp=%r qtype=%s diff=%s",
        name[:50],
        question_type,
        difficulty,
    )

    try:
        response = client.chat.completions.create(
            model=settings.glm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": _build_user_prompt(name, description, tags)},
            ],
            temperature=_TEMPERATURE,
            max_tokens=_MAX_TOKENS,
            response_format={"type": "json_object"},
            timeout=_TIMEOUT,
        )
    except Exception as e:
        logger.warning("generate_question_llm: GLM-5 API call failed for kp=%r: %s", name[:50], e)
        return None

    content = response.choices[0].message.content if response.choices else ""
    if not content:
        logger.warning("generate_question_llm: empty response for kp=%r", name[:50])
        return None

    logger.debug("generate_question_llm: raw response for kp=%r: %.200s", name[:50], content)

    result = _parse_response(content)
    if result is None:
        logger.warning("generate_question_llm: failed to parse response for kp=%r", name[:50])
        return None

    # Determine question type
    if question_type:
        qtype: QuestionType = question_type  # type: ignore[assignment]
    else:
        category = tags[0]["category"] if tags else "concept"
        qtype = category_to_question_type(category)

    return QuestionStem(
        id=0,  # caller assigns IDs
        stem_text=result.stem_text,
        options=result.options,
        correct_answer=result.correct_answer,
        reference_answer=result.reference_answer,
        explanation=result.explanation,
        difficulty=difficulty,
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
