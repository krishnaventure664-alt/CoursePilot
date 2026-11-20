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
print("SPARSE RETRIEVAL + TEXT INSPECTION")
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


document_map = {}

for i, chunk_id in enumerate(documents["ids"]):

    document_map[chunk_id] = {
        "text": documents["documents"][i],
        "metadata": documents["metadatas"][i]
    }


print("\nTop sparse results:\n")


for i, result in enumerate(results):

    chunk_id = result["chunk_id"]

    print("-" * 80)

    print(f"Rank: {i + 1}")
    print(f"Chunk ID: {chunk_id}")
    print(
        f"Sparse Score: "
        f"{result['sparse_score']:.6f}"
    )

    document = document_map.get(chunk_id)

    if document:

        metadata = document["metadata"]

        print(
            f"Video ID: "
            f"{metadata['video_id']}"
        )

        print(
            f"Start: "
            f"{metadata['start']}"
        )

        print(
            f"End: "
            f"{metadata['end']}"
        )

        print("\nText:")

        print(
            document["text"][:500]
        )

    else:

        print("\nText: NOT FOUND")


print("\n" + "=" * 80)