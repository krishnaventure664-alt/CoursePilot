import shutil
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]

CHROMA_DIR = BACKEND_DIR / "chroma_db"
SQLITE_DB_PATH = BACKEND_DIR / "sparse_index.db"
SEED_DB_PATH = BACKEND_DIR / "sparse_index_seed.db"
LIPI_MODEL_DIR = BACKEND_DIR / "models" / "lipi"

# Auto-seed SQLite database on fresh cloud deployments (e.g. Render)
if not SQLITE_DB_PATH.exists() and SEED_DB_PATH.exists():
    try:
        shutil.copy2(SEED_DB_PATH, SQLITE_DB_PATH)
    except Exception:
        pass
elif SQLITE_DB_PATH.exists() and SEED_DB_PATH.exists():
    try:
        import sqlite3
        with sqlite3.connect(str(SEED_DB_PATH)) as seed_conn, sqlite3.connect(str(SQLITE_DB_PATH)) as live_conn:
            courses_to_sync = []
            seed_courses = seed_conn.execute("SELECT id FROM courses").fetchall()
            for (cid,) in seed_courses:
                s_count = seed_conn.execute("SELECT count(*) FROM course_videos WHERE course_id = ?", (cid,)).fetchone()[0]
                l_count_row = live_conn.execute("SELECT count(*) FROM course_videos WHERE course_id = ?", (cid,)).fetchone()
                l_count = l_count_row[0] if l_count_row else 0
                if l_count < s_count or l_count == 0:
                    courses_to_sync.append(cid)

            if courses_to_sync:
                for table in ["courses", "course_videos", "video_detailed_notes", "video_notes", "course_quizzes", "course_flashcards"]:
                    cols = [c[1] for c in seed_conn.execute(f"PRAGMA table_info({table})").fetchall()]
                    placeholders = ",".join(["?"] * len(cols))
                    col_str = ",".join(cols)
                    if table == "courses":
                        rows = seed_conn.execute(f"SELECT {col_str} FROM courses WHERE id IN ({','.join(map(str, courses_to_sync))})").fetchall()
                    else:
                        rows = seed_conn.execute(f"SELECT {col_str} FROM {table} WHERE course_id IN ({','.join(map(str, courses_to_sync))})").fetchall()
                    live_conn.executemany(f"INSERT OR REPLACE INTO {table} ({col_str}) VALUES ({placeholders})", rows)
                live_conn.commit()
    except Exception:
        pass
