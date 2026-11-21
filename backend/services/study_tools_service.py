# backend/services/study_tools_service.py

import json

import logging

import os

import re
import threading

import time

from concurrent.futures import ThreadPoolExecutor

import requests

from requests.adapters import HTTPAdapter

from urllib3.util import Retry

from dotenv import load_dotenv

from services.bge_m3_vector_store_service import collection

from services.course_db_service import (

    get_cached_notes,

    save_notes,

    get_cached_quiz,

    save_quiz,

    get_flashcards,

    save_flashcards,

    clear_flashcards,

    get_quiz_set_count,

    get_flashcard_set_count,

)

load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-flash-lite-latest",
    "gemini-3.1-flash-lite",
    "gemini-3.1-flash-lite-preview",
    "gemini-3-flash-preview",
]

# Persistent session with connection pooling for low-latency concurrent API calls

http_session = requests.Session()

adapter = HTTPAdapter(

    pool_connections=10,

    pool_maxsize=20,

    max_retries=Retry(total=2, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])

)

http_session.mount("https://", adapter)

def sanitize_text(text: str) -> str:

    """Strip all raw LaTeX math syntax, dollar signs, and convert to clean Unicode symbols."""

    if not text:

        return ""

    text = re.sub(r"\\longrightarrow|\\rightarrow", " → ", text)

    text = re.sub(r"\\uparrow", "↑", text)

    text = re.sub(r"\\downarrow", "↓", text)

    text = re.sub(r"\\text\{([^}]+)\}", r"\1", text)

    text = re.sub(r"\$\$([^\$]+)\$\$", r"\1", text)

    text = re.sub(r"\$([^\$]+)\$", r"\1", text)

    text = re.sub(r"\\[a-zA-Z]+", "", text)

    return text.strip()

def is_note_truncated(text: str | None, transcript_len: int = 0) -> bool:

    """Detects if a note was cut off in the middle, incomplete, or ends abruptly."""

    if not text or len(text.strip()) < 500:

        return True

    clean = text.strip()

    last_line = clean.split("\n")[-1].strip()

    # 1. Ends on a markdown heading (e.g. "## 2. Step-by-Step Concepts" or "### A")

    if re.match(r"^#{1,6}\s+.*$", last_line) or re.match(r"^#{1,6}$", last_line):

        return True

    # 2. Ends on an empty bullet, list marker, or dangling label

    if re.match(r"^(\*|-|\d+\.)\s*$", last_line):

        return True

    if re.match(r"^(\*|-|\d+\.)\s+(\*\*[^*]+\*\*:?|\b[A-Za-z\s]+:)\s*$", last_line):

        return True

    # 3. Ends with dangling colon, comma, dash, open bracket

    if last_line.endswith((",", "-", "—", "(", "[", "{", "/", "\\", ":")):

        return True

    # 4. Check if ends mid-sentence without terminal punctuation when ending on an alphanumeric character

    if not re.search(r"(\.|\!|\?|\)|'|\"|```|\*|\*\*|\_|\|)$", last_line):

        if re.search(r"[a-zA-Z0-9]$", last_line) and len(clean) < 2000:

            return True

    # 5. Length sanity: if lecture transcript is 30,000+ chars and note is < 1200 chars

    if transcript_len > 30000 and len(clean) < 1200:

        return True

    return False

def _call_ollama(prompt: str, system_instruction: str = "") -> str | None:
    """Local LLM fallback when cloud API quota or connectivity is degraded."""
    try:
        import ollama
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        resp = ollama.chat(model="qwen2.5:7b", messages=messages)
        content = resp.get("message", {}).get("content", "")
        return sanitize_text(content) if content else None
    except Exception as e:
        logger.warning("Ollama fallback unavailable: %s", e)
        return None


def _call_gemini(prompt: str, system_instruction: str = "", max_output_tokens: int = 16384) -> str | None:

    """Call Gemini with cascade fallback, auto-continuation on token limits, and retry backoff."""

    import time

    for model_name in GEMINI_MODELS:

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"

        payload = {

            "contents": [{"parts": [{"text": prompt}]}],

            "generationConfig": {

                "temperature": 0.2,

                "maxOutputTokens": max_output_tokens,

            }

        }

        if system_instruction:

            payload["system_instruction"] = {"parts": [{"text": system_instruction}]}

        for attempt in range(2):

            try:

                res = http_session.post(url, json=payload, timeout=15)

                if res.status_code == 200:

                    data = res.json()

                    candidates = data.get("candidates", [])

                    if not candidates:

                        break

                    cand = candidates[0]

                    finish_reason = cand.get("finishReason")

                    parts = cand.get("content", {}).get("parts", [])

                    accumulated = "".join(p.get("text", "") for p in parts).strip()

                    # Auto-continuation loop if output hit MAX_TOKENS

                    cont_passes = 0

                    while finish_reason == "MAX_TOKENS" and cont_passes < 2:

                        cont_passes += 1

                        tail_preview = accumulated[-80:].replace("\n", " ")

                        cont_prompt = (

                            f"You stopped at: '{tail_preview}'. "

                            f"Continue directly from where you stopped. Do not repeat anything previously generated. Finish all remaining sections through to the very end."

                        )

                        cont_payload = {

                            "contents": [

                                {"role": "user", "parts": [{"text": prompt}]},

                                {"role": "model", "parts": [{"text": accumulated}]},

                                {"role": "user", "parts": [{"text": cont_prompt}]},

                            ],

                            "generationConfig": {

                                "temperature": 0.2,

                                "maxOutputTokens": max_output_tokens,

                            },

                        }

                        if system_instruction:

                            cont_payload["system_instruction"] = {"parts": [{"text": system_instruction}]}

                        c_res = http_session.post(url, json=cont_payload, timeout=15)

                        if c_res.status_code == 200:

                            c_cand = c_res.json().get("candidates", [{}])[0]

                            finish_reason = c_cand.get("finishReason")

                            c_parts = c_cand.get("content", {}).get("parts", [])

                            accumulated += "\n" + "".join(p.get("text", "") for p in c_parts).strip()

                        else:

                            break

                    return sanitize_text(accumulated)

                elif res.status_code in (429, 503):

                    logger.warning("Gemini model %s busy/rate-limited (%s), immediately trying next model...", model_name, res.status_code)

                    break

                else:

                    logger.warning("Gemini model %s returned status %s: %s", model_name, res.status_code, res.text[:200])

                    break

            except Exception as e:

                logger.warning("Gemini model %s attempt %d error: %s", model_name, attempt + 1, e)

                break

    return None

_lecture_chunks_cache: dict[tuple[int, str | None], list[tuple[float, float, str]]] = {}
_chunks_cache_lock = threading.Lock()

def invalidate_lecture_chunks_cache(course_id: int | None = None, video_id: str | None = None):
    """Invalidate in-memory lecture chunks cache when content is modified or deleted."""
    with _chunks_cache_lock:
        if course_id is None and video_id is None:
            _lecture_chunks_cache.clear()
        else:
            keys_to_del = [
                k for k in _lecture_chunks_cache
                if (course_id is None or k[0] == course_id) and (video_id is None or k[1] == video_id)
            ]
            for k in keys_to_del:
                _lecture_chunks_cache.pop(k, None)

