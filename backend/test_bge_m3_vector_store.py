from services.bge_m3_vector_store_service import (
    store_dense_chunk,
    search_dense_chunks,
    delete_course_dense_chunks
)


print("=" * 70)
print("BGE-M3 DENSE VECTOR STORE TEST")
print("=" * 70)


course_id = 999999
chunk_id = "dense_test_chunk_001"

embedding = [0.1] * 1024


store_dense_chunk(
    chunk_id=chunk_id,
    text="Machine learning is a field of artificial intelligence.",
    embedding=embedding,
    video_id="test_video",
    course_id=course_id,
    start=0.0,
    end=10.0
)


results = search_dense_chunks(
    query_embedding=embedding,
    course_id=course_id,
    n_results=5
)


print("\nRetrieved documents:")

for document in results["documents"][0]:
    print(document)


print("\nRetrieved metadata:")

for metadata in results["metadatas"][0]:
    print(metadata)


print("\nRetrieved distances:")

for distance in results["distances"][0]:
    print(distance)


delete_course_dense_chunks(course_id)


print("\nCourse test data deleted.")


print("\n")
print("=" * 70)
print("TEST COMPLETE")
print("=" * 70)