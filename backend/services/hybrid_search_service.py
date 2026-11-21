from services.bge_m3_service import encode_text
from services.bge_m3_vector_store_service import search_dense_chunks
from services.sparse_index_service import search_sparse_chunks
from services.rrf_service import reciprocal_rank_fusion
from services.reranker_service import rerank_results


import threading

DENSE_TOP_K = 30
SPARSE_TOP_K = 30
RRF_TOP_K = 10
FINAL_TOP_K = 6

_chunk_details_cache: dict[str, dict] = {}
_chunk_details_lock = threading.Lock()


def get_chunk_details(chunk_ids):
    """
    Fetch the actual text and metadata for chunk IDs
    with ultra-fast 0ms in-memory cache lookup.
    """
    if not chunk_ids:
        return []

    cached_results = []
    missing_ids = []

    with _chunk_details_lock:
        for cid in chunk_ids:
            if cid in _chunk_details_cache:
                cached_results.append(_chunk_details_cache[cid])
            else:
                missing_ids.append(cid)

    if missing_ids:
        from services.bge_m3_vector_store_service import collection
        try:
            results = collection.get(
                ids=missing_ids,
                include=["documents", "metadatas"]
            )
            for i, chunk_id in enumerate(results.get("ids", [])):
                c_item = {
                    "chunk_id": chunk_id,
                    "text": results["documents"][i],
                    "video_id": results["metadatas"][i]["video_id"],
                    "course_id": results["metadatas"][i]["course_id"],
                    "start": results["metadatas"][i]["start"],
                    "end": results["metadatas"][i]["end"],
                }
                cached_results.append(c_item)
                with _chunk_details_lock:
                    if len(_chunk_details_cache) > 2000:
                        _chunk_details_cache.pop(next(iter(_chunk_details_cache)))
                    _chunk_details_cache[chunk_id] = c_item
        except Exception:
            pass

    chunk_map = {c["chunk_id"]: c for c in cached_results}
    return [chunk_map[cid] for cid in chunk_ids if cid in chunk_map]


def hybrid_search(
    query: str,
    course_id: int,
    final_top_k: int = FINAL_TOP_K
):
    """
    Production retrieval pipeline:

    Query
      ↓
    BGE-M3 encoding
      ↓
    Dense retrieval + Sparse retrieval
      ↓
    RRF fusion
      ↓
    Fetch chunk text
      ↓
    BGE reranker
      ↓
    Final top K
    """

    if not query or not query.strip():
        return []

    query = query.strip()

    from services.course_db_service import get_canonical_course_id
    effective_course_id = get_canonical_course_id(course_id)

    # --------------------------------------------------
    # 1. Encode query with BGE-M3
    # --------------------------------------------------

    encoded_query = encode_text(query)

    dense_query = encoded_query["dense"]
    sparse_query = encoded_query["sparse"]

    # --------------------------------------------------
    # 2 & 3. Concurrent Dense & Sparse retrieval
    # --------------------------------------------------
    from concurrent.futures import ThreadPoolExecutor

    def _fetch_dense():
        return search_dense_chunks(
            query_embedding=dense_query,
            course_id=effective_course_id,
            n_results=DENSE_TOP_K
        )

    def _fetch_sparse():
        return search_sparse_chunks(
            query_sparse_weights=sparse_query,
            course_id=effective_course_id,
            n_results=SPARSE_TOP_K
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        dense_future = executor.submit(_fetch_dense)
        sparse_future = executor.submit(_fetch_sparse)
        dense_results_raw = dense_future.result()
        sparse_results = sparse_future.result()

    dense_results = []
    if dense_results_raw and dense_results_raw.get("ids") and dense_results_raw["ids"][0]:
        for rank, chunk_id in enumerate(
            dense_results_raw["ids"][0],
            start=1
        ):
            dense_results.append({
                "chunk_id": chunk_id,
                "dense_rank": rank,
                "dense_distance": dense_results_raw["distances"][0][rank - 1]
            })

    # --------------------------------------------------
    # 4. RRF fusion
    # --------------------------------------------------

    rrf_results = reciprocal_rank_fusion(
        dense_results=dense_results,
        sparse_results=sparse_results,
        top_k=RRF_TOP_K
    )

    if not rrf_results:
        return []

    # --------------------------------------------------
    # 5. Fetch actual chunk text + metadata
    # --------------------------------------------------

    chunk_ids = [
        result["chunk_id"]
        for result in rrf_results
    ]

    chunk_details = get_chunk_details(chunk_ids)

    chunk_map = {
        chunk["chunk_id"]: chunk
        for chunk in chunk_details
    }

    reranker_candidates = []

    for result in rrf_results:

        chunk_id = result["chunk_id"]

        if chunk_id not in chunk_map:
            continue

        chunk = chunk_map[chunk_id]

        reranker_candidates.append({
            "chunk_id": chunk_id,
            "text": chunk["text"],
            "video_id": chunk["video_id"],
            "course_id": chunk["course_id"],
            "start": chunk["start"],
            "end": chunk["end"],
            "rrf_score": result["rrf_score"],
            "dense_rank": result["dense_rank"],
            "sparse_rank": result["sparse_rank"],
        })

    if not reranker_candidates:
        return []

    # --------------------------------------------------
    # 6. BGE multilingual reranking
    # --------------------------------------------------

    reranked_results = rerank_results(
        query=query,
        search_results=reranker_candidates,
        top_k=final_top_k
    )

    # --------------------------------------------------
    # 7. Return standardized retrieval results
    # --------------------------------------------------

    final_results = []

    for rank, result in enumerate(
        reranked_results,
        start=1
    ):
        final_results.append({
            "rank": rank,
            "chunk_id": result["chunk_id"],
            "text": result["text"],
            "video_id": result["video_id"],
            "course_id": result["course_id"],
            "start": result["start"],
            "end": result["end"],
            "rerank_score": result["rerank_score"],
            "rrf_score": result.get("rrf_score"),
            "dense_rank": result.get("dense_rank"),
            "sparse_rank": result.get("sparse_rank"),
        })

    return final_results