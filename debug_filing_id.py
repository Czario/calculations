#!/usr/bin/env python3
"""Debug the filing_id error."""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_filing_id_error():
    """Debug why filing_id is missing from annual metadata."""
    print("Debugging filing_id Error")
    print("=" * 40)
    
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
            fiscal_year = 2024
            
            print(f"Debugging for concept: {concept_name}")
            print(f"Company: {company_cik}")
            print(f"Fiscal Year: {fiscal_year}")
            print()
            
            # Get annual filing metadata using the repository method
            annual_metadata = repository.get_annual_filing_metadata_by_name_and_path(
                concept_name, concept_path, company_cik, fiscal_year
            )
            
            if annual_metadata:
                print("Annual metadata found:")
                for key, value in annual_metadata.items():
                    print(f"  {key}: {value}")
                print()
                
                # Check specifically for filing_id
                if "filing_id" in annual_metadata:
                    print("✓ filing_id is present")
                else:
                    print("✗ filing_id is MISSING")
                    print("Available keys:", list(annual_metadata.keys()))
                    
                # Check for other required fields
                required_fields = ["statement_type", "fact_id", "reporting_period"]
                missing_required = []
                for field in required_fields:
                    if field not in annual_metadata:
                        missing_required.append(field)
                
                if missing_required:
                    print(f"Missing required fields: {missing_required}")
                else:
                    print("✓ All other required fields are present")
            else:
                print("✗ No annual metadata found")
                
                # Let's check what annual data exists directly
                print("\nChecking annual concepts directly...")
                annual_concepts = list(db.normalized_concepts_annual.find({
                    "concept": concept_name,
                    "company_cik": company_cik,
                    "statement_type": "income_statement"
                }))
                
                print(f"Found {len(annual_concepts)} annual concepts")
                for i, concept in enumerate(annual_concepts):
                    print(f"  Concept {i+1}: {concept.get('concept')} (path: {concept.get('path', 'N/A')})")
                    
                    # Check values for this concept
                    annual_values = list(db.concept_values_annual.find({
                        "concept_id": concept["_id"],
                        "company_cik": company_cik,
                        "reporting_period.fiscal_year": fiscal_year
                    }))
                    
                    print(f"    Annual values: {len(annual_values)}")
                    if annual_values:
                        value = annual_values[0]
                        print(f"      Value: {value.get('value')}")
                        print(f"      filing_id present: {'filing_id' in value}")
                        print(f"      Available fields: {list(value.keys())}")
            
            return True
            
    except Exception as e:
        print(f"✗ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Debug filing_id error."""
    success = debug_filing_id_error()
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
