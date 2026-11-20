import json


INPUT_FILE = "claim_verification_evaluation.json"
OUTPUT_FILE = "hhem_input.json"


print("Loading evaluation file...")

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)


print(f"Loaded {len(data)} evaluation cases.")


hhem_cases = []

for case in data:

    hhem_cases.append({
        "id": case["id"],
        "category": case["category"],
        "language": case["language"],
        "query": case["query"],
        "claim": case["claim"],
        "expected": case["expected"],
        "retrieved_evidence": case["retrieved_evidence"]
    })


with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        hhem_cases,
        f,
        ensure_ascii=False,
        indent=2
    )


print()
print("=" * 60)
print("HHEM INPUT PREPARATION COMPLETE")
print("=" * 60)
print(f"Cases written : {len(hhem_cases)}")
print(f"Output file   : {OUTPUT_FILE}")
print("=" * 60)