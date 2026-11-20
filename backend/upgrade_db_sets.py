with open("backend/services/course_db_service.py", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Update CREATE TABLE for course_quizzes and course_flashcards
text = text.replace(
    """CREATE TABLE IF NOT EXISTS course_quizzes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                video_id TEXT,
                quiz_data TEXT NOT NULL,
                created_at REAL NOT NULL
            )""",
    """CREATE TABLE IF NOT EXISTS course_quizzes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                video_id TEXT,
                set_index INTEGER DEFAULT 0,
                quiz_data TEXT NOT NULL,
                created_at REAL NOT NULL
            )""",
)

text = text.replace(
    """CREATE TABLE IF NOT EXISTS course_flashcards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                video_id TEXT,
                front TEXT NOT NULL,
                back TEXT NOT NULL,
                category TEXT,
                status TEXT DEFAULT 'new',
                created_at REAL NOT NULL
            )""",
    """CREATE TABLE IF NOT EXISTS course_flashcards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                video_id TEXT,
                set_index INTEGER DEFAULT 0,
                front TEXT NOT NULL,
                back TEXT NOT NULL,
                category TEXT,
                status TEXT DEFAULT 'new',
                created_at REAL NOT NULL
            )""",
)

# Add column migrations in init_db
migration_snippet = """        # Progressive Set Index Migrations
        q_cols = [c["name"] for c in connection.execute("PRAGMA table_info(course_quizzes)").fetchall()]
        if "set_index" not in q_cols:
            connection.execute("ALTER TABLE course_quizzes ADD COLUMN set_index INTEGER DEFAULT 0")

        fc_cols = [c["name"] for c in connection.execute("PRAGMA table_info(course_flashcards)").fetchall()]
        if "set_index" not in fc_cols:
            connection.execute("ALTER TABLE course_flashcards ADD COLUMN set_index INTEGER DEFAULT 0")
"""

if "Progressive Set Index Migrations" not in text:
    text = text.replace(
        'connection.execute("""\n            CREATE TABLE IF NOT EXISTS course_flashcards',
        migration_snippet + '\n        connection.execute("""\n            CREATE TABLE IF NOT EXISTS course_flashcards',
    )

# 2. Update get_cached_quiz, save_quiz, get_flashcards, save_flashcards
old_quiz_fc = """def get_cached_quiz(course_id: int, video_id: str | None = None):
    with get_connection() as conn:
        if video_id:
            row = conn.execute(
                "SELECT quiz_data FROM course_quizzes WHERE course_id = ? AND video_id = ? ORDER BY id DESC LIMIT 1",
                (course_id, video_id),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT quiz_data FROM course_quizzes WHERE course_id = ? ORDER BY id DESC LIMIT 1",
                (course_id,),
            ).fetchone()
        return row["quiz_data"] if row else None


def save_quiz(course_id: int, video_id: str | None, quiz_json: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO course_quizzes (course_id, video_id, quiz_data, created_at) VALUES (?, ?, ?, ?)",
            (course_id, video_id, quiz_json, time.time()),
        )


def get_flashcards(course_id: int, video_id: str | None = None):
    with get_connection() as conn:
        if video_id:
            rows = conn.execute(
                "SELECT id, front, back, category, status FROM course_flashcards WHERE course_id = ? AND video_id = ?",
                (course_id, video_id),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, front, back, category, status FROM course_flashcards WHERE course_id = ?",
                (course_id,),
            ).fetchall()
        return [dict(r) for r in rows]


def clear_flashcards(course_id: int, video_id: str | None = None):
    with get_connection() as conn:
        if video_id:
            conn.execute("DELETE FROM course_flashcards WHERE course_id = ? AND video_id = ?", (course_id, video_id))
        else:
            conn.execute("DELETE FROM course_flashcards WHERE course_id = ?", (course_id,))


def save_flashcards(course_id: int, video_id: str | None, cards: list[dict]):
    with get_connection() as conn:
        for card in cards:
            conn.execute(
                \"\"\"
                INSERT INTO course_flashcards (course_id, video_id, front, back, category, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'new', ?)
                \"\"\",
                (course_id, video_id, card["front"], card["back"], card.get("category", "General"), time.time()),
            )"""

new_quiz_fc = """def get_cached_quiz(course_id: int, video_id: str | None = None, set_index: int | None = None):
    with get_connection() as conn:
        if video_id:
            if set_index is not None:
                row = conn.execute(
                    "SELECT quiz_data, set_index FROM course_quizzes WHERE course_id = ? AND video_id = ? AND set_index = ? ORDER BY id DESC LIMIT 1",
                    (course_id, video_id, set_index),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT quiz_data, set_index FROM course_quizzes WHERE course_id = ? AND video_id = ? ORDER BY id DESC LIMIT 1",
                    (course_id, video_id),
                ).fetchone()
        else:
            if set_index is not None:
                row = conn.execute(
                    "SELECT quiz_data, set_index FROM course_quizzes WHERE course_id = ? AND set_index = ? ORDER BY id DESC LIMIT 1",
                    (course_id, set_index),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT quiz_data, set_index FROM course_quizzes WHERE course_id = ? ORDER BY id DESC LIMIT 1",
                    (course_id,),
                ).fetchone()
        return dict(row) if row else None


def save_quiz(course_id: int, video_id: str | None, quiz_json: str, set_index: int = 0):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO course_quizzes (course_id, video_id, set_index, quiz_data, created_at) VALUES (?, ?, ?, ?, ?)",
            (course_id, video_id, set_index, quiz_json, time.time()),
        )


def get_flashcards(course_id: int, video_id: str | None = None, set_index: int | None = None):
    with get_connection() as conn:
        if video_id:
            if set_index is not None:
                rows = conn.execute(
                    "SELECT id, front, back, category, status, set_index FROM course_flashcards WHERE course_id = ? AND video_id = ? AND set_index = ?",
                    (course_id, video_id, set_index),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, front, back, category, status, set_index FROM course_flashcards WHERE course_id = ? AND video_id = ?",
                    (course_id, video_id),
                ).fetchall()
        else:
            if set_index is not None:
                rows = conn.execute(
                    "SELECT id, front, back, category, status, set_index FROM course_flashcards WHERE course_id = ? AND set_index = ?",
                    (course_id, set_index),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, front, back, category, status, set_index FROM course_flashcards WHERE course_id = ?",
                    (course_id,),
                ).fetchall()
        return [dict(r) for r in rows]


def clear_flashcards(course_id: int, video_id: str | None = None, set_index: int | None = None):
    with get_connection() as conn:
        if video_id:
            if set_index is not None:
                conn.execute("DELETE FROM course_flashcards WHERE course_id = ? AND video_id = ? AND set_index = ?", (course_id, video_id, set_index))
            else:
                conn.execute("DELETE FROM course_flashcards WHERE course_id = ? AND video_id = ?", (course_id, video_id))
        else:
            if set_index is not None:
                conn.execute("DELETE FROM course_flashcards WHERE course_id = ? AND set_index = ?", (course_id, set_index))
            else:
                conn.execute("DELETE FROM course_flashcards WHERE course_id = ?", (course_id,))


def save_flashcards(course_id: int, video_id: str | None, cards: list[dict], set_index: int = 0):
    with get_connection() as conn:
        for card in cards:
            conn.execute(
                \"\"\"
                INSERT INTO course_flashcards (course_id, video_id, set_index, front, back, category, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'new', ?)
                \"\"\",
                (course_id, video_id, set_index, card["front"], card["back"], card.get("category", "General"), time.time()),
            )"""

if old_quiz_fc in text:
    text = text.replace(old_quiz_fc, new_quiz_fc)
    print("Replaced quiz and flashcard functions successfully!")
else:
    print("Could not find exact old_quiz_fc string; doing normalized replace...")
    import re
    # Match the block from get_cached_quiz to update_flashcard_status
    pattern = r'def get_cached_quiz\(.*?(?=def update_flashcard_status)'
    text = re.sub(pattern, new_quiz_fc.strip() + "\n\n\n", text, flags=re.DOTALL)
    print("Replaced with regex successfully!")

with open("backend/services/course_db_service.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Saved course_db_service.py")
