from services.bge_m3_service import encode_text
from services.bge_m3_vector_store_service import search_dense_chunks


QUERY = "What was the Indus Valley Civilization?"


print("=" * 80)
print("BGE-M3 DENSE RETRIEVAL TEST")
print("=" * 80)

print("\nQuery:")
print(QUERY)

encoded = encode_text(QUERY)

results = search_dense_chunks(
    query_embedding=encoded["dense"],
    course_id=1,
    n_results=10
)

print("\nTop results:\n")

documents = results["documents"][0]
metadatas = results["metadatas"][0]
distances = results["distances"][0]

for i in range(len(documents)):
    print("-" * 80)
    print(f"Rank: {i + 1}")
    print(f"Distance: {distances[i]:.4f}")
    print(f"Video ID: {metadatas[i]['video_id']}")
    print(f"Start: {metadatas[i]['start']}")
    print(f"End: {metadatas[i]['end']}")
    print("\nText:")
    print(documents[i][:500])

print("\n" + "=" * 80)