from services.hybrid_search_service import hybrid_search
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch


MODEL_NAME = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"
COURSE_ID = 1


print("Loading NLI model...")

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

    result = {}

    for index, probability in enumerate(probabilities):

        label = model.config.id2label[index]

        result[label] = float(probability)

    return result


TESTS = [
    {
        "query": "Buddhism ke founder kaun the?",
        "claim": "Gautam Buddha founded Buddhism."
    },
    {
        "query": "Buddhism ke founder kaun the?",
        "claim": "Bimbisara founded Buddhism."
    },
    {
        "query": "बौद्ध धर्म के संस्थापक कौन थे?",
        "claim": "गौतम बुद्ध बौद्ध धर्म के संस्थापक थे।"
    },
    {
        "query": "Buddhism ke founder kaun the?",
        "claim": "Buddhism was founded in 500 BC."
    }
]


for test_number, test in enumerate(TESTS, start=1):

    query = test["query"]
    claim = test["claim"]

    print("\n" + "=" * 100)
    print("TEST:", test_number)
    print("QUERY:", query)
    print("CLAIM:", claim)
    print("=" * 100)

    results = hybrid_search(
        query=query,
        course_id=COURSE_ID,
        final_top_k=8
    )

    print("\nTop retrieved evidence:")

    for i, result in enumerate(results[:3], start=1):

        print("\n" + "-" * 80)
        print("Evidence", i)
        print("Rerank score:", result["rerank_score"])
        print("Video:", result["video_id"])
        print("Time:", result["start"], "-", result["end"])
        print("Text:")
        print(result["text"])

    print("\nNLI RESULTS")
    print("-" * 80)

    # Test the claim against every retrieved chunk.
    for i, result in enumerate(results, start=1):

        nli_result = check_nli(
            premise=result["text"],
            hypothesis=claim
        )

        print(
            f"Chunk {i}: "
            f"entailment={nli_result['entailment']:.4f}, "
            f"neutral={nli_result['neutral']:.4f}, "
            f"contradiction={nli_result['contradiction']:.4f}"
        )