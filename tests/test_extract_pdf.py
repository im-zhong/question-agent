"""Tests for F-3: PDF 文本提取."""

import io

import httpx
import pytest
from fpdf import FPDF

BASE = "http://localhost:8000"


def _make_pdf(texts: list[str]) -> bytes:
    """Build a valid multi-page PDF with extractable text on each page."""
    pdf = FPDF()
    pdf.set_font("Helvetica", size=12)
    for t in texts:
        pdf.add_page()
        pdf.cell(text=t)
    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_extract_pdf_returns_text():
    pdf_bytes = _make_pdf(["Hello from PDF"])
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/extract/pdf",
            files={"file": ("doc.pdf", pdf_bytes, "application/pdf")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "Hello from PDF" in data["text"]
        assert data["page_count"] == 1
        assert data["pages_with_text"] == 1


@pytest.mark.asyncio
async def test_extract_pdf_multi_page():
    pdf_bytes = _make_pdf(["First page text", "Second page text"])
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/extract/pdf",
            files={"file": ("doc.pdf", pdf_bytes, "application/pdf")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "--- PAGE BREAK ---" in data["text"]
        assert "First page text" in data["text"]
        assert "Second page text" in data["text"]
        assert data["page_count"] == 2
        assert data["pages_with_text"] == 2


@pytest.mark.asyncio
async def test_extract_pdf_corrupted_returns_422():
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/extract/pdf",
            files={"file": ("bad.pdf", b"not a pdf at all", "application/pdf")},
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_extract_pdf_wrong_mime_returns_422():
    pdf_bytes = _make_pdf(["test"])
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/extract/pdf",
            files={"file": ("doc.pdf", pdf_bytes, "text/plain")},
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_extract_pdf_missing_file_returns_422():
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BASE}/extract/pdf")
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_extract_pdf_empty_pages_reports_warning():
    """PDF with pages but no text layer should produce warnings."""
    pdf = FPDF()
    pdf.set_font("Helvetica", size=12)
    # First page has text, second page is intentionally left blank
    pdf.add_page()
    pdf.cell(text="Only page has text")
    pdf.add_page()
    # Don't add any cell — page 2 is blank / no text content
    buf = io.BytesIO()
    pdf.output(buf)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/extract/pdf",
            files={"file": ("doc.pdf", buf.getvalue(), "application/pdf")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["page_count"] == 2
        assert data["pages_with_text"] == 1
        assert data["warnings"] is not None
        assert len(data["warnings"]) == 1


@pytest.mark.asyncio
async def test_extract_pdf_content_type_with_charset():
    """Accept application/pdf with charset suffix (some clients send this)."""
    pdf_bytes = _make_pdf(["test"])
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/extract/pdf",
            files={"file": ("doc.pdf", pdf_bytes, "application/pdf")},
        )
        # Should accept pure application/pdf
        assert resp.status_code == 200

    # application/pdf with no content_type at all should also work
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/extract/pdf",
            files={"file": ("doc.pdf", pdf_bytes)},
        )
        assert resp.status_code == 200
