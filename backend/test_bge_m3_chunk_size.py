from services.bge_m3_service import encode_text


texts = [
    "Machine learning is a field of artificial intelligence where computers learn patterns from data.",
    
    """
    The Indus Valley Civilization was one of the earliest urban civilizations.
    Major sites included Harappa and Mohenjo-daro. The civilization developed
    sophisticated urban planning, drainage systems, trade networks, and craft
    production.
    """,

    """
    Active Recall is a learning technique in which a learner actively tries
    to retrieve information from memory instead of simply rereading the material.
    It can be used through questioning, self-testing, flashcards, and practice
    questions.
    """
]


print("=" * 70)
print("BGE-M3 SPARSE INDEX SIZE TEST")
print("=" * 70)


for i, text in enumerate(texts, start=1):

    result = encode_text(text)

    print(f"\nTEXT {i}")
    print("-" * 70)

    print("Characters:", len(text))
    print("Words:", len(text.split()))
    print("Sparse terms:", len(result["sparse"]))


print("\n")
print("=" * 70)
print("TEST COMPLETE")
print("=" * 70)