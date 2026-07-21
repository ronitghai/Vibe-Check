"""
session_store.py
-----------------
Tiny SQLite-backed store keyed by session_id. Holds the raw chat history
(as plain dicts, ready to send straight to the Groq/OpenAI-compatible API)
and every game that's been launched in that session — the library is built
from this plus the static template registry, not just "the last game".
"""

import datetime
import json
import sqlite3

from . import config


def _conn():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            history_json TEXT NOT NULL DEFAULT '[]',
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS games (
            session_id TEXT NOT NULL,
            game_id TEXT NOT NULL,
            game_type TEXT NOT NULL,
            title TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (session_id, game_id)
        )
        """
    )
    conn.commit()
    conn.close()


def get_history(session_id: str) -> list:
    conn = _conn()
    row = conn.execute(
        "SELECT history_json FROM sessions WHERE session_id = ?", (session_id,)
    ).fetchone()
    conn.close()
    return json.loads(row["history_json"]) if row else []


def save_history(session_id: str, history: list) -> None:
    conn = _conn()
    now = datetime.datetime.utcnow().isoformat()
    conn.execute(
        """
        INSERT INTO sessions (session_id, history_json, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            history_json = excluded.history_json,
            updated_at = excluded.updated_at
        """,
        (session_id, json.dumps(history), now),
    )
    conn.commit()
    conn.close()


def upsert_game(session_id: str, game_id: str, game_type: str, title: str, payload: dict) -> None:
    """Insert or replace a session's stored game (template config or generated html+spec)."""
    conn = _conn()
    now = datetime.datetime.utcnow().isoformat()
    conn.execute(
        """
        INSERT INTO games (session_id, game_id, game_type, title, payload_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(session_id, game_id) DO UPDATE SET
            game_type = excluded.game_type,
            title = excluded.title,
            payload_json = excluded.payload_json
        """,
        (session_id, game_id, game_type, title, json.dumps(payload), now),
    )
    conn.commit()
    conn.close()


def get_game(session_id: str, game_id: str) -> dict | None:
    conn = _conn()
    row = conn.execute(
        "SELECT game_id, game_type, title, payload_json FROM games "
        "WHERE session_id = ? AND game_id = ?",
        (session_id, game_id),
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "game_id": row["game_id"],
        "game_type": row["game_type"],
        "title": row["title"],
        **json.loads(row["payload_json"]),
    }


def list_generated_games(session_id: str) -> list:
    conn = _conn()
    rows = conn.execute(
        "SELECT game_id, game_type, title, payload_json FROM games "
        "WHERE session_id = ? AND game_type = 'generated' "
        "ORDER BY created_at DESC",
        (session_id,),
    ).fetchall()
    conn.close()
    out = []
    for row in rows:
        payload = json.loads(row["payload_json"])
        out.append(
            {
                "game_id": row["game_id"],
                "game_type": row["game_type"],
                "title": row["title"],
                "description": payload.get("description", "AI-generated game"),
            }
        )
    return out
