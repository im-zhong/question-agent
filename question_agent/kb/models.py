"""Pydantic models for knowledge base."""

from datetime import datetime

from pydantic import BaseModel, Field


class KnowledgeBase(BaseModel):
    """A knowledge base that holds documents and extracted knowledge points."""

    id: str
    name: str
    description: str | None = None
    subject: str | None = None
    grade_level: str | None = None
    document_count: int = Field(default=0, ge=0)
    created_at: datetime
    updated_at: datetime


class KnowledgeBaseCreate(BaseModel):
    """Schema for creating a new knowledge base."""

    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    subject: str | None = None
    grade_level: str | None = None
