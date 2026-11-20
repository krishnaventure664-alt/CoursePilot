from services.search_service import search_course


COURSE_ID = 1


QUESTIONS = [
    "What was the Indus Valley Civilization?",
    "What are the main features of the Vedic Age?",
    "What is Buddhism?",
    "What is Jainism?",
    "What was the Gupta Empire?",
    "What is the Sangam period?",
]


def main():

    print("=" * 100)
    print("COURSEPILOT RETRIEVAL DIAGNOSTICS")
    print("=" * 100)

    for question in QUESTIONS:

        print()
        print("=" * 100)
        print("QUESTION")
        print("=" * 100)
        print(question)

        try:

            results = search_course(
                query=question,
                course_id=COURSE_ID,
                n_results=5
            )

            print()
            print(f"RESULTS FOUND: {len(results)}")

            if not results:
                print("NO RESULTS")
                continue

            for index, result in enumerate(results, start=1):

                print()
                print("-" * 100)
                print(f"RESULT {index}")
                print("-" * 100)

                print(f"Video ID      : {result.get('video_id')}")
                print(f"Start         : {result.get('start')}")
                print(f"End           : {result.get('end')}")
                print(f"Distance      : {result.get('distance')}")
                print(f"Rerank Score  : {result.get('rerank_score')}")

                print()
                print("TEXT:")
                print(result.get("text", ""))

        except Exception as e:

            print()
            print("ERROR")
            print(type(e).__name__, str(e))

    print()
    print("=" * 100)
    print("DIAGNOSTICS COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    main()