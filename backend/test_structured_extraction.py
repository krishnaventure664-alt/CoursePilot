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


schema = {
    "type": "object",
    "properties": {
        "terms": {
            "type": "array",
            "items": {
                "type": "string"
            }
        }
    },
    "required": ["terms"]
}


prompt = f"""
Extract the important technical terms from this course transcript.

Transcript:

{text}

Extract:
- technical concepts
- algorithms
- programming languages
- libraries
- frameworks
- technologies
- named systems
- data structures

Do not extract ordinary words.

Preserve the exact spelling and capitalization
of the technical terms.

The output must follow the provided JSON schema.
"""


response = ollama.chat(
    model="llama3.2",
    messages=[
        {
            "role": "user",
            "content": prompt
        }
    ],
    format=schema
)


output = response["message"]["content"]


print("\nRAW MODEL OUTPUT:")
print(output)


print("\nPARSED RESULT:")

try:

    result = json.loads(output)

    for term in result["terms"]:
        print("-", term)

except Exception as error:

    print("Could not parse JSON.")

    print("Error:", error)