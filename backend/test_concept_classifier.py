from services.concept_candidate_service import (
    extract_concept_candidates
)

from services.concept_classifier_service import (
    classify_concept_candidates
)


text = """
इस वीडियो में एक्टिव रिकॉलिंग क्या है?
एंशिएंट हिस्ट्री में एक्टिव रिकॉलिंग को कैसे अप्लाई करना है?

Machine Learning में हम data से patterns सीखते हैं।
Gradient Descent model के parameters को optimize करने में मदद करता है।

RAG relevant information को retrieve करके answer generate करता है।
"""


print("\n" + "=" * 80)
print("STEP 1: CANDIDATES")
print("=" * 80)


candidates = extract_concept_candidates(
    text
)

for index, candidate in enumerate(
    candidates,
    start=1
):

    print(
        f"{index}. {candidate}"
    )


print("\n" + "=" * 80)
print("STEP 2: CLASSIFIED CONCEPTS")
print("=" * 80)


concepts = classify_concept_candidates(
    candidates=candidates,
    transcript_text=text
)


for index, concept in enumerate(
    concepts,
    start=1
):

    print(
        f"{index}. "
        f"{concept['candidate']}"
        
    )