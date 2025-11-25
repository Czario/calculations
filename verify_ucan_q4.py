"""Verify UCAN Q4 2024 value after recalculation."""

from config.database import DatabaseConfig, DatabaseConnection

def verify_ucan_q4():
    """Verify UCAN streaming member Q4 value for 2024."""
    
    # Initialize database connection
    db_config = DatabaseConfig()
    db_conn = DatabaseConnection(db_config)
    db = db_conn.connect()
    
    company_cik = "0001065280"  # Netflix
    
    print("\n" + "="*80)
    print("VERIFYING UCAN STREAMING MEMBER Q4 (2024)")
    print("="*80)
    
    # Find UCAN streaming member concept
    ucan_concept = db.normalized_concepts_quarterly.find_one({
        "company_cik": company_cik,
        "concept": "nflx:StreamingMember",
        "statement_type": "income_statement",
        "label": "United States and Canada (UCAN)"
    })
    
    if not ucan_concept:
        print("❌ UCAN concept not found!")
        return
    
    print(f"\nUCAN Concept Found:")
    print(f"  Path: {ucan_concept.get('path')}")
    print(f"  Label: {ucan_concept.get('label')}")
    print(f"  Dimensions: {ucan_concept.get('dimensions', {}).get('explicitMember')}")
    
    # Get Q4 value
    ucan_q4 = db.concept_values_quarterly.find_one({
        "concept_id": ucan_concept["_id"],
        "company_cik": company_cik,
        "reporting_period.fiscal_year": 2024,
        "reporting_period.quarter": 4
    })
    
    if not ucan_q4:
        print("\n❌ Q4 value not found!")
        return
    
    print(f"\nUCAN Q4 2024 Value: ${ucan_q4['value']:,.0f}")
    print(f"Expected:           $4,517,018,000")
    
    diff = abs(ucan_q4['value'] - 4517018000)
    if diff < 1000:  # Within $1000
        print(f"\n✅ CORRECT! (Difference: ${diff:,.0f})")
    else:
        print(f"\n❌ STILL WRONG! (Difference: ${diff:,.0f})")
    
    # Check all regions
    print("\n" + "="*80)
    print("ALL STREAMING MEMBER REGIONS (2024 Q4)")
    print("="*80)
    
    regions = [
        ("United States and Canada (UCAN)", 4517018000),
        ("Europe, Middle East, and Africa (EMEA)", 3260434000),
        ("Latin America (LATAM)", 1310023000),
        ("Asia-Pacific (APAC)", 1182892000)
    ]
    
    for label, expected in regions:
        concept = db.normalized_concepts_quarterly.find_one({
            "company_cik": company_cik,
            "concept": "nflx:StreamingMember",
            "statement_type": "income_statement",
            "label": label
        })
        
        if not concept:
            print(f"\n{label}: ❌ Concept not found")
            continue
        
        q4_value = db.concept_values_quarterly.find_one({
            "concept_id": concept["_id"],
            "company_cik": company_cik,
            "reporting_period.fiscal_year": 2024,
            "reporting_period.quarter": 4
        })
        
        if not q4_value:
            print(f"\n{label}: ❌ Q4 value not found")
            continue
        
        actual = q4_value['value']
        diff = abs(actual - expected)
        status = "✅" if diff < 1000 else "❌"
        print(f"\n{label}:")
        print(f"  Expected: ${expected:,.0f}")
        print(f"  Actual:   ${actual:,.0f}")
        print(f"  Status:   {status} (Diff: ${diff:,.0f})")
    
    # Count total Q4 values
    total_q4 = db.concept_values_quarterly.count_documents({
        "company_cik": company_cik,
        "reporting_period.quarter": 4
    })
    
    # Count negative Q4 values
    negative_q4 = db.concept_values_quarterly.count_documents({
        "company_cik": company_cik,
        "reporting_period.quarter": 4,
        "value": {"$lt": 0}
    })
    
    print("\n" + "="*80)
    print(f"Total Q4 values in database: {total_q4}")
    print(f"Negative Q4 values: {negative_q4}")
    print("="*80)

if __name__ == "__main__":
    verify_ucan_q4()
