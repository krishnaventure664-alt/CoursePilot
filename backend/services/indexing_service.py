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
    import os, glob
    try:
        transcript_data = get_video_transcript(video_id, video_title=video_title)
        segments = transcript_data.get("segments", [])

        chunks = create_chunks(segments)
        if not chunks:
            # AI Syllabus Fallback: generate educational chunks from the video title and syllabus
            try:
                from services.study_tools_service import _call_gemini
                prompt = f"""You are a master engineering professor. For the lecture:
"{video_title or video_id}"
Generate a comprehensive, chronological syllabus breakdown and verbatim lecture transcript explanation covering all concepts, definitions, formulas, protocols, and exam tips.
Output 8 to 12 distinct sequential paragraphs (each 100-150 words). Do NOT use LaTeX math ($)."""
                ai_text = _call_gemini(prompt, max_output_tokens=4096)
                if ai_text and len(ai_text) > 100:
                    paragraphs = [p.strip() for p in ai_text.split("\n\n") if len(p.strip()) > 50]
                    chunks = []
                    for idx, p in enumerate(paragraphs):
                        chunks.append({
                            "text": p,
                            "start": idx * 60.0,
                            "end": (idx + 1) * 60.0,
                        })
            except Exception:
                pass

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
            time.sleep(0.015)

        return {
            "video_id": video_id,
            "chunks_indexed": len(chunks),
            "transcript": transcript_data,
        }
    finally:
        # Crucial for Render 512MB RAM & disk limit: clean up downloaded audio immediately
        try:
            for f in glob.glob(os.path.join("backend/downloads", f"{video_id}*")):
                try:
                    os.remove(f)
                except Exception:
                    pass
        except Exception:
            pass
