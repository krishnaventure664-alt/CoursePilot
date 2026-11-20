from services.embedding_service import get_embedding
from services.vector_store_service import store_chunk,collection

text = "Active recalling improves memory retention by forcing your brain to retrieve information."

embedding = get_embedding(text)


store_chunk(
    chunk_id="test_chunk_1",
    text=text,
    embedding=embedding,
    video_id="test_video_123",
    start=10.0,
    end=25.0
)


print("Chunk stored successfully!")

print("Number of chunks:",collection.count())