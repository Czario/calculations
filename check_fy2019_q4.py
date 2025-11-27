"""Check what's wrong with FY2019 specifically."""

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
member_name = "nflx:DomesticStreamingMember"
path = "002.001"
statement = "income_statement"

print("=" * 80)
print("CHECKING FY2019 SPECIFICALLY")
print("=" * 80)

# Find the quarterly concept
quarterly_concept = db.normalized_concepts_quarterly.find_one({
    "company_cik": netflix_cik,
    "concept": member_name,
    "path": path,
    "statement_type": statement
})

print(f"\nQuarterly Concept ID: {quarterly_concept['_id']}")

# Find ALL Q4 values for this concept in FY2019
q4_values = list(db.concept_values_quarterly.find({
    "concept_id": quarterly_concept["_id"],
    "company_cik": netflix_cik,
    "reporting_period.fiscal_year": 2019,
    "reporting_period.quarter": 4
}))

print(f"\nFound {len(q4_values)} Q4 values for FY2019:")

for i, q4 in enumerate(q4_values, 1):
    print(f"\n{i}. Value: {q4['value']:,.2f}")
    print(f"   Calculated: {q4.get('calculated', False)}")
    print(f"   Dimension Value: {q4.get('dimension_value', False)}")
    print(f"   Created At: {q4.get('created_at', 'N/A')}")
    print(f"   _id: {q4['_id']}")

print("\n" + "=" * 80)
