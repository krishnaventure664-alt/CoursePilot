from services.language_translation_service import (
    translate_to_hindi,
    translate_to_hinglish
)


technical_terms = [
    "Active Recall",
    "Machine Learning",
    "Gradient Descent",
    "RAG",
    "Embeddings",
    "Python",
    "Java",
    "ArrayList",
    "HashMap",
]


answer = """
Active Recall helps students improve retention.

Machine Learning models learn patterns from data,
and Gradient Descent helps optimize their parameters.

RAG retrieves relevant information before generating
an answer, while Embeddings represent text as numerical
vectors.

Python and Java are programming languages.
Java provides data structures such as ArrayList and HashMap.
"""


print("\n" + "=" * 80)
print("ORIGINAL ENGLISH")
print("=" * 80)

print(answer)


print("\n" + "=" * 80)
print("HINDI")
print("=" * 80)

hindi = translate_to_hindi(
    answer,
    technical_terms
)

print(hindi)


print("\n" + "=" * 80)
print("HINGLISH")
print("=" * 80)

hinglish = translate_to_hinglish(
    answer,
    technical_terms
)

print(hinglish)