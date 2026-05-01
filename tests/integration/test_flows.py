"""End-to-end flow tests — verify the full business pipeline works."""

from pathlib import Path

import httpx
import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.mark.asyncio
async def test_extract_then_structure_then_knowledge(
    client: httpx.AsyncClient,
) -> None:
    """Full pipeline: same document through extract → structure → knowledge."""
    sample = FIXTURES_DIR / "sample_chapter.txt"
    content = sample.read_bytes()

    # Step 1: Extract raw text
    resp_extract = await client.post(
        "/extract",
        files={"file": ("sample_chapter.txt", content, "text/plain")},
    )
    assert resp_extract.status_code == 200
    extract_data = resp_extract.json()
    assert extract_data["format"] == "text"
    assert extract_data["char_count"] > 0

    # Step 2: Structure detection
    resp_structure = await client.post(
        "/structure",
        files={"file": ("sample_chapter.txt", content, "text/plain")},
    )
    assert resp_structure.status_code == 200
    structure_data = resp_structure.json()
    assert structure_data["format"] == "text"
    assert structure_data["chapters"] is not None
    assert len(structure_data["chapters"]) >= 2  # at least 第一章 and 第二章

    # Step 3: Knowledge extraction
    resp_knowledge = await client.post(
        "/knowledge",
        files={"file": ("sample_chapter.txt", content, "text/plain")},
    )
    assert resp_knowledge.status_code == 200
    knowledge_data = resp_knowledge.json()
    assert knowledge_data["format"] == "text"
    assert isinstance(knowledge_data["knowledge_points"], list)
    assert "extraction_stats" in knowledge_data


@pytest.mark.asyncio
async def test_chapters_consistent_across_endpoints(
    client: httpx.AsyncClient,
) -> None:
    """Chapters detected by /structure match those in /knowledge response."""
    sample = FIXTURES_DIR / "sample_chapter.txt"
    content = sample.read_bytes()

    resp_structure = await client.post(
        "/structure",
        files={"file": ("sample_chapter.txt", content, "text/plain")},
    )
    resp_knowledge = await client.post(
        "/knowledge",
        files={"file": ("sample_chapter.txt", content, "text/plain")},
    )
    assert resp_structure.status_code == 200
    assert resp_knowledge.status_code == 200

    structure_chapters = resp_structure.json().get("chapters") or []
    knowledge_chapters = resp_knowledge.json().get("chapters") or []

    structure_titles = {ch["title"] for ch in structure_chapters}
    knowledge_titles = {ch["title"] for ch in knowledge_chapters}
    assert structure_titles == knowledge_titles
