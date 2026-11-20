from services.vector_store_service import collection
from services.term_extraction_service import extract_course_terms


# --------------------------------------------------
# Get real transcript chunks from the course
# --------------------------------------------------

results = collection.get(
    where={
        "course_id": 1
    },
    limit=5
)


documents = results["documents"]


# Combine a few real course chunks
course_text = "\n\n".join(
    documents
)


print("\n" + "=" * 80)
print("REAL COURSE TEXT")
print("=" * 80)

print(course_text)


# --------------------------------------------------
# Extract technical terms
# --------------------------------------------------

print("\n" + "=" * 80)
print("EXTRACTED COURSE TERMS")
print("=" * 80)

terms = extract_course_terms(
    course_text
)


for index, term in enumerate(
    terms,
    start=1
):

    print(
        f"{index}. {term}"
    )