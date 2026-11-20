hindi_text = (
    "एक्टिव रिकॉल एक सीखने की तकनीक है जो "
    "प्रतिधारण में सुधार करती है और आपके स्कोर में "
    "सुधार करने में मदद करती है।"
)


replacements = {
    "एक्टिव रिकॉल": "Active recall",
    "एक": "ek",
    "सीखने": "learning",
    "की": "ki",
    "तकनीक": "technique",
    "है": "hai",
    "जो": "jo",
    "प्रतिधारण": "retention",
    "में": "mein",
    "सुधार": "improve",
    "करती": "karti",
    "करने": "karne",
    "और": "aur",
    "आपके": "aapke",
    "स्कोर": "score",
    "मदद": "help",
}


hinglish_text = hindi_text

for hindi, roman in replacements.items():
    hinglish_text = hinglish_text.replace(
        hindi,
        roman
    )


print("\n" + "=" * 60)

print("HINDI:")
print(hindi_text)

print("\nHINGLISH:")
print(hinglish_text)