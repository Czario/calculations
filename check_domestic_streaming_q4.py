"""Check DomesticStreamingMember Q4 calculation."""

from pymongo import MongoClient
from bson import ObjectId

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["financial_data"]

cik = "0001065280"  # Netflix

print("=" * 80)
print("CHECKING DOMESTIC STREAMING MEMBER Q4 CALCULATION")
print("=" * 80)

# Find the DomesticStreamingMember concept in quarterly
quarterly_concepts = list(db.normalized_concepts_quarterly.find({
    "company_cik": cik,
    "name": {"$regex": "DomesticStreamingMember", "$options": "i"}
}))

print(f"\n📋 Found {len(quarterly_concepts)} DomesticStreamingMember concepts in quarterly")

for concept in quarterly_concepts:
    print(f"\n  Concept: {concept['name']}")
    print(f"  Path: {concept['path']}")
    print(f"  Label: {concept.get('label', 'N/A')}")
    print(f"  ID: {concept['_id']}")
    
    # Get all quarterly values for this concept
    q_values = list(db.concept_values_quarterly.find({
        "concept_id": concept["_id"],
        "company_cik": cik
    }).sort([("reporting_period.fiscal_year", -1), ("reporting_period.quarter", 1)]))
    
    print(f"\n  📊 Quarterly Values ({len(q_values)} total):")
    
    # Group by fiscal year
    years = {}
    for val in q_values:
        fy = val["reporting_period"]["fiscal_year"]
        quarter = val["reporting_period"]["quarter"]
        if fy not in years:
            years[fy] = {}
        years[fy][quarter] = val["value"]
    
    for fy in sorted(years.keys(), reverse=True):
        print(f"\n    FY {fy}:")
        quarters = years[fy]
        for q in [1, 2, 3, 4]:
            if q in quarters:
                calculated = ""
                # Check if Q4 is calculated
                if q == 4:
                    q4_val = db.concept_values_quarterly.find_one({
                        "concept_id": concept["_id"],
                        "company_cik": cik,
                        "reporting_period.fiscal_year": fy,
                        "reporting_period.quarter": 4
                    })
                    if q4_val and q4_val.get("calculated"):
                        calculated = " [CALCULATED]"
                print(f"      Q{q}: {quarters[q]:,.2f}{calculated}")
        
        # Calculate what Q4 should be if we have annual
        annual_val = db.concept_values_annual.find_one({
            "concept_id": concept["_id"],
            "company_cik": cik,
            "reporting_period.fiscal_year": fy
        })
        
        if annual_val:
            print(f"      Annual: {annual_val['value']:,.2f}")
            
            if 1 in quarters and 2 in quarters and 3 in quarters:
                q1_q2_q3_sum = quarters[1] + quarters[2] + quarters[3]
                expected_q4 = annual_val['value'] - q1_q2_q3_sum
                print(f"      Expected Q4: {expected_q4:,.2f} (Annual - Q1 - Q2 - Q3)")
                
                if 4 in quarters:
                    actual_q4 = quarters[4]
                    diff = actual_q4 - expected_q4
                    if abs(diff) > 0.01:
                        print(f"      ⚠️  MISMATCH! Actual Q4 = {actual_q4:,.2f}, Difference = {diff:,.2f}")
                    else:
                        print(f"      ✓ Q4 matches expected value")

print("\n" + "=" * 80)
