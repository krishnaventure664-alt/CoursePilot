"""
CoursePilot claim verification evaluation runner.

IMPORTANT:
- Evaluation only.
- Does NOT modify production services.
- Does NOT make a final verification decision.
- Collects retrieval, reranker, and NLI signals for analysis.
"""

import json
from pathlib import Path

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

from evaluation_claims import EVALUATION_CASES
from services.hybrid_search_service import hybrid_search
from services.reranker_service import rerank_results


# ============================================================
# CONFIGURATION
# ============================================================

COURSE_ID = 1

NLI_MODEL_NAME = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"

EVIDENCE_TOP_K = 8

OUTPUT_FILE = Path("claim_verification_evaluation.json")


# ============================================================
# LOAD NLI MODEL
# ============================================================

print("\nLoading NLI model...")

tokenizer = AutoTokenizer.from_pretrained(NLI_MODEL_NAME)

nli_model = AutoModelForSequenceClassification.from_pretrained(
    NLI_MODEL_NAME
)

nli_model.eval()

print("NLI model loaded.")
print("Labels:", nli_model.config.id2label)


# ============================================================
# NLI FUNCTION
# ============================================================

def nli_score(premise: str, hypothesis: str):
    """
    Evaluate whether the evidence supports the claim.

    premise    = retrieved evidence
    hypothesis = claim
    """

    inputs = tokenizer(
        premise,
        hypothesis,
        return_tensors="pt",
        truncation=True,
        max_length=512
    )

    with torch.no_grad():
        outputs = nli_model(**inputs)

    probabilities = torch.softmax(outputs.logits, dim=-1)[0]

    scores = {
        "entailment": float(probabilities[0]),
        "neutral": float(probabilities[1]),
        "contradiction": float(probabilities[2]),
    }

    return scores


# ============================================================
# CLAIM → EVIDENCE RERANKING
# ============================================================

def rerank_claim_against_evidence(claim, evidence):
    """
    Use the existing multilingual reranker to measure
    semantic relevance between the claim and evidence.
    """

    candidates = []

    for item in evidence:

        candidates.append(
            {
                "chunk_id": item["chunk_id"],
                "text": item["text"],
                "video_id": item["video_id"],
                "course_id": item["course_id"],
                "start": item["start"],
                "end": item["end"],
            }
        )

    if not candidates:
        return []

    return rerank_results(
        query=claim,
        search_results=candidates,
        top_k=len(candidates)
    )


# ============================================================
# RUN ONE CASE
# ============================================================

def evaluate_case(case):

    case_id = case["id"]
    query = case["query"]
    claim = case["claim"]

    print("\n" + "=" * 80)
    print(f"CASE: {case_id}")
    print(f"CATEGORY: {case['category']}")
    print(f"LANGUAGE: {case['language']}")
    print(f"QUERY: {query}")
    print(f"CLAIM: {claim}")
    print(f"EXPECTED: {case['expected']}")
    print("=" * 80)

    # --------------------------------------------------------
    # STEP 1 — Hybrid retrieval
    # --------------------------------------------------------

    print("\n[1] Hybrid retrieval...")

    evidence = hybrid_search(
        query=query,
        course_id=COURSE_ID,
        final_top_k=EVIDENCE_TOP_K
    )

    print(f"Retrieved evidence: {len(evidence)} chunks")

    if not evidence:
        print("No evidence retrieved.")

        return {
            "id": case_id,
            "category": case["category"],
            "language": case["language"],
            "query": query,
            "claim": claim,
            "expected": case["expected"],
            "retrieved_evidence": [],
            "claim_reranking": [],
            "nli_results": [],
        }

    # --------------------------------------------------------
    # STEP 2 — Claim → Evidence reranking
    # --------------------------------------------------------

    print("\n[2] Claim → Evidence reranking...")

    reranked = rerank_claim_against_evidence(
        claim=claim,
        evidence=evidence
    )

    claim_reranking = []

    for rank, item in enumerate(reranked, start=1):

        score = float(item["rerank_score"])

        claim_reranking.append(
            {
                "rank": rank,
                "chunk_id": item["chunk_id"],
                "video_id": item["video_id"],
                "start": item["start"],
                "end": item["end"],
                "rerank_score": score,
                "text": item["text"],
            }
        )

        print(
            f"\nRank {rank}"
            f"\nScore: {score:.6f}"
            f"\nChunk: {item['chunk_id']}"
            f"\nEvidence: {item['text'][:300]}"
        )

    # --------------------------------------------------------
    # STEP 3 — NLI on every retrieved evidence chunk
    # --------------------------------------------------------

    print("\n[3] NLI evaluation...")

    nli_results = []

    for rank, item in enumerate(reranked, start=1):

        scores = nli_score(
            premise=item["text"],
            hypothesis=claim
        )

        nli_result = {
            "rank": rank,
            "chunk_id": item["chunk_id"],
            "video_id": item["video_id"],
            "start": item["start"],
            "end": item["end"],
            "rerank_score": float(item["rerank_score"]),
            "entailment": scores["entailment"],
            "neutral": scores["neutral"],
            "contradiction": scores["contradiction"],
            "text": item["text"],
        }

        nli_results.append(nli_result)

        print(
            f"\nRank {rank}"
            f"\nReranker: {item['rerank_score']:.6f}"
            f"\nEntailment: {scores['entailment']:.6f}"
            f"\nNeutral: {scores['neutral']:.6f}"
            f"\nContradiction: {scores['contradiction']:.6f}"
        )

    # --------------------------------------------------------
    # IMPORTANT:
    # We intentionally DO NOT classify the claim here.
    # --------------------------------------------------------

    return {
        "id": case_id,
        "category": case["category"],
        "language": case["language"],
        "query": query,
        "claim": claim,
        "expected": case["expected"],
        "retrieved_evidence": evidence,
        "claim_reranking": claim_reranking,
        "nli_results": nli_results,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n")
    print("#" * 80)
    print("COURSEPILOT CLAIM VERIFICATION EVALUATION")
    print("#" * 80)

    print(f"\nTotal cases: {len(EVALUATION_CASES)}")
    print(f"Course ID: {COURSE_ID}")
    print(f"Evidence top-k: {EVIDENCE_TOP_K}")

    all_results = []

    for index, case in enumerate(EVALUATION_CASES, start=1):

        print(
            f"\n\nRunning case "
            f"{index}/{len(EVALUATION_CASES)}..."
        )

        result = evaluate_case(case)

        all_results.append(result)

    # --------------------------------------------------------
    # SAVE RESULTS
    # --------------------------------------------------------

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            all_results,
            file,
            ensure_ascii=False,
            indent=2
        )

    print("\n")
    print("#" * 80)
    print("EVALUATION COMPLETE")
    print("#" * 80)

    print(f"\nResults saved to:")
    print(OUTPUT_FILE.resolve())

    print(
        "\nIMPORTANT:"
        "\nNo automatic verifier decision was made."
        "\nWe will analyze the signals before designing the verifier."
    )


if __name__ == "__main__":
    main()