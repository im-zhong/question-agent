"""Edge case tests for knowledge base data model and database layer."""

import asyncio
from pathlib import Path

import pytest

from question_agent.kb.database import close_db, create_kb, get_db_conn, init_db, list_kbs
from question_agent.kb.models import KnowledgeBase, KnowledgeBaseCreate


@pytest.fixture(autouse=True)
async def _setup_and_teardown(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Use a temp DB for each test and clean up."""
    db_path = tmp_path / "test_kb.db"
    monkeypatch.setattr("question_agent.kb.database.settings.kb_db_path", db_path)
    await init_db()
    yield
    await close_db()


class TestKnowledgeBaseModel:
    def test_create_model_minimal(self) -> None:
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        kb = KnowledgeBase(id="abc123", name="Test KB", created_at=now, updated_at=now)
        assert kb.document_count == 0
        assert kb.description is None
        assert kb.subject is None
        assert kb.grade_level is None

    def test_create_model_validation_rejects_empty_name(self) -> None:
        with pytest.raises(Exception):
            KnowledgeBaseCreate(name="")

    def test_create_model_validation_rejects_name_too_long(self) -> None:
        with pytest.raises(Exception):
            KnowledgeBaseCreate(name="x" * 201)


class TestKbDatabaseCreateAndList:
    async def test_empty_db_returns_empty_list(self) -> None:
        result = await list_kbs()
        assert result == []

    async def test_create_and_list_roundtrip(self) -> None:
        kb = await create_kb(
            KnowledgeBaseCreate(name="数学知识库", description="高中数学", subject="数学")
        )
        assert kb.name == "数学知识库"
        assert kb.subject == "数学"
        assert kb.document_count == 0

        kbs = await list_kbs()
        assert len(kbs) == 1
        assert kbs[0].id == kb.id
        assert kbs[0].name == "数学知识库"

    async def test_create_multiple_returns_all_ordered_by_created_desc(self) -> None:
        await create_kb(KnowledgeBaseCreate(name="First"))
        await create_kb(KnowledgeBaseCreate(name="Second"))
        kbs = await list_kbs()
        assert len(kbs) == 2
        assert kbs[0].name == "Second"

    async def test_create_with_unicode_and_emoji(self) -> None:
        kb = await create_kb(
            KnowledgeBaseCreate(name="📚 数学知识库 🎓", description="包含公式: x²+y²=z²")
        )
        assert "📚" in kb.name
        assert "x²" in kb.description

    async def test_create_with_all_optional_fields(self) -> None:
        kb = await create_kb(
            KnowledgeBaseCreate(
                name="Full KB",
                description="Desc",
                subject="物理",
                grade_level="高中",
            )
        )
        assert kb.subject == "物理"
        assert kb.grade_level == "高中"


class TestKbDatabaseConcurrency:
    async def test_concurrent_creates_dont_corrupt(self) -> None:
        await asyncio.gather(*[create_kb(KnowledgeBaseCreate(name=f"KB-{i}")) for i in range(5)])
        kbs = await list_kbs()
        assert len(kbs) == 5

    async def test_get_db_conn_returns_same_instance(self) -> None:
        conn1 = await get_db_conn()
        conn2 = await get_db_conn()
        assert conn1 is conn2
