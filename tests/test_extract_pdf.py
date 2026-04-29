"""Tests for PDF text extraction via unified /extract endpoint."""

import io

import httpx
import pytest
from fpdf import FPDF

BASE = "http://localhost:8000"


def _make_pdf(texts: list[str]) -> bytes:
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
            f"{BASE}/extract",
            files={"file": ("doc.pdf", pdf_bytes, "application/pdf")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["format"] == "pdf"
        assert "Hello from PDF" in data["text"]
        assert data["page_count"] == 1


@pytest.mark.asyncio
async def test_extract_pdf_multi_page():
    pdf_bytes = _make_pdf(["First page text", "Second page text"])
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/extract",
            files={"file": ("doc.pdf", pdf_bytes, "application/pdf")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["format"] == "pdf"
        assert "--- PAGE BREAK ---" in data["text"]
        assert "First page text" in data["text"]
        assert "Second page text" in data["text"]
        assert data["page_count"] == 2


@pytest.mark.asyncio
async def test_extract_pdf_corrupted_returns_422():
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/extract",
            files={"file": ("bad.pdf", b"not a pdf at all", "application/pdf")},
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_extract_pdf_missing_file_returns_422():
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BASE}/extract")
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_extract_pdf_empty_pages_reports_warning():
    pdf = FPDF()
    pdf.set_font("Helvetica", size=12)
    pdf.add_page()
    pdf.cell(text="Only page has text")
    pdf.add_page()
    buf = io.BytesIO()
    pdf.output(buf)

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/extract",
            files={"file": ("doc.pdf", buf.getvalue(), "application/pdf")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["page_count"] == 2
        assert data["warnings"] is not None
        assert len(data["warnings"]) == 1
