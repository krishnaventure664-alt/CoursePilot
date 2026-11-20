import chromadb

from services.bge_m3_service import encode_text
from services.sparse_index_service import search_sparse_chunks


QUERY = "What was the Indus Valley Civilization?"


client = chromadb.PersistentClient(
    path="./chroma_db"
)

collection = client.get_collection(
    name="course_chunks_bge_m3_v1"
)


print("=" * 80)
print("BGE-M3 SPARSE RETRIEVAL TEST")
print("=" * 80)

print("\nQuery:")
print(QUERY)

encoded = encode_text(QUERY)

results = search_sparse_chunks(
    query_sparse_weights=encoded["sparse"],
    course_id=1,
    n_results=10
)

chunk_ids = [
    result["chunk_id"]
    for result in results
]

documents = collection.get(
    ids=chunk_ids,
    include=["documents", "metadatas"]
)

document_map = {
    chunk_id: {
        "text": documents["documents"][i],
        "metadata": documents["metadatas"][i]
    }
    for i, chunk_id in enumerate(documents["ids"])
}


print("\nTop sparse results:\n")


for i, result in enumerate(results):

    chunk_id = result["chunk_id"]

    document = document_map.get(chunk_id)

    print("-" * 80)
    print(f"Rank: {i + 1}")
    print(f"Chunk ID: {chunk_id}")
    print(f"Sparse Score: {result['sparse_score']:.6f}")

    if document:

        metadata = document["metadata"]

        print(f"Video ID: {metadata['video_id']}")
        print(f"Start: {metadata['start']}")
        print(f"End: {metadata['end']}")

        print("\nText:")
        print(document["text"][:500])

    else:
        print("\nText: NOT FOUND")


print("\n" + "=" * 80)