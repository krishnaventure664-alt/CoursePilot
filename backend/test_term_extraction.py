import ollama
import json


text = """
Active Recall improves retention and helps students remember information.

Machine Learning models learn patterns from data.
Gradient Descent is used to optimize model parameters.

RAG retrieves relevant information from a knowledge base
before generating an answer.

Embeddings represent text as numerical vectors.
"""


prompt = f"""
You are a technical terminology extraction system.

Read the following educational text:

{text}

Identify the important technical terms and named concepts
that should NOT be translated into Hindi.

Rules:

1. Return only terms that are technical concepts,
   technologies, algorithms, methods, frameworks,
   programming languages, libraries, or named systems.

2. Do NOT include normal English words such as:
   information, answer, students, data, improve, learn.

3. Preserve the exact spelling and capitalization
   used in the text.

4. Multi-word technical terms should remain together.

5. Return ONLY a JSON array of strings.

Example:

[
  "Machine Learning",
  "Gradient Descent"
]
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


output = response["message"]["content"]


print("\nRAW MODEL OUTPUT:")
print(output)


print("\nPARSED TERMS:")

try:

    terms = json.loads(output)

    for term in terms:
        print("-", term)

except Exception as error:

    print("Could not parse JSON.")
    print("Error:", error)