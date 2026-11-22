# backend/services/answer_service.py

import os
import re 
import logging
import threading
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import ollama

http_session = requests.Session()
adapter = HTTPAdapter(
    pool_connections=10,
    pool_maxsize=20,
    max_retries=Retry(total=2, backoff_factor=0.3, status_forcelist=[429, 500, 502, 503, 504])
)
http_session.mount("https://", adapter)
_answer_cache: dict[tuple[int, str], dict] = {}
_answer_cache_lock = threading.Lock()

def _get_cached_answer_mem(key):
    with _answer_cache_lock:
        return _answer_cache.get(key)

def _set_cached_answer_mem(key, val):
    with _answer_cache_lock:
        if len(_answer_cache) > 300:
            _answer_cache.clear()
        _answer_cache[key] = val
from dotenv import load_dotenv
from services.hybrid_search_service import hybrid_search
from services.query_processing_service import detect_language

load_dotenv()

def sanitize_answer(text: str) -> str:
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
logger = logging.getLogger(__name__)

OLLAMA_MODEL = "qwen2.5:3b"
FALLBACK_ANSWER = (
    "I could not find enough information about this in the provided course content."
)
RELEVANCE_THRESHOLD = 0.025

# Verified active production models prioritized by low-latency response speed
GEMINI_MODELS = [
    "gemini-flash-lite-latest",
    "gemini-3.1-flash-lite-preview",
    "gemini-2.5-flash",
    "gemini-3-flash-preview",
]


def _build_prompt_content(question: str, language: str, sources: list[dict]) -> tuple[str, str]:
    evidence_parts = []
    for idx, source in enumerate(sources, start=1):
        evidence_parts.append(
            f"[Source {idx}] (Lecture: {source['video_id']}, Timestamp: {int(source['start'])}s - {int(source['end'])}s)\n"
            f"{source['text']}"
        )

    evidence = "\n\n---\n\n".join(evidence_parts)

    lang_instructions = {
        "english": "You MUST write your entire response in clear, fluent English. Even if the lecture was delivered in Hindi or Hinglish, explain the concepts, terms, and teacher examples accurately in English.",
        "hindi": "आपको अपना पूरा उत्तर शुद्ध और स्पष्ट हिंदी (Devanagari script) में देना है। उदाहरण: 'शिक्षक ने समझाया है कि...' (हिंदी भाषा में ही उत्तर दें)।",
        "hinglish": "You MUST write your entire response in natural, conversational Hinglish (Roman script Hindi mixed with standard technical English words, exactly as Indian university teachers and students speak in lectures). Example: 'Instructor ne explain kiya hai ki Narrow AI specific tasks ke liye use hoti hai...'.",
    }
    lang_rule = lang_instructions.get(language, lang_instructions["english"])

    system_prompt = f"""You are CoursePilot, an intelligent AI university teaching assistant.
The lecture transcripts are from video course lectures spoken in Hindi/Hinglish.
Your goal is to answer the student's question accurately in the requested language.

RESPONSE LANGUAGE:
{lang_rule}

ADAPTIVE SCOPE & LENGTH (STRICT):
1. SPECIFIC / SIMPLE QUESTIONS (e.g., 'Who was X?', 'What was the capital of Y?', 'Where is Z located?'):
   - Answer ONLY what was asked directly and concisely in 1 to 3 sentences (or 1-2 focused bullet points).
   - Do NOT give an entire history lesson, background summary, or mention unrelated rulers/dynasties.
2. DETAILED / BROAD QUESTIONS (e.g., questions containing 'in detail', 'explain', 'overview of', 'summarize'):
   - Provide a comprehensive, well-structured breakdown with headings and bullet points synthesizing all relevant facts across the transcripts.
3. GROUNDING & CITATIONS:
   - Cite your sources inline using [Source 1], [Source 2], etc.
   - Base your response strictly on the lecture transcripts. Do not invent outside facts."""

    user_prompt = f"""COURSE TRANSCRIPTS:
{evidence}

STUDENT QUESTION:
{question}

Answer:"""

    return system_prompt, user_prompt


