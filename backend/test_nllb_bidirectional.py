from transformers import AutoTokenizer, AutoModelForSeq2SeqLM


MODEL_NAME = "facebook/nllb-200-distilled-600M"


print("Loading model...")

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME
)

model = AutoModelForSeq2SeqLM.from_pretrained(
    MODEL_NAME
)

print("Model loaded.")


def translate(
        text: str,
        source_language: str,
        target_language: str
):

    tokenizer.src_lang = source_language

    inputs = tokenizer(
        text,
        return_tensors="pt"
    )

    target_token = tokenizer.convert_tokens_to_ids(
        target_language
    )

    outputs = model.generate(
        **inputs,
        forced_bos_token_id=target_token,
        max_length=128
    )

    return tokenizer.batch_decode(
        outputs,
        skip_special_tokens=True
    )[0]


english_text = (
    "Active recall improves both your retention and your score."
)

hindi_text = (
    "सक्रिय याद दिलाने से आपकी प्रतिधारण और स्कोर दोनों में सुधार होता है।"
)


english_to_hindi = translate(
    english_text,
    "eng_Latn",
    "hin_Deva"
)

hindi_to_english = translate(
    hindi_text,
    "hin_Deva",
    "eng_Latn"
)


print("\n" + "=" * 60)

print("ENGLISH → HINDI")
print(english_to_hindi)

print("\n" + "=" * 60)

print("HINDI → ENGLISH")
print(hindi_to_english)