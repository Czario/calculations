#!/usr/bin/env python3

from config.database import DatabaseConfig, DatabaseConnection
from repositories.financial_repository import FinancialDataRepository
from services.q4_calculation_service import Q4CalculationService

def test_q4_with_parent_based_matching():
    """Test Q4 calculation with the new parent-based matching approach."""
    
    config = DatabaseConfig()
    connection = DatabaseConnection(config)
    db = connection.connect()
    repository = FinancialDataRepository(db)
    service = Q4CalculationService(repository)

    print("=== TESTING PARENT-BASED MATCHING WITH Q4 CALCULATION ===")

    # Test a specific dimensional concept calculation
    result = service._calculate_q4_generic(
        "msft:GamingMember", "001.001", "0000789019", 2025, "income_statement"
    )

    print(f"Gaming Member Q4 calculation result: {result}")

    # Test the parent concept calculation  
    parent_result = service._calculate_q4_generic(
        "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax", "001", "0000789019", 2025, "income_statement"
    )

    print(f"Parent Revenue Q4 calculation result: {parent_result}")
    
    # Test another dimensional concept
    cloud_result = service._calculate_q4_generic(
        "msft:IntelligentCloudMember", "001.002", "0000789019", 2025, "income_statement"
    )
    
    print(f"Intelligent Cloud Q4 calculation result: {cloud_result}")

if __name__ == "__main__":
    test_q4_with_parent_based_matching()