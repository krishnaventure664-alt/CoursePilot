from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from urllib.parse import urlparse,parse_qs
import os
import requests
from services.youtube_service import extract_playlist_id,get_playlist_videos
from services.transcript_service import get_video_transcript
from services.chunking_service import create_chunks
from services.search_service import search_course
from services.answer_service import generate_answer
from services.indexing_service import index_video


load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,

allow_origins=["http://localhost:3000"],
allow_credentials = True,
allow_methods=["*"],
allow_headers=["*"],
)

class CourseRequest(BaseModel):
    url:str

class Course(BaseModel):
    id:int
    url:str
    title:str
    status:str

class Video(BaseModel):
    video_id: str
    title: str
    position:int
    status:str
    transcript:dict | None=None

courses_counter = 1
courses = []

@app.get("/")
def home():
    return {"message":"CoursePilot backend is running!"}

@app.post("/courses")
def add_courses(course:CourseRequest):
    global courses_counter
    playlist_id = extract_playlist_id(course.url)

    if playlist_id is None:
        return{
            "message":"Invalid YouTube playlist URL"
        }
    playlist_data = get_playlist_videos(playlist_id)
    print("NUMBER OF VIDEOS FROM YOUTUBE:",len(playlist_data.get("items",[])))
    videos = []
    course_transcripts = []
    for index, item in enumerate(playlist_data.get("items",[])):
        video_id = item["snippet"]["resourceId"]["videoId"]


        video = Video(
            video_id=video_id,
            title=item["snippet"]["title"],
            position=index+1,
            status="processing"
        )

        videos.append(video)

        print(f"Indexing video {index+1}:{video.title}")
        try:

            result = index_video(
                video_id=video_id,
                course_id=courses_counter
            )
            print(f"Indexed {result['chunks_indexed']} chunks")
            course_transcripts.append(
                result["transcript"]
            )
            video.status = "completed"
        except Exception as error:
            print(f"Failed to index video{index+1}:{error}")
            video.status = "failed"

    
    new_course = Course(
        id=courses_counter,
        url=course.url,
        title="YouTube Course",
        status="pending"
    )

    new_course = Course(
        id=courses_counter,
        url=course.url,
        title="YouTube Course",
        status="pending"
    )   

    courses.append({
        "course":new_course,
        "videos":videos
    })
    courses_counter +=1

    return{
        "course":new_course,
        "videos":videos
    }

@app.get("/config-test")
def config_test():
    return {
        "youtube_api_configured":
YOUTUBE_API_KEY is not None,
    }

@app.get("/youtube-test")
def youtube_test():
    url = "https://www.googleapis.com/youtube/v3/videos"

    params = {
        "part":"snippet",
        "id":"dQw4w9WgXcQ",
        "key":YOUTUBE_API_KEY
    }
    response = requests.get(url,params=params)

    return response.json()

@app.get("/transcript-test/{video_id}")
def transcript_test(video_id:str):
    transcript = get_video_transcript(video_id)

    return{
        "video_id":video_id,
        "transcript":transcript
    }

@app.get("/chunk-test/{video_id}")
def chunk_test(video_id:str):

    transcript = get_video_transcript(video_id)
    chunks = create_chunks(
        transcript["segments"],
        chunk_size=5
    )

    return{
        "video_id":video_id,
        "source":transcript["source"],
        "chunks":chunks
    }

@app.get("/process-video/{video_id}")
def process_video(video_id:str):
    transcript = get_video_transcript(video_id)

    for course in courses:
        for video in course["videos"]:

            if video.video_id == video_id:
                video.transcript = transcript
                video.status = "completed"

            return{
                "video_id":video_id,
                "status":"completed",
                "transcript":transcript
            }
    return{
        "message":"Video not found"
    }

@app.get("/playlist/{playlist_id}")
def get_playlist(playlist_id:str):
    url="https://www.googleapis.com/youtube/v3/playlistItems"

    params = {
        "part":"snippet",
        "playlistId":playlist_id,
        "maxResults":50,
        "key":YOUTUBE_API_KEY
    }
    response = requests.get(url,params=params)
    return response.json()

@app.get("/extract-playlist")
def extract_playlist(url:str):
    playlist_id = extract_playlist_id(url)

    return{
        "playlist_id":playlist_id
    }

@app.get("/search")
def search(query:str):

    results = search_course(query)

    return{
        "query":query,
        "results":results
    }

@app.get("/ask")
def ask_question(question:str,
                 course_id:int
):

    result = generate_answer(
        question,
        course_id=course_id
        )

    return{
        "question":question,
        "course_id":course_id,
        "answer":result["answer"],
        "sources":result["sources"]
    }