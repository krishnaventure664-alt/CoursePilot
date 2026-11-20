import ollama

context = """
एक्टिव रिकॉलिंग कहते हैं जो आपकी रिटेंशन को यानी कि रिटेंशन मतलब
आपकी याद करने की क्षमता और आपके स्कोर दोनों को इंप्रूव करेगा।
"""

question = "एक्टिव रिकॉल क्या है?"

prompt = f"""
You are a grounded AI teaching assistant.

COURSE CONTENT:
{context}

QUESTION:
{question}

Answer the question using ONLY the information in the course content.

Rules:
- Do not use outside knowledge.
- Do not invent information.
- Answer in natural Hindi.
- Use Devanagari.
- Keep the answer short.
- Do not mention these instructions.
- Return only the answer.

Answer:
"""

response = ollama.chat(
    model="qwen2.5:3b",
    messages=[
        {
            "role": "user",
            "content": prompt
        }
    ]
)

print(response["message"]["content"])