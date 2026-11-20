from services.bge_m3_service import encode_text, encode_texts
from services.bge_m3_vector_store_service import store_dense_chunk, store_dense_chunks
from services.sparse_index_service import (
    initialize_sparse_index,
    add_sparse_vector,
    add_sparse_vectors_batch,
)


def index_bge_m3_chunks_batch(chunks_payload: list[dict]):
    """
    High-throughput batch indexing:
    1. Runs PyTorch matrix multiplication across all chunks simultaneously.
    2. Writes all dense vectors to ChromaDB in 1 batch call.
    3. Writes all sparse postings to SQLite in 1 transaction.
    """
    if not chunks_payload:
        return

    texts = [item["text"] for item in chunks_payload]
    
    # 1. Vectorized model inference (Batch forward pass)
    result = encode_texts(texts)
    dense_embeddings = result["dense"]
    sparse_weights_list = result["sparse"]

    chunk_ids = [item["chunk_id"] for item in chunks_payload]
    metadatas = [
        {
            "course_id": item["course_id"],
            "video_id": item["video_id"],
            "start": item["start"],
            "end": item["end"],
        }
        for item in chunks_payload
    ]

    # 2. Batch store in ChromaDB (1 call)
    store_dense_chunks(
        chunk_ids=chunk_ids,
        texts=texts,
        embeddings=dense_embeddings,
        metadatas=metadatas,
    )

    # 3. Batch store in SQLite (1 transaction)
    sparse_items = [
        {
            "chunk_id": item["chunk_id"],
            "sparse_weights": sparse_weights_list[idx],
            "course_id": item["course_id"],
        }
        for idx, item in enumerate(chunks_payload)
    ]
    add_sparse_vectors_batch(sparse_items)

    # Immediately release batch memory structures
    del dense_embeddings, sparse_weights_list, texts, metadatas, chunk_ids, sparse_items


def index_bge_m3_chunk(
    chunk_id,
    text,
    video_id,
    course_id,
    start,
    end
):
    result = encode_text(text)
    store_dense_chunk(
        chunk_id=chunk_id,
        text=text,
        embedding=result["dense"],
        video_id=video_id,
        course_id=course_id,
        start=start,
        end=end,
    )
    add_sparse_vector(
        chunk_id=chunk_id,
        sparse_weights=result["sparse"],
        course_id=course_id,
    )


def initialize_bge_m3_index():
    initialize_sparse_index()