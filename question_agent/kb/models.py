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


class Document(BaseModel):
    """A document uploaded to a knowledge base."""

    id: str
    kb_id: str
    filename: str
    format: str
    file_path: str
    char_count: int = Field(default=0, ge=0)
    status: str = "uploaded"
    error_message: str | None = None
    created_at: datetime


class KnowledgePoint(BaseModel):
    """A knowledge point extracted from a document."""

    id: str
    document_id: str
    kb_id: str
    name: str
    description: str
    tags_json: str
    confidence: float
    method: str
    chapter_id: str | None = None
    source_line_start: int = 0
    source_line_end: int = 0
    created_at: datetime


class DocumentUploadResponse(BaseModel):
    """Response for document upload with extraction results."""

    document: Document
    knowledge_point_count: int
    knowledge_points: list[KnowledgePoint]
