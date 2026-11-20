from evaluation_questions import evaluation_questions

from services.search_service import search_course
from services.evidence_service import has_sufficient_evidence


course_id = 1

correct = 0
total = len(evaluation_questions)


for index, item in enumerate(evaluation_questions, start=1):

    question = item["question"]
    expected = item["expected"]

    results = search_course(
        query=question,
        course_id=course_id,
        n_results=5
    )

    actual = (
        "answerable"
        if has_sufficient_evidence(results)
        else "unanswerable"
    )

    if actual == expected:
        correct += 1

    print("\n" + "=" * 80)

    print(f"Question {index}/{total}")
    print("Question:", question)

    print("Expected:", expected)
    print("Actual:", actual)

    if results:
        print(
            "Top rerank score:",
            results[0]["rerank_score"]
        )

    print("Result:", "CORRECT" if actual == expected else "WRONG")


accuracy = (correct / total) * 100


print("\n" + "=" * 80)

print("EVALUATION COMPLETE")

print("Correct:", correct, "/", total)

print("Accuracy:", f"{accuracy:.2f}%")