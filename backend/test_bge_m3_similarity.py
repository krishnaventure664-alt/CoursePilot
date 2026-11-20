from services.bge_m3_service import encode_texts
from FlagEmbedding import BGEM3FlagModel


query = "What is machine learning?"

documents = [
    "Machine learning is a field of artificial intelligence where computers learn patterns from data.",
    "The Gupta Empire was an ancient Indian empire known for its achievements in science and culture.",
    "The capital of France is Paris."
]


# Encode query + documents in one call
query_result = encode_texts([query])
document_results = encode_texts(documents)


query_dense = query_result["dense"][0]
query_sparse = query_result["sparse"][0]

document_dense = document_results["dense"]
document_sparse = document_results["sparse"]


# Load model only for official scoring functions
model = BGEM3FlagModel(
    "BAAI/bge-m3",
    use_fp16=False,
    return_dense=True,
    return_sparse=True
)


print("=" * 70)
print("BGE-M3 OFFICIAL SCORING TEST")
print("=" * 70)

print("\nQuery:")
print(query)

print("\n")


for i in range(len(documents)):

    dense_score = model.compute_score(
        [
            query,
            documents[i]
        ],
        max_passage_length=512
    )["dense"]

    print(f"Document {i + 1}")
    print("-" * 70)
    print(documents[i])
    print("Dense score:", dense_score)
    print()


print("=" * 70)
print("TEST COMPLETE")
print("=" * 70)