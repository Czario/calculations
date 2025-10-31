#!/usr/bin/env python3

from config.database import DatabaseConfig, DatabaseConnection
from repositories.financial_repository import FinancialDataRepository
from services.q4_calculation_service import Q4CalculationService

def test_dimensional_concept_fix():
    """Test that dimensional concepts use correct annual values (not parent values)."""
    
    # Set up connections
    config = DatabaseConfig()
    connection = DatabaseConnection(config)
    db = connection.connect()
    repository = FinancialDataRepository(db)
    service = Q4CalculationService(repository)
    
    print("=== TESTING DIMENSIONAL CONCEPT FIX ===")
    
    # Test with Microsoft Gaming Member (we know this works)
    company_cik = "0000789019"
    fiscal_year = 2024
    
    # Test the Gaming Member (dimensional concept)
    print("\n1. Testing Gaming Member (dimensional concept):")
    gaming_concept = "msft:GamingMember"
    gaming_path = "001.001"
    
    quarterly_data = repository.get_quarterly_data_for_concept_by_name_and_path(
        gaming_concept, gaming_path, company_cik, fiscal_year, "income_statement"
    )
    
    print(f"   Concept: {gaming_concept}")
    print(f"   Path: {gaming_path}")
    print(f"   Q1: {quarterly_data.q1_value:,} (if not None)")
    print(f"   Q2: {quarterly_data.q2_value:,} (if not None)")
    print(f"   Q3: {quarterly_data.q3_value:,} (if not None)")
    print(f"   Annual: {quarterly_data.annual_value:,} (if not None)")
    print(f"   Can calculate Q4: {quarterly_data.can_calculate_q4()}")
    
    if quarterly_data.can_calculate_q4():
        calculated_q4 = quarterly_data.calculate_q4()
        print(f"   Calculated Q4: {calculated_q4:,}")
    
    # Now test the parent concept (total revenue)
    print("\n2. Testing Parent Revenue (root concept):")
    parent_concept = "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"
    parent_path = "001"
    
    parent_quarterly_data = repository.get_quarterly_data_for_concept_by_name_and_path(
        parent_concept, parent_path, company_cik, fiscal_year, "income_statement"
    )
    
    print(f"   Concept: {parent_concept}")
    print(f"   Path: {parent_path}")
    print(f"   Q1: {parent_quarterly_data.q1_value:,} (if not None)")
    print(f"   Q2: {parent_quarterly_data.q2_value:,} (if not None)")
    print(f"   Q3: {parent_quarterly_data.q3_value:,} (if not None)")
    print(f"   Annual: {parent_quarterly_data.annual_value:,} (if not None)")
    print(f"   Can calculate Q4: {parent_quarterly_data.can_calculate_q4()}")
    
    # Verify the annual values are different (dimensional vs parent)
    print("\n3. Verification:")
    if quarterly_data.annual_value and parent_quarterly_data.annual_value:
        if quarterly_data.annual_value != parent_quarterly_data.annual_value:
            print(f"   ✓ Gaming Member annual ({quarterly_data.annual_value:,}) != Parent annual ({parent_quarterly_data.annual_value:,})")
            print("   ✓ Fix working: Dimensional concept uses its own annual value, not parent's")
        else:
            print(f"   ⚠ Gaming Member annual == Parent annual ({quarterly_data.annual_value:,})")
            print("   ⚠ This could indicate the fix isn't working or the data is identical")
    else:
        print("   ⚠ Cannot compare - missing annual values")
    
    # Test a concept that should fail gracefully if no exact annual match
    print("\n4. Testing non-existent dimensional concept:")
    fake_concept = "fake:USCanadaMember"
    fake_path = "001.001.001"
    
    fake_quarterly_data = repository.get_quarterly_data_for_concept_by_name_and_path(
        fake_concept, fake_path, company_cik, fiscal_year, "income_statement"
    )
    
    print(f"   Concept: {fake_concept}")
    print(f"   Path: {fake_path}")
    print(f"   Found concept: {fake_quarterly_data.concept_id is not None}")
    print(f"   Annual value: {fake_quarterly_data.annual_value}")
    
    if fake_quarterly_data.annual_value is None:
        print("   ✓ Correctly returns None for non-existent dimensional concept")
    else:
        print("   ⚠ Unexpectedly found annual value - may be using parent fallback")

if __name__ == "__main__":
    test_dimensional_concept_fix()