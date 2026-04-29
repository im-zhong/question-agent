"""Tests for text extraction via unified /extract endpoint."""

import httpx
import pytest

BASE = "http://localhost:8000"


@pytest.mark.asyncio
async def test_extract_text_returns_content():
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/extract",
            files={"file": ("sample.txt", b"Hello World!", "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["format"] == "text"
        assert data["text"] == "Hello World!"
        assert data["char_count"] == 12


@pytest.mark.asyncio
async def test_extract_text_empty_file():
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE}/extract",
            files={"file": ("empty.txt", b"", "text/plain")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["format"] == "text"
        assert data["text"] == ""
        assert data["char_count"] == 0


@pytest.mark.asyncio
async def test_extract_text_missing_file_returns_422():
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BASE}/extract")
        assert resp.status_code == 422
