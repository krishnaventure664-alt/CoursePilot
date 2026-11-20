import ollama


def convert_answer_language(
        answer: str,
        language: str
):
    """
    Convert a grounded answer into the requested language.

    This stage does NOT add new information.
    It only changes the language/style.
    """

    prompt = f"""
You are a language conversion assistant.

SOURCE ANSWER:
{answer}

TARGET LANGUAGE:
{language}

Your job is ONLY to rewrite the SOURCE ANSWER
in the TARGET LANGUAGE.

STRICT RULES:

1. Do NOT add any new factual information.

2. Do NOT remove important factual information.

3. Keep the original meaning exactly the same.

4. Do NOT explain anything about the conversion.

5. Do NOT add examples that are not in the SOURCE ANSWER.

6. Do NOT add labels such as:
   English:
   Hindi:
   Hinglish:

LANGUAGE RULES:

If the target language is "english":
- Write English only.
- Do NOT use Devanagari.
- Do NOT use Roman Hindi.

If the target language is "hindi":
- Write natural Hindi.
- Use Devanagari for Hindi sentences.
- Common technical terms such as Active Recall, retention,
  score, etc. may remain in English.

If the target language is "hinglish":
- Write Hindi using the Roman/English alphabet.
- Mix Roman Hindi naturally with English technical terms.
- Do NOT use Devanagari.

Return ONLY the converted answer.
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

    return response["message"]["content"]