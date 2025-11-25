"""Check why other regions don't have Q4 values."""

from config.database import DatabaseConfig, DatabaseConnection

def check_regional_data():
    """Check quarterly data availability for all regions."""
    
    # Initialize database connection
    db_config = DatabaseConfig()
    db_conn = DatabaseConnection(db_config)
    db = db_conn.connect()
    
    company_cik = "0001065280"  # Netflix
    
    print("\n" + "="*80)
    print("CHECKING QUARTERLY DATA FOR ALL REGIONS")
    print("="*80)
    
    regions = [
        "United States and Canada (UCAN)",
        "Europe, Middle East, and Africa (EMEA)",
        "Latin America (LATAM)",
        "Asia-Pacific (APAC)"
    ]
    
    for label in regions:
        print(f"\n{'='*80}")
        print(f"{label}")
        print(f"{'='*80}")
        
        concept = db.normalized_concepts_quarterly.find_one({
            "company_cik": company_cik,
            "concept": "nflx:StreamingMember",
            "statement_type": "income_statement",
            "label": label
        })
        
        if not concept:
            print("❌ Concept not found")
            continue
        
        print(f"Concept ID: {concept['_id']}")
        print(f"Path: {concept.get('path')}")
        print(f"Dimension Member: {concept.get('dimensions', {}).get('explicitMember')}")
        
        # Check 2024 data
        quarters_2024 = list(db.concept_values_quarterly.find({
            "concept_id": concept["_id"],
            "company_cik": company_cik,
            "reporting_period.fiscal_year": 2024
        }).sort("reporting_period.quarter", 1))
        
        print(f"\n2024 Quarterly Values:")
        for q in quarters_2024:
            quarter = q.get("reporting_period", {}).get("quarter")
            value = q.get("value", 0)
            print(f"  Q{quarter}: ${value:,.0f}")
        
        if len(quarters_2024) < 4:
            print(f"  Missing quarters: {4 - len(quarters_2024)}")
        
        # Check annual value
        annual_concept = db.normalized_concepts_annual.find_one({
            "company_cik": company_cik,
            "concept": "nflx:StreamingMember",
            "statement_type": "income_statement",
            "label": label
        })
        
        if annual_concept:
            annual_value = db.concept_values_annual.find_one({
                "concept_id": annual_concept["_id"],
                "company_cik": company_cik,
                "reporting_period.fiscal_year": 2024
            })
            
            if annual_value:
                print(f"\n2024 Annual Value: ${annual_value['value']:,.0f}")
                print(f"Annual Path: {annual_concept.get('path')}")
                print(f"Annual Dimension Member: {annual_concept.get('dimensions', {}).get('explicitMember')}")
            else:
                print("\n❌ No annual value for 2024")
        else:
            print("\n❌ No annual concept found")

if __name__ == "__main__":
    check_regional_data()
