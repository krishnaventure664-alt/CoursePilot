from services.nllb_service import translate_text
from services.storage_config import LIPI_MODEL_DIR
from services.term_protection_service import (
    protect_terms,
    restore_terms
)
from lipi import Transliterator


# Load LIPI once when the service starts.
lipi_model = Transliterator(
    model_dir=str(LIPI_MODEL_DIR)
)


def translate_to_hindi(
        text: str,
        technical_terms: list[str]
):
    """
    Translate English text into Hindi while
    preserving technical terms.
    """

    # --------------------------------------------------
    # STEP 1
    # Protect technical terms
    # --------------------------------------------------

    protected_text, protected_terms = protect_terms(
        text,
        technical_terms
    )


    # --------------------------------------------------
    # STEP 2
    # Translate protected text using NLLB
    # --------------------------------------------------

    translated_text = translate_text(
        text=protected_text,
        source_language="eng_Latn",
        target_language="hin_Deva"
    )


    # --------------------------------------------------
    # STEP 3
    # Restore original technical terms
    # --------------------------------------------------

    hindi_text = restore_terms(
        translated_text,
        protected_terms
    )


    return hindi_text


def translate_to_hinglish(
        text: str,
        technical_terms: list[str]
):
    """
    Translate English text into Roman Hinglish.
    """

    # First create Hindi.
    hindi_text = translate_to_hindi(
        text,
        technical_terms
    )


    # Convert Hindi script into Roman Hindi.
    hinglish_text = lipi_model.transliterate_text(
        hindi_text
    )


    return hinglish_text

def translate_to_english(
        text: str,
        technical_terms: list[str]
):
    """
    Translate Hindi or Hinglish text into English
    while preserving protected technical terms.
    """

    protected_text, protected_terms = protect_terms(
        text,
        technical_terms
    )

    translated_text = translate_text(
        text=protected_text,
        source_language="hin_Deva",
        target_language="eng_Latn"
    )

    english_text = restore_terms(
        translated_text,
        protected_terms
    )

    return english_text
