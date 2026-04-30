"""Chapter detection package."""

from question_agent.chapters.detector import detect_chapters
from question_agent.chapters.models import ChapterHeading

__all__ = ["ChapterHeading", "detect_chapters"]
