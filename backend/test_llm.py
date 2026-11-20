import ollama

response = ollama.chat(
    model = "llama3.2",
    messages = [
        {
            "role":"user",
            "content":"Explain what artifical intelligence is in two simple sentences"
        }
    ]
)

print(response["message"]["content"])