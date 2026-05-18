"""Async SQLite storage for knowledge bases."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TypedDict
from uuid import uuid4

import aiosqlite

from question_agent.config import settings
from question_agent.kb.models import Document, KnowledgeBase, KnowledgeBaseCreate, KnowledgePoint

_conn: aiosqlite.Connection | None = None
_lock = asyncio.Lock()


async def get_db_conn() -> aiosqlite.Connection:
    """Return a singleton aiosqlite connection for the KB database."""
    global _conn  # noqa: PLW0603
    async with _lock:
        if _conn is None:
            db_path = settings.kb_db_path
            db_path.parent.mkdir(parents=True, exist_ok=True)
            _conn = await aiosqlite.connect(str(db_path))
            _conn.row_factory = aiosqlite.Row
            await _conn.execute("PRAGMA journal_mode=WAL")
            await _conn.execute("PRAGMA foreign_keys=ON")
    return _conn


async def init_db() -> None:
    """Create all KB tables if they do not exist."""
    conn = await get_db_conn()
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS knowledge_bases (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            subject TEXT,
            grade_level TEXT,
            document_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            kb_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            format TEXT NOT NULL,
            file_path TEXT NOT NULL,
            char_count INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'uploaded',
            error_message TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (kb_id) REFERENCES knowledge_bases(id)
        )
        """
    )
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS knowledge_points (
            id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            kb_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            tags_json TEXT NOT NULL DEFAULT '[]',
            confidence REAL NOT NULL DEFAULT 0.0,
            method TEXT NOT NULL,
            chapter_id TEXT,
            source_line_start INTEGER NOT NULL DEFAULT 0,
            source_line_end INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (document_id) REFERENCES documents(id),
            FOREIGN KEY (kb_id) REFERENCES knowledge_bases(id)
        )
        """
    )
    await conn.commit()


async def close_db() -> None:
    """Close the database connection."""
    global _conn  # noqa: PLW0603
    async with _lock:
        if _conn is not None:
            await _conn.close()
            _conn = None


def _row_to_kb(row: aiosqlite.Row) -> KnowledgeBase:
    """Convert a database row to a KnowledgeBase model."""
    return KnowledgeBase(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        subject=row["subject"],
        grade_level=row["grade_level"],
        document_count=row["document_count"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def _row_to_document(row: aiosqlite.Row) -> Document:
    """Convert a database row to a Document model."""
    return Document(
        id=row["id"],
        kb_id=row["kb_id"],
        filename=row["filename"],
        format=row["format"],
        file_path=row["file_path"],
        char_count=row["char_count"],
        status=row["status"],
        error_message=row["error_message"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _row_to_kp(row: aiosqlite.Row) -> KnowledgePoint:
    """Convert a database row to a KnowledgePoint model."""
    return KnowledgePoint(
        id=row["id"],
        document_id=row["document_id"],
        kb_id=row["kb_id"],
        name=row["name"],
        description=row["description"],
        tags_json=row["tags_json"],
        confidence=row["confidence"],
        method=row["method"],
        chapter_id=row["chapter_id"],
        source_line_start=row["source_line_start"],
        source_line_end=row["source_line_end"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )


async def create_kb(data: KnowledgeBaseCreate) -> KnowledgeBase:
    """Insert a new knowledge base and return it."""
    now = datetime.now(UTC)
    kb = KnowledgeBase(
        id=uuid4().hex,
        name=data.name,
        description=data.description,
        subject=data.subject,
        grade_level=data.grade_level,
        document_count=0,
        created_at=now,
        updated_at=now,
    )
    conn = await get_db_conn()
    await conn.execute(
        """
        INSERT INTO knowledge_bases
            (id, name, description, subject, grade_level, document_count, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            kb.id,
            kb.name,
            kb.description,
            kb.subject,
            kb.grade_level,
            kb.document_count,
            kb.created_at.isoformat(),
            kb.updated_at.isoformat(),
        ),
    )
    await conn.commit()
    return kb


async def list_kbs() -> list[KnowledgeBase]:
    """Return all knowledge bases ordered by creation time descending."""
    conn = await get_db_conn()
    cursor = await conn.execute(
        "SELECT id, name, description, subject, grade_level, "
        "document_count, created_at, updated_at "
        "FROM knowledge_bases ORDER BY created_at DESC"
    )
    rows = await cursor.fetchall()
    return [_row_to_kb(row) for row in rows]


async def get_kb(kb_id: str) -> KnowledgeBase | None:
    """Return a knowledge base by ID, or None if not found."""
    conn = await get_db_conn()
    cursor = await conn.execute(
        "SELECT id, name, description, subject, grade_level, "
        "document_count, created_at, updated_at "
        "FROM knowledge_bases WHERE id = ?",
        (kb_id,),
    )
    row = await cursor.fetchone()
    return _row_to_kb(row) if row else None


