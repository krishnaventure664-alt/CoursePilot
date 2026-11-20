from services.hybrid_search_service import hybrid_search
from services.reranker_service import rerank_results


COURSE_ID = 1


TESTS = [
    {
        "name": "English claim → Hindi evidence",
        "query": "Buddhism ke founder kaun the?",
        "claim": "Gautam Buddha founded Buddhism."
    },
    {
        "name": "Hindi claim → Hindi evidence",
        "query": "बौद्ध धर्म के संस्थापक कौन थे?",
        "claim": "गौतम बुद्ध बौद्ध धर्म के संस्थापक थे।"
    },
    {
        "name": "Hinglish claim → Hindi evidence",
        "query": "Buddhism ke founder kaun the?",
        "claim": "Gautam Buddha Buddhism ke founder the."
    },
    {
        "name": "English unsupported claim → Hindi evidence",
        "query": "Buddhism ke founder kaun the?",
        "claim": "Buddhism was founded in 500 BC."
    },
]


def main():

    for test in TESTS:

        print("\n" + "=" * 110)
        print(test["name"])
        print("=" * 110)

        print("\nQuery:")
        print(test["query"])

        print("\nClaim:")
        print(test["claim"])

        retrieved = hybrid_search(
            query=test["query"],
            course_id=COURSE_ID,
            final_top_k=8
        )

        candidates = []

        for result in retrieved:
            candidates.append({
                "chunk_id": result["chunk_id"],
                "text": result["text"],
                "video_id": result["video_id"],
                "course_id": result["course_id"],
                "start": result["start"],
                "end": result["end"],
            })

        claim_results = rerank_results(
            query=test["claim"],
            search_results=candidates,
            top_k=len(candidates)
        )

        print("\nClaim → Evidence scores:")

        for rank, result in enumerate(claim_results, start=1):

            print("\n" + "-" * 90)

            print(
                f"Rank: {rank} | "
                f"Score: {result['rerank_score']:.6f}"
            )

            print(
                f"Video: {result['video_id']} | "
                f"Time: {result['start']:.2f} - "
                f"{result['end']:.2f}"
            )

            print(f"Text: {result['text']}")


if __name__ == "__main__":
    main()