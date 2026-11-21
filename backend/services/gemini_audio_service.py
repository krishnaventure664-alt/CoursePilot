import os
import re
import json
import time
import subprocess
import logging
import requests
from dotenv import load_dotenv

load_dotenv()
load_dotenv("backend/.env")

logger = logging.getLogger(__name__)

GEMINI_MODELS = [
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite-preview",
    "gemini-3.1-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-2.5-flash",
]


def get_ffmpeg_binary() -> str:
    """Return path to ffmpeg binary, favoring bundled static binary from imageio-ffmpeg."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def get_audio_duration(audio_path: str) -> float:
    """Get the duration of an audio file in seconds using ffprobe or ffmpeg."""
    # 1. Try ffprobe
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            audio_path,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        dur = float(data.get("format", {}).get("duration", 0.0))
        if dur > 0:
            return dur
    except Exception:
        pass

    # 2. Try ffmpeg output duration regex
    try:
        ffmpeg_bin = get_ffmpeg_binary()
        cmd = [ffmpeg_bin, "-i", audio_path]
        res = subprocess.run(cmd, capture_output=True, text=True)
        # Output looks like: Duration: 01:25:39.45, start: 0.000000, bitrate: 64 kb/s
        match = re.search(r"Duration:\s*(\d{2}):(\d{2}):(\d{2}(?:\.\d+)?)", res.stderr)
        if match:
            h, m, s = match.groups()
            return int(h) * 3600 + int(m) * 60 + float(s)
    except Exception as e:
        logger.warning(f"ffmpeg duration check failed for {audio_path}: {e}")

    # 3. Fallback: estimate from file size (assuming ~48kbps opus/webm)
    try:
        f_size = os.path.getsize(audio_path)
        return max(60.0, f_size / (6000.0))
    except Exception:
        return 0.0


def compress_and_slice_audio(
    audio_path: str,
    start_sec: float,
    duration_sec: float,
    output_path: str,
) -> bool:
    """
    Compress an audio slice to 16kHz mono 24kbps MP3 for fast upload and low token usage.
    Fast seeking with -ss before -i executes in under 1 second.
    """
    try:
        ffmpeg_bin = get_ffmpeg_binary()
        cmd = [
            ffmpeg_bin,
            "-y",
            "-ss", str(start_sec),
            "-i", audio_path,
            "-t", str(duration_sec),
            "-ar", "16000",
            "-ac", "1",
            "-b:a", "24k",
            output_path,
        ]
        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return os.path.exists(output_path) and os.path.getsize(output_path) > 1000
    except Exception as e:
        logger.error(f"ffmpeg slicing failed: {e}")
        return False


def upload_audio_to_gemini(file_path: str, api_key: str) -> dict | None:
    """
    Upload an audio file to the Gemini File API via Resumable Upload protocol.
    Returns dict with 'uri' and 'name' (for later deletion).
    """
    f_size = os.path.getsize(file_path)
    upload_url = f"https://generativelanguage.googleapis.com/upload/v1beta/files?key={api_key}"
    headers = {
        "X-Goog-Upload-Protocol": "resumable",
        "X-Goog-Upload-Command": "start",
        "X-Goog-Upload-Header-Content-Length": str(f_size),
        "X-Goog-Upload-Header-Content-Type": "audio/mp3",
        "Content-Type": "application/json",
    }

    try:
        r_start = requests.post(
            upload_url,
            headers=headers,
            json={"file": {"display_name": os.path.basename(file_path)}},
            timeout=30,
        )
        if r_start.status_code != 200:
            logger.error(f"Failed to start Gemini resumable upload: {r_start.text}")
            return None

        resumable_url = r_start.headers.get("X-Goog-Upload-URL")
        if not resumable_url:
            return None

        with open(file_path, "rb") as f:
            r_upload = requests.post(
                resumable_url,
                headers={
                    "Content-Length": str(f_size),
                    "X-Goog-Upload-Offset": "0",
                    "X-Goog-Upload-Command": "upload, finalize",
                },
                data=f,
                timeout=120,
            )

        if r_upload.status_code == 200:
            file_info = r_upload.json().get("file", {})
            return {
                "uri": file_info.get("uri"),
                "name": file_info.get("name"),
            }
        logger.error(f"Gemini upload failed: {r_upload.text}")
    except Exception as e:
        logger.error(f"Gemini upload error: {e}")
    return None


def delete_gemini_file(file_name: str, api_key: str) -> None:
    """Delete uploaded audio from Gemini cloud storage to keep account clean."""
    if not file_name:
        return
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/{file_name}?key={api_key}"
        requests.delete(url, timeout=15)
    except Exception:
        pass


def robust_json_load(raw: str):
    """
    Safely parse JSON response with regex cleanup for invalid escape characters
    and automatic repair for responses cut off by maxOutputTokens.
    """
    raw = raw.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
    if match:
        raw = match.group(1).strip()

    # 1. Direct parse
    try:
        return json.loads(raw, strict=False)
    except Exception:
        pass

    # 2. Fix unescaped backslashes
    try:
        fixed = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', raw)
        return json.loads(fixed, strict=False)
    except Exception:
        pass

    # 3. Repair truncated JSON array if cut off mid-stream
    last_brace = raw.rfind("}")
    if last_brace != -1:
        truncated = raw[:last_brace + 1].strip()
        if not truncated.endswith("]"):
            truncated += "\n]"
        try:
            return json.loads(truncated, strict=False)
        except Exception:
            try:
                fixed = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', truncated)
                return json.loads(fixed, strict=False)
            except Exception:
                pass

    return []


def transcribe_audio_slice(
    file_uri: str,
    api_key: str,
    time_offset: float = 0.0,
    video_title: str = "",
) -> list[dict]:
    """
    Transcribe an audio slice using Gemini Audio Understanding.
    Returns chronological segments with exact timestamps adjusted by time_offset.
    """
    prompt = f"""
