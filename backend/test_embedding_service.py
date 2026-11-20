from services.embedding_service import get_embedding

text = "Active recalling improves memory retention."

embedding = get_embedding(text)

print("Embedding generated successfully!")
print("Dimensions:",len(embedding))
print("First 10 values:",embedding[:10])