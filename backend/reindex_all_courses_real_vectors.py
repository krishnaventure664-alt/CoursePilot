import sys
import os
import time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.bge_m3_vector_store_service import collection
from services.bge_m3_service import encode_texts
from services.sparse_index_service import add_sparse_vectors_batch

def reindex_all_zero_vector_courses():
    print("=" * 70)
    print("  CoursePilot - Recomputing Real BGE-M3 Vectors for All Courses")
    print("=" * 70)

    print("Step 1: Reading all chunks from ChromaDB...")
    t0 = time.time()
    data = collection.get(include=["embeddings", "metadatas", "documents"])
    ids = data["ids"]
    embs = data["embeddings"]
    metas = data["metadatas"]
    docs = data["documents"]

    total = len(ids)
    print(f"Total chunks in ChromaDB: {total}")

    # Identify zero-vector chunks
    zero_chunks = []
    for cid, emb, meta, doc in zip(ids, embs, metas, docs):
        if np.all(np.array(emb) == 0.0):
            zero_chunks.append({
                "chunk_id": cid,
                "course_id": meta.get("course_id"),
                "text": doc,
                "meta": meta
            })

    print(f"Zero-vector chunks to re-embed: {len(zero_chunks)}")
    if not zero_chunks:
        print("[SUCCESS] All chunks already have real vectors! Nothing to do.")
        return

    # Group by course_id for clean batching
    from collections import defaultdict
    course_groups = defaultdict(list)
    for c in zero_chunks:
        course_groups[c["course_id"]].append(c)

    print(f"Courses needing real embeddings: {list(course_groups.keys())}\n")

    BATCH_SIZE = 16
    overall_done = 0

    for cid, chunks in sorted(course_groups.items(), key=lambda x: str(x[0])):
        print(f"--- Processing Course {cid} ({len(chunks)} chunks) ---")
        t_course = time.time()

        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i:i + BATCH_SIZE]
            batch_texts = [b["text"] for b in batch]
            batch_ids = [b["chunk_id"] for b in batch]

            # Encode on GPU with BGE-M3
            encoded = encode_texts(batch_texts)
            dense_vecs = encoded["dense"]
            sparse_weights_list = encoded["sparse"]

            # Update ChromaDB with real dense embeddings
            # Convert dense vectors to float list if numpy array
            dense_list = [v.tolist() if hasattr(v, "tolist") else list(v) for v in dense_vecs]
            collection.update(ids=batch_ids, embeddings=dense_list)

            # Insert sparse vectors into SQLite
            sparse_items = []
            for b_id, s_weights in zip(batch_ids, sparse_weights_list):
                sparse_items.append({
                    "chunk_id": b_id,
                    "course_id": cid,
                    "sparse_weights": s_weights
                })
            add_sparse_vectors_batch(sparse_items)

            overall_done += len(batch)
            print(f"  Course {cid}: {min(i + BATCH_SIZE, len(chunks))}/{len(chunks)} chunks embedded... (Overall: {overall_done}/{len(zero_chunks)})")

        elapsed = time.time() - t_course
        print(f"Course {cid} complete in {elapsed:.1f}s!\n")

    total_time = time.time() - t0
    print("=" * 70)
    print(f"[COMPLETED] Re-embedded {len(zero_chunks)} chunks across all courses in {total_time:.1f}s!")
    print("=" * 70)

if __name__ == "__main__":
    reindex_all_zero_vector_courses()
