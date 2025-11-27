"""Check what concepts actually exist for Netflix."""

from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["financial_data"]

cik = "0001065280"  # Netflix

print("=" * 80)
print("CHECKING NETFLIX CONCEPTS")
print("=" * 80)

# Check if any concepts exist for this CIK
print("\n📋 Checking normalized_concepts_quarterly...")
q_count = db.normalized_concepts_quarterly.count_documents({"company_cik": cik})
print(f"Total quarterly concepts for Netflix: {q_count}")

if q_count > 0:
    # Show sample concepts
    samples = list(db.normalized_concepts_quarterly.find({"company_cik": cik}).limit(10))
    print("\nSample quarterly concepts:")
    for s in samples:
        print(f"  - {s['name']} | {s['path']}")

print("\n📋 Checking normalized_concepts_annual...")
a_count = db.normalized_concepts_annual.count_documents({"company_cik": cik})
print(f"Total annual concepts for Netflix: {a_count}")

if a_count > 0:
    # Show sample concepts
    samples = list(db.normalized_concepts_annual.find({"company_cik": cik}).limit(10))
    print("\nSample annual concepts:")
    for s in samples:
        print(f"  - {s['name']} | {s['path']}")

# Check concept_values_quarterly
print("\n📋 Checking concept_values_quarterly...")
qv_count = db.concept_values_quarterly.count_documents({"company_cik": cik})
print(f"Total quarterly values for Netflix: {qv_count}")

if qv_count > 0:
    # Show sample value with concept name
    sample = db.concept_values_quarterly.find_one({"company_cik": cik})
    concept = db.normalized_concepts_quarterly.find_one({"_id": sample["concept_id"]})
    if concept:
        print(f"\nSample quarterly value:")
        print(f"  Concept: {concept['name']}")
        print(f"  Path: {concept['path']}")
        print(f"  FY{sample['reporting_period']['fiscal_year']} Q{sample['reporting_period']['quarter']}: {sample['value']:,.2f}")

# Check for dimensional values
print("\n📋 Checking dimensional quarterly values...")
dim_count = db.concept_values_quarterly.count_documents({
    "company_cik": cik,
    "dimension_value": True
})
print(f"Total dimensional quarterly values for Netflix: {dim_count}")

if dim_count > 0:
    # Show sample dimensional values
    samples = list(db.concept_values_quarterly.find({
        "company_cik": cik,
        "dimension_value": True
    }).limit(5))
    
    print("\nSample dimensional quarterly values:")
    for sample in samples:
        concept = db.normalized_concepts_quarterly.find_one({"_id": sample["concept_id"]})
        if concept:
            print(f"\n  Concept: {concept['name']}")
            print(f"  Path: {concept['path']}")
            print(f"  FY{sample['reporting_period']['fiscal_year']} Q{sample['reporting_period']['quarter']}: {sample['value']:,.2f}")
            print(f"  Calculated: {sample.get('calculated', False)}")

print("\n" + "=" * 80)
