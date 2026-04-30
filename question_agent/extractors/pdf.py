"""PDF text extractor using pdfplumber."""

import io
from collections import Counter
from typing import Any

import pdfplumber

from question_agent.extractors.exceptions import ExtractionError

# y-coordinate tolerance for grouping chars into the same line (in points)
LINE_Y_TOLERANCE = 4


def _chars_to_lines(chars: list[dict[str, Any]], page_number: int) -> list[dict[str, Any]]:
    """Group page.chars into lines and compute per-line font metadata."""
    if not chars:
        return []

    # Sort by top (y) then x0 (left-to-right)
    chars = sorted(chars, key=lambda c: (c.get("top", 0), c.get("x0", 0)))

    lines: list[dict[str, Any]] = []
    current_line: list[dict[str, Any]] = []
    current_top = chars[0].get("top", 0)

    for c in chars:
        top = c.get("top", 0)
        if abs(top - current_top) > LINE_Y_TOLERANCE:
            lines.append(_build_line(current_line, page_number))
            current_line = [c]
            current_top = top
        else:
            current_line.append(c)

    if current_line:
        lines.append(_build_line(current_line, page_number))

    return [ln for ln in lines if ln["text"].strip()]


def _build_line(chars: list[dict[str, Any]], page_number: int) -> dict[str, Any]:
    """Compute metadata for a single line from its characters."""
    text = "".join(c.get("text", "") for c in chars)
    sizes = [round(c.get("size", 0), 1) for c in chars if c.get("size")]
    fontnames = [c.get("fontname", "") for c in chars]
    x0_values = [c.get("x0", 0) for c in chars]

    font_size = round(Counter(sizes).most_common(1)[0][0], 1) if sizes else None
    is_bold = any("Bold" in fn for fn in fontnames) if fontnames else None
    x0 = round(min(x0_values), 1) if x0_values else None

    return {
        "text": text,
        "page_number": page_number,
        "font_size": font_size,
        "is_bold": is_bold,
        "x0": x0,
    }


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


def extract_pdf_structured(content: bytes) -> dict[str, Any]:
    """Extract structured paragraphs from PDF with font metadata per line.

    Uses page.chars to get char-level data, groups by y-proximity into lines,
    and computes font_size (mode), is_bold (fontname contains Bold), and x0.
    """
    try:
        pdf = pdfplumber.open(io.BytesIO(content))
    except Exception as e:
        detail = "File is not a valid PDF or is corrupted."
        if "password" in str(e).lower():
            detail = "PDF is password-protected and cannot be extracted."
        raise ExtractionError(detail, format="pdf") from e

    all_paragraphs: list[dict[str, Any]] = []
    warnings: list[str] = []
    total_pages = len(pdf.pages)

    for i, page in enumerate(pdf.pages):
        page_number = i + 1
        chars = page.chars
        if not chars:
            # Try extract_text as fallback — scanned page detection
            text = page.extract_text()
            if text:
                for line in text.split("\n"):
                    stripped = line.strip()
                    if stripped:
                        all_paragraphs.append(
                            {
                                "text": stripped,
                                "page_number": page_number,
                                "font_size": None,
                                "is_bold": None,
                                "x0": None,
                            }
                        )
            else:
                warnings.append(
                    f"Page {page_number}: no extractable text layer (likely scanned image)"
                )
            continue

        lines = _chars_to_lines(chars, page_number)
        all_paragraphs.extend(lines)

    pdf.close()

    char_count = sum(len(p["text"]) for p in all_paragraphs)

    return {
        "paragraphs": all_paragraphs,
        "char_count": char_count,
        "page_count": total_pages,
        "warnings": warnings or None,
    }
