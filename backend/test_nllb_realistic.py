from services.nllb_service import translate_text


test_answers = [

    "Active recall is a learning technique that improves retention and helps students remember information.",

    "The Indus Valley Civilization was one of the earliest urban civilizations in South Asia.",

    "Active recall helps students remember information and improves their performance.",

    "The Vedic Age is an important period of ancient Indian history.",

    "Students can use active recall to test their knowledge instead of simply reading the notes.",

    "The Gupta period is known for developments in science, mathematics, literature, and art.",

    "This technique improves memory by asking students to recall information from memory.",

    "The course explains the main features of the Indus Valley Civilization.",

    "Active recall is useful because it requires students to actively retrieve information.",

    "The Chola Empire was an important power in southern India.",
]


for index, answer in enumerate(test_answers, start=1):

    hindi = translate_text(
        text=answer,
        source_language="eng_Latn",
        target_language="hin_Deva"
    )

    print("\n" + "=" * 80)

    print(f"TEST {index}")

    print("\nENGLISH:")
    print(answer)

    print("\nHINDI:")
    print(hindi)