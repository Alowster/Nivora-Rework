import sqlite3
import os
from datetime import datetime
from config import DB_PATH

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL DEFAULT 'Nueva conversación',
            created_at  TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS messages (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            role            TEXT    NOT NULL CHECK(role IN ('user', 'assistant')),
            content         TEXT    NOT NULL,
            created_at      TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS macros (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL,
            hotkey     TEXT,
            content    TEXT    NOT NULL,
            type       TEXT    NOT NULL CHECK(type IN ('shell', 'text'))
        );
    """)

    conn.commit()
    conn.close()

def create_conversation():
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO conversations (name, created_at) VALUES (?, ?)",
        ("Nueva conversación", now)
    )
    conn.commit()
    conversation_id = cursor.lastrowid
    conn.close()
    return conversation_id

def get_conversation_name(conversation_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT name FROM conversations WHERE id = ?", (conversation_id,)
    ).fetchone()
    conn.close()
    return row["name"] if row else ""

def rename_conversation(conversation_id, name):
    conn = get_connection()
    conn.execute(
        "UPDATE conversations SET name = ? WHERE id = ?",
        (name, conversation_id)
    )
    conn.commit()
    conn.close()

def get_all_conversations():
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, name, created_at FROM conversations ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def delete_conversation(conversation_id):
    conn = get_connection()
    conn.execute(
        "DELETE FROM conversations WHERE id = ?", (conversation_id,)
    )
    conn.commit()
    conn.close()

def add_message(conversation_id, role, content):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO messages (conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (conversation_id, role, content, now)
    )
    conn.commit()
    message_id = cursor.lastrowid
    conn.close()
    return message_id

def get_messages(conversation_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT role, content, created_at FROM messages WHERE conversation_id = ? ORDER BY created_at",
        (conversation_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_all_macros():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM macros ORDER BY name"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def create_macro(name, content, macro_type, hotkey=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO macros (name, hotkey, content, type) VALUES (?, ?, ?, ?)",
        (name, hotkey, content, macro_type)
    )
    conn.commit()
    macro_id = cursor.lastrowid
    conn.close()
    return macro_id

def update_macro_hotkey(macro_id, hotkey):
    conn = get_connection()
    conn.execute(
        "UPDATE macros SET hotkey = ? WHERE id = ?",
        (hotkey, macro_id)
    )
    conn.commit()
    conn.close()

def delete_macro(macro_id):
    conn = get_connection()
    conn.execute(
        "DELETE FROM macros WHERE id = ?",
        (macro_id,)
    )
    conn.commit()
    conn.close()

