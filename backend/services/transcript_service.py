import os
import logging
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    YouTubeRequestFailed,
)
from services.youtube_audio_service import download_audio, get_existing_audio_path, cleanup_audio_file
from services.gemini_audio_service import transcribe_audio_file_with_gemini
logger = logging.getLogger(__name__)

# Lazy-load Whisper model to avoid unnecessary VRAM / RAM consumption
_whisper_model = None


def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        import torch
        import whisper
        device = "cuda" if torch.cuda.is_available() else "cpu"
        vram_gb = 0.0
        if device == "cuda":
            try:
                vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            except Exception:
                pass

        cache_dir = os.path.expanduser("~/.cache/whisper")
        if vram_gb >= 8.0:
            model_name = "large-v2" if os.path.exists(os.path.join(cache_dir, "large-v2.pt")) else "base"
        else:
            if os.path.exists(os.path.join(cache_dir, "tiny.pt")):
                model_name = "tiny"
            else:
                model_name = "base"

        logger.info(f"Loading Whisper model ({model_name}) on {device} (VRAM: {vram_gb:.1f} GB)...")
        _whisper_model = whisper.load_model(model_name, device=device)
    return _whisper_model


def get_video_transcript(video_id: str, video_title: str = "", course_title: str = "") -> dict:
    """
    Fetch authentic video transcript grounded strictly in what was taught:
    1. Tries all available YouTube captions first (manual and auto-generated).
    2. If captions are unavailable, downloads audio and runs Gemini Audio Understanding
       (fast 16kHz mono compressed audio, verbatim transcription, exact timestamps).
    3. If Gemini audio transcription is unavailable, falls back to local Whisper with CPU throttling.
    """
    # 1. YouTube Captions (Ultra-fast ~0.3s, 0% CPU/GPU load)
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)

        preferred_langs = ["en", "hi", "en-IN", "hi-Latn", "en-orig", "hi-orig", "en-GB", "en-US", "es", "fr", "de", "ur", "bn"]
        transcript = None
        # Try manual captions first
        try:
            transcript = transcript_list.find_transcript(preferred_langs)
        except Exception:
            # Try auto-generated captions
            try:
                transcript = transcript_list.find_generated_transcript(preferred_langs)
            except Exception:
                for t in transcript_list:
                    transcript = t
                    break

        if transcript:
            raw_data = transcript.fetch()
            if hasattr(raw_data, "to_raw_data"):
                raw_data = raw_data.to_raw_data()
            elif not isinstance(raw_data, list):
                raw_data = list(raw_data)

            logger.info(f"Retrieved {len(raw_data)} segments from YouTube captions for {video_id}")
            return {
                "source": "youtube",
                "segments": raw_data,
            }

    except (NoTranscriptFound, TranscriptsDisabled, YouTubeRequestFailed, Exception) as error:
        logger.info(f"YouTube captions unavailable for {video_id}: {error}")

    # 2. Authentic Speech Transcription via Gemini Audio File API (Cloud-based, 0% CPU load)
    audio_path = None
    try:
        logger.info(f"Obtaining audio for {video_id} ('{video_title[:40]}')...")
        audio_path = download_audio(video_id)
        if audio_path and os.path.exists(audio_path):
            logger.info(f"Transcribing audio with Gemini Speech API for {video_id}...")
            gemini_segments = transcribe_audio_file_with_gemini(
                audio_path,
                video_title=video_title,
            )
            if gemini_segments and len(gemini_segments) > 0:
                logger.info(f"Gemini successfully transcribed {len(gemini_segments)} verbatim segments for {video_id}!")
                # Immediately reclaim disk space
                cleanup_audio_file(video_id)
                return {
                    "source": "gemini_audio",
                    "segments": gemini_segments,
                }
    except Exception as gemini_err:
        logger.warning(f"Gemini audio transcription failed for {video_id}: {gemini_err}")

    # 3. Whisper Fallback (Local fallback with CPU throttling so PC never freezes)
    logger.info(f"Falling back to local Whisper audio transcription for {video_id}...")
    try:
        if not audio_path or not os.path.exists(audio_path):
            audio_path = download_audio(video_id)

        if audio_path and os.path.exists(audio_path):
            import torch
            # Bounded CPU threads prevents 100% CPU lockup and keeps fans cool
            num_threads = min(4, max(1, (os.cpu_count() or 4) // 2))
            torch.set_num_threads(num_threads)

            model = get_whisper_model()
            result = model.transcribe(
                audio_path,
                condition_on_previous_text=False,
                temperature=0,
                beam_size=1,
                best_of=1,
                fp16=torch.cuda.is_available(),
                initial_prompt="This is an educational lecture covering course concepts and technical terms.",
            )

            cleanup_audio_file(video_id)

            raw_segs = result.get("segments", [])
            formatted = []
            for s in raw_segs:
                formatted.append({
                    "start": round(float(s.get("start", 0.0)), 2),
                    "end": round(float(s.get("end", 0.0)), 2),
                    "text": s.get("text", "").strip(),
                })

            return {
                "source": "whisper",
                "segments": formatted,
            }
    except Exception as whisper_err:
        logger.error(f"Whisper transcription failed for {video_id}: {whisper_err}")

    return {
        "source": "none",
        "segments": [],
    }
