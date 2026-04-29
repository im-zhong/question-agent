"""Tests for F-2: 纯文本文件上传与读取."""

import httpx
import pytest

BASE = "http://localhost:8000"


@pytest.mark.asyncio
async def test_extract_text_returns_content():
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/extract/text",
            files={"file": ("sample.txt", b"Hello World!", "text/plain")},
        )
        assert resp.status_code == 200
        assert resp.json()["text"] == "Hello World!"


@pytest.mark.asyncio
async def test_extract_text_rejects_non_text_mime():
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/extract/text",
            files={"file": ("data.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_extract_text_empty_file():
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/extract/text",
            files={"file": ("empty.txt", b"", "text/plain")},
        )
        assert resp.status_code == 200
        assert resp.json()["text"] == ""


@pytest.mark.asyncio
async def test_extract_text_missing_file_returns_422():
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BASE}/extract/text")
        assert resp.status_code == 422
