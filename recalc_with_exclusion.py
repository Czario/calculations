"""Recalculate Q4 for all companies with point-in-time concept exclusion."""

from pymongo import MongoClient
from services.q4_calculation_service import Q4CalculationService
from repositories.financial_repository import FinancialDataRepository

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["normalize_data"]

companies = [
    {"cik": "0000320193", "name": "Apple"},
    {"cik": "0000789019", "name": "Microsoft"},
    {"cik": "0001065280", "name": "Netflix"},
    {"cik": "0001326801", "name": "Meta"}
]

fiscal_year = 2024

print("=" * 80)
print("Q4 RECALCULATION WITH POINT-IN-TIME EXCLUSION")
print("=" * 80)

# Step 1: Delete all existing Q4 values
print("\nStep 1: Deleting all existing Q4 values...")
for company in companies:
    result = db.concept_values_quarterly.delete_many({
        "company_cik": company["cik"],
        "fiscal_year": fiscal_year,
        "fiscal_period": "Q4"
    })
    print(f"  {company['name']}: Deleted {result.deleted_count} Q4 values")

# Step 2: Count quarterly concepts BEFORE recalculation
print("\nStep 2: Counting quarterly concepts before recalculation...")
for company in companies:
    income_count = db.normalized_concepts_quarterly.count_documents({
        "company_cik": company["cik"],
        "fiscal_year": fiscal_year,
        "statement_type": "income_statement"
    })
    cash_count = db.normalized_concepts_quarterly.count_documents({
        "company_cik": company["cik"],
        "fiscal_year": fiscal_year,
        "statement_type": "cash_flows"
    })
    print(f"  {company['name']}: {income_count} income statement + {cash_count} cash flows = {income_count + cash_count} total concepts")

# Step 3: Recalculate Q4 for all companies
print("\nStep 3: Recalculating Q4 for all companies...")
repository = FinancialDataRepository(db)
service = Q4CalculationService(repository)

for company in companies:
    print(f"\n  Processing {company['name']} (CIK: {company['cik']})...")
    
    # Calculate for income statement
    income_results = service.calculate_q4_for_company(company["cik"])
    print(f"    Income Statement: {income_results['successful_calculations']} calculated, {income_results['skipped_concepts']} skipped")
    
    # Calculate for cash flows
    cash_results = service.calculate_q4_for_cash_flow(company["cik"])
    print(f"    Cash Flows: {cash_results['successful_calculations']} calculated, {cash_results['skipped_concepts']} skipped")
    
    # Show errors if any
    all_errors = income_results.get('errors', []) + cash_results.get('errors', [])
    if all_errors:
        print(f"    Errors: {len(all_errors)}")
        for error in all_errors[:3]:  # Show first 3 errors
            print(f"      - {error}")

# Step 4: Verify final Q4 counts and check for point-in-time concepts
print("\n" + "=" * 80)
print("Step 4: Verification - Final Q4 counts")
print("=" * 80)

for company in companies:
    q4_count = db.concept_values_quarterly.count_documents({
        "company_cik": company["cik"],
        "fiscal_year": fiscal_year,
        "fiscal_period": "Q4"
    })
    print(f"\n{company['name']}: {q4_count} Q4 values")
    
    # Check for any point-in-time concepts in Q4 values
    point_in_time_patterns = [
        "CashCashEquivalents",
        "BeginningBalance",
        "EndingBalance",
        "BeginningOfYear",
        "EndOfYear",
        "BeginningOfPeriod",
        "EndOfPeriod"
    ]
    
    for pattern in point_in_time_patterns:
        # Get concepts matching pattern
        concepts_with_q4 = list(db.concept_values_quarterly.aggregate([
            {
                "$match": {
                    "company_cik": company["cik"],
                    "fiscal_year": fiscal_year,
                    "fiscal_period": "Q4"
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
                    "concept.concept_name": {"$regex": pattern, "$options": "i"}
                }
            },
            {
                "$project": {
                    "concept_name": "$concept.concept_name",
                    "label": "$concept.label"
                }
            }
        ]))
        
        if concepts_with_q4:
            print(f"  ⚠️ Found {len(concepts_with_q4)} Q4 values with pattern '{pattern}':")
            for concept in concepts_with_q4[:3]:  # Show max 3
                print(f"     - {concept['concept_name']}")

print("\n" + "=" * 80)
print("Recalculation complete!")
print("=" * 80)
