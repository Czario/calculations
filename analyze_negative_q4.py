"""Analyze negative Q4 values to see if they're legitimate."""

from config.database import DatabaseConfig, DatabaseConnection

def analyze_negative_q4():
    """Check if negative Q4 values are legitimate or errors."""
    
    # Initialize database connection
    db_config = DatabaseConfig()
    db_conn = DatabaseConnection(db_config)
    db = db_conn.connect()
    
    companies = [
        ("0000320193", "Apple"),
        ("0000789019", "Microsoft"),
        ("0001065280", "Netflix"),
        ("0001326801", "Meta")
    ]
    
    print("\n" + "="*80)
    print("ANALYZING NEGATIVE Q4 VALUES")
    print("="*80)
    
    for cik, name in companies:
        print(f"\n{'='*80}")
        print(f"{name} (CIK: {cik})")
        print(f"{'='*80}")
        
        # Get sample negative Q4 values
        negative_q4s = list(db.concept_values_quarterly.find({
            "company_cik": cik,
            "reporting_period.quarter": 4,
            "value": {"$lt": 0}
        }).limit(5))
        
        print(f"\nTotal negative Q4 values: {len(negative_q4s)}")
        
        if not negative_q4s:
            print("✅ No negative Q4 values")
            continue
        
        print("\nSample negative Q4 values:")
        
        for q4 in negative_q4s:
            concept_id = q4.get("concept_id")
            concept = db.normalized_concepts_quarterly.find_one({"_id": concept_id})
            
            if not concept:
                continue
            
            concept_name = concept.get("concept", "Unknown")
            label = concept.get("label", "Unknown")
            statement_type = concept.get("statement_type", "Unknown")
            year = q4.get("reporting_period", {}).get("fiscal_year")
            q4_value = q4.get("value", 0)
            
            # Get Q1, Q2, Q3, Annual values
            q1_val = db.concept_values_quarterly.find_one({
                "concept_id": concept_id,
                "company_cik": cik,
                "reporting_period.fiscal_year": year,
                "reporting_period.quarter": 1
            })
            
            q2_val = db.concept_values_quarterly.find_one({
                "concept_id": concept_id,
                "company_cik": cik,
                "reporting_period.fiscal_year": year,
                "reporting_period.quarter": 2
            })
            
            q3_val = db.concept_values_quarterly.find_one({
                "concept_id": concept_id,
                "company_cik": cik,
                "reporting_period.fiscal_year": year,
                "reporting_period.quarter": 3
            })
            
            # Find matching annual concept
            annual_concept = None
            if concept.get("dimensions") and "explicitMember" in concept.get("dimensions", {}):
                member = concept["dimensions"]["explicitMember"]
                annual_concept = db.normalized_concepts_annual.find_one({
                    "company_cik": cik,
                    "concept": concept_name,
                    "statement_type": statement_type,
                    "dimensions.explicitMember": member
                })
            
            if not annual_concept:
                annual_concept = db.normalized_concepts_annual.find_one({
                    "company_cik": cik,
                    "concept": concept_name,
                    "statement_type": statement_type,
                    "path": concept.get("path")
                })
            
            annual_val = None
            if annual_concept:
                annual_val = db.concept_values_annual.find_one({
                    "concept_id": annual_concept["_id"],
                    "company_cik": cik,
                    "reporting_period.fiscal_year": year
                })
            
            print(f"\n  Concept: {concept_name}")
            print(f"  Label: {label}")
            print(f"  Statement: {statement_type}")
            print(f"  Year: {year}")
            print(f"  Q1: ${q1_val['value']:,.0f}" if q1_val else "  Q1: None")
            print(f"  Q2: ${q2_val['value']:,.0f}" if q2_val else "  Q2: None")
            print(f"  Q3: ${q3_val['value']:,.0f}" if q3_val else "  Q3: None")
            print(f"  Annual: ${annual_val['value']:,.0f}" if annual_val else "  Annual: None")
            print(f"  Q4 (Calculated): ${q4_value:,.0f}")
            
            # Check if calculation is correct
            if q1_val and q2_val and q3_val and annual_val:
                expected_q4 = annual_val['value'] - (q1_val['value'] + q2_val['value'] + q3_val['value'])
                if abs(expected_q4 - q4_value) < 1:
                    print(f"  Status: ✅ Calculation correct (legitimately negative)")
                else:
                    print(f"  Status: ❌ Calculation error (Expected: ${expected_q4:,.0f})")
            else:
                print(f"  Status: ⚠️  Missing data")
        
        # Count by statement type
        income_neg = db.concept_values_quarterly.count_documents({
            "company_cik": cik,
            "reporting_period.quarter": 4,
            "value": {"$lt": 0},
            "statement_type": "income_statement"
        })
        
        cash_neg = db.concept_values_quarterly.count_documents({
            "company_cik": cik,
            "reporting_period.quarter": 4,
            "value": {"$lt": 0},
            "statement_type": "cash_flows"
        })
        
        print(f"\n  Breakdown:")
        print(f"    Income Statement: {income_neg} negative Q4 values")
        print(f"    Cash Flows: {cash_neg} negative Q4 values")

if __name__ == "__main__":
    analyze_negative_q4()