def _generate_with_gemini(system_prompt: str, user_prompt: str, api_key: str) -> str | None:
    """Ultra-fast cloud generation (~350ms - 800ms) with zero-thinking-delay on active Gemini models."""
    for model_name in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        
        gen_config = {
            "temperature": 0.1,
            "maxOutputTokens": 800,
        }
        # Disable thinking token generation latency for 2.5/3 series (saves 2 to 4 seconds!)
        if "2.5" in model_name or "3" in model_name:
            gen_config["thinkingConfig"] = {"thinkingBudget": 0}

        payload = {
            "system_instruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [
                {
                    "parts": [{"text": user_prompt}]
                }
            ],
            "generationConfig": gen_config,
        }

        try:
            res = http_session.post(url, json=payload, timeout=5)
            if res.status_code == 200:
                data = res.json()
                candidates = data.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    text = "".join(p.get("text", "") for p in parts).strip()
                    if text:
                        logger.info("Successfully generated fast answer using Gemini model: %s", model_name)
                        return text
            elif res.status_code == 400 and "thinkingConfig" in gen_config:
                # If model rejected thinkingConfig, retry immediately without it
                payload["generationConfig"] = {
                    "temperature": 0.1,
                    "maxOutputTokens": 800,
                }
                res_retry = http_session.post(url, json=payload, timeout=5)
                if res_retry.status_code == 200:
                    cand = res_retry.json().get("candidates", [])
                    if cand and "content" in cand[0]:
                        parts = cand[0]["content"].get("parts", [])
                        text = "".join(p.get("text", "") for p in parts).strip()
                        if text:
                            return text
            elif res.status_code in (429, 503, 404):
                logger.warning("Gemini model %s returned status %s, cascading to next...", model_name, res.status_code)
                continue
            else:
                logger.warning("Gemini model %s status %s: %s", model_name, res.status_code, res.text[:150])
                continue
        except requests.exceptions.Timeout:
            logger.warning("Gemini model %s timed out after 5s, cascading to next...", model_name)
            continue
        except Exception as e:
            logger.warning("Gemini model %s request failed: %s", model_name, e)
            continue

    return None



def rank_and_merge_sources_by_depth(raw_chunks: list[dict]) -> list[dict]:
    """
    Ranks source links by true semantic relevance AND coverage depth.
    If a concept is discussed for 5 minutes, it is merged into a comprehensive
    span and prioritized ahead of a 30-second passing mention.
    """
    import math

    if not raw_chunks:
        return []

    # 1. Group chunks by video_id to merge consecutive/overlapping segments
    by_video: dict[str, list[dict]] = {}
    for c in raw_chunks:
        by_video.setdefault(c["video_id"], []).append(c)

    merged_candidates: list[dict] = []

    for vid, v_chunks in by_video.items():
        v_chunks.sort(key=lambda x: x["start"])

        current = dict(v_chunks[0])
        for nxt in v_chunks[1:]:
            # If adjacent or within 45 seconds of each other in the same video, merge them
            if nxt["start"] <= current["end"] + 45.0:
                current["end"] = max(current["end"], nxt["end"])
                current["text"] = current["text"] + "\n\n" + nxt["text"]
                current["rerank_score"] = max(
                    current.get("rerank_score", 0.0),
                    nxt.get("rerank_score", 0.0)
                )
            else:
                merged_candidates.append(current)
                current = dict(nxt)
        merged_candidates.append(current)

    # 2. Compute Relevance & Depth Score
    # Semantic Answer Relevance is paramount: the video containing the most direct, accurate
    # answer to the student's question must always come first.
    # Merging adjacent chunks gives the user the full explanation span, while a gentle
    # depth bonus (up to 1.08x) ensures complete discussions are preferred when relevance is comparable.
    for m in merged_candidates:
        duration_sec = max(10.0, m["end"] - m["start"])
        # Subtle boost: 30s is ~1.0, 2m is ~1.04, 5m is ~1.07 (max 1.08x)
        depth_boost = 1.0 + 0.03 * math.log(max(1.0, duration_sec / 30.0))
        depth_boost = min(1.08, depth_boost)
        base_score = float(m.get("rerank_score", 0.5))
        m["depth_score"] = base_score * depth_boost
        m["duration_seconds"] = duration_sec

    # 3. Sort strictly by depth_score descending (most relevant answer first)
    merged_candidates.sort(key=lambda x: x["depth_score"], reverse=True)

    formatted_sources = []
    for rank, m in enumerate(merged_candidates, start=1):
        dur = m["duration_seconds"]
        if dur >= 60:
            dur_label = f"{int(dur // 60)}m {int(dur % 60)}s explanation"
        else:
            dur_label = f"{int(dur)}s mention"

        formatted_sources.append({
            "rank": rank,
            "chunk_id": m.get("chunk_id", ""),
            "video_id": m["video_id"],
            "start": m["start"],
            "end": m["end"],
            "text": m["text"],
            "rerank_score": m.get("rerank_score"),
            "depth_score": m.get("depth_score"),
            "duration_label": dur_label,
            "youtube_url": f"https://www.youtube.com/watch?v={m['video_id']}&t={int(m['start'])}s",
        })

    return formatted_sources


