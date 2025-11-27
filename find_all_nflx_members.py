"""Find all nflx: member concepts and check their Q4 calculations."""

from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["financial_data"]

cik = "0001065280"  # Netflix

print("=" * 80)
print("SEARCHING FOR ALL NFLX: MEMBER CONCEPTS")
print("=" * 80)

# Search in concept_values_quarterly directly for nflx: members
print("\n📋 Checking concept_values_quarterly for nflx: members...")

pipeline = [
    {
        "$match": {
            "company_cik": cik
        }
    },
    {
        "$lookup": {
            "from": "normalized_concepts_quarterly",
            "localField": "concept_id",
            "foreignField": "_id",
            "as": "concept"
        }
    },
    {
        "$unwind": "$concept"
    },
    {
        "$match": {
            "concept.name": {"$regex": "^nflx:", "$options": "i"}
        }
    },
    {
        "$group": {
            "_id": "$concept.name",
            "concept_id": {"$first": "$concept._id"},
            "path": {"$first": "$concept.path"},
            "label": {"$first": "$concept.label"},
            "count": {"$sum": 1}
        }
    },
    {
        "$sort": {"_id": 1}
    }
]

results = list(db.concept_values_quarterly.aggregate(pipeline))

print(f"\nFound {len(results)} unique nflx: concepts with quarterly values")

for result in results:
    concept_name = result["_id"]
    concept_id = result["concept_id"]
    
    # Skip if not a member concept
    if "Member" not in concept_name:
        continue
        
    print(f"\n{'=' * 80}")
    print(f"Concept: {concept_name}")
    print(f"Path: {result['path']}")
    print(f"Label: {result.get('label', 'N/A')}")
    print(f"Total values: {result['count']}")
    
    # Get all values grouped by fiscal year
    values = list(db.concept_values_quarterly.find({
        "concept_id": concept_id,
        "company_cik": cik
    }).sort([("reporting_period.fiscal_year", -1), ("reporting_period.quarter", 1)]))
    
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
        print(f"\n  FY {fy}:")
        quarters = years[fy]
        
        # Print all quarters
        for q in [1, 2, 3, 4]:
            if q in quarters:
                calc_marker = " [CALCULATED]" if quarters[q]["calculated"] else ""
                print(f"    Q{q}: {quarters[q]['value']:>15,.2f}{calc_marker}")
        
        # Get annual value
        annual_val = db.concept_values_annual.find_one({
            "company_cik": cik,
            "reporting_period.fiscal_year": fy
        })
        
        # Try to find matching annual concept
        annual_concept = db.normalized_concepts_annual.find_one({
            "company_cik": cik,
            "name": concept_name
        })
        
        if annual_concept:
            annual_val = db.concept_values_annual.find_one({
                "concept_id": annual_concept["_id"],
                "company_cik": cik,
                "reporting_period.fiscal_year": fy
            })
            
            if annual_val:
                print(f"    Annual: {annual_val['value']:>15,.2f}")
                
                # Calculate expected Q4
                if 1 in quarters and 2 in quarters and 3 in quarters:
                    q1_q2_q3_sum = quarters[1]["value"] + quarters[2]["value"] + quarters[3]["value"]
                    expected_q4 = annual_val['value'] - q1_q2_q3_sum
                    print(f"    Expected Q4: {expected_q4:>11,.2f} (Annual - Q1 - Q2 - Q3)")
                    
                    if 4 in quarters:
                        actual_q4 = quarters[4]["value"]
                        diff = actual_q4 - expected_q4
                        if abs(diff) > 0.01:
                            print(f"    ⚠️  MISMATCH! Actual Q4 = {actual_q4:,.2f}, Difference = {diff:,.2f}")
                        else:
                            print(f"    ✓ Q4 matches expected value")
                    else:
                        print(f"    ❌ Q4 is missing!")
            else:
                print(f"    ⚠️  No annual value found")
        else:
            print(f"    ⚠️  No matching annual concept found")

print("\n" + "=" * 80)
