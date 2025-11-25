"""Verify all regional Q4 values are correct."""

from config.database import DatabaseConfig, DatabaseConnection

def verify_all_regions():
    """Verify Q4 calculations match expected values."""
    
    # Initialize database connection
    db_config = DatabaseConfig()
    db_conn = DatabaseConnection(db_config)
    db = db_conn.connect()
    
    company_cik = "0001065280"  # Netflix
    
    # Expected values for 2024 Q4 (Annual - Q1 - Q2 - Q3)
    expected = {
        "United States and Canada (UCAN)": {
            "q1": 4224315000,
            "q2": 4295560000,
            "q3": 4322476000,
            "annual": 17359369000,
            "expected_q4": 4517018000
        },
        "Europe, Middle East, and Africa (EMEA)": {
            "q1": 2958193000,
            "q2": 3007772000,
            "q3": 3133466000,
            "annual": 12387035000,
            "expected_q4": 3287604000
        },
        "Latin America (LATAM)": {
            "q1": 1165008000,
            "q2": 1204145000,
            "q3": 1240892000,
            "annual": 4839816000,
            "expected_q4": 1229771000
        },
        "Asia-Pacific (APAC)": {
            "q1": 1022924000,
            "q2": 1051833000,
            "q3": 1127869000,
            "annual": 4414746000,
            "expected_q4": 1212120000
        }
    }
    
    print("\n" + "="*80)
    print("VERIFYING ALL REGIONAL Q4 VALUES (2024)")
    print("="*80)
    
    all_correct = True
    
    for label, data in expected.items():
        concept = db.normalized_concepts_quarterly.find_one({
            "company_cik": company_cik,
            "concept": "nflx:StreamingMember",
            "statement_type": "income_statement",
            "label": label
        })
        
        if not concept:
            print(f"\n{label}: ❌ Concept not found")
            all_correct = False
            continue
        
        # Get Q4 value
        q4_value = db.concept_values_quarterly.find_one({
            "concept_id": concept["_id"],
            "company_cik": company_cik,
            "reporting_period.fiscal_year": 2024,
            "reporting_period.quarter": 4
        })
        
        if not q4_value:
            print(f"\n{label}: ❌ Q4 value not found")
            all_correct = False
            continue
        
        actual = q4_value['value']
        expected_q4 = data['expected_q4']
        
        # Calculate from actual quarterly data
        calculated = data['annual'] - (data['q1'] + data['q2'] + data['q3'])
        
        print(f"\n{label}:")
        print(f"  Q1: ${data['q1']:,}")
        print(f"  Q2: ${data['q2']:,}")
        print(f"  Q3: ${data['q3']:,}")
        print(f"  Annual: ${data['annual']:,}")
        print(f"  Expected Q4: ${expected_q4:,}")
        print(f"  Actual Q4: ${actual:,}")
        print(f"  Calculated Q4: ${calculated:,}")
        
        if actual == expected_q4 == calculated:
            print(f"  Status: ✅ PERFECT MATCH")
        else:
            print(f"  Status: ❌ MISMATCH")
            all_correct = False
    
    print("\n" + "="*80)
    if all_correct:
        print("✅ ALL REGIONAL Q4 VALUES ARE CORRECT!")
    else:
        print("❌ SOME VALUES ARE INCORRECT")
    print("="*80)

if __name__ == "__main__":
    verify_all_regions()
