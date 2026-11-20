from services.hybrid_search_service import hybrid_search


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


COURSE_ID = 1


def main():
    for test in TESTS:
        print("\n" + "=" * 100)
        print(test["name"])
        print("=" * 100)

        print("\nQUERY:")
        print(test["query"])

        print("\nCLAIM:")
        print(test["claim"])

        results = hybrid_search(
            query=test["query"],
            course_id=COURSE_ID,
            final_top_k=8
        )

        print("\nRETRIEVED EVIDENCE:")

        for result in results:
            print("\n" + "-" * 80)
            print(
                f"Rank: {result['rank']} | "
                f"Rerank: {result['rerank_score']:.6f} | "
                f"RRF: {result['rrf_score']:.6f}"
            )
            print(f"Video: {result['video_id']}")
            print(f"Time: {result['start']:.2f} - {result['end']:.2f}")
            print(f"Text: {result['text']}")


if __name__ == "__main__":
    main()