"""FastAPI router for knowledge base endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Response

from question_agent.kb import create_kb, list_kbs
from question_agent.kb.models import KnowledgeBase, KnowledgeBaseCreate

router = APIRouter(prefix="/api/v1/knowledge-bases", tags=["knowledge-bases"])


@router.post("", status_code=201, response_model=KnowledgeBase)
async def create_knowledge_base(
    data: KnowledgeBaseCreate,
    response: Response,
) -> KnowledgeBase:
    """Create a new knowledge base."""
    kb = await create_kb(data)
    response.headers["Location"] = f"/api/v1/knowledge-bases/{kb.id}"
    return kb


@router.get("", response_model=list[KnowledgeBase])
async def list_knowledge_bases() -> list[KnowledgeBase]:
    """List all knowledge bases ordered by creation time descending."""
    return await list_kbs()
