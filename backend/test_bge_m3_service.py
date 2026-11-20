from services.bge_m3_service import encode_text


text = "What is machine learning?"

result = encode_text(text)

print("=" * 60)
print("BGE-M3 TEST")
print("=" * 60)

print("Dense type:", type(result["dense"]))
print("Dense dimensions:", len(result["dense"]))

print(
    "Sparse type:",
    type(result["sparse"])
)

print(
    "Sparse terms:",
    len(result["sparse"])
)

print(
    "Sparse sample:",
    list(result["sparse"].items())[:10]
)