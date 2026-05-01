"""Pydantic models for knowledge point detection."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class KnowledgeTag(BaseModel):
    value: str
    category: Literal["concept", "formula", "procedure", "fact", "principle"]


class KnowledgePoint(BaseModel):
    id: int
    name: str
    description: str
    tags: list[KnowledgeTag]
    confidence: float = Field(ge=0.0, le=1.0)
    method: Literal["llm", "rule", "hybrid"]
    source_line_start: int
    source_line_end: int

    @model_validator(mode="after")
    def check_line_range(self) -> "KnowledgePoint":
        if self.source_line_end < self.source_line_start:
            raise ValueError("source_line_end must be >= source_line_start")
        return self


class ChapterWindow(BaseModel):
    chapter_id: str
    chapter_title: str
    text: str
    line_start: int
    line_end: int
