import re


KNOWN_TECHNICAL_TERMS = [
    "Machine Learning",
    "Deep Learning",
    "Neural Network",
    "Gradient Descent",
    "Active Recall",
    "RAG",
    "Embeddings",

    "Python",
    "Java",
    "JavaScript",
    "TypeScript",

    "ArrayList",
    "HashMap",

    "SQL",
    "React",
    "Next.js",
    "FastAPI",

    "API",
    "REST API",

    "BERT",
    "GPT",
    "Transformer",
]


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


def find_terms(text, terms):

    found_terms = []

    for term in terms:

        pattern = re.compile(
            r"(?<!\w)"
            + re.escape(term)
            + r"(?!\w)",
            re.IGNORECASE
        )

        if pattern.search(text):

            found_terms.append(term)

    return found_terms


found_terms = find_terms(
    text,
    KNOWN_TECHNICAL_TERMS
)


print("\nDETECTED TECHNICAL TERMS:")

for term in found_terms:
    print("-", term)