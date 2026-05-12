"""Async SQLite storage for knowledge bases."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import aiosqlite

from question_agent.config import settings
from question_agent.kb.models import KnowledgeBase, KnowledgeBaseCreate

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
    """Create the knowledge_bases table if it does not exist."""
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