def _split_markdown_into_chunks(content: str, total_duration: float = 3600.0) -> list[tuple[float, float, str]]:
    """Splits markdown notes into substantial, cohesive technical chunks without isolated headers."""
    if not content:
        return []
    import re
    raw_sections = re.split(r'(?=\n#{1,4}\s+)', content)
    merged_sections = []
    buffer = ""
    for sec in raw_sections:
        s = sec.strip()
        if not s:
            continue
        # Merge short headers (< 250 chars) into the subsequent body section
        if len(s) < 250:
            if buffer:
                buffer += "\n\n" + s
            else:
                buffer = s
        else:
            if buffer:
                merged_sections.append(buffer + "\n\n" + s)
                buffer = ""
            else:
                merged_sections.append(s)
    if buffer:
        if merged_sections:
            merged_sections[-1] += "\n\n" + buffer
        else:
            merged_sections.append(buffer)

    final_sections = []
    for sec in merged_sections:
        if len(sec) > 3000:
            paras = sec.split("\n\n")
            p_buf = ""
            for p in paras:
                if len(p_buf) + len(p) > 2000 and len(p_buf) >= 400:
                    final_sections.append(p_buf.strip())
                    p_buf = p
                else:
                    p_buf = (p_buf + "\n\n" + p).strip()
            if p_buf:
                final_sections.append(p_buf.strip())
        else:
            final_sections.append(sec)

    dur = max(3600.0, total_duration)
    n = max(1, len(final_sections))
    step = dur / n
    chunks = []
    for i, sec in enumerate(final_sections):
        start = i * step
        end = (i + 1) * step
        chunks.append((start, end, sec))
    return chunks


def _get_lecture_chunks(course_id: int, video_id: str | None = None) -> list[tuple[float, float, str]]:
    """Fetch all indexed chunks with timestamps, sorted chronologically from 0:00 to end with 0ms in-memory cache."""
    try:
        from services.course_db_service import get_canonical_course_id, get_connection
        effective_course_id = get_canonical_course_id(course_id)
        cache_key = (effective_course_id, video_id)
        with _chunks_cache_lock:
            if cache_key in _lecture_chunks_cache:
                return _lecture_chunks_cache[cache_key]

        chunks = []

        # 1. Fetch high-grade detailed notes from SQLite if available
        note_content = ""
        try:
            with get_connection() as conn:
                if video_id:
                    row = conn.execute("SELECT content FROM video_detailed_notes WHERE course_id = ? AND video_id = ?", (effective_course_id, video_id)).fetchone()
                    if not row or not row["content"]:
                        row = conn.execute("SELECT content FROM video_notes WHERE course_id = ? AND video_id = ?", (effective_course_id, video_id)).fetchone()
                    note_content = row["content"] if row else ""
                else:
                    rows = conn.execute("SELECT content FROM video_detailed_notes WHERE course_id = ? ORDER BY id ASC", (effective_course_id,)).fetchall()
                    if not rows:
                        rows = conn.execute("SELECT content FROM video_notes WHERE course_id = ? ORDER BY id ASC", (effective_course_id,)).fetchall()
                    note_content = "\n\n".join(r["content"] for r in rows if r["content"])
        except Exception:
            pass

        # 2. Query ChromaDB collection
        where = {"video_id": video_id} if video_id else {"course_id": effective_course_id}
        results = collection.get(where=where, include=["documents", "metadatas"])
        documents = results.get("documents", [])
        metadatas = results.get("metadatas", [])
        chroma_chunks = []
        if documents:
            for doc, meta in zip(documents, metadatas):
                start = meta.get("start", 0.0) if meta else 0.0
                end = meta.get("end", start + 60.0) if meta else start + 60.0
                chroma_chunks.append((start, end, doc))
            chroma_chunks.sort(key=lambda x: x[0])

        chroma_len = sum(len(c[2]) for c in chroma_chunks)
        # Prioritize master detailed notes whenever Chroma has too few chunks or far less content
        if chroma_chunks and len(chroma_chunks) >= 6 and chroma_len >= 2000 and (len(note_content) <= chroma_len + 500):
            chunks = chroma_chunks
        elif note_content:
            chunks = _split_markdown_into_chunks(note_content, total_duration=max(3600.0, float(len(chroma_chunks) * 60)))
        else:
            chunks = chroma_chunks

        if not chunks:
            try:
                from services.hybrid_search_service import _get_seed_chunks
                seed_chunks = _get_seed_chunks()
                for c in seed_chunks:
                    meta = c.get("metadata", {})
                    c_vid = meta.get("video_id")
                    c_cid = meta.get("course_id")
                    if video_id and str(c_vid) == str(video_id):
                        chunks.append((float(meta.get("start", 0.0)), float(meta.get("end", 60.0)), c["document"]))
                    elif not video_id and str(c_cid) == str(effective_course_id):
                        chunks.append((float(meta.get("start", 0.0)), float(meta.get("end", 60.0)), c["document"]))
                if chunks:
                    chunks.sort(key=lambda x: x[0])
            except Exception:
                pass

        # Clean chunks: merge any residual chunk < 250 chars into adjacent chunk so no isolated header chunk remains
        clean_chunks = []
        buf_c = None
        for c in chunks:
            c_text = c[2].strip()
            if len(c_text) < 250:
                if buf_c:
                    buf_c = (buf_c[0], c[1], buf_c[2] + "\n\n" + c_text)
                else:
                    buf_c = c
            else:
                if buf_c:
                    clean_chunks.append((buf_c[0], c[1], buf_c[2] + "\n\n" + c_text))
                    buf_c = None
                else:
                    clean_chunks.append(c)
        if buf_c:
            if clean_chunks:
                clean_chunks[-1] = (clean_chunks[-1][0], buf_c[1], clean_chunks[-1][2] + "\n\n" + buf_c[2])
            else:
                clean_chunks.append(buf_c)

        chunks = clean_chunks if clean_chunks else chunks

        with _chunks_cache_lock:
            if len(_lecture_chunks_cache) > 150:
                _lecture_chunks_cache.pop(next(iter(_lecture_chunks_cache)))
            _lecture_chunks_cache[cache_key] = chunks
        return chunks
    except Exception as e:
        logger.error("Failed to retrieve chunks: %s", e)
        return []

def _get_lecture_text(course_id: int, video_id: str | None = None) -> str:

    """Fetch the ENTIRE stored lecture transcript in chronological order from 0:00 to the end."""

    try:

        if video_id:

            # Fetch ALL indexed chunks for this video without limit

            results = collection.get(

                where={"video_id": video_id},

                include=["documents", "metadatas"],

            )

        else:
            from services.course_db_service import get_canonical_course_id
            effective_course_id = get_canonical_course_id(course_id)

            results = collection.get(

                where={"course_id": effective_course_id},

                include=["documents", "metadatas"],

            )

        documents = results.get("documents", [])

        metadatas = results.get("metadatas", [])

        if not documents:

            return ""

        # Pair each chunk with its timestamp and sort chronologically

        chunks = []

        for doc, meta in zip(documents, metadatas):

            start = meta.get("start", 0.0) if meta else 0.0

            chunks.append((start, doc))

        chunks.sort(key=lambda x: x[0])

        # Combine all chunks across the full video duration

        full_transcript = "\n\n".join(chunk_text for _, chunk_text in chunks)

        return full_transcript

    except Exception as e:

        logger.error("Failed to retrieve chunks for study tools: %s", e)

        return ""

def contains_devanagari(text: str) -> bool:
    """Returns True if the text contains any Hindi/Devanagari characters."""
    if not text:
        return False
    return any("\u0900" <= ch <= "\u097f" for ch in text)


