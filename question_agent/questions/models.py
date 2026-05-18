"""Pydantic models for question generation."""

from typing import Any, Literal

from pydantic import BaseModel

QuestionType = Literal[
    "definition",
    "application",
    "calculation",
    "procedure",
    "recall",
    "analysis",
    "short_answer",
    "essay",
]

DifficultyLevel = Literal["basic", "intermediate", "advanced"]

QuestionStatus = Literal["success", "failed"]


class QuestionOption(BaseModel):
    label: str
    text: str


class QuestionStem(BaseModel):
    id: int
    stem_text: str
    options: list[QuestionOption]
    correct_answer: str | None = None
    reference_answer: str | None = None
    explanation: str | None = None
    difficulty: DifficultyLevel = "intermediate"
    knowledge_point_name: str
    question_type: QuestionType
    status: QuestionStatus = "success"
    error: str | None = None
    metadata: dict[str, Any] | None = None


class GenerationStats(BaseModel):
    total: int
    successful: int
    failed: int
