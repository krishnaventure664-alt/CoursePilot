with open("backend/main.py", "r", encoding="utf-8") as f:
    text = f.read()

old_endpoints = '''@app.get("/courses/{course_id}/quiz")
def get_quiz_endpoint(course_id: int, video_id: str | None = None, refresh: bool = False):
    questions = get_or_generate_quiz(course_id=course_id, video_id=video_id, force_refresh=refresh)
    return {"quiz": questions}


@app.get("/courses/{course_id}/flashcards")
def get_flashcards_endpoint(course_id: int, video_id: str | None = None, refresh: bool = False):
    cards = get_or_generate_flashcards(course_id=course_id, video_id=video_id, force_refresh=refresh)
    return {"flashcards": cards}'''

new_endpoints = '''@app.get("/courses/{course_id}/quiz")
def get_quiz_endpoint(course_id: int, video_id: str | None = None, refresh: bool = False, set_index: int | None = None):
    return get_or_generate_quiz(course_id=course_id, video_id=video_id, force_refresh=refresh, requested_set=set_index)


@app.get("/courses/{course_id}/flashcards")
def get_flashcards_endpoint(course_id: int, video_id: str | None = None, refresh: bool = False, set_index: int | None = None):
    return get_or_generate_flashcards(course_id=course_id, video_id=video_id, force_refresh=refresh, requested_set=set_index)'''

if old_endpoints in text:
    text = text.replace(old_endpoints, new_endpoints)
    print("Replaced quiz and flashcard endpoints in main.py!")
else:
    print("Could not find exact endpoints; doing normalized replace...")
    import re
    pattern = r'@app\.get\("/courses/{course_id}/quiz"\).*?(?=@app\.post\("/flashcards/{card_id}/review"\))'
    text = re.sub(pattern, new_endpoints + "\n\n\n", text, flags=re.DOTALL)
    print("Replaced endpoints using regex!")

with open("backend/main.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Saved main.py")
