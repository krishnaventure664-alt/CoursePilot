from services.concept_classifier_service import verify_concept_candidate


transcript = """
This lecture introduces several important concepts.

Active Recall is a learning technique used in this course.
In Ancient History, Active Recall helps students remember information.

Machine Learning allows computers to learn patterns from data.
Gradient Descent is an optimization algorithm used to train models.

RAG stands for Retrieval Augmented Generation.
RAG can retrieve relevant information before generating an answer.

The Indus Valley Civilization was an important civilization.
It is also called the सिंधु सभ्यता in Hindi.

Gradient Descent model parameters can be adjusted during training.
RAG relevant information can be retrieved from the database.
"""


valid_candidates = [
    "RAG",
    "Machine Learning",
    "Gradient Descent",
    "Active Recall",
    "Indus Valley Civilization",
]

invalid_candidates = [
    "Gradient Descent model",
    "RAG relevant",
    "RAG relevant information",
    "relevant information",
    "answer generate",
]


print("=" * 80)
print("VALID CONCEPT TEST")
print("=" * 80)

valid_passed = 0

for candidate in valid_candidates:

    result = verify_concept_candidate(
        candidate=candidate,
        transcript_text=transcript
    )

    passed = result is not None

    if passed:
        valid_passed += 1

    print(
        f"{candidate:<35} -> "
        f"{'ACCEPTED' if passed else 'REJECTED'}"
    )


print()
print("=" * 80)
print("INVALID CONCEPT TEST")
print("=" * 80)

invalid_passed = 0

for candidate in invalid_candidates:

    result = verify_concept_candidate(
        candidate=candidate,
        transcript_text=transcript
    )

    passed = result is None

    if passed:
        invalid_passed += 1

    print(
        f"{candidate:<35} -> "
        f"{'REJECTED ✓' if passed else 'ACCEPTED ✗'}"
    )


print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)

print(
    f"Valid concepts correctly accepted: "
    f"{valid_passed}/{len(valid_candidates)}"
)

print(
    f"Invalid candidates correctly rejected: "
    f"{invalid_passed}/{len(invalid_candidates)}"
)

total = len(valid_candidates) + len(invalid_candidates)
correct = valid_passed + invalid_passed

print(
    f"Overall: {correct}/{total}"
)