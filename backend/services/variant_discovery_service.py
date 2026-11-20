import json
import ollama


# =========================================================
# VARIANT DISCOVERY
# =========================================================

def discover_variants(
    concepts,
    transcript_text
):
    """
    Discover alternative language/name forms for already
    accepted concepts.

    IMPORTANT:

    This function does NOT discover new concepts.

    It only looks for variants of concepts that have
    already passed concept classification.

    Every proposed variant must contain exact evidence
    from the transcript.
    """

    if not concepts:
        return []

    # -----------------------------------------------------
    # Prepare accepted concepts
    # -----------------------------------------------------

    concept_names = []

    for concept in concepts:

        canonical = concept.get(
            "canonical",
            ""
        ).strip()

        if not canonical:
            continue

        concept_names.append(
            canonical
        )

    if not concept_names:
        return []

    # -----------------------------------------------------
    # Schema
    # -----------------------------------------------------

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
                                "type": "object",
                                "properties": {
                                    "text": {
                                        "type": "string"
                                    },
                                    "evidence": {
                                        "type": "string"
                                    }
                                },
                                "required": [
                                    "text",
                                    "evidence"
                                ]
                            }
                        }
                    },
                    "required": [
                        "canonical",
                        "variants"
                    ]
                }
            }
        },
        "required": [
            "concepts"
        ]
    }

    # -----------------------------------------------------
    # Accepted concepts
    # -----------------------------------------------------

    concept_text = "\n".join(
        f"- {concept}"
        for concept in concept_names
    )

    # -----------------------------------------------------
    # Prompt
    # -----------------------------------------------------

    prompt = f"""
You are a conservative terminology variant detector.

You have already been given a list of ACCEPTED course
concepts.

Your task is ONLY to find alternative textual forms of
those same concepts that explicitly occur in the
transcript.

You MUST NOT discover new concepts.

========================================================
ACCEPTED CONCEPTS
========================================================

{concept_text}

========================================================
TRANSCRIPT
========================================================

{transcript_text}

========================================================
WHAT IS A VARIANT?
========================================================

A variant is another textual form that refers to the
EXACT SAME concept.

Valid examples:

canonical:
Active Recall

variant:
एक्टिव रिकॉलिंग

if the transcript clearly uses it to refer to Active
Recall.

Another valid pattern:

canonical:
Indus Valley Civilization

variant:
सिंधु सभ्यता

if both occur in the transcript and clearly refer to
the same civilization.

Variants may be:

- Hindi
- Devanagari
- Hinglish
- English spelling variations
- abbreviations
- alternative names
- commonly used alternate names

========================================================
NOT VARIANTS
========================================================

Related concepts are NOT variants.

For example:

Buddhism
→ Mahayana

is NOT automatically a variant.

Gupta Empire
→ Golden Age

is NOT automatically a variant.

Machine Learning
→ Deep Learning

is NOT a variant.

Gradient Descent
→ Optimization

is NOT a variant.

A broader or narrower concept is NOT a variant.

========================================================
EVIDENCE
========================================================

Every variant MUST have exact evidence copied from the
transcript.

The evidence must contain the proposed variant.

Do NOT paraphrase.

Do NOT translate.

Do NOT invent evidence.

If you cannot find exact evidence in the transcript,
DO NOT return the variant.

========================================================
STRICT RULES
========================================================

1. Only return variants of the accepted concepts.

2. Do not create new concepts.

3. Every variant must actually occur in the transcript.

4. Every variant must have exact transcript evidence.

5. A related concept is not a variant.

6. When uncertain, reject the variant.

7. It is completely acceptable for a concept to have
   zero variants.

Return ONLY JSON matching the provided schema.
"""

    # -----------------------------------------------------
    # LLM call
    # -----------------------------------------------------

    response = ollama.chat(
        model="qwen2.5:3b",
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

    # -----------------------------------------------------
    # Python safety gate
    # -----------------------------------------------------

    accepted_map = {
        concept.lower(): concept
        for concept in concept_names
    }

    final_results = []

    for item in result.get(
        "concepts",
        []
    ):

        canonical = item.get(
            "canonical",
            ""
        ).strip()

        original_canonical = accepted_map.get(
            canonical.lower()
        )

        if not original_canonical:
            continue

        valid_variants = []

        for variant in item.get(
            "variants",
            []
        ):

            variant_text = variant.get(
                "text",
                ""
            ).strip()

            evidence = variant.get(
                "evidence",
                ""
            ).strip()

            if not variant_text:
                continue

            if not evidence:
                continue

            # ---------------------------------------------
            # Variant must actually occur in evidence
            # ---------------------------------------------

            if variant_text.lower() not in evidence.lower():
                continue

            # ---------------------------------------------
            # Evidence must actually occur in transcript
            # ---------------------------------------------

            if evidence.lower() not in transcript_text.lower():
                continue

            # ---------------------------------------------
            # Variant cannot simply be the canonical name
            # ---------------------------------------------

            if (
                variant_text.lower()
                == original_canonical.lower()
            ):
                continue

            valid_variants.append(
                {
                    "text": variant_text,
                    "evidence": evidence
                }
            )

        final_results.append(
            {
                "canonical": original_canonical,
                "variants": valid_variants
            }
        )

    return final_results