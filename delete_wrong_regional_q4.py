"""Delete and recalculate Q4 for Netflix regional streaming members."""

from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["normalize_data"]

cik = "0001065280"  # Netflix

regions = [
    {"name": "UCAN", "member": "nflx:UnitedStatesAndCanadaMember"},
    {"name": "EMEA", "member": "us-gaap:EMEAMember"},
    {"name": "LATAM", "member": "srt:LatinAmericaMember"},
    {"name": "APAC", "member": "srt:AsiaPacificMember"}
]

concept_name = "nflx:StreamingMember"
path = "001.001.001"

print("=" * 80)
print("DELETING WRONG Q4 VALUES FOR NETFLIX REGIONAL STREAMING")
print("=" * 80)

total_deleted = 0

for region in regions:
    concept = db.normalized_concepts_quarterly.find_one({
        "company_cik": cik,
        "concept": concept_name,
        "path": path,
        "dimensions.explicitMember": region["member"]
    })
    
    if concept:
        result = db.concept_values_quarterly.delete_many({
            "concept_id": concept["_id"],
            "company_cik": cik,
            "reporting_period.quarter": 4,
            "calculated": True
        })
        
        print(f"\n{region['name']}: Deleted {result.deleted_count} Q4 values")
        total_deleted += result.deleted_count

print(f"\n" + "=" * 80)
print(f"Total deleted: {total_deleted} Q4 values")
print("=" * 80)
print("\nNow run: uv run python app.py --cik 0001065280")
print("to recalculate with the correct dimensional matching fix")
