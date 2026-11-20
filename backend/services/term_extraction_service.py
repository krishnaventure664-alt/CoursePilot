import json
import re
import unicodedata

import ollama


# =========================================================
# KNOWN TECHNICAL TERMS
# =========================================================

KNOWN_TECHNICAL_TERMS = [
    "Machine Learning",
    "Deep Learning",
    "Neural Network",
    "Neural Networks",
    "Gradient Descent",
    "Active Recall",
    "RAG",
    "Embeddings",

    "Python",
    "Java",
    "JavaScript",
    "TypeScript",

    "ArrayList",
    "HashMap",

    "SQL",
    "React",
    "Next.js",
    "FastAPI",

    "API",
    "REST API",

    "BERT",
    "GPT",
    "Transformer",
]


# =========================================================
# GENERIC TERMS
# =========================================================

GENERIC_TERMS = {
    "data",
    "model",
    "answer",
    "students",
    "student",
    "information",
    "course",
    "learn",
    "learning",
    "use",
    "system",
    "video",
    "question",
    "example",
    "people",
    "person",
    "thing",
    "things",
    "method",
    "process",
    "way",
    "time",
    "part",
    "topic",
    "concept",
}


# =========================================================
# FIND KNOWN TECHNICAL TERMS
# =========================================================

def find_known_terms(text: str):
    """
    Find known technical terms using deterministic
    case-insensitive matching.
    """

    found_terms = []

    for term in KNOWN_TECHNICAL_TERMS:

        pattern = re.compile(
            r"(?<!\w)"
            + re.escape(term)
            + r"(?!\w)",
            re.IGNORECASE
        )

        if pattern.search(text):
            found_terms.append(term)

    return found_terms


# =========================================================
# LLM CONCEPT EXTRACTION
# =========================================================

def extract_llm_terms(text):
    """
    Ask the LLM to identify important named concepts
    that are explicitly present in the transcript.

    The LLM only proposes concepts.

    Python performs the final validation against
    the transcript.
    """

    schema = {
        "type": "object",
        "properties": {
            "concepts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "canonical": {
                            "type": "string"
                        },
                        "variants": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            }
                        },
                        "evidence": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            }
                        },
                        "variant_evidence": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            }
                        }
                    },
                    "required": [
                        "canonical",
                        "variants",
                        "evidence",
                        "variant_evidence"
                    ]
                }
            }
        },
        "required": [
            "concepts"
        ]
    }

    prompt = f"""
You are a STRICT information extraction system.

Your ONLY source of information is the transcript below.

You must NOT use outside knowledge.

You must NOT infer concepts from what you know about
the subject.

You must NOT add concepts merely because they are
commonly associated with the subject.

========================================================
TRANSCRIPT
========================================================

{text}

========================================================
PRIMARY RULE
========================================================

Extract only important named concepts that are
explicitly mentioned in the transcript.

If a concept is NOT mentioned in the transcript,
DO NOT return it.

For example, if the transcript does not contain
"Indus Valley Civilization", you MUST NOT return
"Indus Valley Civilization".

========================================================
WHAT COUNTS AS A CONCEPT
========================================================

Possible concepts include:

- historical events
- historical periods
- civilizations
- dynasties
- kingdoms
- empires
- religions
- philosophical concepts
- scientific concepts
- theories
- methods
- techniques
- programming languages
- libraries
- frameworks
- technologies
- algorithms
- data structures
- important people
- important places
- important texts
- artifacts
- organizations

Only extract a concept if it is explicitly mentioned
in the transcript.

========================================================
WHAT MUST NOT BE EXTRACTED
========================================================

Do NOT extract ordinary words.

Examples:

"data"
"answer"
"information"
"people"
"method"
"process"
"system"
"example"
"history"

Do NOT extract sentence fragments.

Do NOT extract explanations.

Do NOT extract descriptions.

Do NOT extract concepts that are merely implied.

Do NOT extract concepts from your own knowledge.

========================================================
CANONICAL NAME
========================================================

For every explicitly mentioned concept:

Return the standard English canonical name if it is
clearly recognizable.

Example:

Transcript:
"Machine Learning"

Return:

canonical:
"Machine Learning"

Example:

Transcript:
"एक्टिव रिकॉल"

Return:

canonical:
"Active Recall"

However, do NOT invent an English canonical name
when the transcript does not provide enough information
to identify it confidently.

========================================================
VARIANTS
========================================================

A variant is another explicit name or language form
for THE SAME concept.

Example:

canonical:
"Active Recall"

variant:
"एक्टिव रिकॉल"

Do NOT treat related concepts as variants.

For example:

Buddhism -> Mahayana

is NOT a valid variant relationship.

Gupta Empire -> Golden Age

is NOT a valid variant relationship.

Only return a variant when the transcript explicitly
contains that alternative form.

========================================================
EVIDENCE
========================================================

Every concept MUST have evidence.

Evidence must be an EXACT short phrase copied from
the transcript.

Example:

canonical:
"Machine Learning"

evidence:
["Machine Learning"]

The evidence must actually appear in the transcript.

Do NOT paraphrase.

Do NOT translate the evidence.

Do NOT invent evidence.

========================================================
VARIANT EVIDENCE
========================================================

Every variant MUST have variant_evidence.

The variant evidence must be an EXACT phrase copied
from the transcript that contains that variant.

Example:

canonical:
"Active Recall"

variants:
["एक्टिव रिकॉल"]

evidence:
["Active Recall"]

variant_evidence:
["एक्टिव रिकॉल"]

If there are no variants, return:

"variants": [],
"variant_evidence": []

========================================================
VERY IMPORTANT
========================================================

Before returning a concept, check:

1. Is the concept explicitly mentioned in the transcript?
2. Does the evidence exactly occur in the transcript?
3. Is this a genuine named concept?
4. Am I accidentally using outside knowledge?
5. Am I confusing a related concept with a variant?

If uncertain, DO NOT return the concept.

Be conservative.

Return fewer concepts rather than hallucinating.

Return ONLY JSON matching the provided schema.
"""

    response = ollama.chat(
        model="llama3.2",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        format=schema
    )

    output = response["message"]["content"]

    result = json.loads(output)

    return result.get(
        "concepts",
        []
    )
