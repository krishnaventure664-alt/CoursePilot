import json
import torch
from transformers import AutoModelForSequenceClassification


MODEL_NAME = "vectara/hallucination_evaluation_model"
INPUT_FILE = "hhem_input.json"
OUTPUT_FILE = "hhem_23_results.json"


print("=" * 80)
print("COURSEPILOT HHEM 23-CASE EVALUATION")
print("=" * 80)

print("\nLoading evaluation data...")

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    cases = json.load(f)

print(f"Loaded {len(cases)} cases.")


print("\nLoading HHEM...")

model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME,
    trust_remote_code=True
)

model.eval()

print("HHEM loaded successfully.")


results = []

for case_index, case in enumerate(cases, start=1):

    print("\n" + "=" * 80)
    print(f"CASE {case_index}/{len(cases)}")
    print("=" * 80)

    print("ID       :", case["id"])
    print("Category :", case["category"])
    print("Language :", case["language"])
    print("Query    :", case["query"])
    print("Claim    :", case["claim"])
    print("Expected :", case["expected"])

    case_result = {
        "id": case["id"],
        "category": case["category"],
        "language": case["language"],
        "query": case["query"],
        "claim": case["claim"],
        "expected": case["expected"],
        "hhem_scores": []
    }

    for evidence_index, evidence in enumerate(
        case["retrieved_evidence"],
        start=1
    ):

        premise = evidence["text"]
        hypothesis = case["claim"]

        score_tensor = model.predict([
            (premise, hypothesis)
        ])

        score = float(score_tensor[0])

        result = {
            "rank": evidence["rank"],
            "chunk_id": evidence["chunk_id"],
            "video_id": evidence["video_id"],
            "start": evidence["start"],
            "end": evidence["end"],
            "rerank_score": evidence["rerank_score"],
            "hhem_score": score,
            "text": premise
        }

        case_result["hhem_scores"].append(result)

        print(
            f"Evidence {evidence_index}/"
            f"{len(case['retrieved_evidence'])} | "
            f"Retriever rank: {evidence['rank']} | "
            f"HHEM: {score:.6f}"
        )

    results.append(case_result)


print("\nSaving results...")

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(
        results,
        f,
        ensure_ascii=False,
        indent=2
    )


print("\n" + "=" * 80)
print("HHEM EVALUATION COMPLETE")
print("=" * 80)
print(f"Cases processed : {len(results)}")
print(f"Output file     : {OUTPUT_FILE}")
print("=" * 80)