"""Plain text extractor."""


def extract_text(content: bytes) -> str:
    """Decode bytes as UTF-8 text, replacing any undecodable characters."""
    return content.decode("utf-8", errors="replace")
