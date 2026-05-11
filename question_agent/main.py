"""FastAPI application entry point."""

import os
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, File, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette import status

from question_agent import __version__
from question_agent.chapters import build_chapter_tree, detect_chapters_hybrid
from question_agent.config import settings
from question_agent.extractors import (
    ExtractionError,
    extract_docx,
    extract_docx_structured,
    extract_pdf,
    extract_pdf_structured,
    extract_text,
    extract_text_structured,
)
from question_agent.knowledge import (
    ChapterWindow,
    build_chapter_windows,
    extract_knowledge_points_hybrid,
)
from question_agent.questions import generate_questions
from question_agent.questions.generator import _KpInput
from question_agent.questions.models import QuestionType

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB

SUPPORTED_FORMATS = {
    ".txt": "text",
    ".pdf": "pdf",
    ".docx": "docx",
}

MIME_TO_FORMAT = {
    "text/plain": "text",
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/octet-stream": None,  # ambiguous, fall back to extension
}


class ExtractResponse(BaseModel):
    format: str
    text: str
    char_count: int
    extraction_time_ms: float
    page_count: int | None = None
    paragraph_count: int | None = None
    table_count: int | None = None
    warnings: list[str] | None = None


class StructuredParagraph(BaseModel):
    text: str
    page_number: int | None = None
    font_size: float | None = None
    is_bold: bool | None = None
    x0: float | None = None
    style_name: str | None = None


class StructuredExtractResponse(BaseModel):
    format: str
    paragraphs: list[StructuredParagraph]
    char_count: int
    extraction_time_ms: float
    page_count: int | None = None
    paragraph_count: int | None = None
    table_count: int | None = None
    warnings: list[str] | None = None


class DetectionStats(BaseModel):
    total: int
    rule_detected: int
    llm_detected: int
    method: str  # "hybrid" | "rule_only"


class StructureResponse(BaseModel):
    format: str
    chapters: list[dict[str, Any]] | None = None
    detection_stats: DetectionStats


class KnowledgeTagResponse(BaseModel):
    value: str
    category: str


class KnowledgePointResponse(BaseModel):
    id: int
    name: str
    description: str
    tags: list[KnowledgeTagResponse]
    confidence: float
    method: str
    source_line_start: int
    source_line_end: int
    chapter_id: str | None = None


class KnowledgeExtractionStats(BaseModel):
    total: int
    rule_count: int
    llm_count: int
    method: str


class KnowledgeResponse(BaseModel):
    format: str
    chapters: list[dict[str, Any]] | None = None
    knowledge_points: list[KnowledgePointResponse]
    extraction_stats: KnowledgeExtractionStats


class KnowledgeTagInput(BaseModel):
    value: str
    category: str


class KnowledgePointInput(BaseModel):
    name: str
    description: str
    tags: list[KnowledgeTagInput]


class QuestionGenerateRequest(BaseModel):
    knowledge_points: list[KnowledgePointInput]


class QuestionOptionResponse(BaseModel):
    label: str
    text: str


class QuestionStemResponse(BaseModel):
    id: int
    stem_text: str
    options: list[QuestionOptionResponse]
    knowledge_point_name: str
    question_type: QuestionType
    status: str
    error: str | None = None
    metadata: dict[str, Any] | None = None


class QuestionGenerationStats(BaseModel):
    total: int
    successful: int
    failed: int


class QuestionGenerateResponse(BaseModel):
    questions: list[QuestionStemResponse]
    generation_stats: QuestionGenerationStats


class QuestionFromFileResponse(BaseModel):
    format: str
    chapters: list[dict[str, Any]] | None = None
    knowledge_points: list[KnowledgePointResponse]
    questions: list[QuestionStemResponse]
    generation_stats: QuestionGenerationStats


LEGACY_EXTENSIONS = {
    ".doc": (
        "Legacy .doc format is not supported. "
        "Please convert to .docx using Microsoft Word or LibreOffice."
    ),
}


