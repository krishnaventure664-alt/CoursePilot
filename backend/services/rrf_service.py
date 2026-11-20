def reciprocal_rank_fusion(
    dense_results,
    sparse_results,
    top_k=50,
    k=60
):
    """
    Combine dense and sparse retrieval results using
    Reciprocal Rank Fusion (RRF).

    RRF score:
        1 / (k + rank)

    Rank starts from 1.
    """

    fused_scores = {}

    # -----------------------------
    # Dense retrieval contribution
    # -----------------------------
    for rank, result in enumerate(dense_results, start=1):

        chunk_id = result["chunk_id"]

        score = 1 / (k + rank)

        if chunk_id not in fused_scores:
            fused_scores[chunk_id] = {
                "chunk_id": chunk_id,
                "rrf_score": 0.0,
                "dense_rank": None,
                "sparse_rank": None
            }

        fused_scores[chunk_id]["rrf_score"] += score
        fused_scores[chunk_id]["dense_rank"] = rank

    # -----------------------------
    # Sparse retrieval contribution
    # -----------------------------
    for rank, result in enumerate(sparse_results, start=1):

        chunk_id = result["chunk_id"]

        score = 1 / (k + rank)

        if chunk_id not in fused_scores:
            fused_scores[chunk_id] = {
                "chunk_id": chunk_id,
                "rrf_score": 0.0,
                "dense_rank": None,
                "sparse_rank": None
            }

        fused_scores[chunk_id]["rrf_score"] += score
        fused_scores[chunk_id]["sparse_rank"] = rank

    # -----------------------------
    # Sort by fused score
    # -----------------------------
    ranked_results = sorted(
        fused_scores.values(),
        key=lambda x: x["rrf_score"],
        reverse=True
    )

    return ranked_results[:top_k]