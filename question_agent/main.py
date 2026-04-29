"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette import status

from question_agent import __version__
from question_agent.config import settings

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — startup and shutdown events."""
    # Startup
    yield
    # Shutdown


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


@app.get("/health")
async def health_check() -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse(
        content={
            "status": "healthy",
            "version": __version__,
        }
    )


@app.post("/extract/text")
async def extract_text(file: UploadFile = File(...)) -> JSONResponse:
    """Extract plain text from an uploaded .txt file."""
    if file.content_type and not file.content_type.startswith("text/"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only text/plain files are accepted.",
        )

    content = await file.read()

    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds 50 MB limit.",
        )

    text = content.decode("utf-8")
    return JSONResponse(content={"text": text})


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
