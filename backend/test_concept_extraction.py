from services.term_extraction_service import extract_course_terms


text = """
इस वीडियो में एक्टिव रिकॉलिंग क्या है?
एंशिएंट हिस्ट्री में एक्टिव रिकॉलिंग को कैसे अप्लाई करना है?

Machine Learning में हम data से patterns सीखते हैं।
Gradient Descent model के parameters को optimize करने में मदद करता है।

RAG relevant information को retrieve करके answer generate करता है।
"""


print("\n" + "=" * 80)
print("COURSE CONCEPT EXTRACTION")
print("=" * 80)


concepts = extract_course_terms(text)


for index, concept in enumerate(
    concepts,
    start=1
):

    print(f"\n{index}. CANONICAL:")
    print(concept["canonical"])

    print("   VARIANTS:")

    for variant in concept["variants"]:
        print(f"   - {variant}")