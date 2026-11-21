import time
from services.transcript_service import get_video_transcript
from services.chunking_service import create_chunks
from services.bge_m3_indexing_service import (
    index_bge_m3_chunks_batch,
    initialize_bge_m3_index,
)

initialize_bge_m3_index()

# Maximum batch size to prevent VRAM / RAM pressure on 3-5 hour lectures
BATCH_SIZE = 32


def index_video(video_id: str, course_id: int, video_title: str = ""):
    transcript_data = get_video_transcript(video_id, video_title=video_title)
    segments = transcript_data.get("segments", [])

    chunks = create_chunks(segments)
    if not chunks:
        return {
            "video_id": video_id,
            "chunks_indexed": 0,
            "transcript": transcript_data,
        }

    title_header = f"Lecture: {video_title.strip()}\n" if video_title else ""

    # Prepare all chunk payloads
    payloads = []
    for index, chunk in enumerate(chunks):
        payloads.append({
            "chunk_id": f"course_{course_id}_{video_id}_chunk_{index}",
            "text": f"{title_header}{chunk['text']}",
            "video_id": video_id,
            "course_id": course_id,
            "start": chunk["start"],
            "end": chunk["end"],
        })

    # Process in chunks of BATCH_SIZE (handles 20-min to 5-hour lectures seamlessly)
    for i in range(0, len(payloads), BATCH_SIZE):
        batch = payloads[i:i + BATCH_SIZE]
        index_bge_m3_chunks_batch(batch)
        # 15ms thermal breather: allows GPU core voltage to step down between bursts,
        # keeping RTX 3050 and laptop CPU cool without loud continuous fan spin.
        time.sleep(0.015)

    total_chunks = len(chunks)
    del payloads, chunks, transcript_data
    return {
        "video_id": video_id,
        "chunks_indexed": total_chunks,
    }
