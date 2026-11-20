import json
import torch

from transformers import AutoModelForSequenceClassification


# ============================================================
# HHEM
# ============================================================

MODEL_NAME = "vectara/hallucination_evaluation_model"

print("=" * 70)
print("Loading HHEM model...")
print("=" * 70)


model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME,
    trust_remote_code=True
)

model.eval()

print("HHEM loaded successfully.")
print()


# ============================================================
# HHEM SCORE
# ============================================================

def hhem_score(context: str, claim: str) -> float:
    """
    HHEM score:
        0 -> not supported
        1 -> fully supported
    """

    score = model.predict(
        [
            (context, claim)
        ]
    )

    return float(score[0].item())


# ============================================================
# LOAD EVALUATION
# ============================================================

INPUT_FILE = "hhem_input.json"

print("=" * 70)
print("Loading evaluation cases...")
print("=" * 70)


with open(
    INPUT_FILE,
    "r",
    encoding="utf-8"
) as f:

    cases = json.load(f)


print(f"Loaded {len(cases)} evaluation cases.")
print()


# ============================================================
# RUN EVALUATION
# ============================================================

results = []


for case_index, case in enumerate(
    cases,
    start=1
):

    case_id = case["id"]
    category = case["category"]
    language = case["language"]
    query = case["query"]
    claim = case["claim"]

    retrieved_evidence = case.get(
        "retrieved_evidence",
        []
    )


    print("=" * 70)
    print(
        f"CASE {case_index}/{len(cases)}"
    )
    print(
        f"ID       : {case_id}"
    )
    print(
        f"Category : {category}"
    )
    print(
        f"Language : {language}"
    )
    print(
        f"Claim    : {claim}"
    )
    print("=" * 70)


    evidence_scores = []


    # --------------------------------------------------------
    # Score each evidence chunk
    # --------------------------------------------------------

    for rank, evidence in enumerate(
        retrieved_evidence,
        start=1
    ):

        evidence_text = evidence.get(
            "text",
            ""
        )


        if not evidence_text.strip():
            continue


        score = hhem_score(
            context=evidence_text,
            claim=claim
        )


        result = {
            "rank": rank,
            "chunk_id": evidence.get(
                "chunk_id"
            ),
            "video_id": evidence.get(
                "video_id"
            ),
            "text": evidence_text,
            "hhem_score": score
        }


        evidence_scores.append(result)


        print()
        print(
            f"Evidence Rank : {rank}"
        )
        print(
            f"Chunk ID       : "
            f"{evidence.get('chunk_id')}"
        )
        print(
            f"HHEM Score     : "
            f"{score:.6f}"
        )
        print(
            f"Text           : "
            f"{evidence_text[:250]}"
        )


    # --------------------------------------------------------
    # Sort by score
    # --------------------------------------------------------

    evidence_scores.sort(
        key=lambda x: x["hhem_score"],
        reverse=True
    )


    if evidence_scores:

        top_score = evidence_scores[0][
            "hhem_score"
        ]

        top_evidence = evidence_scores[0]

    else:

        top_score = 0.0
        top_evidence = None


    print()
    print("-" * 70)
    print(
        f"TOP HHEM SCORE : "
        f"{top_score:.6f}"
    )


    if top_evidence:

        print(
            f"TOP CHUNK      : "
            f"{top_evidence['chunk_id']}"
        )


    print("-" * 70)


    results.append(
        {
            "id": case_id,
            "category": category,
            "language": language,
            "query": query,
            "claim": claim,
            "expected": case.get(
                "expected"
            ),
            "top_hhem_score": top_score,
            "top_evidence": top_evidence,
            "all_evidence_scores": evidence_scores
        }
    )


# ============================================================
# SAVE
# ============================================================

OUTPUT_FILE = "hhem_results.json"


with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        results,
        f,
        ensure_ascii=False,
        indent=2
    )


# ============================================================
# SUMMARY
# ============================================================

print()
print()
print("=" * 70)
print("HHEM EVALUATION COMPLETE")
print("=" * 70)


for result in results:

    print(
        f"{result['id']:15} "
        f"expected={str(result['expected']):12} "
        f"score={result['top_hhem_score']:.6f}"
    )


print()
print(
    f"Results saved to: "
    f"{OUTPUT_FILE}"
)

print("=" * 70)