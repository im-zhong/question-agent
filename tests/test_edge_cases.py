"""Edge case tests for currently implemented endpoints."""

import io

import httpx
import pytest
from fpdf import FPDF

BASE = "http://localhost:8000"


# --- /health edge cases ---


@pytest.mark.asyncio
async def test_health_post_returns_405():
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BASE}/health")
        assert resp.status_code == 405


@pytest.mark.asyncio
async def test_health_head_returns_200():
    async with httpx.AsyncClient() as client:
        resp = await client.head(f"{BASE}/health")
        assert resp.status_code == 200


# --- /extract edge cases: text ---


@pytest.mark.asyncio
async def test_extract_text_gbk_encoding():
    gbk_bytes = "你好世界".encode("gbk")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/extract",
            files={"file": ("gbk.txt", gbk_bytes, "text/plain")},
        )
        assert resp.status_code != 500


@pytest.mark.asyncio
async def test_extract_text_with_bom():
    bom_text = b"\xef\xbb\xbfHello with BOM"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/extract",
            files={"file": ("bom.txt", bom_text, "text/plain")},
        )
        assert resp.status_code == 200
        text = resp.json()["text"]
        assert "﻿" not in text or text.startswith("﻿")


@pytest.mark.asyncio
async def test_extract_text_binary_content_disguised_as_text():
    binary = bytes(range(256)) * 100
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/extract",
            files={"file": ("fake.txt", binary, "text/plain")},
        )
        assert resp.status_code != 500


@pytest.mark.asyncio
async def test_extract_text_one_byte_file():
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/extract",
            files={"file": ("one.txt", b"A", "text/plain")},
        )
        assert resp.status_code == 200
        assert resp.json()["text"] == "A"


# --- /extract edge cases: pdf ---


@pytest.mark.asyncio
async def test_extract_pdf_empty_pdf():
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
            f"{BASE}/extract",
            files={"file": ("empty.pdf", zero_page_pdf, "application/pdf")},
        )
        assert resp.status_code != 500


@pytest.mark.asyncio
async def test_extract_pdf_large_valid_pdf():
    pdf = FPDF()
    pdf.set_font("Helvetica", size=12)
    for i in range(10):
        pdf.add_page()
        pdf.cell(text=f"Page {i + 1}")
    buf = io.BytesIO()
    pdf.output(buf)

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{BASE}/extract",
            files={"file": ("big.pdf", buf.getvalue(), "application/pdf")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["page_count"] == 10
