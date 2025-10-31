#!/usr/bin/env python3
"""Test root parent matching for FamilyOfAppsMember."""

from config.database import DatabaseConfig, DatabaseConnection
from repositories.financial_repository import FinancialDataRepository

def test_root_parent_matching():
    """Test the root parent matching logic."""
    
    db_config = DatabaseConfig()
    
    with DatabaseConnection(db_config) as db:
        repository = FinancialDataRepository(db)
        
        print("=== Testing Root Parent Matching ===\n")
        
        company_cik = "0001326801"
        
        # Get the two FamilyOfAppsMember concepts
        concepts = list(repository.normalized_concepts_quarterly.find({
            "concept": "meta:FamilyOfAppsMember",
            "company_cik": company_cik,
            "statement_type": "income_statement"
        }))
        
        for i, concept in enumerate(concepts, 1):
            print(f"{i}. FamilyOfAppsMember concept:")
            print(f"   Path: {concept.get('path', 'N/A')}")
            
            # Get root parent info
            root_parent_id, root_parent_name = repository._get_root_parent_concept_info(
                concept, "normalized_concepts_quarterly"
            )
            
            print(f"   Root Parent ID: {root_parent_id}")
            print(f"   Root Parent Name: {root_parent_name}")
            
            print()

if __name__ == "__main__":
    test_root_parent_matching()