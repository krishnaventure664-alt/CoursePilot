import json
import requests


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:latest"


def verify_claim(
    query: str,
    claim: str,
    evidence_chunks: list
) -> dict:

    if not query or not claim or not evidence_chunks:
        return {
            "verdict": "INSUFFICIENT",
            "confidence": 0.0,
            "reason": "Missing input."
        }

    evidence_text = "\n\n".join(
        f"[Evidence {i + 1}]\n{chunk['text']}"
        for i, chunk in enumerate(evidence_chunks)
    )

    prompt = f"""
You are a strict evidence verification system for a
Retrieval-Augmented Generation system.

Your ONLY job is to determine whether the CLAIM is supported
by the supplied EVIDENCE.

CRITICAL RULES:

1. Use ONLY the supplied evidence.
2. Do NOT use outside knowledge.
3. Do NOT use your own knowledge about history, science,
   geography, or any other subject.
4. Do NOT assume missing facts.
5. A claim is SUPPORTED only when the evidence explicitly
   establishes the claim.
6. A claim is CONTRADICTED only when the evidence explicitly
   conflicts with the claim.
7. If the evidence does not establish the claim, return
   INSUFFICIENT.
8. Never convert missing information into a fact.
9. If a date, number, person, location, or other specific
   detail is not present in the evidence, it cannot be
   considered supported.
10. Return ONLY valid JSON.

USER QUERY:
{query}

CLAIM:
{claim}

EVIDENCE:
{evidence_text}

Return exactly:

{{
  "verdict": "SUPPORTED",
  "confidence": 0.95,
  "reason": "The evidence explicitly supports the claim."
}}

The verdict MUST be exactly one of:

SUPPORTED
CONTRADICTED
INSUFFICIENT
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        },
        timeout=120
    )

    response.raise_for_status()

    result = response.json()

    raw_answer = result.get("response", "").strip()

    try:
        verification = json.loads(raw_answer)
    except json.JSONDecodeError:
        return {
            "verdict": "INSUFFICIENT",
            "confidence": 0.0,
            "reason": "Invalid verifier output."
        }

    verdict = str(
        verification.get("verdict", "INSUFFICIENT")
    ).upper()

    if verdict not in {
        "SUPPORTED",
        "CONTRADICTED",
        "INSUFFICIENT"
    }:
        verdict = "INSUFFICIENT"

    try:
        confidence = float(
            verification.get("confidence", 0.0)
        )
    except (TypeError, ValueError):
        confidence = 0.0

    confidence = max(
        0.0,
        min(confidence, 1.0)
    )

    return {
        "verdict": verdict,
        "confidence": confidence,
        "reason": verification.get(
            "reason",
            ""
        )
    }