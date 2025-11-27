"""Check Q4 calculations for DomesticStreamingMember and InternationalStreamingMember."""

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

print("=" * 100)
print("CHECKING DOMESTIC AND INTERNATIONAL STREAMING MEMBER Q4 CALCULATIONS")
print("=" * 100)

# Find concepts with these specific members
for member_name in ["DomesticStreamingMember", "InternationalStreamingMember"]:
    print(f"\n{'=' * 100}")
    print(f"CHECKING: {member_name}")
    print("=" * 100)
    
    # Find the dimensional concept
    concepts = list(db.normalized_concepts_quarterly.find({
        "company_cik": netflix_cik,
        "concept": f"nflx:{member_name}",
        "dimension_concept": True
    }))
    
    print(f"\nFound {len(concepts)} concepts with {member_name}")
    
    for concept in concepts:
        print(f"\n  Concept: {concept.get('concept', 'N/A')}")
        print(f"  Label: {concept.get('label', 'N/A')}")
        print(f"  Path: {concept.get('path', 'N/A')}")
        print(f"  Statement: {concept.get('statement_type', 'N/A')}")
        print(f"  Concept Name: {concept.get('concept_name', 'N/A')}")
        
        # Get all quarterly values for this concept
        values = list(db.concept_values_quarterly.find({
            "concept_id": concept["_id"],
            "company_cik": netflix_cik
        }).sort([("reporting_period.fiscal_year", -1), ("reporting_period.quarter", 1)]))
        
        print(f"\n  Total quarterly values: {len(values)}")
        
        # Group by fiscal year
        years = {}
        for val in values:
            fy = val["reporting_period"]["fiscal_year"]
            quarter = val["reporting_period"]["quarter"]
            if fy not in years:
                years[fy] = {}
            years[fy][quarter] = {
                "value": val["value"],
                "calculated": val.get("calculated", False)
            }
        
        # Check each year
        for fy in sorted(years.keys(), reverse=True):
            print(f"\n  📊 FY {fy}:")
            quarters = years[fy]
            
            # Print all quarters
            for q in [1, 2, 3, 4]:
                if q in quarters:
                    calc_marker = " [CALCULATED]" if quarters[q]["calculated"] else ""
                    print(f"      Q{q}: {quarters[q]['value']:>18,.2f}{calc_marker}")
            
            # Try to find matching annual concept and value
            annual_concept = db.normalized_concepts_annual.find_one({
                "company_cik": netflix_cik,
                "concept": f"nflx:{member_name}",
                "dimension_concept": True,
                "path": concept.get("path")
            })
            
            if annual_concept:
                annual_val = db.concept_values_annual.find_one({
                    "concept_id": annual_concept["_id"],
                    "company_cik": netflix_cik,
                    "reporting_period.fiscal_year": fy
                })
                
                if annual_val:
                    print(f"      Annual: {annual_val['value']:>18,.2f}")
                    
                    # Calculate expected Q4
                    if 1 in quarters and 2 in quarters and 3 in quarters:
                        q1_q2_q3_sum = quarters[1]["value"] + quarters[2]["value"] + quarters[3]["value"]
                        expected_q4 = annual_val['value'] - q1_q2_q3_sum
                        print(f"      Expected Q4: {expected_q4:>14,.2f} (Annual - Q1 - Q2 - Q3)")
                        
                        if 4 in quarters:
                            actual_q4 = quarters[4]["value"]
                            diff = actual_q4 - expected_q4
                            if abs(diff) > 0.01:
                                print(f"      ⚠️  MISMATCH! Actual Q4 = {actual_q4:,.2f}, Difference = {diff:,.2f}")
                                print(f"          This is WRONG! Q4 should be {expected_q4:,.2f}")
                            else:
                                print(f"      ✓ Q4 is correct")
                        else:
                            print(f"      ❌ Q4 is missing! Should be {expected_q4:,.2f}")
                else:
                    print(f"      ⚠️  No annual value found for FY{fy}")
            else:
                print(f"      ⚠️  No matching annual concept found")

print("\n" + "=" * 100)
