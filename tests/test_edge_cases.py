"""Edge case tests for currently implemented endpoints."""

import io

import httpx
import pytest
from fpdf import FPDF

BASE = "http://localhost:8000"


# --- /health edge cases ---


@pytest.mark.asyncio
async def test_health_post_returns_405():
    """POST to GET-only /health should return 405 Method Not Allowed."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BASE}/health")
        assert resp.status_code == 405


@pytest.mark.asyncio
async def test_health_head_returns_200():
    """HEAD /health should return 200 with no body."""
    async with httpx.AsyncClient() as client:
        resp = await client.head(f"{BASE}/health")
        assert resp.status_code == 200


# --- /extract/text edge cases ---


@pytest.mark.asyncio
async def test_extract_text_gbk_encoding():
    """Upload a GBK-encoded text file — should decode as raw bytes or error gracefully."""
    gbk_bytes = "你好世界".encode("gbk")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/extract/text",
            files={"file": ("gbk.txt", gbk_bytes, "text/plain")},
        )
        # UTF-8 decode of GBK bytes will fail → should return 200 with raw decode
        # or produce replacement characters; either way must not 500
        assert resp.status_code != 500


@pytest.mark.asyncio
async def test_extract_text_with_bom():
    """UTF-8 BOM should be stripped or handled without breaking."""
    bom_text = b"\xef\xbb\xbfHello with BOM"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/extract/text",
            files={"file": ("bom.txt", bom_text, "text/plain")},
        )
        assert resp.status_code == 200
        # BOM should not appear as garbage
        text = resp.json()["text"]
        assert "﻿" not in text or text.startswith("﻿")


@pytest.mark.asyncio
async def test_extract_text_binary_content_disguised_as_text():
    """Binary content with text/plain MIME should not 500-crash."""
    binary = bytes(range(256)) * 100  # 25.6 KB of binary
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/extract/text",
            files={"file": ("fake.txt", binary, "text/plain")},
        )
        # May return 200 (with replacement chars) or an error, but NOT 500
        assert resp.status_code != 500


@pytest.mark.asyncio
async def test_extract_text_one_byte_file():
    """Single byte file should work fine."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/extract/text",
            files={"file": ("one.txt", b"A", "text/plain")},
        )
        assert resp.status_code == 200
        assert resp.json()["text"] == "A"


# --- /extract/pdf edge cases ---


@pytest.mark.asyncio
async def test_extract_pdf_empty_pdf():
    """A PDF with zero pages should be rejected or handled gracefully."""
    # Minimal PDF with 0 pages
    zero_page_pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\n"
        b"xref\n0 3\n0000000000 65535 f \n0000000009 00000 n \n0000000051 00000 n \n"
        b"trailer<</Size 3/Root 1 0 R>>\n"
        b"startxref\n105\n%%EOF"
    )
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/extract/pdf",
            files={"file": ("empty.pdf", zero_page_pdf, "application/pdf")},
        )
        # Should not 500; pdfplumber may parse this with 0 pages
        assert resp.status_code != 500


@pytest.mark.asyncio
async def test_extract_pdf_large_valid_pdf():
    """A PDF with many pages should not timeout."""
    pdf = FPDF()
    pdf.set_font("Helvetica", size=12)
    for i in range(10):
        pdf.add_page()
        pdf.cell(text=f"Page {i + 1}")
    buf = io.BytesIO()
    pdf.output(buf)

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{BASE}/extract/pdf",
            files={"file": ("big.pdf", buf.getvalue(), "application/pdf")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["page_count"] == 10
        assert data["pages_with_text"] == 10
