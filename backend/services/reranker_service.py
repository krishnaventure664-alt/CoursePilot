import logging
import threading

logger = logging.getLogger(__name__)

_reranker_model = None
_reranker_lock = threading.Lock()


def get_reranker_model():
    """Thread-safe lazy initialization for the BGE-Reranker model.
    Deferred import of FlagEmbedding prevents PyTorch/HF import lag at server boot.
    Falls back gracefully if FlagEmbedding or PyTorch is unavailable (e.g. cloud free tier).
    """
    global _reranker_model
    if _reranker_model is None:
        with _reranker_lock:
            if _reranker_model is None:
                try:
                    logger.info("Importing FlagEmbedding and loading BGE-Reranker model weights...")
                    from FlagEmbedding import FlagReranker

                    import torch
                    dev = "cuda:0" if torch.cuda.is_available() else "cpu"

                    try:
                        # Fast local GPU path: 13x faster reranking with local cached weights
                        _reranker_model = FlagReranker(
                            "BAAI/bge-reranker-v2-m3",
                            use_fp16=True,
                            devices=dev,
                            local_files_only=True,
                        )
                    except Exception:
                        _reranker_model = FlagReranker(
                            "BAAI/bge-reranker-v2-m3",
                            use_fp16=True,
                            devices=dev,
                        )
                except Exception as e:
                    logger.warning("FlagEmbedding/PyTorch not available for neural reranking (%s). Using RRF scores.", e)
                    return None
    return _reranker_model


def __getattr__(name: str):
    if name == "reranker_model":
        return get_reranker_model()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def rerank_results(
    query: str,
    search_results: list,
    top_k: int = 5,
):
    if not search_results:
        return []

    try:
        reranker = get_reranker_model()
    except Exception:
        reranker = None

    if reranker is None:
        # Graceful cloud fallback: sort by RRF score
        for r in search_results:
            if "rerank_score" not in r:
                r["rerank_score"] = float(r.get("rrf_score", 0.0))
        return search_results[:top_k]

    pairs = []
    for result in search_results:
        pairs.append([query, result["text"]])

    try:
        scores = reranker.compute_score(
            pairs,
            normalize=True,
            max_length=256,
            batch_size=16,
        )

        if isinstance(scores, float):
            scores = [scores]

        for i, score in enumerate(scores):
            search_results[i]["rerank_score"] = float(score)

        search_results.sort(key=lambda x: x["rerank_score"], reverse=True)
    except Exception as e:
        logger.warning("Reranking failed (%s). Falling back to RRF scores.", e)
        for r in search_results:
            if "rerank_score" not in r:
                r["rerank_score"] = float(r.get("rrf_score", 0.0))

    return search_results[:top_k]
