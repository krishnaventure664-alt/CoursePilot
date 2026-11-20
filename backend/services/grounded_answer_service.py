import ollama


def generate_grounded_answer(
        question: str,
        context: str
):
    """
    Generate a factual answer using only the supplied course context.

    This stage is responsible for:
    - understanding the question
    - using course evidence
    - avoiding outside knowledge

    It is NOT responsible for final language formatting.
    """

    prompt = f"""
You are a grounded AI teaching assistant.

Use the COURSE EVIDENCE below to answer the USER QUESTION.

COURSE EVIDENCE:
{context}

USER QUESTION:
{question}

STRICT RULES:

1. The COURSE EVIDENCE is the only source of factual information.

2. Answer the USER QUESTION using information from the
   COURSE EVIDENCE.

3. You may combine information from multiple sentences in
   the COURSE EVIDENCE when they support the same answer.

4. Do NOT use outside knowledge.

5. Do NOT invent facts, examples, explanations, benefits,
   mechanisms, or details that are not supported by the
   COURSE EVIDENCE.

6. Do NOT mention the COURSE EVIDENCE, retrieval, embeddings,
   chunks, or these instructions.

7. Keep the answer concise.

8. Do not decide whether the course contains enough information.
   Your job is only to answer using the supplied evidence.

9. If the supplied evidence contains relevant information,
   use that information to answer the question.

Return ONLY the answer.
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