def _detect_format(filename: str, content_type: str | None) -> str | None:
    """Detect file format from extension and MIME type.  Returns None for unknown/legacy formats."""
    if content_type and content_type in MIME_TO_FORMAT:
        fmt = MIME_TO_FORMAT[content_type]
        if fmt is not None:
            return fmt

    ext = os.path.splitext(filename)[1].lower()
    if ext in LEGACY_EXTENSIONS:
        return None
    return SUPPORTED_FORMATS.get(ext)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — startup and shutdown events."""
    yield


app = FastAPI(
    title="AI 智能出题智能体",
    description=(
        "基于 GLM-5 的智能出题引擎 — 支持知识点抽取、题干生成、干扰项构建、答案解析与质量评估"
    ),
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.api_route("/health", methods=["GET", "HEAD"])
async def health_check() -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse(
        content={
            "status": "healthy",
            "version": __version__,
        }
    )


@app.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket) -> None:
    """WebSocket echo endpoint for chat prototyping."""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            content = data.get("content", "")
            await websocket.send_json({"type": "message", "content": content})
    except WebSocketDisconnect:
        pass


@app.post("/extract")
async def extract_unified(
    file: UploadFile = File(...),
    mode: str = Query("text", pattern="^(text|structured)$"),
) -> JSONResponse:
    """Unified extraction endpoint — auto-detects format and extracts text.

    Query params:
        mode: "text" (default) for flat text, "structured" for per-paragraph metadata.
    """
    t0 = time.perf_counter()
    filename = file.filename or ""
    fmt = _detect_format(filename, file.content_type)

    if fmt is None:
        ext = os.path.splitext(filename)[1].lower()
        legacy_hint = LEGACY_EXTENSIONS.get(ext, "")
        supported = ", ".join(SUPPORTED_FORMATS.keys())
        detail = f"Unsupported file format. Supported extensions: {supported}"
        if legacy_hint:
            detail = f"{detail}. {legacy_hint}"
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )

    content = await file.read()

    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds 50 MB limit.",
        )

    if mode == "structured":
        return await _extract_structured(fmt, content, t0)
    return await _extract_text_mode(fmt, content, t0)


async def _extract_text_mode(fmt: str, content: bytes, t0: float) -> JSONResponse:
    """Extract flat text (mode=text, default)."""
    if fmt == "text":
        text = extract_text(content)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        return JSONResponse(
            content=ExtractResponse(
                format="text",
                text=text,
                char_count=len(text),
                extraction_time_ms=round(elapsed_ms, 2),
            ).model_dump()
        )

    elif fmt == "pdf":
        try:
            result = extract_pdf(content)
        except ExtractionError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e),
            )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        return JSONResponse(
            content=ExtractResponse(
                format="pdf",
                text=result["text"],
                char_count=len(result["text"]),
                extraction_time_ms=round(elapsed_ms, 2),
                page_count=result["page_count"],
                warnings=result["warnings"],
            ).model_dump()
        )

    elif fmt == "docx":
        try:
            result = extract_docx(content)
        except ExtractionError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e),
            )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        return JSONResponse(
            content=ExtractResponse(
                format="docx",
                text=result["text"],
                char_count=len(result["text"]),
                extraction_time_ms=round(elapsed_ms, 2),
                paragraph_count=result["paragraph_count"],
                table_count=result["table_count"],
            ).model_dump()
        )

    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown format")


async def _extract_structured(fmt: str, content: bytes, t0: float) -> JSONResponse:
    """Extract structured paragraphs with font/style metadata (mode=structured)."""
    if fmt == "text":
        paragraphs, char_count = extract_text_structured(content)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        return JSONResponse(
            content=StructuredExtractResponse(
                format="text",
                paragraphs=[StructuredParagraph(**p) for p in paragraphs],
                char_count=char_count,
                extraction_time_ms=round(elapsed_ms, 2),
                paragraph_count=len(paragraphs),
            ).model_dump()
        )

    elif fmt == "pdf":
        try:
            result = extract_pdf_structured(content)
        except ExtractionError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e),
            )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        return JSONResponse(
            content=StructuredExtractResponse(
                format="pdf",
                paragraphs=[StructuredParagraph(**p) for p in result["paragraphs"]],
                char_count=result["char_count"],
                extraction_time_ms=round(elapsed_ms, 2),
                page_count=result["page_count"],
                warnings=result["warnings"],
            ).model_dump()
        )

    elif fmt == "docx":
        try:
            result = extract_docx_structured(content)
        except ExtractionError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e),
            )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        return JSONResponse(
            content=StructuredExtractResponse(
                format="docx",
                paragraphs=[StructuredParagraph(**p) for p in result["paragraphs"]],
                char_count=result["char_count"],
                extraction_time_ms=round(elapsed_ms, 2),
                paragraph_count=result["paragraph_count"],
                table_count=result["table_count"],
            ).model_dump()
        )

    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown format")


@app.post("/structure")
async def structure_endpoint(file: UploadFile = File(...)) -> JSONResponse:
    """Extract chapter structure from a document.

    Full pipeline: extract paragraphs → detect chapters → build tree.
    """
    filename = file.filename or ""
    fmt = _detect_format(filename, file.content_type)

    if fmt is None:
        ext = os.path.splitext(filename)[1].lower()
        legacy_hint = LEGACY_EXTENSIONS.get(ext, "")
        supported = ", ".join(SUPPORTED_FORMATS.keys())
        detail = f"Unsupported file format. Supported extensions: {supported}"
        if legacy_hint:
            detail = f"{detail}. {legacy_hint}"
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )

    content = await file.read()

    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds 50 MB limit.",
        )

    # Step 1: Extract structured paragraphs
    if fmt == "text":
        paragraphs_list, _ = extract_text_structured(content)
        page_map = None
    elif fmt == "pdf":
        try:
            result = extract_pdf_structured(content)
        except ExtractionError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e),
            )
        paragraphs_list = result["paragraphs"]
        # Re-index: paragraphs_list items may not have line_index; add it
        for i, p in enumerate(paragraphs_list):
            p["line_index"] = i
        page_map = {
            p["line_index"]: p["page_number"] for p in paragraphs_list if p.get("page_number")
        }
    elif fmt == "docx":
        try:
            result = extract_docx_structured(content)
        except ExtractionError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e),
            )
        paragraphs_list = result["paragraphs"]
        page_map = None
        for i, p in enumerate(paragraphs_list):
            p["line_index"] = i
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown format"
        )

    # Step 2: Detect chapters
    detection = detect_chapters_hybrid(paragraphs_list)
    headings = detection["headings"]
    chapters_tree = None

    if headings:
        # Build per-line page map for PDF
        line_page_map: dict[int, int] | None = None
        if page_map:
            line_page_map = {}
            for i, p in enumerate(paragraphs_list):
                pn = p.get("page_number")
                if pn is not None:
                    line_page_map[i] = pn

        tree = build_chapter_tree(headings, len(paragraphs_list), line_page_map)
        chapters_tree = [n.to_dict() for n in tree]

    stats = DetectionStats(
        total=detection["rule_count"] + detection["llm_count"],
        rule_detected=detection["rule_count"],
        llm_detected=detection["llm_count"],
        method=detection["detection_method"],
    )

    return JSONResponse(
        content=StructureResponse(
            format=fmt,
            chapters=chapters_tree,
            detection_stats=stats,
        ).model_dump()
    )


@app.post("/knowledge")
async def knowledge_endpoint(file: UploadFile = File(...)) -> JSONResponse:
    """Extract knowledge points from a document.

    Full pipeline: extract paragraphs → detect chapters → build windows →
    extract knowledge points (rule + LLM hybrid).
    """
    filename = file.filename or ""
    fmt = _detect_format(filename, file.content_type)

    if fmt is None:
        ext = os.path.splitext(filename)[1].lower()
        legacy_hint = LEGACY_EXTENSIONS.get(ext, "")
        supported = ", ".join(SUPPORTED_FORMATS.keys())
        detail = f"Unsupported file format. Supported extensions: {supported}"
        if legacy_hint:
            detail = f"{detail}. {legacy_hint}"
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )

    content = await file.read()

    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds 50 MB limit.",
        )

    # Step 1: Extract structured paragraphs
    if fmt == "text":
        paragraphs_list, _ = extract_text_structured(content)
        page_map = None
    elif fmt == "pdf":
        try:
            result = extract_pdf_structured(content)
        except ExtractionError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e),
            )
        paragraphs_list = result["paragraphs"]
        for i, p in enumerate(paragraphs_list):
            p["line_index"] = i
        page_map = {
            p["line_index"]: p["page_number"] for p in paragraphs_list if p.get("page_number")
        }
    elif fmt == "docx":
        try:
            result = extract_docx_structured(content)
        except ExtractionError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e),
            )
        paragraphs_list = result["paragraphs"]
        page_map = None
        for i, p in enumerate(paragraphs_list):
            p["line_index"] = i
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown format"
        )

    # Step 2: Detect chapters (reuse /structure logic)
    detection = detect_chapters_hybrid(paragraphs_list)
    headings = detection["headings"]
    chapters_tree = None
    chapter_nodes = []

    if headings:
        line_page_map: dict[int, int] | None = None
        if page_map:
            line_page_map = {}
            for i, p in enumerate(paragraphs_list):
                pn = p.get("page_number")
                if pn is not None:
                    line_page_map[i] = pn

        chapter_nodes = build_chapter_tree(headings, len(paragraphs_list), line_page_map)
        chapters_tree = [n.to_dict() for n in chapter_nodes]

    # Step 3: Build chapter windows
    if chapter_nodes:
        windows = build_chapter_windows(chapter_nodes, paragraphs_list)
    else:
        # No chapters — treat entire document as one window
        all_text = "\n".join(p.get("text") or "" for p in paragraphs_list)
        windows = (
            [
                ChapterWindow(
                    chapter_id="doc_full",
                    chapter_title="Full Document",
                    text=all_text,
                    line_start=0,
                    line_end=len(paragraphs_list),
                )
            ]
            if all_text.strip()
            else []
        )

    # Step 4: Extract knowledge points
    kp_result = extract_knowledge_points_hybrid(windows, paragraphs_list)

    # Step 5: Build response with chapter_id association
    # Map source_line ranges to chapter_id
    line_to_chapter: dict[int, str] = {}
    if chapter_nodes:
        for node in chapter_nodes:
            for li in range(node.start_line, node.end_line):
                line_to_chapter[li] = node.id

    kp_responses: list[KnowledgePointResponse] = []
    for kp in kp_result["knowledge_points"]:
        # Find chapter_id by checking any line in the KP's range
        ch_id: str | None = None
        for li in range(kp.source_line_start, kp.source_line_end):
            if li in line_to_chapter:
                ch_id = line_to_chapter[li]
                break
        kp_responses.append(
            KnowledgePointResponse(
                id=kp.id,
                name=kp.name,
                description=kp.description,
                tags=[KnowledgeTagResponse(value=t.value, category=t.category) for t in kp.tags],
                confidence=kp.confidence,
                method=kp.method,
                source_line_start=kp.source_line_start,
                source_line_end=kp.source_line_end,
                chapter_id=ch_id,
            )
        )

    return JSONResponse(
        content=KnowledgeResponse(
            format=fmt,
            chapters=chapters_tree,
            knowledge_points=kp_responses,
            extraction_stats=KnowledgeExtractionStats(
                total=len(kp_responses),
                rule_count=kp_result["rule_count"],
                llm_count=kp_result["llm_count"],
                method=kp_result["detection_method"],
            ),
        ).model_dump()
    )


@app.post("/questions/generate")
async def questions_generate(request: QuestionGenerateRequest) -> JSONResponse:
    """Generate questions from a list of knowledge points.

    Uses GLM-5 to generate question stems; marks failures with
    status="failed" and tracks generation statistics.
    """
    kp_inputs = [
        _KpInput(
            name=kp.name,
            description=kp.description,
            tags=[{"value": t.value, "category": t.category} for t in kp.tags],
        )
        for kp in request.knowledge_points
    ]

    questions, gen_stats = await generate_questions(kp_inputs)

    return JSONResponse(
        content=QuestionGenerateResponse(
            questions=[
                QuestionStemResponse(
                    id=q.id,
                    stem_text=q.stem_text,
                    options=[QuestionOptionResponse(label=o.label, text=o.text) for o in q.options],
                    knowledge_point_name=q.knowledge_point_name,
                    question_type=q.question_type,
                    status=q.status,
                    error=q.error,
                    metadata=q.metadata,
                )
                for q in questions
            ],
            generation_stats=QuestionGenerationStats(
                total=gen_stats.total, successful=gen_stats.successful, failed=gen_stats.failed
            ),
        ).model_dump()
    )


@app.post("/questions/generate/from-file")
async def questions_generate_from_file(file: UploadFile = File(...)) -> JSONResponse:
    """Generate questions from an uploaded document.

    Full pipeline: extract paragraphs → detect chapters → build windows →
    extract knowledge points → generate question stems.
    """
    filename = file.filename or ""
    fmt = _detect_format(filename, file.content_type)

    if fmt is None:
        ext = os.path.splitext(filename)[1].lower()
        legacy_hint = LEGACY_EXTENSIONS.get(ext, "")
        supported = ", ".join(SUPPORTED_FORMATS.keys())
        detail = f"Unsupported file format. Supported extensions: {supported}"
        if legacy_hint:
            detail = f"{detail}. {legacy_hint}"
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )

    content = await file.read()

    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds 50 MB limit.",
        )

    # Step 1: Extract structured paragraphs
    if fmt == "text":
        paragraphs_list, _ = extract_text_structured(content)
        page_map = None
    elif fmt == "pdf":
        try:
            result = extract_pdf_structured(content)
        except ExtractionError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e),
            )
        paragraphs_list = result["paragraphs"]
        for i, p in enumerate(paragraphs_list):
            p["line_index"] = i
        page_map = {
            p["line_index"]: p["page_number"] for p in paragraphs_list if p.get("page_number")
        }
    elif fmt == "docx":
        try:
            result = extract_docx_structured(content)
        except ExtractionError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e),
            )
        paragraphs_list = result["paragraphs"]
        page_map = None
        for i, p in enumerate(paragraphs_list):
            p["line_index"] = i
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown format"
        )

    # Step 2: Detect chapters
    detection = detect_chapters_hybrid(paragraphs_list)
    headings = detection["headings"]
    chapters_tree = None
    chapter_nodes = []

    if headings:
        line_page_map: dict[int, int] | None = None
        if page_map:
            line_page_map = {}
            for i, p in enumerate(paragraphs_list):
                pn = p.get("page_number")
                if pn is not None:
                    line_page_map[i] = pn

        chapter_nodes = build_chapter_tree(headings, len(paragraphs_list), line_page_map)
        chapters_tree = [n.to_dict() for n in chapter_nodes]

    # Step 3: Build chapter windows
    if chapter_nodes:
        windows = build_chapter_windows(chapter_nodes, paragraphs_list)
    else:
        all_text = "\n".join(p.get("text") or "" for p in paragraphs_list)
        windows = (
            [
                ChapterWindow(
                    chapter_id="doc_full",
                    chapter_title="Full Document",
                    text=all_text,
                    line_start=0,
                    line_end=len(paragraphs_list),
                )
            ]
            if all_text.strip()
            else []
        )

    # Step 4: Extract knowledge points
    kp_result = extract_knowledge_points_hybrid(windows, paragraphs_list)

    # Step 5: Map knowledge points to chapter_ids
    line_to_chapter: dict[int, str] = {}
    if chapter_nodes:
        for node in chapter_nodes:
            for li in range(node.start_line, node.end_line):
                line_to_chapter[li] = node.id

    kp_responses: list[KnowledgePointResponse] = []
    for kp in kp_result["knowledge_points"]:
        ch_id: str | None = None
        for li in range(kp.source_line_start, kp.source_line_end):
            if li in line_to_chapter:
                ch_id = line_to_chapter[li]
                break
        kp_responses.append(
            KnowledgePointResponse(
                id=kp.id,
                name=kp.name,
                description=kp.description,
                tags=[KnowledgeTagResponse(value=t.value, category=t.category) for t in kp.tags],
                confidence=kp.confidence,
                method=kp.method,
                source_line_start=kp.source_line_start,
                source_line_end=kp.source_line_end,
                chapter_id=ch_id,
            )
        )

    # Step 6: Generate questions from extracted knowledge points
    kp_inputs = [
        _KpInput(
            name=kp.name,
            description=kp.description,
            tags=[{"value": t.value, "category": t.category} for t in kp.tags],
        )
        for kp in kp_result["knowledge_points"]
    ]
    questions, gen_stats = await generate_questions(kp_inputs)

    return JSONResponse(
        content=QuestionFromFileResponse(
            format=fmt,
            chapters=chapters_tree,
            knowledge_points=kp_responses,
            questions=[
                QuestionStemResponse(
                    id=q.id,
                    stem_text=q.stem_text,
                    options=[QuestionOptionResponse(label=o.label, text=o.text) for o in q.options],
                    knowledge_point_name=q.knowledge_point_name,
                    question_type=q.question_type,
                    status=q.status,
                    error=q.error,
                    metadata=q.metadata,
                )
                for q in questions
            ],
            generation_stats=QuestionGenerationStats(
                total=gen_stats.total, successful=gen_stats.successful, failed=gen_stats.failed
            ),
        ).model_dump()
    )


def main() -> None:
    """Entry point for `question-agent` CLI script."""
    import uvicorn

    uvicorn.run(
        "question_agent.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
