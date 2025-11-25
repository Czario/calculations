"""Investigate Netflix streaming member concepts (UCAN, EMEA, LATAM, APAC)."""

from pymongo import MongoClient
from services.q4_calculation_service import Q4CalculationService
from repositories.financial_repository import FinancialDataRepository

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["normalize_data"]

repository = FinancialDataRepository(db)
service = Q4CalculationService(repository)

cik = "0001065280"  # Netflix
fiscal_year = 2024

print("=" * 80)
print("INVESTIGATING NETFLIX STREAMING MEMBERS")
print("=" * 80)

# Find streaming member concepts
streaming_concepts = list(db.normalized_concepts_quarterly.find({
    "company_cik": cik,
    "dimensions.explicitMember": {"$regex": "StreamingMember|DomesticStreamingMember", "$options": "i"}
}))

print(f"\nFound {len(streaming_concepts)} streaming member concepts")

# Group by concept name
by_concept = {}
for concept in streaming_concepts:
    concept_name = concept.get("concept", "Unknown")
    if concept_name not in by_concept:
        by_concept[concept_name] = []
    by_concept[concept_name].append(concept)

print(f"Unique concept names: {len(by_concept)}")

# Check specific concept with DomesticStreamingMember
print("\n" + "=" * 80)
print("DOMESTIC STREAMING MEMBER CONCEPTS")
print("=" * 80)

domestic_concepts = [c for c in streaming_concepts if "DomesticStreaming" in str(c.get("dimensions", {}))]
print(f"\nFound {len(domestic_concepts)} domestic streaming concepts")

for concept in domestic_concepts[:5]:
    concept_name = concept.get("concept", "Unknown")
    path = concept.get("path", "N/A")
    label = concept.get("label", "N/A")
    dimensions = concept.get("dimensions", {})
    
    print(f"\nConcept: {concept_name}")
    print(f"Path: {path}")
    print(f"Label: {label}")
    print(f"Dimensions: {dimensions.get('explicitMember', 'None')}")
    print(f"Statement: {concept.get('statement_type', 'N/A')}")
    
    # Check if Q4 exists
    q4_exists = db.concept_values_quarterly.find_one({
        "concept_id": concept["_id"],
        "company_cik": cik,
        "reporting_period.fiscal_year": fiscal_year,
        "reporting_period.quarter": 4
    })
    
    # Get quarterly data
    quarterly_data = repository.get_quarterly_data_by_concept_id(
        concept["_id"], cik, fiscal_year, concept.get("statement_type", "income_statement")
    )
    
    print(f"\nQuarterly Data:")
    print(f"  Q1: {quarterly_data.q1_value}")
    print(f"  Q2: {quarterly_data.q2_value}")
    print(f"  Q3: {quarterly_data.q3_value}")
    print(f"  Annual: {quarterly_data.annual_value}")
    print(f"  Can calculate Q4: {quarterly_data.can_calculate_q4()}")
    
    if q4_exists:
        print(f"\n✅ Q4 exists: {q4_exists['value']:,.2f}")
        if quarterly_data.can_calculate_q4():
            expected = quarterly_data.calculate_q4()
            if abs(q4_exists['value'] - expected) < 0.01:
                print(f"   Matches expected: {expected:,.2f} ✓")
            else:
                print(f"   ❌ MISMATCH! Expected: {expected:,.2f}")
    else:
        print(f"\n❌ Q4 does NOT exist")
        if quarterly_data.can_calculate_q4():
            print(f"   Should be: {quarterly_data.calculate_q4():,.2f}")
        else:
            missing = []
            if quarterly_data.q1_value is None: missing.append("Q1")
            if quarterly_data.q2_value is None: missing.append("Q2")
            if quarterly_data.q3_value is None: missing.append("Q3")
            if quarterly_data.annual_value is None: missing.append("Annual")
            print(f"   Missing: {', '.join(missing)}")

# Check all 4 regions for revenue
print("\n" + "=" * 80)
print("REVENUE BY REGION (All 4 Streaming Members)")
print("=" * 80)

regions = ["UCAN", "EMEA", "LATAM", "APAC"]
revenue_concept = "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"

for region in regions:
    member_pattern = f"nflx:{region}StreamingMember"
    
    concept = db.normalized_concepts_quarterly.find_one({
        "company_cik": cik,
        "concept": revenue_concept,
        "dimensions.explicitMember": member_pattern
    })
    
    if concept:
        print(f"\n{region} ({member_pattern}):")
        print(f"  Path: {concept.get('path', 'N/A')}")
        
        quarterly_data = repository.get_quarterly_data_by_concept_id(
            concept["_id"], cik, fiscal_year, "income_statement"
        )
        
        print(f"  Q1: {quarterly_data.q1_value:,.0f}" if quarterly_data.q1_value else "  Q1: None")
        print(f"  Q2: {quarterly_data.q2_value:,.0f}" if quarterly_data.q2_value else "  Q2: None")
        print(f"  Q3: {quarterly_data.q3_value:,.0f}" if quarterly_data.q3_value else "  Q3: None")
        print(f"  Annual: {quarterly_data.annual_value:,.0f}" if quarterly_data.annual_value else "  Annual: None")
        
        q4_exists = db.concept_values_quarterly.find_one({
            "concept_id": concept["_id"],
            "company_cik": cik,
            "reporting_period.fiscal_year": fiscal_year,
            "reporting_period.quarter": 4
        })
        
        if q4_exists:
            print(f"  ✅ Q4: {q4_exists['value']:,.0f}")
            if quarterly_data.can_calculate_q4():
                expected = quarterly_data.calculate_q4()
                if abs(q4_exists['value'] - expected) < 0.01:
                    print(f"     Correct!")
                else:
                    print(f"     ❌ Should be: {expected:,.0f}")
        else:
            print(f"  ❌ Q4: NOT FOUND")
            if quarterly_data.can_calculate_q4():
                print(f"     Should create: {quarterly_data.calculate_q4():,.0f}")
    else:
        print(f"\n{region}: ❌ Concept not found")
