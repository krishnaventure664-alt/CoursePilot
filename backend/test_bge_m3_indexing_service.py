from services.bge_m3_indexing_service import (
    initialize_bge_m3_index,
    index_bge_m3_chunk
)

from services.bge_m3_vector_store_service import (
    search_dense_chunks,
    delete_course_dense_chunks
)

from services.sparse_index_service import (
    get_postings,
    delete_chunks
)


print("=" * 70)
print("BGE-M3 INDEXING INTEGRATION TEST")
print("=" * 70)


# --------------------------------------------------
# Test data
# --------------------------------------------------

course_id = 999998
chunk_id = "bge_m3_test_chunk_001"

text = """
Machine learning is a field of artificial intelligence
where computers learn patterns from data.
"""


# --------------------------------------------------
# Initialize indexes
# --------------------------------------------------

initialize_bge_m3_index()


# --------------------------------------------------
# Index the chunk
# --------------------------------------------------

index_bge_m3_chunk(
    chunk_id=chunk_id,
    text=text,
    video_id="test_video",
    course_id=course_id,
    start=0.0,
    end=10.0
)


print("\nChunk indexed successfully.")


# --------------------------------------------------
# Test dense index
# --------------------------------------------------

from services.bge_m3_service import encode_text

query_result = encode_text(
    "What is machine learning?"
)

dense_results = search_dense_chunks(
    query_embedding=query_result["dense"],
    course_id=course_id,
    n_results=5
)


print("\n")
print("DENSE INDEX RESULT")
print("-" * 70)

print("Documents:")

for document in dense_results["documents"][0]:
    print(document)

print("\nMetadata:")

for metadata in dense_results["metadatas"][0]:
    print(metadata)

print("\nDistances:")

for distance in dense_results["distances"][0]:
    print(distance)


# --------------------------------------------------
# Test sparse index
# --------------------------------------------------

print("\n")
print("SPARSE INDEX RESULT")
print("-" * 70)

for token_id in query_result["sparse"]:

    postings = get_postings(token_id)

    if postings:
        print(
            f"Token {token_id}:",
            postings
        )


# --------------------------------------------------
# Cleanup
# --------------------------------------------------

delete_course_dense_chunks(course_id)

delete_chunks(
    [chunk_id]
)


print("\n")
print("Test data deleted.")


print("\n")
print("=" * 70)
print("INTEGRATION TEST COMPLETE")
print("=" * 70)