
ATOMIC_TEST_CASES = [
    {
        "id": "multi_01",
        "original_claim": "सिंधु घाटी सभ्यता कांस्य युग की सभ्यता थी।",
        "atomic_claims": [
            "सिंधु घाटी सभ्यता कांस्य युग की सभ्यता थी।",
        ],
        "expected": ["SUPPORTED"],
    },
    {
        "id": "multi_02",
        "original_claim": "Indus Valley Civilization ek Bronze Age civilization thi.",
        "atomic_claims": [
            "Indus Valley Civilization ek Bronze Age civilization thi.",
        ],
        "expected": ["SUPPORTED"],
    },
    {
        "id": "multi_03",
        "original_claim": "बिंबिसार बौद्ध धर्म के संस्थापक थे।",
        "atomic_claims": [
            "बिंबिसार बौद्ध धर्म के संस्थापक थे।",
        ],
        "expected": ["CONTRADICTED_OR_INSUFFICIENT"],
    },
    {
        "id": "partial_01",
        "original_claim": (
            "The Indus Valley Civilization was a Bronze Age civilization "
            "located only in modern-day India."
        ),
        "atomic_claims": [
            "The Indus Valley Civilization was a Bronze Age civilization.",
            "The Indus Valley Civilization was located only in modern-day India.",
        ],
        "expected": ["SUPPORTED", "INSUFFICIENT"],
    },
    {
        "id": "partial_02",
        "original_claim": "Gautam Buddha founded Buddhism and Jainism.",
        "atomic_claims": [
            "Gautam Buddha founded Buddhism.",
            "Gautam Buddha founded Jainism.",
        ],
        "expected": ["SUPPORTED", "CONTRADICTED_OR_INSUFFICIENT"],
    },
    {
        "id": "negation_01",
        "original_claim": "Gautam Buddha did not found Buddhism.",
        "atomic_claims": [
            "Gautam Buddha did not found Buddhism.",
        ],
        "expected": ["CONTRADICTED"],
    },
    {
        "id": "negation_02",
        "original_claim": (
            "The Indus Valley Civilization was not a Bronze Age civilization."
        ),
        "atomic_claims": [
            "The Indus Valley Civilization was not a Bronze Age civilization.",
        ],
        "expected": ["CONTRADICTED"],
    },
]


if __name__ == "__main__":
    for case in ATOMIC_TEST_CASES:
        print(f"\n{case['id']}: {case['original_claim']}")
        for i, claim in enumerate(case["atomic_claims"]):
            print(f"  Atomic claim {i + 1}: {claim}")
            print(f"  Expected: {case['expected'][i]}")

    print(f"\nTotal cases: {len(ATOMIC_TEST_CASES)}")
