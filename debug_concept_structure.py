"""Debug quarterly concepts - see full document structure."""

from config.database import DatabaseConfig, DatabaseConnection
import json

def debug_concepts():
    """See full structure of streaming member concepts."""
    
    # Initialize database connection
    db_config = DatabaseConfig()
    db_conn = DatabaseConnection(db_config)
    db = db_conn.connect()
    
    company_cik = "0001065280"  # Netflix
    concept_name = "nflx:StreamingMember"
    statement_type = "income_statement"
    
    print("\n" + "="*80)
    print("ALL nflx:StreamingMember QUARTERLY CONCEPTS")
    print("="*80)
    
    # Get all matching concepts
    concepts = list(db.normalized_concepts_quarterly.find({
        "company_cik": company_cik,
        "concept": concept_name,
        "statement_type": statement_type
    }))
    
    for i, concept in enumerate(concepts, 1):
        print(f"\n--- Concept {i} ---")
        print(f"Path: {concept.get('path')}")
        print(f"Label: {concept.get('label')}")
        print(f"Concept: {concept.get('concept')}")
        print(f"Original Concept: {concept.get('original_concept')}")
        print(f"Parent Concept ID: {concept.get('parent_concept_id')}")
        
        # Check if there are any other differentiating fields
        for key, value in concept.items():
            if key not in ['_id', 'path', 'label', 'concept', 'original_concept', 
                          'parent_concept_id', 'company_cik', 'statement_type']:
                print(f"{key}: {value}")
    
    print("\n" + "="*80)
    print("ALL nflx:StreamingMember ANNUAL CONCEPTS")
    print("="*80)
    
    # Get all matching annual concepts
    annual_concepts = list(db.normalized_concepts_annual.find({
        "company_cik": company_cik,
        "concept": concept_name,
        "statement_type": statement_type
    }))
    
    for i, concept in enumerate(annual_concepts, 1):
        print(f"\n--- Annual Concept {i} ---")
        print(f"Path: {concept.get('path')}")
        print(f"Label: {concept.get('label')}")
        print(f"Concept: {concept.get('concept')}")
        print(f"Original Concept: {concept.get('original_concept')}")
        
        # Check if there are any other differentiating fields
        for key, value in concept.items():
            if key not in ['_id', 'path', 'label', 'concept', 'original_concept', 
                          'parent_concept_id', 'company_cik', 'statement_type']:
                print(f"{key}: {value}")

if __name__ == "__main__":
    debug_concepts()
