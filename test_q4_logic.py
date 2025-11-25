"""Check if point-in-time Q4 values match what they should be."""

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
print("TESTING POINT-IN-TIME CONCEPT Q4 CREATION")
print("=" * 80)

# Test with a specific point-in-time concept
concept_name = "us-gaap:CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"

# Get the concept
concept = db.normalized_concepts_quarterly.find_one({
    "company_cik": cik,
    "concept": concept_name,
    "statement_type": "cash_flows"
})

if not concept:
    print(f"❌ Concept not found")
else:
    print(f"\nConcept: {concept_name}")
    print(f"Concept ID: {concept['_id']}")
    
    # Get quarterly data
    quarterly_data = repository.get_quarterly_data_by_concept_id(
        concept["_id"], cik, fiscal_year, "cash_flows"
    )
    
    print(f"\nQuarterly Data:")
    print(f"  Q1: {quarterly_data.q1_value}")
    print(f"  Q2: {quarterly_data.q2_value}")
    print(f"  Q3: {quarterly_data.q3_value}")
    print(f"  Annual: {quarterly_data.annual_value}")
    
    # Check if it's point-in-time
    is_point_in_time = service._is_point_in_time_concept(concept_name, concept.get("label", ""))
    print(f"\nIs point-in-time: {is_point_in_time}")
    
    # Get existing Q4 value
    q4_record = db.concept_values_quarterly.find_one({
        "concept_id": concept["_id"],
        "company_cik": cik,
        "reporting_period.fiscal_year": fiscal_year,
        "reporting_period.quarter": 4
    })
    
    if q4_record:
        print(f"\nExisting Q4 value: {q4_record['value']:,.2f}")
        print(f"Calculated flag: {q4_record.get('calculated', False)}")
        
        if quarterly_data.annual_value:
            if abs(q4_record['value'] - quarterly_data.annual_value) < 0.01:
                print(f"✅ Q4 = Annual ({quarterly_data.annual_value:,.2f}) - CORRECT for point-in-time")
            else:
                calc_q4 = quarterly_data.annual_value - (quarterly_data.q1_value or 0) - (quarterly_data.q2_value or 0) - (quarterly_data.q3_value or 0)
                if abs(q4_record['value'] - calc_q4) < 0.01:
                    print(f"⚠️ Q4 = Annual - (Q1+Q2+Q3) = {calc_q4:,.2f} - WRONG for point-in-time!")
                    print(f"   Should be: {quarterly_data.annual_value:,.2f}")
                else:
                    print(f"❓ Q4 value doesn't match expected patterns")
    else:
        print(f"\n❌ No Q4 value found")

# Test a flow concept to ensure it's still calculated correctly
print("\n" + "=" * 80)
print("TESTING FLOW CONCEPT Q4 CALCULATION")
print("=" * 80)

flow_concept = db.normalized_concepts_quarterly.find_one({
    "company_cik": cik,
    "concept": {"$regex": "Revenue", "$options": "i"},
    "statement_type": "income_statement"
})

if flow_concept:
    concept_name = flow_concept.get("concept", "")
    print(f"\nConcept: {concept_name}")
    
    quarterly_data = repository.get_quarterly_data_by_concept_id(
        flow_concept["_id"], cik, fiscal_year, "income_statement"
    )
    
    print(f"\nQuarterly Data:")
    print(f"  Q1: {quarterly_data.q1_value}")
    print(f"  Q2: {quarterly_data.q2_value}")
    print(f"  Q3: {quarterly_data.q3_value}")
    print(f"  Annual: {quarterly_data.annual_value}")
    
    is_point_in_time = service._is_point_in_time_concept(concept_name, flow_concept.get("label", ""))
    print(f"\nIs point-in-time: {is_point_in_time}")
    
    q4_record = db.concept_values_quarterly.find_one({
        "concept_id": flow_concept["_id"],
        "company_cik": cik,
        "reporting_period.fiscal_year": fiscal_year,
        "reporting_period.quarter": 4
    })
    
    if q4_record and quarterly_data.can_calculate_q4():
        expected_q4 = quarterly_data.calculate_q4()
        print(f"\nQ4 value: {q4_record['value']:,.2f}")
        print(f"Expected Q4 (Annual - Q1 - Q2 - Q3): {expected_q4:,.2f}")
        
        if abs(q4_record['value'] - expected_q4) < 0.01:
            print(f"✅ Q4 calculated correctly for flow concept")
        else:
            print(f"❌ Q4 calculation mismatch!")
