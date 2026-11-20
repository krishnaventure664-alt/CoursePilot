def create_chunks(
    segments,
    target_words: int = 160,
    overlap_words: int = 35,
    max_duration_seconds: float = 60.0,
):
    """
    Create coherent transcript chunks based on word count and time window.
    Works seamlessly with both YouTube transcript segments and Whisper segments.
    """
    chunks = []
    if not segments:
        return chunks

    current_segments = []
    current_word_count = 0
    current_start = None

    for seg in segments:
        text = seg.get("text", "").strip()
        if not text:
            continue

        words = text.split()
        seg_word_count = len(words)
        seg_start = float(seg.get("start", 0.0))
        seg_end = float(seg.get("end", seg_start + seg.get("duration", 0.0)))

        if current_start is None:
            current_start = seg_start

        current_segments.append({
            "text": text,
            "start": seg_start,
            "end": seg_end,
            "words": seg_word_count,
        })
        current_word_count += seg_word_count
        chunk_duration = seg_end - current_start

        # Window threshold: reached target words or maximum time duration
        if current_word_count >= target_words or chunk_duration >= max_duration_seconds:
            chunk_text = " ".join(s["text"] for s in current_segments)
            chunk_end = current_segments[-1]["end"]

            chunks.append({
                "text": chunk_text,
                "start": round(current_start, 2),
                "end": round(chunk_end, 2),
            })

            # Roll back segments to preserve overlap_words
            overlap_acc = 0
            keep_idx = len(current_segments)
            for i in range(len(current_segments) - 1, -1, -1):
                overlap_acc += current_segments[i]["words"]
                keep_idx = i
                if overlap_acc >= overlap_words:
                    break

            if keep_idx < len(current_segments) and keep_idx > 0:
                current_segments = current_segments[keep_idx:]
                current_word_count = sum(s["words"] for s in current_segments)
                current_start = current_segments[0]["start"]
            else:
                current_segments = []
                current_word_count = 0
                current_start = None

    # Handle any remaining segments
    if current_segments:
        chunk_text = " ".join(s["text"] for s in current_segments)
        chunks.append({
            "text": chunk_text,
            "start": round(current_start, 2),
            "end": round(current_segments[-1]["end"], 2),
        })

    return chunks