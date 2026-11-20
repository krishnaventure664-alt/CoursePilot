import ollama

answer = "Active recall improves both your retention and your score."

languages = [
    "english",
    "hindi",
    "hinglish"
]

for language in languages:

    prompt = f"""
Rewrite the following sentence in {language}.

SOURCE:
{answer}

Rules:

- Preserve the exact meaning.
- Do not add information.
- Do not remove information.
- Return only one sentence.

For English:
Use English only.

For Hindi:
Use natural Hindi with Devanagari.

For Hinglish:
Use natural Roman Hindi mixed with English.
Do not use Devanagari.

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

    print("\n" + "=" * 60)
    print("TARGET:", language)
    print(response["message"]["content"])