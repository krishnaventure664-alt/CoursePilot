from transformers import AutoTokenizer, AutoModelForSeq2SeqLM


MODEL_NAME = "facebook/nllb-200-distilled-600M"


print("Loading NLLB translation model...")

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME
)

model = AutoModelForSeq2SeqLM.from_pretrained(
    MODEL_NAME
)

print("NLLB translation model loaded.")


def translate_text(
        text: str,
        source_language: str,
        target_language: str
):
    """
    Translate text using NLLB-200.

    source_language:
        "eng_Latn" → English
        "hin_Deva" → Hindi

    target_language:
        "eng_Latn" → English
        "hin_Deva" → Hindi
    """

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
        max_length=256
    )

    translation = tokenizer.batch_decode(
        outputs,
        skip_special_tokens=True
    )[0]

    return translation