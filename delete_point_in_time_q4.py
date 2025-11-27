"""Delete incorrect Q4 values for point-in-time concepts."""

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
print("DELETING INCORRECT Q4 VALUES FOR POINT-IN-TIME CONCEPTS")
print("=" * 80)

# Patterns for point-in-time concepts
patterns = [
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    "WeightedAverageNumberOfShares",
    "PeriodIncreaseDecrease",
    "EffectOfExchangeRate"
]

total_deleted = 0

for pattern in patterns:
    # Find concepts matching this pattern
    concepts = list(db.normalized_concepts_quarterly.find({
        "company_cik": netflix_cik,
        "$or": [
            {"name": {"$regex": pattern, "$options": "i"}},
            {"concept": {"$regex": pattern, "$options": "i"}}
        ]
    }))
    
    print(f"\nPattern: {pattern}")
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

print(f"\n✓ Total deleted: {total_deleted} incorrect Q4 values")
print("\n" + "=" * 80)
