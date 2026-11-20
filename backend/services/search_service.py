from services.embedding_service import get_embedding
from services.vector_store_service import search_chunks
from services.reranker_service import rerank_results
from services.query_processing_service import normalize_query, detect_language
from services.nllb_service import translate_text


def prepare_retrieval_query(query: str):
    language = detect_language(query)

    if language == "english":
        return normalize_query(query)

    if language == "hindi":
        english_query = translate_text(
            text=query,
            source_language="hin_Deva",
            target_language="eng_Latn"
        )

        return normalize_query(english_query)

    if language == "hinglish":
        return normalize_query(query)

    return normalize_query(query)


def search_course(query, course_id, n_results=5):

    original_query = query

    # --------------------------------------------------
    # STEP 1: Prepare primary retrieval query
    # --------------------------------------------------

    retrieval_query = prepare_retrieval_query(original_query)

    # --------------------------------------------------
    # STEP 2: Semantic retrieval
    #
    # Retrieve candidates only ONCE.
    # --------------------------------------------------

    query_embedding = get_embedding(retrieval_query)

    results = search_chunks(
        query_embedding=query_embedding,
        course_id=course_id,
        n_results=10
    )

    formatted_results = []

    for i in range(len(results["documents"][0])):

        formatted_results.append({
            "text": results["documents"][0][i],
            "video_id": results["metadatas"][0][i]["video_id"],
            "start": results["metadatas"][0][i]["start"],
            "end": results["metadatas"][0][i]["end"],
            "distance": results["distances"][0][i]
        })

    if not formatted_results:
        return []

    # --------------------------------------------------
    # STEP 3: English reranking
    # --------------------------------------------------

    english_results = rerank_results(
        query=original_query,
        search_results=formatted_results,
        top_k=len(formatted_results)
    )

    # Create lookup using text
    english_scores = {}

    for result in english_results:
        english_scores[result["text"]] = result["rerank_score"]

    # --------------------------------------------------
    # STEP 4: Hindi query
    #
    # Only create Hindi query for English/Hinglish
    # questions. Hindi questions already contain Hindi.
    # --------------------------------------------------

    language = detect_language(original_query)

    hindi_query = None

    if language == "english" or language == "hinglish":

        hindi_query = translate_text(
            text=original_query,
            source_language="eng_Latn",
            target_language="hin_Deva"
        )

    elif language == "hindi":

        hindi_query = original_query

    # --------------------------------------------------
    # STEP 5: Hindi reranking
    # --------------------------------------------------

    hindi_results = rerank_results(
        query=hindi_query,
        search_results=formatted_results,
        top_k=len(formatted_results)
    )

    hindi_scores = {}

    for result in hindi_results:
        hindi_scores[result["text"]] = result["rerank_score"]

    # --------------------------------------------------
    # STEP 6: Combine scores
    #
    # For now we use the stronger language signal.
    # This is deliberately simple and easy to evaluate.
    # --------------------------------------------------

    combined_results = []

    for result in formatted_results:

        text = result["text"]

        english_score = english_scores.get(text, 0.0)
        hindi_score = hindi_scores.get(text, 0.0)

        combined_score = max(
            english_score,
            hindi_score
        )

        combined_result = result.copy()

        combined_result["english_score"] = english_score
        combined_result["hindi_score"] = hindi_score
        combined_result["rerank_score"] = combined_score

        combined_results.append(combined_result)

    # --------------------------------------------------
    # STEP 7: Sort by combined score
    # --------------------------------------------------

    combined_results.sort(
        key=lambda x: x["rerank_score"],
        reverse=True
    )

    # --------------------------------------------------
    # STEP 8: Return top results
    # --------------------------------------------------

    return combined_results[:n_results]