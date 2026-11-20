from services.hybrid_search_service import hybrid_search


COURSE_ID = 1

QUERIES = [
    "What was the Indus Valley Civilization?",
    "बौद्ध धर्म के संस्थापक कौन थे?",
    "Buddhism ke founder kaun the?"
]


for query in QUERIES:

    print("\n" + "=" * 100)
    print("QUERY:", query)
    print("=" * 100)

    results = hybrid_search(
        query=query,
        course_id=COURSE_ID,
        final_top_k=8
    )

    for result in results:

        print("\n" + "-" * 100)

        print("Rank:", result["rank"])
        print("Chunk ID:", result["chunk_id"])
        print("Rerank Score:", result["rerank_score"])
        print("RRF Score:", result["rrf_score"])
        print("Dense Rank:", result["dense_rank"])
        print("Sparse Rank:", result["sparse_rank"])
        print("Video ID:", result["video_id"])
        print("Start:", result["start"])
        print("End:", result["end"])

        print("\nText:")
        print(result["text"])