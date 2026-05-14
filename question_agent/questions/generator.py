"""Batch question generation from knowledge points."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from question_agent.questions.llm import category_to_question_type, generate_question_llm
from question_agent.questions.models import (
    DifficultyLevel,
    GenerationStats,
    QuestionOption,
    QuestionStem,
)

logger = logging.getLogger(__name__)


@dataclass
class _KpInput:
    """Internal input for question generation."""

    name: str
    description: str
    tags: list[dict[str, str]]


def _make_failed_stem(idx: int, kp: _KpInput, question_type: str | None = None) -> QuestionStem:
    """Create a placeholder stem for a failed generation."""
    if question_type:
        qtype = question_type
    else:
        category = kp.tags[0]["category"] if kp.tags else "concept"
        qtype = category_to_question_type(category)
    is_subjective = question_type in ("short_answer", "essay")
    return QuestionStem(
        id=idx,
        stem_text=f"关于「{kp.name}」的{qtype}题（生成失败）",
        options=[]
        if is_subjective
        else [
            QuestionOption(label="A", text="选项A（占位）"),
            QuestionOption(label="B", text="选项B（占位）"),
            QuestionOption(label="C", text="选项C（占位）"),
            QuestionOption(label="D", text="选项D（占位）"),
        ],
        knowledge_point_name=kp.name,
        question_type=qtype,  # type: ignore[arg-type]
        status="failed",
        error="GLM-5 生成失败，返回占位题干",
    )


async def generate_questions(
    knowledge_points: list[_KpInput],
    difficulty: DifficultyLevel = "intermediate",
    question_type: str | None = None,
) -> tuple[list[QuestionStem], GenerationStats]:
    """Generate questions from a list of knowledge points.

    Args:
        knowledge_points: List of named tuples with name, description, tags.
        difficulty: Question difficulty level (basic/intermediate/advanced).
        question_type: Optional question type override (short_answer/essay).

    Returns:
        Tuple of (questions, generation_stats).
    """
    logger.info(
        "generate_questions: %d KPs, difficulty=%s, question_type=%s",
        len(knowledge_points),
        difficulty,
        question_type,
    )

    results: list[QuestionStem | None] = await asyncio.gather(
        *[
            asyncio.to_thread(
                generate_question_llm,
                name=kp.name,
                description=kp.description,
                tags=kp.tags,
                difficulty=difficulty,
                question_type=question_type,
            )
            for kp in knowledge_points
        ]
    )

    questions: list[QuestionStem] = []
    successful = 0
    for idx, result in enumerate(results):
        if result is not None:
            result.id = idx + 1
            successful += 1
            questions.append(result)
        else:
            kp_name = knowledge_points[idx].name[:50]
            logger.warning(
                "generate_questions: KP %r (idx=%d) failed, placeholder",
                kp_name,
                idx,
            )
            questions.append(_make_failed_stem(idx + 1, knowledge_points[idx], question_type))

    total = len(questions)
    failed = total - successful
    logger.info("generate_questions: done total=%d success=%d failed=%d", total, successful, failed)
    return questions, GenerationStats(total=total, successful=successful, failed=failed)
