"""FastAPI application entry point."""

import os
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette import status

from question_agent import __version__
from question_agent.chapters import detect_chapters_hybrid
from question_agent.chapters.tree import build_chapter_tree
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
