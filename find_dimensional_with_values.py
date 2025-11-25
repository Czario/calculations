"""Find dimensional concepts that have actual values."""

from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["normalize_data"]

cik = "0001065280"  # Netflix

print("=" * 80)
print("NETFLIX DIMENSIONAL CONCEPTS WITH VALUES")
print("=" * 80)

# Find all dimensional concepts
dimensional_concepts = list(db.normalized_concepts_quarterly.find({
    "company_cik": cik,
    "dimensions.explicitMember": {"$exists": True, "$ne": None}
}).limit(20))

print(f"\nFound {len(dimensional_concepts)} dimensional concepts (showing first 20)")

for concept in dimensional_concepts:
    concept_name = concept.get("concept", "Unknown")
    member = concept.get("dimensions", {}).get("explicitMember", "None")
    
    # Check if this concept has any quarterly values
    has_values = db.concept_values_quarterly.count_documents({
        "concept_id": concept["_id"],
        "company_cik": cik
    })
    
    # Check if Q4 exists
    has_q4 = db.concept_values_quarterly.count_documents({
        "concept_id": concept["_id"],
        "company_cik": cik,
        "reporting_period.quarter": 4
    })
    
    if has_values > 0:
        print(f"\n{concept_name}")
        print(f"  Member: {member}")
        print(f"  Path: {concept.get('path', 'N/A')}")
        print(f"  Statement: {concept.get('statement_type', 'N/A')}")
        print(f"  Total quarterly values: {has_values}")
        print(f"  Q4 values: {has_q4}")
        
        # Get a sample value
        sample = db.concept_values_quarterly.find_one({
            "concept_id": concept["_id"],
            "company_cik": cik
        })
        if sample:
            print(f"  Sample: FY{sample['reporting_period']['fiscal_year']} Q{sample['reporting_period']['quarter']}: {sample['value']:,.0f}")

# Look specifically for revenue with regions
print("\n" + "=" * 80)
print("LOOKING FOR REVENUE BY REGION PATTERNS")
print("=" * 80)

# Search for concepts with "United" or "Canada" in member
regional_concepts = list(db.normalized_concepts_quarterly.find({
    "company_cik": cik,
    "$or": [
        {"dimensions.explicitMember": {"$regex": "United", "$options": "i"}},
        {"dimensions.explicitMember": {"$regex": "Canada", "$options": "i"}},
        {"dimensions.explicitMember": {"$regex": "UCAN", "$options": "i"}},
        {"dimensions.explicitMember": {"$regex": "EMEA", "$options": "i"}},
        {"dimensions.explicitMember": {"$regex": "LATAM", "$options": "i"}},
        {"dimensions.explicitMember": {"$regex": "APAC", "$options": "i"}},
        {"dimensions.explicitMember": {"$regex": "AsiaPacific", "$options": "i"}},
    ]
}).limit(30))

print(f"\nFound {len(regional_concepts)} regional concepts")

for concept in regional_concepts:
    member = concept.get("dimensions", {}).get("explicitMember", "None")
    concept_name = concept.get("concept", "Unknown")
    
    # Check if has values
    value_count = db.concept_values_quarterly.count_documents({
        "concept_id": concept["_id"],
        "company_cik": cik
    })
    
    if value_count > 0:
        print(f"\n{member}")
        print(f"  Concept: {concept_name}")
        print(f"  Path: {concept.get('path', 'N/A')}")
        print(f"  Values: {value_count}")
