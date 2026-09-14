"""
SQLite storage for transcription history.
"""

import sqlite3
import datetime
from typing import List, Dict, Optional, Any
from config import DB_PATH

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema and performs migrations."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transcriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                target_app TEXT,
                language TEXT,
                tone TEXT,
                raw_text TEXT NOT NULL,
                raw_in_english TEXT,
                english_translation TEXT,
                polished_text TEXT NOT NULL,
                duration_seconds REAL,
                status TEXT DEFAULT 'success'
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON transcriptions(timestamp DESC)")

        # Schema migration for existing databases
        existing_cols = [r["name"] for r in conn.execute("PRAGMA table_info(transcriptions)").fetchall()]
        if "raw_in_english" not in existing_cols:
            conn.execute("ALTER TABLE transcriptions ADD COLUMN raw_in_english TEXT")
        if "english_translation" not in existing_cols:
            conn.execute("ALTER TABLE transcriptions ADD COLUMN english_translation TEXT")

        conn.commit()

def save_transcription(
    raw_text: str,
    polished_text: str,
    tone: str,
    language: str = "auto",
    target_app: Optional[str] = None,
    duration_seconds: float = 0.0,
    status: str = "success",
    raw_in_english: Optional[str] = None,
    english_translation: Optional[str] = None
) -> int:
    """Inserts a new transcription record into the database."""
    init_db()
    timestamp = datetime.datetime.now().isoformat()
    # Default fallbacks if omitted
    effective_raw_en = raw_in_english if raw_in_english is not None else raw_text
    effective_trans_en = english_translation if english_translation is not None else polished_text

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO transcriptions (
                timestamp, target_app, language, tone,
                raw_text, raw_in_english, english_translation,
                polished_text, duration_seconds, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp, target_app, language, tone,
                raw_text, effective_raw_en, effective_trans_en,
                polished_text, duration_seconds, status
            )
        )
        conn.commit()
        return cursor.lastrowid

def get_history(limit: int = 50, search: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves recent transcriptions, with optional full-text search."""
    init_db()
    with get_connection() as conn:
        if search:
            query = """
                SELECT * FROM transcriptions 
                WHERE raw_text LIKE ? OR raw_in_english LIKE ? OR english_translation LIKE ? OR polished_text LIKE ? OR target_app LIKE ?
                ORDER BY timestamp DESC LIMIT ?
            """
            pattern = f"%{search}%"
            rows = conn.execute(query, (pattern, pattern, pattern, pattern, pattern, limit)).fetchall()
        else:
            query = "SELECT * FROM transcriptions ORDER BY timestamp DESC LIMIT ?"
            rows = conn.execute(query, (limit,)).fetchall()
        
        return [dict(row) for row in rows]

def delete_transcription(record_id: int) -> bool:
    """Deletes a transcription by ID."""
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM transcriptions WHERE id = ?", (record_id,))
        conn.commit()
        return cursor.rowcount > 0

def clear_history():
    """Wipes all transcription records."""
    with get_connection() as conn:
        conn.execute("DELETE FROM transcriptions")
        conn.commit()

# Ensure DB is created on import
init_db()
