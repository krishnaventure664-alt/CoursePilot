import re


def normalize_roman_hindi(text: str):

    replacements = {

        # -----------------------------------------
        # Common Hindi words
        # -----------------------------------------

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


    # Apply word replacements
    for old, new in replacements.items():
        text = text.replace(old, new)


    # -----------------------------------------
    # Remove academic transliteration marks
    # -----------------------------------------

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


    # -----------------------------------------
    # ITRANS punctuation cleanup
    # -----------------------------------------

    text = text.replace("|", ".")


    # -----------------------------------------
    # Remove accidental double spaces
    # -----------------------------------------

    text = re.sub(
        r"\s+",
        " ",
        text
    )


    return text.strip()


# =================================================
# TEST CASES
# =================================================

test_texts = [

    "Active Recall eka sIkhane kI technique hai|",

    "Indus Valley Civilization eka prAchIna sabhyatA thI|",

    "Retention meM sudhAra karane ke lie Active Recall upayogI hai|",

    "Students ko information yAda rakhane meM Active Recall madada karatA hai|",

]


# =================================================
# RUN TESTS
# =================================================

for index, text in enumerate(test_texts, start=1):

    result = normalize_roman_hindi(text)

    print("\n" + "=" * 70)

    print(f"TEST {index}")

    print("\nINPUT:")
    print(text)

    print("\nNORMALIZED:")
    print(result)