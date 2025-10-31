#!/usr/bin/env python3
"""Quick test to check Q4 deletion count."""

from config.database import DatabaseConfig, DatabaseConnection
from repositories.financial_repository import FinancialDataRepository

def test_deletion():
    # Setup database connection
    db_config = DatabaseConfig()
    
    with DatabaseConnection(db_config) as db:
        repository = FinancialDataRepository(db)
        
        # Count Q4 values before deletion
        before_count = repository.concept_values_quarterly.count_documents({
            "company_cik": "0001326801",
            "reporting_period.quarter": 4,
            "statement_type": {"$in": ["income_statement", "cash_flows"]}
        })
        print(f"Q4 values before deletion: {before_count}")
        
        # Check breakdown by statement type
        income_count = repository.concept_values_quarterly.count_documents({
            "company_cik": "0001326801", 
            "reporting_period.quarter": 4,
            "statement_type": "income_statement"
        })
        cash_count = repository.concept_values_quarterly.count_documents({
            "company_cik": "0001326801",
            "reporting_period.quarter": 4, 
            "statement_type": "cash_flows"
        })
        print(f"  Income statement Q4 values: {income_count}")
        print(f"  Cash flows Q4 values: {cash_count}")
        
        # Perform deletion
        deleted_count = repository.delete_all_q4_values("0001326801")
        print(f"Deleted Q4 values: {deleted_count}")
        
        # Count after deletion
        after_count = repository.concept_values_quarterly.count_documents({
            "company_cik": "0001326801",
            "reporting_period.quarter": 4,
            "statement_type": {"$in": ["income_statement", "cash_flows"]}
        })
        print(f"Q4 values after deletion: {after_count}")

if __name__ == "__main__":
    test_deletion()