import os
import re
import requests
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

load_dotenv()
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")


def extract_playlist_id(url: str):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    return query_params.get("list", [None])[0]


def get_playlist_videos(playlist_id: str):
    videos = []
    
    # 1. Try Google YouTube Data API if key is present
    if YOUTUBE_API_KEY:
        url = "https://www.googleapis.com/youtube/v3/playlistItems"
        next_page_token = None
        try:
            while True:
                params = {
                    "part": "snippet",
                    "playlistId": playlist_id,
                    "maxResults": 50,
                    "key": YOUTUBE_API_KEY
                }
                if next_page_token:
                    params["pageToken"] = next_page_token

                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                items = data.get("items", [])
                if not items:
                    break
                videos.extend(items)
                next_page_token = data.get("nextPageToken")
                if not next_page_token:
                    break
        except Exception as e:
            print(f"YouTube Data API error for playlist: {e}")

    # 2. Fallback: extract playlist via yt-dlp (works with zero API key)
    if not videos:
        try:
            import yt_dlp
            ydl_opts = {
                "extract_flat": True,
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/playlist?list={playlist_id}", download=False)
                for entry in (info.get("entries") or []):
                    vid = entry.get("id")
                    if vid:
                        videos.append({
                            "snippet": {
                                "title": entry.get("title", f"Video {vid}"),
                                "resourceId": {"videoId": vid},
                                "description": entry.get("description", ""),
                            }
                        })
        except Exception as ydl_err:
            print(f"yt-dlp playlist extraction fallback error: {ydl_err}")

    return {
        "items": videos
    }


# --- Extract single video ID from youtu.be, watch?v=, or shorts ---
def extract_video_id(url: str) -> str | None:
    patterns = [
        r"(?:v=|\/videos\/|embed\/|shorts\/|\/v\/|youtu\.be\/|\/watch\?v=|\/watch\?.+&v=)([\w-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


# --- Fetch single video details and format as standard item ---
def get_single_video_item(video_id: str) -> dict:
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet",
        "id": video_id,
        "key": YOUTUBE_API_KEY
    }
    try:
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        items = data.get("items", [])
        if items:
            snippet = items[0]["snippet"]
            return {
                "snippet": {
                    "title": snippet.get("title", f"Video {video_id}"),
                    "resourceId": {"videoId": video_id},
                    "description": snippet.get("description", ""),
                }
            }
    except Exception as e:
        print(f"YouTube Data API error for single video: {e}")

    # Fallback using yt-dlp if YouTube API key is missing/limited
    try:
        import yt_dlp
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            return {
                "snippet": {
                    "title": info.get("title", f"Video {video_id}"),
                    "resourceId": {"videoId": video_id},
                    "description": info.get("description", ""),
                }
            }
    except Exception as ydl_err:
        print(f"yt-dlp fallback error: {ydl_err}")

    return {
        "snippet": {
            "title": f"Video {video_id}",
            "resourceId": {"videoId": video_id},
            "description": "",
        }
    }
