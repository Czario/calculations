"""Check Q4 status for the 4 Netflix regional streaming concepts."""

from pymongo import MongoClient
from repositories.financial_repository import FinancialDataRepository

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["normalize_data"]

repository = FinancialDataRepository(db)

cik = "0001065280"  # Netflix
fiscal_year = 2024

print("=" * 80)
print("NETFLIX REGIONAL STREAMING REVENUE - Q4 STATUS")
print("=" * 80)

# The 4 regional members
regions = [
    {"name": "UCAN", "member": "nflx:UnitedStatesAndCanadaMember"},
    {"name": "EMEA", "member": "us-gaap:EMEAMember"},
    {"name": "LATAM", "member": "srt:LatinAmericaMember"},
    {"name": "APAC", "member": "srt:AsiaPacificMember"}
]

concept_name = "nflx:StreamingMember"
path = "001.001.001"

for region in regions:
    print(f"\n{region['name']} - {region['member']}")
    print("-" * 80)
    
    # Find the concept
    concept = db.normalized_concepts_quarterly.find_one({
        "company_cik": cik,
        "concept": concept_name,
        "path": path,
        "dimensions.explicitMember": region["member"]
    })
    
    if not concept:
        print(f"  ❌ Concept not found")
        continue
    
    print(f"  Concept ID: {concept['_id']}")
    print(f"  Statement: {concept.get('statement_type', 'N/A')}")
    
    # Get quarterly data
    quarterly_data = repository.get_quarterly_data_by_concept_id(
        concept["_id"], cik, fiscal_year, concept.get("statement_type", "income_statement")
    )
    
    print(f"\n  Quarterly Data for FY{fiscal_year}:")
    print(f"    Q1: {quarterly_data.q1_value:,.0f}" if quarterly_data.q1_value else "    Q1: None")
    print(f"    Q2: {quarterly_data.q2_value:,.0f}" if quarterly_data.q2_value else "    Q2: None")
    print(f"    Q3: {quarterly_data.q3_value:,.0f}" if quarterly_data.q3_value else "    Q3: None")
    print(f"    Annual: {quarterly_data.annual_value:,.0f}" if quarterly_data.annual_value else "    Annual: None")
    
    # Check if Q4 exists
    q4_record = db.concept_values_quarterly.find_one({
        "concept_id": concept["_id"],
        "company_cik": cik,
        "reporting_period.fiscal_year": fiscal_year,
        "reporting_period.quarter": 4
    })
    
    if q4_record:
        print(f"\n  ✅ Q4 EXISTS: {q4_record['value']:,.0f}")
        if quarterly_data.can_calculate_q4():
            expected = quarterly_data.calculate_q4()
            if abs(q4_record['value'] - expected) < 0.01:
                print(f"     Correct! (Annual - Q1 - Q2 - Q3 = {expected:,.0f})")
            else:
                print(f"     ❌ WRONG! Should be: {expected:,.0f}")
                print(f"     Difference: {q4_record['value'] - expected:,.0f}")
    else:
        print(f"\n  ❌ Q4 DOES NOT EXIST")
        if quarterly_data.can_calculate_q4():
            expected = quarterly_data.calculate_q4()
            print(f"     Should create Q4 = {expected:,.0f}")
            print(f"     (Annual {quarterly_data.annual_value:,.0f} - Q1 {quarterly_data.q1_value:,.0f} - Q2 {quarterly_data.q2_value:,.0f} - Q3 {quarterly_data.q3_value:,.0f})")
        else:
            missing = []
            if quarterly_data.q1_value is None: missing.append("Q1")
            if quarterly_data.q2_value is None: missing.append("Q2")
            if quarterly_data.q3_value is None: missing.append("Q3")
            if quarterly_data.annual_value is None: missing.append("Annual")
            print(f"     Cannot calculate - Missing: {', '.join(missing)}")

# Check total Q4 count for all regional concepts
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

total_regional_q4 = 0
for region in regions:
    concept = db.normalized_concepts_quarterly.find_one({
        "company_cik": cik,
        "concept": concept_name,
        "path": path,
        "dimensions.explicitMember": region["member"]
    })
    
    if concept:
        q4_count = db.concept_values_quarterly.count_documents({
            "concept_id": concept["_id"],
            "company_cik": cik,
            "reporting_period.quarter": 4
        })
        total_regional_q4 += q4_count
        print(f"\n{region['name']}: {q4_count} Q4 values")

print(f"\nTotal Q4 values across all 4 regions: {total_regional_q4}")
print(f"Expected (4 regions × ~16 years): ~64")