# =========================================================
# NORMALIZE CONCEPT NAME
# =========================================================

def normalize_concept_name(concept):
    """
    Safely normalize a concept name.

    This does NOT translate the concept.

    It only:
    - removes surrounding whitespace
    - removes surrounding punctuation
    - normalizes repeated whitespace
    """

    if not concept:
        return None

    concept = concept.strip()

    concept = concept.strip(
        ".,!?;:()[]{}\"'"
    )

    concept = re.sub(
        r"\s+",
        " ",
        concept
    )

    if not concept:
        return None

    return concept


# =========================================================
# NORMALIZE TEXT FOR MATCHING
# =========================================================

def normalize_for_matching(text):
    """
    Normalize text for safe transcript evidence matching.

    This does NOT translate or semantically modify text.

    It only normalizes:
    - case
    - Unicode representation
    - punctuation
    - repeated whitespace
    """

    if not text:
        return ""

    text = text.lower()

    text = unicodedata.normalize(
        "NFKC",
        text
    )

    # Replace punctuation with spaces.
    text = re.sub(
        r"[^\w\s]",
        " ",
        text,
        flags=re.UNICODE
    )

    # Collapse repeated whitespace.
    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# =========================================================
# CLEAN CANONICAL CONCEPT
# =========================================================

def clean_concept(
    concept,
    existing_canonicals
):
    """
    Deterministically clean and validate a concept.

    This function does NOT:
    - translate
    - invent concepts
    - make semantic guesses

    It only:
    - normalizes formatting
    - rejects generic terms
    - rejects very long sentence-like concepts
    - merges exact duplicates
    """

    concept = normalize_concept_name(
        concept
    )

    if not concept:
        return None

    normalized = concept.lower()

    # Reject generic concepts.
    if normalized in GENERIC_TERMS:
        return None

    # Reject very long sentence-like concepts.
    if len(concept.split()) > 8:
        return None

    # Merge case-insensitive duplicates.
    for canonical in existing_canonicals:

        canonical_normalized = (
            canonical.lower()
        )

        if normalized == canonical_normalized:
            return canonical

    return concept


