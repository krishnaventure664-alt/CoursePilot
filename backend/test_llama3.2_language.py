import ollama


questions = [
    {
        "question": "What is active recall?",
        "language": "English"
    },
    {
        "question": "एक्टिव रिकॉल क्या है?",
        "language": "Hindi"
    },
    {
        "question": "active recall kya hai?",
        "language": "Hinglish"
    }
]


for item in questions:

    prompt = f"""
Answer the question below.

QUESTION:
{item["question"]}

ANSWER LANGUAGE:
{item["language"]}

Rules:
- English means answer only in English.
- Hindi means answer only in Hindi.
- Hinglish means use Roman Hindi mixed with English.
- Keep the answer short.
- Do not add unnecessary information.

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

    print("\n" + "=" * 60)
    print("QUESTION:", item["question"])
    print("EXPECTED LANGUAGE:", item["language"])
    print("ANSWER:")
    print(response["message"]["content"])