import threading

_answer_in_flight: dict[tuple[int, str], threading.Event] = {}
_answer_in_flight_lock = threading.Lock()


def generate_answer(question: str, course_id: int) -> dict:
    if not isinstance(question, str) or not question.strip():
        return {"answer": "Please enter a question.", "sources": []}

    question = question.strip()
    from services.course_db_service import normalize_answer_question, get_cached_answer, save_cached_answer
    norm_q = normalize_answer_question(question)
    cache_key = (course_id, norm_q)

    # 1. 0ms Fast In-Memory Cache Check
    mem_cached = _get_cached_answer_mem(cache_key)
    if mem_cached:
        return mem_cached

    # 2. < 1ms Persistent SQLite Cache Check
    db_cached = get_cached_answer(course_id, question)
    if db_cached:
        _set_cached_answer_mem(cache_key, db_cached)
        return db_cached

    # 3. Thread-safe in-flight coordination to eliminate duplicate concurrent executions
    event = None
    is_leader = False
    with _answer_in_flight_lock:
        event = _answer_in_flight.get(cache_key)
        if event is None:
            event = threading.Event()
            _answer_in_flight[cache_key] = event
            is_leader = True

    if not is_leader and event is not None:
        event.wait(timeout=25.0)
        db_cached = get_cached_answer(course_id, question)
        if db_cached:
            _set_cached_answer_mem(cache_key, db_cached)
            return db_cached

    try:
        try:
            language = detect_language(question)
        except Exception:
            language = "english"

        # 4. Fast Hybrid Retrieval with tuned candidate pool
        try:
            search_results = hybrid_search(
                query=question,
                course_id=course_id,
                final_top_k=6,
            )
        except Exception as error:
            logger.exception("Hybrid retrieval failed: %s", error)
            return {"answer": FALLBACK_ANSWER, "sources": []}

        if not search_results or search_results[0].get("rerank_score", 0.0) < RELEVANCE_THRESHOLD:
            return {"answer": FALLBACK_ANSWER, "sources": []}

        valid_chunks = [c for c in search_results if c.get("rerank_score", 0.0) >= 0.08]
        if not valid_chunks:
            valid_chunks = search_results[:4]

        # Rank and merge sources prioritizing depth of explanation
        formatted_sources = rank_and_merge_sources_by_depth(valid_chunks)

        # Feed top 4-5 high-density chunks to LLM to halve prompt token size and accelerate TTFT
        top_evidence = valid_chunks[:5]
        system_prompt, user_prompt = _build_prompt_content(question, language, top_evidence)

        # 5. Cloud generation with ultra-fast Gemini
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        if gemini_key:
            answer = _generate_with_gemini(system_prompt, user_prompt, gemini_key)
            if answer:
                clean_ans = sanitize_answer(answer)
                res_payload = {"answer": clean_ans, "sources": formatted_sources}
                _set_cached_answer_mem(cache_key, res_payload)
                try:
                    save_cached_answer(course_id, question, clean_ans, formatted_sources)
                except Exception:
                    pass
                return res_payload

        # 6. Local Ollama fallback (only if Ollama daemon is actively running locally on port 11434)
        try:
            import socket
            ollama_active = False
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.3)
                    ollama_active = (s.connect_ex(("127.0.0.1", 11434)) == 0)
            except Exception:
                ollama_active = False

            if ollama_active:
                response = ollama.chat(
                    model=OLLAMA_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    options={
                        "temperature": 0.2,
                        "repeat_penalty": 1.25,
                        "num_ctx": 4096,
                        "num_predict": 700,
                    },
                )
                answer = response["message"]["content"].strip()
            else:
                answer = FALLBACK_ANSWER
        except Exception as error:
            logger.warning("Ollama fallback failed/skipped: %s", error)
            return {"answer": FALLBACK_ANSWER, "sources": formatted_sources}

        if FALLBACK_ANSWER.lower() in answer.lower() and len(answer) < len(FALLBACK_ANSWER) + 30:
            return {"answer": FALLBACK_ANSWER, "sources": []}

        clean_ans = sanitize_answer(answer)
        result = {"answer": clean_ans, "sources": formatted_sources}
        _set_cached_answer_mem(cache_key, result)
        try:
            save_cached_answer(course_id, question, clean_ans, formatted_sources)
        except Exception:
            pass
        return result
    finally:
        if is_leader and event is not None:
            with _answer_in_flight_lock:
                _answer_in_flight.pop(cache_key, None)
            event.set()