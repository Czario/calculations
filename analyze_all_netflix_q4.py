"""Comprehensive analysis of ALL Q4 calculations for Netflix."""

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
print("COMPREHENSIVE Q4 CALCULATION ANALYSIS FOR NETFLIX")
print("=" * 100)

# Get all concepts (both dimensional and non-dimensional)
all_concepts = list(db.normalized_concepts_quarterly.find({
    "company_cik": netflix_cik
}))

print(f"\nTotal concepts: {len(all_concepts)}")

total_checked = 0
total_correct = 0
mismatches = []
missing_annual = []
missing_quarters = []

for concept in all_concepts:
    # Get all calculated Q4 values for this concept
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
            qvals = list(db.concept_values_quarterly.find({
                "concept_id": concept["_id"],
                "company_cik": netflix_cik,
                "reporting_period.fiscal_year": fy,
                "reporting_period.quarter": q
            }))
            if len(qvals) == 1:
                quarterly_vals[q] = qvals[0]["value"]
            elif len(qvals) > 1:
                # Multiple values found - use sum or flag as issue
                quarterly_vals[q] = sum(v["value"] for v in qvals)
        
        if len(quarterly_vals) != 3:
            missing_quarters.append({
                "concept": concept.get("concept", concept.get("name")),
                "path": concept.get("path"),
                "fy": fy,
                "missing": [q for q in [1, 2, 3] if q not in quarterly_vals]
            })
            continue
        
        # Find matching annual concept
        is_dimensional = concept.get("dimension_concept", False)
        
        if is_dimensional:
            # For dimensional concepts, match by concept name AND path
            annual_concept = db.normalized_concepts_annual.find_one({
                "company_cik": netflix_cik,
                "concept": concept["concept"],
                "path": concept["path"],
                "statement_type": concept["statement_type"]
            })
        else:
            # For non-dimensional, match by name/concept and path
            concept_name = concept.get("name") or concept.get("concept")
            annual_concept = db.normalized_concepts_annual.find_one({
                "company_cik": netflix_cik,
                "$or": [
                    {"name": concept_name},
                    {"concept": concept_name}
                ],
                "path": concept["path"],
                "statement_type": concept["statement_type"]
            })
        
        if not annual_concept:
            missing_annual.append({
                "concept": concept.get("concept", concept.get("name")),
                "path": concept.get("path"),
                "fy": fy,
                "dimensional": is_dimensional
            })
            continue
        
        # Get annual value
        annual_val = db.concept_values_annual.find_one({
            "concept_id": annual_concept["_id"],
            "company_cik": netflix_cik,
            "reporting_period.fiscal_year": fy
        })
        
        if not annual_val:
            missing_annual.append({
                "concept": concept.get("concept", concept.get("name")),
                "path": concept.get("path"),
                "fy": fy,
                "dimensional": is_dimensional,
                "reason": "annual_concept_found_but_no_value"
            })
            continue
        
        # Calculate expected Q4
        total_checked += 1
        expected_q4 = annual_val["value"] - sum(quarterly_vals.values())
        actual_q4 = q4_val["value"]
        
        if abs(expected_q4 - actual_q4) > 0.01:
            mismatches.append({
                "concept": concept.get("concept", concept.get("name")),
                "path": concept.get("path"),
                "statement": concept.get("statement_type"),
                "fy": fy,
                "q1": quarterly_vals.get(1),
                "q2": quarterly_vals.get(2),
                "q3": quarterly_vals.get(3),
                "annual": annual_val["value"],
                "expected": expected_q4,
                "actual": actual_q4,
                "diff": actual_q4 - expected_q4,
                "dimensional": is_dimensional
            })
        else:
            total_correct += 1

print(f"\n📊 SUMMARY:")
print(f"  Total Q4 values checked: {total_checked}")
print(f"  Correct: {total_correct}")
print(f"  Incorrect: {len(mismatches)}")
print(f"  Missing annual values: {len(missing_annual)}")
print(f"  Missing quarterly values: {len(missing_quarters)}")

if mismatches:
    print(f"\n{'=' * 100}")
    print(f"⚠️  INCORRECT Q4 CALCULATIONS ({len(mismatches)} found):")
    print(f"{'=' * 100}")
    
    for i, m in enumerate(mismatches, 1):
        print(f"\n{i}. {m['concept']} (path: {m['path']}) - {m['statement']} - FY{m['fy']}")
        print(f"   Dimensional: {m['dimensional']}")
        print(f"   Q1: {m['q1']:>18,.2f}")
        print(f"   Q2: {m['q2']:>18,.2f}")
        print(f"   Q3: {m['q3']:>18,.2f}")
        print(f"   Sum Q1-Q3: {m['q1'] + m['q2'] + m['q3']:>11,.2f}")
        print(f"   Annual: {m['annual']:>15,.2f}")
        print(f"   Expected Q4: {m['expected']:>11,.2f}")
        print(f"   Actual Q4: {m['actual']:>13,.2f}")
        print(f"   Difference: {m['diff']:>14,.2f}")
else:
    print("\n✅ All Q4 calculations are correct!")

if missing_annual:
    print(f"\n{'=' * 100}")
    print(f"ℹ️  CONCEPTS WITH MISSING ANNUAL VALUES ({len(missing_annual)} found):")
    print(f"{'=' * 100}")
    
    # Group by concept
    from collections import defaultdict
    by_concept = defaultdict(list)
    for m in missing_annual:
        by_concept[m['concept']].append(m)
    
    for concept, entries in sorted(by_concept.items())[:20]:  # Show first 20
        print(f"\n  {concept}:")
        for e in entries[:5]:  # Show first 5 years per concept
            print(f"    FY{e['fy']} - path: {e['path']} - dimensional: {e['dimensional']}")

print("\n" + "=" * 100)
