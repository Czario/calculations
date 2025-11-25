"""Test to ensure dimensional concept Q4 calculation is always correct."""

from pymongo import MongoClient
from services.q4_calculation_service import Q4CalculationService
from repositories.financial_repository import FinancialDataRepository

client = MongoClient("mongodb://localhost:27017/")
db = client["normalize_data"]

repository = FinancialDataRepository(db)
service = Q4CalculationService(repository)

cik = "0001065280"  # Netflix
fiscal_year = 2024

print("=" * 80)
print("TEST: DIMENSIONAL CONCEPT Q4 CALCULATION ACCURACY")
print("=" * 80)

# Test Netflix's 4 regional streaming concepts (they all share path 001.001.001)
concept_name = "nflx:StreamingMember"
path = "001.001.001"

regions = [
    {"name": "UCAN", "member": "nflx:UnitedStatesAndCanadaMember"},
    {"name": "EMEA", "member": "us-gaap:EMEAMember"},
    {"name": "LATAM", "member": "srt:LatinAmericaMember"},
    {"name": "APAC", "member": "srt:AsiaPacificMember"}
]

print("\nTesting 4 regions that share the same path but differ by dimension member:")
print(f"  Concept: {concept_name}")
print(f"  Path: {path}")

all_passed = True

for region in regions:
    print(f"\n{'='*80}")
    print(f"Testing: {region['name']} ({region['member']})")
    print(f"{'='*80}")
    
    # Get quarterly concept
    quarterly_concept = db.normalized_concepts_quarterly.find_one({
        "company_cik": cik,
        "concept": concept_name,
        "path": path,
        "dimensions.explicitMember": region["member"]
    })
    
    if not quarterly_concept:
        print(f"❌ FAIL: Quarterly concept not found")
        all_passed = False
        continue
    
    # Get annual concept using the repository's matching logic
    annual_concept = repository._find_matching_annual_concept(
        concept_name,
        cik,
        "income_statement",
        quarterly_concept=quarterly_concept
    )
    
    if not annual_concept:
        print(f"❌ FAIL: Annual concept not found")
        all_passed = False
        continue
    
    # Verify annual concept has the SAME dimension member
    quarterly_member = quarterly_concept.get("dimensions", {}).get("explicitMember")
    annual_member = annual_concept.get("dimensions", {}).get("explicitMember")
    
    print(f"\nDimension Member Matching:")
    print(f"  Quarterly: {quarterly_member}")
    print(f"  Annual:    {annual_member}")
    
    if quarterly_member != annual_member:
        print(f"  ❌ FAIL: Dimension members don't match!")
        all_passed = False
        continue
    else:
        print(f"  ✅ PASS: Dimension members match")
    
    # Get quarterly data
    quarterly_data = repository.get_quarterly_data_by_concept_id(
        quarterly_concept["_id"], cik, fiscal_year, "income_statement"
    )
    
    # Get annual value from the matched annual concept
    annual_value_record = db.concept_values_annual.find_one({
        "concept_id": annual_concept["_id"],
        "company_cik": cik,
        "reporting_period.fiscal_year": fiscal_year
    })
    
    if not annual_value_record:
        print(f"  ⚠️ No annual value for FY{fiscal_year}")
        continue
    
    print(f"\nData Values:")
    print(f"  Q1:     {quarterly_data.q1_value:>15,.0f}")
    print(f"  Q2:     {quarterly_data.q2_value:>15,.0f}")
    print(f"  Q3:     {quarterly_data.q3_value:>15,.0f}")
    print(f"  Annual: {annual_value_record['value']:>15,.0f}")
    
    # Verify annual value matches what the repository found
    if quarterly_data.annual_value != annual_value_record['value']:
        print(f"  ❌ FAIL: Repository's annual value doesn't match database!")
        print(f"     Repository: {quarterly_data.annual_value:,.0f}")
        print(f"     Database:   {annual_value_record['value']:,.0f}")
        all_passed = False
        continue
    else:
        print(f"  ✅ PASS: Repository found correct annual value")
    
    # Check Q4 calculation
    if quarterly_data.can_calculate_q4():
        expected_q4 = quarterly_data.calculate_q4()
        
        # Get actual Q4 from database
        q4_record = db.concept_values_quarterly.find_one({
            "concept_id": quarterly_concept["_id"],
            "company_cik": cik,
            "reporting_period.fiscal_year": fiscal_year,
            "reporting_period.quarter": 4
        })
        
        if q4_record:
            actual_q4 = q4_record['value']
            print(f"\nQ4 Calculation:")
            print(f"  Expected: {expected_q4:>15,.0f}")
            print(f"  Actual:   {actual_q4:>15,.0f}")
            
            if abs(actual_q4 - expected_q4) < 0.01:
                print(f"  ✅ PASS: Q4 calculated correctly!")
            else:
                print(f"  ❌ FAIL: Q4 calculation is WRONG!")
                print(f"     Difference: {actual_q4 - expected_q4:,.0f}")
                all_passed = False
        else:
            print(f"  ⚠️ No Q4 value in database")

print(f"\n{'='*80}")
print("TEST SUMMARY")
print(f"{'='*80}")

if all_passed:
    print("\n✅ ALL TESTS PASSED!")
    print("\nDimensional concept matching is working correctly:")
    print("  • Each quarterly concept matches to its correct annual concept")
    print("  • Dimension members are matched properly")
    print("  • Q4 calculations use the correct annual values")
    print("  • No cross-contamination between regions")
else:
    print("\n❌ SOME TESTS FAILED!")
    print("\nPlease review the failures above.")
