# Evaluation dataset for CoursePilot claim verification.
# This file contains controlled claims for testing verifier behavior.
#
# IMPORTANT:
# This is an evaluation dataset only.
# It does NOT change the production retrieval or verification pipeline.

EVALUATION_CASES = [

    # ============================================================
    # 1. DIRECTLY SUPPORTED FACTS
    # ============================================================

    {
        "id": "supported_01",
        "category": "supported",
        "language": "english",
        "query": "What was the Indus Valley Civilization?",
        "claim": "The Indus Valley Civilization was a Bronze Age civilization.",
        "expected": "SUPPORTED",
    },

    {
        "id": "supported_02",
        "category": "supported",
        "language": "english",
        "query": "Buddhism ke founder kaun the?",
        "claim": "Gautam Buddha founded Buddhism.",
        "expected": "SUPPORTED",
    },

    {
        "id": "supported_03",
        "category": "supported",
        "language": "hindi",
        "query": "बौद्ध धर्म के संस्थापक कौन थे?",
        "claim": "गौतम बुद्ध बौद्ध धर्म के संस्थापक थे।",
        "expected": "SUPPORTED",
    },

    {
        "id": "supported_04",
        "category": "supported",
        "language": "hinglish",
        "query": "Buddhism ke founder kaun the?",
        "claim": "Gautam Buddha Buddhism ke founder the.",
        "expected": "SUPPORTED",
    },


    # ============================================================
    # 2. UNSUPPORTED FACTS
    # ============================================================

    {
        "id": "unsupported_01",
        "category": "unsupported",
        "language": "english",
        "query": "Buddhism ke founder kaun the?",
        "claim": "Buddhism was founded in 500 BC.",
        "expected": "INSUFFICIENT",
    },

    {
        "id": "unsupported_02",
        "category": "unsupported",
        "language": "english",
        "query": "What was the Indus Valley Civilization?",
        "claim": "The Indus Valley Civilization developed artificial intelligence.",
        "expected": "INSUFFICIENT",
    },

    {
        "id": "unsupported_03",
        "category": "unsupported",
        "language": "english",
        "query": "What was the Gupta Empire?",
        "claim": "The Gupta Empire invented modern computers.",
        "expected": "INSUFFICIENT",
    },


    # ============================================================
    # 3. CONTRADICTED / WRONG RELATIONSHIP
    # ============================================================

    {
        "id": "contradicted_01",
        "category": "wrong_relationship",
        "language": "english",
        "query": "Buddhism ke founder kaun the?",
        "claim": "Bimbisara founded Buddhism.",
        "expected": "CONTRADICTED_OR_INSUFFICIENT",
    },

    {
        "id": "contradicted_02",
        "category": "wrong_relationship",
        "language": "hindi",
        "query": "बौद्ध धर्म के संस्थापक कौन थे?",
        "claim": "चंद्रगुप्त मौर्य बौद्ध धर्म के संस्थापक थे।",
        "expected": "CONTRADICTED_OR_INSUFFICIENT",
    },


    # ============================================================
    # 4. ENTITY / RELATIONSHIP CONFUSION
    # ============================================================

    {
        "id": "entity_01",
        "category": "entity_relationship",
        "language": "english",
        "query": "Buddhism ke founder kaun the?",
        "claim": "Bimbisara was a founder of Buddhism.",
        "expected": "CONTRADICTED_OR_INSUFFICIENT",
    },

    {
        "id": "entity_02",
        "category": "entity_relationship",
        "language": "english",
        "query": "Buddhism ke founder kaun the?",
        "claim": "Gautam Buddha was the founder of Jainism.",
        "expected": "CONTRADICTED_OR_INSUFFICIENT",
    },


    # ============================================================
    # 5. PARTIALLY TRUE CLAIMS
    # ============================================================

    {
        "id": "partial_01",
        "category": "partially_true",
        "language": "english",
        "query": "What was the Indus Valley Civilization?",
        "claim": "The Indus Valley Civilization was a Bronze Age civilization located only in modern-day India.",
        "expected": "INSUFFICIENT",
    },

    {
        "id": "partial_02",
        "category": "partially_true",
        "language": "english",
        "query": "Buddhism ke founder kaun the?",
        "claim": "Gautam Buddha founded Buddhism and Jainism.",
        "expected": "INSUFFICIENT",
    },


    # ============================================================
    # 6. NEGATION
    # ============================================================

    {
        "id": "negation_01",
        "category": "negation",
        "language": "english",
        "query": "Buddhism ke founder kaun the?",
        "claim": "Gautam Buddha did not found Buddhism.",
        "expected": "CONTRADICTED",
    },

    {
        "id": "negation_02",
        "category": "negation",
        "language": "english",
        "query": "What was the Indus Valley Civilization?",
        "claim": "The Indus Valley Civilization was not a Bronze Age civilization.",
        "expected": "CONTRADICTED",
    },


    # ============================================================
    # 7. DATE / NUMBER CLAIMS
    # ============================================================

    {
        "id": "date_01",
        "category": "date_number",
        "language": "english",
        "query": "Buddhism ke founder kaun the?",
        "claim": "Gautam Buddha founded Buddhism in exactly 500 BC.",
        "expected": "INSUFFICIENT",
    },

    {
        "id": "date_02",
        "category": "date_number",
        "language": "english",
        "query": "What was the Indus Valley Civilization?",
        "claim": "The Indus Valley Civilization existed for exactly 100 years.",
        "expected": "INSUFFICIENT",
    },


    # ============================================================
    # 8. MULTILINGUAL CLAIMS
    # ============================================================

    {
        "id": "multi_01",
        "category": "multilingual",
        "language": "hindi",
        "query": "सिंधु घाटी सभ्यता क्या थी?",
        "claim": "सिंधु घाटी सभ्यता कांस्य युग की सभ्यता थी।",
        "expected": "SUPPORTED",
    },

    {
        "id": "multi_02",
        "category": "multilingual",
        "language": "hinglish",
        "query": "Indus Valley Civilization kya thi?",
        "claim": "Indus Valley Civilization ek Bronze Age civilization thi.",
        "expected": "SUPPORTED",
    },

    {
        "id": "multi_03",
        "category": "multilingual",
        "language": "hindi",
        "query": "बौद्ध धर्म के संस्थापक कौन थे?",
        "claim": "बिंबिसार बौद्ध धर्म के संस्थापक थे।",
        "expected": "CONTRADICTED_OR_INSUFFICIENT",
    },


    # ============================================================
    # 9. IRRELEVANT EVIDENCE / OUT-OF-DOMAIN
    # ============================================================

    {
        "id": "irrelevant_01",
        "category": "irrelevant",
        "language": "english",
        "query": "What was the Indus Valley Civilization?",
        "claim": "Python is a programming language.",
        "expected": "INSUFFICIENT",
    },

    {
        "id": "irrelevant_02",
        "category": "irrelevant",
        "language": "english",
        "query": "Buddhism ke founder kaun the?",
        "claim": "Quantum computers use quantum mechanical phenomena.",
        "expected": "INSUFFICIENT",
    },

    {
        "id": "irrelevant_03",
        "category": "irrelevant",
        "language": "english",
        "query": "What was the Gupta Empire?",
        "claim": "The capital of France is Paris.",
        "expected": "INSUFFICIENT",
    },
]


if __name__ == "__main__":
    print(f"Total evaluation cases: {len(EVALUATION_CASES)}")

    for case in EVALUATION_CASES:
        print(
            f"{case['id']:16} | "
            f"{case['category']:20} | "
            f"{case['language']:10} | "
            f"{case['expected']}"
        )