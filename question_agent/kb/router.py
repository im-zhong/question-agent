"""FastAPI router for knowledge base endpoints."""

from __future__ import annotations

import json
import os
import pathlib
import uuid
from typing import Any

from fastapi import APIRouter, File, HTTPException, Response, UploadFile
from starlette import status

from question_agent.chapters import build_chapter_tree, detect_chapters_hybrid
from question_agent.config import settings
from question_agent.extractors import (
    ExtractionError,
    extract_docx_structured,
    extract_pdf_structured,
    extract_text_structured,
)
from question_agent.kb import create_kb, list_kbs
from question_agent.kb.database import (
    KnowledgePointInput,
    create_document,
    create_knowledge_points,
    get_kb,
    increment_kb_document_count,
    list_documents,
    list_kbs_knowledge_points,
    update_document_status,
)
from question_agent.kb.models import (
    Document,
    DocumentUploadResponse,
    KnowledgeBase,
    KnowledgeBaseCreate,
    KnowledgePoint,
)
from question_agent.knowledge import (
    ChapterWindow,
    build_chapter_windows,
    extract_knowledge_points_hybrid,
)

router = APIRouter(prefix="/v1/knowledge-bases", tags=["knowledge-bases"])

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB

SUPPORTED_FORMATS = {".txt": "text", ".pdf": "pdf", ".docx": "docx"}

MIME_TO_FORMAT = {
    "text/plain": "text",
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/octet-stream": None,
}


def _detect_format(filename: str, content_type: str | None) -> str | None:
    """Detect file format from extension and MIME type."""
    if content_type and content_type in MIME_TO_FORMAT:
        fmt = MIME_TO_FORMAT[content_type]
        if fmt is not None:
            return fmt
    ext = os.path.splitext(filename)[1].lower()
    return SUPPORTED_FORMATS.get(ext)


def _extract_paragraphs(
    fmt: str, content: bytes
) -> tuple[list[dict[str, Any]], dict[int, int] | None]:
    """Extract structured paragraphs and optional page map from file content."""
    page_map: dict[int, int] | None = None
    if fmt == "text":
        paragraphs_list, _ = extract_text_structured(content)
    elif fmt == "pdf":
        result = extract_pdf_structured(content)
        paragraphs_list = result["paragraphs"]
        for i, p in enumerate(paragraphs_list):
            p["line_index"] = i
        page_map = {
            int(p["line_index"]): int(p["page_number"])
            for p in paragraphs_list
            if p.get("page_number") is not None
        }
    elif fmt == "docx":
        result = extract_docx_structured(content)
        paragraphs_list = result["paragraphs"]
        for i, p in enumerate(paragraphs_list):
            p["line_index"] = i
    else:
        raise ValueError(f"Unknown format: {fmt}")
    return paragraphs_list, page_map


def _build_windows(
    paragraphs_list: list[dict[str, Any]],
    page_map: dict[int, int] | None,
) -> tuple[list[ChapterWindow], list[Any]]:
    """Detect chapters and build chapter windows from paragraphs.

    Returns (windows, chapter_nodes) so callers can reuse chapter_nodes
    for chapter_id mapping without re-running detection.
    """
    detection = detect_chapters_hybrid(paragraphs_list)
    headings = detection["headings"]
    chapter_nodes: list[Any] = []

    if headings:
        line_page_map: dict[int, int] | None = None
        if page_map:
            line_page_map = {}
            for i, p in enumerate(paragraphs_list):
                pn = p.get("page_number")
                if pn is not None:
                    line_page_map[i] = int(pn)
        chapter_nodes = build_chapter_tree(headings, len(paragraphs_list), line_page_map)

    if chapter_nodes:
        return build_chapter_windows(chapter_nodes, paragraphs_list), chapter_nodes

    all_text = "\n".join(str(p.get("text") or "") for p in paragraphs_list)
    if not all_text.strip():
        return [], []
    return [
        ChapterWindow(
            chapter_id="doc_full",
            chapter_title="Full Document",
            text=all_text,
            line_start=0,
            line_end=len(paragraphs_list),
        )
    ], []


@router.post("", status_code=201, response_model=KnowledgeBase)
async def create_knowledge_base(
    data: KnowledgeBaseCreate,
    response: Response,
) -> KnowledgeBase:
    """Create a new knowledge base."""
    kb = await create_kb(data)
    response.headers["Location"] = f"/v1/knowledge-bases/{kb.id}"
    return kb


