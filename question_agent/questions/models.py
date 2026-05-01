"""Pydantic models for question generation."""

from typing import Any, Literal

from pydantic import BaseModel

QuestionType = Literal[
    "definition", "application", "calculation", "procedure", "recall", "analysis"
]


class QuestionOption(BaseModel):
    label: str
    text: str


class QuestionStem(BaseModel):
    id: int
    stem_text: str
    options: list[QuestionOption]
    knowledge_point_name: str
    question_type: QuestionType
    metadata: dict[str, Any] | None = None
