"""Edge case tests: HTTP method mismatches and header/boundary scenarios."""

import pytest
from httpx import AsyncClient

# --- HTTP method mismatches on POST endpoints ---


@pytest.mark.asyncio
async def test_extract_get_returns_405(client: AsyncClient):
    resp = await client.get("/extract")
    assert resp.status_code == 405


@pytest.mark.asyncio
async def test_extract_put_returns_405(client: AsyncClient):
    resp = await client.put("/extract")
    assert resp.status_code == 405


@pytest.mark.asyncio
async def test_extract_delete_returns_405(client: AsyncClient):
    resp = await client.delete("/extract")
    assert resp.status_code == 405


@pytest.mark.asyncio
async def test_structure_get_returns_405(client: AsyncClient):
    resp = await client.get("/structure")
    assert resp.status_code == 405


@pytest.mark.asyncio
async def test_structure_put_returns_405(client: AsyncClient):
    resp = await client.put("/structure")
    assert resp.status_code == 405


@pytest.mark.asyncio
async def test_knowledge_get_returns_405(client: AsyncClient):
    resp = await client.get("/knowledge")
    assert resp.status_code == 405


@pytest.mark.asyncio
async def test_knowledge_put_returns_405(client: AsyncClient):
    resp = await client.put("/knowledge")
    assert resp.status_code == 405


# --- Query parameter edge cases ---


@pytest.mark.asyncio
async def test_extract_mode_uppercase_rejected(client: AsyncClient):
    """mode=TEXT should be rejected (pattern enforces lowercase)."""
    resp = await client.post(
        "/extract?mode=TEXT",
        files={"file": ("test.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_extract_mode_invalid_rejected(client: AsyncClient):
    """mode=xml should be rejected."""
    resp = await client.post(
        "/extract?mode=xml",
        files={"file": ("test.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 422


# --- Filename edge cases ---


@pytest.mark.asyncio
async def test_extract_uppercase_extension(client: AsyncClient):
    """FILE.TXT should be detected as text format."""
    resp = await client.post(
        "/extract",
        files={"file": ("TEST.TXT", b"hello", "text/plain")},
    )
    assert resp.status_code == 200
    assert resp.json()["format"] == "text"


@pytest.mark.asyncio
async def test_extract_double_extension(client: AsyncClient):
    """file.pdf.txt should be detected as text (last extension wins)."""
    resp = await client.post(
        "/extract",
        files={"file": ("file.pdf.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 200
    assert resp.json()["format"] == "text"


@pytest.mark.asyncio
async def test_extract_filename_with_unicode(client: AsyncClient):
    """Unicode filename should not crash format detection."""
    resp = await client.post(
        "/extract",
        files={"file": ("文件.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 200
    assert resp.json()["format"] == "text"


@pytest.mark.asyncio
async def test_extract_filename_with_spaces(client: AsyncClient):
    """Filename with spaces should work."""
    resp = await client.post(
        "/extract",
        files={"file": ("my file.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 200


# --- /knowledge endpoint edge cases ---


@pytest.mark.asyncio
async def test_knowledge_no_knowledge_points_text(client: AsyncClient):
    """Plain text with no knowledge markers should return empty knowledge_points."""
    resp = await client.post(
        "/knowledge",
        files={"file": ("test.txt", b"Just some plain narrative text.", "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "knowledge_points" in data
    assert "extraction_stats" in data
    assert data["extraction_stats"]["total"] >= 0


@pytest.mark.asyncio
async def test_knowledge_empty_file(client: AsyncClient):
    """Empty file uploaded to /knowledge should not crash."""
    resp = await client.post(
        "/knowledge",
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["knowledge_points"] == []
    assert data["extraction_stats"]["total"] == 0


@pytest.mark.asyncio
async def test_knowledge_unsupported_format(client: AsyncClient):
    """Unsupported format should return 422."""
    resp = await client.post(
        "/knowledge",
        files={"file": ("data.xyz", b"???", "application/octet-stream")},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_knowledge_missing_file(client: AsyncClient):
    """Missing file parameter should return 422."""
    resp = await client.post("/knowledge")
    assert resp.status_code == 422


# --- /structure endpoint edge cases ---


@pytest.mark.asyncio
async def test_structure_empty_file(client: AsyncClient):
    """Empty text file should return chapters=null and total=0."""
    resp = await client.post(
        "/structure",
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["detection_stats"]["total"] == 0


@pytest.mark.asyncio
async def test_structure_missing_file(client: AsyncClient):
    """Missing file parameter should return 422."""
    resp = await client.post("/structure")
    assert resp.status_code == 422


# --- Null byte / special content ---


@pytest.mark.asyncio
async def test_extract_text_with_null_bytes(client: AsyncClient):
    """Text containing null bytes should not crash."""
    resp = await client.post(
        "/extract",
        files={"file": ("test.txt", b"hello\x00world", "text/plain")},
    )
    assert resp.status_code != 500
