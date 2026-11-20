from transformers import AutoModelForSequenceClassification

MODEL_NAME = "vectara/hallucination_evaluation_model"

print("Loading HHEM...")
model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME,
    trust_remote_code=True
)

print("HHEM loaded.")
print("Model type:", type(model).__name__)

tests = [
    (
        "Gautam Buddha founded Buddhism.",
        "Gautam Buddha founded Buddhism."
    ),
    (
        "Bimbisara was a contemporary of Gautam Buddha.",
        "Bimbisara founded Buddhism."
    ),
    (
        "The evidence discusses Buddhism and Gautam Buddha.",
        "Buddhism was founded in 500 BC."
    ),
]

print()
print("=" * 70)
print("HHEM BASIC TEST")
print("=" * 70)

for i, (evidence, claim) in enumerate(tests, start=1):

    print()
    print(f"Test {i}")
    print("-" * 70)
    print("Evidence:", evidence)
    print("Claim   :", claim)

    result = model.predict([
        (evidence, claim)
    ])

    print("Raw result:", result)

print()
print("=" * 70)
print("TEST COMPLETE")
print("=" * 70)