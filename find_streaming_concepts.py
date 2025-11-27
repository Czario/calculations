"""Find all dimensional concepts with 'Streaming' in the name for Netflix."""

from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["financial_data"]

cik = "0001065280"  # Netflix

print("=" * 80)
print("SEARCHING FOR STREAMING MEMBERS IN NETFLIX DATA")
print("=" * 80)

# Search in quarterly concepts
print("\n📋 QUARTERLY CONCEPTS with 'Streaming':")
quarterly_concepts = list(db.normalized_concepts_quarterly.find({
    "company_cik": cik,
    "name": {"$regex": "Streaming", "$options": "i"}
}).limit(20))

for concept in quarterly_concepts:
    print(f"\n  Name: {concept['name']}")
    print(f"  Path: {concept['path']}")
    print(f"  Label: {concept.get('label', 'N/A')}")
    
    # Count values
    value_count = db.concept_values_quarterly.count_documents({
        "concept_id": concept["_id"],
        "company_cik": cik
    })
    print(f"  Values: {value_count}")

# Search in annual concepts
print("\n\n📋 ANNUAL CONCEPTS with 'Streaming':")
annual_concepts = list(db.normalized_concepts_annual.find({
    "company_cik": cik,
    "name": {"$regex": "Streaming", "$options": "i"}
}).limit(20))

for concept in annual_concepts:
    print(f"\n  Name: {concept['name']}")
    print(f"  Path: {concept['path']}")
    print(f"  Label: {concept.get('label', 'N/A')}")
    
    # Count values
    value_count = db.concept_values_annual.count_documents({
        "concept_id": concept["_id"],
        "company_cik": cik
    })
    print(f"  Values: {value_count}")

# Also search for 'Domestic'
print("\n\n📋 QUARTERLY CONCEPTS with 'Domestic':")
quarterly_concepts = list(db.normalized_concepts_quarterly.find({
    "company_cik": cik,
    "name": {"$regex": "Domestic", "$options": "i"}
}).limit(20))

for concept in quarterly_concepts:
    print(f"\n  Name: {concept['name']}")
    print(f"  Path: {concept['path']}")
    print(f"  Label: {concept.get('label', 'N/A')}")
    
    # Count values
    value_count = db.concept_values_quarterly.count_documents({
        "concept_id": concept["_id"],
        "company_cik": cik
    })
    print(f"  Values: {value_count}")

print("\n" + "=" * 80)
