"""Investigate the one remaining mismatch."""

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
concept_name = "nflx:InternationalMember"
path = "001.004.002"

print("=" * 80)
print(f"INVESTIGATING: {concept_name} at path {path} for FY2011")
print("=" * 80)

# Find quarterly concept
q_concept = db.normalized_concepts_quarterly.find_one({
    "company_cik": netflix_cik,
    "concept": concept_name,
    "path": path
})

print(f"\nQuarterly Concept:")
print(f"  Concept: {q_concept['concept']}")
print(f"  Label: {q_concept.get('label')}")
print(f"  Concept Name: {q_concept.get('concept_name')}")

# Get quarterly values for FY2011
q_vals = list(db.concept_values_quarterly.find({
    "concept_id": q_concept["_id"],
    "company_cik": netflix_cik,
    "reporting_period.fiscal_year": 2011
}).sort("reporting_period.quarter", 1))

print(f"\nQuarterly Values for FY2011:")
for qv in q_vals:
    q = qv["reporting_period"]["quarter"]
    calc = " [CALCULATED]" if qv.get("calculated") else ""
    print(f"  Q{q}: {qv['value']:>15,.2f}{calc}")

# Find annual concept
a_concept = db.normalized_concepts_annual.find_one({
    "company_cik": netflix_cik,
    "concept": concept_name,
    "path": path
})

if a_concept:
    print(f"\nAnnual Concept:")
    print(f"  Concept: {a_concept['concept']}")
    print(f"  Label: {a_concept.get('label')}")
    print(f"  Concept Name: {a_concept.get('concept_name')}")
    
    # Get annual value
    a_val = db.concept_values_annual.find_one({
        "concept_id": a_concept["_id"],
        "company_cik": netflix_cik,
        "reporting_period.fiscal_year": 2011
    })
    
    if a_val:
        print(f"  Annual Value: {a_val['value']:,.2f}")
        
        # Calculate what Q4 should be
        q1 = q_vals[0]["value"] if len(q_vals) > 0 and q_vals[0]["reporting_period"]["quarter"] == 1 else None
        q2 = q_vals[1]["value"] if len(q_vals) > 1 and q_vals[1]["reporting_period"]["quarter"] == 2 else None
        q3 = q_vals[2]["value"] if len(q_vals) > 2 and q_vals[2]["reporting_period"]["quarter"] == 3 else None
        
        if q1 is not None and q2 is not None and q3 is not None:
            expected_q4 = a_val['value'] - (q1 + q2 + q3)
            print(f"\n  Expected Q4: {expected_q4:,.2f} (Annual - Q1 - Q2 - Q3)")
            print(f"  Calculation: {a_val['value']:,.2f} - ({q1:,.2f} + {q2:,.2f} + {q3:,.2f})")

# Check if there are multiple annual concepts with the same name
all_annual = list(db.normalized_concepts_annual.find({
    "company_cik": netflix_cik,
    "concept": concept_name
}))

print(f"\n\nAll annual concepts with name '{concept_name}': {len(all_annual)}")
for i, ac in enumerate(all_annual, 1):
    print(f"\n  {i}. Path: {ac['path']}")
    print(f"     Label: {ac.get('label')}")
    print(f"     Concept Name: {ac.get('concept_name')}")
    
    # Get sample value
    sample = db.concept_values_annual.find_one({
        "concept_id": ac["_id"],
        "company_cik": netflix_cik,
        "reporting_period.fiscal_year": 2011
    })
    if sample:
        print(f"     FY2011 Value: {sample['value']:,.2f}")

print("\n" + "=" * 80)
