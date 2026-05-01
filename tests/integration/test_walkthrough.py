"""Walkthrough tests — verify every registered endpoint responds correctly."""

import httpx
import pytest


@pytest.mark.asyncio
async def test_health(client: httpx.AsyncClient) -> None:
    """GET /health returns 200 with status=healthy."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "version" in data


@pytest.mark.asyncio
async def test_extract_text_mode(client: httpx.AsyncClient) -> None:
    """POST /extract with .txt file (mode=text) returns extracted text."""
    resp = await client.post(
        "/extract",
        files={"file": ("sample.txt", b"Hello walkthrough", "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["format"] == "text"
    assert "Hello walkthrough" in data["text"]
    assert data["char_count"] > 0
    assert data["extraction_time_ms"] >= 0


@pytest.mark.asyncio
async def test_extract_structured_mode(client: httpx.AsyncClient) -> None:
    """POST /extract with .txt file (mode=structured) returns paragraph metadata."""
    resp = await client.post(
        "/extract",
        params={"mode": "structured"},
        files={"file": ("sample.txt", b"Hello walkthrough", "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["format"] == "text"
    assert "paragraphs" in data
    assert isinstance(data["paragraphs"], list)
    assert data["paragraph_count"] >= 1


@pytest.mark.asyncio
async def test_structure(client: httpx.AsyncClient) -> None:
    """POST /structure on text with chapter headings returns chapter tree."""
    text = "第一章 引言\n引言内容。\n1.1 背景\n背景信息。\n第二章 方法\n方法描述。"
    resp = await client.post(
        "/structure",
        files={"file": ("chapters.txt", text.encode(), "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["format"] == "text"
    assert "chapters" in data
    assert "detection_stats" in data
    assert data["detection_stats"]["method"] in ("hybrid", "rule_only")


@pytest.mark.asyncio
async def test_knowledge(client: httpx.AsyncClient) -> None:
    """POST /knowledge on text with chapter headings returns knowledge points."""
    text = (
        "第一章 引言\n实数包括有理数和无理数。\n函数是一种特殊的对应关系。\n"
        "第二章 代数\n一元二次方程的一般形式为 ax²+bx+c=0。"
    )
    resp = await client.post(
        "/knowledge",
        files={"file": ("knowledge.txt", text.encode(), "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["format"] == "text"
    assert "knowledge_points" in data
    assert "extraction_stats" in data
    assert data["extraction_stats"]["method"] in ("hybrid", "rule_only", "llm_only", "none")
