from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate


texts = [

    "Active Recall एक सीखने की technique है।",

    "Indus Valley Civilization एक प्राचीन सभ्यता थी।",

    "Retention में सुधार करने के लिए Active Recall उपयोगी है।",

    "Students को information याद रखने में Active Recall मदद करता है।",
]


for text in texts:

    roman = transliterate(
        text,
        sanscript.DEVANAGARI,
        sanscript.ITRANS
    )

    print("\n" + "=" * 70)

    print("INPUT:")
    print(text)

    print("\nROMAN:")
    print(roman)