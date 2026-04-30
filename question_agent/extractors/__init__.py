"""Text extraction modules for .txt, .pdf, and .docx formats."""

from question_agent.extractors.docx import extract_docx, extract_docx_structured
from question_agent.extractors.exceptions import ExtractionError
from question_agent.extractors.pdf import extract_pdf, extract_pdf_structured
from question_agent.extractors.text import extract_text, extract_text_structured

__all__ = [
    "ExtractionError",
    "extract_text",
    "extract_text_structured",
    "extract_pdf",
    "extract_pdf_structured",
    "extract_docx",
    "extract_docx_structured",
]
