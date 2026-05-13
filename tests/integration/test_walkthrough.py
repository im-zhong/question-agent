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


@pytest.mark.asyncio
async def test_questions_generate(client: httpx.AsyncClient) -> None:
    """POST /questions/generate returns placeholder questions for knowledge points."""
    resp = await client.post(
        "/questions/generate",
        json={
            "knowledge_points": [
                {
                    "name": "牛顿第二定律",
                    "description": "力等于质量乘以加速度",
                    "tags": [{"value": "牛顿第二定律", "category": "formula"}],
                }
            ]
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "questions" in data
    assert len(data["questions"]) == 1
    q = data["questions"][0]
    assert q["knowledge_point_name"] == "牛顿第二定律"
    assert q["question_type"] == "calculation"
    assert len(q["options"]) == 4


@pytest.mark.asyncio
async def test_questions_generate_from_file(client: httpx.AsyncClient) -> None:
    """POST /questions/generate/from-file runs full pipeline and returns questions."""
    text = (
        "第一章 力学\n牛顿第二定律描述了力等于质量乘以加速度。\n"
        "加速度是速度变化量与时间的比值。\n"
        "第二章 电磁学\n欧姆定律表明电流等于电压除以电阻。"
    )
    resp = await client.post(
        "/questions/generate/from-file",
        files={"file": ("physics.txt", text.encode(), "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["format"] == "text"
    assert "chapters" in data
    assert "knowledge_points" in data
    assert "questions" in data
    assert "generation_stats" in data


@pytest.mark.asyncio
async def test_knowledge_bases_crud(client: httpx.AsyncClient) -> None:
    """POST/GET /v1/knowledge-bases creates and lists knowledge bases (direct backend path)."""
    resp = await client.post(
        "/v1/knowledge-bases",
        json={"name": "Walkthrough KB", "subject": "数学", "grade_level": "高中"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Walkthrough KB"
    assert data["subject"] == "数学"
    assert "id" in data

    resp = await client.get("/v1/knowledge-bases")
    assert resp.status_code == 200
    kbs = resp.json()
    assert isinstance(kbs, list)
    assert any(kb["name"] == "Walkthrough KB" for kb in kbs)


@pytest.mark.asyncio
async def test_kb_document_upload_and_list(client: httpx.AsyncClient) -> None:
    """POST .../documents uploads a file and GET lists it (direct backend)."""
    # Create a KB
    resp = await client.post(
        "/v1/knowledge-bases",
        json={"name": "Upload Walkthrough KB"},
    )
    assert resp.status_code == 201
    kb_id = resp.json()["id"]

    # Upload a text file
    text = "实数包括有理数和无理数。函数是一种特殊的对应关系。"
    resp = await client.post(
        f"/v1/knowledge-bases/{kb_id}/documents",
        files={"file": ("math.txt", text.encode(), "text/plain")},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "document" in data
    assert data["document"]["filename"] == "math.txt"
    assert data["document"]["format"] == "text"
    assert data["document"]["status"] == "ready"
    assert "knowledge_point_count" in data

    # List documents
    resp = await client.get(f"/v1/knowledge-bases/{kb_id}/documents")
    assert resp.status_code == 200
    docs = resp.json()
    assert isinstance(docs, list)
    assert len(docs) >= 1
    assert docs[0]["filename"] == "math.txt"


@pytest.mark.asyncio
async def test_kb_knowledge_points_list(client: httpx.AsyncClient) -> None:
    """GET .../knowledge-points returns KPs after upload (direct backend)."""
    # Create a KB and upload
    resp = await client.post(
        "/v1/knowledge-bases",
        json={"name": "KP Walkthrough KB"},
    )
    kb_id = resp.json()["id"]

    text = "第一章 力学\n牛顿第二定律描述了力等于质量乘以加速度。\n加速度是速度变化量与时间的比值。"
    resp = await client.post(
        f"/v1/knowledge-bases/{kb_id}/documents",
        files={"file": ("physics.txt", text.encode(), "text/plain")},
    )
    assert resp.status_code == 201

    # List knowledge points
    resp = await client.get(f"/v1/knowledge-bases/{kb_id}/knowledge-points")
    assert resp.status_code == 200
    kps = resp.json()
    assert isinstance(kps, list)
