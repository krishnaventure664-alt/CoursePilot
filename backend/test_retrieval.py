from services.embedding_service import get_embedding
from services.vector_store_service import search_chunks

questions = [
    "What is active recall?",
    "Why does active recall work?",
    "What is SEO?",
    "What is HTML?",
    "What is archaeology?"
]

for question in questions:
    embedding = get_embedding(question)

    results = search_chunks(
        query_embedding=embedding,
        course_id=1,
        n_results=3
    )

    print("\nQUESTION:", question)
    print("DISTANCES:", results["distances"][0])
    print("TOP TEXT:", results["documents"][0][0][:150])