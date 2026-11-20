import ollama

text = "Active recalling improves memory retention."

response = ollama.embeddings(
    model= "bge-m3",
    prompt= text
)

embedding = response["embedding"]

print("Embedding generated successfully!")
print("Number of Dimensions:",len(embedding))
print("First 10 values:",embedding[:10])