You are an expert university lecture transcriber.
Lecture Topic: "{video_title or 'Computer Science / Engineering Lecture'}"
Task: Transcribe this audio recording into chronological segments (each segment about 40 to 80 seconds long).
The audio contains real classroom speech in English, Hindi, or Hinglish (Hindi + English technical terms).

For each segment, output an object with:
- "start": start time in seconds within this audio clip (float, e.g. 0.0)
- "end": end time in seconds within this audio clip (float, e.g. 60.5)
- "text": exact verbatim spoken words. Capture all technical terms, algorithms, formulas, complexity notations (e.g. O(n log n), Theta(n^2)), and exam tips spoken by the instructor.

FORMAT REQUIREMENTS:
1. Do NOT use LaTeX math ($ or $$) or unescaped backslashes. Use clean Unicode symbols.
2. Return ONLY a valid JSON array of segment objects.
[
  {{"start": 0.0, "end": 55.0, "text": "Verbatim speech..."}}
]
"""

    payload = {
        "contents": [
            {
                "parts": [
                    {"file_data": {"mime_type": "audio/mp3", "file_uri": file_uri}},
                    {"text": prompt},
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 8192,
        },
    }

    for model_name in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        try:
            logger.info(f"Transcribing audio slice with {model_name}...")
            res = requests.post(url, json=payload, timeout=90)
            if res.status_code == 200:
                data = res.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                parsed = robust_json_load(raw_text)
                if isinstance(parsed, list) and len(parsed) > 0:
                    adjusted_segments = []
                    for seg in parsed:
                        s = float(seg.get("start", 0.0)) + time_offset
                        e = float(seg.get("end", s + 45.0)) + time_offset
                        txt = str(seg.get("text", "")).strip()
                        if txt:
                            adjusted_segments.append({
                                "start": round(s, 2),
                                "end": round(max(e, s + 1.0), 2),
                                "text": txt,
                            })
                    return adjusted_segments
            else:
                logger.warning(f"{model_name} responded with status {res.status_code}: {res.text[:200]}")
        except Exception as e:
            logger.warning(f"Error querying {model_name} for audio transcription: {e}")

    return []


def transcribe_audio_file_with_gemini(
    audio_path: str,
    video_title: str = "",
    slice_duration_seconds: float = 1200.0,  # 20-minute slices: fast, highly reliable, never hits token limit
) -> list[dict]:
    """
    Transcribe a full video audio file (even 2-4 hours long) using Gemini Audio File API.
    Splits long audio into ~20-minute slices, uploads each to Gemini, transcribes verbatim,
    and returns a single unified list of chronological segments.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        logger.error("GEMINI_API_KEY not configured for Gemini audio transcription.")
        return []

    if not os.path.exists(audio_path):
        logger.error(f"Audio file not found: {audio_path}")
        return []

    total_duration = get_audio_duration(audio_path)
    if total_duration <= 0:
        logger.error(f"Could not determine audio duration for {audio_path}")
        return []

    logger.info(
        f"Starting Gemini speech transcription for '{os.path.basename(audio_path)}' "
        f"({total_duration:.1f}s / {total_duration/60:.1f} mins)..."
    )

    all_segments = []
    current_start = 0.0
    slice_idx = 0
    temp_dir = os.path.join(os.path.dirname(os.path.abspath(audio_path)), "temp_slices")
    os.makedirs(temp_dir, exist_ok=True)

    while current_start < total_duration:
        dur = min(slice_duration_seconds, total_duration - current_start)
        slice_idx += 1
        slice_file = os.path.join(temp_dir, f"slice_{slice_idx}_{int(current_start)}.mp3")

        logger.info(
            f"Processing slice {slice_idx}: {current_start:.0f}s to {current_start+dur:.0f}s "
            f"({dur/60:.1f} mins)..."
        )

        ok = compress_and_slice_audio(audio_path, current_start, dur, slice_file)
        if not ok:
            logger.error(f"Failed to create compressed slice {slice_idx}")
            current_start += dur
            continue

        file_meta = upload_audio_to_gemini(slice_file, api_key)
        if not file_meta:
            logger.error(f"Failed to upload slice {slice_idx} to Gemini File API")
            if os.path.exists(slice_file):
                try:
                    os.remove(slice_file)
                except OSError:
                    pass
            current_start += dur
            continue

        file_uri = file_meta.get("uri")
        file_name = file_meta.get("name")

        try:
            slice_segments = transcribe_audio_slice(
                file_uri,
                api_key,
                time_offset=current_start,
                video_title=video_title,
            )
            if slice_segments:
                logger.info(f"Slice {slice_idx} transcribed: {len(slice_segments)} verbatim segments.")
                all_segments.extend(slice_segments)
            else:
                logger.warning(f"Slice {slice_idx} produced no segments from Gemini.")
        finally:
            # Always clean up Gemini cloud file and local temporary slice
            delete_gemini_file(file_name, api_key)
            if os.path.exists(slice_file):
                try:
                    os.remove(slice_file)
                except OSError:
                    pass

        current_start += dur

    # Clean up temp folder if empty
    try:
        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)
    except OSError:
        pass

    # Sort all segments chronologically
    all_segments.sort(key=lambda x: x["start"])
    logger.info(
        f"Completed audio transcription for '{os.path.basename(audio_path)}': "
        f"{len(all_segments)} total verbatim segments."
    )
    return all_segments