# =========================================================
# CLEAN VARIANT
# =========================================================

def clean_variant(
    variant,
    canonical,
    transcript_text
):
    """
    Deterministically validate an LLM-generated variant.

    A variant must:
    - exist in the transcript
    - not be generic
    - not be too long
    - not be the canonical itself
    - not contain unrelated explanation
    """

    variant = normalize_concept_name(
        variant
    )

    if not variant:
        return None

    canonical_normalized = canonical.lower()

    variant_normalized = variant.lower()

    transcript_normalized = (
        normalize_for_matching(
            transcript_text
        )
    )

    # -----------------------------------------
    # Canonical itself is not a useful variant
    # -----------------------------------------

    if (
        variant_normalized
        == canonical_normalized
    ):
        return None

    # -----------------------------------------
    # Variant must occur in transcript
    # -----------------------------------------

    normalized_variant = (
        normalize_for_matching(
            variant
        )
    )

    if (
        not normalized_variant
        or normalized_variant
        not in transcript_normalized
    ):
        return None

    # -----------------------------------------
    # Reject generic words
    # -----------------------------------------

    if variant_normalized in GENERIC_TERMS:
        return None

    # -----------------------------------------
    # Reject sentence-like variants
    # -----------------------------------------

    if len(variant.split()) > 8:
        return None

    # -----------------------------------------
    # Reject canonical + explanation
    # -----------------------------------------

    pattern = (
        r"(?<!\w)"
        + re.escape(canonical_normalized)
        + r"(?!\w)"
    )

    match = re.search(
        pattern,
        variant_normalized
    )

    if match:

        before = (
            variant_normalized[
                :match.start()
            ]
            .strip()
        )

        after = (
            variant_normalized[
                match.end():
            ]
            .strip()
        )

        surrounding_text = (
            before
            + " "
            + after
        ).strip()

        if surrounding_text:
            return None

    return variant


# =========================================================
# MERGE TERMS
# =========================================================

