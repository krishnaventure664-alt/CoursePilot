from services.transcript_service import get_video_transcript
from services.chunking_service import create_chunks


VIDEO_ID = "nlVeEwkbtBU"


print("=" * 80)
print("TESTING NEW CHUNKING")
print("=" * 80)


# Get transcript
transcript_data = get_video_transcript(VIDEO_ID)

segments = transcript_data["segments"]

print("\nTranscript segments:", len(segments))


# Create chunks using the new chunking logic
chunks = create_chunks(segments)


print("Chunks created:", len(chunks))


# Show first 5 chunks
for index, chunk in enumerate(chunks[:5], start=1):

    print("\n" + "-" * 80)

    print("CHUNK:", index)

    print("START:", chunk["start"])

    print("END:", chunk["end"])

    print("TEXT:")

    print(chunk["text"])


print("\n" + "=" * 80)
print("CHUNKING TEST COMPLETE")
print("=" * 80)