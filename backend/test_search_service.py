from services.search_service import search_course

query = "What is active recalling?"

results = search_course(query)

print("\nCourse Search Results:\n")

for index,result in enumerate(results):
    print(f"Result {index+1}")

    print("Text:")
    print(result["text"])

    print("\nVideo ID:")
    print(result["video_id"])

    print("\nTimestamp:")
    print(f'{result["start"]}->{result["end"]}')

    print("\nDistances:")
    print(result["distance"])

    print("\n"+"="*50+"\n")