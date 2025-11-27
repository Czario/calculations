"""Search for any dimensional concepts for Netflix."""

from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["financial_data"]

cik = "0001065280"  # Netflix

print("=" * 80)
print("SEARCHING FOR DIMENSIONAL CONCEPTS IN NETFLIX DATA")
print("=" * 80)

# Search for dimensional concepts (dimension_value = True)
print("\n📋 DIMENSIONAL QUARTERLY CONCEPTS:")
quarterly_concepts = list(db.normalized_concepts_quarterly.find({
    "company_cik": cik,
    "dimension_value": True
}).limit(50))

print(f"Found {len(quarterly_concepts)} dimensional quarterly concepts")

for i, concept in enumerate(quarterly_concepts[:10], 1):
    print(f"\n{i}. Name: {concept['name']}")
    print(f"   Path: {concept['path']}")
    print(f"   Label: {concept.get('label', 'N/A')}")
    
    # Count values
    value_count = db.concept_values_quarterly.count_documents({
        "concept_id": concept["_id"],
        "company_cik": cik
    })
    print(f"   Values: {value_count}")
    
    # Show sample value
    if value_count > 0:
        sample = db.concept_values_quarterly.find_one({
            "concept_id": concept["_id"],
            "company_cik": cik
        })
        print(f"   Sample: FY{sample['reporting_period']['fiscal_year']} Q{sample['reporting_period']['quarter']} = {sample['value']:,.2f}")

# Check for concepts with 'nflx:' prefix
print("\n\n📋 CONCEPTS WITH 'nflx:' PREFIX:")
nflx_concepts = list(db.normalized_concepts_quarterly.find({
    "company_cik": cik,
    "name": {"$regex": "^nflx:", "$options": "i"}
}).limit(50))

print(f"Found {len(nflx_concepts)} concepts with nflx: prefix")

for i, concept in enumerate(nflx_concepts[:20], 1):
    print(f"\n{i}. Name: {concept['name']}")
    print(f"   Path: {concept['path']}")
    print(f"   Dimensional: {concept.get('dimension_value', False)}")
    
    # Count values
    value_count = db.concept_values_quarterly.count_documents({
        "concept_id": concept["_id"],
        "company_cik": cik
    })
    print(f"   Values: {value_count}")

print("\n" + "=" * 80)
