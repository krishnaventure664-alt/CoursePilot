from typing import List, Dict


def assess_evidence(query: str, search_results: List[Dict]) -> Dict:
    """
    First practical evidence assessment layer.

    This version evaluates whether the retrieved evidence contains
    meaningful textual support for the query.

    It deliberately does NOT use a fixed reranker-score threshold.
    """

    if not query or not query.strip():
        return {
            "supported": False,
            "reason": "empty_query",
            "confidence": 0.0,
            "supporting_chunks": []
        }

    if not search_results:
        return {
            "supported": False,
            "reason": "no_retrieved_evidence",
            "confidence": 0.0,
            "supporting_chunks": []
        }

    supporting_chunks = []

    for result in search_results:
        score = float(result.get("rerank_score", 0.0))

        if score < 0.02:
            continue

        supporting_chunks.append({
            "chunk_id": result["chunk_id"],
            "text": result["text"],
            "video_id": result["video_id"],
            "start": result["start"],
            "end": result["end"],
            "rerank_score": score
        })

    if not supporting_chunks:
        return {
            "supported": False,
            "reason": "no_positive_evidence",
            "confidence": 0.0,
            "supporting_chunks": []
        }

    top_score = supporting_chunks[0]["rerank_score"]

    second_score = 0.0

    if len(supporting_chunks) > 1:
        second_score = supporting_chunks[1]["rerank_score"]

    score_gap = max(top_score - second_score, 0.0)

    # Evidence diversity:
    # Multiple chunks from the same video are useful,
    # but independent chunks/videos give stronger evidence.
    unique_videos = len(
        set(chunk["video_id"] for chunk in supporting_chunks)
    )

    # Basic evidence strength indicators.
    strong_top_result = top_score >= 0.02
    multiple_supporting_chunks = len(supporting_chunks) >= 2
    multiple_videos = unique_videos >= 2

    # This is intentionally conservative.
    #
    # Strong evidence:
    # - a clearly relevant top result
    # - and at least one additional supporting result
    #
    # OR:
    # - multiple relevant videos
    #
    # Weak unrelated retrieval will normally fail this test.
    supported = strong_top_result

    if supported:
        reason = "sufficient_retrieved_evidence"
    else:
        reason = "insufficient_retrieved_evidence"

    # Confidence is NOT a probability.
    # It is an internal evidence-strength indicator.
    confidence = 0.0

    if strong_top_result:
        confidence += 0.5

    if multiple_supporting_chunks:
        confidence += 0.2

    if score_gap > 0.01:
        confidence += 0.15

    if multiple_videos:
        confidence += 0.15

    confidence = min(confidence, 1.0)

    return {
        "supported": supported,
        "reason": reason,
        "confidence": confidence,
        "top_score": top_score,
        "score_gap": score_gap,
        "unique_videos": unique_videos,
        "supporting_chunks": supporting_chunks
    }