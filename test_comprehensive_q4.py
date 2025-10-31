#!/usr/bin/env python3
"""Comprehensive test for Q4 calculations with root parent matching."""

from config.database import DatabaseConfig, DatabaseConnection
from repositories.financial_repository import FinancialDataRepository
from services.q4_calculation_service import Q4CalculationService

def test_comprehensive_q4():
    """Test comprehensive Q4 calculation."""
    
    db_config = DatabaseConfig()
    
    with DatabaseConnection(db_config) as db:
        repository = FinancialDataRepository(db)
        service = Q4CalculationService(repository)
        
        print("=== Comprehensive Q4 Calculation Test ===\n")
        
        company_cik = "0001326801"
        fiscal_year = 2024
        
        # Run income statement calculation
        print("1. Income Statement Calculation:")
        result_income = service.calculate_q4_for_company(company_cik)
        
        print(f"   Company CIK: {result_income['company_cik']}")
        print(f"   Statement Type: {result_income['statement_type']}")
        print(f"   Processed concepts: {result_income['processed_concepts']}")
        print(f"   Successful calculations: {result_income['successful_calculations']}")
        print(f"   Skipped concepts: {result_income['skipped_concepts']}")
        
        # Run cash flow calculation
        print("\n2. Cash Flow Statement Calculation:")
        result_cash = service.calculate_q4_for_cash_flow(company_cik)
        
        print(f"   Company CIK: {result_cash['company_cik']}")
        print(f"   Statement Type: {result_cash['statement_type']}")
        print(f"   Processed concepts: {result_cash['processed_concepts']}")
        print(f"   Successful calculations: {result_cash['successful_calculations']}")
        print(f"   Skipped concepts: {result_cash['skipped_concepts']}")
        
        # Show total successful calculations
        total_successful = result_income['successful_calculations'] + result_cash['successful_calculations']
        total_processed = result_income['processed_concepts'] + result_cash['processed_concepts']
        print(f"\n=== Summary ===")
        print(f"Total processed: {total_processed}")
        print(f"Total successful: {total_successful}")
        
        if result_income.get('errors') or result_cash.get('errors'):
            income_errors = len(result_income.get('errors', []))
            cash_errors = len(result_cash.get('errors', []))
            print(f"Total errors: {income_errors + cash_errors}")
            
            # Show sample errors
            print("\nSample errors:")
            for error in (result_income.get('errors', []) + result_cash.get('errors', []))[:3]:
                print(f"  - {error}")

if __name__ == "__main__":
    test_comprehensive_q4()