@router.get("", response_model=list[KnowledgeBase])
async def list_knowledge_bases() -> list[KnowledgeBase]:
    """List all knowledge bases ordered by creation time descending."""
    return await list_kbs()


@router.post("/{kb_id}/documents", status_code=201, response_model=DocumentUploadResponse)
async def upload_document(
    kb_id: str,
    file: UploadFile = File(...),
) -> DocumentUploadResponse:
    """Upload a document to a knowledge base and run extraction pipeline."""
    kb = await get_kb(kb_id)
    if kb is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )

    filename = file.filename or ""
    fmt = _detect_format(filename, file.content_type)
    if fmt is None:
        supported = ", ".join(SUPPORTED_FORMATS.keys())
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file format. Supported extensions: {supported}",
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds 50 MB limit.",
        )

    save_dir = settings.kb_db_path.parent / kb_id
    save_dir.mkdir(parents=True, exist_ok=True)
    safe_name = pathlib.PurePosixPath(filename).name
    safe_filename = f"{uuid.uuid4().hex}_{safe_name}"
    file_path = save_dir / safe_filename
    file_path.write_bytes(content)

    # Extract paragraphs to get accurate char_count
    try:
        paragraphs_list, page_map = _extract_paragraphs(fmt, content)
    except ExtractionError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    char_count = sum(len(str(p.get("text") or "")) for p in paragraphs_list)

    doc = await create_document(
        kb_id=kb_id,
        filename=filename,
        fmt=fmt,
        file_path=str(file_path),
        char_count=char_count,
    )
    await update_document_status(doc.id, "processing")

    try:
        windows, chapter_nodes = _build_windows(paragraphs_list, page_map)
        kp_result = extract_knowledge_points_hybrid(windows, paragraphs_list)

        line_to_chapter: dict[int, str] = {}
        for node in chapter_nodes:
            for li in range(node.start_line, node.end_line):
                line_to_chapter[li] = node.id

        kp_inputs: list[KnowledgePointInput] = []
        for kp in kp_result["knowledge_points"]:
            ch_id: str | None = None
            for li in range(kp.source_line_start, kp.source_line_end):
                if li in line_to_chapter:
                    ch_id = line_to_chapter[li]
                    break
            kp_input: KnowledgePointInput = {
                "name": kp.name,
                "description": kp.description,
                "tags_json": json.dumps(
                    [{"value": t.value, "category": t.category} for t in kp.tags]
                ),
                "confidence": kp.confidence,
                "method": kp.method,
                "source_line_start": kp.source_line_start,
                "source_line_end": kp.source_line_end,
            }
            if ch_id:
                kp_input["chapter_id"] = ch_id
            kp_inputs.append(kp_input)

        created_kps = await create_knowledge_points(kb_id, doc.id, kp_inputs)
    except ExtractionError as e:
        await update_document_status(doc.id, "failed", str(e))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception:
        await update_document_status(doc.id, "failed", "Knowledge point extraction failed")
        raise

    await update_document_status(doc.id, "ready")
    await increment_kb_document_count(kb_id)
    updated_doc = Document(
        id=doc.id,
        kb_id=doc.kb_id,
        filename=doc.filename,
        format=doc.format,
        file_path=doc.file_path,
        char_count=doc.char_count,
        status="ready",
        error_message=None,
        created_at=doc.created_at,
    )
    return DocumentUploadResponse(
        document=updated_doc,
        knowledge_point_count=len(created_kps),
        knowledge_points=created_kps,
    )


@router.get("/{kb_id}/documents", response_model=list[Document])
async def list_kb_documents(kb_id: str) -> list[Document]:
    """List all documents in a knowledge base."""
    kb = await get_kb(kb_id)
    if kb is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )
    return await list_documents(kb_id)


@router.get("/{kb_id}/knowledge-points", response_model=list[KnowledgePoint])
async def list_kb_knowledge_points(kb_id: str) -> list[KnowledgePoint]:
    """List all knowledge points in a knowledge base."""
    kb = await get_kb(kb_id)
    if kb is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )
    return await list_kbs_knowledge_points(kb_id)
