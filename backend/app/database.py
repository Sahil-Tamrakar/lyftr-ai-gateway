"""Async SQLite storage for conversation messages.

The schema is fixed by the API contract:

    messages (id INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id TEXT NOT NULL,
              role TEXT NOT NULL,
              content TEXT NOT NULL,
              metadata TEXT,
              created_at TEXT NOT NULL)

System prompts are persisted as ``role='system'`` rows and hidden from the
public message listing.  Failed requests never reach this layer.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import aiosqlite

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_session_id_id
    ON messages (session_id, id);
"""


def sqlite_path_from_url(url: str) -> str:
    """Translate a ``sqlite:///`` URL into a filesystem path.

    Supports the SQLAlchemy conventions used by the project:
      * ``sqlite:////data/app.db`` -> ``/data/app.db`` (absolute)
      * ``sqlite:///./app.db``      -> ``./app.db`` (relative)
      * ``sqlite:///C:/tmp/app.db`` -> ``C:/tmp/app.db`` (Windows absolute)
    """

    url = url.strip()
    if not url.startswith("sqlite:"):
        raise ValueError("DATABASE_URL must use the sqlite: scheme")

    remainder = url[len("sqlite:") :].lstrip("/")
    # ``lstrip("/")`` handles sqlite:////abs by leaving "abs"; prefix the slash
    # back when the original URL used four slashes (absolute POSIX path).
    if url.startswith("sqlite:////"):
        remainder = "/" + remainder

    if remainder in ("", ":memory:"):
        return ":memory:"
    return remainder


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    """Small wrapper around a single aiosqlite connection."""

    def __init__(self, url: str) -> None:
        self.url = url
        self.path = sqlite_path_from_url(url)
        self._conn: aiosqlite.Connection | None = None
        self._write_lock = asyncio.Lock()

    # ------------------------------------------------------------------ setup
    async def connect(self) -> None:
        if self.path != ":memory:":
            parent = Path(self.path).expanduser().parent
            parent.mkdir(parents=True, exist_ok=True)

        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.execute("PRAGMA busy_timeout=5000")
        await self._conn.executescript(_SCHEMA)
        await self._conn.commit()
        logger.info("SQLite ready at %s", self.path)

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("database is not connected")
        return self._conn

    async def ping(self) -> None:
        async with self.conn.execute("SELECT 1") as cursor:
            await cursor.fetchone()

    # ------------------------------------------------------------------- read
    async def get_chat_history(self, session_id: str) -> list[aiosqlite.Row]:
        """Visible conversation turns, oldest first (system rows excluded)."""
        async with self.conn.execute(
            """
            SELECT id, role, content, metadata, created_at
            FROM messages
            WHERE session_id = ? AND role != 'system'
            ORDER BY id ASC
            """,
            (session_id,),
        ) as cursor:
            return list(await cursor.fetchall())

    async def list_sessions(self, limit: int = 50) -> list[aiosqlite.Row]:
        """Conversation summaries, most recently active first.

        The title is the first visible user message; hidden ``system`` rows are
        counted neither in ``message_count`` nor as the title.
        """
        async with self.conn.execute(
            """
            SELECT
                m.session_id,
                COALESCE(
                    (
                        SELECT content FROM messages t
                        WHERE t.session_id = m.session_id AND t.role = 'user'
                        ORDER BY t.id ASC
                        LIMIT 1
                    ),
                    ''
                ) AS title,
                (
                    SELECT content FROM messages s
                    WHERE s.session_id = m.session_id AND s.role = 'system'
                    ORDER BY s.id DESC
                    LIMIT 1
                ) AS system_prompt,
                MAX(m.created_at) AS updated_at,
                COUNT(*) AS message_count,
                MAX(m.id) AS last_id
            FROM messages m
            WHERE m.role != 'system'
            GROUP BY m.session_id
            ORDER BY last_id DESC
            LIMIT ?
            """,
            (limit,),
        ) as cursor:
            return list(await cursor.fetchall())

    async def get_system_prompt(self, session_id: str) -> str | None:
        async with self.conn.execute(
            """
            SELECT content FROM messages
            WHERE session_id = ? AND role = 'system'
            ORDER BY id DESC
            LIMIT 1
            """,
            (session_id,),
        ) as cursor:
            row = await cursor.fetchone()
        return row["content"] if row else None

    # ------------------------------------------------------------------ write
    async def add_exchange(
        self,
        *,
        session_id: str,
        user_content: str,
        assistant_content: str,
        assistant_metadata: dict[str, Any],
        update_system_prompt: bool = False,
        system_prompt: str | None = None,
    ) -> None:
        """Persist one successful turn atomically.

        When ``update_system_prompt`` is set, any previous system prompt for the
        session is replaced (or cleared when ``system_prompt`` is falsy).
        """
        now = _utc_now()
        async with self._write_lock:
            try:
                if update_system_prompt:
                    await self.conn.execute(
                        "DELETE FROM messages WHERE session_id = ? AND role = 'system'",
                        (session_id,),
                    )
                    if system_prompt:
                        await self.conn.execute(
                            """
                            INSERT INTO messages
                                (session_id, role, content, metadata, created_at)
                            VALUES (?, 'system', ?, NULL, ?)
                            """,
                            (session_id, system_prompt, now),
                        )

                await self.conn.execute(
                    """
                    INSERT INTO messages (session_id, role, content, metadata, created_at)
                    VALUES (?, 'user', ?, NULL, ?)
                    """,
                    (session_id, user_content, now),
                )
                await self.conn.execute(
                    """
                    INSERT INTO messages (session_id, role, content, metadata, created_at)
                    VALUES (?, 'assistant', ?, ?, ?)
                    """,
                    (
                        session_id,
                        assistant_content,
                        json.dumps(assistant_metadata, ensure_ascii=False),
                        now,
                    ),
                )
                await self.conn.commit()
            except Exception:
                await self.conn.rollback()
                raise
