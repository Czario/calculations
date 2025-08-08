#!/usr/bin/env python3
"""Investigate Gaming Member Q4 data."""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def investigate_gaming_member():
    """Investigate why Gaming Member has Q4 data."""
    print("Investigating Gaming Member Q4 Data")
    print("=" * 50)
    
    try:
        from config.database import DatabaseConfig, DatabaseConnection
        from repositories.financial_repository import FinancialDataRepository
        
        # Connect to database
        config = DatabaseConfig()
        with DatabaseConnection(config) as db:
            repository = FinancialDataRepository(db)
            
            company_cik = "0000789019"  # Microsoft
            concept_name = "msft:GamingMember"
            fiscal_year = 2024
            
            print(f"Searching for: {concept_name}")
            print(f"Company: {company_cik} (Microsoft)")
            print(f"Fiscal Year: {fiscal_year}")
            print()
            
            # Find the concept in quarterly normalized concepts
            quarterly_concept = db.normalized_concepts_quarterly.find_one({
                "concept": concept_name,
                "company_cik": company_cik,
                "statement_type": "income_statement"
            })
            
            if quarterly_concept:
                print("✓ Found quarterly concept:")
                print(f"  ID: {quarterly_concept['_id']}")
                print(f"  Path: {quarterly_concept.get('path', 'N/A')}")
                print(f"  Dimension concept: {quarterly_concept.get('dimension_concept', False)}")
                print(f"  Label: {quarterly_concept.get('label', 'N/A')}")
                
                if quarterly_concept.get('concept_id'):
                    parent_concept = db.normalized_concepts_quarterly.find_one({
                        "_id": quarterly_concept['concept_id']
                    })
                    if parent_concept:
                        print(f"  Parent concept: {parent_concept.get('concept', 'N/A')}")
                
                print()
                
                # Get all quarterly values for this concept
                quarterly_values = list(db.concept_values_quarterly.find({
                    "concept_id": quarterly_concept["_id"],
                    "company_cik": company_cik,
                    "reporting_period.fiscal_year": fiscal_year
                }).sort("reporting_period.quarter", 1))
                
                print("Quarterly values found:")
                for qval in quarterly_values:
                    quarter = qval["reporting_period"]["quarter"]
                    value = qval["value"]
                    end_date = qval["reporting_period"]["end_date"]
                    calculated = qval.get("calculated", False)
                    
                    print(f"  Q{quarter}: {value:,.0f} (End: {end_date}) {'[CALCULATED]' if calculated else '[FROM FILING]'}")
                
                print()
                
                # Check if this is a Q4 value that was calculated by our system
                q4_values = [v for v in quarterly_values if v["reporting_period"]["quarter"] == 4]
                if q4_values:
                    q4_value = q4_values[0]
                    print("Q4 Analysis:")
                    print(f"  Value: {q4_value['value']:,.0f}")
                    print(f"  Calculated: {q4_value.get('calculated', False)}")
                    print(f"  Data source: {q4_value['reporting_period'].get('data_source', 'N/A')}")
                    print(f"  Form type: {q4_value.get('form_type', 'N/A')}")
                    
                    if q4_value.get('calculated'):
                        print("  ✓ This Q4 was calculated by our system")
                    else:
                        print("  ⚠ This Q4 appears to be from original filing data")
                        
                    print()
                
                # Try to get annual value using our repository method
                quarterly_data = repository.get_quarterly_data_for_concept_by_name(
                    concept_name, company_cik, fiscal_year
                )
                
                print("Repository analysis:")
                print(f"  Q1: {quarterly_data.q1_value}")
                print(f"  Q2: {quarterly_data.q2_value}")
                print(f"  Q3: {quarterly_data.q3_value}")
                print(f"  Annual: {quarterly_data.annual_value}")
                print(f"  Can calculate Q4: {quarterly_data.can_calculate_q4()}")
                
                if quarterly_data.can_calculate_q4():
                    calculated_q4 = quarterly_data.calculate_q4()
                    print(f"  Our calculated Q4 would be: {calculated_q4:,.0f}")
                    
                    # Compare with existing Q4 if present
                    if q4_values:
                        existing_q4 = q4_values[0]["value"]
                        print(f"  Existing Q4 in database: {existing_q4:,.0f}")
                        if abs(calculated_q4 - existing_q4) < 1:
                            print("  ✓ Values match - Q4 was correctly calculated")
                        else:
                            print(f"  ⚠ Values differ by: {abs(calculated_q4 - existing_q4):,.0f}")
                else:
                    missing = []
                    if quarterly_data.q1_value is None:
                        missing.append("Q1")
                    if quarterly_data.q2_value is None:
                        missing.append("Q2")
                    if quarterly_data.q3_value is None:
                        missing.append("Q3")
                    if quarterly_data.annual_value is None:
                        missing.append("Annual")
                    print(f"  Cannot calculate Q4 - missing: {', '.join(missing)}")
                
            else:
                print("✗ Gaming Member concept not found in quarterly normalized concepts")
                
                # Check if it exists in annual concepts
                annual_concept = db.normalized_concepts_annual.find_one({
                    "concept": concept_name,
                    "company_cik": company_cik,
                    "statement_type": "income_statement"
                })
                
                if annual_concept:
                    print("ℹ Found in annual concepts though")
                else:
                    print("ℹ Not found in annual concepts either")
            
            return True
            
    except Exception as e:
        print(f"✗ Investigation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run Gaming Member investigation."""
    success = investigate_gaming_member()
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
