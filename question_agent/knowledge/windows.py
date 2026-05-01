"""Chapter text window builder for knowledge point extraction."""

from typing import Any

from question_agent.chapters.tree import ChapterNode
from question_agent.knowledge.models import ChapterWindow


def build_chapter_windows(
    chapter_nodes: list[ChapterNode],
    paragraphs: list[dict[str, Any]],
    max_chars: int = 3000,
) -> list[ChapterWindow]:
    """Build text windows from chapter nodes for knowledge point extraction.

    Each chapter node produces one or more windows. If a chapter's text exceeds
    max_chars, it is split at paragraph boundaries (never mid-paragraph).
    Empty chapters (no paragraph text) are skipped.

    Args:
        chapter_nodes: List of ChapterNode objects with start_line/end_line.
        paragraphs: Flat list of paragraph dicts, each with a "text" key.
        max_chars: Maximum characters per window. Default 3000.

    Returns:
        List of ChapterWindow objects ready for LLM processing.
    """
    if not chapter_nodes or not paragraphs:
        return []

    windows: list[ChapterWindow] = []

    for node in chapter_nodes:
        # Slice paragraphs belonging to this chapter
        node_paragraphs = paragraphs[node.start_line : node.end_line]
        texts = [p.get("text") or "" for p in node_paragraphs]

        total_len = sum(len(t) for t in texts)
        if total_len == 0:
            continue

        if total_len <= max_chars:
            # Fits in a single window
            combined = "\n".join(t for t in texts if t)
            windows.append(
                ChapterWindow(
                    chapter_id=node.id,
                    chapter_title=node.title,
                    text=combined,
                    line_start=node.start_line,
                    line_end=node.end_line,
                )
            )
        else:
            # Split at paragraph boundaries
            _split_into_windows(node, texts, max_chars, windows)

    return windows


def _split_into_windows(
    node: ChapterNode,
    texts: list[str],
    max_chars: int,
    windows: list[ChapterWindow],
) -> None:
    """Split a large chapter's paragraphs into multiple windows."""
    chunk_texts: list[str] = []
    chunk_len = 0
    chunk_first_idx = 0
    chunk_last_idx = 0

    for i, text in enumerate(texts):
        if not text:
            continue

        text_len = len(text)

        # If adding this paragraph would exceed max_chars AND we already have
        # content, flush the current chunk first
        if chunk_len > 0 and chunk_len + text_len + len(chunk_texts) > max_chars:
            _flush_chunk(node, chunk_texts, chunk_first_idx, chunk_last_idx, windows)
            chunk_texts = []
            chunk_len = 0
            chunk_first_idx = i

        # Single paragraph exceeding max_chars gets its own window
        chunk_texts.append(text)
        chunk_len += text_len
        chunk_last_idx = i

    # Flush remaining
    if chunk_texts:
        _flush_chunk(node, chunk_texts, chunk_first_idx, chunk_last_idx, windows)


def _flush_chunk(
    node: ChapterNode,
    chunk_texts: list[str],
    first_idx: int,
    last_idx: int,
    windows: list[ChapterWindow],
) -> None:
    """Append a single window from accumulated chunk texts."""
    windows.append(
        ChapterWindow(
            chapter_id=node.id,
            chapter_title=node.title,
            text="\n".join(chunk_texts),
            line_start=node.start_line + first_idx,
            line_end=node.start_line + last_idx + 1,
        )
    )
