import ollama
import json


text = """
Aaj hum Machine Learning ke baare mein baat karenge.
Machine Learning mein hum data se different patterns learn karte hain.

Agar hum model ko train kar rahe hain,
toh Gradient Descent ka use karke model ke parameters
ko optimize kar sakte hain.

Ab agar hum RAG system ki baat karein,
toh RAG pehle relevant documents ko retrieve karta hai
aur uske baad answer generate karta hai.

Embeddings ka use text ko numerical vectors mein represent
karne ke liye hota hai.

Students ko Active Recall ka use karke concepts ko
better remember karne mein help milti hai.

Python aur Java dono programming languages hain,
lekin is course mein hum Java ke ArrayList aur HashMap
data structures ke baare mein bhi padhenge.
"""


prompt = f"""
You are a technical terminology extraction system.

Read the following real educational course transcript:

{text}

Identify important technical terms and named concepts
that should NOT be translated into Hindi.

Rules:

1. Extract technical concepts, algorithms, methods,
   frameworks, programming languages, libraries,
   technologies, named systems, and data structures.

2. The transcript may contain English, Hindi,
   or Hinglish.

3. Extract the technical term itself, not the surrounding
   Hindi or Hinglish words.

4. Preserve the original spelling and capitalization.

5. Multi-word technical terms must remain together.

6. Do NOT extract normal words such as:
   data, model, answer, students, concepts,
   information, use, learn, course.

7. Do NOT extract Hindi words.

8. Return ONLY a JSON array of strings.

Example:

[
    "Machine Learning",
    "Gradient Descent",
    "RAG"
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