async def create_document(
    kb_id: str,
    filename: str,
    fmt: str,
    file_path: str,
    char_count: int = 0,
) -> Document:
    """Insert a new document record and return it."""
    now = datetime.now(UTC)
    doc = Document(
        id=uuid4().hex,
        kb_id=kb_id,
        filename=filename,
        format=fmt,
        file_path=file_path,
        char_count=char_count,
        status="uploaded",
        created_at=now,
    )
    conn = await get_db_conn()
    await conn.execute(
        """
        INSERT INTO documents
            (id, kb_id, filename, format, file_path, char_count, status, error_message, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            doc.id,
            doc.kb_id,
            doc.filename,
            doc.format,
            doc.file_path,
            doc.char_count,
            doc.status,
            doc.error_message,
            doc.created_at.isoformat(),
        ),
    )
    await conn.commit()
    return doc


async def list_documents(kb_id: str) -> list[Document]:
    """Return all documents in a knowledge base ordered by creation time."""
    conn = await get_db_conn()
    cursor = await conn.execute(
        "SELECT id, kb_id, filename, format, file_path, char_count, "
        "status, error_message, created_at "
        "FROM documents WHERE kb_id = ? ORDER BY created_at DESC",
        (kb_id,),
    )
    rows = await cursor.fetchall()
    return [_row_to_document(row) for row in rows]


async def update_document_status(
    doc_id: str, status: str, error_message: str | None = None
) -> None:
    """Update a document's processing status."""
    conn = await get_db_conn()
    await conn.execute(
        "UPDATE documents SET status = ?, error_message = ? WHERE id = ?",
        (status, error_message, doc_id),
    )
    await conn.commit()


async def increment_kb_document_count(kb_id: str) -> None:
    """Increment the document_count of a knowledge base by 1."""
    conn = await get_db_conn()
    await conn.execute(
        "UPDATE knowledge_bases SET document_count = document_count + 1, "
        "updated_at = ? WHERE id = ?",
        (datetime.now(UTC).isoformat(), kb_id),
    )
    await conn.commit()


class KnowledgePointInput(TypedDict, total=False):
    """Input dict for batch knowledge point creation."""

    name: str
    description: str
    tags_json: str
    confidence: float
    method: str
    chapter_id: str
    source_line_start: int
    source_line_end: int


async def create_knowledge_points(
    kb_id: str,
    document_id: str,
    points: list[KnowledgePointInput],
) -> list[KnowledgePoint]:
    """Batch-insert knowledge points and return them."""
    conn = await get_db_conn()
    now = datetime.now(UTC)
    created: list[KnowledgePoint] = []
    for pt in points:
        chapter_id_val = pt.get("chapter_id")
        kp = KnowledgePoint(
            id=uuid4().hex,
            document_id=document_id,
            kb_id=kb_id,
            name=pt["name"],
            description=pt["description"],
            tags_json=pt.get("tags_json", "[]"),
            confidence=pt.get("confidence", 0.0),
            method=pt.get("method", "unknown"),
            chapter_id=chapter_id_val if chapter_id_val else None,
            source_line_start=pt.get("source_line_start", 0),
            source_line_end=pt.get("source_line_end", 0),
            created_at=now,
        )
        await conn.execute(
            """
            INSERT INTO knowledge_points
                (id, document_id, kb_id, name, description, tags_json,
                 confidence, method, chapter_id, source_line_start, source_line_end, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                kp.id,
                kp.document_id,
                kp.kb_id,
                kp.name,
                kp.description,
                kp.tags_json,
                kp.confidence,
                kp.method,
                kp.chapter_id,
                kp.source_line_start,
                kp.source_line_end,
                kp.created_at.isoformat(),
            ),
        )
        created.append(kp)
    await conn.commit()
    return created


async def list_kbs_knowledge_points(kb_id: str) -> list[KnowledgePoint]:
    """Return all knowledge points in a knowledge base ordered by creation time."""
    conn = await get_db_conn()
    cursor = await conn.execute(
        "SELECT id, document_id, kb_id, name, description, tags_json, "
        "confidence, method, chapter_id, source_line_start, source_line_end, created_at "
        "FROM knowledge_points WHERE kb_id = ? ORDER BY created_at",
        (kb_id,),
    )
    rows = await cursor.fetchall()
    return [_row_to_kp(row) for row in rows]


async def delete_kb(kb_id: str) -> bool:
    """Delete a knowledge base and all its documents and knowledge points.

    Also removes associated files on disk. Returns True if the KB existed
    and was deleted, False if not found.
    """
    import shutil

    from question_agent.config import settings

    conn = await get_db_conn()
    cursor = await conn.execute("SELECT id FROM knowledge_bases WHERE id = ?", (kb_id,))
    if await cursor.fetchone() is None:
        return False

    # Cascade delete: knowledge_points → documents → knowledge_bases
    await conn.execute("DELETE FROM knowledge_points WHERE kb_id = ?", (kb_id,))
    await conn.execute("DELETE FROM documents WHERE kb_id = ?", (kb_id,))
    await conn.execute("DELETE FROM knowledge_bases WHERE id = ?", (kb_id,))
    await conn.commit()

    # Remove files on disk
    kb_dir = settings.kb_db_path.parent / kb_id
    if kb_dir.is_dir():
        shutil.rmtree(kb_dir, ignore_errors=True)

    return True
