from services.vector_store_service import delete_course_chunks
from services.indexing_service import index_video
from services.youtube_service import get_playlist_videos


COURSE_ID = 1

PLAYLIST_ID = "PLIB57UzWtUdhdJ11pxTJk0QIp8pX3SFFf"


print("=" * 80)
print("COURSE RE-INDEX STARTED")
print("=" * 80)


# --------------------------------------------------
# STEP 1: Delete existing chunks for this course
# --------------------------------------------------

print("\nDeleting old Course 1 vectors...")

delete_course_chunks(COURSE_ID)

print("Old vectors deleted successfully.")


# --------------------------------------------------
# STEP 2: Fetch all playlist videos
# --------------------------------------------------

print("\nFetching playlist videos...")

playlist_data = get_playlist_videos(PLAYLIST_ID)

videos = playlist_data["items"]

print("Videos found:", len(videos))


# --------------------------------------------------
# STEP 3: Index every video
# --------------------------------------------------

successful = 0
failed = 0


for index, video in enumerate(videos, start=1):

    video_id = video["snippet"]["resourceId"]["videoId"]

    title = video["snippet"]["title"]

    print("\n" + "-" * 80)
    print(f"VIDEO {index}/{len(videos)}")
    print("Title:", title)
    print("Video ID:", video_id)

    try:

        result = index_video(
            video_id=video_id,
            course_id=COURSE_ID
        )

        print(
            "Chunks indexed:",
            result["chunks_indexed"]
        )

        successful += 1

    except Exception as e:

        print("ERROR:", e)

        failed += 1


# --------------------------------------------------
# STEP 4: Final summary
# --------------------------------------------------

print("\n" + "=" * 80)
print("RE-INDEX COMPLETE")
print("=" * 80)

print("Total videos:", len(videos))
print("Successful:", successful)
print("Failed:", failed)

print("=" * 80)