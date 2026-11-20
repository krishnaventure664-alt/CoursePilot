from services.embedding_service import get_embedding
from services.vector_store_service import search_chunks
from services.reranker_service import rerank_results
from services.nllb_service import translate_text


COURSE_ID = 1


QUESTIONS = [
    "What is Buddhism?",
    "What is Jainism?",
    "What was the Gupta Empire?",
    "What are the main features of the Vedic Age?",
]


def test_question(question):

    print()
    print("=" * 100)
    print("QUESTION")
    print(question)

    # --------------------------------------------------
    # English retrieval query
    # --------------------------------------------------

    english_embedding = get_embedding(question)

    results = search_chunks(
        query_embedding=english_embedding,
        course_id=COURSE_ID,
        n_results=20
    )

    formatted_results = []

    for i in range(len(results["documents"][0])):

        formatted_results.append(
            {
                "text": results["documents"][0][i],
                "video_id": results["metadatas"][0][i]["video_id"],
                "start": results["metadatas"][0][i]["start"],
                "end": results["metadatas"][0][i]["end"],
                "distance": results["distances"][0][i]
            }
        )

    # --------------------------------------------------
    # English query reranking
    # --------------------------------------------------

    english_ranked = rerank_results(
        query=question,
        search_results=formatted_results,
        top_k=5
    )

    print()
    print("ENGLISH QUERY RERANKING")

    for i, result in enumerate(english_ranked, start=1):

        print(
            f"{i}. "
            f"score={result['rerank_score']:.6f} | "
            f"video={result['video_id']}"
        )

        print(
            result["text"][:300]
        )

    # --------------------------------------------------
    # Translate query to Hindi
    # --------------------------------------------------

    hindi_query = translate_text(
        text=question,
        source_language="eng_Latn",
        target_language="hin_Deva"
    )

    print()
    print("HINDI QUERY")
    print(hindi_query)

    # --------------------------------------------------
    # Hindi query reranking
    #
    # IMPORTANT:
    # We use the SAME retrieved chunks.
    #
    # Therefore this test isolates the reranker.
    # --------------------------------------------------

    hindi_ranked = rerank_results(
        query=hindi_query,
        search_results=formatted_results,
        top_k=5
    )

    print()
    print("HINDI QUERY RERANKING")

    for i, result in enumerate(hindi_ranked, start=1):

        print(
            f"{i}. "
            f"score={result['rerank_score']:.6f} | "
            f"video={result['video_id']}"
        )

        print(
            result["text"][:300]
        )


def main():

    print("=" * 100)
    print("RERANKER LANGUAGE DIAGNOSTIC")
    print("=" * 100)

    for question in QUESTIONS:
        test_question(question)


if __name__ == "__main__":
    main()