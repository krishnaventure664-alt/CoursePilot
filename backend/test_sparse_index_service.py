from services.sparse_index_service import (
    initialize_sparse_index,
    add_sparse_vector,
    get_postings,
    delete_chunk
)


print("=" * 70)
print("SPARSE INDEX TEST")
print("=" * 70)


initialize_sparse_index()


chunk_id = "test_chunk_001"

sparse_weights = {
    "4865": 0.14629409,
    "83": 0.15839018,
    "36279": 0.26954895
}


add_sparse_vector(
    chunk_id=chunk_id,
    sparse_weights=sparse_weights
)


print("\nStored postings:")

for token_id in sparse_weights:

    postings = get_postings(token_id)

    print(
        f"Token {token_id}:",
        postings
    )


delete_chunk(chunk_id)


print("\nAfter deletion:")

for token_id in sparse_weights:

    postings = get_postings(token_id)

    print(
        f"Token {token_id}:",
        postings
    )


print("\n")
print("=" * 70)
print("TEST COMPLETE")
print("=" * 70)