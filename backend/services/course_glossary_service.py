import json
import os


GLOSSARY_FILE = "course_glossaries.json"


def load_glossaries():
    """
    Load all stored course glossaries from disk.
    """

    if not os.path.exists(GLOSSARY_FILE):
        return {}

    with open(
        GLOSSARY_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


def save_glossaries(glossaries):
    """
    Save all course glossaries to disk.
    """

    with open(
        GLOSSARY_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            glossaries,
            file,
            ensure_ascii=False,
            indent=2
        )


def save_course_glossary(course_id, concepts):
    """
    Store the glossary for one course.
    """

    glossaries = load_glossaries()

    glossaries[str(course_id)] = concepts

    save_glossaries(glossaries)


def get_course_glossary(course_id):
    """
    Get the glossary belonging to a course.
    """

    glossaries = load_glossaries()

    return glossaries.get(
        str(course_id),
        []
    )