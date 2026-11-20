from services.term_protection_service import (
    protect_terms,
    restore_terms,
    TECHNICAL_TERMS
)


text = (
    "Active Recall improves retention. "
    "Machine Learning models use Gradient Descent. "
    "RAG uses Embeddings. "
    "Java ArrayList is a data structure."
)


print("\nORIGINAL:")
print(text)


protected_text, protected_terms = protect_terms(
    text,
    TECHNICAL_TERMS
)


print("\nPROTECTED:")
print(protected_text)


print("\nTERM MAP:")
print(protected_terms)


restored_text = restore_terms(
    protected_text,
    protected_terms
)


print("\nRESTORED:")
print(restored_text)