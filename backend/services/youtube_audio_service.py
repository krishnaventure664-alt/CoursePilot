import os
import yt_dlp

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)


def get_existing_audio_path(video_id: str) -> str | None:
    search_dirs = [
        DOWNLOADS_DIR,
        "downloads",
        "backend/downloads",
        os.path.join(os.getcwd(), "downloads"),
        os.path.join(os.getcwd(), "backend", "downloads"),
    ]
    for d in search_dirs:
        for ext in ["webm", "m4a", "mp3", "opus", "mp4"]:
            path = os.path.join(d, f"{video_id}.{ext}")
            if os.path.exists(path) and os.path.getsize(path) > 10000:
                return os.path.abspath(path)
    return None


def download_audio(video_id: str) -> str:
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)

    # 1. Reuse existing downloaded audio file if present
    existing = get_existing_audio_path(video_id)
    if existing:
        return existing

    # 2. Download highest quality audio directly into DOWNLOADS_DIR
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    out_template = os.path.join(DOWNLOADS_DIR, "%(id)s.%(ext)s")
    
    # Try multiple player clients to bypass datacenter IP restrictions
    client_configs = [
        ["android", "mweb"],
        ["ios"],
        ["mweb"],
        ["web"],
    ]

    download_success = False
    for clients in client_configs:
        try:
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": out_template,
                "quiet": True,
                "no_warnings": True,
                "extractor_args": {
                    "youtube": {
                        "player_client": clients,
                    }
                },
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(video_url, download=True)
            existing = get_existing_audio_path(video_id)
            if existing:
                download_success = True
                return existing
        except Exception:
            continue

    existing = get_existing_audio_path(video_id)
    if existing:
        return existing

    return os.path.join(DOWNLOADS_DIR, f"{video_id}.webm")
