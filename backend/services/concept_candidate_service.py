import re


# =========================================================
# STOPWORDS
# =========================================================

STOPWORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "but",
    "if",
    "then",
    "than",
    "that",
    "this",
    "these",
    "those",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "to",
    "of",
    "in",
    "on",
    "at",
    "for",
    "from",
    "with",
    "by",
    "as",
    "into",
    "about",
    "through",
    "during",
    "after",
    "before",
    "between",
    "over",
    "under",
    "when",
    "where",
    "why",
    "how",
    "what",
    "which",
    "who",
    "whom",
    "can",
    "could",
    "should",
    "would",
    "will",
    "shall",
    "may",
    "might",
    "must",
    "do",
    "does",
    "did",
    "have",
    "has",
    "had",
    "having",
    "not",
    "no",
    "yes",
    "you",
    "your",
    "we",
    "our",
    "they",
    "their",
    "he",
    "she",
    "it",
    "its",
    "i",
    "me",
    "my",
}


# =========================================================
# NORMALIZATION
# =========================================================

def normalize_text(text: str) -> str:
    """
    Normalize whitespace only.

    We deliberately do not alter the actual words.
    """

    if not text:
        return ""

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


# =========================================================
# ACRONYM EXTRACTION
# =========================================================

def extract_acronym_candidates(text: str):
    """
    Extract acronym-like terms.

    Examples:

    RAG
    API
    SQL
    GPT
    NLP
    """

    if not text:
        return []

    matches = re.findall(
        r"(?<!\w)[A-Z][A-Z0-9]{1,8}(?!\w)",
        text
    )

    candidates = []

    seen = set()

    for match in matches:

        normalized = match.lower()

        if normalized in seen:
            continue

        seen.add(normalized)

        candidates.append(match)

    return candidates


# =========================================================
# CAPITALIZED ENGLISH PHRASES
# =========================================================

def extract_capitalized_phrases(text: str):
    """
    Extract explicitly capitalized English phrases.

    Examples:

    Machine Learning
    Gradient Descent
    Active Recall
    Indus Valley Civilization

    This is only candidate discovery.

    It does NOT decide whether something is actually
    a glossary concept.
    """

    if not text:
        return []

    pattern = re.compile(
        r"(?<![A-Za-z])"
        r"[A-Z][A-Za-z0-9-]*"
        r"(?:\s+[A-Z][A-Za-z0-9-]*){0,5}"
        r"(?![A-Za-z])"
    )

    matches = pattern.findall(text)

    candidates = []

    seen = set()

    for match in matches:

        match = match.strip()

        if not match:
            continue

        normalized = match.lower()

        if normalized in seen:
            continue

        seen.add(normalized)

        candidates.append(match)

    return candidates


# =========================================================
# LOWERCASE ENGLISH PHRASE CANDIDATES
# =========================================================

def extract_english_phrase_candidates(
    text: str,
    max_words: int = 3
):
    """
    Extract short English-only phrases.

    IMPORTANT:

    We intentionally restrict this to ASCII English
    words.

    This prevents Hindi/Devanagari text from being
    broken into meaningless character fragments.

    These phrases are only candidates.

    The LLM will decide whether they are actual concepts.
    """

    if not text:
        return []

    # Extract only contiguous English word sequences.
    english_sequences = re.findall(
        r"[A-Za-z]+(?:\s+[A-Za-z]+)*",
        text
    )

    candidates = []

    seen = set()

    for sequence in english_sequences:

        words = sequence.split()

        if len(words) < 2:
            continue

        for size in range(
            2,
            min(max_words, len(words)) + 1
        ):

            for start in range(
                len(words) - size + 1
            ):

                phrase_words = words[
                    start:start + size
                ]

                first_word = (
                    phrase_words[0].lower()
                )

                last_word = (
                    phrase_words[-1].lower()
                )

                # Don't begin/end with common stopwords.
                if first_word in STOPWORDS:
                    continue

                if last_word in STOPWORDS:
                    continue

                # Avoid phrases consisting entirely
                # of stopwords.
                if all(
                    word.lower() in STOPWORDS
                    for word in phrase_words
                ):
                    continue

                phrase = " ".join(
                    phrase_words
                )

                normalized = phrase.lower()

                if normalized in seen:
                    continue

                seen.add(normalized)

                candidates.append(
                    phrase
                )

    return candidates


# =========================================================
# MERGE CANDIDATES
# =========================================================

def merge_candidates(*candidate_lists):
    """
    Merge candidates while preserving the first
    observed spelling.
    """

    merged = []

    seen = set()

    for candidate_list in candidate_lists:

        for candidate in candidate_list:

            if not candidate:
                continue

            candidate = candidate.strip()

            if not candidate:
                continue

            normalized = candidate.lower()

            if normalized in seen:
                continue

            seen.add(normalized)

            merged.append(candidate)

    return merged


# =========================================================
# MAIN CANDIDATE GENERATOR
# =========================================================

def extract_concept_candidates(text: str):
    """
    Generate possible glossary candidates.

    This function DOES NOT decide whether candidates
    are valid concepts.

    Responsibilities:

    1. Find explicit acronyms.
    2. Find explicitly capitalized English phrases.
    3. Find short English phrase candidates.

    The next LLM stage will classify them.

    The transcript remains the ultimate source of truth.
    """

    text = normalize_text(text)

    if not text:
        return []

    acronym_candidates = (
        extract_acronym_candidates(text)
    )

    capitalized_candidates = (
        extract_capitalized_phrases(text)
    )

    english_phrase_candidates = (
        extract_english_phrase_candidates(text)
    )

    return merge_candidates(
        acronym_candidates,
        capitalized_candidates,
        english_phrase_candidates
    )