from services.answer_service import generate_answer


COURSE_ID = 1


questions = [
    "What is active recall?",
    "एक्टिव रिकॉल क्या है?",
    "active recall kya hai?"
]


for question in questions:

    print("\n" + "=" * 80)

    print("QUESTION:")
    print(question)

    print("=" * 80)

    result = generate_answer(
        question=question,
        course_id=COURSE_ID
    )

    print("\nANSWER:")
    print(result["answer"])

    print("\nSOURCES:")
    print(len(result["sources"]))