from services.nllb_service import translate_text


test_sentences = [
    "__TERM_0__ improves retention.",

    "__TERM_0__ models learn patterns from data.",

    "__TERM_0__ helps optimize model parameters.",

    "__TERM_0__ retrieves relevant information before generating an answer.",

    "__TERM_0__ represent text as numerical vectors.",

    "__TERM_0__ are used to learn complex patterns.",

    "__TERM_0__ __TERM_1__ is a commonly used data structure.",

    "__TERM_0__ is used to retrieve data from a database.",

    "__TERM_0__ is used to build interactive user interfaces.",

    "__TERM_0__ allows two software systems to communicate."
]


for index, sentence in enumerate(test_sentences, start=1):

    result = translate_text(
        text=sentence,
        source_language="eng_Latn",
        target_language="hin_Deva"
    )

    print("\n" + "=" * 80)

    print(f"TEST {index}")

    print("\nINPUT:")
    print(sentence)

    print("\nNLLB OUTPUT:")
    print(result)