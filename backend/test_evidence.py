from services.search_service import search_course
from services.evidence_service import has_sufficient_evidence


course_id = 1

questions = [
    "What is active recall?",
    "Explain active recall.",
    "Why is active recall useful?",
    "active recall kya hai?",
    "active recall kya hota hai?"
]


for question in questions:

    print("\n" + "=" * 100)
    print("QUESTION:", question)
    print("=" * 100)

    results = search_course(
        query=question,
        course_id=course_id,
        n_results=5
    )

    print("\nEvidence decision:",
          has_sufficient_evidence(results))

    for i, result in enumerate(results, start=1):

        print("\n" + "-" * 100)
        print(f"RESULT {i}")

        print("Rerank score:",
              result["rerank_score"])

        print("Vector distance:",
              result["distance"])

        print("Video ID:",
              result["video_id"])

        print("Start:",
              result["start"])

        print("End:",
              result["end"])

        print("TEXT:")
        print(result["text"])