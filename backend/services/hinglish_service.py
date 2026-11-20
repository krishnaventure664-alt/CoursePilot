import re

from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

from services.nllb_service import translate_text


def normalize_roman_hindi(text: str):
    """
    Convert academic transliteration output into
    readable Roman Hindi.
    """

    replacements = {

        # Common Hindi words
        "eka": "ek",
        "kI": "ki",
        "meM": "mein",
        "aura": "aur",
        "Apa": "aap",
        "Apake": "aapke",
        "yAda": "yaad",
        "madada": "madad",

        # Verb forms
        "karatA": "karta",
        "karatI": "karti",
        "karane": "karne",
        "rakhane": "rakhne",
        "lie": "liye",

        # Learning-related words
        "sIkhane": "seekhne",
        "sudhAra": "sudhaar",
        "pratidhAraNa": "retention",
        "upayogI": "useful",

        # Common Hindi words
        "prAchIna": "prachin",
        "sabhyatA": "sabhyata",
        "thI": "thi",
        "thA": "tha",
        "thE": "the",

        # Common transliteration patterns
        "chA": "cha",
        "chI": "chi",
        "chU": "chu",
        "chE": "che",

        "jA": "ja",
        "jI": "ji",
        "jU": "ju",
        "jE": "je",
    }


    for old, new in replacements.items():
        text = text.replace(old, new)


    # Remove academic transliteration marks
    text = text.replace("ā", "a")
    text = text.replace("ī", "i")
    text = text.replace("ū", "u")

    text = text.replace("ṃ", "n")
    text = text.replace("ṁ", "n")

    text = text.replace("ṭ", "t")
    text = text.replace("ḍ", "d")
    text = text.replace("ṇ", "n")

    text = text.replace("ś", "sh")
    text = text.replace("ṣ", "sh")

    text = text.replace("ṛ", "r")


    # Convert ITRANS punctuation
    text = text.replace("|", ".")


    # Remove repeated spaces
    text = re.sub(
        r"\s+",
        " ",
        text
    )


    return text.strip()


def convert_to_hinglish(answer: str):
    """
    Convert a grounded English answer into
    Roman Hinglish.

    Pipeline:

    English
       ↓
    NLLB English → Hindi
       ↓
    Hindi → Roman Hindi
       ↓
    Normalization
    """

    hindi_text = translate_text(
        text=answer,
        source_language="eng_Latn",
        target_language="hin_Deva"
    )


    roman_text = transliterate(
        hindi_text,
        sanscript.DEVANAGARI,
        sanscript.ITRANS
    )


    hinglish_text = normalize_roman_hindi(
        roman_text
    )


    return hinglish_text