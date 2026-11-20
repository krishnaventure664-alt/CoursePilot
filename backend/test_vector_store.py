from services.vector_store_service import collection

print("Vector database connected succesfully!")

print("Collection name:",collection.name)
print("Number of chunks:",collection.count())