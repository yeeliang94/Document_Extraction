"""Minimal SQLite database — documents, pages, extracted fields."""

import sqlite3
import threading
from pathlib import Path

from config import settings

_local = threading.local()


def get_conn() -> sqlite3.Connection:
    """Get a thread-local SQLite connection."""
    if not hasattr(_local, "conn") or _local.conn is None:
        db_path = Path(settings.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        _local.conn = conn
    return _local.conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            total_pages INTEGER DEFAULT 0,
            status TEXT DEFAULT 'uploaded',
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS pages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL REFERENCES documents(id),
            page_num INTEGER NOT NULL,
            image_path TEXT,
            width INTEGER,
            height INTEGER,
            UNIQUE(document_id, page_num)
        );

        CREATE TABLE IF NOT EXISTS extracted_fields (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL REFERENCES documents(id),
            field_number INTEGER NOT NULL,
            field_name TEXT NOT NULL,
            value TEXT,
            found INTEGER DEFAULT 0,
            needs_review INTEGER DEFAULT 0,
            source_page INTEGER,
            extraction_note TEXT,
            source_strategy TEXT DEFAULT 'vision_extraction',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(document_id, field_number)
        );

        CREATE TABLE IF NOT EXISTS agent_corrections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id INTEGER NOT NULL REFERENCES documents(id),
            field_number INTEGER NOT NULL,
            old_value TEXT,
            new_value TEXT,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()


# --- Documents CRUD ---

def create_document(filename: str, file_path: str, total_pages: int) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO documents (filename, file_path, total_pages) VALUES (?, ?, ?)",
        (filename, file_path, total_pages),
    )
    conn.commit()
    return cur.lastrowid


def get_document(doc_id: int) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    return dict(row) if row else None


def list_documents() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM documents ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def update_document_status(doc_id: int, status: str, error_message: str = None):
    conn = get_conn()
    conn.execute(
        "UPDATE documents SET status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (status, error_message, doc_id),
    )
    conn.commit()


# --- Pages CRUD ---

def insert_page(document_id: int, page_num: int, image_path: str, width: int, height: int):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO pages (document_id, page_num, image_path, width, height) VALUES (?, ?, ?, ?, ?)",
        (document_id, page_num, image_path, width, height),
    )
    conn.commit()


def get_pages(document_id: int) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM pages WHERE document_id = ? ORDER BY page_num", (document_id,)
    ).fetchall()
    return [dict(r) for r in rows]


# --- Fields CRUD ---

def bulk_insert_fields(document_id: int, fields: list[dict]):
    conn = get_conn()
    for f in fields:
        conn.execute(
            """INSERT OR REPLACE INTO extracted_fields
            (document_id, field_number, field_name, value, found, needs_review, source_page, extraction_note, source_strategy)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                document_id,
                f["field_number"],
                f.get("name", f.get("field_name", "")),
                f.get("value"),
                1 if f.get("found") else 0,
                1 if f.get("needs_review") else 0,
                f.get("source_page"),
                f.get("note", f.get("extraction_note")),
                f.get("source_strategy", "vision_extraction"),
            ),
        )
    conn.commit()


def get_fields(document_id: int) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM extracted_fields WHERE document_id = ? ORDER BY field_number",
        (document_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def update_field(document_id: int, field_number: int, value: str, reason: str, strategy: str = "review_agent"):
    conn = get_conn()
    # Log correction
    old = conn.execute(
        "SELECT value FROM extracted_fields WHERE document_id = ? AND field_number = ?",
        (document_id, field_number),
    ).fetchone()
    old_value = dict(old)["value"] if old else None

    conn.execute(
        "INSERT INTO agent_corrections (document_id, field_number, old_value, new_value, reason) VALUES (?, ?, ?, ?, ?)",
        (document_id, field_number, old_value, value, reason),
    )

    conn.execute(
        """UPDATE extracted_fields SET value = ?, needs_review = 0,
        source_strategy = ?, extraction_note = ? WHERE document_id = ? AND field_number = ?""",
        (value, strategy, reason, document_id, field_number),
    )
    conn.commit()


def get_corrections(document_id: int) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM agent_corrections WHERE document_id = ? ORDER BY created_at",
        (document_id,),
    ).fetchall()
    return [dict(r) for r in rows]
