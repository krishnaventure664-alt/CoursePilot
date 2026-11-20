
import sqlite3
from pathlib import Path
import time

DB_PATH = Path(__file__).resolve().parents[1] / "sparse_index.db"


def get_connection():
    connection = sqlite3.connect(DB_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_course_db():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                playlist_id TEXT NOT NULL UNIQUE,
                url TEXT NOT NULL,
                title TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at REAL NOT NULL
            )
        """)


def get_course_by_playlist(playlist_id: str):
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM courses WHERE playlist_id = ?",
            (playlist_id,),
        ).fetchone()

        return dict(row) if row else None


def create_course(playlist_id: str, url: str, title: str):
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO courses (
                playlist_id, url, title, status, created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (playlist_id, url, title, "processing", time.time()),
        )

        row = connection.execute(
            "SELECT * FROM courses WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()

        return dict(row)


def update_course_status(course_id: int, status: str):
    with get_connection() as connection:
        connection.execute(
            "UPDATE courses SET status = ? WHERE id = ?",
            (status, course_id),
        )


initialize_course_db()
