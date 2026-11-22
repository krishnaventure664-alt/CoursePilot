# backend/main.py
import os
import sys

# Ensure backend root is always on sys.path regardless of execution directory
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Thermal & CPU thread capping: prevents 100% CPU core saturation, fan runaway, and laptop overheating
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"
os.environ["RAYON_NUM_THREADS"] = "4"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "max_split_size_mb:128")

try:
    import torch
    if hasattr(torch, "set_num_threads"):
        torch.set_num_threads(4)
    if hasattr(torch, "set_num_interop_threads"):
        torch.set_num_interop_threads(2)
except Exception:
    pass

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os

from services.youtube_service import extract_playlist_id, get_playlist_videos, extract_video_id, get_single_video_item
from services.transcript_service import get_video_transcript
from services.chunking_service import create_chunks
from services.hybrid_search_service import hybrid_search
from services.answer_service import generate_answer
from services.indexing_service import index_video
from services.course_db_service import (
    get_course_by_playlist,
    create_course,
    update_course_status,
    save_course_video,
    get_course_videos,
    get_all_courses,
    get_all_courses_with_videos,
    update_course_progress,
    get_course_progress,
    update_flashcard_status,
    find_completed_vault_course,
    clone_vault_course_to_user,
    can_delete_course_vectors,
    get_canonical_course_id,
    sync_vault_to_existing_course,
)
from services.study_tools_service import (
    get_or_generate_notes,
    get_or_generate_quiz,
    get_or_generate_flashcards,
    invalidate_lecture_chunks_cache,
)

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Depends, HTTPException, Security

from services.auth_service import get_current_user, get_optional_user

limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])
app = FastAPI(title="CoursePilot API", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

cors_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
frontend_url = os.getenv("FRONTEND_URL")
if frontend_url and frontend_url not in cors_origins:
    cors_origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CourseRequest(BaseModel):
    url: str
    user_id: str | None = None


class Course(BaseModel):
    id: int
    url: str
    title: str
    status: str


class Video(BaseModel):
    video_id: str
    title: str
    position: int
    status: str
    transcript: dict | None = None
    has_notes: int | bool | None = 0


class FlashcardReviewRequest(BaseModel):
    status: str  # 'new', 'reviewing', 'mastered'


@app.on_event("startup")
def startup_self_heal():
    """
    PERMANENT SELF-HEALING:
    Automatically resumes indexing for any course whose indexing was interrupted
    by a backend restart, crash, or PC sleep.
    """
    import threading
    from services.course_db_service import get_connection, get_course_videos

    def _resume_worker():
        try:
            with get_connection() as conn:
                rows = conn.execute("SELECT id FROM courses WHERE status = 'indexing'").fetchall()

            for row in rows:
                c_id = row["id"]
                with get_connection() as conn:
                    conn.execute(
                        "UPDATE course_videos SET status = 'queued' WHERE course_id = ? AND status = 'processing'",
                        (c_id,),
                    )
                videos = get_course_videos(c_id)
                if videos:
                    items = [
                        {"snippet": {"resourceId": {"videoId": v["video_id"]}, "title": v["title"]}}
                        for v in videos
                    ]
                    print(f"[Self-Heal] Resuming background indexing for interrupted course {c_id}...")
                    index_playlist_in_background(c_id, items)
        except Exception as e:
            print(f"[Self-Heal] Startup recovery error: {e}")

    threading.Thread(target=_resume_worker, daemon=True).start()

    def _prewarm_models_worker():
        import time
        # Non-blocking pause: lets FastAPI immediately bind port and serve frontend requests
        time.sleep(1.0)
        try:
            from services.bge_m3_service import get_bge_m3_model
            print("[Warmup] Pre-warming BGE-M3 embedding model in background...")
            model = get_bge_m3_model()
            # 1-token encode to allocate GPU fp16 memory and compile execution graph quietly
            model.encode([""])
            print("[Warmup] BGE-M3 ready: 0ms lag on first video indexing!")
        except Exception as e:
            print(f"[Warmup] Non-critical BGE-M3 warmup note: {e}")

        try:
            from services.reranker_service import get_reranker_model
            print("[Warmup] Pre-warming BGE-Reranker model on GPU in background...")
            reranker = get_reranker_model()
            # 1-pair warm compute score to compile CUDA execution graph quietly
            reranker.compute_score([["q", "t"]], max_length=64)
            print("[Warmup] BGE-Reranker ready: 0ms lag on Ask AI Q&A answers!")
        except Exception as e:
            print(f"[Warmup] Non-critical Reranker warmup note: {e}")

    threading.Thread(target=_prewarm_models_worker, daemon=True).start()


@app.get("/")
def home():
    return {"message": "CoursePilot backend is running!"}


@app.get("/courses")
@limiter.limit("60/minute")
def list_courses(request: Request, user_id: str = Depends(get_current_user)):
    courses = get_all_courses_with_videos(user_id=user_id)
    return {"courses": courses}


import threading
_indexing_semaphore = threading.Semaphore(1)

def index_playlist_in_background(course_id: int, items: list):
    """
    High-throughput, low-load asynchronous indexing for 40+ hour playlists:
    Protected by _indexing_semaphore(1) to guarantee that even if 10+ users add courses simultaneously,
    indexing tasks run safely one-by-one without GPU VRAM exhaustion or PC freeze.
    """
    with _indexing_semaphore:
        import gc
        import time
        try:
            import torch
            has_cuda = torch.cuda.is_available()
        except Exception:
            has_cuda = False

        from concurrent.futures import ThreadPoolExecutor
        from services.bge_m3_vector_store_service import collection
        from services.course_db_service import get_connection

        # 1. State check: Verify course still exists and isn't already completed
        with get_connection() as conn:
            c_row = conn.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
            if not c_row:
                print(f"[Queue Worker] Course {course_id} no longer exists. Skipping.")
                return
            if c_row["status"] == "completed":
                print(f"[Queue Worker] Course {course_id} is already completed. Skipping redundant indexing.")
                return
            current_playlist_id = c_row["playlist_id"]

        # 2. Global Vault match check: Did another job complete this playlist while we waited in queue?
        completed_vault = find_completed_vault_course(current_playlist_id)
        if completed_vault and completed_vault["id"] != course_id:
            print(f"[Queue Vault Match] Course {course_id} matched completed vault course {completed_vault['id']}! Instant sync...")
            synced = sync_vault_to_existing_course(
                source_course_id=completed_vault["id"],
                target_course_id=course_id,
            )
            if synced:
                update_course_progress(course_id, completed_vault["total_videos"], completed_vault["total_videos"], "completed")
                print(f"[Queue Vault Match] Course {course_id} successfully linked to vault course {completed_vault['id']} in 0.01s!")
                return

        total = len(items)
        completed = 0
    
        indexed_data = collection.get(
            where={"course_id": course_id},
            include=["metadatas"],
        )
        indexed_video_ids = {
            metadata["video_id"]
            for metadata in indexed_data["metadatas"]
            if metadata and metadata.get("video_id")
        }
    
        # Background executor for active lecture pre-generation (1 worker prevents API contention)
        first_lecture_executor = ThreadPoolExecutor(max_workers=1)
        first_lecture_started = False
    
        def _safe_pregenerate_active_lecture(c_id: int, v_id: str):
            """Pre-generate Notes, Quiz, and Flashcards for the active lecture in background."""
            try:
                get_or_generate_notes(c_id, v_id)
            except Exception as note_err:
                print(f"Background note generation for active lecture {v_id}: {note_err}")
            try:
                get_or_generate_quiz(c_id, v_id)
            except Exception as q_err:
                print(f"Background quiz generation for active lecture {v_id}: {q_err}")
            try:
                get_or_generate_flashcards(c_id, v_id)
            except Exception as f_err:
                print(f"Background flashcard generation for active lecture {v_id}: {f_err}")
    
        for position, item in enumerate(items, start=1):
            snippet = item["snippet"]
            video_id = snippet["resourceId"]["videoId"]
            title = snippet["title"]
    
            if video_id in indexed_video_ids:
                completed += 1
                save_course_video(course_id, video_id, title, position, "completed")
                update_course_progress(course_id, completed, total, "indexing")
                if not first_lecture_started and position == 1:
                    first_lecture_started = True
                    first_lecture_executor.submit(_safe_pregenerate_active_lecture, course_id, video_id)
                continue
    
            save_course_video(course_id, video_id, title, position, "processing")
            try:
                res = index_video(video_id=video_id, course_id=course_id, video_title=title)
                video_status = "completed" if res.get("chunks_indexed", 0) > 0 else "failed"
            except Exception as e:
                video_status = "failed"
                print(f"Error indexing video {video_id}: {e}")
    
            if video_status == "completed":
                completed += 1
                # Eagerly launch study tools pre-generation for the very first completed lecture
                if not first_lecture_started:
                    first_lecture_started = True
                    first_lecture_executor.submit(_safe_pregenerate_active_lecture, course_id, video_id)
    
            save_course_video(course_id, video_id, title, position, video_status)
            update_course_progress(course_id, completed, total, "indexing")
    
            # Thermal breather + immediate tensor garbage collection keeps CPU/GPU cool
            gc.collect()
            if has_cuda:
                torch.cuda.empty_cache()
            time.sleep(0.02)
    
        first_lecture_executor.shutdown(wait=False)
    
        final_status = "completed" if completed > 0 else "failed"
        update_course_progress(course_id, completed, total, final_status)
        print(f"Course {course_id} background indexing finished: {completed}/{total} videos indexed.")
    
        # Deep cleanup: return all freed memory back to Windows OS
        gc.collect()
        if has_cuda:
            torch.cuda.empty_cache()
    

@app.post("/courses")
@limiter.limit("10/minute")
def add_courses(
    request: Request,
    course: CourseRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
):
    url = course.url.strip()
    playlist_id = extract_playlist_id(url)
    video_id = extract_video_id(url) if not playlist_id else None

    # 1. Validation check
    if not playlist_id and not video_id:
        return {"message": "Invalid YouTube URL. Please provide a playlist or video link."}

    # 2. Fetch items (multi-video playlist or 1-video course)
    if playlist_id:
        playlist_data = get_playlist_videos(playlist_id)
        items = playlist_data.get("items", [])
        storage_id = playlist_id
    else:
        single_item = get_single_video_item(video_id)
        items = [single_item] if single_item else []
        storage_id = f"video_{video_id}"

    if not items:
        return {"message": "No video content found. Please check URL or access permissions."}

    # 3. Secure multi-tenancy: strictly use verified user_id from token
    req_user_id = user_id
    existing_course = get_course_by_playlist(storage_id, user_id=req_user_id)
    if existing_course:
        course_record = existing_course
        course_id = course_record["id"]
        if course_record.get("status") == "completed":
            return {
                "course": course_record,
                "videos": get_course_videos(course_id),
            }
    else:
        # 3b. GLOBAL COURSE VAULT: Check if ANY user already indexed this course completely!
        vault_course = find_completed_vault_course(storage_id)
        if vault_course:
            print(f"[Course Vault] Instant match for '{storage_id}'! Linking pre-computed course {vault_course['id']} to user '{req_user_id}'...")
            cloned_course = clone_vault_course_to_user(
                source_course_id=vault_course["id"],
                user_id=req_user_id,
                url=course.url,
            )
            return {
                "course": cloned_course,
                "videos": get_course_videos(cloned_course["id"]),
                "vault_instant_linked": True,
            }

        course_record = create_course(
            playlist_id=storage_id,
            url=course.url,
            title=items[0]["snippet"]["title"],
            user_id=req_user_id,
        )
        course_id = course_record["id"]

    # 4. Save video entries & launch progressive background indexing
    videos = []
    for position, item in enumerate(items, start=1):
        snippet = item["snippet"]
        v_id = snippet["resourceId"]["videoId"]
        title = snippet["title"]
        save_course_video(course_id, v_id, title, position, "queued")
        videos.append(Video(video_id=v_id, title=title, position=position, status="queued"))

    update_course_progress(course_id, completed=0, total=len(items), status="indexing")
    course_record["status"] = "indexing"

    # Automatically indexes 1 video or 50 videos identically
    background_tasks.add_task(index_playlist_in_background, course_id, items)

    return {
        "course": course_record,
        "videos": videos,
    }


@app.get("/courses/{course_id}/progress")
def get_progress_endpoint(course_id: int):
    return get_course_progress(course_id)


@app.post("/courses/{course_id}/resume")
def resume_course_endpoint(course_id: int, background_tasks: BackgroundTasks):
    """Resumes indexing for any course whose indexing was interrupted."""
    from services.course_db_service import get_connection, get_course_videos
    videos = get_course_videos(course_id)
    if not videos:
        return {"error": "Course not found"}

    with get_connection() as conn:
        conn.execute("UPDATE course_videos SET status = 'queued' WHERE course_id = ? AND status IN ('processing', 'failed')", (course_id,))
        conn.execute("UPDATE courses SET status = 'indexing' WHERE id = ?", (course_id,))

    items = []
    for v in videos:
        items.append({
            "snippet": {
                "resourceId": {"videoId": v["video_id"]},
                "title": v["title"],
            }
        })

    background_tasks.add_task(index_playlist_in_background, course_id, items)
    return {"status": "resumed", "course_id": course_id, "videos_count": len(items)}

@app.delete("/courses/{course_id}")
def delete_course_endpoint(course_id: int, user_id: str = Depends(get_current_user)):
    from services.bge_m3_vector_store_service import delete_course_dense_chunks
    from services.sparse_index_service import delete_course_sparse_postings
    from services.course_db_service import (
        delete_course_from_db,
        get_course_videos,
        can_delete_course_vectors,
        get_canonical_course_id,
        check_course_access,
    )

    if not check_course_access(course_id, user_id):
        raise HTTPException(status_code=403, detail="You do not have permission to delete this course.")

    canonical_id = get_canonical_course_id(course_id)
    should_delete_vectors = can_delete_course_vectors(course_id)

    # 1 & 2. Free vector storage ONLY if no other user is sharing the canonical course vault
    if should_delete_vectors:
        try:
            delete_course_dense_chunks(canonical_id)
        except Exception as e:
            print(f"Chroma delete error for course {canonical_id}: {e}")

        try:
            delete_course_sparse_postings(canonical_id)
        except Exception as e:
            print(f"Sparse index delete error for course {canonical_id}: {e}")

        videos = get_course_videos(course_id)
        for v in videos:
            mp3_path = os.path.join("downloads", f"{v['video_id']}.mp3")
            if os.path.exists(mp3_path):
                try:
                    os.remove(mp3_path)
                except OSError:
                    pass

    # 3. Invalidate in-memory chunk cache and delete course records
    invalidate_lecture_chunks_cache(course_id)
    delete_course_from_db(course_id)

    return {
        "status": "success",
        "course_id": course_id,
        "message": f"Course {course_id} removed successfully from user library.",
    }
@app.get("/search")
def search(query: str, course_id: int):
    results = hybrid_search(query=query, course_id=course_id, final_top_k=5)
    return {
        "query": query,
        "course_id": course_id,
        "results": results,
    }


@app.get("/ask")
@limiter.limit("30/minute")
def ask_question(request: Request, question: str, course_id: int, user_id: str = Depends(get_optional_user)):
    result = generate_answer(
        question,
        course_id=course_id,
    )
    return {
        "question": question,
        "course_id": course_id,
        "answer": result["answer"],
        "sources": result["sources"],
    }


@app.get("/courses/{course_id}/notes")
def get_notes_endpoint(course_id: int, video_id: str, refresh: bool = False):
    return get_or_generate_notes(course_id=course_id, video_id=video_id, force_refresh=refresh)

def batch_generate_notes_in_background(course_id: int):
    """Generates notes sequentially in background for any lecture missing notes."""
    from services.course_db_service import get_all_course_notes_db
    lectures = get_all_course_notes_db(course_id)
    for l in lectures:
        if not l.get("notes") and l.get("status") == "completed":
            try:
                get_or_generate_notes(course_id=course_id, video_id=l["video_id"])
            except Exception as e:
                print(f"Error auto-generating notes for {l['video_id']}: {e}")


@app.get("/courses/{course_id}/all-notes")
def get_all_notes_endpoint(course_id: int):
    from services.study_tools_service import compile_course_handbook
    from services.course_db_service import get_connection

    with get_connection() as conn:
        row = conn.execute("SELECT title FROM courses WHERE id = ?", (course_id,)).fetchone()
    title = row["title"] if row else "Course"

    return compile_course_handbook(course_id, course_title=title)


@app.post("/courses/{course_id}/generate-all-notes")
def trigger_generate_all_notes_endpoint(course_id: int, background_tasks: BackgroundTasks):
    background_tasks.add_task(batch_generate_notes_in_background, course_id)
    return {
        "status": "started",
        "message": f"Background notes generation started for course {course_id}.",
    }

def batch_generate_detailed_notes_in_background(course_id: int):
    """Generates exhaustive detailed notes sequentially in background for all lectures."""
    from services.course_db_service import get_all_detailed_course_notes_db
    from services.study_tools_service import get_or_generate_detailed_notes
    lectures = get_all_detailed_course_notes_db(course_id)
    for l in lectures:
        if not l.get("notes") and l.get("status") == "completed":
            try:
                get_or_generate_detailed_notes(course_id=course_id, video_id=l["video_id"])
            except Exception as e:
                print(f"Error generating background detailed notes for {l['video_id']}: {e}")

@app.post("/courses/{course_id}/generate-all-detailed-notes")
def trigger_generate_all_detailed_notes_endpoint(course_id: int, background_tasks: BackgroundTasks):
    background_tasks.add_task(batch_generate_detailed_notes_in_background, course_id)
    return {
        "status": "started",
        "message": f"Background detailed notes generation started for course {course_id}.",
    }
@app.get("/courses/{course_id}/quiz")
def get_quiz_endpoint(course_id: int, video_id: str | None = None, refresh: bool = False, set_index: int | None = None):
    return get_or_generate_quiz(course_id=course_id, video_id=video_id, force_refresh=refresh, requested_set=set_index)


@app.get("/courses/{course_id}/flashcards")
def get_flashcards_endpoint(course_id: int, video_id: str | None = None, refresh: bool = False, set_index: int | None = None):
    return get_or_generate_flashcards(course_id=course_id, video_id=video_id, force_refresh=refresh, requested_set=set_index)


@app.post("/flashcards/{card_id}/review")
def review_flashcard_endpoint(card_id: int, req: FlashcardReviewRequest):
    update_flashcard_status(card_id=card_id, status=req.status)
    return {"status": "success", "card_id": card_id, "new_status": req.status}
from fastapi.responses import Response
from services.pdf_export_service import markdown_to_pdf_bytes
from services.study_tools_service import (
    get_or_generate_notes,
    compile_course_handbook,
    get_or_generate_detailed_notes,
    compile_detailed_course_handbook,
)

# 1. Fetch In-Depth Master Notes for a video
@app.get("/courses/{course_id}/detailed-notes")
def get_detailed_notes_endpoint(course_id: int, video_id: str, refresh: bool = False):
    return get_or_generate_detailed_notes(course_id=course_id, video_id=video_id, force_refresh=refresh)

# 2. Fetch In-Depth Master Handbook for the whole course
@app.get("/courses/{course_id}/detailed-handbook")
def get_detailed_handbook_endpoint(course_id: int):
    from services.course_db_service import get_connection
    with get_connection() as conn:
        row = conn.execute("SELECT title FROM courses WHERE id = ?", (course_id,)).fetchone()
    title = row["title"] if row else "Course"
    return compile_detailed_course_handbook(course_id=course_id, course_title=title)

# 3. Export PDF for In-Depth Notes
@app.get("/courses/{course_id}/detailed-notes-pdf")
def export_detailed_notes_pdf(course_id: int, video_id: str):
    res = get_or_generate_detailed_notes(course_id=course_id, video_id=video_id)
    pdf_bytes = markdown_to_pdf_bytes(
        title="Comprehensive Lecture Master Notes",
        subtitle=f"Course #{course_id} • Video ID: {video_id}",
        markdown_text=res.get("notes", "No notes available."),
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Detailed_Notes_{course_id}_{video_id}.pdf"'},
    )

# 4. Export PDF for Complete Course Handbook
@app.get("/courses/{course_id}/detailed-handbook-pdf")
def export_detailed_handbook_pdf(course_id: int):
    from services.course_db_service import get_connection
    with get_connection() as conn:
        row = conn.execute("SELECT title FROM courses WHERE id = ?", (course_id,)).fetchone()
    title = row["title"] if row else "Course"
    handbook_data = compile_detailed_course_handbook(course_id=course_id, course_title=title)
    pdf_bytes = markdown_to_pdf_bytes(
        title=f"{handbook_data.get('course_title', 'Course')} - Master Study Handbook",
        subtitle=f"Full Syllabus Exhaustive Coverage • {handbook_data.get('total', 0)} Lectures",
        markdown_text=handbook_data.get("handbook", "No handbook compiled."),
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Course_{course_id}_Master_Handbook.pdf"'},
    )# 5. Export PDF for Quick Revision Notes (Single Lecture)
@app.get("/courses/{course_id}/notes-pdf")
def export_notes_pdf(course_id: int, video_id: str):
    res = get_or_generate_notes(course_id=course_id, video_id=video_id)
    pdf_bytes = markdown_to_pdf_bytes(
        title="Lecture Quick Revision Notes",
        subtitle=f"Course #{course_id} • Video ID: {video_id}",
        markdown_text=res.get("notes", "No notes available."),
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Quick_Notes_{course_id}_{video_id}.pdf"'},
    )

# 6. Export PDF for Complete Course Quick Revision Handbook
@app.get("/courses/{course_id}/all-notes-pdf")
def export_all_notes_pdf(course_id: int):
    from services.course_db_service import get_connection
    with get_connection() as conn:
        row = conn.execute("SELECT title FROM courses WHERE id = ?", (course_id,)).fetchone()
    title = row["title"] if row else "Course"
    handbook_data = compile_course_handbook(course_id=course_id, course_title=title)
    pdf_bytes = markdown_to_pdf_bytes(
        title=f"{handbook_data.get('course_title', 'Course')} - Quick Revision Guide",
        subtitle=f"Rapid Revision Handbook • {handbook_data.get('total', 0)} Lectures",
        markdown_text=handbook_data.get("handbook", "No handbook compiled."),
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="Course_{course_id}_Quick_Handbook.pdf"'},
    )


@app.get("/admin/metrics")
def get_metrics_endpoint():
    """Returns verified student counts and usage metrics for interviewer evaluation."""
    from services.course_db_service import get_admin_metrics
    return get_admin_metrics()


class FeedbackRequest(BaseModel):
    feedback_type: str = "general"
    rating: int = 0
    message: str = ""
    context: dict = {}
    user_email: str = ""


@app.post("/feedback")
def submit_feedback_endpoint(
    req: FeedbackRequest,
    user_id: str = Depends(get_current_user),
):
    """Records user feedback, ratings, and issue reports linked to verified user."""
    from services.course_db_service import save_user_feedback
    fid = save_user_feedback(
        user_id=user_id,
        feedback_type=req.feedback_type,
        rating=req.rating,
        message=req.message,
        context_data=req.context,
        user_email=req.user_email,
    )
    return {"status": "success", "feedback_id": fid}


@app.get("/admin/feedback")
def get_feedback_endpoint():
    """Returns recent user feedback records for review and interviewer metrics."""
    from services.course_db_service import get_all_feedback
    return {"feedback": get_all_feedback()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
