"""SQLite-based memory storage for LocalCoder."""

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class MemoryEntry:
    """A memory entry."""

    id: Optional[int]
    content: str
    category: str
    project_root: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def new(cls, content: str, category: str, project_root: str) -> "MemoryEntry":
        """Create a new memory entry."""
        now = datetime.now()
        return cls(
            id=None,
            content=content,
            category=category,
            project_root=project_root,
            created_at=now,
            updated_at=now,
        )


class MemoryStore:
    """SQLite-based memory storage with full-text search."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = self._get_conn()
        cursor = conn.cursor()

        # Create memory entries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                category TEXT NOT NULL,
                project_root TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create full-text search virtual table
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                content,
                category,
                project_root,
                content='memory_entries',
                content_rowid='id'
            )
        """)

        # Create triggers for FTS
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS memory_ai AFTER INSERT ON memory_entries BEGIN
                INSERT INTO memory_fts(rowid, content, category, project_root)
                VALUES (new.id, new.content, new.category, new.project_root);
            END
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS memory_ad AFTER DELETE ON memory_entries BEGIN
                INSERT INTO memory_fts(memory_fts, rowid, content, category, project_root)
                VALUES ('delete', old.id, old.content, old.category, old.project_root);
            END
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS memory_au AFTER UPDATE ON memory_entries BEGIN
                INSERT INTO memory_fts(memory_fts, rowid, content, category, project_root)
                VALUES ('delete', old.id, old.content, old.category, old.project_root);
                INSERT INTO memory_fts(rowid, content, category, project_root)
                VALUES (new.id, new.content, new.category, new.project_root);
            END
        """)

        # Create indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_category ON memory_entries(category)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_project ON memory_entries(project_root)"
        )

        conn.commit()

    def add(self, entry: MemoryEntry) -> MemoryEntry:
        """Add a memory entry."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO memory_entries (content, category, project_root, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """,
            (entry.content, entry.category, entry.project_root, entry.created_at, entry.updated_at),
        )

        entry.id = cursor.lastrowid
        conn.commit()
        return entry

    def get(self, entry_id: int) -> Optional[MemoryEntry]:
        """Get a memory entry by ID."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM memory_entries WHERE id = ?",
            (entry_id,),
        )

        row = cursor.fetchone()
        if row:
            return self._row_to_entry(row)
        return None

    def delete(self, entry_id: int) -> bool:
        """Delete a memory entry."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM memory_entries WHERE id = ?",
            (entry_id,),
        )

        conn.commit()
        return cursor.rowcount > 0

    def search(self, query: str, project_root: Optional[str] = None) -> list[MemoryEntry]:
        """Search memory entries using full-text search."""
        conn = self._get_conn()
        cursor = conn.cursor()

        if project_root:
            cursor.execute(
                """
                SELECT e.* FROM memory_entries e
                JOIN memory_fts fts ON e.id = fts.rowid
                WHERE memory_fts MATCH ? AND e.project_root = ?
                ORDER BY rank
            """,
                (query, project_root),
            )
        else:
            cursor.execute(
                """
                SELECT e.* FROM memory_entries e
                JOIN memory_fts fts ON e.id = fts.rowid
                WHERE memory_fts MATCH ?
                ORDER BY rank
            """,
                (query,),
            )

        return [self._row_to_entry(row) for row in cursor.fetchall()]

    def list_all(
        self,
        project_root: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100,
    ) -> list[MemoryEntry]:
        """List all memory entries with optional filters."""
        conn = self._get_conn()
        cursor = conn.cursor()

        query = "SELECT * FROM memory_entries WHERE 1=1"
        params = []

        if project_root:
            query += " AND project_root = ?"
            params.append(project_root)

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        return [self._row_to_entry(row) for row in cursor.fetchall()]

    def update(self, entry: MemoryEntry) -> bool:
        """Update a memory entry."""
        if entry.id is None:
            return False

        conn = self._get_conn()
        cursor = conn.cursor()
        entry.updated_at = datetime.now()

        cursor.execute(
            """
            UPDATE memory_entries
            SET content = ?, category = ?, updated_at = ?
            WHERE id = ?
        """,
            (entry.content, entry.category, entry.updated_at, entry.id),
        )

        conn.commit()
        return cursor.rowcount > 0

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def _row_to_entry(self, row: sqlite3.Row) -> MemoryEntry:
        """Convert a database row to MemoryEntry."""
        return MemoryEntry(
            id=row["id"],
            content=row["content"],
            category=row["category"],
            project_root=row["project_root"],
            created_at=datetime.fromisoformat(row["created_at"])
            if isinstance(row["created_at"], str)
            else row["created_at"],
            updated_at=datetime.fromisoformat(row["updated_at"])
            if isinstance(row["updated_at"], str)
            else row["updated_at"],
        )
