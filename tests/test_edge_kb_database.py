"""Edge case tests for knowledge base data model and database layer."""

import asyncio
from pathlib import Path

import pytest

from question_agent.kb.database import (
    close_db,
    create_document,
    create_kb,
    create_knowledge_points,
    get_db_conn,
    get_kb,
    init_db,
    list_documents,
    list_kbs,
    list_kbs_knowledge_points,
    update_document_status,
)
from question_agent.kb.models import Document, KnowledgeBase, KnowledgeBaseCreate, KnowledgePoint


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


class TestGetKb:
    async def test_get_kb_found(self) -> None:
        kb = await create_kb(KnowledgeBaseCreate(name="FindMe"))
        found = await get_kb(kb.id)
        assert found is not None
        assert found.name == "FindMe"

    async def test_get_kb_not_found(self) -> None:
        assert await get_kb("nonexistent") is None


class TestDocumentModel:
    def test_document_defaults(self) -> None:
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        doc = Document(
            id="d1",
            kb_id="kb1",
            filename="test.pdf",
            format="pdf",
            file_path="/tmp/test.pdf",
            created_at=now,
        )
        assert doc.char_count == 0
        assert doc.status == "uploaded"
        assert doc.error_message is None

    def test_document_with_all_fields(self) -> None:
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        doc = Document(
            id="d1",
            kb_id="kb1",
            filename="test.pdf",
            format="pdf",
            file_path="/tmp/test.pdf",
            char_count=5000,
            status="ready",
            error_message="none",
            created_at=now,
        )
        assert doc.char_count == 5000
        assert doc.status == "ready"


class TestDocumentDatabase:
    async def test_create_and_list_documents(self) -> None:
        kb = await create_kb(KnowledgeBaseCreate(name="DocTest"))
        doc = await create_document(
            kb_id=kb.id,
            filename="chapter1.pdf",
            fmt="pdf",
            file_path=f"data/kb/{kb.id}/chapter1.pdf",
            char_count=3000,
        )
        assert doc.kb_id == kb.id
        assert doc.filename == "chapter1.pdf"
        assert doc.format == "pdf"
        assert doc.char_count == 3000
        assert doc.status == "uploaded"

        docs = await list_documents(kb.id)
        assert len(docs) == 1
        assert docs[0].id == doc.id

    async def test_list_documents_empty(self) -> None:
        kb = await create_kb(KnowledgeBaseCreate(name="EmptyDocs"))
        docs = await list_documents(kb.id)
        assert docs == []

    async def test_list_documents_filters_by_kb(self) -> None:
        kb1 = await create_kb(KnowledgeBaseCreate(name="KB1"))
        kb2 = await create_kb(KnowledgeBaseCreate(name="KB2"))
        await create_document(kb_id=kb1.id, filename="a.pdf", fmt="pdf", file_path="/a")
        await create_document(kb_id=kb2.id, filename="b.pdf", fmt="pdf", file_path="/b")
        assert len(await list_documents(kb1.id)) == 1
        assert len(await list_documents(kb2.id)) == 1

    async def test_update_document_status(self) -> None:
        kb = await create_kb(KnowledgeBaseCreate(name="StatusTest"))
        doc = await create_document(
            kb_id=kb.id,
            filename="f.txt",
            fmt="text",
            file_path="/f",
        )
        assert doc.status == "uploaded"
        await update_document_status(doc.id, "processing")
        docs = await list_documents(kb.id)
        assert docs[0].status == "processing"

    async def test_update_document_status_with_error(self) -> None:
        kb = await create_kb(KnowledgeBaseCreate(name="ErrorTest"))
        doc = await create_document(
            kb_id=kb.id,
            filename="bad.pdf",
            fmt="pdf",
            file_path="/bad",
        )
        await update_document_status(doc.id, "failed", "Extraction error")
        docs = await list_documents(kb.id)
        assert docs[0].status == "failed"
        assert docs[0].error_message == "Extraction error"


class TestKnowledgePointModel:
    def test_kp_defaults(self) -> None:
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        kp = KnowledgePoint(
            id="kp1",
            document_id="d1",
            kb_id="kb1",
            name="函数概念",
            description="函数的定义与性质",
            tags_json='[{"value":"核心","category":"importance"}]',
            confidence=0.9,
            method="hybrid",
            created_at=now,
        )
        assert kp.chapter_id is None
        assert kp.source_line_start == 0
        assert kp.source_line_end == 0


class TestKnowledgePointDatabase:
    async def test_create_and_list_kps(self) -> None:
        kb = await create_kb(KnowledgeBaseCreate(name="KPTest"))
        doc = await create_document(
            kb_id=kb.id,
            filename="math.pdf",
            fmt="pdf",
            file_path="/math",
        )
        kps = await create_knowledge_points(
            kb_id=kb.id,
            document_id=doc.id,
            points=[
                {
                    "name": "函数概念",
                    "description": "函数的定义与性质",
                    "tags_json": '[{"value":"核心","category":"importance"}]',
                    "confidence": 0.9,
                    "method": "hybrid",
                },
            ],
        )
        assert len(kps) == 1
        assert kps[0].name == "函数概念"
        assert kps[0].kb_id == kb.id
        assert kps[0].document_id == doc.id

        listed = await list_kbs_knowledge_points(kb.id)
        assert len(listed) == 1
        assert listed[0].name == "函数概念"

    async def test_create_kps_batch(self) -> None:
        kb = await create_kb(KnowledgeBaseCreate(name="BatchKP"))
        doc = await create_document(
            kb_id=kb.id,
            filename="batch.pdf",
            fmt="pdf",
            file_path="/batch",
        )
        kps = await create_knowledge_points(
            kb_id=kb.id,
            document_id=doc.id,
            points=[{"name": f"KP-{i}", "description": f"Desc-{i}"} for i in range(3)],
        )
        assert len(kps) == 3
        listed = await list_kbs_knowledge_points(kb.id)
        assert len(listed) == 3

    async def test_list_kps_empty(self) -> None:
        kb = await create_kb(KnowledgeBaseCreate(name="EmptyKP"))
        assert await list_kbs_knowledge_points(kb.id) == []

    async def test_kps_with_chapter_and_lines(self) -> None:
        kb = await create_kb(KnowledgeBaseCreate(name="ChapterKP"))
        doc = await create_document(
            kb_id=kb.id,
            filename="ch.pdf",
            fmt="pdf",
            file_path="/ch",
        )
        kps = await create_knowledge_points(
            kb_id=kb.id,
            document_id=doc.id,
            points=[
                {
                    "name": "微积分基础",
                    "description": "极限与连续",
                    "chapter_id": "ch-1",
                    "source_line_start": 10,
                    "source_line_end": 50,
                }
            ],
        )
        assert kps[0].chapter_id == "ch-1"
        assert kps[0].source_line_start == 10
        assert kps[0].source_line_end == 50
