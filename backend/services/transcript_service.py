import os
import logging
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    YouTubeRequestFailed,
)
from services.youtube_audio_service import download_audio, get_existing_audio_path
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


def extract_captions_via_ytdlp(video_id: str) -> dict | None:
    """Extract YouTube captions directly via yt-dlp internal client spoofing.
    Bypasses datacenter IP blocking on AWS/Render without requiring proxy or cookies."""
    import requests
    import yt_dlp

    video_url = f"https://www.youtube.com/watch?v={video_id}"

    client_configs = [
        ["android", "mweb"],
        ["ios"],
        ["mweb"],
        ["web"],
    ]

    for clients in client_configs:
        try:
            ydl_opts = {
                "skip_download": True,
                "writesubtitles": True,
                "writeautomaticsub": True,
                "quiet": True,
                "no_warnings": True,
                "extractor_args": {
                    "youtube": {
                        "player_client": clients,
                    }
                },
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                subs = info.get("subtitles") or {}
                auto_subs = info.get("automatic_captions") or {}

                def _fetch_json3(track_list):
                    json3_track = next((f for f in track_list if f.get("ext") == "json3"), None)
                    if not json3_track or not json3_track.get("url"):
                        return None
                    try:
                        resp = requests.get(json3_track["url"], timeout=15)
                        if resp.status_code == 200:
                            data = resp.json()
                            segments = []
                            for ev in data.get("events", []):
                                if "segs" in ev:
                                    txt = "".join(s.get("utf8", "") for s in ev["segs"]).replace("\n", " ").strip()
                                    if txt:
                                        start = round(float(ev.get("tStartMs", 0)) / 1000.0, 2)
                                        dur = round(float(ev.get("dDurationMs", 0)) / 1000.0, 2)
                                        segments.append({
                                            "start": start,
                                            "duration": dur,
                                            "end": round(start + dur, 2),
                                            "text": txt,
                                        })
                            if segments:
                                return segments
                    except Exception:
                        pass
                    return None

                # Try preferred educational languages: hi, en, en-IN, hi-Latn
                for lang_code in ["hi", "en", "en-IN", "hi-Latn", "ur", "bn", "mr"]:
                    track_list = subs.get(lang_code) or auto_subs.get(lang_code) or []
                    segs = _fetch_json3(track_list)
                    if segs:
                        return {"source": f"youtube_ytdlp_{lang_code}", "segments": segs}

                # If specific codes not found, try the very first track in auto_subs or subs
                for track_dict in [subs, auto_subs]:
                    if track_dict:
                        first_lang = next(iter(track_dict))
                        segs = _fetch_json3(track_dict[first_lang])
                        if segs:
                            return {"source": f"youtube_ytdlp_{first_lang}", "segments": segs}
        except Exception:
            continue

    return None


def get_video_transcript(video_id: str, video_title: str = "", course_title: str = "") -> dict:
    """
    Fetch authentic video transcript grounded strictly in what was taught:
    1. Tries all available YouTube captions first (manual and auto-generated).
    2. If captions are unavailable, downloads audio and runs Gemini Audio Understanding
       (fast 16kHz mono compressed audio, verbatim transcription, exact timestamps).
    3. If Gemini audio transcription is unavailable, falls back to local Whisper.
    """
    # 1. YouTube Captions
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)

        transcript = None
        # Try manual captions first
        try:
            transcript = transcript_list.find_transcript(["en", "hi", "en-IN", "hi-Latn"])
        except Exception:
            # Try auto-generated captions
            try:
                transcript = transcript_list.find_generated_transcript(["en", "hi", "en-IN"])
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

    # 1.5. Extract captions via yt-dlp (Bypasses YouTube datacenter IP blocking on cloud servers like Render)
    try:
        ytdlp_trans = extract_captions_via_ytdlp(video_id)
        if ytdlp_trans and ytdlp_trans.get("segments"):
            logger.info(f"Retrieved {len(ytdlp_trans['segments'])} segments via yt-dlp captions for {video_id}")
            return ytdlp_trans
    except Exception as ytdlp_err:
        logger.info(f"yt-dlp captions unavailable for {video_id}: {ytdlp_err}")

    # 2. Authentic Speech Transcription via Gemini Audio File API
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
                return {
                    "source": "gemini_audio",
                    "segments": gemini_segments,
                }
    except Exception as gemini_err:
        logger.warning(f"Gemini audio transcription failed for {video_id}: {gemini_err}")

    # 3. Whisper Fallback (Local fallback if Gemini audio is unavailable)
    logger.info(f"Falling back to local Whisper audio transcription for {video_id}...")
    try:
        if not audio_path or not os.path.exists(audio_path):
            audio_path = download_audio(video_id)

        if audio_path and os.path.exists(audio_path):
            model = get_whisper_model()
            import torch
            result = model.transcribe(
                audio_path,
                condition_on_previous_text=False,
                temperature=0,
                beam_size=1,
                best_of=1,
                fp16=torch.cuda.is_available(),
                initial_prompt="This is an educational lecture covering course concepts and technical terms.",
            )

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
