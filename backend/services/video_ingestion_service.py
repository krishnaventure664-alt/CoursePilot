from services.transcript_service import get_video_transcript
from services.chunking_service import create_chunks
from services.embedding_service import get_embedding
from services.vector_store_service import store_chunk


def process_video(video_id: str):
    print(f"Processing video:{video_id}")

    transcript_data = get_video_transcript(video_id)

    segments = transcript_data["segments"]

    chunks = create_chunks(segments)

    print(f"Created{len(chunks)} chunks")

    for index, chunk in enumerate(chunks):
        print(f"Processing chunk {index+1}/{len(chunks)}")

        embedding = get_embedding(chunk["text"])

        chunk_id = f"{video_id}_chunk_{index}"


        store_chunk(
            chunk_id=chunk_id,
            text=chunk["text"],
            embedding=embedding,
            video_id=video_id,
            start=chunk["start"],
            end=chunk["end"]
        )

    print("Video processed successfully!")

    return{
        "video_id":video_id,
        "chunks_processed":len(chunks)
    }