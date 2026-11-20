from services.hybrid_search_service import hybrid_search
from services.claim_verification_service import verify_claim


COURSE_ID = 1


TESTS = [
    {
        "query": "Buddhism ke founder kaun the?",
        "claim": "Gautam Buddha founded Buddhism."
    },
    {
        "query": "Buddhism ke founder kaun the?",
        "claim": "Bimbisara founded Buddhism."
    },
    {
        "query": "Buddhism ke founder kaun the?",
        "claim": "Buddhism was founded in 500 BC."
    }
]


for test in TESTS:

    query = test["query"]
    claim = test["claim"]

    print("\n" + "=" * 100)
    print("QUERY:", query)
    print("CLAIM:", claim)
    print("=" * 100)

    results = hybrid_search(
        query=query,
        course_id=COURSE_ID,
        final_top_k=8
    )

    verification = verify_claim(
        query=query,
        claim=claim,
        evidence_chunks=results
    )

    print("\nVERIFICATION")
    print("-" * 100)

    print("Verdict:", verification["verdict"])
    print("Confidence:", verification["confidence"])
    print("Reason:", verification["reason"])