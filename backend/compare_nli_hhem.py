import json


NLI_FILE = "claim_verification_evaluation.json"
HHEM_FILE = "hhem_23_results.json"
OUTPUT_FILE = "nli_hhem_comparison.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


print("Loading NLI results...")
nli_data = load_json(NLI_FILE)

print("Loading HHEM results...")
hhem_data = load_json(HHEM_FILE)

print(f"NLI cases  : {len(nli_data)}")
print(f"HHEM cases : {len(hhem_data)}")


# ---------------------------------------------------------
# Index HHEM results by case ID
# ---------------------------------------------------------

hhem_by_id = {
    case["id"]: case
    for case in hhem_data
}


comparison = []


# ---------------------------------------------------------
# Compare case by case
# ---------------------------------------------------------

for nli_case in nli_data:

    case_id = nli_case["id"]

    hhem_case = hhem_by_id.get(case_id)

    if hhem_case is None:
        print(f"WARNING: HHEM result missing for {case_id}")
        continue

    nli_results = nli_case.get("nli_results", [])

    # Strongest NLI signals
    max_entailment = max(
        (float(x.get("entailment", 0.0)) for x in nli_results),
        default=0.0
    )

    max_contradiction = max(
        (float(x.get("contradiction", 0.0)) for x in nli_results),
        default=0.0
    )

    max_neutral = max(
        (float(x.get("neutral", 0.0)) for x in nli_results),
        default=0.0
    )

    # -----------------------------------------------------
    # HHEM result format may contain different field names.
    # Support the common possibilities without assuming one.
    # -----------------------------------------------------

    hhem_results = hhem_case.get("hhem_scores", [])

    hhem_scores = [
        float(result["hhem_score"])
        for result in hhem_results
        if "hhem_score" in result
    ]

    max_hhem = max(hhem_scores, default=0.0)

    for result in hhem_results:

        if isinstance(result, dict):

            score = (
                result.get("score")
                if result.get("score") is not None
                else result.get("hhem_score")
            )

            if score is not None:
                hhem_scores.append(float(score))

        elif isinstance(result, (int, float)):
            hhem_scores.append(float(result))

    max_hhem = max(hhem_scores, default=0.0)

    comparison.append({
        "id": case_id,
        "category": nli_case["category"],
        "language": nli_case["language"],
        "expected": nli_case["expected"],
        "max_entailment": max_entailment,
        "max_contradiction": max_contradiction,
        "max_neutral": max_neutral,
        "max_hhem": max_hhem
    })


# ---------------------------------------------------------
# Save comparison
# ---------------------------------------------------------

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(
        comparison,
        f,
        ensure_ascii=False,
        indent=2
    )


# ---------------------------------------------------------
# Print readable table
# ---------------------------------------------------------

print()
print("=" * 110)
print("NLI vs HHEM COMPARISON")
print("=" * 110)

print(
    f"{'ID':<16}"
    f"{'Expected':<13}"
    f"{'Lang':<10}"
    f"{'Entail':<12}"
    f"{'Contrad':<12}"
    f"{'HHEM':<12}"
)

print("-" * 110)

for row in comparison:

    print(
        f"{row['id']:<16}"
        f"{row['expected']:<13}"
        f"{row['language']:<10}"
        f"{row['max_entailment']:<12.4f}"
        f"{row['max_contradiction']:<12.4f}"
        f"{row['max_hhem']:<12.4f}"
    )

print("=" * 110)

print()
print(f"Comparison cases : {len(comparison)}")
print(f"Output file      : {OUTPUT_FILE}")
print()
print("COMPARISON COMPLETE")