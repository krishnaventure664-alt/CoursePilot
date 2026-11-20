
from services.course_db_service import (
    get_course_videos,
    save_course_video,
)
from services.indexing_service import index_video
from services.bge_m3_vector_store_service import collection
from services.sparse_index_service import get_connection


COURSE_ID = 2

# Safety setting: test only ONE failed video first.
MAX_VIDEOS = 15


def verify_indexes(video_id):
    # Check the dense Chroma index.
    dense_result = collection.get(
        where={"video_id": video_id},
        include=["metadatas"],
    )
    dense_count = len(dense_result["ids"])

    # Check distinct chunk IDs in the sparse SQLite index.
    # GLOB treats underscores in YouTube IDs literally.
    chunk_pattern = f"course_{COURSE_ID}_{video_id}_chunk_*"

    with get_connection() as connection:
        sparse_count = connection.execute(
            """
            SELECT COUNT(DISTINCT chunk_id)
            FROM sparse_postings
            WHERE course_id = ?
              AND chunk_id GLOB ?
            """,
            (COURSE_ID, chunk_pattern),
        ).fetchone()[0]

    print("Dense chunks:", dense_count)
    print("Sparse chunks:", sparse_count)

    return dense_count > 0 and dense_count == sparse_count


def main():
    videos = get_course_videos(COURSE_ID)
    failed_videos = [
        video for video in videos
        if video["status"] == "failed"
    ]

    print("Failed videos found:", len(failed_videos))
    print("Videos to attempt this run:", min(
        MAX_VIDEOS, len(failed_videos)
    ))

    for video in failed_videos[:MAX_VIDEOS]:
        video_id = video["video_id"]
        title = video["title"]
        position = video["position"]

        print("\n" + "=" * 60)
        print("Playlist position:", position)
        print("Video ID:", video_id)
        print("Title:", title)

        try:
            result = index_video(video_id, COURSE_ID)
            print("Chunks produced:", result["chunks_indexed"])

            if result["chunks_indexed"] <= 0:
                raise RuntimeError("No chunks were produced.")

            if not verify_indexes(video_id):
                raise RuntimeError(
                    "Dense and sparse indexes do not match."
                )

            save_course_video(
                COURSE_ID,
                video_id,
                title,
                position,
                "completed",
            )

            print("RESULT: SUCCESS - status set to completed")

        except Exception as error:
            save_course_video(
                COURSE_ID,
                video_id,
                title,
                position,
                "failed",
            )
            print("RESULT: FAILED")
            print("Error:", type(error).__name__, str(error))
            print("The next run can retry this video.")

    print("\nRetry run finished.")


if __name__ == "__main__":
    main()
