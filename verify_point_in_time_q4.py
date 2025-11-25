"""Verify that point-in-time concepts now have Q4 values copied from annual."""

from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["normalize_data"]

cik = "0001065280"  # Netflix
fiscal_year = 2024

print("=" * 80)
print("VERIFYING POINT-IN-TIME Q4 VALUES FOR NETFLIX")
print("=" * 80)

# Point-in-time concepts we identified earlier
point_in_time_concepts = [
    "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding",
    "us-gaap:WeightedAverageNumberOfSharesOutstandingBasic",
    "custom:CashCashEquivalentsAndRestrictedCashEndOfYear",
    "us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    "us-gaap:EffectOfExchangeRateOnCashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"
]

for concept_name in point_in_time_concepts:
    print(f"\n{concept_name}:")
    print("-" * 80)
    
    # Get the concept
    concept = db.normalized_concepts_quarterly.find_one({
        "company_cik": cik,
        "concept": concept_name
    })
    
    if not concept:
        print(f"  ⚠️ Concept not found in quarterly concepts")
        continue
    
    concept_id = concept["_id"]
    
    # Get annual value
    annual_value = db.concept_values_annual.find_one({
        "concept_id": concept_id,
        "company_cik": cik,
        "reporting_period.fiscal_year": fiscal_year
    })
    
    # Get Q4 value
    q4_value = db.concept_values_quarterly.find_one({
        "concept_id": concept_id,
        "company_cik": cik,
        "reporting_period.fiscal_year": fiscal_year,
        "reporting_period.quarter": 4
    })
    
    if annual_value:
        print(f"  Annual value: {annual_value['value']:,.2f}")
    else:
        print(f"  Annual value: NOT FOUND")
    
    if q4_value:
        print(f"  Q4 value: {q4_value['value']:,.2f}")
        print(f"  Calculated: {q4_value.get('calculated', False)}")
        
        if annual_value and abs(q4_value['value'] - annual_value['value']) < 0.01:
            print(f"  ✅ Q4 = Annual (correctly copied for point-in-time concept)")
        elif annual_value:
            print(f"  ❌ Q4 ≠ Annual (should be equal for point-in-time)")
            print(f"     Difference: {q4_value['value'] - annual_value['value']:,.2f}")
    else:
        print(f"  Q4 value: NOT FOUND")
        if annual_value:
            print(f"  ❌ Q4 should have been created from annual value")

# Count total point-in-time Q4 values created
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

total_point_in_time_q4 = 0
for concept_name in point_in_time_concepts:
    concept = db.normalized_concepts_quarterly.find_one({
        "company_cik": cik,
        "concept": concept_name
    })
    
    if concept:
        count = db.concept_values_quarterly.count_documents({
            "concept_id": concept["_id"],
            "company_cik": cik,
            "reporting_period.quarter": 4,
            "calculated": True
        })
        total_point_in_time_q4 += count

print(f"\nTotal Q4 values created for point-in-time concepts: {total_point_in_time_q4}")
print(f"Expected (5 concepts × 16 years): 80")

if total_point_in_time_q4 > 0:
    print(f"\n✅ Point-in-time Q4 values are being created!")
else:
    print(f"\n❌ No point-in-time Q4 values found")
