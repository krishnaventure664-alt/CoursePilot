
import sqlite3
from services.storage_config import SQLITE_DB_PATH

DB_PATH = SQLITE_DB_PATH


def get_connection():
    connection = sqlite3.connect(DB_PATH, timeout=60.0)
    connection.execute("PRAGMA busy_timeout = 60000;")
    connection.execute("PRAGMA journal_mode=WAL;")
    connection.execute("PRAGMA synchronous=NORMAL;")
    connection.execute("PRAGMA cache_size=-64000;")
    connection.execute("PRAGMA temp_store=MEMORY;")
    connection.execute("PRAGMA mmap_size=268435456;")
    connection.execute("PRAGMA foreign_keys=ON;")
    return connection


def initialize_sparse_index():
    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS sparse_postings (
            token_id INTEGER NOT NULL,
            chunk_id TEXT NOT NULL,
            weight REAL NOT NULL,
            course_id INTEGER,
            PRIMARY KEY (token_id, chunk_id)
        );
    """)

    columns = {
        row[1]
        for row in connection.execute(
            "PRAGMA table_info(sparse_postings)"
        ).fetchall()
    }

    if "course_id" not in columns:
        connection.execute(
            "ALTER TABLE sparse_postings ADD COLUMN course_id INTEGER"
        )

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_sparse_token
        ON sparse_postings(token_id);
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_sparse_chunk
        ON sparse_postings(chunk_id);
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_sparse_course_token
        ON sparse_postings(course_id, token_id);
    """)

    # Recover course IDs for existing postings using the
    # indexer's state table, when that table is available.
    state_table_exists = connection.execute("""
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'bge_m3_index_state'
    """).fetchone()

    if state_table_exists:
        connection.execute("""
            UPDATE sparse_postings
            SET course_id = (
                SELECT course_id
                FROM bge_m3_index_state
                WHERE bge_m3_index_state.chunk_id =
                      sparse_postings.chunk_id
            )
            WHERE course_id IS NULL
              AND EXISTS (
                SELECT 1
                FROM bge_m3_index_state
                WHERE bge_m3_index_state.chunk_id =
                      sparse_postings.chunk_id
              )
        """)

    connection.commit()
    connection.close()


def add_sparse_vector(chunk_id, sparse_weights, course_id):
    connection = get_connection()

    rows = [
        (int(token_id), chunk_id, float(weight), int(course_id))
        for token_id, weight in sparse_weights.items()
    ]

    connection.executemany("""
        INSERT OR REPLACE INTO sparse_postings
        (token_id, chunk_id, weight, course_id)
        VALUES (?, ?, ?, ?)
    """, rows)

    connection.commit()
    connection.close()
def add_sparse_vectors_batch(items: list[dict]):
    """
    Batch inserts sparse weights for an entire lecture in a single SQLite transaction.
    Reduces disk syncs from dozens per video down to 1 single commit.
    """
    if not items:
        return

    connection = get_connection()
    all_rows = []
    for item in items:
        chunk_id = item["chunk_id"]
        course_id = int(item["course_id"])
        for token_id, weight in item["sparse_weights"].items():
            all_rows.append((int(token_id), chunk_id, float(weight), course_id))

    connection.executemany("""
        INSERT OR REPLACE INTO sparse_postings
        (token_id, chunk_id, weight, course_id)
        VALUES (?, ?, ?, ?)
    """, all_rows)

    connection.commit()
    connection.close()

def add_sparse_vectors(items):
    if not items:
        return

    connection = get_connection()
    rows = []

    for item in items:
        chunk_id = item["chunk_id"]
        course_id = int(item["course_id"])
        sparse_weights = item["sparse_weights"]

        for token_id, weight in sparse_weights.items():
            rows.append((
                int(token_id),
                chunk_id,
                float(weight),
                course_id
            ))

    connection.executemany("""
        INSERT OR REPLACE INTO sparse_postings
        (token_id, chunk_id, weight, course_id)
        VALUES (?, ?, ?, ?)
    """, rows)

    connection.commit()
    connection.close()


def get_postings(token_id):
    connection = get_connection()

    rows = connection.execute("""
        SELECT chunk_id, weight
        FROM sparse_postings
        WHERE token_id = ?
    """, (int(token_id),)).fetchall()

    connection.close()
    return rows


def delete_chunk(chunk_id):
    connection = get_connection()

    connection.execute("""
        DELETE FROM sparse_postings
        WHERE chunk_id = ?
    """, (chunk_id,))

    connection.commit()
    connection.close()


def delete_chunks(chunk_ids):
    if not chunk_ids:
        return

    connection = get_connection()

    connection.executemany("""
        DELETE FROM sparse_postings
        WHERE chunk_id = ?
    """, [(chunk_id,) for chunk_id in chunk_ids])

    connection.commit()
    connection.close()


def search_sparse_chunks(query_sparse_weights, course_id, n_results=50):
    if not query_sparse_weights:
        return []

    token_ids = [int(token_id) for token_id in query_sparse_weights.keys()]
    if not token_ids:
        return []

    connection = get_connection()
    placeholders = ",".join("?" for _ in token_ids)
    sql = f"""
        SELECT token_id, chunk_id, weight
        FROM sparse_postings
        WHERE course_id = ?
          AND token_id IN ({placeholders})
    """
    params = [int(course_id)] + token_ids
    rows = connection.execute(sql, params).fetchall()
    connection.close()

    scores = {}
    for token_id, chunk_id, doc_weight in rows:
        query_weight = float(query_sparse_weights.get(token_id, query_sparse_weights.get(str(token_id), 0.0)))
        scores[chunk_id] = scores.get(chunk_id, 0.0) + (query_weight * float(doc_weight))

    ranked_results = sorted(
        scores.items(),
        key=lambda item: item[1],
        reverse=True
    )

    return [
        {"chunk_id": chunk_id, "sparse_score": score}
        for chunk_id, score in ranked_results[:n_results]
    ]
def delete_course_sparse_postings(course_id: int):
    """Deletes all sparse BGE-M3 postings for a course to free storage."""
    with get_connection() as connection:
        connection.execute(
            "DELETE FROM sparse_postings WHERE course_id = ?",
            (int(course_id),),
        )
        connection.commit()