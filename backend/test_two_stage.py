from services.grounded_answer_service import generate_grounded_answer
from services.language_service import convert_answer_language


question = "What is active recall?"

context = """
एक्टिव रिकॉलिंग कहते हैं जो आपकी रिटेंशन को यानी कि रिटेंशन मतलब
आपकी याद करने की क्षमता और आपके स्कोर दोनों को इंप्रूव करेगा।
"""


print("=" * 70)
print("STAGE 1: GROUNDED ANSWER")
print("=" * 70)

grounded_answer = generate_grounded_answer(
    question=question,
    context=context
)

print(grounded_answer)


print("\n" + "=" * 70)
print("STAGE 2: ENGLISH")
print("=" * 70)

english_answer = convert_answer_language(
    answer=grounded_answer,
    language="english"
)

print(english_answer)


print("\n" + "=" * 70)
print("STAGE 2: HINDI")
print("=" * 70)

hindi_answer = convert_answer_language(
    answer=grounded_answer,
    language="hindi"
)

print(hindi_answer)


print("\n" + "=" * 70)
print("STAGE 2: HINGLISH")
print("=" * 70)

hinglish_answer = convert_answer_language(
    answer=grounded_answer,
    language="hinglish"
)

print(hinglish_answer)