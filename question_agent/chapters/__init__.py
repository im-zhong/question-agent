"""Chapter detection package."""

from question_agent.chapters.detector import detect_chapters
from question_agent.chapters.hybrid import detect_chapters_hybrid
from question_agent.chapters.llm import LlmChapterResult, detect_chapters_llm
from question_agent.chapters.models import ChapterHeading
from question_agent.chapters.tree import ChapterNode, build_chapter_tree

__all__ = [
    "ChapterHeading",
    "ChapterNode",
    "LlmChapterResult",
    "build_chapter_tree",
    "detect_chapters",
    "detect_chapters_hybrid",
    "detect_chapters_llm",
]
