from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

MODEL_NAME = "ai4bharat/indictrans2-en-indic-1B"

print("Loading model...")

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME,
    trust_remote_code=True
)

model = AutoModelForSeq2SeqLM.from_pretrained(
    MODEL_NAME,
    trust_remote_code=True
)

print("Model loaded.")

text = "Active recall improves both your retention and your score."

src_lang = "eng_Latn"
tgt_lang = "hin_Deva"

inputs = tokenizer(
    text,
    src_lang=src_lang,
    return_tensors="pt"
)

outputs = model.generate(
    **inputs,
    max_length=128
)

translation = tokenizer.batch_decode(
    outputs,
    skip_special_tokens=True
)[0]

print("\nEnglish:")
print(text)

print("\nHindi:")
print(translation)