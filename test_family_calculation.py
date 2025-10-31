#!/usr/bin/env python3
"""Test FamilyOfAppsMember calculation with the fix."""

from config.database import DatabaseConfig, DatabaseConnection
from repositories.financial_repository import FinancialDataRepository

def test_family_apps_calculation():
    """Test FamilyOfAppsMember Q4 calculation to verify correct parent matching."""
    
    db_config = DatabaseConfig()
    
    with DatabaseConnection(db_config) as db:
        repository = FinancialDataRepository(db)
        
        print("=== Testing FamilyOfAppsMember Q4 Calculation ===\n")
        
        company_cik = "0001326801"
        fiscal_year = 2024
        statement_type = "income_statement"
        
        # Test the two different contexts
        test_cases = [
            {
                "path": "001.002.001",  # Under Revenue
                "description": "FamilyOfAppsMember under Revenue"
            },
            {
                "path": "003.001",      # Under Operating Income/Loss
                "description": "FamilyOfAppsMember under Operating Income/Loss"
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"{i}. Testing: {test_case['description']}")
            print(f"   Path: {test_case['path']}")
            
            # Get quarterly data
            quarterly_data = repository.get_quarterly_data_for_concept_by_name_and_path(
                "meta:FamilyOfAppsMember",
                test_case["path"],
                company_cik,
                fiscal_year,
                statement_type
            )
            
            if quarterly_data and quarterly_data.concept_id:
                print(f"   ✓ Found quarterly data")
                print(f"   Q1: {quarterly_data.q1_value}")
                print(f"   Q2: {quarterly_data.q2_value}")
                print(f"   Q3: {quarterly_data.q3_value}")
                print(f"   Annual: {quarterly_data.annual_value}")
                
                if quarterly_data.annual_value and all([
                    quarterly_data.q1_value is not None,
                    quarterly_data.q2_value is not None, 
                    quarterly_data.q3_value is not None
                ]):
                    q4_calculated = (quarterly_data.annual_value - 
                                   quarterly_data.q1_value - 
                                   quarterly_data.q2_value - 
                                   quarterly_data.q3_value)
                    print(f"   Q4 (calculated): {q4_calculated}")
                else:
                    print(f"   ✗ Cannot calculate Q4 - missing data")
            else:
                print(f"   ✗ No quarterly data found")
            
            print()

if __name__ == "__main__":
    test_family_apps_calculation()