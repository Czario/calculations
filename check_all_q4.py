"""Check all Q4 values for Netflix streaming member concepts."""

from config.database import DatabaseConfig, DatabaseConnection

def check_all_q4_values():
    """Check Q4 values for all streaming member concept IDs."""
    
    # Initialize database connection
    db_config = DatabaseConfig()
    db_conn = DatabaseConnection(db_config)
    db = db_conn.connect()
    
    company_cik = "0001065280"  # Netflix
    
    print("\n" + "="*80)
    print("ALL STREAMING MEMBER CONCEPTS")
    print("="*80)
    
    # Get all streaming member concepts
    concepts = list(db.normalized_concepts_quarterly.find({
        "company_cik": company_cik,
        "concept": "nflx:StreamingMember",
        "statement_type": "income_statement"
    }))
    
    print(f"\nFound {len(concepts)} streaming member concepts")
    
    for concept in concepts:
        print(f"\n{'-'*80}")
        print(f"Label: {concept.get('label')}")
        print(f"Concept ID: {concept['_id']}")
        print(f"Path: {concept.get('path')}")
        print(f"Dimension Member: {concept.get('dimensions', {}).get('explicitMember')}")
        
        # Get all Q4 values for this concept ID
        q4_values = list(db.concept_values_quarterly.find({
            "concept_id": concept["_id"],
            "company_cik": company_cik,
            "reporting_period.quarter": 4
        }).sort("reporting_period.fiscal_year", -1).limit(5))
        
        if q4_values:
            print(f"\nRecent Q4 values:")
            for q4 in q4_values:
                year = q4.get("reporting_period", {}).get("fiscal_year")
                value = q4.get("value", 0)
                print(f"  {year}: ${value:,.0f}")
        else:
            print("\n❌ No Q4 values found for this concept ID")

if __name__ == "__main__":
    check_all_q4_values()