def _clean_json_response(raw_text: str) -> str:

    """Robustly extract and strip JSON payload, handling markdown codeblocks or raw JSON."""

    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_text)

    if match:

        return match.group(1).strip()

    text = raw_text.strip()

    if text.startswith("```"):

        parts = text.split("```")

        if len(parts) >= 2:

            inner = parts[1]

            if inner.startswith("json"):

                inner = inner[4:]

            return inner.strip()

    return text

_notes_in_flight: dict[tuple[int, str], threading.Event] = {}
_notes_in_flight_lock = threading.Lock()


def get_or_generate_notes(course_id: int, video_id: str, force_refresh: bool = False) -> dict:
    """Return cached notes or generate comprehensive, un-truncated revision notes across the FULL lecture."""
    # Fast path: instant return from SQLite cache without disk/ChromaDB overhead
    if not force_refresh:
        cached = get_cached_notes(course_id, video_id)
        if cached and not is_note_truncated(cached) and "*(Complete Section Notes)*" not in cached:
            return {"notes": sanitize_text(cached), "cached": True}

    event = None
    is_leader = False
    if not force_refresh:
        with _notes_in_flight_lock:
            event = _notes_in_flight.get((course_id, video_id))
            if event is None:
                event = threading.Event()
                _notes_in_flight[(course_id, video_id)] = event
                is_leader = True

        if not is_leader and event is not None:
            # Another worker is already generating notes for this lecture - wait for it
            event.wait(timeout=45.0)
            cached = get_cached_notes(course_id, video_id)
            if cached and not is_note_truncated(cached) and "*(Complete Section Notes)*" not in cached:
                return {"notes": sanitize_text(cached), "cached": True}
    else:
        with _notes_in_flight_lock:
            event = threading.Event()
            _notes_in_flight[(course_id, video_id)] = event
            is_leader = True

    try:
        chunks = _get_lecture_chunks(course_id, video_id)
        if not chunks:
            # AI Syllabus Fallback
            v_title, c_title = "", ""
            try:
                from services.course_db_service import get_connection
                with get_connection() as conn:
                    r_v = conn.execute("SELECT title FROM course_videos WHERE video_id = ?", (video_id,)).fetchone()
                    if r_v: v_title = r_v["title"]
                    r_c = conn.execute("SELECT title FROM courses WHERE id = ?", (course_id,)).fetchone()
                    if r_c: c_title = r_c["title"]
            except Exception:
                pass
            prompt = f"""Generate comprehensive, high-yield bulleted revision notes for:
Course: {c_title or 'Engineering'}
Lecture: {v_title or video_id}

Requirements:
- Complete chronological coverage of all topics, core definitions, formulas, and exam takeaways from start to finish.
- Zero content skipped: every single sub-topic taught must have clear bullet points without cuts.
- Format: Clean Markdown bullet points with bold keywords. Do NOT use LaTeX math ($)."""
            gen = _call_gemini(prompt, max_output_tokens=4096)
            if gen and len(gen) > 50:
                save_notes(course_id, video_id, gen)
                return {"notes": sanitize_text(gen), "cached": False}
            return {"notes": "No lecture content found to generate notes.", "cached": False}

        total_dur = chunks[-1][1] - chunks[0][0] if chunks else 0.0
        total_transcript_len = sum(len(c[2]) for c in chunks)

        if not force_refresh:
            cached = get_cached_notes(course_id, video_id)
            if cached and not is_note_truncated(cached, total_transcript_len) and "*(Complete Section Notes)*" not in cached:
                return {"notes": sanitize_text(cached), "cached": True}

        # For videos > 45 mins, use concurrent sectional rapid revision to cover 100% of the lecture without skips
        if total_dur > 2700.0 or len(chunks) > 40:
            logger.info("Generating sectional quick revision notes for %s (%.1f mins)...", video_id, total_dur / 60)
            notes = _generate_sectional_quick_notes(chunks)
        else:
            context = "\n\n".join(c[2] for c in chunks)
            system_prompt = (
                "You are an expert university professor creating high-yield, structured Quick Revision Notes based EXCLUSIVELY on the provided lecture transcript.\n\n"
                "ABSOLUTE ZERO-OUTSIDE-KNOWLEDGE & COMPLETION RULES:\n"
                "1. STRICT FACTUAL GROUNDING: Base every note, bullet point, theorem, and explanation ONLY on what was actually spoken, taught, or demonstrated by the instructor in this lecture transcript.\n"
                "2. ZERO OUTSIDE ADDITIONS: Do NOT introduce external textbook concepts, proofs, history, or algorithms that the instructor did not explain in this lecture.\n"
                "3. COMPLETE CHRONOLOGICAL COVERAGE: You MUST cover the ENTIRE lecture from the very beginning (00:00) through all middle concepts to the final conclusion. Do NOT stop halfway.\n"
                "4. HIGH-YIELD & STRUCTURED: Write in clear, punchy bullet points. Focus on definitions, core concepts, whiteboard diagrams, exam questions, and takeaways.\n"
                "5. NO LATEX: Do NOT use LaTeX math syntax or dollar signs ($ or $$). Use clean Unicode symbols instead (e.g. O(n log n), ->, <=, >=, Theta, Omega, ^ for exponents).\n"
                "6. CLEAN COMPLETION: Ensure every list and section is fully closed with proper punctuation. Never leave a heading or bullet dangling.\n\n"
                "Structure the notes with clear Markdown headings:\n"
                "## 1. Lecture Overview & Core Objectives\n"
                "## 2. Key Concepts & Definitions (Chronological syllabus breakdown covering all topics from start to end)\n"
                "## 3. Important Formulas, Pseudocode & Mechanisms\n"
                "## 4. University Exam Questions (PYQs), Pitfalls & Instructor Tips\n"
                "## 5. High-Yield Revision Summary (Key takeaways for rapid recall)"
            )
            user_prompt = f"FULL LECTURE TRANSCRIPT:\n{context}\n\nGenerate structured, complete Quick Revision Notes covering the entire lecture from start to finish in clean Markdown:"
            notes = _call_gemini(user_prompt, system_instruction=system_prompt, max_output_tokens=16384)

        if notes and "*(Complete Section Notes)*" not in notes:
            save_notes(course_id, video_id, notes)
            return {"notes": notes, "cached": False}

        return {"notes": "Failed to generate notes. Please try again.", "cached": False}
    finally:
        if is_leader and event is not None:
            with _notes_in_flight_lock:
                _notes_in_flight.pop((course_id, video_id), None)
            event.set()


def _get_study_tool_grounding_context(course_id: int, video_id: str | None = None, max_chars: int = 35000) -> str:
    """
    Retrieves high-density grounding text for quizzes and flashcards.
    1. If verified Quick Notes or Deep Notes exist, samples from them (highest density of facts/questions).
    2. Otherwise, evenly samples chronological chunks from the start, middle, and end of the lecture.
    """
    notes = get_cached_notes(course_id, video_id)
    if notes and len(notes) > 500 and "*(Complete Section Notes)*" not in notes:
        return notes[:max_chars]

    deep = get_cached_detailed_notes(course_id, video_id)
    if deep and len(deep) > 500 and "*(Complete Section Notes)*" not in deep:
        return deep[:max_chars]

    chunks = _get_lecture_chunks(course_id, video_id)
    if not chunks:
        return ""
    total_chunks = len(chunks)
    if total_chunks <= 30:
        return "\n\n".join(c[2] for c in chunks)[:max_chars]

    step = total_chunks / 25
    sampled = [chunks[int(i * step)][2] for i in range(25)]
    return "\n\n".join(sampled)[:max_chars]


