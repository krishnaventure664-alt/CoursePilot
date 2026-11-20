import ollama


def convert_to_hinglish(hindi_text: str):

    prompt = f"""
Convert the following Hindi text into natural Roman Hinglish.

HINDI TEXT:
{hindi_text}

STRICT RULES:

1. Do NOT add any new information.

2. Do NOT remove any information.

3. Preserve the exact meaning.

4. Write Hindi using English/Roman letters.

5. Keep common technical and English terms in English.

6. Do NOT translate technical terms such as:
   Active Recall
   Machine Learning
   Deep Learning
   Retention
   Students
   Information
   Data
   API
   SQL
   Python
   Java
   RAG

7. Do NOT use Devanagari.

8. Do NOT use academic transliteration.

9. Use natural everyday Roman Hindi.

10. Do NOT add labels or explanations.

11. Return ONLY the converted text.

Example:

Hindi:
एक्टिव रिकॉल एक ऐसी तकनीक है जो छात्रों को जानकारी याद रखने में मदद करती है।

Good:
Active Recall ek aisi technique hai jo students ko information yaad rakhne mein help karti hai.

Bad:
sakriya yaad dilana eka aisI takanIka hai...

Now convert the text.
"""

    response = ollama.chat(
        model="qwen2.5:3b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response["message"]["content"]


test_sentences = [

    "सक्रिय याद दिलाना एक सीखने की तकनीक है जो प्रतिधारण में सुधार करती है और छात्रों को जानकारी याद रखने में मदद करती है।",

    "सिंधु घाटी सभ्यता दक्षिण एशिया की सबसे पुरानी शहरी सभ्यताओं में से एक थी।",

    "सक्रिय याद रखने से छात्रों को जानकारी याद आती है और उनके प्रदर्शन में सुधार होता है।",

    "वैदिक युग प्राचीन भारतीय इतिहास का एक महत्वपूर्ण काल है।",

    "छात्र नोट्स पढ़ने के बजाय अपने ज्ञान की जांच करने के लिए सक्रिय यादों का उपयोग कर सकते हैं।",

    "गुप्त काल विज्ञान, गणित, साहित्य और कला में विकास के लिए जाना जाता है।",

    "यह तकनीक छात्रों से स्मृति से जानकारी को याद करने के लिए कहकर स्मृति में सुधार करती है।",

    "इस पाठ्यक्रम में सिंधु घाटी सभ्यता की मुख्य विशेषताएं बताई गई हैं।",

    "सक्रिय याद दिलाना उपयोगी है क्योंकि इससे छात्रों को सक्रिय रूप से जानकारी प्राप्त करनी होती है।",

    "चोल साम्राज्य दक्षिण भारत में एक महत्वपूर्ण शक्ति थी.",
]


for index, sentence in enumerate(test_sentences, start=1):

    result = convert_to_hinglish(sentence)

    print("\n" + "=" * 80)
    print(f"TEST {index}")

    print("\nHINDI:")
    print(sentence)

    print("\nHINGLISH:")
    print(result)