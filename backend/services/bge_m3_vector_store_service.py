import json
import logging
from pathlib import Path
import chromadb
from services.storage_config import CHROMA_DIR

logger = logging.getLogger(__name__)

# Use absolute path from storage_config so it works from any directory
client = chromadb.PersistentClient(
    path=str(CHROMA_DIR)
)

collection = client.get_or_create_collection(
    name="course_chunks_bge_m3_v1"
)

# Auto-seed ChromaDB on fresh cloud deployments (e.g. Render)
try:
    if collection.count() == 0:
        seed_file = Path(__file__).resolve().parents[1] / "course18_chunks_seed.json"
        if seed_file.exists():
            with open(seed_file, "r", encoding="utf-8") as f:
                seed_data = json.load(f)
            if seed_data:
                c_ids = [item["id"] for item in seed_data]
                c_docs = [item["document"] for item in seed_data]
                c_metas = [item["metadata"] for item in seed_data]
                c_embs = [item["embedding"] for item in seed_data]
                collection.upsert(
                    ids=c_ids,
                    documents=c_docs,
                    metadatas=c_metas,
                    embeddings=c_embs,
                )
                logger.info(f"Auto-seeded {len(c_ids)} chunks into ChromaDB from {seed_file.name}")
except Exception as e:
    logger.warning("Could not auto-seed ChromaDB: %s", e)


def store_dense_chunk(
    chunk_id,
    text,
    embedding,
    video_id,
    course_id,
    start,
    end
):
    collection.upsert(
        ids=[chunk_id],
        documents=[text],
        embeddings=[embedding],
        metadatas=[
            {
                "course_id": course_id,
                "video_id": video_id,
                "start": start,
                "end": end
            }
        ]
    )


def store_dense_chunks(
    chunk_ids,
    texts,
    embeddings,
    metadatas
):
    if not chunk_ids:
        return

    collection.upsert(
        ids=chunk_ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas
    )


def search_dense_chunks(
    query_embedding,
    course_id,
    n_results=20
):
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where={
            "course_id": course_id
        }
    )

    return results


def delete_course_dense_chunks(course_id):
    collection.delete(
        where={
            "course_id": course_id
        }
    )
