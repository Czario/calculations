"""Debug why EMEA Q4 is not being calculated."""

from config.database import DatabaseConfig, DatabaseConnection
from repositories.financial_repository import FinancialDataRepository

def debug_emea():
    """Debug EMEA Q4 calculation."""
    
    # Initialize database connection
    db_config = DatabaseConfig()
    db_conn = DatabaseConnection(db_config)
    db = db_conn.connect()
    
    # Initialize repository
    repo = FinancialDataRepository(db)
    
    company_cik = "0001065280"  # Netflix
    concept_name = "nflx:StreamingMember"
    statement_type = "income_statement"
    fiscal_year = 2024
    
    # Get EMEA concept
    emea_concept = db.normalized_concepts_quarterly.find_one({
        "company_cik": company_cik,
        "concept": concept_name,
        "statement_type": statement_type,
        "label": "Europe, Middle East, and Africa (EMEA)"
    })
    
    if not emea_concept:
        print("❌ EMEA concept not found!")
        return
    
    print("\n" + "="*80)
    print("EMEA QUARTERLY CONCEPT")
    print("="*80)
    print(f"Concept ID: {emea_concept['_id']}")
    print(f"Path: {emea_concept.get('path')}")
    print(f"Label: {emea_concept.get('label')}")
    print(f"Dimension Member: {emea_concept.get('dimensions', {}).get('explicitMember')}")
    
    # Try to get quarterly data using the path from EMEA quarterly concept
    emea_path = emea_concept.get('path')
    
    print("\n" + "="*80)
    print(f"TESTING _find_quarterly_concept with path: {emea_path}")
    print("="*80)
    
    result = repo._find_quarterly_concept(
        company_cik=company_cik,
        statement_type=statement_type,
        concept_name=concept_name,
        concept_path=emea_path
    )
    
    if result:
        print(f"\nReturned concept:")
        print(f"  ID: {result['_id']}")
        print(f"  Label: {result.get('label')}")
        print(f"  Dimension Member: {result.get('dimensions', {}).get('explicitMember')}")
        print(f"  Match: {'✅ CORRECT' if result['_id'] == emea_concept['_id'] else '❌ WRONG'}")
    else:
        print("\n❌ No concept returned!")
    
    # Now test with EMEA annual concept path (001.001.002)
    emea_annual = db.normalized_concepts_annual.find_one({
        "company_cik": company_cik,
        "concept": concept_name,
        "statement_type": statement_type,
        "label": "Europe, Middle East, and Africa (EMEA)"
    })
    
    if emea_annual:
        annual_path = emea_annual.get('path')
        print("\n" + "="*80)
        print(f"TESTING _find_quarterly_concept with ANNUAL path: {annual_path}")
        print("="*80)
        
        result2 = repo._find_quarterly_concept(
            company_cik=company_cik,
            statement_type=statement_type,
            concept_name=concept_name,
            concept_path=annual_path
        )
        
        if result2:
            print(f"\nReturned concept:")
            print(f"  ID: {result2['_id']}")
            print(f"  Label: {result2.get('label')}")
            print(f"  Dimension Member: {result2.get('dimensions', {}).get('explicitMember')}")
            print(f"  Match: {'✅ CORRECT' if result2['_id'] == emea_concept['_id'] else '❌ WRONG'}")
        else:
            print("\n❌ No concept returned!")
    
    # Test get_quarterly_data_for_concept_by_name_and_path
    print("\n" + "="*80)
    print("TESTING get_quarterly_data_for_concept_by_name_and_path")
    print("="*80)
    
    if emea_annual:
        data = repo.get_quarterly_data_for_concept_by_name_and_path(
            concept_name=concept_name,
            concept_path=emea_annual.get('path'),
            company_cik=company_cik,
            fiscal_year=fiscal_year,
            statement_type=statement_type
        )
        
        print(f"\nResults for path {emea_annual.get('path')}:")
        print(f"  Q1: ${data.q1_value:,.0f}" if data.q1_value else "  Q1: None")
        print(f"  Q2: ${data.q2_value:,.0f}" if data.q2_value else "  Q2: None")
        print(f"  Q3: ${data.q3_value:,.0f}" if data.q3_value else "  Q3: None")
        print(f"  Annual: ${data.annual_value:,.0f}" if data.annual_value else "  Annual: None")
        
        if data.q1_value and data.q2_value and data.q3_value and data.annual_value:
            expected_q4 = data.annual_value - (data.q1_value + data.q2_value + data.q3_value)
            print(f"\n  Expected Q4: ${expected_q4:,.0f}")
            print(f"  Actual Q4: 3,260,434,000 (from expected data)")

if __name__ == "__main__":
    debug_emea()
