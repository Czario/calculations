"""Verify all dimensional Q4 calculations are correct."""

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
print("VERIFYING ALL DIMENSIONAL Q4 CALCULATIONS")
print("=" * 80)

# Get all dimensional concepts
dimensional_concepts = list(db.normalized_concepts_quarterly.find({
    "company_cik": netflix_cik,
    "dimension_concept": True
}))

total_checked = 0
mismatches = []

for concept in dimensional_concepts:
    # Get calculated Q4 values
    q4_values = list(db.concept_values_quarterly.find({
        "concept_id": concept["_id"],
        "company_cik": netflix_cik,
        "calculated": True,
        "reporting_period.quarter": 4
    }))
    
    for q4_val in q4_values:
        fy = q4_val["reporting_period"]["fiscal_year"]
        
        # Get Q1, Q2, Q3
        quarterly_vals = {}
        for q in [1, 2, 3]:
            qval = db.concept_values_quarterly.find_one({
                "concept_id": concept["_id"],
                "company_cik": netflix_cik,
                "reporting_period.fiscal_year": fy,
                "reporting_period.quarter": q
            })
            if qval:
                quarterly_vals[q] = qval["value"]
        
        # Get annual value - match by both concept name and path
        annual_concept = db.normalized_concepts_annual.find_one({
            "company_cik": netflix_cik,
            "concept": concept["concept"],
            "path": concept["path"],
            "statement_type": concept["statement_type"]
        })
        
        if annual_concept and len(quarterly_vals) == 3:
            annual_val = db.concept_values_annual.find_one({
                "concept_id": annual_concept["_id"],
                "company_cik": netflix_cik,
                "reporting_period.fiscal_year": fy
            })
            
            if annual_val:
                total_checked += 1
                expected_q4 = annual_val["value"] - sum(quarterly_vals.values())
                actual_q4 = q4_val["value"]
                
                if abs(expected_q4 - actual_q4) > 0.01:
                    mismatches.append({
                        "concept": concept["concept"],
                        "path": concept["path"],
                        "fy": fy,
                        "expected": expected_q4,
                        "actual": actual_q4,
                        "diff": actual_q4 - expected_q4
                    })

print(f"\nTotal Q4 values checked: {total_checked}")
print(f"Mismatches found: {len(mismatches)}")

if mismatches:
    print("\n⚠️  MISMATCHES:")
    for m in mismatches:
        print(f"\n  {m['concept']} (path: {m['path']}) FY{m['fy']}:")
        print(f"    Expected: {m['expected']:,.2f}")
        print(f"    Actual: {m['actual']:,.2f}")
        print(f"    Difference: {m['diff']:,.2f}")
else:
    print("\n✅ All dimensional Q4 values are correct!")

print("\n" + "=" * 80)
