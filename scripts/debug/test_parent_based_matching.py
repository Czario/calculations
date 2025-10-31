#!/usr/bin/env python3

from config.database import DatabaseConfig, DatabaseConnection
from repositories.financial_repository import FinancialDataRepository

def test_parent_based_matching():
    """Test that the new parent-based matching logic works correctly."""
    
    config = DatabaseConfig()
    connection = DatabaseConnection(config)
    db = connection.connect()
    repository = FinancialDataRepository(db)
    
    print("=== TESTING PARENT-BASED CONCEPT MATCHING ===")
    
    company_cik = "0000789019"  # Microsoft
    fiscal_year = 2024
    
    # Test 1: Gaming Member (dimensional concept)
    print("\n1. Testing Gaming Member (dimensional concept):")
    gaming_concept = "msft:GamingMember"
    gaming_path = "001.001"
    
    quarterly_data = repository.get_quarterly_data_for_concept_by_name_and_path(
        gaming_concept, gaming_path, company_cik, fiscal_year, "income_statement"
    )
    
    print(f"   Concept: {gaming_concept}")
    print(f"   Path: {gaming_path}")
    print(f"   Found quarterly concept: {quarterly_data.concept_id is not None}")
    print(f"   Annual value found: {quarterly_data.annual_value is not None}")
    if quarterly_data.annual_value:
        print(f"   Annual value: {quarterly_data.annual_value:,}")
    
    # Test 2: Parent concept (total revenue)
    print("\n2. Testing Parent Revenue (root concept):")
    parent_concept = "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"
    parent_path = "001"
    
    parent_data = repository.get_quarterly_data_for_concept_by_name_and_path(
        parent_concept, parent_path, company_cik, fiscal_year, "income_statement"
    )
    
    print(f"   Concept: {parent_concept}")
    print(f"   Path: {parent_path}")
    print(f"   Found quarterly concept: {parent_data.concept_id is not None}")
    print(f"   Annual value found: {parent_data.annual_value is not None}")
    if parent_data.annual_value:
        print(f"   Annual value: {parent_data.annual_value:,}")
    
    # Test 3: Verify parent-based matching is working
    print("\n3. Parent-Based Matching Verification:")
    if quarterly_data.annual_value and parent_data.annual_value:
        print(f"   Gaming Member annual: {quarterly_data.annual_value:,}")
        print(f"   Total Revenue annual: {parent_data.annual_value:,}")
        
        if quarterly_data.annual_value != parent_data.annual_value:
            print("   ✓ Parent-based matching working: Different values for dimensional vs parent")
            print("   ✓ Gaming Member uses its own annual value, not parent's total revenue")
        else:
            print("   ⚠ Values are identical - may indicate parent fallback issue")
    
    # Test 4: Test a concept that might not have exact match (should return None, not parent)
    print("\n4. Testing Non-Existent Dimensional Concept:")
    fake_concept = "fake:NonExistentMember" 
    fake_path = "999.999"
    
    fake_data = repository.get_quarterly_data_for_concept_by_name_and_path(
        fake_concept, fake_path, company_cik, fiscal_year, "income_statement"
    )
    
    print(f"   Concept: {fake_concept}")
    print(f"   Found quarterly concept: {fake_data.concept_id is not None}")
    print(f"   Annual value: {fake_data.annual_value}")
    
    if fake_data.annual_value is None:
        print("   ✓ Correctly returns None for non-existent concept (no parent fallback)")
    else:
        print("   ⚠ Unexpectedly found annual value - parent fallback may still be active")
    
    # Test 5: Test a complex dimensional concept
    print("\n5. Testing Complex Dimensional Concept:")
    complex_concept = "msft:IntelligentCloudMember"
    complex_path = "001.002"
    
    complex_data = repository.get_quarterly_data_for_concept_by_name_and_path(
        complex_concept, complex_path, company_cik, fiscal_year, "income_statement"
    )
    
    print(f"   Concept: {complex_concept}")
    print(f"   Path: {complex_path}")
    print(f"   Found concept: {complex_data.concept_id is not None}")
    print(f"   Annual value: {complex_data.annual_value:,}" if complex_data.annual_value else "None")
    
    if complex_data.annual_value and parent_data.annual_value:
        if complex_data.annual_value != parent_data.annual_value:
            print("   ✓ Intelligent Cloud uses its own annual value (parent-based matching)")
        else:
            print("   ⚠ Same as parent value - may need investigation")

if __name__ == "__main__":
    test_parent_based_matching()