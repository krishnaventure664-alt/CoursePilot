from services.search_service import search_course
from services.evidence_service import has_sufficient_evidence


queries = [
            "Explain active recall?",
            "Why is active recall is useful?",
            "active recall kya hai?",
           ]


for query in queries:

    print("\n"+"="*80)
    print("QUERY:",query)


    results = search_course(
        query=query,
        course_id=1,
        n_results=5
    )

    enough_evidence = has_sufficient_evidence(results)

    print("\nTop score:",results[0]["rerank_score"] if results else None)


    if len(results)>=2:
        gap = (
            results[0]["rerank_score"] - results[1]["rerank_score"]
        )

        print("Score gap:",gap)
    else:
        print("Score gap: N/A")

    print("Sufficient evidence:",enough_evidence)