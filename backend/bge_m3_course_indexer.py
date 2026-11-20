
import sqlite3
import time

import chromadb

from services.bge_m3_service import encode_texts
from services.bge_m3_vector_store_service import store_dense_chunks
from services.sparse_index_service import (
    initialize_sparse_index,
    add_sparse_vectors,
)


# ============================================================
# CONFIGURATION
# ============================================================

COURSE_ID = 1
BATCH_SIZE = 16

OLD_COLLECTION_NAME = "course_chunks"
STATE_DB = "./sparse_index.db"


# ============================================================
# DATABASE: INDEXING STATE
# ============================================================

def initialize_state_table():
    """Create the table that tracks completed chunks."""

    with sqlite3.connect(STATE_DB) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS bge_m3_index_state (
                chunk_id TEXT PRIMARY KEY,
                course_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                updated_at REAL NOT NULL
            )
        """)


def is_chunk_indexed(chunk_id):
    """Return True if this chunk is already marked completed."""

    with sqlite3.connect(STATE_DB) as connection:
        row = connection.execute(
            """
            SELECT status
            FROM bge_m3_index_state
            WHERE chunk_id = ?
            """,
            (chunk_id,),
        ).fetchone()

    return row is not None and row[0] == "completed"


def mark_chunks_completed(chunk_ids):
    """Mark chunks completed after both indexes are stored."""

    now = time.time()

    with sqlite3.connect(STATE_DB) as connection:
        connection.executemany(
            """
            INSERT OR REPLACE INTO bge_m3_index_state
                (chunk_id, course_id, status, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            [
                (chunk_id, COURSE_ID, "completed", now)
                for chunk_id in chunk_ids
            ],
        )


# ============================================================
# LOAD EXISTING COURSE CHUNKS
# ============================================================

def load_existing_chunks():
    """Load chunks for the configured course from the old collection."""

    client = chromadb.PersistentClient(path="./chroma_db")

    collection = client.get_collection(name=OLD_COLLECTION_NAME)

    results = collection.get(
        where={"course_id": COURSE_ID},
        include=["documents", "metadatas"],
    )

    chunks = []

    for index, chunk_id in enumerate(results["ids"]):
        metadata = results["metadatas"][index]
        text = results["documents"][index]

        chunks.append(
            {
                "chunk_id": chunk_id,
                "text": text,
                "metadata": metadata,
            }
        )

    return chunks


# ============================================================
# PROCESS ONE BATCH
# ============================================================

def process_batch(chunks):
    """Generate and store dense and sparse representations."""

    texts = [chunk["text"] for chunk in chunks]
    chunk_ids = [chunk["chunk_id"] for chunk in chunks]

    # Generate BGE-M3 embeddings.
    encoded = encode_texts(texts)

    dense_vectors = encoded["dense"]
    sparse_vectors = encoded["sparse"]

    # Prepare metadata for the dense vector collection.
    metadatas = [
        {
            "course_id": chunk["metadata"]["course_id"],
            "video_id": chunk["metadata"]["video_id"],
            "start": chunk["metadata"]["start"],
            "end": chunk["metadata"]["end"],
        }
        for chunk in chunks
    ]

    # Store dense vectors.
    store_dense_chunks(
        chunk_ids=chunk_ids,
        texts=texts,
        embeddings=dense_vectors,
        metadatas=metadatas,
    )

    # Prepare sparse vectors with their corresponding course IDs.
    sparse_items = []

    for chunk, chunk_id, sparse_vector in zip(
        chunks,
        chunk_ids,
        sparse_vectors,
    ):
        sparse_items.append(
            {
                "chunk_id": chunk_id,
                "sparse_weights": sparse_vector,
                "course_id": chunk["metadata"]["course_id"],
            }
        )

    # Store sparse vectors.
    add_sparse_vectors(sparse_items)

    # Mark completed only after both storage operations succeed.
    mark_chunks_completed(chunk_ids)


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 70)
    print("COURSEPILOT BGE-M3 COURSE INDEXER")
    print("=" * 70)

    print(f"\nCourse ID: {COURSE_ID}")
    print(f"Batch size: {BATCH_SIZE}")

    # Initialize the sparse index and indexing-state table.
    initialize_sparse_index()
    initialize_state_table()

    # Load existing chunks.
    print("\nLoading existing course chunks...")

    chunks = load_existing_chunks()

    print(f"Total existing chunks: {len(chunks)}")

    if not chunks:
        print("No chunks found. Nothing to index.")
        return

    # Exclude chunks already marked as completed.
    pending_chunks = [
        chunk
        for chunk in chunks
        if not is_chunk_indexed(chunk["chunk_id"])
    ]

    already_completed = len(chunks) - len(pending_chunks)

    print(f"Already completed: {already_completed}")
    print(f"Remaining: {len(pending_chunks)}")

    if not pending_chunks:
        print("\nAll chunks are already indexed.")
        return

    # Process remaining chunks in batches.
    total = len(pending_chunks)
    total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
    start_time = time.time()

    for start_index in range(0, total, BATCH_SIZE):
        batch = pending_chunks[start_index:start_index + BATCH_SIZE]
        batch_number = start_index // BATCH_SIZE + 1

        print(f"\nBatch {batch_number}/{total_batches}")
        print(
            f"Processing chunks "
            f"{start_index + 1}-{start_index + len(batch)} "
            f"of {total}"
        )

        batch_start = time.time()

        process_batch(batch)

        batch_time = time.time() - batch_start
        elapsed = time.time() - start_time

        print(f"Batch completed in {batch_time:.2f} seconds")
        print(f"Progress: {min(start_index + len(batch), total)}/{total}")
        print(f"Elapsed time: {elapsed / 60:.2f} minutes")

    total_time = time.time() - start_time

    print("\n" + "=" * 70)
    print("BGE-M3 INDEXING COMPLETE")
    print("=" * 70)
    print(f"Newly indexed chunks: {total}")
    print(f"Total time: {total_time / 60:.2f} minutes")


if __name__ == "__main__":
    main()
