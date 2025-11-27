"""Delete remaining incorrect point-in-time Q4 values."""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database name from config
db_name = os.getenv("TARGET_DB_NAME", "normalize_data")

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client[db_name]

netflix_cik = "0001065280"

print("=" * 80)
print("DELETING REMAINING POINT-IN-TIME Q4 VALUES")
print("=" * 80)

# Additional patterns and specific concept names
targets = [
    "WeightedAverageNumberOfDilutedSharesOutstanding",
    "CashCashEquivalentsAndRestrictedCashEndOfYear"
]

total_deleted = 0

for target in targets:
    # Find concepts matching this exact name or pattern
    concepts = list(db.normalized_concepts_quarterly.find({
        "company_cik": netflix_cik,
        "$or": [
            {"name": target},
            {"concept": target},
            {"name": {"$regex": target, "$options": "i"}},
            {"concept": {"$regex": target, "$options": "i"}}
        ]
    }))
    
    print(f"\nTarget: {target}")
    print(f"  Found {len(concepts)} matching concepts")
    
    for concept in concepts:
        concept_name = concept.get("concept") or concept.get("name")
        
        # Delete calculated Q4 values for this concept
        result = db.concept_values_quarterly.delete_many({
            "concept_id": concept["_id"],
            "company_cik": netflix_cik,
            "calculated": True,
            "reporting_period.quarter": 4
        })
        
        if result.deleted_count > 0:
            print(f"    Deleted {result.deleted_count} Q4 values for {concept_name}")
            total_deleted += result.deleted_count

print(f"\n✓ Total deleted: {total_deleted} Q4 values")
print("\n" + "=" * 80)
