from services.hybrid_search_service import hybrid_search
from services.evidence_assessment_service import assess_evidence


COURSE_ID = 1

QUERIES = [
    "Buddhism ke founder kaun the?",
    "What was the Indus Valley Civilization?",
    "What is machine learning?"
]


for query in QUERIES:

    print("\n" + "=" * 100)
    print("QUERY:", query)
    print("=" * 100)

    # --------------------------------------------------
    # Retrieve evidence
    # --------------------------------------------------

    results = hybrid_search(
        query=query,
        course_id=COURSE_ID,
        final_top_k=8
    )

    # --------------------------------------------------
    # Assess evidence
    # --------------------------------------------------

    assessment = assess_evidence(
        query=query,
        search_results=results
    )

    print("\nEVIDENCE ASSESSMENT")
    print("-" * 100)

    print("Supported:", assessment["supported"])
    print("Reason:", assessment["reason"])
    print("Confidence:", assessment["confidence"])
    print("Top Score:", assessment.get("top_score"))
    print("Score Gap:", assessment.get("score_gap"))

    print("\nSupporting Chunks:", len(
        assessment["supporting_chunks"]
    ))

    for chunk in assessment["supporting_chunks"][:5]:

        print("\n" + "-" * 80)

        print("Chunk ID:", chunk["chunk_id"])
        print("Rerank Score:", chunk["rerank_score"])
        print("Video ID:", chunk["video_id"])
        print("Start:", chunk["start"])
        print("End:", chunk["end"])

        print("\nText:")
        print(chunk["text"])