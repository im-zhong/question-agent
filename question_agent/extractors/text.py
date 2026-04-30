"""Plain text extractor."""

from typing import Any


def extract_text(content: bytes) -> str:
    """Decode bytes as UTF-8 text, replacing any undecodable characters."""
    return content.decode("utf-8", errors="replace")


def extract_text_structured(content: bytes) -> tuple[list[dict[str, Any]], int]:
    """Extract text as structured paragraphs — one per non-empty line.

    Returns (paragraphs, char_count). All font fields are None for plain text.
    """
    decoded = content.decode("utf-8", errors="replace")
    paragraphs = [{"text": line.strip()} for line in decoded.split("\n") if line.strip()]
    if not paragraphs:
        paragraphs = [{"text": decoded}] if decoded.strip() else []
    char_count = sum(len(p["text"]) for p in paragraphs)
    return paragraphs, char_count
