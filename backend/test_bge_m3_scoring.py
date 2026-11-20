from FlagEmbedding import BGEM3FlagModel


MODEL_NAME = "BAAI/bge-m3"

model = BGEM3FlagModel(
    MODEL_NAME,
    use_fp16=False,
    return_dense=True,
    return_sparse=True
)


query = "What is machine learning?"

documents = [
    "Machine learning is a field of artificial intelligence where computers learn patterns from data.",
    "The Gupta Empire was an ancient Indian empire known for its achievements in science and culture.",
    "The capital of France is Paris."
]


# --------------------------------------------------
# Encode query
# --------------------------------------------------

query_result = model.encode(
    [query]
)

query_dense = query_result["dense_vecs"][0]
query_sparse = query_result["lexical_weights"][0]


# --------------------------------------------------
# Encode documents
# --------------------------------------------------

document_results = model.encode(
    documents
)

document_dense = document_results["dense_vecs"]
document_sparse = document_results["lexical_weights"]


# --------------------------------------------------
# Calculate scores
# --------------------------------------------------

print("=" * 80)
print("BGE-M3 SCORING TEST")
print("=" * 80)

print("\nQuery:")
print(query)

print()


for i, document in enumerate(documents):

    dense_score = float(
        query_dense @ document_dense[i]
    )

    sparse_score = float(
        model.compute_lexical_matching_score(
            query_sparse,
            document_sparse[i]
        )
    )

    combined_score = float(
        model.compute_score(
            [(query, document)]
        )["sparse+dense"][0]
    )

    print("=" * 80)
    print(f"DOCUMENT {i + 1}")
    print("=" * 80)

    print(document)

    print("\nDense score:")
    print(dense_score)

    print("\nSparse score:")
    print(sparse_score)

    print("\nBGE-M3 sparse+dense score:")
    print(combined_score)


print("\n")
print("=" * 80)
print("TEST COMPLETE")
print("=" * 80)