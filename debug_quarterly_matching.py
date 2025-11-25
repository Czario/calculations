"""Debug quarterly concept matching to understand why wrong values are returned."""

from pymongo import MongoClient
from config.database import DatabaseConfig, DatabaseConnection
from repositories.financial_repository import FinancialDataRepository

def debug_quarterly_matching():
    """Debug why quarterly matching returns wrong values."""
    
    # Initialize database connection
    db_config = DatabaseConfig()
    db_conn = DatabaseConnection(db_config)
    db = db_conn.connect()
    
    # Initialize repository
    repo = FinancialDataRepository(db)
    
    company_cik = "0001065280"  # Netflix
    concept_name = "nflx:StreamingMember"
    statement_type = "income_statement"
    
    # Test UCAN path
    ucan_path = "001.001.001"
    
    print("\n" + "="*80)
    print("DEBUGGING QUARTERLY CONCEPT MATCHING")
    print("="*80)
    print(f"\nCompany: {company_cik}")
    print(f"Concept: {concept_name}")
    print(f"Path: {ucan_path}")
    print(f"Statement: {statement_type}")
    
    # Get all matching concepts first
    all_concepts = list(db.normalized_concepts_quarterly.find({
        "company_cik": company_cik,
        "concept": concept_name,
        "statement_type": statement_type
    }))
    
    print(f"\nFound {len(all_concepts)} concepts with name '{concept_name}':")
    for concept in all_concepts:
        print(f"  - Path: {concept.get('path')} | Label: {concept.get('label')}")
    
    # Test the method
    print("\n" + "="*80)
    print("TESTING _find_quarterly_concept METHOD")
    print("="*80)
    
    result = repo._find_quarterly_concept(
        company_cik=company_cik,
        statement_type=statement_type,
        concept_name=concept_name,
        concept_path=ucan_path
    )
    
    if result:
        print(f"\nReturned concept:")
        print(f"  Path: {result.get('path')}")
        print(f"  Label: {result.get('label')}")
        print(f"  Concept: {result.get('concept')}")
    else:
        print("\n❌ No concept returned!")
    
    # Now test the actual data retrieval
    print("\n" + "="*80)
    print("TESTING get_quarterly_data_for_concept_by_name_and_path")
    print("="*80)
    
    data = repo.get_quarterly_data_for_concept_by_name_and_path(
        company_cik=company_cik,
        statement_type=statement_type,
        concept_name=concept_name,
        concept_path=ucan_path
    )
    
    if data:
        print(f"\nReturned data for path {ucan_path}:")
        for key, value in data.items():
            if key.startswith('q') or key == 'annual':
                formatted_value = f"{value:,.0f}" if value else "None"
                print(f"  {key}: {formatted_value}")
    else:
        print("\n❌ No data returned!")

if __name__ == "__main__":
    debug_quarterly_matching()
