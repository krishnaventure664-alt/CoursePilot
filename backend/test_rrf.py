import chromadb

from services.bge_m3_service import encode_text
from services.bge_m3_vector_store_service import search_dense_chunks
from services.sparse_index_service import search_sparse_chunks
from services.rrf_service import reciprocal_rank_fusion


QUERY = "What was the Indus Valley Civilization?"
COURSE_ID = 1


# -----------------------------------
# 1. Encode query
# -----------------------------------

encoded = encode_text(QUERY)

dense_query = encoded["dense"]
sparse_query = encoded["sparse"]


# -----------------------------------
# 2. Dense retrieval
# -----------------------------------

dense_raw = search_dense_chunks(
    query_embedding=dense_query,
    course_id=COURSE_ID,
    n_results=50
)


dense_results = []

for i in range(len(dense_raw["ids"][0])):

    dense_results.append({
        "chunk_id": dense_raw["ids"][0][i],
        "dense_distance": dense_raw["distances"][0][i]
    })


# -----------------------------------
# 3. Sparse retrieval
# -----------------------------------

sparse_results = search_sparse_chunks(
    query_sparse_weights=sparse_query,
    course_id=COURSE_ID,
    n_results=50
)


# -----------------------------------
# 4. RRF Fusion
# -----------------------------------

fused_results = reciprocal_rank_fusion(
    dense_results=dense_results,
    sparse_results=sparse_results,
    top_k=10
)


# -----------------------------------
# 5. Get transcript text
# -----------------------------------

chunk_ids = [
    result["chunk_id"]
    for result in fused_results
]


client = chromadb.PersistentClient(
    path="./chroma_db"
)

collection = client.get_collection(
    name="course_chunks_bge_m3_v1"
)


stored = collection.get(
    ids=chunk_ids,
    include=["documents", "metadatas"]
)


document_map = {}

for i, chunk_id in enumerate(stored["ids"]):

    document_map[chunk_id] = {
        "text": stored["documents"][i],
        "metadata": stored["metadatas"][i]
    }


# -----------------------------------
# 6. Print fused results
# -----------------------------------

print()
print("=" * 100)
print("RRF FUSION RESULTS WITH TRANSCRIPT TEXT")
print("=" * 100)

print()
print("Query:")
print(QUERY)

for rank, result in enumerate(fused_results, start=1):

    chunk_id = result["chunk_id"]

    data = document_map.get(chunk_id)

    print()
    print("-" * 100)

    print("Rank:", rank)
    print("Chunk ID:", chunk_id)

    print(
        "RRF Score:",
        round(result["rrf_score"], 6)
    )

    print(
        "Dense Rank:",
        result["dense_rank"]
    )

    print(
        "Sparse Rank:",
        result["sparse_rank"]
    )

    if data:

        metadata = data["metadata"]

        print(
            "Video ID:",
            metadata["video_id"]
        )

        print(
            "Start:",
            metadata["start"]
        )

        print(
            "End:",
            metadata["end"]
        )

        print()
        print("Text:")
        print(data["text"][:600])

    else:

        print()
        print("Text: NOT FOUND")


print()
print("=" * 100)