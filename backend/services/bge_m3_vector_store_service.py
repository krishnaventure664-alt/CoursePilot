import chromadb
from services.storage_config import CHROMA_DIR

# Use absolute path from storage_config so it works from any directory
client = chromadb.PersistentClient(
    path=str(CHROMA_DIR)
)

collection = client.get_or_create_collection(
    name="course_chunks_gemini_v1"
)


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
