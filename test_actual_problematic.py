"""Test the actual problematic concepts identified earlier."""

from pymongo import MongoClient
from services.q4_calculation_service import Q4CalculationService
from repositories.financial_repository import FinancialDataRepository

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["normalize_data"]

# Initialize service
repository = FinancialDataRepository(db)
service = Q4CalculationService(repository)

# These are the actual problematic concepts identified in check_point_in_time.py
problematic_concepts = {
    "Apple": [
        "us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        "us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsIncludingDisposalGroupAndDiscontinuedOperations"
    ],
    "Microsoft": [
        "us-gaap:WeightedAverageNumberOfSharesOutstandingBasic",
        "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding",
        "us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        "us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsIncludingDisposalGroupAndDiscontinuedOperations",
        "us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsPeriodIncreaseDecreaseIncludingExchangeRateEffect"
    ],
    "Netflix": [
        "us-gaap:WeightedAverageNumberOfSharesOutstandingBasic",
        "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding",
        "us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        "us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsPeriodIncreaseDecreaseIncludingExchangeRateEffect",
        "us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsPeriodIncreaseDecreaseExcludingExchangeRateEffect",
        "us-gaap:EffectOfExchangeRateOnCashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"
    ],
    "Meta": [
        "us-gaap:WeightedAverageNumberOfSharesOutstandingBasic",
        "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding",
        "us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        "us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsPeriodIncreaseDecreaseIncludingExchangeRateEffect",
        "us-gaap:EffectOfExchangeRateOnCashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"
    ]
}

print("=" * 80)
print("TESTING ACTUAL PROBLEMATIC CONCEPTS")
print("=" * 80)

total_concepts = 0
detected_count = 0
missed_count = 0

for company, concepts in problematic_concepts.items():
    print(f"\n{company}:")
    print("-" * 80)
    
    for concept_name in concepts:
        total_concepts += 1
        is_point_in_time = service._is_point_in_time_concept(concept_name, "")
        
        if is_point_in_time:
            detected_count += 1
            print(f"  ✅ DETECTED: {concept_name}")
        else:
            missed_count += 1
            print(f"  ❌ MISSED: {concept_name}")

print("\n" + "=" * 80)
print(f"SUMMARY:")
print(f"  Total problematic concepts: {total_concepts}")
print(f"  ✅ Correctly detected: {detected_count} ({detected_count/total_concepts*100:.1f}%)")
print(f"  ❌ Missed: {missed_count} ({missed_count/total_concepts*100:.1f}%)")
print("=" * 80)

if missed_count == 0:
    print("\n🎉 SUCCESS! All problematic concepts are now correctly detected!")
else:
    print(f"\n⚠️ WARNING: {missed_count} concepts still not detected")
