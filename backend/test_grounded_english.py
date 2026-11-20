import ollama


context = """
एक्टिव रिकॉलिंग कहते हैं जो आपकी रिटेंशन को यानी कि रिटेंशन मतलब
आपकी याद करने की क्षमता और आपके स्कोर दोनों को इंप्रूव करेगा।
"""


prompt = f"""
Use ONLY the information in the evidence below.

EVIDENCE:
{context}

QUESTION:
What is active recall?

OUTPUT LANGUAGE:
English

Rules:
- Write English only.
- Do not use Hindi.
- Do not use Devanagari.
- Do not use Roman Hindi.
- Use only facts from the evidence.
- Keep the answer to one sentence.

Answer:
"""


response = ollama.chat(
    model="llama3.2",
    messages=[
        {
            "role": "user",
            "content": prompt
        }
    ]
)


print(response["message"]["content"])