from services.hybrid_search_service import hybrid_search
from services.reranker_service import rerank_results


COURSE_ID = 1


TESTS = [
    # =========================================================
    # SUPPORTED
    # =========================================================

    {
        "domain": "History",
        "type": "supported",
        "query": "Buddhism ke founder kaun the?",
        "claim": "Gautam Buddha founded Buddhism."
    },

    {
        "domain": "History",
        "type": "supported",
        "query": "What was the Indus Valley Civilization?",
        "claim": "The Indus Valley Civilization was a Bronze Age civilization."
    },

    # =========================================================
    # UNSUPPORTED
    # =========================================================

    {
        "domain": "History",
        "type": "unsupported",
        "query": "Buddhism ke founder kaun the?",
        "claim": "Buddhism was founded in 500 BC."
    },

    {
        "domain": "History",
        "type": "unsupported",
        "query": "What was the Indus Valley Civilization?",
        "claim": "The Indus Valley Civilization developed artificial intelligence."
    },

    # =========================================================
    # CONTRADICTED / WRONG RELATIONSHIP
    # =========================================================

    {
        "domain": "History",
        "type": "contradicted",
        "query": "Buddhism ke founder kaun the?",
        "claim": "Bimbisara founded Buddhism."
    },

    {
        "domain": "History",
        "type": "contradicted",
        "query": "बौद्ध धर्म के संस्थापक कौन थे?",
        "claim": "चंद्रगुप्त मौर्य बौद्ध धर्म के संस्थापक थे।"
    },

    # =========================================================
    # MULTILINGUAL
    # =========================================================

    {
        "domain": "History",
        "type": "supported_hindi",
        "query": "बौद्ध धर्म के संस्थापक कौन थे?",
        "claim": "गौतम बुद्ध बौद्ध धर्म के संस्थापक थे।"
    },

    {
        "domain": "History",
        "type": "supported_hinglish",
        "query": "Buddhism ke founder kaun the?",
        "claim": "Gautam Buddha Buddhism ke founder the."
    },
]


def get_claim_evidence_scores(query, claim):

    retrieved = hybrid_search(
        query=query,
        course_id=COURSE_ID,
        final_top_k=8
    )

    if not retrieved:
        return []

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
        query=claim,
        search_results=candidates,
        top_k=len(candidates)
    )

    return claim_results


def main():

    print("\n")
    print("=" * 110)
    print("COURSEPILOT CROSS-DOMAIN / ADVERSARIAL EVALUATION")
    print("=" * 110)

    for index, test in enumerate(TESTS, start=1):

        print("\n")
        print("#" * 110)
        print(f"TEST {index}")
        print("#" * 110)

        print(f"\nDomain: {test['domain']}")
        print(f"Type:   {test['type']}")

        print(f"\nQuery:")
        print(test["query"])

        print(f"\nClaim:")
        print(test["claim"])

        results = get_claim_evidence_scores(
            query=test["query"],
            claim=test["claim"]
        )

        if not results:
            print("\nNO EVIDENCE RETRIEVED")
            continue

        print("\nClaim → Evidence scores:")

        for rank, result in enumerate(results, start=1):

            print("\n" + "-" * 90)

            print(
                f"Rank: {rank} | "
                f"Score: {result['rerank_score']:.6f}"
            )

            print(
                f"Video: {result['video_id']} | "
                f"Time: {result['start']:.2f} - {result['end']:.2f}"
            )

            print(f"Text: {result['text']}")


if __name__ == "__main__":
    main()