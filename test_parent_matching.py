#!/usr/bin/env python3
"""Test parent matching issue with FamilyOfAppsMember."""

from config.database import DatabaseConfig, DatabaseConnection
from repositories.financial_repository import FinancialDataRepository

def test_family_apps_parent_matching():
    """Test the parent matching issue with FamilyOfAppsMember under different parents."""
    
    db_config = DatabaseConfig()
    
    with DatabaseConnection(db_config) as db:
        repository = FinancialDataRepository(db)
        
        print("=== Testing FamilyOfAppsMember Parent Matching Issue ===\n")
        
        # Test the two different paths for FamilyOfAppsMember
        test_cases = [
            {
                "concept_name": "meta:FamilyOfAppsMember",
                "path": "001.002.001",  # Under Revenue
                "description": "FamilyOfAppsMember under Revenue"
            },
            {
                "concept_name": "meta:FamilyOfAppsMember", 
                "path": "003.001",      # Under Operating Income/Loss
                "description": "FamilyOfAppsMember under Operating Income/Loss"
            }
        ]
        
        company_cik = "0001326801"
        fiscal_year = 2024
        statement_type = "income_statement"
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"{i}. Testing: {test_case['description']}")
            print(f"   Path: {test_case['path']}")
            
            # Find the quarterly concept
            quarterly_concept = repository.normalized_concepts_quarterly.find_one({
                "concept": test_case["concept_name"],
                "path": test_case["path"],
                "company_cik": company_cik,
                "statement_type": statement_type
            })
            
            if quarterly_concept:
                print(f"   ✓ Found quarterly concept: {quarterly_concept['_id']}")
                
                # Get parent info
                parent_id, parent_name = repository._get_parent_concept_info(
                    quarterly_concept, "normalized_concepts_quarterly"
                )
                print(f"   Parent ID: {parent_id}")
                print(f"   Parent Name: {parent_name}")
                
                # Find matching annual concept
                annual_concept = repository._find_matching_annual_concept(
                    test_case["concept_name"], company_cik, statement_type,
                    parent_id, parent_name, test_case["path"]
                )
                
                if annual_concept:
                    print(f"   ✓ Found annual concept: {annual_concept['_id']}")
                    print(f"   Annual Path: {annual_concept.get('path', 'N/A')}")
                    
                    # Check if we got the same annual concept for both (the problem!)
                    if i == 1:
                        first_annual_id = annual_concept['_id']
                    elif i == 2 and annual_concept['_id'] == first_annual_id:
                        print(f"   🚨 PROBLEM: Both concepts match to same annual concept!")
                else:
                    print(f"   ✗ No matching annual concept found")
                
            else:
                print(f"   ✗ Quarterly concept not found")
            
            print()

if __name__ == "__main__":
    test_family_apps_parent_matching()