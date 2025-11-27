"""Check if 'incorrect' point-in-time Q4 values are actually correct copies of annual."""

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

# Check specific concepts
concepts_to_check = [
    "us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding"
]

print("=" * 100)
print("CHECKING IF POINT-IN-TIME Q4 VALUES ARE CORRECT")
print("=" * 100)

for concept_name in concepts_to_check:
    print(f"\n{'=' * 100}")
    print(f"Concept: {concept_name}")
    print("=" * 100)
    
    # Find the concept
    concept = db.normalized_concepts_quarterly.find_one({
        "company_cik": netflix_cik,
        "$or": [{"name": concept_name}, {"concept": concept_name}]
    })
    
    if not concept:
        print("  Concept not found!")
        continue
    
    # Get Q4 values
    q4_values = list(db.concept_values_quarterly.find({
        "concept_id": concept["_id"],
        "company_cik": netflix_cik,
        "calculated": True,
        "reporting_period.quarter": 4
    }).sort("reporting_period.fiscal_year", 1).limit(3))
    
    for q4 in q4_values:
        fy = q4["reporting_period"]["fiscal_year"]
        q4_val = q4["value"]
        
        # Get annual value
        annual_concept = db.normalized_concepts_annual.find_one({
            "company_cik": netflix_cik,
            "$or": [{"name": concept_name}, {"concept": concept_name}]
        })
        
        if annual_concept:
            annual = db.concept_values_annual.find_one({
                "concept_id": annual_concept["_id"],
                "company_cik": netflix_cik,
                "reporting_period.fiscal_year": fy
            })
            
            if annual:
                annual_val = annual["value"]
                
                print(f"\n  FY{fy}:")
                print(f"    Q4 value: {q4_val:>18,.2f}")
                print(f"    Annual value: {annual_val:>14,.2f}")
                
                if abs(q4_val - annual_val) < 0.01:
                    print(f"    ✓ Q4 = Annual (CORRECT for point-in-time)")
                else:
                    print(f"    ✗ Q4 ≠ Annual (INCORRECT!)")
                    print(f"    Difference: {q4_val - annual_val:,.2f}")

print("\n" + "=" * 100)
