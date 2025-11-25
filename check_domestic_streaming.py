"""Check specific Netflix DomesticStreamingMember concepts."""

from pymongo import MongoClient
from repositories.financial_repository import FinancialDataRepository

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["normalize_data"]

repository = FinancialDataRepository(db)

cik = "0001065280"  # Netflix
fiscal_year = 2024

print("=" * 80)
print("NETFLIX DOMESTIC STREAMING MEMBER - SPECIFIC PATHS")
print("=" * 80)

# The two specific paths mentioned
paths_to_check = [
    "001.001.005.001",
    "002.001"
]

for path in paths_to_check:
    print(f"\n{'='*80}")
    print(f"PATH: {path}")
    print(f"{'='*80}")
    
    # Find concept with this path
    concept = db.normalized_concepts_quarterly.find_one({
        "company_cik": cik,
        "dimensions.explicitMember": "nflx:DomesticStreamingMember",
        "path": path
    })
    
    if not concept:
        print(f"❌ Concept not found with path {path}")
        
        # Check if path exists without the member filter
        any_concept = db.normalized_concepts_quarterly.find_one({
            "company_cik": cik,
            "path": path
        })
        if any_concept:
            print(f"   But found concept at this path:")
            print(f"   Concept: {any_concept.get('concept', 'N/A')}")
            print(f"   Label: {any_concept.get('label', 'N/A')}")
            print(f"   Dimensions: {any_concept.get('dimensions', {})}")
        continue
    
    concept_name = concept.get("concept", "Unknown")
    label = concept.get("label", "N/A")
    statement_type = concept.get("statement_type", "N/A")
    
    print(f"\nConcept: {concept_name}")
    print(f"Label: {label}")
    print(f"Statement: {statement_type}")
    print(f"Path: {path}")
    print(f"Member: {concept.get('dimensions', {}).get('explicitMember', 'None')}")
    
    # Get quarterly data
    quarterly_data = repository.get_quarterly_data_by_concept_id(
        concept["_id"], cik, fiscal_year, statement_type
    )
    
    print(f"\nQuarterly Data for FY{fiscal_year}:")
    print(f"  Q1: {quarterly_data.q1_value:,.0f}" if quarterly_data.q1_value else "  Q1: None")
    print(f"  Q2: {quarterly_data.q2_value:,.0f}" if quarterly_data.q2_value else "  Q2: None")
    print(f"  Q3: {quarterly_data.q3_value:,.0f}" if quarterly_data.q3_value else "  Q3: None")
    print(f"  Annual: {quarterly_data.annual_value:,.0f}" if quarterly_data.annual_value else "  Annual: None")
    print(f"  Can calculate Q4: {quarterly_data.can_calculate_q4()}")
    
    # Check if Q4 exists
    q4_record = db.concept_values_quarterly.find_one({
        "concept_id": concept["_id"],
        "company_cik": cik,
        "reporting_period.fiscal_year": fiscal_year,
        "reporting_period.quarter": 4
    })
    
    if q4_record:
        print(f"\n✅ Q4 EXISTS: {q4_record['value']:,.0f}")
        if quarterly_data.can_calculate_q4():
            expected = quarterly_data.calculate_q4()
            if abs(q4_record['value'] - expected) < 0.01:
                print(f"   Correct calculation!")
            else:
                print(f"   ❌ MISMATCH! Expected: {expected:,.0f}")
    else:
        print(f"\n❌ Q4 DOES NOT EXIST")
        if quarterly_data.can_calculate_q4():
            expected = quarterly_data.calculate_q4()
            print(f"   Should be created: {expected:,.0f}")
        else:
            missing = []
            if quarterly_data.q1_value is None: missing.append("Q1")
            if quarterly_data.q2_value is None: missing.append("Q2")
            if quarterly_data.q3_value is None: missing.append("Q3")
            if quarterly_data.annual_value is None: missing.append("Annual")
            print(f"   Missing data: {', '.join(missing)}")
    
    # Check all years for this concept
    all_q4 = db.concept_values_quarterly.count_documents({
        "concept_id": concept["_id"],
        "company_cik": cik,
        "reporting_period.quarter": 4
    })
    
    all_values = db.concept_values_quarterly.count_documents({
        "concept_id": concept["_id"],
        "company_cik": cik
    })
    
    print(f"\nHistorical data:")
    print(f"  Total quarterly values: {all_values}")
    print(f"  Q4 values: {all_q4}")

# Also find ALL DomesticStreamingMember concepts regardless of path
print(f"\n{'='*80}")
print("ALL DOMESTIC STREAMING MEMBER CONCEPTS")
print(f"{'='*80}")

all_domestic = list(db.normalized_concepts_quarterly.find({
    "company_cik": cik,
    "dimensions.explicitMember": "nflx:DomesticStreamingMember"
}))

print(f"\nFound {len(all_domestic)} DomesticStreamingMember concepts:")

for concept in all_domestic:
    path = concept.get("path", "N/A")
    concept_name = concept.get("concept", "N/A")
    statement = concept.get("statement_type", "N/A")
    
    # Count values
    value_count = db.concept_values_quarterly.count_documents({
        "concept_id": concept["_id"],
        "company_cik": cik
    })
    
    q4_count = db.concept_values_quarterly.count_documents({
        "concept_id": concept["_id"],
        "company_cik": cik,
        "reporting_period.quarter": 4
    })
    
    print(f"\n  Path {path} ({statement}):")
    print(f"    Concept: {concept_name}")
    print(f"    Total values: {value_count}, Q4 values: {q4_count}")
