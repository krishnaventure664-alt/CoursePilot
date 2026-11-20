from services.embedding_service import get_embedding
from services.vector_store_service import search_chunks

query = "What is active recalling ?"

query_embedding = get_embedding(query)

results = search_chunks(
    query_embedding=query_embedding,
    n_results=5
)
print("\nSearch Results:\n")

for i in range(len(results["documents"][0])):
    print(f"Result{i+1}")

    print("Text:")
    print(results["documents"][0][i])
    print("\nMetaData:")
    print(results["metadatas"][0][i])
    print("\nDistance:")
    print(results["distances"][0][i])

    print("\n"+"="*50+"\n")