_quiz_in_flight: dict[tuple[int, str | None, int], threading.Event] = {}
_quiz_in_flight_lock = threading.Lock()

def get_or_generate_quiz(
    course_id: int,
    video_id: str | None = None,
    force_refresh: bool = False,
    requested_set: int | None = None,
) -> dict:
    """
    Returns or generates progressive interactive MCQs for the lecture.
    If force_refresh is True, advances to the next chronological set.
    When all sets covering the lecture are complete, it loops back to Set 1 and flags all_covered=True.
    """
    set_cnt = get_quiz_set_count(course_id, video_id)
    effective_total = max(4, set_cnt) if set_cnt > 0 else 4

    # Instant return from SQLite cache when requested set exists
    if requested_set is not None:
        target_s = requested_set % effective_total
        all_cov = (requested_set >= effective_total)
        msg = "🎉 You have covered all questions & concepts from this lecture! Starting revision from Set 1." if all_cov else ""
        cached = get_cached_quiz(course_id, video_id, set_index=target_s)
        if cached and not contains_devanagari(cached.get("quiz_data", "")):
            try:
                quiz_data = json.loads(cached["quiz_data"])
                cur_set = cached.get("set_index", target_s)
                return {
                    "quiz": quiz_data,
                    "set_index": cur_set + 1,
                    "total_sets": effective_total,
                    "all_covered": all_cov,
                    "message": msg,
                }
            except Exception:
                pass
    elif not force_refresh:
        # Default initial load: Set 1
        cached = get_cached_quiz(course_id, video_id, set_index=0)
        if cached and not contains_devanagari(cached.get("quiz_data", "")):
            try:
                quiz_data = json.loads(cached["quiz_data"])
                return {
                    "quiz": quiz_data,
                    "set_index": 1,
                    "total_sets": effective_total,
                    "all_covered": False,
                    "message": "",
                }
            except Exception:
                pass

    chunks = _get_lecture_chunks(course_id, video_id)
    if not chunks:
        # AI Syllabus Fallback for Quiz
        v_title, c_title = "", ""
        try:
            from services.course_db_service import get_connection
            with get_connection() as conn:
                r_v = conn.execute("SELECT title FROM course_videos WHERE video_id = ?", (video_id,)).fetchone()
                if r_v: v_title = r_v["title"]
                r_c = conn.execute("SELECT title FROM courses WHERE id = ?", (course_id,)).fetchone()
                if r_c: c_title = r_c["title"]
        except Exception:
            pass
        q_prompt = f"""Generate exactly 5 multiple choice questions for exam practice on:
Course: {c_title}
Lecture: {v_title or video_id}
Output ONLY a JSON array of objects with keys: id (integer 1-5), question (string), options (list of 4 strings), correct_index (integer 0-3), explanation (string).
No markdown code fences, raw JSON only."""
        raw_q = _call_gemini(q_prompt, max_output_tokens=2048) or ""
        import json as _json, re as _re
        raw_q = _re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_q).strip()
        try:
            q_data = _json.loads(raw_q)
            if isinstance(q_data, list) and len(q_data) > 0:
                save_quiz(course_id, video_id, _json.dumps(q_data), set_index=0)
                return {"quiz": q_data, "set_index": 1, "total_sets": 1, "all_covered": True, "message": ""}
        except Exception:
            pass
        return {"quiz": [], "set_index": 1, "total_sets": 1, "all_covered": False, "message": "No lecture content found."}

    total_dur = chunks[-1][1] - chunks[0][0] if chunks else 0.0
    if set_cnt >= 4:
        total_sets = set_cnt
    elif len(chunks) <= 4:
        total_sets = max(2, len(chunks))
    elif len(chunks) <= 8:
        total_sets = 4
    else:
        total_sets = max(4, min(8, len(chunks) // 2))

    all_covered = False
    message = ""
    if requested_set is not None:
        target_set = requested_set % total_sets
        all_covered = (requested_set >= total_sets)
        if all_covered:
            message = "🎉 You have covered all questions & concepts from this lecture! Starting revision from Set 1."
    elif force_refresh:
        latest = get_cached_quiz(course_id, video_id)
        last_set = latest.get("set_index", 0) if latest else 0
        next_set = last_set + 1
        if next_set >= total_sets:
            target_set = 0
            all_covered = True
            message = "🎉 You have covered all questions & concepts from this lecture! Starting revision from Set 1."
        else:
            target_set = next_set
    else:
        target_set = 0

    cached = get_cached_quiz(course_id, video_id, set_index=target_set)
    if cached and (not force_refresh or all_covered or requested_set is not None):
        if not contains_devanagari(cached.get("quiz_data", "")):
            try:
                quiz_data = json.loads(cached["quiz_data"])
                return {
                    "quiz": quiz_data,
                    "set_index": target_set + 1,
                    "total_sets": total_sets,
                    "all_covered": all_covered,
                    "message": message,
                }
            except Exception:
                pass

    # Thread-safe in-flight coordination to eliminate duplicate concurrent Gemini calls
    event = None
    is_leader = False
    in_flight_key = (course_id, video_id, target_set)
    with _quiz_in_flight_lock:
        event = _quiz_in_flight.get(in_flight_key)
        if event is None:
            event = threading.Event()
            _quiz_in_flight[in_flight_key] = event
            is_leader = True

    if not is_leader and event is not None:
        event.wait(timeout=35.0)
        cached = get_cached_quiz(course_id, video_id, set_index=target_set)
        if cached and not contains_devanagari(cached.get("quiz_data", "")):
            try:
                quiz_data = json.loads(cached["quiz_data"])
                return {
                    "quiz": quiz_data,
                    "set_index": target_set + 1,
                    "total_sets": total_sets,
                    "all_covered": all_covered,
                    "message": message,
                }
            except Exception:
                pass

    try:
        s_start = target_set * (total_dur / total_sets)
        s_end = (target_set + 1) * (total_dur / total_sets)
        s_chunks = [c for c in chunks if c[1] >= s_start and c[0] <= s_end]
        if not s_chunks:
            s_chunks = chunks

        if total_dur >= 3600.0:
            s_label = f"{int(s_start) // 3600:02d}:{(int(s_start) % 3600) // 60:02d}:{int(s_start) % 60:02d}"
            e_label = f"{int(s_end) // 3600:02d}:{(int(s_end) % 3600) // 60:02d}:{int(s_end) % 60:02d}"
        else:
            s_label = f"{int(s_start) // 60:02d}:{int(s_start) % 60:02d}"
            e_label = f"{int(s_end) // 60:02d}:{int(s_end) % 60:02d}"

        context = "\n\n".join(c[2] for c in s_chunks)[:30000]

        system_prompt = (
            f"You are an expert academic examiner creating high-quality, interactive multiple choice questions (MCQs) "
            f"based EXCLUSIVELY on the provided lecture section ({s_label} to {e_label}).\n\n"
            "ABSOLUTE ZERO-OUTSIDE-KNOWLEDGE RULES:\n"
            "1. STRICT FACTUAL GROUNDING: Every question, answer option, and explanation MUST be derived ONLY from what "
            "the instructor explicitly explained, demonstrated, solved, or taught in this section.\n"
            "2. ZERO OUTSIDE ADDITIONS: Do NOT introduce external textbook questions, facts, or proofs.\n"
            "3. EXPLANATION GROUNDING: In the 'explanation' field, cite the instructor's reasoning from the lecture.\n"
            "4. MANDATORY ENGLISH LANGUAGE: All questions, answer options, and explanations MUST be written 100% in clear, fluent English. Even if the lecture is spoken in Hindi, Hinglish, or another regional language, translate and phrase all concepts, questions, choices, and explanations strictly in standard English. NEVER use Hindi or Devanagari script.\n"
                        "5. NO LATEX: Use clean Unicode.\n"
            "6. ZERO METADATA / HEADING QUESTIONS: ABSOLUTELY NEVER ask questions about headings, unit titles, document names, syllabus structure, or section names (e.g. NEVER ask 'What is the title of Unit 1?' or 'What section follows this header?'). Every question MUST test concrete technical knowledge, protocol mechanisms, definitions, formulas, frame formats, packet routing, architectural layers, or real calculations taught in this section.\n\n"
            "Return ONLY a valid JSON array of 5 objects with exact fields:\n"
            "- 'id': (integer 1-5)\n"
            "- 'question': (string)\n"
            "- 'options': (array of 4 distinct choices)\n"
            "- 'correct_index': (integer 0-3)\n"
            "- 'explanation': (string)"
        )

        user_prompt = f"LECTURE SECTION ({s_label} to {e_label}):\n{context}\n\nGenerate 5 strictly grounded MCQs in JSON format:"

        raw_text = _call_gemini(user_prompt, system_instruction=system_prompt, max_output_tokens=2048)
        if raw_text:
            try:
                clean_json = _clean_json_response(raw_text)
                quiz_data = json.loads(clean_json)
                save_quiz(course_id, video_id, clean_json, set_index=target_set)
                return {
                    "quiz": quiz_data,
                    "set_index": target_set + 1,
                    "total_sets": total_sets,
                    "all_covered": all_covered,
                    "message": message,
                }
            except Exception as e:
                logger.error("Failed to parse quiz JSON: %s", e)

        return {"quiz": [], "set_index": target_set + 1, "total_sets": total_sets, "all_covered": all_covered, "message": message}
    finally:
        if is_leader and event is not None:
            with _quiz_in_flight_lock:
                _quiz_in_flight.pop(in_flight_key, None)
            event.set()


_flashcards_in_flight: dict[tuple[int, str | None, int], threading.Event] = {}
_flashcards_in_flight_lock = threading.Lock()

def get_or_generate_flashcards(
    course_id: int,
    video_id: str | None = None,
    force_refresh: bool = False,
    requested_set: int | None = None,
) -> dict:
    """
    Returns or generates progressive spaced-repetition flashcards for the lecture.
    If force_refresh is True, advances to the next chronological set.
    When all sets covering the lecture are complete, it loops back to Set 1 and flags all_covered=True.
    """
    set_cnt = get_flashcard_set_count(course_id, video_id)
    effective_total = max(4, set_cnt) if set_cnt > 0 else 4

    # Instant return from SQLite cache when requested set exists
    if requested_set is not None:
        target_s = requested_set % effective_total
        all_cov = (requested_set >= effective_total)
        msg = "🎉 You have reviewed all key concepts from this lecture! Starting revision loop from Set 1." if all_cov else ""
        existing_set = get_flashcards(course_id, video_id, set_index=target_s)
        if existing_set and not any(contains_devanagari(c.get("front", "") + c.get("back", "") + c.get("category", "")) for c in existing_set):
            cur_set = existing_set[0].get("set_index", target_s) if existing_set else target_s
            return {
                "flashcards": existing_set,
                "set_index": cur_set + 1,
                "total_sets": effective_total,
                "all_covered": all_cov,
                "message": msg,
            }
    elif not force_refresh:
        # Default initial load: Set 1
        existing_set = get_flashcards(course_id, video_id, set_index=0)
        if existing_set and not any(contains_devanagari(c.get("front", "") + c.get("back", "") + c.get("category", "")) for c in existing_set):
            return {
                "flashcards": existing_set,
                "set_index": 1,
                "total_sets": effective_total,
                "all_covered": False,
                "message": "",
            }

    chunks = _get_lecture_chunks(course_id, video_id)
    if not chunks:
        # AI Syllabus Fallback for Flashcards
        v_title, c_title = "", ""
        try:
            from services.course_db_service import get_connection
            with get_connection() as conn:
                r_v = conn.execute("SELECT title FROM course_videos WHERE video_id = ?", (video_id,)).fetchone()
                if r_v: v_title = r_v["title"]
                r_c = conn.execute("SELECT title FROM courses WHERE id = ?", (course_id,)).fetchone()
                if r_c: c_title = r_c["title"]
        except Exception:
            pass
        fc_prompt = f"""Generate 6 flashcards for exam practice on:
Course: {c_title}
Lecture: {v_title or video_id}
Output ONLY a JSON array of objects with keys: front (string question/concept), back (concise definition/answer), category (string e.g. 'Protocol', 'Formula', 'Definition').
No markdown code fences, raw JSON only."""
        raw_fc = _call_gemini(fc_prompt, max_output_tokens=2048) or ""
        import json as _json, re as _re
        raw_fc = _re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_fc).strip()
        try:
            fc_data = _json.loads(raw_fc)
            if isinstance(fc_data, list) and len(fc_data) > 0:
                save_flashcards(course_id, video_id, fc_data, set_index=0)
                return {"flashcards": fc_data, "set_index": 1, "total_sets": 1, "all_covered": True, "message": ""}
        except Exception:
            pass
        return {"flashcards": [], "set_index": 1, "total_sets": 1, "all_covered": False, "message": "No lecture content found."}

    total_dur = chunks[-1][1] - chunks[0][0] if chunks else 0.0
    if set_cnt >= 4:
        total_sets = set_cnt
    elif len(chunks) <= 4:
        total_sets = max(2, len(chunks))
    elif len(chunks) <= 8:
        total_sets = 4
    else:
        total_sets = max(4, min(8, len(chunks) // 2))

    all_covered = False
    message = ""
    if requested_set is not None:
        target_set = requested_set % total_sets
        all_covered = (requested_set >= total_sets)
        if all_covered:
            message = "🎉 You have reviewed all key concepts from this lecture! Starting revision loop from Set 1."
    elif force_refresh:
        existing_all = get_flashcards(course_id, video_id)
        last_set = max((c.get("set_index", 0) for c in existing_all), default=0)
        next_set = last_set + 1
        if next_set >= total_sets:
            target_set = 0
            all_covered = True
            message = "🎉 You have reviewed all key concepts from this lecture! Starting revision loop from Set 1."
        else:
            target_set = next_set
    else:
        target_set = 0

    existing_set = get_flashcards(course_id, video_id, set_index=target_set)
    if existing_set and (not force_refresh or all_covered or requested_set is not None):
        if not any(contains_devanagari(c.get("front", "") + c.get("back", "") + c.get("category", "")) for c in existing_set):
            return {
                "flashcards": existing_set,
                "set_index": target_set + 1,
                "total_sets": total_sets,
                "all_covered": all_covered,
                "message": message,
            }
        else:
            clear_flashcards(course_id, video_id, set_index=target_set)

    # Thread-safe in-flight coordination to eliminate duplicate concurrent Gemini calls
    event = None
    is_leader = False
    in_flight_key = (course_id, video_id, target_set)
    with _flashcards_in_flight_lock:
        event = _flashcards_in_flight.get(in_flight_key)
        if event is None:
            event = threading.Event()
            _flashcards_in_flight[in_flight_key] = event
            is_leader = True

    if not is_leader and event is not None:
        event.wait(timeout=35.0)
        existing_set = get_flashcards(course_id, video_id, set_index=target_set)
        if existing_set and not any(contains_devanagari(c.get("front", "") + c.get("back", "") + c.get("category", "")) for c in existing_set):
            return {
                "flashcards": existing_set,
                "set_index": target_set + 1,
                "total_sets": total_sets,
                "all_covered": all_covered,
                "message": message,
            }

    try:
        s_start = target_set * (total_dur / total_sets)
        s_end = (target_set + 1) * (total_dur / total_sets)
        s_chunks = [c for c in chunks if c[1] >= s_start and c[0] <= s_end]
        if not s_chunks:
            s_chunks = chunks

        if total_dur >= 3600.0:
            s_label = f"{int(s_start) // 3600:02d}:{(int(s_start) % 3600) // 60:02d}:{int(s_start) % 60:02d}"
            e_label = f"{int(s_end) // 3600:02d}:{(int(s_end) % 3600) // 60:02d}:{int(s_end) % 60:02d}"
        else:
            s_label = f"{int(s_start) // 60:02d}:{int(s_start) % 60:02d}"
            e_label = f"{int(s_end) // 60:02d}:{int(s_end) % 60:02d}"

        context = "\n\n".join(c[2] for c in s_chunks)[:30000]

        system_prompt = (
            f"You are an expert tutor creating study flashcards for spaced repetition based EXCLUSIVELY on the provided lecture section ({s_label} to {e_label}).\n\n"
            "ABSOLUTE ZERO-OUTSIDE-KNOWLEDGE RULES:\n"
            "1. STRICT FACTUAL GROUNDING: Every card MUST be based ONLY on what the instructor explained or demonstrated in this section.\n"
            "2. ZERO OUTSIDE ADDITIONS: Do NOT pull trivia or facts from external sources.\n"
            "3. ACCURATE CATEGORIES: Categorize each card according to subject matter (e.g. 'Definition', 'Core Concept', 'Formula & Derivation', 'Instructor Tip').\n"
            "4. MANDATORY ENGLISH LANGUAGE: All flashcards (front, back, and category) MUST be written 100% in clear, fluent English. Even if the lecture is spoken in Hindi, Hinglish, or another regional language, translate and express all terms, concepts, questions, and explanations strictly in standard English. NEVER use Hindi or Devanagari script.\n"
                        "5. NO LATEX: Use clean Unicode.\n"
            "6. ZERO METADATA / HEADING CARDS: ABSOLUTELY NEVER create flashcards about headings, unit titles, document names, or syllabus structure. Every card MUST test concrete technical definitions, protocol functions, mathematical formulas, network parameters, or exam principles.\n\n"
            "Return ONLY a valid JSON array of 6 to 8 objects with exact fields:\n"
            "- 'front': (string, clear question or term)\n"
            "- 'back': (string, accurate concise answer)\n"
            "- 'category': (string, subject category)"
        )

        user_prompt = f"LECTURE SECTION ({s_label} to {e_label}):\n{context}\n\nGenerate 6 to 8 strictly grounded flashcards in JSON format:"

        raw_text = _call_gemini(user_prompt, system_instruction=system_prompt, max_output_tokens=2048)
        if raw_text:
            try:
                clean_json = _clean_json_response(raw_text)
                cards = json.loads(clean_json)
                if force_refresh:
                    clear_flashcards(course_id, video_id, set_index=target_set)
                save_flashcards(course_id, video_id, cards, set_index=target_set)
                return {
                    "flashcards": get_flashcards(course_id, video_id, set_index=target_set),
                    "set_index": target_set + 1,
                    "total_sets": total_sets,
                    "all_covered": all_covered,
                    "message": message,
                }
            except Exception as e:
                logger.error("Failed to parse flashcard JSON: %s", e)

        return {
            "flashcards": existing_set if existing_set else [],
            "set_index": target_set + 1,
            "total_sets": total_sets,
            "all_covered": all_covered,
            "message": message,
        }
    finally:
        if is_leader and event is not None:
            with _flashcards_in_flight_lock:
                _flashcards_in_flight.pop(in_flight_key, None)
            event.set()


def _generate_sectional_quick_notes(chunks: list[tuple[float, float, str]], video_title: str = "") -> str:
    """Concurrently generates high-yield rapid revision notes covering every chronological section of a marathon video."""
    total_dur = chunks[-1][1] - chunks[0][0] if chunks else 0.0
    section_duration = 1800.0 if total_dur > 7200.0 else 1200.0

    sections = []
    current_section = []
    section_start = chunks[0][0]

    for start, end, chunk_text in chunks:
        if (end - section_start) > section_duration and current_section:
            sections.append(current_section)
            current_section = [(start, end, chunk_text)]
            section_start = start
        else:
            current_section.append((start, end, chunk_text))
    if current_section:
        sections.append(current_section)

    total_secs = len(sections)
    system_prompt = (
        "You are an expert university tutor creating complete, high-yield Quick Revision Notes based EXCLUSIVELY on the transcript.\n"
        "ZERO OUTSIDE KNOWLEDGE: Strictly grounded in what was spoken by the instructor.\n"
        "ZERO CONTENT SKIPPED: Cover EVERY topic, rule, formula, scheme year, and question taught in this section from start to end without omission.\n"
        "NO LATEX: Use clean Unicode symbols.\n"
        "Generate punchy, high-yield bullet points capturing ALL concepts and questions taught in this section chronologically without skipping any topic."
    )

    def _process_quick_section(sec_data: tuple[int, list]) -> tuple[int, str]:
        import time
        idx, sec = sec_data
        s_time = int(sec[0][0])
        e_time = int(sec[-1][1])
        if total_dur >= 3600.0:
            s_label = f"{s_time // 3600:02d}:{(s_time % 3600) // 60:02d}:{s_time % 60:02d}"
            e_label = f"{e_time // 3600:02d}:{(e_time % 3600) // 60:02d}:{e_time % 60:02d}"
        else:
            s_label = f"{s_time // 60:02d}:{s_time % 60:02d}"
            e_label = f"{e_time // 60:02d}:{e_time % 60:02d}"

        sec_text = "\n\n".join(t for _, _, t in sec)
        user_prompt = (
            f"LECTURE SECTION {idx} OF {total_secs} ({s_label} to {e_label}):\n"
            f"{sec_text}\n\n"
            f"Generate high-yield quick revision bullet points for this section:"
        )

        for attempt in range(2):
            notes = _call_gemini(user_prompt, system_instruction=system_prompt, max_output_tokens=3000)
            if notes and len(notes.strip()) > 150:
                header = f"\n\n### ⏱️ Section {idx} ({s_label} - {e_label}) • Rapid Revision\n\n"
                return (idx, header + notes.strip())
            time.sleep(1.0)
        return (idx, "")

    workers = min(total_secs, 4)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(_process_quick_section, [(i, s) for i, s in enumerate(sections, start=1)]))

    results.sort(key=lambda x: x[0])
    compiled = [content for _, content in results if content]
    return "\n".join(compiled)


def compile_course_handbook(course_id: int, course_title: str = "Course") -> dict:

    """

    Compiles full study notes for the ENTIRE playlist automatically.

    If any lecture does not have notes yet, it automatically synthesizes them on the fly.

    """

    from services.course_db_service import get_all_course_notes_db

    lectures = get_all_course_notes_db(course_id)

    total = len(lectures)

    toc_lines = []

    content_blocks = []

    for l in lectures:

        pos = l["position"]

        v_title = l["title"]

        v_notes = l.get("notes")

        # Automatically synthesize full notes on the fly if not already cached or if cached note was truncated

        if not v_notes or is_note_truncated(v_notes, 30000):

            res = get_or_generate_notes(course_id, l["video_id"], force_refresh=True)

            v_notes = res.get("notes", "")

        toc_lines.append(f"{pos}. **{v_title}**")

        if v_notes:

            content_blocks.append(

                f"# 📖 Lecture {pos}: {v_title}\n\n{sanitize_text(v_notes)}"

            )

    formatted_toc = "\n".join(toc_lines)

    formatted_body = "\n\n---\n\n".join(content_blocks)

    handbook_md = (

        f"# 📚 Complete Course Study Guide: {course_title}\n\n"

        f"> **Total Lectures:** {total} • **Full Syllabus Coverage**  \n"

        f"> **Engine:** CoursePilot BGE-M3 Multilingual Dense + Sparse Retrieval  \n\n"

        f"---\n\n"

        f"## 📑 Table of Contents\n\n"

        f"{formatted_toc}\n\n"

        f"---\n\n"

        f"{formatted_body}"

    )

    return {

        "course_id": course_id,

        "course_title": course_title,

        "total": total,

        "ready": total,

        "is_complete": True,

        "handbook": handbook_md,

        "lectures": lectures,

    }

from services.course_db_service import (

    get_cached_detailed_notes,

    save_detailed_notes,

    get_all_detailed_course_notes_db,

)

def _generate_sectional_notes(chunks: list[tuple[float, float, str]], video_title: str = "") -> str:
    """
    CONCURRENT SECTION-BY-SECTION SYNTHESIS:
    Splits marathon lectures into ~30-minute chronological blocks.
    Processes all sections concurrently in parallel threads, providing exhaustive
    question-by-question analysis for MCQs and full theoretical derivations.
    """
    total_dur = chunks[-1][1] - chunks[0][0] if chunks else 0.0
    if total_dur <= 1800.0:        # <= 30 mins
        section_duration = 900.0   # 15 min blocks
    elif total_dur <= 7200.0:      # <= 2 hours
        section_duration = 1500.0  # 25 min blocks
    else:                          # > 2 hours (up to 13+ hour marathons)
        section_duration = 1800.0  # 30 min blocks

    sections = []
    current_section = []
    section_start = chunks[0][0]

    for start, end, text in chunks:
        if (end - section_start) > section_duration and current_section:
            sections.append(current_section)
            current_section = [(start, end, text)]
            section_start = start
        else:
            current_section.append((start, end, text))
    if current_section:
        sections.append(current_section)

    system_prompt = (
        "You are an expert university professor creating publication-grade, exhaustive study notes based EXCLUSIVELY on the provided lecture transcript.\n\n"
        "ABSOLUTE ZERO-OMISSION & STRICT GROUNDING RULES:\n"
        "1. STRICT FACTUAL GROUNDING: Base every note, formula, theorem, question, and explanation ONLY on what was actually spoken, taught, or demonstrated by the instructor in this section.\n"
        "2. ZERO CONTENT SKIPPED: Do NOT cut, summarize away, or omit any concept, proof, step, whiteboard diagram, example, or problem taught by the instructor. Every single idea taught from the first second to the last second must be thoroughly documented in full depth.\n"
        "3. ZERO OUTSIDE ADDITIONS: Do NOT introduce external textbook concepts, history, or algorithms not taught.\n"
        "3. ADAPTIVE LECTURE FORMAT:\n"
        "   A. IF THE INSTRUCTOR IS SOLVING MCQs, PYQs, OR PRACTICE QUESTIONS:\n"
        "      - You MUST list EVERY SINGLE QUESTION discussed in chronological order. Never condense or skip any question!\n"
        "      - Format each question clearly:\n"
        "        ### Question [N]: [Full Question Statement]\n"
        "        * **Options:** [List options A, B, C, D discussed]\n"
        "        * **Correct Answer:** [The correct answer]\n"
        "        * **Teacher's Explanation & Elimination Logic:** [Why correct, why wrong options were eliminated, mnemonics/tricks]\n"
        "        * **Key Facts / Syllabus Notes:** [Any additional facts, years, data, or context given by the teacher]\n"
        "   B. IF THE INSTRUCTOR IS TEACHING THEORETICAL CONCEPTS, PROOFS, OR MECHANISMS:\n"
        "      - Provide exhaustive step-by-step notes covering definitions, architectures, algorithms, whiteboard diagrams, and comparison tables.\n"
        "   C. IF THE SECTION CONTAINS BOTH THEORY AND QUESTIONS:\n"
        "      - Present the theoretical concepts first, followed by the complete question-by-question analysis.\n"
        "4. COMPLETE CHRONOLOGICAL COVERAGE: Cover this section from the first second to the last second. Do not stop early.\n"
        "5. NO LATEX: Do NOT use LaTeX math syntax or dollar signs ($ or $$). Use clean Unicode symbols.\n"
    )

    total_secs = len(sections)

    def _process_single_section(sec_data: tuple[int, list]) -> tuple[int, str]:
        import time
        idx, sec = sec_data
        s_time = int(sec[0][0])
        e_time = int(sec[-1][1])
        if total_dur >= 3600.0:
            s_label = f"{s_time // 3600:02d}:{(s_time % 3600) // 60:02d}:{s_time % 60:02d}"
            e_label = f"{e_time // 3600:02d}:{(e_time % 3600) // 60:02d}:{e_time % 60:02d}"
        else:
            s_label = f"{s_time // 60:02d}:{s_time % 60:02d}"
            e_label = f"{e_time // 60:02d}:{e_time % 60:02d}"

        if idx > 1:
            time.sleep(0.2 * ((idx - 1) % 4))

        sec_text = "\n\n".join(t for _, _, t in sec)
        user_prompt = (
            f"LECTURE SECTION {idx} OF {total_secs} ({s_label} to {e_label}):\n"
            f"{sec_text}\n\n"
            f"Generate exhaustive, highly detailed notes covering EVERY concept and question taught in this section in clean Markdown:"
        )

        for attempt in range(3):
            part_notes = _call_gemini(user_prompt, system_instruction=system_prompt, max_output_tokens=16384)
            if part_notes and not is_note_truncated(part_notes, len(sec_text)):
                header = f"\n\n---\n\n### ⏱️ Section {idx} ({s_label} - {e_label})\n\n"
                return (idx, header + part_notes.strip())
            time.sleep(1.5 * (attempt + 1))

        if part_notes:
            header = f"\n\n---\n\n### ⏱️ Section {idx} ({s_label} - {e_label})\n\n"
            return (idx, header + part_notes.strip())
        return (idx, "")

    workers = min(total_secs, 4)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(_process_single_section, [(i, s) for i, s in enumerate(sections, start=1)]))

    final_results = []
    for idx, content in results:
        if not content or is_note_truncated(content):
            logger.warning("Recovering missing/truncated section %d of %d...", idx, total_secs)
            sec = sections[idx - 1]
            s_time = int(sec[0][0])
            e_time = int(sec[-1][1])
            if total_dur >= 3600.0:
                s_label = f"{s_time // 3600:02d}:{(s_time % 3600) // 60:02d}:{s_time % 60:02d}"
                e_label = f"{e_time // 3600:02d}:{(e_time % 3600) // 60:02d}:{e_time % 60:02d}"
            else:
                s_label = f"{s_time // 60:02d}:{s_time % 60:02d}"
                e_label = f"{e_time // 60:02d}:{e_time % 60:02d}"

            sec_text = "\n\n".join(t for _, _, t in sec)
            user_prompt = (
                f"LECTURE SECTION {idx} OF {total_secs} ({s_label} to {e_label}):\n"
                f"{sec_text}\n\n"
                f"Generate exhaustive, highly detailed notes covering EVERY concept and question taught in this section in clean Markdown:"
            )
            rec_notes = _call_gemini(user_prompt, system_instruction=system_prompt, max_output_tokens=16384)
            if rec_notes and not is_note_truncated(rec_notes):
                header = f"\n\n---\n\n### ⏱️ Section {idx} ({s_label} - {e_label})\n\n"
                final_results.append((idx, header + rec_notes.strip()))
            elif content and not is_note_truncated(content):
                final_results.append((idx, content))
            else:
                logger.error("Section %d failed to generate comprehensive notes.", idx)
        else:
            final_results.append((idx, content))

    final_results.sort(key=lambda x: x[0])
    compiled_sections = [content for _, content in final_results if content]
    return "\n".join(compiled_sections)


def get_or_generate_detailed_notes(course_id: int, video_id: str, force_refresh: bool = False) -> dict:

    """Generates or retrieves exhaustive, un-truncated Master Notes."""

    # Fast path: instant return from SQLite cache without disk/ChromaDB overhead
    if not force_refresh:
        cached = get_cached_detailed_notes(course_id, video_id)
        if cached and not is_note_truncated(cached):
            return {"notes": sanitize_text(cached), "cached": True}

    chunks = _get_lecture_chunks(course_id, video_id)
    if not chunks:
        # AI Syllabus Fallback: Synthesize master lecture notes directly from university lecture topic
        v_title = ""
        c_title = ""
        try:
            from services.course_db_service import get_connection
            with get_connection() as conn:
                r_v = conn.execute("SELECT title FROM course_videos WHERE video_id = ?", (video_id,)).fetchone()
                if r_v: v_title = r_v["title"]
                r_c = conn.execute("SELECT title FROM courses WHERE id = ?", (course_id,)).fetchone()
                if r_c: c_title = r_c["title"]
        except Exception:
            pass

        topic_label = v_title or f"Lecture {video_id}"
        prompt = f"""You are a distinguished university engineering professor.
Write exhaustive, highly detailed Master Study Notes for the following lecture:
Course: {c_title or 'Engineering / Computer Science'}
Lecture: {topic_label}

Requirements:
- ZERO-OMISSION COVERAGE: Cover every concept, architectural layer, protocol state transition, definition, and formula relevant to this topic. Nothing must be skipped or cut.
- Markdown formatted with ## and ### headings, step-by-step numbered derivations, ASCII/Unicode protocol flows, comparison tables, and solved numerical problems.
- Include an 'AKTU Exam High-Yield PYQs & Problem-Solving Strategies' section.
- Write an in-depth, textbook-grade master study guide (at least 1500 words).
- Do NOT use LaTeX math ($). Use plain text or Unicode symbols."""
        generated = _call_gemini(prompt, max_output_tokens=8192)
        if generated and len(generated) > 100:
            save_detailed_notes(course_id, video_id, generated)
            return {"notes": sanitize_text(generated), "cached": False}
        return {"notes": "No lecture content found to generate detailed notes.", "cached": False}

    total_duration = chunks[-1][1] - chunks[0][0]

    total_transcript_len = sum(len(c[2]) for c in chunks)

    if not force_refresh:

        cached = get_cached_detailed_notes(course_id, video_id)

        if cached and not is_note_truncated(cached, total_transcript_len):

            return {"notes": sanitize_text(cached), "cached": True}

    # For short videos (< 25 mins), 1 call is enough. For marathon videos, use sectional synthesis.

    if total_duration <= 1500.0 or len(chunks) <= 20:

        context = "\n\n".join(doc for _, _, doc in chunks)

        system_prompt = (

            "You are an expert tutor creating exhaustive, publication-grade study notes based EXCLUSIVELY on the transcript.\n"

            "STRICT GROUNDING: Include ONLY what is taught. Zero outside knowledge. Capture all whiteboard steps and MCQs.\n"

            "CRITICAL: Cover the entire lecture from 00:00 to the end. Do not truncate."

        )

        user_prompt = f"FULL LECTURE TRANSCRIPT:\n{context}\n\nGenerate detailed, publication-grade notes in clean Markdown:"

        notes = _call_gemini(user_prompt, system_instruction=system_prompt, max_output_tokens=16384)

    else:

        logger.info(f"Generating sectional deep notes for {video_id} ({total_duration/60:.1f} mins)...")

        notes = _generate_sectional_notes(chunks)

    if notes:

        save_detailed_notes(course_id, video_id, notes)

        return {"notes": notes, "cached": False}

    return {"notes": "Failed to generate detailed notes.", "cached": False}

def compile_detailed_course_handbook(course_id: int, course_title: str = "Course") -> dict:

    """Compiles exhaustive Master Notes for the entire playlist into a single master guide concurrently."""

    lectures = get_all_detailed_course_notes_db(course_id)

    total = len(lectures)

    # Concurrently pre-generate any completed lectures that do not have notes cached yet or whose notes are truncated

    missing_completed = [

        l for l in lectures

        if (not l.get("notes") or is_note_truncated(l.get("notes"), 30000)) and l.get("status") == "completed"

    ]

    generated_map = {}

    if missing_completed:

        def _fetch_notes_worker(l):

            res = get_or_generate_detailed_notes(course_id, l["video_id"])

            return l["video_id"], res.get("notes", "")

        workers = min(len(missing_completed), 2)

        with ThreadPoolExecutor(max_workers=workers) as executor:

            generated_map = dict(executor.map(_fetch_notes_worker, missing_completed))

    toc_lines = []

    content_blocks = []

    for l in lectures:

        pos = l["position"]

        v_title = l["title"]

        v_notes = l.get("notes") or generated_map.get(l["video_id"], "")

        if not v_notes:

            if l.get("status") != "completed":

                v_notes = "*Indexing in progress for this lecture. Notes will be generated once indexing completes.*"

        toc_lines.append(f"{pos}. **{v_title}**")

        if v_notes:

            content_blocks.append(f"# 📖 Lecture {pos}: {v_title}\n\n{sanitize_text(v_notes)}")

    formatted_toc = "\n".join(toc_lines)

    formatted_body = "\n\n---\n\n".join(content_blocks)

    handbook_md = (

        f"# 📚 Complete Master Study Handbook: {course_title}\n\n"

        f"> **Total Lectures:** {total} • **Exhaustive Section-by-Section Syllabus Coverage**  \n\n"

        f"---\n\n"

        f"## 📑 Table of Contents\n\n{formatted_toc}\n\n---\n\n{formatted_body}"

    )

    return {

        "course_id": course_id,

        "course_title": course_title,

        "total": total,

        "handbook": handbook_md,

    }

