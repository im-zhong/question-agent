"""Batch question generation from knowledge points."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from question_agent.questions.llm import category_to_question_type, generate_question_llm
from question_agent.questions.models import GenerationStats, QuestionOption, QuestionStem


@dataclass
class _KpInput:
    """Internal input for question generation."""

    name: str
    description: str
    tags: list[dict[str, str]]


def _make_failed_stem(idx: int, kp: _KpInput) -> QuestionStem:
    """Create a placeholder stem for a failed generation."""
    category = kp.tags[0]["category"] if kp.tags else "concept"
    qtype = category_to_question_type(category)
    return QuestionStem(
        id=idx,
        stem_text=f"关于「{kp.name}」的{qtype}题（生成失败）",
        options=[
            QuestionOption(label="A", text="选项A（占位）"),
            QuestionOption(label="B", text="选项B（占位）"),
            QuestionOption(label="C", text="选项C（占位）"),
            QuestionOption(label="D", text="选项D（占位）"),
        ],
        knowledge_point_name=kp.name,
        question_type=qtype,
        status="failed",
        error="GLM-5 生成失败，返回占位题干",
    )


async def generate_questions(
    knowledge_points: list[_KpInput],
) -> tuple[list[QuestionStem], GenerationStats]:
    """Generate questions from a list of knowledge points.

    Args:
        knowledge_points: List of named tuples with name, description, tags.

    Returns:
        Tuple of (questions, generation_stats).
    """
    questions: list[QuestionStem] = []
    successful = 0

    for idx, kp in enumerate(knowledge_points):
        result = await asyncio.to_thread(
            generate_question_llm, name=kp.name, description=kp.description, tags=kp.tags
        )
        if result is not None:
            result.id = idx + 1
            successful += 1
            questions.append(result)
        else:
            questions.append(_make_failed_stem(idx + 1, kp))

    total = len(questions)
    failed = total - successful
    return questions, GenerationStats(total=total, successful=successful, failed=failed)
