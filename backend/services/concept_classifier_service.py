import json
import ollama

def is_clean_concept_candidate(candidate: str) -> bool:
    """
    Deterministic quality filter.

    Rejects phrases that look like sentence fragments,
    descriptions, or a concept followed by a generic word.
    """

    candidate = candidate.strip()

    if not candidate:
        return False

    words = candidate.split()

    # A single word is allowed.
    # Examples:
    # RAG
    # Buddhism
    # Python
    if len(words) == 1:
        return True

    # Generic words that commonly turn real concepts
    # into accidental transcript fragments.
    generic_words = {
        "model",
        "models",
        "system",
        "systems",
        "data",
        "information",
        "answer",
        "answers",
        "question",
        "questions",
        "example",
        "examples",
        "method",
        "methods",
        "process",
        "processes",
        "result",
        "results",
        "approach",
        "approaches",
        "problem",
        "problems",
        "concept",
        "concepts",
        "theory",
        "theories",
        "relevant",
        "important",
        "related",
        "based",
        "using",
        "use",
        "used",
        "generate",
        "generated",
        "generation",
        "learn",
        "learning",
        "works",
        "working",
    }

    # If the candidate ends with a generic contextual word,
    # it is probably a transcript fragment.
    if words[-1].lower() in generic_words:
        return False

    # If the candidate starts with a generic contextual word,
    # it is probably a fragment.
    if words[0].lower() in generic_words:
        return False

    return True

def verify_concept_candidate(candidate: str, transcript_text: str):
    """
    Verify ONE candidate at a time.

    The LLM only answers:
        Is this candidate a genuine concept?

    It does NOT rename or normalize the candidate.
    """

    candidate = candidate.strip()

    if not candidate:
        return None
    if not is_clean_concept_candidate(candidate):
        return None

    # --------------------------------------------------
    # Candidate must actually occur in the transcript
    # --------------------------------------------------

    if candidate.lower() not in transcript_text.lower():
        return None

    schema = {
        "type": "object",
        "properties": {
            "is_concept": {
                "type": "boolean"
            }
        },
        "required": [
            "is_concept"
        ]
    }

    prompt = f"""
You are a very conservative academic glossary classifier.

You must classify EXACTLY ONE candidate.

CANDIDATE:
{candidate}

TRANSCRIPT:
{transcript_text}

QUESTION:

Is the CANDIDATE itself a genuine named academic concept
that is worth storing in a course glossary?

Accept things such as:

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
- named methods
- named techniques
- algorithms
- data structures
- programming languages
- libraries
- frameworks
- technologies
- important people
- important places
- important texts
- important artifacts
- organizations
- other clearly identifiable academic concepts

Reject:

- ordinary words
- generic nouns
- generic verbs
- sentence fragments
- incomplete phrases
- descriptions
- explanations
- accidental combinations of words
- grammatical phrases
- contextual fragments
- phrases that merely contain a concept
- phrases created by joining a concept with another generic word

Examples:

data -> false
answer -> false
model -> false
relevant information -> false
answer generate -> false

Gradient Descent -> true
Machine Learning -> true
RAG -> true

IMPORTANT:

"Gradient Descent model" is NOT a concept.
It merely contains the concept "Gradient Descent".

"RAG relevant" is NOT a concept.
It merely contains the concept "RAG".

The candidate must itself be a complete recognizable concept.

Do NOT rename the candidate.

Do NOT suggest another concept.

Do NOT invent a concept.

If uncertain, return false.

Return ONLY JSON matching the schema.
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

    try:
        result = json.loads(output)
    except json.JSONDecodeError:
        return None

    if result.get("is_concept") is not True:
        return None

    # --------------------------------------------------
    # Candidate passed all checks
    # --------------------------------------------------

    return {
        "candidate": candidate
    }


def classify_concept_candidates(candidates, transcript_text):
    """
    Verify every candidate independently.
    """

    accepted = []
    seen = set()

    for candidate in candidates:

        result = verify_concept_candidate(
            candidate=candidate,
            transcript_text=transcript_text
        )

        if result is None:
            continue

        normalized = candidate.lower()

        if normalized in seen:
            continue

        seen.add(normalized)

        accepted.append(result)

    return accepted