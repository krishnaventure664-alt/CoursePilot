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

_cached_seed_chunks: list[dict] | None = None
_seed_chunks_lock = threading.Lock()


def _get_seed_chunks() -> list[dict]:
    global _cached_seed_chunks
    if _cached_seed_chunks is not None:
        return _cached_seed_chunks

    with _seed_chunks_lock:
        if _cached_seed_chunks is not None:
            return _cached_seed_chunks

        import json
        from pathlib import Path
        backend_dir = Path(__file__).resolve().parents[1]
        all_seed = backend_dir / "all_courses_chunks_seed.json"
        c18_seed = backend_dir / "course18_chunks_seed.json"

        chunks = []
        target_file = all_seed if all_seed.exists() else (c18_seed if c18_seed.exists() else None)
        if target_file:
            try:
                with open(target_file, "r", encoding="utf-8") as f:
                    chunks = json.load(f)
            except Exception:
                chunks = []

        _cached_seed_chunks = chunks
        return _cached_seed_chunks


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
        # First check in-memory seed chunks
        seed_chunks = _get_seed_chunks()
        seed_map = {c["id"]: c for c in seed_chunks}
        still_missing = []
        for cid in missing_ids:
            if cid in seed_map:
                sc = seed_map[cid]
                meta = sc.get("metadata", {})
                c_item = {
                    "chunk_id": sc["id"],
                    "text": sc["document"],
                    "video_id": meta.get("video_id", ""),
                    "course_id": meta.get("course_id", ""),
                    "start": meta.get("start", 0),
                    "end": meta.get("end", 0),
                }
                cached_results.append(c_item)
                with _chunk_details_lock:
                    if len(_chunk_details_cache) > 2000:
                        _chunk_details_cache.pop(next(iter(_chunk_details_cache)))
                    _chunk_details_cache[cid] = c_item
            else:
                still_missing.append(cid)

        if still_missing:
            from services.bge_m3_vector_store_service import collection
            try:
                results = collection.get(
                    ids=still_missing,
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

    is_zero_dense = not dense_query or all(v == 0.0 for v in dense_query)
    is_empty_sparse = not sparse_query

    dense_results = []
    sparse_results = []
    rrf_results = []

    if not is_zero_dense or not is_empty_sparse:
        # --------------------------------------------------
        # 2 & 3. Concurrent Dense & Sparse retrieval
        # --------------------------------------------------
        from concurrent.futures import ThreadPoolExecutor

        def _fetch_dense():
            if is_zero_dense:
                return None
            return search_dense_chunks(
                query_embedding=dense_query,
                course_id=effective_course_id,
                n_results=DENSE_TOP_K
            )

        def _fetch_sparse():
            if is_empty_sparse:
                return []
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

    reranker_candidates = []

    if rrf_results:
        chunk_ids = [
            result["chunk_id"]
            for result in rrf_results
        ]

        chunk_details = get_chunk_details(chunk_ids)

        chunk_map = {
            chunk["chunk_id"]: chunk
            for chunk in chunk_details
        }

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
        # Cloud multi-course fallback when local PyTorch model weights are omitted
        try:
            import re, math
            from collections import Counter

            candidate_items = []
            seed_chunks = _get_seed_chunks()

            # 1. Check all seeded course chunks
            for c in seed_chunks:
                meta = c.get("metadata", {})
                c_course_id = meta.get("course_id")
                if str(c_course_id) == str(effective_course_id):
                    candidate_items.append({
                        "id": c["id"],
                        "document": c["document"],
                        "metadata": meta,
                    })

            # 2. Check live ChromaDB collection (covers newly indexed courses)
            if not candidate_items:
                from services.bge_m3_vector_store_service import collection
                try:
                    c_data = collection.get(
                        where={"course_id": effective_course_id},
                        include=["documents", "metadatas"],
                    )
                    docs = c_data.get("documents", [])
                    metas = c_data.get("metadatas", [])
                    ids = c_data.get("ids", [])
                    for i in range(len(docs)):
                        candidate_items.append({
                            "id": ids[i],
                            "document": docs[i],
                            "metadata": metas[i] if i < len(metas) else {},
                        })
                except Exception:
                    pass

            # 3. Check SQLite detailed notes and lecture notes as dynamic fallback
            if not candidate_items:
                from services.course_db_service import get_connection
                try:
                    with get_connection() as conn:
                        rows = conn.execute(
                            "SELECT video_id, content FROM video_detailed_notes WHERE course_id = ?",
                            (effective_course_id,)
                        ).fetchall()
                        if not rows:
                            rows = conn.execute(
                                "SELECT video_id, content FROM video_notes WHERE course_id = ?",
                                (effective_course_id,)
                            ).fetchall()
                        for v_id, content in rows:
                            if not content:
                                continue
                            secs = re.split(r"(?=\n###?\s+)", content)
                            for s_idx, sec in enumerate(secs):
                                sec_str = sec.strip()
                                if len(sec_str) >= 50:
                                    candidate_items.append({
                                        "id": f"course_{effective_course_id}_{v_id}_sec_{s_idx}",
                                        "document": sec_str,
                                        "metadata": {
                                            "course_id": effective_course_id,
                                            "video_id": v_id,
                                            "start": 0,
                                            "end": 60,
                                        }
                                    })
                except Exception:
                    pass

            if candidate_items:
                stop_words = {
                    "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of", "with",
                    "by", "as", "is", "are", "was", "were", "it", "its", "this", "that", "from",
                    "be", "what", "which", "how", "explain", "can", "you", "tell", "me", "about"
                }
                doc_tokens = [re.findall(r"\w+", c["document"].lower()) for c in candidate_items]
                N = len(doc_tokens)
                avgdl = (sum(len(d) for d in doc_tokens) / (N or 1)) or 1.0
                k1 = 1.5
                b = 0.75

                dfs = Counter()
                for d in doc_tokens:
                    dfs.update(set(d))

                q_tokens = [w for w in re.findall(r"\w+", query.lower()) if w not in stop_words]
                if not q_tokens:
                    q_tokens = re.findall(r"\w+", query.lower())

                def _bm25_score(d_tokens):
                    counts = Counter(d_tokens)
                    dl = len(d_tokens) or 1
                    score = 0.0
                    for w in q_tokens:
                        if w in counts:
                            df = dfs.get(w, 0)
                            idf = math.log(1.0 + (N - df + 0.5) / (df + 0.5))
                            f = counts[w]
                            num = f * (k1 + 1.0)
                            denom = f + k1 * (1.0 - b + b * (dl / avgdl))
                            score += idf * (num / denom)
                    return score

                scored = []
                for c, d in zip(candidate_items, doc_tokens):
                    s = _bm25_score(d)
                    if s > 0:
                        scored.append((c, s))

                scored.sort(key=lambda x: x[1], reverse=True)

                if not scored:
                    scored = [(c, 0.0) for c in candidate_items[:final_top_k]]

                for c, sc in scored[:final_top_k]:
                    meta = c.get("metadata", {})
                    reranker_candidates.append({
                        "chunk_id": c["id"],
                        "text": c["document"],
                        "video_id": meta.get("video_id", ""),
                        "course_id": meta.get("course_id", effective_course_id),
                        "start": meta.get("start", 0),
                        "end": meta.get("end", 0),
                        "rrf_score": sc,
                        "dense_rank": 1,
                        "sparse_rank": 1,
                    })
        except Exception:
            pass

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