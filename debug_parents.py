#!/usr/bin/env python3
"""Debug parent concept data."""

from config.database import DatabaseConfig, DatabaseConnection
from repositories.financial_repository import FinancialDataRepository

def debug_parent_concepts():
    """Debug the parent concept data to understand why names are None."""
    
    db_config = DatabaseConfig()
    
    with DatabaseConnection(db_config) as db:
        repository = FinancialDataRepository(db)
        
        print("=== Debugging Parent Concept Data ===\n")
        
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
            print(f"   Concept ID (parent): {concept.get('concept_id', 'N/A')}")
            
            parent_id = concept.get("concept_id")
            if parent_id:
                # Find the parent concept in quarterly collection
                parent_concept = repository.normalized_concepts_quarterly.find_one({"_id": parent_id})
                if parent_concept:
                    print(f"   Parent concept found in QUARTERLY:")
                    print(f"     _id: {parent_concept['_id']}")
                    print(f"     concept: {parent_concept.get('concept', 'MISSING')}")
                    print(f"     path: {parent_concept.get('path', 'N/A')}")
                    print(f"     dimension_concept: {parent_concept.get('dimension_concept', 'N/A')}")
                else:
                    # Try annual collection
                    parent_concept = repository.normalized_concepts_annual.find_one({"_id": parent_id})
                    if parent_concept:
                        print(f"   Parent concept found in ANNUAL:")
                        print(f"     _id: {parent_concept['_id']}")
                        print(f"     concept: {parent_concept.get('concept', 'MISSING')}")
                        print(f"     path: {parent_concept.get('path', 'N/A')}")
                        print(f"     dimension_concept: {parent_concept.get('dimension_concept', 'N/A')}")
                    else:
                        print(f"   ✗ Parent concept not found in either collection with ID: {parent_id}")
            else:
                print(f"   ✗ No parent concept ID (this is a root concept)")
            
            print()

if __name__ == "__main__":
    debug_parent_concepts()