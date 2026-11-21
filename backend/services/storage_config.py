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
                s_vcount = seed_conn.execute("SELECT count(*) FROM course_videos WHERE course_id = ?", (cid,)).fetchone()[0]
                l_vcount_row = live_conn.execute("SELECT count(*) FROM course_videos WHERE course_id = ?", (cid,)).fetchone()
                l_vcount = l_vcount_row[0] if l_vcount_row else 0
                
                s_qcount = seed_conn.execute("SELECT count(*) FROM course_quizzes WHERE course_id = ?", (cid,)).fetchone()[0]
                l_qcount_row = live_conn.execute("SELECT count(*) FROM course_quizzes WHERE course_id = ?", (cid,)).fetchone()
                l_qcount = l_qcount_row[0] if l_qcount_row else 0

                s_fcount = seed_conn.execute("SELECT count(*) FROM course_flashcards WHERE course_id = ?", (cid,)).fetchone()[0]
                l_fcount_row = live_conn.execute("SELECT count(*) FROM course_flashcards WHERE course_id = ?", (cid,)).fetchone()
                l_fcount = l_fcount_row[0] if l_fcount_row else 0

                s_dlen = seed_conn.execute("SELECT sum(length(content)) FROM video_detailed_notes WHERE course_id = ?", (cid,)).fetchone()[0] or 0
                l_dlen_row = live_conn.execute("SELECT sum(length(content)) FROM video_detailed_notes WHERE course_id = ?", (cid,)).fetchone()
                l_dlen = (l_dlen_row[0] or 0) if l_dlen_row else 0

                if l_vcount < s_vcount or l_qcount < s_qcount or l_fcount < s_fcount or l_dlen < s_dlen or l_vcount == 0:
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
