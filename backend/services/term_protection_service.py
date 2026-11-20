import re


TECHNICAL_TERMS = [
    "Active Recall",
    "Machine Learning",
    "Gradient Descent",
    "RAG",
    "Embeddings",
    "Neural Networks",
    "Java",
    "ArrayList",
    "SQL",
    "React",
    "API",
]


def protect_terms(
        text: str,
        terms: list[str]
):
    """
    Replace technical terms with safe placeholders.

    Example:

    Active Recall improves retention.

    becomes:

    __TERM_0__ improves retention.
    """

    protected_terms = {}

    protected_text = text

    # Longest terms should be replaced first.
    # This prevents smaller terms from interfering
    # with larger phrases.
    sorted_terms = sorted(
        terms,
        key=len,
        reverse=True
    )

    for index, term in enumerate(sorted_terms):

        placeholder = f"__TERM_{index}__"

        pattern = re.compile(
            re.escape(term),
            re.IGNORECASE
        )

        if pattern.search(protected_text):

            protected_text = pattern.sub(
                placeholder,
                protected_text
            )

            protected_terms[placeholder] = term

    return protected_text, protected_terms


def restore_terms(
        text: str,
        protected_terms: dict
):
    """
    Restore original technical terms.

    Example:

    __TERM_0__ प्रतिधारण में सुधार करता है।

    becomes:

    Active Recall प्रतिधारण में सुधार करता है।
    """

    restored_text = text

    for placeholder, original_term in protected_terms.items():

        restored_text = restored_text.replace(
            placeholder,
            original_term
        )

    return restored_text