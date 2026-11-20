import json
import math


INPUT_FILE = "claim_verification_evaluation.json"
OUTPUT_FILE = "evidence_aggregation_results.json"


# ---------------------------------------------------------
# Load evaluation data
# ---------------------------------------------------------

print("Loading evaluation data...")

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Cases loaded: {len(data)}")


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

def top_k_mean(values, k=3):
    """
    Mean of the strongest k values.
    Used only as a diagnostic signal.
    """
    if not values:
        return 0.0

    values = sorted(values, reverse=True)

    selected = values[:k]

    return sum(selected) / len(selected)


def softmax(values):
    """
    Convert reranker scores into relative weights.

    This is NOT being used as a probability of correctness.
    It only tells us how much relative attention each retrieved
    chunk receives in this diagnostic experiment.
    """
    if not values:
        return []

    maximum = max(values)

    exponentials = [
        math.exp(value - maximum)
        for value in values
    ]

    total = sum(exponentials)

    if total == 0:
        return [1.0 / len(values)] * len(values)

    return [
        value / total
        for value in exponentials
    ]


def weighted_mean(values, weights):
    """
    Weighted average.
    """
    if not values or not weights:
        return 0.0

    total_weight = sum(weights)

    if total_weight == 0:
        return 0.0

    return sum(
        value * weight
        for value, weight in zip(values, weights)
    ) / total_weight


# ---------------------------------------------------------
# Process every evaluation case
# ---------------------------------------------------------

results = []


for case in data:

    nli_results = case.get("nli_results", [])

    if not nli_results:
        continue


    # -----------------------------------------------------
    # Extract NLI signals
    # -----------------------------------------------------

    entailments = [
        float(result.get("entailment", 0.0))
        for result in nli_results
    ]

    contradictions = [
        float(result.get("contradiction", 0.0))
        for result in nli_results
    ]


    # -----------------------------------------------------
    # Extract BGE reranker scores
    # -----------------------------------------------------

    reranker_scores = [
        float(result.get("rerank_score", 0.0))
        for result in nli_results
    ]


    # -----------------------------------------------------
    # Convert reranker scores into relative weights
    # -----------------------------------------------------

    weights = softmax(reranker_scores)


    # -----------------------------------------------------
    # Aggregation signals
    # -----------------------------------------------------

    max_entailment = max(entailments)

    max_contradiction = max(contradictions)

    top3_entailment_mean = top_k_mean(
        entailments,
        k=3
    )

    top3_contradiction_mean = top_k_mean(
        contradictions,
        k=3
    )

    weighted_entailment = weighted_mean(
        entailments,
        weights
    )

    weighted_contradiction = weighted_mean(
        contradictions,
        weights
    )


    # -----------------------------------------------------
    # Evidence concentration
    # -----------------------------------------------------

    # Sort evidence according to NLI entailment.
    ranked_by_entailment = sorted(
        nli_results,
        key=lambda x: float(
            x.get("entailment", 0.0)
        ),
        reverse=True
    )


    top3_evidence = []

    for result in ranked_by_entailment[:3]:

        top3_evidence.append({
            "chunk_id": result.get("chunk_id"),
            "rerank_score": result.get("rerank_score"),
            "entailment": result.get("entailment"),
            "contradiction": result.get("contradiction")
        })


    # -----------------------------------------------------
    # Store result
    # -----------------------------------------------------

    results.append({

        "id": case["id"],

        "category": case["category"],

        "language": case["language"],

        "expected": case["expected"],

        "claim": case["claim"],

        "evidence_count": len(nli_results),

        "max_entailment": max_entailment,

        "top3_entailment_mean": top3_entailment_mean,

        "weighted_entailment": weighted_entailment,

        "max_contradiction": max_contradiction,

        "top3_contradiction_mean": top3_contradiction_mean,

        "weighted_contradiction": weighted_contradiction,

        "top3_evidence": top3_evidence
    })


# ---------------------------------------------------------
# Save results
# ---------------------------------------------------------

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:

    json.dump(
        results,
        f,
        ensure_ascii=False,
        indent=2
    )


# ---------------------------------------------------------
# Print diagnostic table
# ---------------------------------------------------------

print()
print("=" * 150)
print("CLAIM-LEVEL EVIDENCE AGGREGATION")
print("=" * 150)

print(
    f"{'ID':<16}"
    f"{'Expected':<30}"
    f"{'Lang':<10}"
    f"{'MaxEnt':<10}"
    f"{'Top3Ent':<10}"
    f"{'WtEnt':<10}"
    f"{'MaxCon':<10}"
    f"{'Top3Con':<10}"
    f"{'WtCon':<10}"
)

print("-" * 150)


for result in results:

    print(
        f"{result['id']:<16}"
        f"{result['expected']:<30}"
        f"{result['language']:<10}"
        f"{result['max_entailment']:<10.4f}"
        f"{result['top3_entailment_mean']:<10.4f}"
        f"{result['weighted_entailment']:<10.4f}"
        f"{result['max_contradiction']:<10.4f}"
        f"{result['top3_contradiction_mean']:<10.4f}"
        f"{result['weighted_contradiction']:<10.4f}"
    )


print("=" * 150)

print()
print(f"Cases processed : {len(results)}")
print(f"Output file     : {OUTPUT_FILE}")

print()
print("DIAGNOSTIC EXPERIMENT COMPLETE")