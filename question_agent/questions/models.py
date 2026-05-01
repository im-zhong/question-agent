"""Pydantic models for question generation."""

from typing import Any, Literal

from pydantic import BaseModel

QuestionType = Literal[
    "definition", "application", "calculation", "procedure", "recall", "analysis"
]

QuestionStatus = Literal["success", "failed"]


class QuestionOption(BaseModel):
    label: str
    text: str


class QuestionStem(BaseModel):
    id: int
    stem_text: str
    options: list[QuestionOption]
    knowledge_point_name: str
    question_type: QuestionType
    status: QuestionStatus = "success"
    error: str | None = None
    metadata: dict[str, Any] | None = None


class GenerationStats(BaseModel):
    total: int
    successful: int
    failed: int
