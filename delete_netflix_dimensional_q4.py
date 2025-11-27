"""Delete all calculated Q4 values for dimensional concepts for Netflix."""

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
print("DELETING INCORRECT Q4 VALUES FOR NETFLIX DIMENSIONAL CONCEPTS")
print("=" * 80)

# Find all calculated Q4 values for dimensional concepts
result = db.concept_values_quarterly.delete_many({
    "company_cik": netflix_cik,
    "dimension_value": True,
    "calculated": True,
    "reporting_period.quarter": 4
})

print(f"\n✓ Deleted {result.deleted_count} incorrect Q4 values")

print("\n" + "=" * 80)
