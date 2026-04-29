"""Word .docx text extractor using python-docx."""

import io
from typing import Any

import docx

from question_agent.extractors.exceptions import ExtractionError


def extract_docx(content: bytes) -> dict[str, Any]:
    """Extract text from .docx bytes.  Returns dict with text, paragraph_count, table_count."""
    try:
        document = docx.Document(io.BytesIO(content))
    except Exception as e:
        raise ExtractionError(
            "File is not a valid .docx document. "
            "Legacy .doc files are not supported — please convert to .docx first.",
            format="docx",
        ) from e

    paragraphs: list[str] = []
    for para in document.paragraphs:
        style = para.style.name if para.style and para.style.name != "Normal" else None
        prefix = f"[{style}] " if style else ""
        t = para.text.strip()
        if t:
            paragraphs.append(f"{prefix}{t}")

    table_texts: list[str] = []
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                table_texts.append(" | ".join(cells))

    parts = []
    if paragraphs:
        parts.append("\n".join(paragraphs))
    if table_texts:
        parts.append("\n\n[Tables]\n" + "\n".join(table_texts))

    return {
        "text": "\n\n".join(parts) if parts else "",
        "paragraph_count": len(paragraphs),
        "table_count": len(document.tables),
    }
