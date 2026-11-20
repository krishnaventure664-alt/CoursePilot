import chromadb

from services.bge_m3_service import encode_text
from services.bge_m3_vector_store_service import search_dense_chunks
from services.sparse_index_service import search_sparse_chunks
from services.rrf_service import reciprocal_rank_fusion
from services.reranker_service import rerank_results


QUERY = "Buddhism ke founder kaun the?"
COURSE_ID = 1


# ==========================================
# 1. Encode query
# ==========================================

encoded = encode_text(QUERY)

dense_query = encoded["dense"]
sparse_query = encoded["sparse"]


# ==========================================
# 2. Dense retrieval
# ==========================================

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


# ==========================================
# 3. Sparse retrieval
# ==========================================

sparse_results = search_sparse_chunks(
    query_sparse_weights=sparse_query,
    course_id=COURSE_ID,
    n_results=50
)


# ==========================================
# 4. RRF Fusion
# ==========================================

fused_results = reciprocal_rank_fusion(
    dense_results=dense_results,
    sparse_results=sparse_results,
    top_k=50
)


# ==========================================
# 5. Get transcript text from Chroma
# ==========================================

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


# ==========================================
# 6. Prepare candidates for reranker
# ==========================================

reranker_candidates = []

for result in fused_results:

    chunk_id = result["chunk_id"]

    data = document_map.get(chunk_id)

    if not data:
        continue

    metadata = data["metadata"]

    reranker_candidates.append({
        "chunk_id": chunk_id,
        "text": data["text"],
        "video_id": metadata["video_id"],
        "start": metadata["start"],
        "end": metadata["end"],
        "rrf_score": result["rrf_score"],
        "dense_rank": result["dense_rank"],
        "sparse_rank": result["sparse_rank"]
    })


# ==========================================
# 7. Rerank
# ==========================================

reranked_results = rerank_results(
    query=QUERY,
    search_results=reranker_candidates,
    top_k=8
)


# ==========================================
# 8. Print final results
# ==========================================

print()
print("=" * 100)
print("RRF -> BGE RERANKER RESULTS")
print("=" * 100)

print()
print("Query:")
print(QUERY)

for rank, result in enumerate(reranked_results, start=1):

    print()
    print("-" * 100)

    print("Rank:", rank)

    print(
        "Chunk ID:",
        result["chunk_id"]
    )

    print(
        "Rerank Score:",
        result["rerank_score"]
    )

    print(
        "RRF Score:",
        result["rrf_score"]
    )

    print(
        "Dense Rank:",
        result["dense_rank"]
    )

    print(
        "Sparse Rank:",
        result["sparse_rank"]
    )

    print(
        "Video ID:",
        result["video_id"]
    )

    print(
        "Start:",
        result["start"]
    )

    print(
        "End:",
        result["end"]
    )

    print()
    print("Text:")
    print(result["text"][:700])


print()
print("=" * 100)