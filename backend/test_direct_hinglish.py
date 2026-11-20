import ollama


answer = "Active recall is a learning technique that improves retention and helps improve your score."


prompt = f"""
Rewrite the following answer in natural Indian Hinglish.

SOURCE ANSWER:
{answer}

RULES:

1. Preserve the exact meaning.
2. Do not add any new information.
3. Use Roman Hindi mixed naturally with English.
4. Do not use Devanagari.
5. Keep technical terms such as "Active recall", "retention",
   "score", and "learning technique" in English when natural.
6. Do not translate every English word.
7. Write like an Indian student normally speaks.
8. Do not use labels.
9. Return only the answer.

HINGLISH ANSWER:
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
print("SOURCE:")
print(answer)

print("\nHINGLISH:")
print(response["message"]["content"])