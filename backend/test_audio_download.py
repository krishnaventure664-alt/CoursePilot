from services.youtube_audio_service import download_audio

video_id = "nlVeEwkbtBU"
audio_path = download_audio(video_id)

print("AUDIO DOWNLOADED:")
print(audio_path)