def merge_terms(
    llm_concepts,
    known_terms,
    transcript_text
):
    """
    Merge LLM-discovered concepts with deterministic
    known technical terms.

    The LLM proposes concepts and relationships.

    Python verifies:
    - concept evidence exists in transcript
    - variants exist in transcript
    - variants are not generic
    - variants are not sentence-like
    - duplicates are removed
    """

    merged = []

    canonical_map = {}

    # -----------------------------------------
    # Normalize transcript ONCE
    # -----------------------------------------

    normalized_transcript = (
        normalize_for_matching(
            transcript_text
        )
    )

    # -----------------------------------------
    # Helper: safely add variant
    # -----------------------------------------

    def add_variant(
        concept,
        variant
    ):

        if not variant:
            return

        variant = variant.strip()

        if not variant:
            return

        # Never store canonical as its own variant.
        if (
            variant.lower()
            == concept["canonical"].lower()
        ):
            return

        # Avoid duplicate variants.
        variant_exists = any(
            existing.lower()
            == variant.lower()
            for existing in concept["variants"]
        )

        if not variant_exists:
            concept["variants"].append(
                variant
            )

    # =========================================
    # 1. PROCESS LLM CONCEPTS
    # =========================================

    for concept in llm_concepts:

        # -------------------------------------
        # Safely read fields
        # -------------------------------------

        raw_canonical = concept.get(
            "canonical",
            ""
        )

        raw_variants = concept.get(
            "variants",
            []
        )

        raw_evidence = concept.get(
            "evidence",
            []
        )

        raw_variant_evidence = concept.get(
            "variant_evidence",
            []
        )

        # -------------------------------------
        # Clean canonical
        # -------------------------------------

        canonical = clean_concept(
            raw_canonical,
            canonical_map.keys()
        )

        if not canonical:
            continue

        # -------------------------------------
        # Validate concept evidence
        # -------------------------------------

        valid_evidence = []

        for evidence_text in raw_evidence:

            evidence_text = (
                normalize_concept_name(
                    evidence_text
                )
            )

            if not evidence_text:
                continue

            normalized_evidence = (
                normalize_for_matching(
                    evidence_text
                )
            )

            if (
                normalized_evidence
                and normalized_evidence
                in normalized_transcript
            ):
                valid_evidence.append(
                    evidence_text
                )

        # No grounded evidence = reject concept.
        if not valid_evidence:
            continue

        # -------------------------------------
        # Create or reuse canonical concept
        # -------------------------------------

        normalized_canonical = (
            canonical.lower()
        )

        if (
            normalized_canonical
            not in canonical_map
        ):

            new_concept = {
                "canonical": canonical,
                "variants": []
            }

            canonical_map[
                normalized_canonical
            ] = new_concept

            merged.append(
                new_concept
            )

        else:

            new_concept = canonical_map[
                normalized_canonical
            ]

        # =====================================
        # 2. PROCESS VARIANTS
        # =====================================

        for variant in raw_variants:

            cleaned_variant = clean_variant(
                variant,
                canonical,
                transcript_text
            )

            if not cleaned_variant:
                continue

            # ---------------------------------
            # Validate variant evidence
            # ---------------------------------

            valid_variant_evidence = []

            for evidence_text in (
                raw_variant_evidence
            ):

                evidence_text = (
                    normalize_concept_name(
                        evidence_text
                    )
                )

                if not evidence_text:
                    continue

                normalized_evidence = (
                    normalize_for_matching(
                        evidence_text
                    )
                )

                if (
                    normalized_evidence
                    and normalized_evidence
                    in normalized_transcript
                ):
                    valid_variant_evidence.append(
                        evidence_text
                    )

            # Variant needs grounded evidence.
            if not valid_variant_evidence:
                continue

            # ---------------------------------
            # Variant must occur inside
            # its own evidence
            # ---------------------------------

            normalized_variant = (
                normalize_for_matching(
                    cleaned_variant
                )
            )

            variant_supported = any(
                normalized_variant
                in normalize_for_matching(
                    evidence_text
                )
                for evidence_text
                in valid_variant_evidence
            )

            if not variant_supported:
                continue

            # ---------------------------------
            # Variant passed validation
            # ---------------------------------

            add_variant(
                new_concept,
                cleaned_variant
            )

    # =========================================
    # 3. ADD DETERMINISTIC KNOWN TERMS
    # =========================================

    for term in known_terms:

        canonical = clean_concept(
            term,
            canonical_map.keys()
        )

        if not canonical:
            continue

        normalized_canonical = (
            canonical.lower()
        )

        # Already discovered by LLM.
        if normalized_canonical in canonical_map:
            continue

        new_concept = {
            "canonical": canonical,
            "variants": []
        }

        canonical_map[
            normalized_canonical
        ] = new_concept

        merged.append(
            new_concept
        )

    # =========================================
    # 4. FINAL DEDUPLICATION
    # =========================================

    for concept in merged:

        canonical = concept["canonical"]

        unique_variants = []

        for variant in concept["variants"]:

            if not variant:
                continue

            # Canonical must never be its own variant.
            if (
                variant.lower()
                == canonical.lower()
            ):
                continue

            duplicate = any(
                existing.lower()
                == variant.lower()
                for existing in unique_variants
            )

            if not duplicate:
                unique_variants.append(
                    variant
                )

        concept["variants"] = (
            unique_variants
        )

    return merged


# =========================================================
# COMPLETE COURSE TERM EXTRACTION
# =========================================================

def extract_course_terms(text):
    """
    Extract the complete glossary information
    from course transcript text.
    """

    # -----------------------------------------
    # 1. Discover concepts using LLM
    # -----------------------------------------

    llm_concepts = extract_llm_terms(
        text
    )

    # Temporary debugging output.
    # Keep this for now so we can inspect
    # exactly what the LLM returns.

    print(
        "\n"
        + "=" * 80
    )

    print(
        "RAW LLM CONCEPTS"
    )

    print(
        "=" * 80
    )

    print(
        json.dumps(
            llm_concepts,
            ensure_ascii=False,
            indent=2
        )
    )

    # -----------------------------------------
    # 2. Find known technical terms
    # -----------------------------------------

    known_terms = find_known_terms(
        text
    )

    # -----------------------------------------
    # 3. Merge LLM and deterministic terms
    # -----------------------------------------

    final_concepts = merge_terms(
        llm_concepts,
        known_terms,
        text
    )

    return final_concepts