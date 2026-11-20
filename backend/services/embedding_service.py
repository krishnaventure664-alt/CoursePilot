import ollama

EMBEDDING_MODEL = "bge-m3"

def get_embedding(text:str):
    response = ollama.embeddings(
        model = EMBEDDING_MODEL,
        prompt = text
    )

    return response["embedding"]