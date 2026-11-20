from services.term_extraction_service import (
    extract_course_terms
)


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


terms = extract_course_terms(text)


print("\nFINAL COURSE GLOSSARY:")

for term in terms:

    print("-", term)