"""Test the annual concept matching for DomesticStreamingMember."""

from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database name from config
db_name = os.getenv("TARGET_DB_NAME", "normalize_data")

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client[db_name]

netflix_cik = "0001065280"
member_name = "nflx:DomesticStreamingMember"
path = "002.001"
statement = "income_statement"

print("=" * 100)
print(f"TESTING ANNUAL CONCEPT MATCHING FOR {member_name}")
print("=" * 100)

# Find the quarterly concept
quarterly_concept = db.normalized_concepts_quarterly.find_one({
    "company_cik": netflix_cik,
    "concept": member_name,
    "path": path,
    "statement_type": statement
})

print(f"\n📋 QUARTERLY CONCEPT:")
print(f"  Concept: {quarterly_concept.get('concept')}")
print(f"  Label: {quarterly_concept.get('label')}")
print(f"  Path: {quarterly_concept.get('path')}")
print(f"  Concept Name: {quarterly_concept.get('concept_name')}")
print(f"  Dimensions: {quarterly_concept.get('dimensions')}")

# Find all annual concepts with this name
annual_concepts = list(db.normalized_concepts_annual.find({
    "company_cik": netflix_cik,
    "concept": member_name,
    "statement_type": statement
}))

print(f"\n\n📋 ANNUAL CONCEPTS WITH SAME NAME ({len(annual_concepts)} found):")
for i, annual in enumerate(annual_concepts, 1):
    print(f"\n  {i}. Annual Concept:")
    print(f"     Concept: {annual.get('concept')}")
    print(f"     Label: {annual.get('label')}")
    print(f"     Path: {annual.get('path')}")
    print(f"     Concept Name: {annual.get('concept_name')}")
    print(f"     Dimensions: {annual.get('dimensions')}")
    
    # Check if this matches
    quarterly_member = quarterly_concept.get('dimensions', {}).get('explicitMember')
    annual_member = annual.get('dimensions', {}).get('explicitMember')
    
    if quarterly_member == annual_member:
        print(f"     ✅ MATCH BY EXPLICIT MEMBER!")
    
    if annual.get('path') == quarterly_concept.get('path'):
        print(f"     ✅ MATCH BY PATH!")
    
    # Get a sample annual value
    sample_value = db.concept_values_annual.find_one({
        "concept_id": annual["_id"],
        "company_cik": netflix_cik,
        "reporting_period.fiscal_year": 2019
    })
    
    if sample_value:
        print(f"     Sample FY2019 value: {sample_value['value']:,.2f}")

# Now check what the repository would actually return
print("\n\n" + "=" * 100)
print("TESTING REPOSITORY LOGIC")
print("=" * 100)

from config.database import DatabaseConfig, DatabaseConnection
from repositories.financial_repository import FinancialDataRepository

# Create repository
config = DatabaseConfig()
with DatabaseConnection(config) as database:
    repo = FinancialDataRepository(database)
    
    # Get quarterly data for FY2019
    quarterly_data = repo.get_quarterly_data_by_concept_id(
        quarterly_concept["_id"],
        netflix_cik,
        2019,
        statement
    )
    
    print(f"\n📊 RETRIEVED QUARTERLY DATA FOR FY2019:")
    q1_str = f"{quarterly_data.q1_value:,.2f}" if quarterly_data.q1_value is not None else "None"
    q2_str = f"{quarterly_data.q2_value:,.2f}" if quarterly_data.q2_value is not None else "None"
    q3_str = f"{quarterly_data.q3_value:,.2f}" if quarterly_data.q3_value is not None else "None"
    annual_str = f"{quarterly_data.annual_value:,.2f}" if quarterly_data.annual_value is not None else "None"
    
    print(f"  Q1: {q1_str}")
    print(f"  Q2: {q2_str}")
    print(f"  Q3: {q3_str}")
    print(f"  Annual: {annual_str}")
    
    if quarterly_data.can_calculate_q4():
        expected_q4 = quarterly_data.calculate_q4()
        print(f"  Expected Q4: {expected_q4:,.2f}")
        
        # Get actual Q4
        actual_q4_value = db.concept_values_quarterly.find_one({
            "concept_id": quarterly_concept["_id"],
            "company_cik": netflix_cik,
            "reporting_period.fiscal_year": 2019,
            "reporting_period.quarter": 4
        })
        
        if actual_q4_value:
            print(f"  Actual Q4 in DB: {actual_q4_value['value']:,.2f}")
            print(f"  Calculated: {actual_q4_value.get('calculated', False)}")
            if abs(actual_q4_value['value'] - expected_q4) > 0.01:
                print(f"  ⚠️  MISMATCH! Difference: {actual_q4_value['value'] - expected_q4:,.2f}")

print("\n" + "=" * 100)
