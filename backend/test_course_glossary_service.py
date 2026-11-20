from services.course_glossary_service import (
    save_course_glossary,
    get_course_glossary
)


test_glossary = [
    {
        "canonical": "Active Recall",
        "variants": [
            "Active Recall",
            "एक्टिव रिकॉलिंग"
        ]
    },
    {
        "canonical": "Machine Learning",
        "variants": [
            "Machine Learning"
        ]
    }
]


save_course_glossary(
    course_id=1,
    concepts=test_glossary
)


glossary = get_course_glossary(
    course_id=1
)


print("\n" + "=" * 80)
print("COURSE GLOSSARY TEST")
print("=" * 80)

print(glossary)