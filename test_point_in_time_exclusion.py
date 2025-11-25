"""Test that point-in-time concepts are properly excluded from Q4 calculations."""

from pymongo import MongoClient
from services.q4_calculation_service import Q4CalculationService
from repositories.financial_repository import FinancialDataRepository

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["normalize_data"]

# Test company: Netflix
cik = "0001065280"
fiscal_year = 2024

# Initialize service
repository = FinancialDataRepository(db)
service = Q4CalculationService(repository)

# Point-in-time concepts that should be skipped
point_in_time_concepts = [
    {
        "concept_name": "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        "label": "Cash, Cash Equivalents, Restricted Cash and Restricted Cash Equivalents",
        "expected_skip": True
    },
    {
        "concept_name": "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsIncludingDisposalGroupAndDiscontinuedOperations",
        "label": "Cash, Cash Equivalents, Restricted Cash and Restricted Cash Equivalents, Including Disposal Group and Discontinued Operations",
        "expected_skip": True
    },
    {
        "concept_name": "WeightedAverageNumberOfSharesOutstandingBasic",
        "label": "Weighted Average Number of Shares Outstanding, Basic",
        "expected_skip": False  # This is NOT point-in-time
    },
    {
        "concept_name": "RevenueFromContractWithCustomerExcludingAssessedTax",
        "label": "Revenue from Contract with Customer, Excluding Assessed Tax",
        "expected_skip": False  # This is NOT point-in-time
    }
]

print("Testing point-in-time concept exclusion...\n")

for test_case in point_in_time_concepts:
    concept_name = test_case["concept_name"]
    label = test_case["label"]
    expected_skip = test_case["expected_skip"]
    
    # Test the _is_point_in_time_concept method directly
    is_point_in_time = service._is_point_in_time_concept(concept_name, label)
    
    status = "✅" if is_point_in_time == expected_skip else "❌"
    action = "SKIP" if is_point_in_time else "CALCULATE"
    
    print(f"{status} {concept_name}")
    print(f"   Label: {label}")
    print(f"   Expected: {'SKIP' if expected_skip else 'CALCULATE'}, Got: {action}")
    print(f"   Is point-in-time: {is_point_in_time}")
    print()

# Now test actual Q4 calculation for a point-in-time concept
print("=" * 80)
print("Testing actual Q4 calculation with point-in-time concept...")
print("=" * 80)

# Get a point-in-time concept from Netflix
cash_concept = db.normalized_concepts_quarterly.find_one({
    "company_cik": cik,
    "fiscal_year": fiscal_year,
    "concept_name": {"$regex": "CashCashEquivalents", "$options": "i"}
})

if cash_concept:
    print(f"\nTesting Q4 calculation for: {cash_concept['concept_name']}")
    print(f"Label: {cash_concept.get('label', 'N/A')}")
    print(f"Path: {cash_concept.get('path', 'N/A')}")
    
    # Try to calculate Q4
    result = service._calculate_q4_generic(
        concept_name=cash_concept['concept_name'],
        concept_path=cash_concept['path'],
        company_cik=cik,
        fiscal_year=fiscal_year,
        statement_type=cash_concept.get('statement_type', 'cash_flows'),
        quarterly_concept=cash_concept
    )
    
    print(f"\nResult: {result}")
    
    if not result["success"] and "Point-in-time" in result.get("reason", ""):
        print("✅ Point-in-time concept correctly SKIPPED")
    else:
        print("❌ Point-in-time concept was NOT skipped properly!")
else:
    print("⚠️ Could not find cash concept for testing")

# Test a regular flow concept to ensure it's NOT skipped
print("\n" + "=" * 80)
print("Testing that regular flow concepts are NOT excluded...")
print("=" * 80)

revenue_concept = db.normalized_concepts_quarterly.find_one({
    "company_cik": cik,
    "fiscal_year": fiscal_year,
    "concept_name": {"$regex": "Revenue", "$options": "i"}
})

if revenue_concept:
    print(f"\nTesting Q4 calculation for: {revenue_concept['concept_name']}")
    print(f"Label: {revenue_concept.get('label', 'N/A')}")
    print(f"Path: {revenue_concept.get('path', 'N/A')}")
    
    # Try to calculate Q4
    result = service._calculate_q4_generic(
        concept_name=revenue_concept['concept_name'],
        concept_path=revenue_concept['path'],
        company_cik=cik,
        fiscal_year=fiscal_year,
        statement_type=revenue_concept.get('statement_type', 'income_statement'),
        quarterly_concept=revenue_concept
    )
    
    print(f"\nResult: {result}")
    
    if result["success"] or "Point-in-time" not in result.get("reason", ""):
        print("✅ Regular flow concept correctly NOT skipped")
    else:
        print("❌ Regular flow concept was incorrectly skipped!")
else:
    print("⚠️ Could not find revenue concept for testing")

print("\n" + "=" * 80)
print("Test complete!")
print("=" * 80)
