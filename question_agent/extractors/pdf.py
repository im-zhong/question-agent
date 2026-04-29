"""PDF text extractor using pdfplumber."""

import io
from typing import Any

import pdfplumber

from question_agent.extractors.exceptions import ExtractionError


def extract_pdf(content: bytes) -> dict[str, Any]:
    """Extract text from PDF bytes.  Returns dict with text, page_count, warnings."""
    try:
        pdf = pdfplumber.open(io.BytesIO(content))
    except Exception as e:
        detail = "File is not a valid PDF or is corrupted."
        if "password" in str(e).lower():
            detail = "PDF is password-protected and cannot be extracted."
        raise ExtractionError(detail, format="pdf") from e

    pages = []
    warnings: list[str] = []
    total_pages = len(pdf.pages)
    for i, page in enumerate(pdf.pages):
        text = page.extract_text(layout=True)
        if text:
            pages.append(text)
        else:
            warnings.append(f"Page {i + 1}: no extractable text layer (likely scanned image)")

    pdf.close()

    return {
        "text": "\n--- PAGE BREAK ---\n".join(pages),
        "page_count": total_pages,
        "warnings": warnings or None,
    }
