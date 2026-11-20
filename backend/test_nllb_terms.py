from services.nllb_service import translate_text


test_sentences = [
    "Active Recall improves retention.",
    "Machine Learning models learn patterns from data.",
    "Gradient Descent helps optimize model parameters.",
    "RAG retrieves relevant information before generating an answer.",
    "Embeddings represent text as numerical vectors.",
    "Neural Networks are used to learn complex patterns.",
    "Java ArrayList is a commonly used data structure.",
    "SQL is used to retrieve data from a database.",
    "React is used to build interactive user interfaces.",
    "API allows two software systems to communicate."
]


for index, sentence in enumerate(test_sentences, start=1):

    result = translate_text(
        text=sentence,
        source_language="eng_Latn",
        target_language="hin_Deva"
    )

    print("\n" + "=" * 80)

    print(f"TEST {index}")

    print("\nENGLISH:")
    print(sentence)

    print("\nHINDI:")
    print(result)