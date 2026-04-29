"""FastAPI application entry point."""

import os
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette import status

from question_agent import __version__
from question_agent.config import settings
from question_agent.extractors import ExtractionError, extract_docx, extract_pdf, extract_text

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
async def extract_unified(file: UploadFile = File(...)) -> JSONResponse:
    """Unified extraction endpoint — auto-detects format and extracts text."""
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
