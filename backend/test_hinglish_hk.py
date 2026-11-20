from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate


hindi_text = (
    "एक्टिव रिकॉल एक सीखने की तकनीक है जो "
    "प्रतिधारण में सुधार करती है और आपके स्कोर में "
    "सुधार करने में मदद करती है।"
)


hinglish_text = transliterate(
    hindi_text,
    sanscript.DEVANAGARI,
    sanscript.HK
)


print("\n" + "=" * 60)

print("HINDI:")
print(hindi_text)

print("\nROMAN:")
print(hinglish_text)