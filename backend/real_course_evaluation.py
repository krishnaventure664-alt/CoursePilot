from services.answer_service import generate_answer


COURSE_ID = 1


TEST_QUESTIONS = [

    # ==========================================================
    # ENGLISH — ANSWERABLE
    # ==========================================================

    {
        "id": 1,
        "question": "What is Active Recall?",
        "expected": "answerable",
    },

    {
        "id": 2,
        "question": "How should Active Recall be applied in Ancient History?",
        "expected": "answerable",
    },

    {
        "id": 3,
        "question": "What was the Indus Valley Civilization?",
        "expected": "answerable",
    },

    {
        "id": 4,
        "question": "What are the main features of the Vedic Age?",
        "expected": "answerable",
    },

    {
        "id": 5,
        "question": "What is Buddhism?",
        "expected": "answerable",
    },

    {
        "id": 6,
        "question": "What is Jainism?",
        "expected": "answerable",
    },

    {
        "id": 7,
        "question": "What was the Gupta Empire?",
        "expected": "answerable",
    },

    {
        "id": 8,
        "question": "What is the Sangam period?",
        "expected": "answerable",
    },


    # ==========================================================
    # HINDI — ANSWERABLE
    # ==========================================================

    {
        "id": 9,
        "question": "एक्टिव रिकॉल क्या है?",
        "expected": "answerable",
    },

    {
        "id": 10,
        "question": "सिंधु घाटी सभ्यता क्या थी?",
        "expected": "answerable",
    },


    # ==========================================================
    # HINGLISH — ANSWERABLE
    # ==========================================================

    {
        "id": 11,
        "question": "Active Recall ko Ancient History mein kaise apply karna hai?",
        "expected": "answerable",
    },

    {
        "id": 12,
        "question": "Buddhism kya hai?",
        "expected": "answerable",
    },


    # ==========================================================
    # OUTSIDE COURSE — SHOULD NOT ANSWER
    # ==========================================================

    {
        "id": 13,
        "question": "What is Machine Learning?",
        "expected": "unanswerable",
    },

    {
        "id": 14,
        "question": "What is Quantum Computing?",
        "expected": "unanswerable",
    },

    {
        "id": 15,
        "question": "What is the capital of France?",
        "expected": "unanswerable",
    },

    {
        "id": 16,
        "question": "Explain Python programming.",
        "expected": "unanswerable",
    },
]


def main():

    print("=" * 80)
    print("COURSEPILOT REAL COURSE EVALUATION")
    print("=" * 80)

    print(f"Course ID: {COURSE_ID}")
    print(f"Total questions: {len(TEST_QUESTIONS)}")

    print()

    for test in TEST_QUESTIONS:

        print("=" * 80)
        print(
            f"QUESTION {test['id']} "
            f"[Expected: {test['expected']}]"
        )
        print("=" * 80)

        print("Question:")
        print(test["question"])

        print()
        print("Generating answer...")

        try:

            result = generate_answer(
                question=test["question"],
                course_id=COURSE_ID
            )

            print()
            print("ANSWER:")
            print(result["answer"])

            print()
            print(
                f"SOURCES RETURNED: "
                f"{len(result.get('sources', []))}"
            )

        except Exception as e:

            print()
            print("ERROR:")
            print(type(e).__name__, str(e))

        print()


if __name__ == "__main__":
    main()