#!/usr/bin/env python3
"""Debug the filing_id error in annual metadata."""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_annual_metadata():
    """Debug what's happening with annual metadata retrieval."""
    print("DEBUGGING ANNUAL METADATA RETRIEVAL")
    print("=" * 50)
    
    try:
        from config.database import DatabaseConfig, DatabaseConnection
        from repositories.financial_repository import FinancialDataRepository
        
        # Connect to database
        config = DatabaseConfig()
        with DatabaseConnection(config) as db:
            repository = FinancialDataRepository(db)
            
            company_cik = "0000789019"  # Microsoft
            concept_name = "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax"
            concept_path = "001"
            fiscal_year = 2025
            
            print(f"Testing: {concept_name}")
            print(f"Company: {company_cik}")
            print(f"Fiscal Year: {fiscal_year}")
            print()
            
            # Get annual metadata using repository method
            print("Step 1: Get annual metadata using repository method")
            annual_metadata = repository.get_annual_filing_metadata_by_name_and_path(
                concept_name, concept_path, company_cik, fiscal_year
            )
            
            if annual_metadata:
                print("✓ Annual metadata found")
                print("Available fields:")
                for key, value in annual_metadata.items():
                    if key == "reporting_period":
                        print(f"  {key}: (reporting period object)")
                        for rp_key, rp_value in value.items():
                            print(f"    {rp_key}: {rp_value}")
                    else:
                        print(f"  {key}: {value}")
                print()
                
                # Check specifically for missing fields
                missing_fields = []
                if "filing_id" not in annual_metadata:
                    missing_fields.append("filing_id")
                if "fact_id" not in annual_metadata:
                    missing_fields.append("fact_id")
                
                if missing_fields:
                    print(f"⚠ Missing fields: {', '.join(missing_fields)}")
                else:
                    print("✓ All required fields present")
                    
            else:
                print("✗ No annual metadata found")
                
                # Let's check manually
                print("\nStep 2: Manual check - find quarterly concept")
                quarterly_concept = db.normalized_concepts_quarterly.find_one({
                    "concept": concept_name,
                    "path": concept_path,
                    "company_cik": company_cik,
                    "statement_type": "income_statement"
                })
                
                if quarterly_concept:
                    print("✓ Found quarterly concept")
                    print(f"  ID: {quarterly_concept['_id']}")
                    
                    print("\nStep 3: Manual check - find annual concept")
                    annual_concept = db.normalized_concepts_annual.find_one({
                        "concept": concept_name,
                        "company_cik": company_cik,
                        "statement_type": "income_statement"
                    })
                    
                    if annual_concept:
                        print("✓ Found annual concept")
                        print(f"  ID: {annual_concept['_id']}")
                        
                        print("\nStep 4: Manual check - find annual value")
                        annual_value = db.concept_values_annual.find_one({
                            "concept_id": annual_concept["_id"],
                            "company_cik": company_cik,
                            "reporting_period.fiscal_year": fiscal_year
                        })
                        
                        if annual_value:
                            print("✓ Found annual value")
                            print("Annual value fields:")
                            for key, value in annual_value.items():
                                if key == "reporting_period":
                                    print(f"  {key}: (reporting period object)")
                                else:
                                    print(f"  {key}: {value}")
                        else:
                            print("✗ No annual value found")
                    else:
                        print("✗ No annual concept found")
                else:
                    print("✗ No quarterly concept found")
                    
    except Exception as e:
        print(f"✗ Debug failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run annual metadata debug."""
    debug_annual_metadata()

if __name__ == "__main__":
    main()
