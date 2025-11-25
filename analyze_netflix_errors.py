"""Analyze the 64 'errors' in Netflix cash flows to verify they're point-in-time skips."""

from pymongo import MongoClient
from services.q4_calculation_service import Q4CalculationService
from repositories.financial_repository import FinancialDataRepository

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["normalize_data"]

# Initialize service
repository = FinancialDataRepository(db)
service = Q4CalculationService(repository)

cik = "0001065280"  # Netflix

print("=" * 80)
print("ANALYZING NETFLIX CASH FLOW 'ERRORS'")
print("=" * 80)

# Get cash flow concepts for Netflix
concepts = repository.get_cash_flow_concepts(cik)
print(f"\nTotal cash flow concepts: {len(concepts)}")

# Get fiscal years
fiscal_years = repository.get_fiscal_years_for_company(cik)
print(f"Fiscal years: {fiscal_years}")

# Categorize the errors
error_categories = {
    "point_in_time_skipped": [],
    "missing_data": [],
    "already_exists": [],
    "other": []
}

for concept in concepts:
    concept_name = concept.get("concept", "Unknown")
    concept_path = concept.get("path", "")
    label = concept.get("label", "")
    
    for fiscal_year in fiscal_years:
        result = service._calculate_q4_generic(
            concept_name,
            concept_path,
            cik,
            fiscal_year,
            "cash_flows",
            quarterly_concept=concept
        )
        
        if not result["success"]:
            reason = result.get("reason", "")
            
            if "Point-in-time" in reason:
                error_categories["point_in_time_skipped"].append({
                    "concept": concept_name,
                    "year": fiscal_year,
                    "reason": reason
                })
            elif "Missing values" in reason or "not found" in reason:
                error_categories["missing_data"].append({
                    "concept": concept_name,
                    "year": fiscal_year,
                    "reason": reason
                })
            elif "already exists" in reason:
                error_categories["already_exists"].append({
                    "concept": concept_name,
                    "year": fiscal_year,
                    "reason": reason
                })
            else:
                error_categories["other"].append({
                    "concept": concept_name,
                    "year": fiscal_year,
                    "reason": reason
                })

print("\n" + "=" * 80)
print("ERROR BREAKDOWN")
print("=" * 80)

print(f"\n🚫 Point-in-time concepts (correctly skipped): {len(error_categories['point_in_time_skipped'])}")
if error_categories['point_in_time_skipped']:
    # Group by concept
    concepts_skipped = {}
    for item in error_categories['point_in_time_skipped']:
        concept = item['concept']
        if concept not in concepts_skipped:
            concepts_skipped[concept] = []
        concepts_skipped[concept].append(item['year'])
    
    print(f"\n  Unique concepts skipped: {len(concepts_skipped)}")
    for concept, years in concepts_skipped.items():
        print(f"    • {concept}")
        print(f"      Years: {sorted(years)}")

print(f"\n⚠️  Missing data: {len(error_categories['missing_data'])}")
if error_categories['missing_data'] and len(error_categories['missing_data']) <= 10:
    for item in error_categories['missing_data'][:5]:
        print(f"    • {item['concept']} (FY{item['year']}): {item['reason']}")

print(f"\n⏭️  Already exists: {len(error_categories['already_exists'])}")

print(f"\n❓ Other: {len(error_categories['other'])}")
if error_categories['other']:
    for item in error_categories['other'][:5]:
        print(f"    • {item['concept']} (FY{item['year']}): {item['reason']}")

# Calculate expected error count
total_errors = sum(len(v) for v in error_categories.values())
print(f"\n" + "=" * 80)
print(f"TOTAL 'ERRORS': {total_errors}")
print("=" * 80)

if len(error_categories['point_in_time_skipped']) == 64:
    print("\n✅ ALL 64 'errors' are point-in-time concepts being correctly skipped!")
    print("   These are NOT actual errors - the system is working as designed.")
elif len(error_categories['point_in_time_skipped']) > 0:
    print(f"\n✅ {len(error_categories['point_in_time_skipped'])} of the 'errors' are point-in-time concepts (expected)")
    print(f"⚠️  {total_errors - len(error_categories['point_in_time_skipped'])} are other types of issues")
