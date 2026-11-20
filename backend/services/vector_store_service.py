import chromadb


# ---------------------------------------------------------
# Persistent ChromaDB client
# ---------------------------------------------------------

client = chromadb.PersistentClient(
    path="./chroma_db"
)


# ---------------------------------------------------------
# Course chunk collection
# ---------------------------------------------------------

collection = client.get_or_create_collection(
    name="course_chunks"
)


# ---------------------------------------------------------
# Store one transcript chunk
# ---------------------------------------------------------

def store_chunk(
    chunk_id,
    text,
    embedding,
    video_id,
    course_id,
    start,
    end
):

    collection.add(
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


# ---------------------------------------------------------
# Search course chunks
# ---------------------------------------------------------

def search_chunks(
    query_embedding,
    course_id,
    n_results=5
):

    # -----------------------------------------------------
    # Retrieve more candidates than we finally need.
    #
    # We want the reranker to decide relevance.
    # Therefore we do NOT apply a hard distance cutoff here.
    # -----------------------------------------------------

    retrieval_count = max(
        n_results * 4,
        20
    )

    results = collection.query(
        query_embeddings=[query_embedding],

        n_results=retrieval_count,

        where={
            "course_id": course_id
        }
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    return {
        "documents": [documents],
        "metadatas": [metadatas],
        "distances": [distances]
    }


# ---------------------------------------------------------
# Delete all chunks belonging to a course
# ---------------------------------------------------------

def delete_course_chunks(course_id):

    collection.delete(
        where={
            "course_id": course_id
        }
    )