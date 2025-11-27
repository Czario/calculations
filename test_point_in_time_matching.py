"""Test point-in-time pattern matching."""

from services.q4_calculation_service import Q4CalculationService

# Test concepts
test_concepts = [
    ("us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents", "Cash and Cash Equivalents"),
    ("us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding", "Weighted Average Shares"),
    ("us-gaap:WeightedAverageNumberOfSharesOutstandingBasic", "Basic Shares"),
    ("custom:CashCashEquivalentsAndRestrictedCashEndOfYear", "Cash at End of Year"),
    ("us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsPeriodIncreaseDecreaseIncludingExchangeRateEffect", "Period Increase"),
    ("us-gaap:EffectOfExchangeRateOnCashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents", "FX Effect"),
    ("us-gaap:Revenues", "Revenues")  # Should NOT be point-in-time
]

service = Q4CalculationService(None)

print("=" * 80)
print("TESTING POINT-IN-TIME PATTERN MATCHING")
print("=" * 80)

for concept_name, label in test_concepts:
    is_pit = service._is_point_in_time_concept(concept_name, label)
    status = "✓ DETECTED" if is_pit else "✗ NOT DETECTED"
    print(f"\n{status}: {concept_name}")
    print(f"  Label: {label}")

print("\n" + "=" * 80)
