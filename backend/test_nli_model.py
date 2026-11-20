import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification


MODEL_NAME = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"


print("Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

print("Loading model...")
model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME
)

model.eval()

print("\nModel loaded successfully.")
print("Device:", "cuda" if torch.cuda.is_available() else "cpu")
print("Labels:", model.config.id2label)


def check_nli(premise, hypothesis):
    inputs = tokenizer(
        premise,
        hypothesis,
        truncation=True,
        max_length=512,
        return_tensors="pt"
    )

    with torch.no_grad():
        outputs = model(**inputs)

    probabilities = torch.softmax(
        outputs.logits[0],
        dim=-1
    )

    result = {}

    for index, probability in enumerate(probabilities):
        label = model.config.id2label[index]
        result[label] = float(probability)

    return result


tests = [
    {
        "premise": "Gautam Buddha founded Buddhism.",
        "hypothesis": "Gautam Buddha founded Buddhism."
    },
    {
        "premise": "Bimbisara was a contemporary of Gautam Buddha.",
        "hypothesis": "Bimbisara founded Buddhism."
    },
    {
        "premise": "The evidence discusses Buddhism and Gautam Buddha.",
        "hypothesis": "Buddhism was founded in 500 BC."
    }
]


for i, test in enumerate(tests, start=1):

    print("\n" + "=" * 80)
    print("TEST", i)
    print("=" * 80)

    print("Premise:")
    print(test["premise"])

    print("\nHypothesis:")
    print(test["hypothesis"])

    result = check_nli(
        test["premise"],
        test["hypothesis"]
    )

    print("\nNLI probabilities:")

    for label, probability in result.items():
        print(
            f"{label}: {probability:.4f}"
        )