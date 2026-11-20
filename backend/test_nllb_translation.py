from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

MODEL_NAME = "facebook/nllb-200-distilled-600M"

print("Loading tokenizer...")

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME,
    src_lang="eng_Latn"
)

print("Loading model...")

model = AutoModelForSeq2SeqLM.from_pretrained(
    MODEL_NAME
)

print("Model loaded.")

text = "Active recall improves both your retention and your score."

inputs = tokenizer(
    text,
    return_tensors="pt"
)

target_language = "hin_Deva"

forced_bos_token_id = tokenizer.convert_tokens_to_ids(
    target_language
)

outputs = model.generate(
    **inputs,
    forced_bos_token_id=forced_bos_token_id,
    max_length=128
)

translation = tokenizer.batch_decode(
    outputs,
    skip_special_tokens=True
)[0]

print("\n" + "=" * 60)
print("SOURCE:")
print(text)

print("\nHINDI:")
print(translation)