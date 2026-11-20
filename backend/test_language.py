from services.query_processing_service import detect_language

questions = [
    "What is active recall?",
    "एक्टिव रिकॉल क्या है?",
    "active recall kya hai?",
    "Indus Valley Civilization kya thi?",
    "What is the Indus Valley Civilization?",
    "सिंधु घाटी सभ्यता क्या थी?"

]

for question in questions:
    language = detect_language(question)

    print(
        f"{question} -> {language}"
    )