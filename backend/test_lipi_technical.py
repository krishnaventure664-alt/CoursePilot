from lipi import Transliterator


model = Transliterator(
    model_dir="./models/lipi"
)


test_sentences = [

    "Machine Learning एक ऐसी तकनीक है जो डेटा से पैटर्न सीखती है।",

    "Neural Network का उपयोग जटिल समस्याओं को हल करने के लिए किया जाता है।",

    "Gradient Descent मॉडल के parameters को optimize करने में मदद करता है।",

    "RAG सिस्टम relevant information को retrieve करके बेहतर answer generate करता है।",

    "Embeddings text को numerical vectors में बदलते हैं।",

    "Java में ArrayList एक commonly used data structure है।",

    "SQL का उपयोग database से data निकालने और उसे manage करने के लिए किया जाता है।",

    "React का उपयोग interactive user interfaces बनाने के लिए किया जाता है।",

    "API दो अलग-अलग software systems के बीच communication करने में मदद करता है।",

    "Active Recall students को information याद रखने में help करता है।",
]


for index, sentence in enumerate(test_sentences, start=1):

    result = model.transliterate_text(sentence)

    print("\n" + "=" * 80)

    print(f"TEST {index}")

    print("\nINPUT:")
    print(sentence)

    print("\nROMAN OUTPUT:")
    print(result)