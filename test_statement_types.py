#!/usr/bin/env python3
"""Check statement types for cash flow concepts."""

from config.database import DatabaseConfig, DatabaseConnection
from repositories.financial_repository import FinancialDataRepository

def check_statement_types():
    db_config = DatabaseConfig()
    
    with DatabaseConnection(db_config) as db:
        repository = FinancialDataRepository(db)
        
        # Get cash flow concept names from the patterns we saw in verbose output
        cash_flow_concepts = [
            "us-gaap:NetCashProvidedByUsedInOperatingActivities",
            "us-gaap:NetCashProvidedByUsedInInvestingActivities", 
            "us-gaap:NetCashProvidedByUsedInFinancingActivities",
            "us-gaap:CashAndCashEquivalentsAtCarryingValue",
            "us-gaap:PaymentsToAcquirePropertyPlantAndEquipment"
        ]
        
        print("Checking statement types for cash flow concepts with Q4 values...")
        for concept in cash_flow_concepts:
            # Find Q4 values for this concept
            q4_values = list(repository.concept_values_quarterly.find({
                "company_cik": "0001326801",
                "reporting_period.quarter": 4,
                "concept_name": concept
            }).limit(3))
            
            if q4_values:
                statement_types = set()
                for value in q4_values:
                    statement_types.add(value.get("statement_type", "MISSING"))
                print(f"  {concept}: {list(statement_types)}")
        
        # Check all distinct statement types for Q4 values
        print("\nAll distinct statement types for Q4 values:")
        pipeline = [
            {"$match": {
                "company_cik": "0001326801",
                "reporting_period.quarter": 4
            }},
            {"$group": {"_id": "$statement_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        
        results = list(repository.concept_values_quarterly.aggregate(pipeline))
        for result in results:
            statement_type = result["_id"] if result["_id"] else "NULL"
            count = result["count"]
            print(f"  {statement_type}: {count} values")

if __name__ == "__main__":
    check_statement_types()