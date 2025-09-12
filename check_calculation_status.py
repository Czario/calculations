#!/usr/bin/env python3
"""Check why no Q4 calculations were performed."""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_calculation_status():
    """Check why no Q4 calculations were performed."""
    print("Analyzing Q4 Calculation Status")
    print("=" * 50)
    
    try:
        from config.database import DatabaseConfig, DatabaseConnection
        from repositories.financial_repository import FinancialDataRepository
        from services.q4_calculation_service import Q4CalculationService
        
        # Connect to database
        config = DatabaseConfig()
        with DatabaseConnection(config) as db:
            repository = FinancialDataRepository(db)
            service = Q4CalculationService(repository)
            
            # Check Microsoft Gaming Member that we know worked before
            company_cik = "0000789019"  # Microsoft
            concept_name = "msft:GamingMember"
            concept_path = "001.001"
            fiscal_year = 2024
            
            print(f"Checking Microsoft Gaming Member:")
            print(f"  Company: {company_cik}")
            print(f"  Concept: {concept_name}")
            print(f"  Path: {concept_path}")
            print(f"  Fiscal Year: {fiscal_year}")
            print()
            
            # Check if Q4 already exists
            q4_exists = repository.check_q4_exists_by_name_and_path(
                concept_name, concept_path, company_cik, fiscal_year
            )
            print(f"Q4 already exists: {q4_exists}")
            
            if q4_exists:
                print("✓ Q4 already exists - that's why it was skipped")
                
                # Get the quarterly data to see the values
                quarterly_data = repository.get_quarterly_data_for_concept_by_name_and_path(
                    concept_name, concept_path, company_cik, fiscal_year
                )
                
                print("Current values:")
                print(f"  Q1: {quarterly_data.q1_value}")
                print(f"  Q2: {quarterly_data.q2_value}")
                print(f"  Q3: {quarterly_data.q3_value}")
                print(f"  Annual: {quarterly_data.annual_value}")
                
                # Check actual Q4 value in database
                quarterly_concept = db.normalized_concepts_quarterly.find_one({
                    "concept": concept_name,
                    "path": concept_path,
                    "company_cik": company_cik,
                    "statement_type": "income_statement"
                })
                
                if quarterly_concept:
                    q4_record = db.concept_values_quarterly.find_one({
                        "concept_id": quarterly_concept["_id"],
                        "company_cik": company_cik,
                        "reporting_period.fiscal_year": fiscal_year,
                        "reporting_period.quarter": 4
                    })
                    
                    if q4_record:
                        print(f"  Existing Q4: {q4_record['value']:,.0f}")
                        print(f"  Calculated: {q4_record.get('calculated', False)}")
                        print(f"  Data source: {q4_record['reporting_period'].get('data_source', 'N/A')}")
            else:
                print("Q4 does not exist - checking why it wasn't calculated...")
                
                # Try the calculation
                result = service._calculate_q4_for_concept_by_name_and_path(
                    concept_name, concept_path, company_cik, fiscal_year
                )
                
                print(f"Calculation result: {result}")
            
            print()
            print("=" * 50)
            print("Checking a few more concepts to understand the pattern...")
            
            # Check some regular concepts from Microsoft
            regular_concepts = [
                ("us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax", "001"),
                ("us-gaap:CostOfGoodsAndServicesSold", "002"),
                ("us-gaap:ResearchAndDevelopmentExpense", "003")
            ]
            
            for concept_name, concept_path in regular_concepts:
                print(f"\nChecking {concept_name} (path: {concept_path}):")
                
                # Check if Q4 exists
                q4_exists = repository.check_q4_exists_by_name_and_path(
                    concept_name, concept_path, company_cik, fiscal_year
                )
                
                if q4_exists:
                    print("  ✓ Q4 already exists")
                else:
                    print("  ⚠ Q4 does not exist")
                    
                    # Check the data
                    quarterly_data = repository.get_quarterly_data_for_concept_by_name_and_path(
                        concept_name, concept_path, company_cik, fiscal_year
                    )
                    
                    missing = []
                    if quarterly_data.q1_value is None:
                        missing.append("Q1")
                    if quarterly_data.q2_value is None:
                        missing.append("Q2")
                    if quarterly_data.q3_value is None:
                        missing.append("Q3")
                    if quarterly_data.annual_value is None:
                        missing.append("Annual")
                    
                    if missing:
                        print(f"    Missing: {', '.join(missing)}")
                    else:
                        print("    All values present - should be calculated")
                        print(f"    Q1: {quarterly_data.q1_value:,.0f}")
                        print(f"    Q2: {quarterly_data.q2_value:,.0f}")
                        print(f"    Q3: {quarterly_data.q3_value:,.0f}")
                        print(f"    Annual: {quarterly_data.annual_value:,.0f}")
            
            return True
            
    except Exception as e:
        print(f"✗ Check failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Check calculation status."""
    success = check_calculation_status()
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
