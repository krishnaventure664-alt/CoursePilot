from services.embedding_service import get_embedding
from services.vector_store_service import search_chunks
from services.reranker_service import rerank_results
from services.nllb_service import translate_text


COURSE_ID = 1

questions = [
    "What was the Indus Valley Civilization?",
    "What are the main features of the Vedic Age?",
    "What is Buddhism?",
    "What is Jainism?",
    "What was the Gupta Empire?",
    "What is the Sangam period?",
    "What is Active Recall?"
]


def retrieve_candidates(query):
    embedding = get_embedding(query)

    results = search_chunks(
        query_embedding=embedding,
        course_id=COURSE_ID,
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

    return formatted_results


for question in questions:

    print("\n" + "=" * 80)
    print("QUESTION:", question)

    # --------------------------------------------------
    # 1. Retrieve candidates using English query
    # --------------------------------------------------

    candidates = retrieve_candidates(question)

    # --------------------------------------------------
    # 2. English reranking
    # --------------------------------------------------

    english_results = rerank_results(
        query=question,
        search_results=candidates,
        top_k=5
    )

    english_score = (
        english_results[0]["rerank_score"]
        if english_results
        else 0
    )

    english_video = (
        english_results[0]["video_id"]
        if english_results
        else "None"
    )

    # --------------------------------------------------
    # 3. Translate query to Hindi
    # --------------------------------------------------

    hindi_query = translate_text(
        text=question,
        source_language="eng_Latn",
        target_language="hin_Deva"
    )

    # --------------------------------------------------
    # 4. Hindi reranking
    # --------------------------------------------------

    hindi_results = rerank_results(
        query=hindi_query,
        search_results=candidates,
        top_k=5
    )

    hindi_score = (
        hindi_results[0]["rerank_score"]
        if hindi_results
        else 0
    )

    hindi_video = (
        hindi_results[0]["video_id"]
        if hindi_results
        else "None"
    )

    # --------------------------------------------------
    # 5. Compare
    # --------------------------------------------------

    max_score = max(
        english_score,
        hindi_score
    )

    print("Hindi Query:", hindi_query)

    print("\nEnglish Reranker")
    print("Score:", english_score)
    print("Video:", english_video)

    print("\nHindi Reranker")
    print("Score:", hindi_score)
    print("Video:", hindi_video)

    print("\nMAX SCORE:", max_score)