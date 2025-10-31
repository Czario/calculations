#!/usr/bin/env python3

from config.database import DatabaseConfig, DatabaseConnection
from repositories.financial_repository import FinancialDataRepository
from services.q4_calculation_service import Q4CalculationService

def comprehensive_test():
    """Comprehensive test of the fixed calculation service."""
    
    # Test the service with Microsoft
    config = DatabaseConfig()
    connection = DatabaseConnection(config)
    db = connection.connect()
    repository = FinancialDataRepository(db)
    service = Q4CalculationService(repository)

    print("=== COMPREHENSIVE TEST ===")
    print("Testing Q4 calculation for Microsoft income statement concepts...")

    # Calculate Q4 for Microsoft (should handle dimensional concepts correctly now)
    result = service.calculate_q4_for_company("0000789019")

    print(f"Processed concepts: {result['processed_concepts']}")
    print(f"Successful calculations: {result['successful_calculations']}")
    print(f"Skipped concepts: {result['skipped_concepts']}")
    print(f"Errors: {len(result['errors'])}")

    if result["errors"]:
        print("\nFirst 5 errors:")
        for error in result["errors"][:5]:
            print(f"  - {error}")
    
    # Specifically test that dimensional concepts work correctly
    print("\n=== DIMENSIONAL CONCEPT VERIFICATION ===")
    
    # Check that the Gaming Member Q4 was calculated correctly
    gaming_q4_exists = repository.check_q4_exists_by_name_and_path(
        "msft:GamingMember", "001.001", "0000789019", 2024, "income_statement"
    )
    
    if gaming_q4_exists:
        print("✓ Gaming Member Q4 calculated successfully")
    else:
        print("⚠ Gaming Member Q4 not found")
    
    # Verify that dimensional vs parent calculations are different
    gaming_data = repository.get_quarterly_data_for_concept_by_name_and_path(
        "msft:GamingMember", "001.001", "0000789019", 2024, "income_statement"
    )
    
    parent_data = repository.get_quarterly_data_for_concept_by_name_and_path(
        "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax", "001", 
        "0000789019", 2024, "income_statement"
    )
    
    print(f"\nDimensional vs Parent Revenue Comparison:")
    print(f"  Gaming Member (dimensional): {gaming_data.annual_value:,} annual")
    print(f"  Total Revenue (parent): {parent_data.annual_value:,} annual")
    
    if gaming_data.annual_value and parent_data.annual_value:
        if gaming_data.annual_value != parent_data.annual_value:
            print("  ✓ Correctly using different values for dimensional vs parent concepts")
        else:
            print("  ⚠ Same values - may indicate an issue")

if __name__ == "__main__":
    comprehensive_test()