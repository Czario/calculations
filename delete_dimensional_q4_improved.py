"""Delete all calculated Q4 values for dimensional concepts - better approach."""

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
print("DELETING ALL CALCULATED Q4 VALUES FOR DIMENSIONAL CONCEPTS - IMPROVED")
print("=" * 80)

# Get all dimensional concepts for Netflix
dimensional_concepts = list(db.normalized_concepts_quarterly.find({
    "company_cik": netflix_cik,
    "dimension_concept": True
}, {"_id": 1}))

dimensional_concept_ids = [c["_id"] for c in dimensional_concepts]

print(f"\nFound {len(dimensional_concept_ids)} dimensional concepts")

# Delete all Q4 values for these concepts
result = db.concept_values_quarterly.delete_many({
    "concept_id": {"$in": dimensional_concept_ids},
    "company_cik": netflix_cik,
    "calculated": True,
    "reporting_period.quarter": 4
})

print(f"✓ Deleted {result.deleted_count} calculated Q4 values for dimensional concepts")

print("\n" + "=" * 80)
