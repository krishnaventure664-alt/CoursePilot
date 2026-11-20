from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch


MODEL_NAME = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"


tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME
)

model.eval()


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

    return {
        model.config.id2label[i]: float(probabilities[i])
        for i in range(len(probabilities))
    }


tests = [

    {
        "name": "Hindi evidence → English claim",

        "premise": """
जिन्होंने इसकी एक तरीके से नीव रखी उनको सभी लोग जानते हैं
गौतम बुद्ध उनका नाम है
""",

        "hypothesis": "Gautam Buddha founded Buddhism."
    },

    {
        "name": "Hindi evidence → Hindi claim",

        "premise": """
जिन्होंने इसकी एक तरीके से नीव रखी उनको सभी लोग जानते हैं
गौतम बुद्ध उनका नाम है
""",

        "hypothesis": "गौतम बुद्ध बौद्ध धर्म के संस्थापक थे।"
    },

    {
        "name": "Hindi evidence → English weaker claim",

        "premise": """
जिन्होंने इसकी एक तरीके से नीव रखी उनको सभी लोग जानते हैं
गौतम बुद्ध उनका नाम है
""",

        "hypothesis": "Gautam Buddha was associated with Buddhism."
    },

    {
        "name": "Hindi evidence → unsupported date",

        "premise": """
जिन्होंने इसकी एक तरीके से नीव रखी उनको सभी लोग जानते हैं
गौतम बुद्ध उनका नाम है
""",

        "hypothesis": "Buddhism was founded in 500 BC."
    }
]


for test in tests:

    print("\n" + "=" * 100)
    print(test["name"])
    print("=" * 100)

    print("\nPremise:")
    print(test["premise"].strip())

    print("\nHypothesis:")
    print(test["hypothesis"])

    result = check_nli(
        test["premise"],
        test["hypothesis"]
    )

    print("\nResult:")

    for label, probability in result.items():

        print(
            f"{label}: {probability:.4f}"
        )