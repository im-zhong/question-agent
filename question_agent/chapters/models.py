"""Pydantic models for chapter detection."""

from typing import Literal

from pydantic import BaseModel


class ChapterHeading(BaseModel):
    line_index: int
    level: int
    title: str
    confidence: float
    method: Literal["pattern", "style", "font"]
