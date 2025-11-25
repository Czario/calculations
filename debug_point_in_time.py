from services.q4_calculation_service import Q4CalculationService
from repositories.financial_repository import FinancialDataRepository
from pymongo import MongoClient

db = MongoClient('mongodb://localhost:27017/')['normalize_data']
repository = FinancialDataRepository(db)
service = Q4CalculationService(repository)

# Test specific concepts
test_cases = [
    {
        "concept": "us-gaap:WeightedAverageNumberOfSharesOutstandingBasic",
        "label": "Common Class A [Member]",
        "should_skip": True
    },
    {
        "concept": "custom:BuildingsAndImprovements",
        "label": "Cash",
        "should_skip": True  # Label says Cash
    },
    {
        "concept": "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax",
        "label": "Revenue",
        "should_skip": False
    },
    {
        "concept": "us-gaap:CashAndCashEquivalentsAtCarryingValue",
        "label": "Cash and cash equivalents",
        "should_skip": True
    }
]

print("Testing point-in-time detection:")
print("=" * 80)

for test in test_cases:
    result = service._is_point_in_time_concept(test["concept"], test["label"])
    expected = "SKIP" if test["should_skip"] else "CALCULATE"
    actual = "SKIP" if result else "CALCULATE"
    status = "✅" if (result == test["should_skip"]) else "❌"
    
    print(f"\n{status} Concept: {test['concept']}")
    print(f"   Label: {test['label']}")
    print(f"   Expected: {expected}, Got: {actual}")
    
    # Debug: Check which pattern matched
    if result:
        for pattern in service.POINT_IN_TIME_PATTERNS:
            if pattern.lower() in test["concept"].lower() or (test["label"] and pattern.lower() in test["label"].lower()):
                print(f"   Matched pattern: '{pattern}'")
                break
