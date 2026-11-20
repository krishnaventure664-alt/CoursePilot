import re


def normalize_query(query: str) -> str:
    """
    Normalize a user query for retrieval.

    This function does not change the original user question.
    It only creates a cleaner version for semantic search.
    """

    # Remove extra spaces
    query = " ".join(query.split())

    # Convert English/Romanized text to lowercase
    query = query.lower()

    # Remove unnecessary punctuation
    query = re.sub(r"[?!.,]+", " ", query)

    # Remove extra spaces created after punctuation removal
    query = " ".join(query.split())

    return query


def detect_language(query: str) -> str:
    """
    Detect the language/style of the user's question.

    Returns:
        "english"
        "hindi"
        "hinglish"
    """

    # Remove spaces and punctuation so we can inspect the characters
    cleaned_query = re.sub(
        r"[\s?!.,]+",
        "",
        query
    )

    if not cleaned_query:
        return "english"

    # Count Devanagari characters
    hindi_characters = re.findall(
        r"[\u0900-\u097F]",
        cleaned_query
    )

    hindi_ratio = (
        len(hindi_characters)
        / len(cleaned_query)
    )

    # Mostly Devanagari → Hindi
    if hindi_ratio >= 0.50:
        return "hindi"

    # Mostly Latin characters → English or Hinglish
    #
    # Common Hindi/Romanized-Hindi words.
    hinglish_words = {
        "kya",
        "hai",
        "hain",
        "tha",
        "thi",
        "ka",
        "ki",
        "ke",
        "ko",
        "se",
        "mein",
        "aur",
        "ye",
        "yeh",
        "woh",
        "kyu",
        "kyon",
        "kaise",
        "kaisa",
        "hota",
        "hoti",
        "hote",
        "karo",
        "karna",
        "kar",
        "samjho",
        "samajh",
        "batao",
        "bata",
    }

    words = set(
        re.findall(
            r"[a-zA-Z]+",
            query.lower()
        )
    )

    if words.intersection(hinglish_words):
        return "hinglish"

    return "english"