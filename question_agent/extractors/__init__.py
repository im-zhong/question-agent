"""Text extraction modules for .txt, .pdf, and .docx formats."""

from question_agent.extractors.docx import extract_docx
from question_agent.extractors.exceptions import ExtractionError
from question_agent.extractors.pdf import extract_pdf
from question_agent.extractors.text import extract_text

__all__ = ["extract_text", "extract_pdf", "extract_docx", "ExtractionError"]
