import json
from pathlib import Path

import torch
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
)

from test_atomic_claim_decomposition import ATOMIC_TEST_CASES


INPUT_FILE = Path("claim_verification_evaluation.json")
OUTPUT_FILE = Path("atomic_claim_evaluation_results.json")

MODEL_NAME = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"


def load_evaluation_data():
    with INPUT_FILE.open("r", encoding="utf-8") as file:
        cases = json.load(file)

    return {case["id"]: case for case in cases}


def load_nli_model():
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME
    )
    model.eval()

    return tokenizer, model


def score_claim_against_evidence(
    claim,
    evidence_texts,
    tokenizer,
    model,
):
    results = []

    for evidence in evidence_texts:
        inputs = tokenizer(
            evidence,
            claim,
            return_tensors="pt",
            truncation=True,
            max_length=512,
        )

        with torch.no_grad():
            logits = model(**inputs).logits
            scores = torch.softmax(logits, dim=-1)[0].tolist()

        # Verified model label mapping:
        # 0 = entailment
        # 1 = neutral
        # 2 = contradiction

        results.append(
            {
                "evidence": evidence,
                "entailment": scores[0],
                "neutral": scores[1],
                "contradiction": scores[2],
            }
        )

    return results


def get_evidence_texts(original_case):
    evidence_items = original_case.get("nli_results", [])

    return [
        item["text"]
        for item in evidence_items
        if item.get("text")
    ]


def get_summary(scores):
    return {
        "best_entailment": max(
            (item["entailment"] for item in scores),
            default=0.0,
        ),
        "best_neutral": max(
            (item["neutral"] for item in scores),
            default=0.0,
        ),
        "best_contradiction": max(
            (item["contradiction"] for item in scores),
            default=0.0,
        ),
    }


def main():
    evaluation_data = load_evaluation_data()

    print("Loading multilingual NLI model...")
    tokenizer, model = load_nli_model()

    output = []
    mapping_errors = 0
    skipped_cases = 0

    for test_case in ATOMIC_TEST_CASES:
        case_id = test_case["id"]
        original_claim = test_case["original_claim"]

        original_case = evaluation_data.get(case_id)

        # 1. Check whether the evaluation record exists.
        if original_case is None:
            print(
                f"\nERROR: No evaluation record found for {case_id}"
            )
            skipped_cases += 1
            continue

        # 2. Validate the case ID against its original claim.
        evaluation_claim = original_case.get("claim", "")

        if evaluation_claim.strip() != original_claim.strip():
            print(f"\nMAPPING ERROR: {case_id}")
            print("Expected original:", repr(original_claim))
            print("Evaluation original:", repr(evaluation_claim))
            print(
                "Skipping this case to prevent invalid comparisons."
            )
            mapping_errors += 1
            skipped_cases += 1
            continue

        # All claims for this case use the same evidence set.
        evidence_texts = get_evidence_texts(original_case)

        if not evidence_texts:
            print(f"\nWARNING: No evidence found for {case_id}")
            skipped_cases += 1
            continue

        print("\n" + "=" * 70)
        print(f"Case: {case_id}")
        print(f"Original claim: {original_claim}")
        print(f"Evidence chunks: {len(evidence_texts)}")

        # Score the original claim as the baseline.
        original_scores = score_claim_against_evidence(
            original_claim,
            evidence_texts,
            tokenizer,
            model,
        )

        original_summary = get_summary(original_scores)

        print("\nOriginal claim baseline:")
        print(
            "  Maximum entailment: "
            f"{original_summary['best_entailment']:.4f}"
        )
        print(
            "  Maximum neutral: "
            f"{original_summary['best_neutral']:.4f}"
        )
        print(
            "  Maximum contradiction: "
            f"{original_summary['best_contradiction']:.4f}"
        )

        case_output = {
            "id": case_id,
            "original_claim": original_claim,
            "original_expected": original_case.get("expected"),
            "evidence_count": len(evidence_texts),
            "original_claim_baseline": {
                **original_summary,
                "evidence_scores": original_scores,
            },
            "atomic_results": [],
        }

        # Score every atomic claim against the same evidence.
        for index, atomic_claim in enumerate(
            test_case["atomic_claims"]
        ):
            expected = test_case["expected"][index]

            scores = score_claim_against_evidence(
                atomic_claim,
                evidence_texts,
                tokenizer,
                model,
            )

            summary = get_summary(scores)

            result = {
                "claim": atomic_claim,
                "expected": expected,
                **summary,
                "evidence_scores": scores,
            }

            case_output["atomic_results"].append(result)

            print(f"\nAtomic claim: {atomic_claim}")
            print(f"Expected label: {expected}")
            print(
                "  Maximum entailment: "
                f"{summary['best_entailment']:.4f}"
            )
            print(
                "  Maximum neutral: "
                f"{summary['best_neutral']:.4f}"
            )
            print(
                "  Maximum contradiction: "
                f"{summary['best_contradiction']:.4f}"
            )

        output.append(case_output)

    OUTPUT_FILE.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n" + "=" * 70)
    print("Evaluation finished.")
    print(f"Cases saved: {len(output)}")
    print(f"Mapping errors: {mapping_errors}")
    print(f"Skipped cases: {skipped_cases}")
    print(f"Results saved to: {OUTPUT_FILE.resolve()}")
    print(
        "\nImportant: These are diagnostic model scores, "
        "not calibrated probabilities or final truth labels."
    )


if __name__ == "__main__":
    main()