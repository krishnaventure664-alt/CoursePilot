from services.transcript_service import get_video_transcript

video_id = "IOX8AWe_INg"

result = get_video_transcript(video_id)

print("Source:",result["source"])
print("Number of segments:",len(result["segments"]))

print("\nFirst Segment:")
print(result["segments"][0])