from services.nllb_service import translate_text


text = """
Active Recall is a learning technique that improves retention
and helps improve your score.
"""


result = translate_text(
    text=text,
    source_language="eng_Latn",
    target_language="hin_Deva"
)


print("\n" + "=" * 60)

print("SOURCE:")
print(text)

print("\nHINDI:")
print(result)