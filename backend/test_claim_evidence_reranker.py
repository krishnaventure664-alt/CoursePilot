from services.hybrid_search_service import hybrid_search
from services.reranker_service import rerank_results


COURSE_ID = 1


TESTS = [
    {
        "name": "SUPPORTED",
        "query": "Buddhism ke founder kaun the?",
        "claim": "Gautam Buddha founded Buddhism."
    },
    {
        "name": "CONTRADICTED",
        "query": "Buddhism ke founder kaun the?",
        "claim": "Bimbisara founded Buddhism."
    },
    {
        "name": "UNSUPPORTED",
        "query": "Buddhism ke founder kaun the?",
        "claim": "Buddhism was founded in 500 BC."
    },
    {
        "name": "SUPPORTED",
        "query": "What was the Indus Valley Civilization?",
        "claim": "The Indus Valley Civilization was a Bronze Age civilization."
    },
    {
        "name": "UNSUPPORTED",
        "query": "What was the Indus Valley Civilization?",
        "claim": "The Indus Valley Civilization developed artificial intelligence."
    },
]


def main():

    for test in TESTS:

        print("\n" + "=" * 110)
        print(test["name"])
        print("=" * 110)

        print("\nOriginal Query:")
        print(test["query"])

        print("\nClaim:")
        print(test["claim"])

        # Retrieve evidence using the normal CoursePilot pipeline.
        retrieved = hybrid_search(
            query=test["query"],
            course_id=COURSE_ID,
            final_top_k=8
        )

        # Prepare the retrieved evidence for direct claim-to-evidence
        # reranking.
        candidates = []

        for result in retrieved:
            candidates.append({
                "chunk_id": result["chunk_id"],
                "text": result["text"],
                "video_id": result["video_id"],
                "course_id": result["course_id"],
                "start": result["start"],
                "end": result["end"],
                "original_rerank_score": result["rerank_score"],
                "rrf_score": result["rrf_score"],
            })

        # IMPORTANT:
        # We are NOT changing production retrieval.
        # We are only testing whether the reranker can judge
        # claim -> evidence relevance.
        claim_reranked = rerank_results(
            query=test["claim"],
            search_results=candidates,
            top_k=len(candidates)
        )

        print("\nClaim → Evidence scores:")

        for rank, result in enumerate(claim_reranked, start=1):

            print("\n" + "-" * 90)

            print(
                f"Rank: {rank} | "
                f"Claim-Evidence Score: "
                f"{result['rerank_score']:.6f}"
            )

            print(
                f"Original Query Rerank: "
                f"{result.get('original_rerank_score', 0.0):.6f}"
            )

            print(
                f"Video: {result['video_id']} | "
                f"Time: {result['start']:.2f} - "
                f"{result['end']:.2f}"
            )

            print(f"Text: {result['text']}")


if __name__ == "__main__":
    main()